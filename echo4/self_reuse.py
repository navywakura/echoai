"""Bounded T readout. No physics, body registers or diagnostic labels."""
from dataclasses import dataclass

from echoai.core.cam import Cam
from echoai.echo4.boundary import code, integer
from echoai.echo4.sensation import checked_packet
from echoai.nexus0.qtable import QTable
from echoai.nexus0.world import World


@dataclass(frozen=True)
class ReuseDecision:
    action: int
    predictions: tuple[int | None, ...]
    matches: tuple[int, ...]
    source: str


def validate_target(target):
    checked_packet(target)
    if any(not -100 <= code(target, j) <= 100 for j in range(4, 10)):
        raise ValueError("invalid goal E range")


def choose_from_memory(cam, world, q, slot, target, proposed, *, use_t=True):
    if not isinstance(cam, Cam) or not isinstance(world, World) or not isinstance(q, QTable):
        raise ValueError("requires existing CAM/T/Q")
    integer(slot, 0, 4095)
    integer(proposed, 0, 2)
    validate_target(target)
    if type(use_t) is not bool or world.n_actions != 3 or q.n_actions != 3 or not cam.slot[slot].occupied:
        raise ValueError("invalid readout context")
    if not use_t:
        return ReuseDecision(proposed, (None, None, None), (), "q_ablation")
    predictions = tuple(world.predict(slot, action) for action in range(3))
    matches = tuple(action for action, nxt in enumerate(predictions)
                    if nxt is not None and 0 <= nxt < 4096 and cam.slot[nxt].occupied
                    and cam.slot[nxt].wsp == target)
    if not matches:
        return ReuseDecision(proposed, predictions, (), "q_no_match")
    action = max(matches, key=lambda a: (q.get(slot, a), a == proposed, a == 2, -a))
    return ReuseDecision(action, predictions, matches, "t")
