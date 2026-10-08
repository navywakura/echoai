"""Use the historical gate; the fusion reducer never controls an actuator."""
import struct
from echoai.nexus0.gate import gate
from echoai.nexus0.constants import ACTION_APPROACH
from .core import ABSENT, BARRIER, unpack


def admit(wsp, proposed=ACTION_APPROACH):
    value, certainty, predicate, _, _ = unpack(wsp)
    allowed = predicate == BARRIER and value == ABSENT and certainty >= 80
    return gate(wsp, cam_hit=False, extract_ok=allowed,
                E=struct.unpack('<6b', wsp[4:10]), proposed=proposed,
                inhibit=not allowed)
