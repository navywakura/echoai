"""Same-history Q interventions on existing PUBLIC v3/v4 traces only.

No policy fitting, world generation, B/C or isolated-exam claims. Forced Q
rows measure the controller's reachable decision channel, not a deployable
oracle policy. True distances are used only by this outside adjudicator.
"""
import argparse
from copy import copy, deepcopy
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1.controller import add
from echoai.nexus0.compose1.space import DIRECTIONS
from . import policy
from .rehearsal_v2 import Space

ROOT = Path(__file__).resolve().parents[2]


def action(decision):
    return bytes.fromhex(decision['wsp'])[13]


def observe_copy(agent, frame):
    probe = deepcopy(agent, {id(agent.model): agent.model})
    probe.update(frame)
    return probe


def intervene(agent, frame, values, *, observed=None):
    # Share read-only learned tables, copy episodic memory. Override ONLY Q
    # lookup, not visits, geometry, gate, search horizon or the action ordering.
    # Sensor ingestion is identical for every intervention. Do it once in a
    # private copy, then share its read-only evidence between probes. decide
    # resets pending and assigns all other control fields on the shallow copy.
    probe = copy(observed if observed is not None else observe_copy(agent, frame))
    probe.update = lambda same_frame: None
    probe.model = copy(agent.model)
    probe.model.values = lambda feature: list(values)
    return probe.decide(frame)


def conflicting_rankings(rows):
    """Opposite strict preferences for the SAME simultaneously offered pair.

    Different best actions with different candidate sets are not sufficient
    evidence that a fixed Q ranking cannot satisfy both contexts.
    """
    seen = {}
    for row in rows:
        distances = {int(a):d for a,d in row['oracle_distances'].items() if d is not None}
        orders = seen.setdefault(row['feature'], set())
        for a, da in distances.items():
            for b, db in distances.items():
                if da < db:
                    orders.add((a, b))
    return [dict(feature=k, action_pair=[a,b]) for k, pairs in sorted(seen.items())
            for a,b in sorted(pairs) if a < b and (b,a) in pairs]


def analyze(report, version, variant):
    school = report['schools'][variant]
    payload = report['payloads'][variant] if version == 3 else school['payload']
    model = policy.restore(payload)
    counts = school['counts']
    decisions = changed = sensitive = uncovered = 0
    quality = dict(better=0, worse=0, equal=0)
    rows = []
    for exam in report['exams'][variant]:
        world = Space(exam['seed'])  # Only previously public, recorded rooms.
        agent = Composer(model.snapshot(), world.goal)
        for trace in exam['rows']:
            frame = trace['observation']
            if trace['consequence'] is None:
                if agent.decide(frame) != trace['decision']:
                    raise ValueError('terminal replay mismatch')
                continue
            observed = observe_copy(agent, frame)
            zero = intervene(agent, frame, [0]*7, observed=observed)
            forced = []
            for preferred in range(4):
                values = [-127]*4+[0]*3
                values[preferred] = 127
                forced.append(action(intervene(agent, frame, values, observed=observed)))
            actual = agent.decide(frame)
            if actual != trace['decision']:
                raise ValueError('same-history replay mismatch')
            key = agent.feature().hex()
            chosen, baseline = action(actual), action(zero)
            allowed = sorted(set(forced))
            decisions += 1
            sensitive += len(allowed) > 1
            changed += chosen != baseline
            uncovered += counts.get(key, [0]*4)[chosen] == 0
            pos = tuple(frame['odometry'])
            distances = {a: world.path_distance(add(pos, DIRECTIONS[a]), world.goal)
                         for a in allowed if a < 4}
            if chosen != baseline:
                a = world.path_distance(add(pos, DIRECTIONS[chosen]), world.goal)
                b = world.path_distance(add(pos, DIRECTIONS[baseline]), world.goal)
                if a is None or b is None:
                    raise ValueError('counterfactual non-traversable action')
                quality['better' if a < b else 'worse' if a > b else 'equal'] += 1
            rows.append(dict(seed=exam['seed'], now_ns=frame['now_ns'], feature=key,
                             chosen=chosen, zero=baseline, forced_actions=allowed,
                             training_counts=counts.get(key, [0]*4),
                             oracle_distances={str(a):d for a,d in distances.items()}))
        if agent.model.fingerprint() != model.fingerprint():
            raise ValueError('diagnostic changed Q/T')
    conflicts = conflicting_rankings(rows)
    return dict(decisions=decisions, q_zero_changed=changed,
                forced_q_sensitive=sensitive, selected_untrained_pair=uncovered,
                changed_action_local_distance=quality,
                contradictory_pair_rankings=conflicts,
                school_features=len(counts),
                school_pairs=sum(sum(n > 0 for n in r) for r in counts.values()),
                schema_features=1728, planar_feature_upper_bound=144, rows=rows)


def run():
    result = dict(scope='public-same-history-diagnostic', transfer3_green=False,
                  campaign_C_opened=False, reports={}, findings={})
    for version in (3, 4):
        path = ROOT/'lab'/ 'transfer3'/f'rehearsal-v{version}.json'
        report = loads_strict(path.read_bytes())
        result['reports'][str(version)] = sha256_bytes(canonical_bytes(report))
        for rel, expected in report['inventory'].items():
            if sha256_bytes((ROOT/rel).read_bytes()) != expected:
                raise ValueError('frozen source changed: '+rel)
        for variant in ('corrected', 'reward_only', 'coverage_only'):
            print(f'diagnostic v{version}/{variant}', flush=True)
            result['findings'][f'v{version}/{variant}'] = analyze(report, version, variant)
    result['sources'] = {str(p.relative_to(ROOT)):sha256_bytes(p.read_bytes()) for p in
                         sorted((ROOT/'nexus0'/'transfer3').glob('*v5.py'))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    actual = run()
    raw = canonical_bytes(actual)
    if args.command == 'run':
        # New artifact only: never overwrite a prior diagnostic.
        with args.path.open('xb') as out:
            out.write(raw)
    elif loads_strict(args.path.read_bytes()) != actual:
        raise ValueError('diagnostic replay differs')
    print(sha256_bytes(raw), flush=True)
    for key, value in actual['findings'].items():
        print(key, {k:v for k,v in value.items() if k != 'rows'}, flush=True)


if __name__ == '__main__':
    main()
