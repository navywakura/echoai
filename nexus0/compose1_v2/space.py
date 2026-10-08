"""Private extruded rooms; the same geometry can be rendered by Gazebo.

The agent never imports this module. Planar missions have a real 3D body but
do not claim arbitrary-altitude navigation. Units here are three-metre cells.
"""
import random
from collections import deque
from echoai.nexus0.compose1.space import DIRECTIONS, add, distance
from echoai.nexus0.fusion1.core import packet

CELL_MM = 3000
ALTITUDE_MM = 2500


class Space:
    def __init__(self, seed, condition='static'):
        rng = random.Random(seed)
        self.condition = condition
        self.rotation = rng.randrange(4)
        self.wall_x = rng.choice((1, 2, 3))
        self.gap_y = rng.choice((-2, -1, 1, 2))
        self.start = (0, 0, 0)
        self.goal = self.rotate((4, 0, 0))
        self.pos = self.start
        self.steps = self.collisions = 0
        self.energy = 30 if condition == 'low_energy' else 240
        self.domain = {self.rotate((x, y, 0)) for x in range(-1, 6) for y in range(-3, 4)}
        self.solids = self.make_solids(None if condition == 'closed' else self.gap_y)
        self.camera_solids = set(self.solids)
        self.moved = False

    def rotate(self, p):
        x, y, z = p
        for _ in range(self.rotation):
            x, y = -y, x
        return x, y, z

    def make_solids(self, gap):
        return {self.rotate((x, y, 0)) for x in range(-1, 6) for y in range(-3, 4)
                if x in (-1, 5) or y in (-3, 3) or (x == self.wall_x and y != gap)}

    def visible(self, target):
        # Discrete ray through cell centres; occupied endpoints remain visible.
        dx, dy = target[0]-self.pos[0], target[1]-self.pos[1]
        n = max(abs(dx), abs(dy))*12
        if not n:
            return True
        for step in range(n):
            p = (self.pos[0]+round(dx*step/n), self.pos[1]+round(dy*step/n), 0)
            if p != target and p in self.solids:
                return False
        return True

    def scan(self):
        cells = [dict(position=list(p),
                      depth=packet(int(p in self.camera_solids), 40).hex(),
                      lidar=packet(int(p in self.solids), 40).hex())
                 for p in sorted(self.domain) if self.visible(p)]
        self.camera_solids = set(self.solids)
        return dict(now_ns=self.steps*25_000_000, odometry=list(self.pos),
                    energy=self.energy, station_observed=self.pos == self.goal, cells=cells)

    def step(self, action):
        if type(action) is not int or not 0 <= action < 7:
            raise ValueError('action')
        before = self.pos
        target = add(before, DIRECTIONS[action])
        blocked = target not in self.domain or target in self.solids
        self.collisions += blocked
        if not blocked:
            self.pos = target
        cost = 1 if action == 6 else 4
        self.steps += 1
        self.energy -= cost
        if self.condition == 'dynamic' and self.steps >= 2 and not self.moved:
            old_gap = self.rotate((self.wall_x, self.gap_y, 0))
            if self.pos != old_gap:
                self.solids = self.make_solids(-self.gap_y)
                self.moved = True
        return dict(before=list(before), after=list(self.pos),
                    delta=[b-a for a, b in zip(before, self.pos)],
                    blocked=blocked, cost=cost, energy=self.energy)

    def home_distance(self, p):
        return self.path_distance(p, self.start)

    def path_distance(self, start, goal):
        if start not in self.domain or start in self.solids:
            return None
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            p, n = queue.popleft()
            if p == goal:
                return n
            for v in DIRECTIONS[:4]:
                q = add(p, v)
                if q in self.domain and q not in self.solids and q not in seen:
                    seen.add(q)
                    queue.append((q, n+1))
        return None

    def oracle_distance(self):
        return self.path_distance(self.start, self.goal)


def source_sdf(space, *, empty=False):
    """Only declarative models; world systems come from frozen FLIGHT-1S."""
    lines = ['<?xml version="1.0"?><sdf version="1.9"><world name="sim3">',
             '    <physics name="physics" type="ignored"><max_step_size>0.001</max_step_size>'
             '<real_time_factor>1</real_time_factor></physics>',
             '    <gravity>0 0 -9.80665</gravity>',
             '    <light name="sun" type="directional"><pose>0 0 10 0 0 0</pose>'
             '<diffuse>1 1 1 1</diffuse><direction>0.2 0.3 -1</direction></light>']

    def box(name, pose, size, color):
        geometry = '<geometry><box><size>'+size+'</size></box></geometry>'
        lines.append(f'    <model name="{name}"><static>true</static><pose>{pose}</pose>'
                     f'<link name="link"><collision name="collision">{geometry}</collision>'
                     f'<visual name="visual">{geometry}<material><ambient>{color}</ambient>'
                     f'<diffuse>{color}</diffuse></material></visual></link></model>')

    box('floor', '0 0 -0.1 0 0 0', '80 80 0.2', '0.35 0.35 0.35 1')
    if not empty:
        for i, (x, y, _) in enumerate(sorted(space.solids)):
            box(f'barrier_{i}', f'{x*3} {y*3} 2 0 0 0', '3 3 4', '0.7 0.7 0.7 1')
        # A marker on the enclosing wall identifies the station's approach
        # area. It does not occupy the cell where the body must arrive.
        dx, dy, _ = space.rotate((1, 0, 0))
        x, y, _ = space.goal
        size = '0.02 1 1' if dx else '1 0.02 1'
        box('station_beacon', f'{x*3+dx*1.49} {y*3+dy*1.49} 2.5 0 0 0',
            size, '0 1 0 1')
    lines.append('  </world></sdf>')
    return ('\n'.join(lines)+'\n').encode()
