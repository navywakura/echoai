"""Fresh, bounded Gazebo/PX4 campaigns using the existing local image.

Importing this module launches nothing. Only run_sitl_campaign launches a
container. No external endpoint, host device, historical lock or replay input
is accepted. A software report can never satisfy this module's receipt gate.
"""

from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time
import uuid

from .legacy import ROOT as LEGACY_ROOT, module
from .distribution import CORE_FILES
from .mission import MODES, digest, goal_request, summarize, synthetic_models, validate_raw
from .mission_reasoning import OUTCOME_SCHEMA, audit_reasoning, audit_information, validate_outcome
from .sitl_truth import audit_pose_stream
from .sitl_parameters import (audit_parameters, validate_parameters,
                              reconcile_parameter_evidence, require_parameter_manifest)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config/mission.json"
IMAGE_ID = "5364c865ebf08b1dd19ee7a6a46ca3c3911056269974e7d9db2ced4a74201d27"
CONDITIONS = ("static", "contradiction", "low_energy", "sensor_stale", "agent_hang", "static")
PX4_BINARY = "/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4"
MAX_LINE = 2_000_000
MAX_EPISODE_BYTES = 512*1024*1024
RUNNER_MODULES = (
    "constants.py", "gate.py", "fusion1/core.py", "fusion1/integration.py",
    "compose1_v3/perception.py", "cause1/core.py", "px41/core.py", "power1/core.py",
    "safe1/core.py", "safe1/service.py", "transfer3/calib_c1.py", "drone3/__init__.py",
    "drone3/contract.py", "drone3/calibration.py", "drone3/energy.py", "drone3/gates.py",
    "drone3/gateway.py", "drone3/supervisor.py", "drone3/probes.py")
ASSETS = {
    "legacy_runner.py": "nexus0/drone3/assets/runner.py",
    "live_runner.py": "nexus0/compose1_v3/assets/live_runner.py",
    "flightrunner_survey.py": "nexus0/pattern1r_v4/assets/flightrunner_survey.py"}
ACTOR_MODULES = ("types.py", "qtable.py", "world.py", "compose1/controller.py",
                 "compose1/model.py", "compose1_v2/controller.py", "compose1_v3/controller.py",
                 "drone3/agent.py")


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def _save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def _load(path):
    return json.loads(Path(path).read_text())


def _command(argv, timeout=10):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=timeout, check=False)


def availability():
    """Read-only metadata; does not run even a probe container or simulator."""
    podman = shutil.which("podman")
    out = dict(schema="echo5.sitl.availability.v1", checked_utc=datetime.now(timezone.utc).isoformat(),
               podman=podman, image_id=None, host_gz=shutil.which("gz"),
               host_px4=shutil.which("px4"), blockers=[], runtime_probed=False,
               host_px4_candidate=shutil.which("px4"))
    if not podman:
        out["blockers"].append("podman is not on PATH")
        return out
    try:
        result = _command([podman, "image", "inspect", IMAGE_ID, "--format", "{{.Id}}"])
        if result.returncode or result.stdout.strip().removeprefix("sha256:") != IMAGE_ID:
            out["blockers"].append("pinned local image unavailable: "+result.stderr.strip()[:400])
        else:
            out["image_id"] = IMAGE_ID
        version = _command([podman, "--version"])
        out["podman_version"] = version.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        out["blockers"].append(type(exc).__name__+": "+str(exc))
    for path in [*ASSETS.values(), *CORE_FILES, *("nexus0/"+p for p in RUNNER_MODULES+ACTOR_MODULES)]:
        if not (LEGACY_ROOT/path).is_file():
            out["blockers"].append("missing runtime source "+path)
    out["ready_to_attempt"] = not out["blockers"]
    return out


def _config(config):
    allowed = {"output", "seed", "cases", "phase", "budget", "max_decisions",
               "episode_timeout_s", "campaign_timeout_s"}
    if type(config) is not dict or not set(config) <= allowed or "output" not in config:
        raise ValueError("sitl_config: output required; no executable, host, port or backend overrides")
    protocol = _load(CONTRACT)['sitl']
    phase = config.get('phase', 'development')
    if phase not in ('development', 'confirmation'):
        raise ValueError('sitl_phase')
    cfg = dict(seed=protocol[phase + '_seed'], cases=6, phase=phase, budget=20_000_000, max_decisions=64,
               episode_timeout_s=900, campaign_timeout_s=18000)
    cfg.update(config)
    limits = {"seed": (1, 2**31-1), "cases": (1, 12), "budget": (1, 100_000_000),
              "max_decisions": (1, 64), "episode_timeout_s": (60, 900),
              "campaign_timeout_s": (60, 18000)}
    for key, (low, high) in limits.items():
        if type(cfg[key]) is not int or not low <= cfg[key] <= high:
            raise ValueError("sitl_config_bounds:"+key)
    if cfg["phase"] not in ("development", "confirmation"):
        raise ValueError("sitl_phase")
    intervals = [protocol['reserved_confirmation_interval'],
                 *protocol.get('retired_confirmation_intervals', [])]
    for interval in intervals:
        if (type(interval) is not list or len(interval) != 2
                or any(type(n) is not int for n in interval)
                or not 1 <= interval[0] <= interval[1] <= 2**31 - 1):
            raise ValueError('invalid_confirmation_seed_interval')
        if cfg['phase'] == 'development' and cfg['seed'] <= interval[1] and cfg['seed']+cfg['cases']-1 >= interval[0]:
            raise ValueError('reserved_confirmation_seed_interval')
    if protocol['reserved_confirmation_interval'] != [protocol['confirmation_seed'],
                                                       protocol['confirmation_seed'] + protocol['cases'] - 1]:
        raise ValueError('confirmation_seed_contract_mismatch')
    if cfg["phase"] == "confirmation" and any(cfg[k] != v for k, v in {
            "seed": protocol['confirmation_seed'], "cases": 6, "budget": 20_000_000, "max_decisions": 64,
            "episode_timeout_s": 900, "campaign_timeout_s": 18000}.items()):
        raise ValueError("sitl_confirmation_contract")
    output = Path(cfg["output"]).expanduser().resolve()
    if not output.is_relative_to((ROOT/"artifacts").resolve()) or output == (ROOT/"artifacts").resolve():
        raise ValueError("new output directory must be inside simulation/artifacts")
    cfg["output"] = str(output)
    return cfg


# A new launcher envelope stages the frozen runtime and an explicit, hashed
# exception-recovery adaptation. Its evidence records
# actual OS process identity and ULog contents; it does not invent telemetry.
BOOTSTRAP = r'''
import hashlib, importlib.metadata, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path
sys.path.insert(0, '/flight')
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()
def save(name, value):
    with open('/out/'+name, 'x') as f: json.dump(value, f, sort_keys=True)
px4 = '/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4'
identity = dict(nonce=os.environ['ECHO5_RUN_NONCE'], pid=os.getpid(), started_ns=time.time_ns(),
                image_id=os.environ['ECHO5_IMAGE_ID'], python=sys.version,
                px4_binary_sha256=sha(px4), gz=shutil.which('gz'), packages={})
for package in ('pymavlink', 'pyulog', 'numpy'):
    identity['packages'][package] = importlib.metadata.version(package)
identity['gz_version'] = subprocess.run(['gz', 'sim', '--version'], capture_output=True, text=True, timeout=10).stdout.strip()
save('runtime-identity.json', identity)
import flightrunner_survey as flight
from sitl_parameters import configure_driver
save('px4-parameter-adapter.json', configure_driver(
    flight.ConfiguredDriver, json.loads(os.environ['FLIGHT1S_PARAMETERS'])))
from sitl_truth import PoseRecorder, instrument_backend
poses = PoseRecorder(Path('/out'), os.environ['ECHO5_RUN_NONCE'])
flight.Backend = instrument_backend(flight.Backend, poses)
finished = threading.Event()
def observe_processes():
    seen = set()
    with open('/out/processes.jsonl', 'x', buffering=1) as log:
        while not finished.wait(.2):
            for p in Path('/proc').iterdir():
                if not p.name.isdigit(): continue
                try:
                    cmd = (p/'cmdline').read_bytes().replace(b'\x00', b' ').decode(errors='replace')
                    if p.name in seen or not ('/px4 ' in cmd or 'gz sim' in cmd or 'gz-sim' in cmd): continue
                    exe = str((p/'exe').resolve())
                    log.write(json.dumps(dict(pid=int(p.name), cmd=cmd, exe=exe, time_ns=time.time_ns()))+'\n')
                    seen.add(p.name)
                except OSError: pass
t = threading.Thread(target=observe_processes, daemon=True); t.start()
code = 1
try:
    from sitl_recovery import adapt_runner_source
    runner_path = '/flight/legacy_runner.py'
    adapted = adapt_runner_source(Path(runner_path).read_text())
    save('runner-adaptation.json', dict(schema='echo5.sitl.runner-adaptation.v1',
        nonce=os.environ['ECHO5_RUN_NONCE'], original_sha256=sha(runner_path),
        adapter_sha256=sha('/flight/sitl_recovery.py'),
        effective_sha256=hashlib.sha256(adapted.encode()).hexdigest(),
        scope='passive exceptional recovery and post-flight logger shutdown; original errors remain failures'))
    sys.argv[0] = runner_path
    exec(compile(adapted, runner_path, 'exec'),
         dict(__name__='__main__', __file__=runner_path, __package__=None))
except SystemExit as exc:
    code = int(exc.code or 0)
finally:
    finished.set(); t.join(2)
    poses.close()
    try:
        from pyulog import ULog
        files = sorted(Path('/out').rglob('*.ulg'))
        if len(files) != 1: raise RuntimeError('exactly one complete PX4 ULog required')
        path = files[0]
        names = ['vehicle_local_position', 'vehicle_status', 'vehicle_land_detected', 'battery_status']
        log = ULog(str(path), message_name_filter_list=names)
        from sitl_parameters import extract_ulog_parameters
        save('ulog-parameters.json', extract_ulog_parameters(
            path, os.environ['ECHO5_RUN_NONCE'], str(path.relative_to('/out'))))
        datasets = {}
        for data in log.data_list:
            fields = {'vehicle_local_position':['timestamp','x','y','z','vx','vy','vz'],
                      'vehicle_status':['timestamp','arming_state','nav_state','failsafe'],
                      'vehicle_land_detected':['timestamp','landed'],
                      'battery_status':['timestamp','voltage_v','remaining']}[data.name]
            # Preserve all samples for independent binding, no average-only receipt.
            datasets[data.name] = {k:data.data[k].tolist() for k in fields if k in data.data}
        save('ulog-evidence.json', dict(file=str(path.relative_to('/out')), sha256=sha(path),
             start_timestamp=log.start_timestamp, last_timestamp=log.last_timestamp, datasets=datasets))
    except Exception as exc:
        save('ulog-error.json', dict(error=repr(exc)))
sys.exit(code)
'''


def _prepare(root, cfg, case, mode, nonce):
    """Generate new assets; no historical lock/config/data file is read."""
    root.mkdir()
    (root/"out").mkdir()
    condition = CONDITIONS[case % len(CONDITIONS)]
    space_module = module("nexus0.compose1_v3.space")
    space = space_module.Space(cfg["seed"]+case, "dynamic" if condition == "contradiction" else "static")
    source = space_module.source_sdf(space)
    effective = module("nexus0.flight1s.worldbuild").build_effective(source, hashlib.sha256(source).hexdigest()).data
    effective = effective.replace(b"  </world>", b'    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>\n  </world>')
    (root/"source.sdf").write_bytes(source)
    (root/"world.sdf").write_bytes(effective)
    for name, text in module("nexus0.compose1_v3.rig").models().items():
        path = root/"models"/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    imported = {}
    paths = dict(ASSETS)
    paths.update({"echoai/nexus0/"+name: "nexus0/"+name for name in RUNNER_MODULES})
    paths.update({"echoai/"+name: name for name in ("__init__.py", *CORE_FILES)})
    for dest, src in paths.items():
        path = root/dest
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LEGACY_ROOT/src, path)
        imported[src] = _sha(path)
    for name in ACTOR_MODULES:
        imported["nexus0/"+name] = _sha(LEGACY_ROOT/"nexus0"/name)
    for name in ("seed/relational_dsl.py", "seed/dsl.py", "seed/refinement.py"):
        imported[name] = _sha(LEGACY_ROOT/name)
    (root/"runner.py").write_text(BOOTSTRAP)
    shutil.copyfile(ROOT/"src/echo5/sitl_truth.py", root/"sitl_truth.py")
    shutil.copyfile(ROOT/"src/echo5/sitl_parameters.py", root/"sitl_parameters.py")
    shutil.copyfile(ROOT/"src/echo5/sitl_recovery.py", root/"sitl_recovery.py")
    _, power = synthetic_models()
    contract = _load(CONTRACT)
    fault = {"kind": "lidar_stale" if condition == "sensor_stale" else "agent_hang", "after_moves": 1}
    intervention = None
    if condition == "contradiction":
        source_cell = space.rotate((space.wall_x, -space.gap_y, 0))
        target_cell = space.rotate((space.wall_x, space.gap_y, 0))
        intervention = dict(entity="barrier_"+str(sorted(space.solids).index(source_cell)),
                            source=[source_cell[0]*3, source_cell[1]*3, 2],
                            target=[target_cell[0]*3, target_cell[1]*3, 2],
                            trigger="first_admitted_from_home_side",
                            home_side=sorted(list(space.rotate((x, y, 0))[:2]) for x in range(space.wall_x) for y in range(-2, 3)))
    runner = dict(seed=cfg["seed"]+case, condition=condition, physics_seed=cfg["seed"]+case+1_000_000,
                  timeouts=dict(launch_s=30, estimator_s=45, arm_s=10, takeoff_s=30, land_s=35,
                                episode_s=cfg["episode_timeout_s"]-20),
                  battery=contract["sitl"]["battery"], power_model=power, offset=[0, 0],
                  handover_remaining=150 if condition == "low_energy" else None,
                  fault=fault if condition in ("sensor_stale", "agent_hang") else None,
                  world_intervention=intervention)
    goal = goal_request(space.goal, goal_id=f"sitl-{case:04d}", max_decisions=cfg["max_decisions"])
    init = dict(goal=goal, budget=cfg["budget"], mode=mode)
    geometry = dict(solids=[list(p) for p in sorted(space.solids)], goal=list(space.goal),
                    home=list(space.start), intervention=intervention)
    _save(root/"configuration.json", dict(runner=runner, agent=init, geometry=geometry,
                                         nonce=nonce, mode=mode, imported_sources=imported,
                                         instrumentation_sources={
                                             "src/echo5/sitl_truth.py": _sha(root/"sitl_truth.py"),
                                             "src/echo5/sitl_parameters.py": _sha(root/"sitl_parameters.py"),
                                             "src/echo5/sitl_recovery.py": _sha(root/"sitl_recovery.py")},
                                         px4_parameters=validate_parameters(contract["sitl"]["px4_parameters"]),
                                         condition=condition, image_id=IMAGE_ID))
    immutable = {str(p.relative_to(root)): _sha(p) for p in sorted(root.rglob("*")) if p.is_file()}
    _save(root/"input-manifest.json", immutable)
    return runner, init


def launch_argv(podman, root, runner, nonce):
    """No configurable shell/executable/address; all ports stay in netns."""
    parameters = validate_parameters(_load(CONTRACT)["sitl"]["px4_parameters"])
    return [podman, "run", "--name", "echo5-sitl-"+nonce, "--cidfile", str(root/"container.cid"),
            "--timeout", str(runner["timeouts"]["episode_s"]+20),
            "--pull=never", "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--security-opt=label=disable",
            "--cpus=4", "--memory=4096m", "--pids-limit=512", "--shm-size=256m",
            "--tmpfs", "/tmp:rw,exec,size=1024m", "--tmpfs", "/run:rw,size=64m", "-i",
            "-e", "HOME=/out/wd", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "GZ_PARTITION=echo5-"+nonce, "-e", "GZ_IP=127.0.0.1",
            "-e", "GZ_FUEL_STATIC_ONLY=1", "-e", "LIBGL_ALWAYS_SOFTWARE=1",
            "-e", "GALLIUM_DRIVER=llvmpipe", "-e", "LP_NUM_THREADS=2",
            "-e", "FLIGHT1S_HEARTBEAT_S=30", "-e", "ECHO5_RUN_NONCE="+nonce,
            "-e", "ECHO5_IMAGE_ID="+IMAGE_ID,
            "-e", "FLIGHT1S_PARAMETERS="+json.dumps(parameters, sort_keys=True),
            "-v", f"{root}:/flight:ro", "-v", f"{root/'out'}:/out:rw",
            IMAGE_ID, "python3", "-B", "/flight/runner.py", json.dumps(runner, sort_keys=True)]


class _Lines:
    """Bounded binary pipe reader: no TextIO buffering or blocking readline."""
    def __init__(self, pipe):
        self.pipe, self.buffer, self.lines = pipe, b"", []
        os.set_blocking(pipe.fileno(), False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(pipe, selectors.EVENT_READ)

    def next(self, timeout):
        if self.lines:
            return self.lines.pop(0)
        if not self.selector.select(max(0, timeout)):
            return None
        chunk = os.read(self.pipe.fileno(), 65536)
        if not chunk:
            raise EOFError("external process closed stdout")
        self.buffer += chunk
        if len(self.buffer) > MAX_LINE:
            raise ValueError("external line exceeds limit")
        parts = self.buffer.split(b"\n")
        self.buffer = parts.pop()
        self.lines.extend(parts)
        return self.lines.pop(0) if self.lines else None

    def close(self):
        self.selector.close()


def _send(process, value, timeout=1.0):
    data = json.dumps(value, sort_keys=True, allow_nan=False).encode()+b"\n"
    if len(data) > MAX_LINE:
        raise ValueError("outgoing line exceeds limit")
    deadline = time.monotonic()+timeout
    os.set_blocking(process.stdin.fileno(), False)
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdin, selectors.EVENT_WRITE)
        while data:
            remaining = deadline-time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("bounded input pipe write")
            try:
                count = os.write(process.stdin.fileno(), data[:65536])
            except BlockingIOError:
                continue
            data = data[count:]


def _kill_owned(process):
    if process is None or process.poll() is not None:
        return
    # Only process groups created by this invocation, never names or port scans.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=1)
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=1)


def _inspect(podman, cid):
    result = _command([podman, "inspect", cid], timeout=2)
    if result.returncode:
        raise RuntimeError("container inspect: "+result.stderr[:300])
    value = json.loads(result.stdout)[0]
    host = value["HostConfig"]
    return dict(id=value["Id"], image=value["Image"].removeprefix("sha256:"),
                state=value["State"], network=host.get("NetworkMode"),
                privileged=host.get("Privileged"), devices=host.get("Devices"),
                port_bindings=host.get("PortBindings"), mounts=value.get("Mounts", []))


PUBLIC_OUTCOMES_SCHEMA = "echo5.sitl.public-outcomes.v1"


class _CommandEvidence:
    """Bind public commands to sends, ACKs and distinct completion samples.

    This checks ledger structure, not flight truth or policy correctness. The
    external auditor additionally recomputes the original SAFE/POWER gateway.
    At most one command can be in flight; an ACK has no transaction id.
    """
    def __init__(self, responses=None):
        self.responses, self.commands, self.completed = {}, {}, {}
        self.active = None
        self.last_mono = -1
        self.vetoed = False
        for epoch, response in (responses or {}).items():
            self.register(epoch, response)

    @staticmethod
    def require(ok, reason):
        if not ok:
            raise ValueError("public_command:"+reason)

    def register(self, epoch, response):
        self.require(type(epoch) is int and 0 <= epoch < 160, "epoch")
        self.require(epoch not in self.responses or self.responses[epoch] == response, "duplicate_response")
        self.responses[epoch] = deepcopy(response)

    def feed(self, event):
        kind = event["kind"]
        if kind not in ("proposal", "send", "ack", "check", "arrival", "stale_decision", "veto"):
            return
        self.require(type(event["now_ns"]) is int and event["now_ns"] >= 0
                     and type(event["mono_ns"]) is int and event["mono_ns"] >= max(0, self.last_mono), "event_order")
        self.last_mono = event["mono_ns"]
        if kind == "veto":
            self.vetoed = True
            return
        if kind == "check":
            if self.active is None:
                return
            command = self.commands[self.active]
            command["check"] = event
            if command.get("ack") is None or event["ok"] is not True:
                return
            frame = event["health"]["frame"]
            stamp = frame["received_ns"]
            self.require(type(stamp) is int and 0 <= stamp <= event["now_ns"]
                         and type(event["samples"]) is int, "sample_clock_and_count")
            if command["samples"] < 3 and stamp > command["last_sample"]:
                command["last_sample"] = stamp
                target = command["proposal"]["decision"]["target_mm"]
                settled = (frame["armed"] is True and frame["authority"] is True and frame["failsafe"] is False
                           and type(frame["speed_mm_s"]) is int and 0 <= frame["speed_mm_s"] <= 150
                           and len(frame["position_mm"]) == 3
                           and sum((a-b)**2 for a,b in zip(frame["position_mm"], target)) <= 350**2)
                command["samples"] = command["samples"]+1 if settled else 0
            self.require(event["samples"] == command["samples"], "distinct_settled_samples")
            self.require(event["state"] == ("complete" if command["samples"] >= 3 else "executing"), "completion_state")
            return
        if kind == "send":
            seq = event["seq"]
            self.require(type(seq) is int and seq > 0, "send_sequence")
            epoch = seq-1
        else:
            epoch = event["epoch"]
        self.require(type(epoch) is int and epoch in self.responses, "response_missing")
        response = self.responses[epoch]
        self.require(epoch not in self.completed, "duplicate_or_post_completion_event")
        if kind == "proposal":
            self.require(epoch not in self.commands and self.active is None and not self.vetoed, "proposal_order")
            request, decision = event["request"], event["decision"]
            self.require(type(request["seq"]) is int and request["seq"] == epoch+1
                         and request["wsp"] == response["wsp"] and request["prediction"] == response["prediction"]
                         and request["published_ns"] == response["observation_ns"], "proposal_binding")
            self.require(type(decision["allowed"]) is bool, "approval")
            self.commands[epoch] = dict(proposal=event, samples=0)
            if decision["allowed"]:
                target = [response["prediction"][0]*3000, response["prediction"][1]*3000, 2500]
                self.require(decision["target_mm"] == target, "approved_target")
                self.active = epoch
            return
        if kind == "stale_decision":
            self.require(epoch not in self.commands and self.active is None and not self.vetoed, "stale_after_execution")
            outcome = self._base(response)
            outcome.update(disposition="not_executed", command_seq=None, ack=None, samples=0,
                           estimate=None, reason=event["reason"])
            self.completed[epoch] = validate_outcome(outcome, response)
            return
        self.require(self.active == epoch and not self.vetoed, "active_command")
        command = self.commands[epoch]
        proposal = command["proposal"]
        if kind == "send":
            self.require("send" not in command and proposal["decision"]["allowed"] is True, "unique_approved_send")
            self.require(event["target_mm"] == proposal["decision"]["target_mm"]
                         and event["yaw_mrad"] == proposal["decision"]["yaw_mrad"]
                         and event["mono_ns"] > proposal["mono_ns"] and event["now_ns"] >= proposal["now_ns"], "send_binding")
            command["send"] = event
            return
        self.require("send" in command, "missing_send")
        sent = command["send"]
        if kind == "ack":
            self.require(type(event["accepted"]) is bool and event["mono_ns"] > sent["mono_ns"], "ack_order")
            if not event["accepted"]:
                return
            ack = event["ack"]
            self.require("ack" not in command and set(ack) == {"system", "component", "command", "result", "received_ns"}
                         and all(type(v) is int for v in ack.values())
                         and (ack["system"], ack["component"], ack["command"], ack["result"]) == (1,1,192,0)
                         and sent["now_ns"] < ack["received_ns"] <= event["now_ns"]
                         and event["now_ns"]-proposal["now_ns"] <= 2_000_000_000, "matching_ack")
            command.update(ack=event, last_sample=ack["received_ns"])
            return
        ack, sample = command.get("ack"), command.get("check")
        self.require(ack is not None and sample is not None and sample["ok"] is True
                     and sample["state"] == "complete" and command["samples"] >= 3
                     and event["samples"] == sample["samples"] == command["samples"]
                     and ack["mono_ns"] < sample["mono_ns"] < event["mono_ns"]
                     and event["target_mm"] == sent["target_mm"] == proposal["decision"]["target_mm"], "arrival_binding")
        outcome = self._base(response)
        outcome.update(disposition="arrived", command_seq=proposal["request"]["seq"], ack=ack["ack"],
                       samples=event["samples"], reason="gateway_complete",
                       estimate={k:sample["health"]["frame"][k] for k in ("position_mm", "received_ns", "speed_mm_s")})
        self.completed[epoch] = validate_outcome(outcome, response)
        self.active = None

    @staticmethod
    def _base(response):
        return dict(schema=OUTCOME_SCHEMA, **{k:deepcopy(response[k]) for k in ("sequence", "raw_sha256", "wsp", "prediction")})

    def snapshot(self, deliveries):
        self.require(set(deliveries) <= set(self.completed), "delivery_without_outcome")
        completed, unresolved = [], []
        for epoch, outcome in sorted(self.completed.items()):
            reply = deliveries.get(epoch)
            self.require(reply is None or (type(reply) is int and reply > epoch), "delivery_order")
            completed.append(dict(epoch=epoch, outcome=deepcopy(outcome), reply_epoch=reply,
                                  actor_delivery="unconfirmed" if reply is None else "confirmed_by_reply"))
        for epoch, response in sorted(self.responses.items()):
            if epoch in self.completed or module("nexus0.drone3.contract").intention(response["wsp"])[0] == "stop":
                continue
            command = self.commands.get(epoch, {})
            stage = ("completion_unrecorded" if command.get("samples", 0) >= 3 else
                     "executing" if "ack" in command else "awaiting_ack" if "send" in command else
                     "awaiting_send" if command and command["proposal"]["decision"]["allowed"] else
                     "denied" if command else "awaiting_admission")
            unresolved.append(dict(epoch=epoch, sequence=response["sequence"], raw_sha256=response.get("raw_sha256"),
                                   wsp=response["wsp"], prediction=deepcopy(response["prediction"]), stage=stage,
                                   command_seq=command["proposal"]["request"]["seq"] if command else None,
                                   reason="episode_ended_before_completion"))
        return dict(schema=PUBLIC_OUTCOMES_SCHEMA, completed=completed, terminal_unresolved=unresolved)


class _PublicOutcomes:
    """Incremental public receipt extraction; never reads simulator truth.

    Retention is independent of actor delivery. A reply confirms that the
    existing worker consumed the previous outcome, not that it learned a fact.
    """
    def __init__(self, path):
        self.path, self.offset = Path(path), 0
        self.ledger, self.deliveries = _CommandEvidence(), {}

    def register(self, epoch, response):
        self.ledger.register(epoch, response)

    def _read(self, final=False):
        with self.path.open() as stream:
            stream.seek(self.offset)
            while True:
                offset = stream.tell()
                line = stream.readline(MAX_LINE+1)
                if len(line) > MAX_LINE:
                    raise ValueError("outcome_trace_line_limit")
                if not line or not line.endswith("\n"):
                    self.offset = offset
                    if line and final:
                        raise ValueError("incomplete_terminal_trace_line")
                    break
                self.ledger.feed(json.loads(line))
                self.offset = stream.tell()

    def take(self, epoch, response):
        self.register(epoch, response)
        try:
            self._read()
            return deepcopy(self.ledger.completed[epoch])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("missing_public_execution_outcome:"+str(exc)) from exc

    def delivered(self, epoch, reply_epoch):
        self.ledger.require(epoch in self.ledger.completed and epoch not in self.deliveries
                            and type(reply_epoch) is int and reply_epoch > epoch, "delivery_binding")
        self.deliveries[epoch] = reply_epoch

    def finish(self):
        self._read(final=True)
        return self.ledger.snapshot(self.deliveries)


def _audit_public_outcomes(retained, ledger, deliveries):
    """Require every completed/stale outcome and every terminal unresolved command."""
    if retained != ledger.snapshot(deliveries):
        raise ValueError("public_outcome_ledger_binding_or_completeness")
    if any(row["stage"] == "completion_unrecorded" for row in retained["terminal_unresolved"]):
        raise ValueError("completed_gateway_missing_arrival_record")
    return dict(consequence_receipts=len(ledger.completed), actor_consequences=len(deliveries),
                terminal_unresolved=len(retained["terminal_unresolved"]))


def _latency_evidence(receipt, transport):
    """Every attempted worker call ends in a reply or an explicit timeout.

    Injected hang skips the call entirely and keeps its existing fault judge.
    A condition label never excuses an actual attempted request timing out.
    """
    requests, results, latencies, durations = {}, {}, [], []
    timed_out = 0
    for row in transport:
        side = row["side"]
        if side not in ("worker_request", "agent", "worker_timeout"):
            continue
        epoch, sent = row["epoch"], row["sent_mono_ns"]
        if type(epoch) is not int or epoch < 0 or type(sent) is not int or sent < 0:
            raise ValueError("worker_request_identity")
        if side == "worker_request":
            if epoch in requests:
                raise ValueError("duplicate_worker_request")
            requests[epoch] = sent
            continue
        if epoch not in requests or requests[epoch] != sent or epoch in results:
            raise ValueError("worker_result_binding")
        duration = row["latency_ns"] if side == "agent" else row["elapsed_ns"]
        if type(duration) is not int or duration < 0:
            raise ValueError("worker_duration")
        results[epoch] = side
        durations.append(duration)
        if side == "agent":
            latencies.append(duration)
        else:
            timed_out += 1
    if (set(requests) != set(results) or receipt.get("latency_ns") != latencies
            or receipt.get("worker_timeout", False) is not bool(timed_out)):
        raise ValueError("worker_attempt_accounting")
    durations.sort()
    return dict(n=len(latencies), attempts=len(requests), timed_out=timed_out,
                p95_ns=durations[math.ceil(len(durations)*.95)-1] if durations else None,
                max_ns=max(durations) if durations else None, includes_timeout_lower_bounds=bool(timed_out),
                passed=bool(latencies) and not timed_out and max(latencies) <= 1_000_000_000)


def _run_episode(root, cfg, case, mode, podman, campaign_deadline, journal):
    nonce = uuid.uuid4().hex
    runner, init = _prepare(root, cfg, case, mode, nonce)
    argv = launch_argv(podman, root, runner, nonce)
    started_ns = time.time_ns()
    started = time.monotonic()
    receipt = dict(schema="echo5.sitl.process.v1", evidence="external_gazebo_px4", nonce=nonce,
                   launcher_pid=os.getpid(), external_pid=None, started_ns=started_ns,
                   argv=argv, image_id=IMAGE_ID, returncode=None, container=None,
                   teardown=False, error=None, protocol_result=None, latency_ns=[], agent_cost=0,
                   worker_timeout=False)
    process = worker = reader = worker_reader = None
    container_id = None
    frozen = False
    sequence = 0
    previous_response = previous_epoch = None
    public_outcomes = _PublicOutcomes(root/"out/trace.jsonl")
    files = []
    try:
        error = (root/"container.stderr").open("xb"); files.append(error)
        worker_error = (root/"agent.stderr").open("xb"); files.append(worker_error)
        transport = (root/"transport.jsonl").open("x", buffering=1); files.append(transport)
        worker = subprocess.Popen([sys.executable, "-I", "-B", str(ROOT/"scripts/run_sitl.py"), "agent-worker"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=worker_error, start_new_session=True)
        worker_reader = _Lines(worker.stdout)
        _send(worker, init)
        ready = None
        ready_deadline = time.monotonic()+20
        while ready is None and time.monotonic() < ready_deadline:
            ready = worker_reader.next(.2)
        if ready is None or json.loads(ready).get("ready") is not True:
            raise RuntimeError("mission worker not ready")
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=error, start_new_session=True)
        receipt["external_pid"] = process.pid
        reader = _Lines(process.stdout)
        deadline = min(started+cfg["episode_timeout_s"], campaign_deadline)
        size_check = time.monotonic()
        while time.monotonic() < deadline:
            line = reader.next(.2)
            if container_id is None and (root/"container.cid").exists():
                candidate = (root/"container.cid").read_text().strip()
                if re.fullmatch(r"[0-9a-f]{64}", candidate):
                    container_id = candidate
            if time.monotonic()-size_check > 3:
                size_check = time.monotonic()
                if sum(p.stat().st_size for p in (root/"out").rglob("*") if p.is_file()) > MAX_EPISODE_BYTES:
                    raise RuntimeError("episode artifact size limit")
            if line is None:
                continue
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            transport.write(json.dumps(dict(side="backend", received_mono_ns=time.monotonic_ns(), event=event), sort_keys=True)+"\n")
            if event.get("kind") == "observation":
                if frozen:
                    continue
                sent = time.monotonic_ns()
                outcome = (None if previous_response is None else
                           public_outcomes.take(previous_epoch, previous_response))
                transport.write(json.dumps(dict(side="worker_request", epoch=event["epoch"],
                                                sent_mono_ns=sent), sort_keys=True)+"\n")
                _send(worker, dict(raw=event["raw"], sequence=sequence, now_ns=event["raw"]["now_ns"], outcome=outcome))
                reply = None
                while reply is None and time.monotonic_ns()-sent < 1_000_000_000 and time.monotonic() < deadline:
                    reply = worker_reader.next(.02)
                if reply is None:
                    # Do not fabricate a response. SAFE detects the missing worker.
                    frozen = True
                    receipt["worker_timeout"] = True
                    transport.write(json.dumps(dict(side="worker_timeout", epoch=event["epoch"],
                                                    sent_mono_ns=sent, elapsed_ns=time.monotonic_ns()-sent),
                                               sort_keys=True)+"\n")
                    continue
                response = json.loads(reply)
                elapsed = time.monotonic_ns()-sent
                receipt["latency_ns"].append(elapsed)
                receipt["agent_cost"] = response["budget"]["used"]
                public_outcomes.register(event["epoch"], response)
                if outcome is not None:
                    public_outcomes.delivered(previous_epoch, event["epoch"])
                transport.write(json.dumps(dict(side="agent", epoch=event["epoch"], response=response,
                                                latency_ns=elapsed, sent_mono_ns=sent, outcome=outcome), sort_keys=True)+"\n")
                # Rejection before a reliable position cannot invent a target.
                if response["prediction"] is None:
                    frozen = True
                    continue
                _send(process, dict(wsp=response["wsp"], prediction=response["prediction"]))
                previous_response, previous_epoch = response, event["epoch"]
                if journal:
                    journal.write(kind="sitl_decision", case_id=init["goal"]["goal_id"], mode=mode,
                                  response=deepcopy(response), logic_latency_ns=elapsed)
                sequence += 1
            elif event.get("kind") == "inject":
                if event.get("fault") != "agent_hang":
                    raise ValueError("unexpected injection")
                frozen = True
                os.killpg(worker.pid, signal.SIGSTOP)
            elif event.get("kind") == "result":
                receipt["protocol_result"] = event
                process.wait(timeout=min(15, max(.1, deadline-time.monotonic())))
                break
        else:
            raise TimeoutError("bounded episode/campaign wall deadline")
    except (Exception, KeyboardInterrupt) as exc:
        receipt["error"] = type(exc).__name__+": "+str(exc)[:1000]
    finally:
        teardown_started = time.monotonic()
        if worker is not None and worker.poll() is None:
            try:
                os.killpg(worker.pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
        if container_id is None and (root/"container.cid").exists():
            candidate = (root/"container.cid").read_text().strip()
            if re.fullmatch(r"[0-9a-f]{64}", candidate):
                container_id = candidate
        try:
            if container_id:
                initial = _inspect(podman, container_id)
                if initial["state"].get("Running"):
                    _command([podman, "stop", "--time=5", container_id], timeout=6)
                receipt["container"] = _inspect(podman, container_id)
                removed = _command([podman, "rm", "--force", container_id], timeout=2)
                absent = _command([podman, "container", "exists", container_id], timeout=1)
                receipt["teardown"] = removed.returncode == 0 and absent.returncode == 1
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            receipt["teardown_error"] = repr(exc)
            if container_id:
                try:
                    _command([podman, "rm", "--force", container_id], timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        for owned in (worker, process):
            _kill_owned(owned)
            if owned is not None:
                for pipe in (owned.stdin, owned.stdout):
                    if pipe:
                        pipe.close()
        for lines in (reader, worker_reader):
            if lines:
                lines.close()
        # The runner is now stopped. Capture its final completed/stale outcome
        # even when an intentional hang prevented another worker request.
        # This file is an execution receipt, never input to an actor by itself.
        try:
            retained = public_outcomes.finish()
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            receipt["public_outcome_error"] = type(exc).__name__+": "+str(exc)[:500]
            try:
                retained = public_outcomes.ledger.snapshot(public_outcomes.deliveries)
            except (ValueError, KeyError, TypeError):
                retained = dict(schema=PUBLIC_OUTCOMES_SCHEMA, completed=[], terminal_unresolved=[])
            retained["error"] = receipt["public_outcome_error"]
        _save(root/"public-outcomes.json", retained)
        for stream in files:
            stream.close()
        receipt["returncode"] = None if process is None else process.returncode
        receipt["finished_ns"] = time.time_ns()
        receipt["wall_ns"] = time.monotonic_ns()-round(started*1e9)
        receipt["container_id"] = container_id
        receipt["teardown_wall_s"] = time.monotonic()-teardown_started
        receipt["teardown"] = receipt["teardown"] and receipt["teardown_wall_s"] <= 20
        _save(root/"process-receipt.json", receipt)
    row = evaluate_episode(root)
    _save(root/"row.json", row)
    evidence = {str(p.relative_to(root)): _sha(p) for p in sorted(root.rglob("*")) if p.is_file()}
    _save(root/"evidence-manifest.json", evidence)
    if journal:
        journal.write(kind="sitl_result", row=deepcopy(row))
    return row


def _lines(path):
    with Path(path).open() as stream:
        for line in stream:
            if len(line) > MAX_LINE:
                raise ValueError("oversize receipt")
            yield json.loads(line)


def _segment_box_distance(a, b, lo, hi):
    """Exact horizontal segment/AABB distance; evaluator geometry only."""
    enter, leave = 0.0, 1.0
    for k in range(2):
        delta = b[k]-a[k]
        if delta == 0:
            if not lo[k] <= a[k] <= hi[k]:
                enter, leave = 1.0, 0.0
                break
        else:
            first, last = sorted(((lo[k]-a[k])/delta, (hi[k]-a[k])/delta))
            enter, leave = max(enter, first), min(leave, last)
    if enter <= leave:
        return 0.0
    point = lambda p: math.hypot(*(max(lo[k]-p[k], 0, p[k]-hi[k]) for k in range(2)))
    best = min(point(a), point(b))
    length = sum((b[k]-a[k])**2 for k in range(2))
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            p = (x, y)
            t = min(1, max(0, sum((p[k]-a[k])*(b[k]-a[k]) for k in range(2))/length)) if length else 0
            best = min(best, math.hypot(*(p[k]-a[k]-t*(b[k]-a[k]) for k in range(2))))
    return best


def _blank_row(config):
    return dict(case_id=config["agent"]["goal"]["goal_id"], condition=config["condition"], mode=config["mode"],
                seed=config["runner"]["seed"], evidence="external_gazebo_px4", success=False,
                status="missing_external_receipt", valid_receipt=False, safety_success=False,
                collisions=None, reserve_violations=None, unsafe_commands=None, goal_observed=False,
                returned_home=False, disarmed=False, cost=0, final_reserve=None, logic_latency=None,
                findings=[], hardware_valid=False, reasoner_calls=0, reasoner_actions=0,
                reasoner_executed=0, consequence_receipts=0, actor_consequences=0, terminal_unresolved=0)


def _independent_parameters(path, nonce, relative_file):
    """Offline binary extraction only: no simulator, network, devices or writes."""
    name = 'echo5-ulog-' + uuid.uuid4().hex
    argv = [
        'podman', 'run', '--rm', '--name', name, '--timeout=45',
        '--pull=never', '--network=none', '--read-only',
        '--cap-drop=ALL', '--security-opt=no-new-privileges', '--security-opt=label=disable',
        '--cpus=1', '--memory=1536m', '--pids-limit=64',
        '-v', str(path)+':/input.ulg:ro',
        '-v', str(ROOT/'src/echo5/sitl_parameters.py')+':/extract.py:ro', IMAGE_ID,
        'python3', '-B', '/extract.py', '--file', '/input.ulg', '--nonce', nonce,
        '--relative-file', relative_file]
    try:
        result = _command(argv, timeout=60)
        if result.returncode:
            raise ValueError('independent ULog extraction failed: '+result.stderr[-800:])
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('independent ULog extraction failed: '+type(exc).__name__) from exc
    finally:
        try:
            removed = _command(['podman', 'rm', '--force', '--ignore', name], timeout=5)
            absent = _command(['podman', 'container', 'exists', name], timeout=5)
            if removed.returncode != 0 or absent.returncode != 1:
                raise ValueError('owned ULog extractor teardown failed')
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('owned ULog extractor teardown failed: '+type(exc).__name__) from exc


def _logger_shutdown_valid(trace, result):
    """Reconcile post-disarm shutdown evidence with the final runner receipt."""
    stops = [(i, r) for i, r in enumerate(trace) if r.get('kind') == 'logger_shutdown']
    disarms = [(i, r) for i, r in enumerate(trace) if r.get('kind') == 'disarmed']
    if len(stops) != 1 or not disarms or result.get('disarmed') is not True:
        return False
    i, stop = stops[0]
    j, disarm = disarms[-1]
    payload = {k: v for k, v in stop.items() if k not in ('kind', 'now_ns', 'mono_ns')}
    if (payload != result.get('logger_shutdown') or payload.get('complete') is not True
            or type(payload.get('returncode')) is not int or payload['returncode'] != 0
            or payload.get('schema') != 'echo5.sitl.logger-shutdown.v1'
            or payload.get('command') != [PX4_BINARY+'-logger', 'stop']
            or 'error' in payload or 'log_error' in payload or i <= j):
        return False
    for name in ('stdout', 'stderr'):
        if type(payload.get(name)) is not str or 'forcing stop' in payload[name]:
            return False
    for key in ('now_ns', 'mono_ns'):
        if (type(stop.get(key)) is not int or type(disarm.get(key)) is not int
                or stop[key] < disarm[key] or disarm[key] <= 0):
            return False
    return (type(payload.get('timeout_s')) in (int, float)
            and 0 < payload['timeout_s'] <= 8
            and type(payload.get('wall_s')) in (int, float)
            and math.isfinite(payload['wall_s']) and payload['wall_s'] >= 0)


def evaluate_episode(root):
    """Adjudicate raw receipts; agent.reached and runner.ok are not judges."""
    root = Path(root)
    config = _load(root/"configuration.json")
    row = _blank_row(config)
    findings = row["findings"]

    def check(ok, name):
        if not ok and name not in findings:
            findings.append(name)
        return bool(ok)

    try:
        receipt = _load(root/"process-receipt.json")
        row["cost"] = receipt.get("agent_cost", 0)
        container = receipt.get("container") or {}
        check(receipt.get("schema") == "echo5.sitl.process.v1" and receipt.get("evidence") == "external_gazebo_px4", "external_process_receipt")
        check(receipt.get("external_pid") is not None and receipt["external_pid"] != receipt.get("launcher_pid"), "separate_external_process")
        check(receipt.get("nonce") == config["nonce"] and bool(re.fullmatch(r"[0-9a-f]{32}", config["nonce"])), "fresh_nonce")
        check(receipt.get("finished_ns", 0) > receipt.get("started_ns", 0) > 0, "process_time")
        check(receipt.get("returncode") == 0 and receipt.get("error") is None, "process_exit")
        check(receipt.get("teardown") is True and container.get("state", {}).get("Running") is False, "bounded_teardown")
        check(container.get("id") == receipt.get("container_id") and bool(container.get("id")), "container_identity")
        check(container.get("image") == receipt.get("image_id") == IMAGE_ID, "image_identity")
        check(container.get("network") == "none" and container.get("privileged") is False
              and not container.get("devices") and not container.get("port_bindings"), "isolated_no_devices_or_host_ports")
        for name, expected in _load(root/"input-manifest.json").items():
            path = (root/name).resolve()
            check(path.is_relative_to(root.resolve()) and path.is_file() and _sha(path) == expected, "input_hash:"+name)
        for name, expected in config["imported_sources"].items():
            source = (LEGACY_ROOT/name).resolve()
            check(source.is_relative_to(LEGACY_ROOT.parent) and source.is_file() and _sha(source) == expected,
                  "imported_source_changed:"+name)
        truth_source = config["instrumentation_sources"]["src/echo5/sitl_truth.py"]
        check(_sha(ROOT/"src/echo5/sitl_truth.py") == truth_source
              and _sha(root/"sitl_truth.py") == truth_source, "truth_instrument_source")
        parameter_source = config["instrumentation_sources"]["src/echo5/sitl_parameters.py"]
        check(_sha(ROOT/"src/echo5/sitl_parameters.py") == parameter_source
              and _sha(root/"sitl_parameters.py") == parameter_source, "parameter_adapter_source")
        recovery_source = config["instrumentation_sources"]["src/echo5/sitl_recovery.py"]
        check(_sha(ROOT/"src/echo5/sitl_recovery.py") == recovery_source
              and _sha(root/"sitl_recovery.py") == recovery_source, "recovery_adapter_source")
        adaptation = _load(root/"out/runner-adaptation.json")
        check(adaptation.get("nonce") == config["nonce"]
              and adaptation.get("original_sha256") == _sha(root/"legacy_runner.py")
              and adaptation.get("adapter_sha256") == recovery_source
              and bool(re.fullmatch(r"[0-9a-f]{64}", adaptation.get("effective_sha256", ""))),
              "runner_adaptation_binding")
        expected_parameters = validate_parameters(_load(CONTRACT)["sitl"]["px4_parameters"])
        adapter = _load(root/"out/px4-parameter-adapter.json")
        check(config["px4_parameters"] == adapter.get("requested") == expected_parameters,
              "parameter_contract_binding")
        params = _load(root/"out/ulog-parameters.json")
        for finding in audit_parameters(expected_parameters, params["initial"], params["changes"]):
            check(False, finding)
        identity = _load(root/"out/runtime-identity.json")
        check(identity.get("nonce") == config["nonce"] and identity.get("image_id") == IMAGE_ID, "runtime_nonce")
        check(receipt["started_ns"] <= identity.get("started_ns", 0) <= receipt["finished_ns"], "runtime_freshness")
        check(bool(identity.get("gz_version")) and bool(identity.get("gz"))
              and bool(re.fullmatch(r"[0-9a-f]{64}", identity.get("px4_binary_sha256", ""))), "runtime_binaries")
        processes = list(_lines(root/"out/processes.jsonl"))
        check(any("/px4 " in p["cmd"] for p in processes)
              and any("gz sim" in p["cmd"] or "gz-sim" in p["cmd"] for p in processes), "real_px4_gazebo_processes")
        ulog = _load(root/"out/ulog-evidence.json")
        ulog_path = (root/"out"/ulog["file"]).resolve()
        check(len(list((root/"out").rglob('*.ulg'))) == 1, 'single_complete_ulog')
        check(ulog_path.is_relative_to((root/"out").resolve()) and _sha(ulog_path) == ulog["sha256"], "ulog_hash")
        if not ulog_path.is_relative_to((root/"out").resolve()):
            raise ValueError('ULog must remain inside the episode')
        if (root/'evidence-manifest.json').exists():
            require_parameter_manifest(_load(root/'evidence-manifest.json'), ulog['file'])
        independent_parameters = _independent_parameters(ulog_path, config['nonce'], ulog['file'])
        with ulog_path.open("rb") as stream:
            check(stream.read(7) == b"ULog\x01\x12\x35", "ulog_magic")
        datasets = ulog["datasets"]
        check(ulog["last_timestamp"] > ulog["start_timestamp"] and all(
            len(datasets.get(k, {}).get("timestamp", [])) >= 3 for k in
            ("vehicle_local_position", "vehicle_status", "vehicle_land_detected")), "ulog_real_telemetry")
        check(2 in datasets["vehicle_status"]["arming_state"] and datasets["vehicle_land_detected"]["landed"][-1] == 1, "ulog_armed_then_landed")
        trace = list(_lines(root/"out/trace.jsonl"))
        check(_logger_shutdown_valid(trace, _load(root/'out/result.json')), 'clean_logger_shutdown')
        # Include the entire preparation/long hover, through observed disarm.
        # 60 ms is the existing ULog telemetry binding tolerance.
        begin = min(r['now_ns'] for r in trace if r.get('now_ns', 0) > 0)
        end = next(r['now_ns'] for r in trace if r['kind'] == 'disarmed')
        reconcile_parameter_evidence(params, independent_parameters, nonce=config['nonce'],
                                     sha256=ulog['sha256'], start_ns=begin, end_ns=end)
        truth = list(_lines(root/"out/private.jsonl"))
        transport = list(_lines(root/"transport.jsonl"))
        observations = [r for r in trace if r["kind"] == "observation"]
        checks = [r for r in trace if r["kind"] == "check"]
        bodies = list(_lines(root/"out/private-poses.jsonl"))
        truth_receipt = _load(root/"out/private-poses-receipt.json")
        check(_sha(root/"out/private-poses.jsonl") == truth_receipt["sha256"], "truth_stream_hash")
        start_stamp = next((r["now_ns"] for r in trace if r["kind"] == "supervision_start"), None)
        end_stamp = next((r["now_ns"] for r in trace if r["kind"] == "disarmed"), None)
        truth_findings = audit_pose_stream(bodies, truth_receipt, nonce=config["nonce"],
                                          source_sha256=truth_source,
                                          max_gap_ns=_load(CONTRACT)["sitl"]["truth_max_gap_ns"],
                                          start_ns=start_stamp, end_ns=end_stamp)
        for finding in truth_findings:
            check(False, finding)
        changes = [r for r in truth if r.get("kind") == "world_change"]
        check(bool(observations) and len(checks) >= 3 and len(bodies) >= 3, "raw_observations_health_truth")
        if not observations or len(bodies) < 3:
            raise ValueError("insufficient measured episode")
        stamps = [r["now_ns"] for r in bodies]
        check(all(a < b for a, b in zip(stamps, stamps[1:])), "advancing_sim_clock")
        row["truth_samples"] = len(stamps)
        row["truth_max_gap_ns"] = max(b-a for a, b in zip(stamps, stamps[1:]))
        # PX4's estimated position must bind to its independently recorded ULog.
        import bisect
        local = datasets["vehicle_local_position"]
        origin = next(r["value"] for r in trace if r["kind"] == "origin")
        for observation in observations:
            raw = observation["raw"]
            validate_raw(raw, raw["now_ns"])
            estimate = raw["estimate"]
            boot_us = estimate["px4_boot_ms"]*1000
            index = bisect.bisect_left(local["timestamp"], boot_us)
            candidates = [i for i in (index-1, index) if 0 <= i < len(local["timestamp"])]
            i = min(candidates, key=lambda j: abs(local["timestamp"][j]-boot_us))
            pos = [round((local["y"][i]-origin[0])*1000), round((local["x"][i]-origin[1])*1000),
                   round((-local["z"][i]-origin[2])*1000)]
            check(abs(local["timestamp"][i]-boot_us) <= 60000 and max(abs(a-b) for a, b in zip(pos, estimate["position_mm"])) <= 150,
                  "ulog_estimate_binding")
        c = module("nexus0.drone3.contract")
        perception = module("nexus0.compose1_v3.perception")
        energy = module("nexus0.drone3.energy")
        supervisor = module("nexus0.drone3.supervisor").MissionSupervisor(config["runner"]["power_model"], [0, 0], (0, 0))
        obs_by_epoch = {r["epoch"]: r for r in observations}
        responses = {r["epoch"]: r["response"] for r in transport if r["side"] == "agent"}
        reply_records = {r["epoch"]: r for r in transport if r["side"] == "agent"}
        check(len(reply_records) == sum(r["side"] == "agent" for r in transport), "one_response_per_epoch")
        command_evidence = _CommandEvidence(responses)
        deliveries = {}
        previous_response_epoch = None
        reason_visits, reason_position = Counter(), None
        information_counts = Counter()
        approved = {}
        arrived = set()
        unsafe = 0
        veto = next((r for r in trace if r["kind"] == "veto"), None)
        for event in trace:
            kind = event["kind"]
            command_evidence.feed(event)
            if kind == "check":
                ok = supervisor.check(event["health"])
                if not check(ok == event["ok"] and event["state"] == supervisor.gateway.state
                             and event["samples"] == supervisor.gateway.samples, "safe_recompute"):
                    raise ValueError("independent_completion_samples")
            elif kind == "observation":
                supervisor.occupied(c.grid(event["raw"]["estimate"]["position_mm"]))
                response = responses.get(event["epoch"])
                if response is not None:
                    incoming = reply_records[event["epoch"]].get("outcome")
                    if previous_response_epoch is None:
                        check(incoming is None, "no_invented_initial_consequence")
                    else:
                        expected = command_evidence.completed.get(previous_response_epoch)
                        if not check(expected is not None and incoming == expected
                                     and previous_response_epoch not in deliveries, "public_consequence_vs_gateway_trace"):
                            raise ValueError("actor_outcome_delivery_binding")
                        if incoming is not None:
                            validate_outcome(incoming, responses[previous_response_epoch])
                            deliveries[previous_response_epoch] = event["epoch"]
                            row["actor_consequences"] += 1
                            if incoming["disposition"] == "arrived" and c.intention(incoming["wsp"])[0] == "move":
                                reason_position = tuple(incoming["prediction"])
                                reason_visits[reason_position] += 1
                    raw = event["raw"]
                    check(response.get("raw_sha256") == digest(raw), "all_response_sensor_binding")
                    frame = perception.project({k:v for k,v in raw.items() if k != "battery"}, 240)
                    verified = audit_reasoning(frame, response, config["agent"]["goal"], config["mode"])
                    audit_information(frame, response, information_counts, config["mode"])
                    row["reasoner_calls"] += verified["called"]
                    row["reasoner_actions"] += verified["applied"]
                    if verified["called"]:
                        point = tuple(frame["odometry"])
                        if point != reason_position:
                            reason_visits[point] += 1
                            reason_position = point
                        proof = response["reasoning"]["proposal"]
                        check(proof["visits"] == [[list(p),n] for p,n in sorted(reason_visits.items())]
                              and proof["consequence_count"] == row["actor_consequences"], "reasoning_history_binding")
                    previous_response_epoch = event["epoch"]
            elif kind == "proposal":
                raw = obs_by_epoch[event["epoch"]]["raw"]
                frame = perception.project({k: v for k, v in raw.items() if k != "battery"}, 240)
                decision = supervisor.submit(event["request"], event["health"], dict(frame=frame, battery=energy.battery_sample(raw["battery"])))
                if not check(decision == event["decision"], "gateway_and_power_recompute"):
                    raise ValueError("independent_command_admission")
                response = responses.get(event["epoch"], {})
                check(response.get("raw_sha256") == digest(raw) and response.get("wsp") == event["request"]["wsp"]
                      and response.get("prediction") == event["request"]["prediction"], "reasoning_to_gateway_binding")
                if decision["allowed"]:
                    approved[event["request"]["seq"]] = decision
            elif kind == "send":
                proposal = approved.get(event["seq"])
                unsafe += int(not proposal or proposal["target_mm"] != event["target_mm"])
                unsafe += int(veto is not None and event["mono_ns"] >= veto["mono_ns"])
            elif kind == "ack":
                if not check(supervisor.acknowledge(event["ack"], event["now_ns"]) == event["accepted"], "ack_identity_and_order"):
                    raise ValueError("independent_ack_acceptance")
            elif kind == "arrival":
                if not check(supervisor.gateway.state == "complete" and supervisor.gateway.samples >= 3
                             and event["samples"] == supervisor.gateway.samples, "arrival_after_ack_and_samples"):
                    raise ValueError("independent_arrival_completion")
                check(supervisor.gateway.release(), "arrival_release")
                arrived.add(event["epoch"])
        row.update(_audit_public_outcomes(_load(root/"public-outcomes.json"), command_evidence, deliveries))
        row["reasoner_executed"] = sum(int(responses[epoch]["reasoning"]["applied"]) for epoch in arrived)
        sends = [r for r in trace if r["kind"] == "send"]
        check(len({r["seq"] for r in sends}) == len(sends), "one_send_per_sequence")
        if config["condition"] != "low_energy":
            check(bool(sends) and bool(arrived), "actual_mission_goals_and_arrivals")
        row["unsafe_commands"] = unsafe
        check(unsafe == 0, "no_unsafe_commands")
        if veto:
            check(not any(r["kind"] in ("send", "land_request", "gcs_heartbeat") and r["mono_ns"] > veto["mono_ns"] for r in trace), "nothing_after_veto")
            recoveries = [r for r in trace if r["kind"] == "recovery_probe"]
            check(len(recoveries) >= 2 and all(r["ok"] is False for r in recoveries), "safe_latch")
        # Private pose judge: swept body against geometry, including between samples.
        minimum = math.inf
        collisions = 0
        for left, right in zip(bodies, bodies[1:]):
            a, b = [v*1000 for v in left["body"][1:3]], [v*1000 for v in right["body"][1:3]]
            gap_s = (right["now_ns"]-left["now_ns"])/1e9
            check(math.dist(a, b) <= 3000*gap_s+1, "physical_speed_envelope")
            solids = [tuple(p) for p in config["geometry"]["solids"]]
            for change in changes:
                if right["now_ns"] >= change["begin_ns"]:
                    src = (round(change["source"][0]/3), round(change["source"][1]/3), 0)
                    dst = (round(change["target"][0]/3), round(change["target"][1]/3), 0)
                    # During transition take both locations, then the new one.
                    if left["now_ns"] >= change["now_ns"] and src in solids:
                        solids.remove(src)
                    solids.append(dst)
            for x, y, _ in solids:
                clearance = _segment_box_distance(a, b, (x*3000-1500, y*3000-1500), (x*3000+1500, y*3000+1500))
                # Bounded unobserved curvature margin. Excessive gaps fail above.
                margin = 3000*gap_s/2
                minimum = min(minimum, clearance-margin)
                collisions += int(clearance-margin <= 400)
        row["collisions"] = collisions
        row["minimum_clearance_mm"] = round(minimum, 3)
        check(collisions == 0, "swept_collision_envelope")
        goal = config["geometry"]["goal"]
        for observation in observations:
            raw = observation["raw"]
            projected = perception.project({k: v for k, v in raw.items() if k != "battery"}, 240)
            body = min(bodies, key=lambda r: abs(r["now_ns"]-raw["now_ns"]))
            near_truth = abs(body["now_ns"]-raw["now_ns"]) <= 100_000_000
            at_goal = math.dist([body["body"][1]*1000, body["body"][2]*1000], [goal[0]*3000, goal[1]*3000]) <= 350
            row["goal_observed"] |= bool(near_truth and at_goal and projected["station_observed"] and projected["odometry"] == goal)
        disarm = next((r for r in trace if r["kind"] == "disarmed"), None)
        row["disarmed"] = disarm is not None
        check(row["disarmed"], "observed_disarm")
        if disarm:
            final = min(bodies, key=lambda r: abs(r["now_ns"]-disarm["now_ns"]))
            row["returned_home"] = math.hypot(final["body"][1]*1000, final["body"][2]*1000) <= 500
            check(abs(final["now_ns"]-disarm["now_ns"]) <= 100_000_000, "landing_pose_coverage")
        start = next(r["now_ns"] for r in trace if r["kind"] == "supervision_start")
        batteries = [energy.battery_sample(r["battery"]) for r in trace if r["kind"] == "sample" and r.get("battery") and r["now_ns"] >= start]
        remaining = [b["remaining"] for b in batteries if b is not None]
        check(bool(remaining), "measured_simulated_reserve")
        row["final_reserve"] = min(remaining) if remaining else None
        row["reserve_violations"] = sum(v < 40 for v in remaining)
        check(bool(remaining) and row["reserve_violations"] == 0, "reserve_floor")
        row["logic_latency"] = _latency_evidence(receipt, transport)
        check(row["logic_latency"]["passed"], "logic_latency")
        if config["condition"] in ("sensor_stale", "agent_hang"):
            injection = next((r for r in trace if r["kind"] == "injection"), None)
            check(injection is not None and veto is not None, "fault_actually_injected_and_vetoed")
            if injection and veto:
                key = "now_ns" if config["condition"] == "sensor_stale" else "mono_ns"
                limit = 500_000_000 if key == "now_ns" else 1_500_000_000
                expected_fault, expected_reason = (("lidar_stale", "sensor_stale") if key == "now_ns"
                                                   else ("agent_hang", "process_dead"))
                check(injection["fault"] == expected_fault and veto["reason"] == expected_reason, "fault_specific_veto")
                request = next((r for r in observations if r["mono_ns"] >= injection["mono_ns"]), None)
                begin = injection if key == "now_ns" else request
                row["injection_to_veto_ns"] = veto[key]-injection[key]
                row["fault_response_ns"] = veto[key]-begin[key] if begin else None
                check(begin is not None and 0 <= row["fault_response_ns"] <= limit, "fault_veto_latency")
        if config["condition"] == "contradiction":
            check(len(changes) == 1, "world_change_observed")
        row["valid_receipt"] = not findings
        row["information_probes"] = sum(information_counts.values())
        row["safety_success"] = row["valid_receipt"] and row["disarmed"]
        row["success"] = row["safety_success"] and row["goal_observed"] and row["returned_home"]
        row["status"] = "measured" if row["valid_receipt"] else "receipt_or_measurement_failed"
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
        findings.append(type(exc).__name__+": "+str(exc)[:500])
        row["status"] = "missing_or_invalid_external_receipt"
    return row


def _campaign_gates(rows, cfg):
    normal = [r for r in rows if r["condition"] in ("static", "contradiction")]
    complete = len(rows) == cfg["cases"]*len(MODES)
    coverage = set(r["condition"] for r in rows) == set(CONDITIONS)
    measured = bool(rows) and all(r["valid_receipt"] for r in rows)
    safe = measured and all(r["safety_success"] for r in rows)
    tasks = bool(normal) and all(r["success"] for r in normal if r["mode"] == "echo32")
    low = [r for r in rows if r["condition"] == "low_energy"]
    low_ok = bool(low) and all(r["returned_home"] and not r["goal_observed"] for r in low)
    principal = [r for r in normal if r["mode"] == "echo32"]
    reasoning_used = bool(principal) and all(r.get("reasoner_calls", 0) > 0 and r.get("reasoner_executed", 0) > 0 for r in principal)
    compared = summarize(rows)["controls"]["conventional"]
    advantage = measured and safe and compared["losses"] == 0 and (compared["wins"] > 0 or compared["cost_delta"] < 0)
    return dict(denominator=complete, condition_coverage=coverage, real_receipts=measured,
                safety=safe, nominal_goals=tasks, low_energy_safe=low_ok,
                reasoning_used=reasoning_used,
                measurements_pass=complete and coverage and safe and tasks and low_ok and reasoning_used,
                advantage=advantage, independent_audit=False, sitl_valid=False, hardware_valid=False)


def run_sitl_campaign(config, journal=None):
    """Launch only fresh real simulation; failures remain in the denominator."""
    cfg = _config(config)
    output = Path(cfg["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    ready = availability()
    _save(output/"availability.json", ready)
    _save(output/"contract.json", _load(CONTRACT))
    _save(output/"configuration.json", cfg)
    sources = {str(p.relative_to(ROOT)): _sha(p) for folder in ("src", "scripts") for p in sorted((ROOT/folder).rglob("*.py"))}
    _save(output/"sources.json", sources)
    rows = []
    deadline = time.monotonic()+cfg["campaign_timeout_s"]
    for case in range(cfg["cases"]):
        for mode in MODES:
            if ready["blockers"] or time.monotonic() >= deadline:
                row = dict(case_id=f"sitl-{case:04d}", condition=CONDITIONS[case % len(CONDITIONS)], mode=mode,
                           seed=cfg["seed"]+case, evidence="not_run", valid_receipt=False, safety_success=False,
                           success=False, status="blocked" if ready["blockers"] else "campaign_timeout",
                           cost=0, collisions=None, reserve_violations=None, findings=list(ready["blockers"]),
                           returned_home=False, goal_observed=False, disarmed=False)
            else:
                folder = output/f"{case:04d}-{mode}"
                try:
                    row = _run_episode(folder, cfg, case, mode, ready["podman"], deadline, journal)
                except Exception as exc:
                    # Instrument failures retain their own artifact and their
                    # original scheduled denominator; never retry over files.
                    error = dict(error=type(exc).__name__+": "+str(exc)[:1000], case_id=f"sitl-{case:04d}", mode=mode)
                    folder.mkdir(exist_ok=True)
                    _save(folder/"instrument-error.json", error)
                    row = dict(case_id=error["case_id"], condition=CONDITIONS[case % len(CONDITIONS)], mode=mode,
                               seed=cfg["seed"]+case, evidence="incomplete_external_process", valid_receipt=False,
                               safety_success=False, success=False, status="instrument_error", cost=0,
                               collisions=None, reserve_violations=None, findings=[error["error"]],
                               returned_home=False, goal_observed=False, disarmed=False)
            rows.append(row)
    gates = _campaign_gates(rows, cfg)
    report = dict(schema="echo5.sitl.campaign.v1", config=cfg, rows=rows, summary=summarize(rows), gates=gates,
                  launcher_pid=os.getpid(), contract_sha256=_sha(output/"contract.json"),
                  status="pending_independent_audit" if gates["real_receipts"] else "blocked_or_failed",
                  limits=["Gazebo/PX4 simulation only; no hardware", "Synthetic power/effects priors; charge is sim_u",
                          "Seeded physics uses numerical tolerances; no exact floating replay promise",
                          "Hashes detect alteration, not malicious fabrication by an owner controlling code and receipts"])
    _save(output/"report.json", report)
    return report


def audit_sitl_campaign(output):
    """Run in a different process after measurement. No simulation replay."""
    output = Path(output).resolve()
    report = _load(output/"report.json")
    cfg = _config(_load(output/"configuration.json"))
    findings = []
    if report.get("schema") != "echo5.sitl.campaign.v1" or report.get("launcher_pid") == os.getpid():
        findings.append("fresh_external_auditor_required")
    if report.get("config") != cfg:
        findings.append("configuration_changed")
    if _load(output/"contract.json") != _load(CONTRACT) or _sha(output/"contract.json") != report.get("contract_sha256"):
        findings.append("contract_changed")
    for name, expected in _load(output/"sources.json").items():
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file() or _sha(path) != expected:
            findings.append("source_changed:"+name)
    rows = []
    nonces, containers = set(), set()
    for case in range(cfg["cases"]):
        for mode in MODES:
            folder = output/f"{case:04d}-{mode}"
            if not (folder/"evidence-manifest.json").is_file():
                findings.append("missing_external_receipt:"+folder.name)
                continue
            for name, expected in _load(folder/"evidence-manifest.json").items():
                path = (folder/name).resolve()
                if not path.is_relative_to(folder) or not path.is_file() or _sha(path) != expected:
                    findings.append("evidence_changed:"+folder.name+":"+name)
            row = evaluate_episode(folder)
            config = _load(folder/"configuration.json")
            receipt = _load(folder/"process-receipt.json")
            if (row["case_id"] != f"sitl-{case:04d}" or row["mode"] != mode
                    or row["seed"] != cfg["seed"]+case or row["condition"] != CONDITIONS[case % len(CONDITIONS)]):
                findings.append("case_identity_changed:"+folder.name)
            if config["nonce"] in nonces or receipt.get("container_id") in containers:
                findings.append("reused_episode_identity:"+folder.name)
            nonces.add(config["nonce"])
            containers.add(receipt.get("container_id"))
            if row != _load(folder/"row.json"):
                findings.append("row_not_reconstructible:"+folder.name)
            rows.append(row)
    gates = _campaign_gates(rows, cfg)
    if rows != report["rows"] or summarize(rows) != report["summary"]:
        findings.append("campaign_totals_or_denominator_changed")
    gates["independent_audit"] = not findings
    gates["sitl_valid"] = gates["measurements_pass"] and not findings
    result = dict(schema="echo5.sitl.audit.v1", config=cfg, rows=rows, summary=summarize(rows),
                  gates=gates, findings=findings, auditor_pid=os.getpid(), valid=gates["sitl_valid"])
    _save(output/"audit.json", result)
    return result
