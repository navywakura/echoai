"""Plan C1 school, evaluator side. The estimate is a pure function of frames.

In A the agent does not yet know its mount offset, so it acts with the
uncalibrated camera and records what it sees. `calib_c1.estimate` then reads only
those frames. `replay` re-derives the payload from the recorded frames, so an
audit can check that the transferred offset follows from observation alone.
"""
from . import calib_c1, policy
from .camera_c1 import OffsetRoom, declared_body
from .planner_c1 import CalibratedPlanner
from .space_a2 import suite

GYM_SEED = 20273001
GYMS = 2
GYM_MOVES = 4
RESERVE = 6


def gym_rooms():
    rooms, _ = suite(GYM_SEED, GYMS, [], declared_body())
    return rooms


def train(offset):
    frames, energy, moves, collisions = [], 0, 0, 0
    for room in gym_rooms():
        world = OffsetRoom(room['seed'], declared_body(), offset)
        agent = CalibratedPlanner(policy.restore(policy.scratch()).snapshot(), world.goal,
                                  calib_c1.nominal(), reserve=RESERVE)
        frame = world.scan()
        frames.append(frame)
        for _ in range(GYM_MOVES):
            decision = agent.decide(frame)
            if decision['status'] not in ('moving', 'returning'):
                break
            before = world.energy
            consequence = world.step(bytes.fromhex(decision['wsp'])[13])
            energy += before-world.energy
            moves += 1
            collisions += consequence['blocked']
            frame = world.scan()
            frames.append(frame)
    payload = calib_c1.estimate(frames)
    return dict(payload=payload, identified=payload['offset'] == list(offset),
                frames=frames, moves=moves, energy=energy, collisions=collisions)


def replay(school):
    if calib_c1.estimate(school['frames']) != school['payload']:
        raise ValueError('school payload does not follow its own frames')
    return school['payload']
