"""Pessimistic transfer of unsampled actions. The factor lives in the export.

One budgeted school run is exported two ways. Nothing here changes the planner,
the reward, the exam or the frozen `transfer3-relative-q-v2` schema: a floored
row is an ordinary int8 row that `policy.validate` accepts unmodified.
"""
from echoai.nexus0.compose1.model import state_packet
from . import policy
from .rehearsal_v2 import Space
from .repair_v5 import episode as repaired_episode

FLOOR_MIN = -127
PLANAR = 4


def train(seeds, budget=128, *, reward_kind='progress', failure_bonus=-32):
    """Spend exactly `budget` executed moves; never fabricate observations."""
    if type(budget) is not int or not 1 <= budget <= 4096 or not seeds:
        raise ValueError('school budget/seeds')
    payload = policy.scratch()
    counts, episodes = {}, []
    used = 0
    while used < budget:
        if len(episodes) > budget:
            raise ValueError('school cannot spend its budget')
        seed = seeds[len(episodes) % len(seeds)]
        world = Space(seed)
        row = repaired_episode(world, payload, learn=True, reward_kind=reward_kind,
                               failure_bonus=failure_bonus,
                               move_budget=min(64, budget-used))
        payload = row['payload']
        used += row['moves']
        for feature, sampled in row['counts'].items():
            total = counts.setdefault(feature, [0]*PLANAR)
            for action, n in enumerate(sampled):
                total[action] += n
        episodes.append(dict(seed=seed, status=row['status'],
            moves=row['moves'], collisions=row['collisions'],
            reserve_violations=row['reserve_violations'],
            ingestions=row['ingestions'], visits=row['visits'],
            terminal_updates=sum(bool(r['learning'] and r['learning']['terminal'])
                                 for r in row['rows']),
            failure_bonus_applied=sum(bool(r['outcome']) and r['outcome'] != 'reached'
                                      for r in row['rows'])))
    if used != budget:
        raise ValueError('school did not spend exactly its budget')
    if sum(sum(row) for row in counts.values()) != used:
        raise ValueError('one executed move must mean one sample')
    return dict(payload=payload, counts=counts, moves=used, sim_u=used*4,
                episodes=episodes, features=len(counts),
                feature_action_pairs=sum(sum(n > 0 for n in r) for r in counts.values()),
                features_with_one_action=sum(sum(n > 0 for n in r) == 1
                                             for r in counts.values()),
                failure_bonus_applied=sum(e['failure_bonus_applied'] for e in episodes),
                terminal_updates=sum(e['terminal_updates'] for e in episodes))


def export_pessimistic(payload, counts):
    """Unsampled planar actions rank below every sampled one at that feature.

    A pure function of the standard export and the school's sample counts, so
    both arms provably come from one school run. A feature absent from the
    standard export was sampled with every learned value at zero, which is what
    an omitted row means; it is read as zeros rather than as missing evidence.
    """
    policy.validate(payload)
    learned_rows = {row['feature']: row['values'] for row in payload['q']}
    rows, matched = [], 0
    for code in range(1728):
        sampled = counts.get(state_packet(code, 3).hex())
        if not sampled or not any(sampled):
            continue
        matched += 1
        learned = learned_rows.get(code, [0]*7)[:PLANAR]
        floor = max(FLOOR_MIN, min(learned[a] for a in range(PLANAR) if sampled[a])-1)
        values = [learned[a] if sampled[a] else floor for a in range(PLANAR)]+[0, 0, 0]
        if any(values):
            rows.append(dict(feature=code, values=values))
    if matched != sum(1 for row in counts.values() if any(row)):
        raise ValueError('sampled feature outside the planar schema enumeration')
    floored = dict(schema=policy.SCHEMA, q=rows)
    policy.validate(floored)
    return floored
