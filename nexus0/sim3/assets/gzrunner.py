"""Private side of SIM-3: the only process that talks to Gazebo.

Runs inside the pinned container, never on the host, and never in the
same process as the consumer. It speaks one JSON line per message over
stdin/stdout to the supervisor. Everything it reports — sim time, rig
pose, model poses, contacts — is read back out of the running backend's
entity component manager or off a sensor topic. Nothing here reads the
manifest, the split, the seed or the roles: it is handed an effective
SDF and a model name and that is all it knows.

Stdlib plus the Gazebo Python bindings only; it is mounted read-only and
its bytes are hashed into the run record.
"""

import json
import resource
import sys
import time

import gz.math7  # noqa: F401  - registers Pose3d for the pybind11 signatures
import gz.sim8 as sim
from gz.msgs10.contacts_pb2 import Contacts
from gz.transport13 import Node

STEP_LIMIT = 1_000_000


def _ns(stamp) -> int:
    """Exact nanoseconds from whatever the binding hands back."""
    for attr in ("nanoseconds", "total_nanoseconds"):
        if hasattr(stamp, attr):
            return int(getattr(stamp, attr)())
    days = getattr(stamp, "days", 0)
    seconds = getattr(stamp, "seconds", 0)
    micros = getattr(stamp, "microseconds", None)
    if micros is not None:
        return ((days * 86400 + seconds) * 1_000_000 + micros) * 1000
    return int(round(stamp.total_seconds() * 1e9))


def _um(v: float) -> int:
    return int(round(v * 1_000_000))


def emit(obj) -> None:
    sys.stdout.write(json.dumps(obj, sort_keys=True) + "\n")
    sys.stdout.flush()


def main() -> int:
    args = json.loads(sys.argv[1])
    sdf_path = args["sdf"]
    rig_model = args["rig_model"]
    contact_topic = args["contact_topic"]

    contacts = []

    def on_contact(msg: Contacts) -> None:
        if not len(msg.contact):
            return
        stamp = msg.header.stamp
        contacts.append({
            "stamp_ns": int(stamp.sec) * 1_000_000_000 + int(stamp.nsec),
            "pairs": sorted({(c.collision1.name, c.collision2.name)
                             for c in msg.contact})[:4],
            "n": len(msg.contact),
        })

    node = Node()
    subscribed = bool(node.subscribe(Contacts, contact_topic, on_contact))

    fixture = sim.TestFixture(sdf_path)
    state = {"pre": None, "frame": None, "models": None, "gravity": None}

    def pre_update(info, ecm):
        if state["pre"] is not None:
            return
        world = sim.World(sim.world_entity(ecm))
        link = sim.Link(sim.Model(world.model_by_name(ecm, rig_model))
                        .link_by_name(ecm, "body"))
        pose = link.world_pose(ecm)
        state["pre"] = {
            "sim_time_ns": _ns(info.sim_time),
            "rig_um": [_um(pose.x()), _um(pose.y()), _um(pose.z())],
        }
        gravity = world.gravity(ecm)
        state["gravity"] = [_um(gravity.x()), _um(gravity.y()), _um(gravity.z())]
        models = {}
        for entity in world.models(ecm):
            model = sim.Model(entity)
            name = model.name(ecm)
            body = model.link_by_name(ecm, "body")
            if body is None:
                continue
            p = sim.Link(body).world_pose(ecm)
            models[name] = [_um(p.x()), _um(p.y()), _um(p.z())]
        state["models"] = models

    def post_update(info, ecm):
        world = sim.World(sim.world_entity(ecm))
        link = sim.Link(sim.Model(world.model_by_name(ecm, rig_model))
                        .link_by_name(ecm, "body"))
        pose = link.world_pose(ecm)
        state["frame"] = {
            "sim_time_ns": _ns(info.sim_time),
            "rig_um": [_um(pose.x()), _um(pose.y()), _um(pose.z())],
        }

    fixture.on_pre_update(pre_update)
    fixture.on_post_update(post_update)
    fixture.finalize()
    server = fixture.server()

    emit({"ev": "ready", "subscribed": subscribed, "contact_topic": contact_topic})

    seq = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        cmd = msg.get("cmd")
        if cmd == "step":
            state["frame"] = None
            server.run(True, 1, False)
            if state["frame"] is None:
                emit({"ev": "error", "why": "no_post_update"})
                return 3
            seq += 1
            out = {"ev": "frame", "i": seq}
            out.update(state["frame"])
            if seq == 1:
                out["pre"] = state["pre"]
                out["gravity_um"] = state["gravity"]
                out["models_um"] = state["models"]
            emit(out)
        elif cmd == "report":
            time.sleep(float(msg.get("settle_s", 0.3)))
            emit({
                "ev": "report",
                "n_contact_msgs": len(contacts),
                "first_contact": contacts[0] if contacts else None,
                "last_contact": contacts[-1] if contacts else None,
                "pairs": sorted({tuple(p) for c in contacts for p in c["pairs"]}),
                "max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
            })
        elif cmd == "quit":
            return 0
        else:
            emit({"ev": "error", "why": "unknown_command"})
            return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
