"""DYNAMIC-1 runner: PATTERN-1R's runner, copied, with the survey replaced by
a mover. The body hovers; the harness walks one world model along a straight
line with the set_pose service, and records both what it asked for and what
the world published. The service answers false even when it works, so the
published pose is what counts. None of this reaches the consumer.

PATTERN-1R survey runner: the frozen FLIGHT-1S stage script, copied,
with one stage added. After the recovery the harness sends PX4 a list of
bounded goals (MAV_CMD_DO_REPOSITION, COMMAND_INT) so the body sees the
same objects from several viewpoints and altitudes. PX4 keeps its PID,
its controllers and its failsafes; nothing streams setpoints, and the
agent is not in the loop. Targets come from the harness truth, which the
consumer never sees.

Private side of FLIGHT-1S: the only process that talks to Gazebo and PX4.

Runs inside the pinned container, one fresh process tree per episode. It
starts a Gazebo server on the effective world, lets PX4 SITL attach in
standalone mode and create its own body through the backend, drives the
frozen stage script over MAVLink, applies the disturbance as a real link
wrench, and streams one JSON line per sample and per event to the
supervisor on stdout.

Three things it deliberately does not do:

* it never writes a pose. PX4 flies the body or the body does not fly;
  the only thing this process pushes into the physics is a wrench;
* it never reads the manifest, the split, the seed or the roles. It is
  handed a world file, a spawn pose and a script, and that is all it
  knows. The script is identical in every world and every condition;
* it never reconstructs a measurement it did not observe. A missing
  quantity is reported absent, not filled in from the reference.

Ground-truth pose comes from the backend's own pose stream. Velocity is
a finite difference of that stream and is labelled as derived.
"""

import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import gz.math7  # noqa: F401
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.entity_wrench_pb2 import EntityWrench
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.transport13 import Node

from pymavlink import mavutil

PX4_BIN = "/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4"
PX4_ETC = "/opt/PX4-Autopilot/build/px4_sitl_default/etc"
PX4_MODELS = "/opt/PX4-Autopilot/Tools/simulation/gz/models"
MAVLINK_URL = "udpin:127.0.0.1:14540"

# PX4 custom mode encoding, from the PX4 MAVLink dialect.
PX4_MAIN_MODE_AUTO = 4
PX4_SUB_MODE_AUTO_TAKEOFF = 2


def emit(obj):
    sys.stdout.write(json.dumps(obj, sort_keys=True) + "\n")
    sys.stdout.flush()


def _um(v):
    return int(round(float(v) * 1_000_000))


def _mdeg(rad):
    return int(round(math.degrees(float(rad)) * 1000))


class Backend:
    """Gazebo: the clock, the truth about where the body is, and the wrench."""

    def __init__(self, world):
        self.world = world
        self.node = Node()
        self.sim_ns = 0
        self.clock_samples = 0
        self.lock = threading.Lock()
        self.body = None            # (sim_ns, x, y, z, roll, pitch, yaw) in SI
        self.body_seen = 0
        self.static_poses = {}
        self.contacts = []
        self.wrench_pub = self.node.advertise(
            f"/world/{world}/wrench/persistent", EntityWrench)
        self.clear_pub = self.node.advertise(f"/world/{world}/wrench/clear", Entity)
        self.model_name = None

    def start(self):
        ok = self.node.subscribe(Clock, f"/world/{self.world}/clock", self._clock)
        ok &= self.node.subscribe(Pose_V, f"/world/{self.world}/dynamic_pose/info",
                                  self._dyn_pose)
        ok &= self.node.subscribe(Pose_V, f"/world/{self.world}/pose/info",
                                  self._pose)
        return bool(ok)

    def _clock(self, msg):
        with self.lock:
            self.sim_ns = int(msg.sim.sec) * 1_000_000_000 + int(msg.sim.nsec)
            self.clock_samples += 1

    def _pose(self, msg):
        with self.lock:
            for p in msg.pose:
                if "::" not in p.name:
                    self.static_poses[p.name] = (p.position.x, p.position.y,
                                                 p.position.z)

    def _dyn_pose(self, msg):
        if self.model_name is None:
            return
        target = self.model_name
        stamp = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nsec)
        for p in msg.pose:
            if p.name != target:
                continue
            q = p.orientation
            roll, pitch, yaw = _quat_to_rpy(q.w, q.x, q.y, q.z)
            with self.lock:
                self.body = (stamp, p.position.x, p.position.y, p.position.z,
                             roll, pitch, yaw)
                self.body_seen += 1
            return

    def now_ns(self):
        with self.lock:
            return self.sim_ns

    def snapshot(self):
        with self.lock:
            return self.body, self.sim_ns, self.body_seen

    def model_pose(self, name):
        with self.lock:
            return self.static_poses.get(name)

    def move_model(self, name, x, y, z):
        """Ask the world to put a model somewhere. The service answers false
        even when it moves it, so the caller reads the published pose."""
        req = Pose()
        req.name = name
        req.position.x, req.position.y, req.position.z = float(x), float(y), float(z)
        req.orientation.w = 1.0
        try:
            self.node.request(f"/world/{self.world}/set_pose", req, Pose, Boolean, 300)
        except Exception as exc:                       # noqa: BLE001 - logged
            emit({"ev": "mover_error", "error": repr(exc)[:120]})
            return False
        return True

    def apply_wrench(self, link, force_n):
        msg = EntityWrench()
        msg.entity.name = link
        msg.entity.type = Entity.LINK
        msg.wrench.force.x = float(force_n[0])
        msg.wrench.force.y = float(force_n[1])
        msg.wrench.force.z = float(force_n[2])
        return bool(self.wrench_pub.publish(msg))

    def clear_wrench(self, link):
        ent = Entity()
        ent.name = link
        ent.type = Entity.LINK
        return bool(self.clear_pub.publish(ent))


def _quat_to_rpy(w, x, y, z):
    sinr = 2.0 * (w * x + y * z)
    cosr = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr, cosr)
    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)
    siny = 2.0 * (w * z + x * y)
    cosy = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny, cosy)
    return roll, pitch, yaw


class Driver:
    """The frozen stage script, over MAVLink. No motors, no PID, no map."""

    def __init__(self, timeouts):
        self.timeouts = timeouts
        self.conn = None
        self.events = []

    def connect(self, deadline_s):
        self.conn = mavutil.mavlink_connection(MAVLINK_URL)
        t0 = time.monotonic()
        while time.monotonic() - t0 < deadline_s:
            hb = self.conn.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
            if hb is not None:
                self.log("heartbeat", system=self.conn.target_system,
                         component=self.conn.target_component)
                return True
        return False

    def log(self, what, **kw):
        entry = {"event": what, "wall_s": round(time.monotonic(), 3)}
        entry.update(kw)
        self.events.append(entry)
        emit({"ev": "driver", **entry})

    def _cmd(self, command, *params):
        p = list(params) + [0.0] * (7 - len(params))
        self.conn.mav.command_long_send(
            self.conn.target_system, self.conn.target_component, command, 0,
            p[0], p[1], p[2], p[3], p[4], p[5], p[6])

    def _ack(self, command, timeout):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            msg = self.conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=1)
            if msg is not None and msg.command == command:
                return msg.result
        return None

    def set_param(self, name, value, ptype):
        self.conn.mav.param_set_send(
            self.conn.target_system, self.conn.target_component,
            name.encode(), float(value), ptype)
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5:
            msg = self.conn.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
            if msg is not None and msg.param_id.strip("\x00") == name:
                self.log("param_set", name=name, value=msg.param_value)
                return True
        self.log("param_set_timeout", name=name)
        return False

    def wait_ready(self, timeout_s):
        """Wait until PX4 says it can fly: a global position and no prearm veto."""
        t0 = time.monotonic()
        have_global = False
        while time.monotonic() - t0 < timeout_s:
            msg = self.conn.recv_match(
                type=["GLOBAL_POSITION_INT", "HEARTBEAT", "STATUSTEXT"],
                blocking=True, timeout=1)
            if msg is None:
                continue
            if msg.get_type() == "GLOBAL_POSITION_INT" and msg.lat != 0:
                have_global = True
            if msg.get_type() == "HEARTBEAT" and have_global:
                if msg.system_status in (mavutil.mavlink.MAV_STATE_STANDBY,
                                         mavutil.mavlink.MAV_STATE_ACTIVE):
                    self.log("ready", system_status=msg.system_status)
                    return True
        return False

    def global_alt_m(self, timeout_s=5):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            msg = self.conn.recv_match(type="GLOBAL_POSITION_INT", blocking=True,
                                       timeout=1)
            if msg is not None and msg.lat != 0:
                return msg.alt / 1000.0
        return None

    def arm(self, timeout_s):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            self._cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1.0)
            result = self._ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 3)
            if result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                self.log("armed")
                return True
            self.log("arm_rejected", result=result)
            time.sleep(1.0)
        return False

    def takeoff(self, timeout_s):
        """AUTO.TAKEOFF, then arm. PX4 climbs to MIS_TAKEOFF_ALT and holds.

        A bare ``MAV_CMD_NAV_TAKEOFF`` is acknowledged and then ignored on
        this build: the vehicle stays on the ground and auto-disarms ten
        seconds later. The mode switch is what actually commands a
        takeoff, and after it PX4 owns the whole climb and the hold.
        """
        self._cmd(mavutil.mavlink.MAV_CMD_DO_SET_MODE, 1.0,
                  float(PX4_MAIN_MODE_AUTO), float(PX4_SUB_MODE_AUTO_TAKEOFF))
        result = self._ack(mavutil.mavlink.MAV_CMD_DO_SET_MODE, timeout_s)
        self.log("mode_auto_takeoff", result=result)
        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def global_position(self, timeout_s=5):
        """(lat_deg, lon_deg) from PX4's own estimate."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            msg = self.conn.recv_match(type='GLOBAL_POSITION_INT', blocking=False)
            if msg is not None:
                return msg.lat / 1e7, msg.lon / 1e7
            time.sleep(0.02)
        return None

    def reposition(self, lat_deg, lon_deg, alt_rel_m, yaw_rad):
        """One bounded goal. PX4 flies it, or refuses it."""
        self.conn.mav.command_int_send(
            self.conn.target_system, self.conn.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            mavutil.mavlink.MAV_CMD_DO_REPOSITION, 0, 0,
            SURVEY_SPEED_MS, 1.0, 0.0, float(yaw_rad),
            int(round(lat_deg * 1e7)), int(round(lon_deg * 1e7)), float(alt_rel_m))
        result = self._ack(mavutil.mavlink.MAV_CMD_DO_REPOSITION, 5)
        self.log('reposition', result=result, lat=lat_deg, lon=lon_deg,
                 alt_rel_m=alt_rel_m, yaw=yaw_rad)
        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def land(self, timeout_s):
        self._cmd(mavutil.mavlink.MAV_CMD_NAV_LAND)
        result = self._ack(mavutil.mavlink.MAV_CMD_NAV_LAND, timeout_s)
        self.log("land_command", result=result)
        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def wait_disarm(self, timeout_s):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            msg = self.conn.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
            if msg is None:
                continue
            armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            if not armed:
                self.log("disarmed")
                return True
        self._cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0.0, 21196.0)
        result = self._ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 5)
        self.log("forced_disarm", result=result)
        return result == mavutil.mavlink.MAV_RESULT_ACCEPTED

    def drain(self):
        """Keep the MAVLink socket from backing up while we sample poses."""
        for _ in range(64):
            if self.conn.recv_match(blocking=False) is None:
                return


SURVEY_SPEED_MS = 1.0            # slow enough that a bearing drifts under a
                                 # degree per scan, which is what tracking needs


class ConfiguredDriver(Driver):
    """FLIGHT-1S v6's configured driver, over this runner's Driver: PX4
    parameters from the environment, and its own first-heartbeat deadline."""

    ALLOWED = {'EKF2_GPS_DELAY', 'MPC_XY_VEL_P_ACC', 'MPC_XY_VEL_D_ACC',
               'MPC_XY_VEL_I_ACC', 'EKF2_NOAID_NOISE', 'EKF2_GPS_P_NOISE', 'EKF2_GPS_V_NOISE'}

    def connect(self, timeout_s):
        parameters = json.loads(os.environ.get('FLIGHT1S_PARAMETERS', '{}'))
        if not set(parameters) <= self.ALLOWED:
            raise ValueError('unexpected flight parameter')
        heartbeat_s = float(os.environ.get('FLIGHT1S_HEARTBEAT_S', '0'))
        if heartbeat_s > 0:
            timeout_s = min(timeout_s, heartbeat_s)
        if not super().connect(timeout_s):
            return False
        for name, value in sorted(parameters.items()):
            if not super().set_param(name, value, mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
                return False
            actual = self.events[-1].get('value')
            if actual is None or not math.isclose(actual, value, abs_tol=1e-5):
                raise RuntimeError('PX4 parameter readback mismatch: ' + name)
        return True


def main():
    cfg = json.loads(sys.argv[1])
    world = cfg["world_name"]
    stages = cfg["stages"]
    timeouts = cfg["timeouts"]
    disturb = cfg["disturbance"]
    condition = cfg["condition"]
    sample_dt = 1.0 / float(cfg["rates"]["sample_hz"])

    workdir = Path(cfg["workdir"])
    workdir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["GZ_SIM_RESOURCE_PATH"] = PX4_MODELS
    env["GZ_FUEL_STATIC_ONLY"] = "1"
    gz = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "--headless-rendering", cfg["world_path"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)

    backend = Backend(world)
    if not backend.start():
        emit({"ev": "error", "why": "backend_subscribe_failed"})
        return 3

    t0 = time.monotonic()
    while backend.clock_samples == 0:
        if time.monotonic() - t0 > timeouts["launch_s"]:
            emit({"ev": "error", "why": "backend_no_clock"})
            gz.kill()
            return 3
        time.sleep(0.1)
    emit({"ev": "backend_ready", "sim_time_ns": backend.now_ns()})

    px4_env = dict(env)
    px4_env.update({
        "PX4_SYS_AUTOSTART": str(cfg["airframe"]),
        "PX4_SIM_MODEL": "gz_x500",
        "PX4_GZ_STANDALONE": "1",
        "PX4_GZ_MODEL": cfg["model"],
        "PX4_GZ_WORLD": world,
        "PX4_GZ_MODEL_POSE": cfg["spawn_pose"],
        "HOME": str(workdir),
    })
    px4 = subprocess.Popen(
        [PX4_BIN, PX4_ETC, "-s", "etc/init.d-posix/rcS", "-i", "0", "-d",
         "-w", str(workdir)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=px4_env,
        cwd=str(workdir))
    px4_lines = []
    threading.Thread(target=_drain, args=(px4.stdout, px4_lines),
                     daemon=True).start()

    backend.model_name = cfg["model"] + "_0"
    emit({"ev": "px4_started", "model": backend.model_name})

    driver = Driver(timeouts)
    result = {"ok": False, "cause": None}
    samples = []
    try:
        if not driver.connect(timeouts["launch_s"]):
            result["cause"] = {"code": "mavlink_no_heartbeat"}
            raise SystemExit
        if not driver.wait_ready(timeouts["estimator_s"]):
            result["cause"] = {"code": "estimator_not_ready"}
            raise SystemExit

        base_alt = driver.global_alt_m()
        if base_alt is None:
            result["cause"] = {"code": "no_global_position"}
            raise SystemExit
        # The reference is a height above the ground the body is standing
        # on, and the ground is observed, not assumed: the resting pose
        # comes from the backend before anything is armed.
        rest, _, _ = backend.snapshot()
        if rest is None:
            result["cause"] = {"code": "no_resting_pose"}
            raise SystemExit
        rest_z = rest[3]
        if not driver.set_param("MIS_TAKEOFF_ALT",
                                stages["takeoff_alt_mm"] / 1000.0,
                                mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
            result["cause"] = {"code": "takeoff_alt_not_set"}
            raise SystemExit

        stage_marks = {"rest_z_um": _um(rest_z), "base_amsl_um": _um(base_alt)}
        sim_start = backend.now_ns()
        stage_marks["start_ns"] = sim_start

        if not driver.takeoff(timeouts["takeoff_s"]):
            result["cause"] = {"code": "takeoff_mode_rejected"}
            raise SystemExit
        if not driver.arm(timeouts["arm_s"]):
            result["cause"] = {"code": "arm_failed"}
            raise SystemExit
        stage_marks["armed_ns"] = backend.now_ns()
        stage_marks["takeoff_ns"] = backend.now_ns()

        # From here the schedule is written in simulation time, so a slow
        # host cannot shorten a stage.
        plan = []
        cursor = stage_marks["takeoff_ns"]
        for name, key in (("climb", "takeoff_hold_ms"),
                          ("stabilize", "stabilize_ms"),
                          ("hover", "hover_ms"),
                          ("disturb", "disturb_ms"),
                          ("recover", "recover_ms")):
            span = int(stages[key]) * 1_000_000
            plan.append((name, cursor, cursor + span))
            cursor += span
        stage_marks["plan"] = [[n, a, b] for n, a, b in plan]

        wrench_published = 0
        force_n = [0.0, 0.0, 0.0]
        if condition == "perturbed":
            axis = disturb["axis"]
            magnitude = disturb["force_mn"] / 1000.0
            force_n = [magnitude * axis[0], magnitude * axis[1], magnitude * axis[2]]

        last_sample = 0.0
        active_wrench = False
        for name, begin_ns, end_ns in plan:
            emit({"ev": "stage", "stage": name, "begin_ns": begin_ns,
                  "end_ns": end_ns, "sim_time_ns": backend.now_ns()})
            while backend.now_ns() < end_ns:
                now = time.monotonic()
                if now - last_sample >= sample_dt:
                    last_sample = now
                    body, sim_ns, seen = backend.snapshot()
                    if body is not None:
                        samples.append([
                            sim_ns, _um(body[1]), _um(body[2]), _um(body[3]),
                            _mdeg(body[4]), _mdeg(body[5]), _mdeg(body[6]),
                            1 if active_wrench else 0,
                        ])
                    driver.drain()
                if (name == "disturb" and condition == "perturbed"
                        and not active_wrench):
                    # Exactly once. /wrench/persistent *adds* a wrench per
                    # message, so republishing it in the sample loop sums
                    # into kilonewtons and throws the body across the room.
                    if backend.apply_wrench(disturb["link"], force_n):
                        wrench_published += 1
                        active_wrench = True
                        emit({"ev": "wrench_applied", "force_n": force_n,
                              "sim_time_ns": backend.now_ns()})
                if px4.poll() is not None:
                    result["cause"] = {"code": "px4_exited",
                                       "detail": "".join(px4_lines[-5:])[:300]}
                    raise SystemExit
                time.sleep(0.002)
            if name == "disturb" and condition == "perturbed":
                backend.clear_wrench(disturb["link"])
                active_wrench = False
                emit({"ev": "wrench_cleared", "published": wrench_published,
                      "sim_time_ns": backend.now_ns()})

        stage_marks["recovered_ns"] = backend.now_ns()

        # ---- mover: the world moves, the body watches
        mover = cfg.get("mover")
        steps = []
        if mover:
            emit({"ev": "stage", "stage": "move", "begin_ns": backend.now_ns(),
                  "end_ns": 0, "sim_time_ns": backend.now_ns()})
            name = mover["model"]
            home = backend.model_pose(name)
            if home is None:
                result["cause"] = {"code": "mover_not_found", "detail": name}
                raise SystemExit
            vx = mover["velocity_mm_s"][0] / 1000.0
            vy = mover["velocity_mm_s"][1] / 1000.0
            step_ns = int(mover["step_ms"]) * 1_000_000
            span_ns = int(mover["duration_ms"]) * 1_000_000
            begin_ns = backend.now_ns()
            while True:
                now = backend.now_ns()
                dt = now - begin_ns
                if dt > span_ns:
                    break
                want = (home[0] + vx * dt / 1e9, home[1] + vy * dt / 1e9, home[2])
                moved = backend.move_model(name, *want)
                deadline = now + step_ns
                while backend.now_ns() < deadline:
                    t = time.monotonic()
                    if t - last_sample >= sample_dt:
                        last_sample = t
                        body, sim_ns, _ = backend.snapshot()
                        if body is not None:
                            samples.append([
                                sim_ns, _um(body[1]), _um(body[2]), _um(body[3]),
                                _mdeg(body[4]), _mdeg(body[5]), _mdeg(body[6]), 0,
                            ])
                        driver.drain()
                    if px4.poll() is not None:
                        result["cause"] = {"code": "px4_exited",
                                           "detail": "".join(px4_lines[-5:])[:300]}
                        raise SystemExit
                    time.sleep(0.002)
                seen = backend.model_pose(name)
                steps.append({"sim_time_ns": now, "asked_mm": [_um(v) // 1000 for v in want],
                              "seen_mm": [_um(v) // 1000 for v in seen] if seen else None,
                              "commanded": bool(moved)})
            stage_marks["mover"] = {"model": name, "home_mm": [_um(v) // 1000 for v in home],
                                    "velocity_mm_s": list(mover["velocity_mm_s"]),
                                    "begin_ns": begin_ns, "end_ns": backend.now_ns(),
                                    "steps": steps}
            emit({"ev": "mover_done", "steps": len(steps), "sim_time_ns": backend.now_ns()})

        if not driver.land(timeouts["land_s"]):
            result["cause"] = {"code": "land_rejected"}
            raise SystemExit
        land_deadline = backend.now_ns() + int(timeouts["land_s"]) * 1_000_000_000
        while backend.now_ns() < land_deadline:
            now = time.monotonic()
            if now - last_sample >= sample_dt:
                last_sample = now
                body, sim_ns, _ = backend.snapshot()
                if body is not None:
                    samples.append([sim_ns, _um(body[1]), _um(body[2]), _um(body[3]),
                                    _mdeg(body[4]), _mdeg(body[5]), _mdeg(body[6]), 0])
            if driver.conn.recv_match(type="HEARTBEAT", blocking=False) is not None:
                pass
            hb = driver.conn.messages.get("HEARTBEAT")
            if hb is not None and not (hb.base_mode
                                       & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED):
                break
            time.sleep(0.01)
        stage_marks["landed_ns"] = backend.now_ns()
        driver.wait_disarm(timeouts["land_s"])
        stage_marks["disarmed_ns"] = backend.now_ns()
        result["ok"] = True
    except SystemExit:
        pass
    except Exception as exc:  # noqa: BLE001
        result["cause"] = {"code": "runner_exception", "detail": repr(exc)[:300]}
    finally:
        try:
            backend.clear_wrench(disturb["link"])
        except Exception:  # noqa: BLE001
            pass
        ulog = _latest_ulog(workdir)
        emit({
            "ev": "episode",
            "ok": result["ok"],
            "cause": result["cause"],
            "condition": condition,
            "stage_marks": locals().get("stage_marks", {}),
            "samples": samples,
            "sample_columns": ["sim_time_ns", "x_um", "y_um", "z_um",
                               "roll_mdeg", "pitch_mdeg", "yaw_mdeg", "wrench"],
            "wrench_published": locals().get("wrench_published", 0),
            "force_n": locals().get("force_n", [0.0, 0.0, 0.0]),
            "body_pose_updates": backend.body_seen,
            "clock_samples": backend.clock_samples,
            "driver_events": driver.events,
            "px4_tail": px4_lines[-40:],
            "ulog": str(ulog) if ulog else None,
            "final_sim_time_ns": backend.now_ns(),
        })
        px4.terminate()
        try:
            px4.wait(timeout=15)
        except subprocess.TimeoutExpired:
            px4.kill()
        gz.terminate()
        try:
            gz.wait(timeout=15)
        except subprocess.TimeoutExpired:
            gz.kill()
    return 0 if result["ok"] else 1


def _drain(stream, sink):
    for line in iter(stream.readline, b""):
        sink.append(line.decode("utf-8", "replace"))


def _latest_ulog(workdir):
    logs = sorted(Path(workdir).glob("log/**/*.ulg"))
    return logs[-1] if logs else None


if __name__ == "__main__":
    sys.exit(main())
