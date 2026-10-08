"""Plan C1 world: a camera mounted with an extrinsic offset. Evaluator side only.

The LiDAR is truthful and registered to the body. The camera only reports on
cells it actually saw, but tags each report at `seen cell + offset`. Reports that
land outside the map are dropped, as a real sensor's would be outside its frame.

An earlier probe modelled the camera as reporting, at each visible cell q, the
occupancy of q - offset even when that cell had never been seen. That is not how
a sensor works, and it hid information the agent could never have had. It was
replaced before this module was written; the probe result is published.

The agent never imports this module and it is never mounted in the cage.
"""
from echoai.nexus0.fusion1.core import UNKNOWN, packet
from .space_a2 import Body, Room

OFFSETS = tuple((x, y) for x in (-1, 0, 1) for y in (-1, 0, 1))


def validate_offset(offset):
    offset = tuple(int(v) for v in offset)
    if len(offset) != 2 or offset not in OFFSETS:
        raise ValueError('offset outside the declared Chebyshev-1 family')
    return offset


class OffsetRoom(Room):
    def __init__(self, seed, body, offset):
        super().__init__(seed, body)
        self.offset = validate_offset(offset)

    def scan(self):
        ox, oy = self.offset
        seen = [p for p in sorted(self.domain) if self.visible(p)]
        lidar = {p: packet(int(p in self.solids), 40).hex() for p in seen}
        camera = {}
        for r in seen:
            q = (r[0]+ox, r[1]+oy, r[2])
            if q in self.domain:
                camera[q] = packet(int(r in self.camera_solids), 40).hex()
        unknown = packet(UNKNOWN, 0).hex()
        cells = [dict(position=list(q), depth=camera.get(q, unknown), lidar=lidar.get(q, unknown))
                 for q in sorted(set(lidar) | set(camera))]
        self.camera_solids = set(self.solids)
        return dict(now_ns=self.steps*25_000_000, odometry=list(self.pos),
                    energy=self.energy, station_observed=self.pos == self.goal, cells=cells)


def declared_body():
    """Uniform movement cost, no turn term: C1 varies perception only."""
    return Body((4, 4, 4, 4), 0)
