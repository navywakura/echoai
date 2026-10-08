"""Reconstruct observation-only OTHER memory; never execute a peer or world."""
import hashlib

from echoai.core.cam import Cam
from echoai.nexus0.constants import UNKNOWN_NEXT
from echoai.nexus0.world import World
from echoai.echo4.continuity import canonical
from echoai.echo4.other_model import OtherModel, LIMIT, decode


def digest(model):
    """Canonical public subgraph, independent of private CAM slot addresses."""
    cam, world = model.cam, model.world
    rows = []
    for index, slot in enumerate(cam.slot):
        if not slot.occupied or not slot.source.startswith("other1-"):
            continue
        row = {"packet": slot.wsp.hex(), "fact": slot.has_fact,
               "extract": slot.extract, "source": slot.source,
               "transitions": [], "inverse": []}
        for action in range(3):
            pred, alt = world.pred[index][action], world.alt[index][action]
            row["transitions"].append((cam.slot[pred].wsp.hex() if pred != UNKNOWN_NEXT else None,
                                        world.n[index][action],
                                        cam.slot[alt].wsp.hex() if alt != UNKNOWN_NEXT else None,
                                        world.alt_n[index][action]))
        row["inverse"] = [(cam.slot[nxt].wsp.hex(), action, count)
                           for nxt, action, count in world.inv[index]]
        rows.append(row)
    pending = None if model.pending is None else (
        model.pending[0], tuple(p.hex() if p is not None else None for p in model.pending[1]), model.pending[2])
    state = {"rows": sorted(rows, key=lambda r: r["packet"]), "mode": model.mode,
             "last_tick": model.last_tick, "count": model.count,
             "pending": pending, "stopped": model.stopped,
             "capacity_drops": model.capacity_drops}
    return hashlib.sha256(canonical(state)).hexdigest()


def transcript(frames, observer):
    return [{"tick": f["tick"], "contexts": f["contexts"][observer],
             "outcomes": f["outcomes"][observer]} for f in frames]


def replay(records, mode):
    if type(records) is not list or len(records) > LIMIT:
        raise ValueError("bounded public transcript required")
    model = OtherModel(Cam(), World(), mode=mode)
    predictions, forecasts = [], []
    for record in records:
        if type(record) is not dict or set(record) != {"tick", "contexts", "outcomes"}:
            raise ValueError("public record shape")
        decoded = []
        for key in ("contexts", "outcomes"):
            values = record[key]
            if type(values) is not list or len(values) != 2:
                raise ValueError("public record packets")
            if any(p is not None and (type(p) is not str or len(p) != 32) for p in values):
                raise ValueError("packet encoding")
            decoded.append(tuple(bytes.fromhex(p) if p is not None else None for p in values))
        own_action = decode(decoded[1][0], action=True)[2]
        forecasts.append(model.begin(record["tick"], decoded[0]))
        predictions.append(model.finish(record["tick"], own_action, decoded[1]))
    return {"predictions": predictions, "forecasts": forecasts, "memory_sha256": digest(model)}
