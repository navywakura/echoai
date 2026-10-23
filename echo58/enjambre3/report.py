"""Prospective selection and verdict. Descriptive development is not validation."""
import argparse
from itertools import product
import json
from pathlib import Path

from ..crece.artifacts import save_new
from ..enjambre2.transport import ATTACKS, require
from . import bench as b
from .verify import verify


def exact_signed_rank(differences):
    """One-sided exact sign permutation on average absolute ranks, zeros removed.

    A positive difference means the candidate improves on its paired control.
    Ranks are doubled to keep ties exact; there is no asymptotic approximation.
    """
    values = [x for x in differences if x]
    if not values:
        return 1.0
    order = sorted(range(len(values)), key=lambda i: abs(values[i]))
    ranks = [0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and abs(values[order[end]]) == abs(values[order[cursor]]):
            end += 1
        for i in order[cursor:end]:
            ranks[i] = cursor + 1 + end
        cursor = end
    observed = sum(rank for rank, delta in zip(ranks, values) if delta > 0)
    at_least = sum(sum(rank for rank, sign in zip(ranks, signs) if sign) >= observed
                   for signs in product((0, 1), repeat=len(values)))
    return at_least / (2 ** len(values))


def holm(pvalues):
    passed = {}
    still = True
    ordered = sorted(pvalues, key=lambda key: (pvalues[key], key))
    for i, key in enumerate(ordered):
        still = still and pvalues[key] <= .05 / (len(ordered) - i)
        passed[key] = still
    return passed


def aggregate(audit):
    rows = audit['rows']
    out = {}
    for name, row in rows.items():
        arm, attack, macro = name.removesuffix('.json').split('-')
        target = out.setdefault(arm, {}).setdefault(attack, {
            'score': 0, 'harm': 0, 'solved': 0, 'failed': 0, 'episodes': 0,
            'exposure_queries': 0, 'affected_memory_responses': 0,
            'probe_actions': 0, 'probe_harm': 0, 'released_actions': 0, 'released_harm': 0,
            'steps': 0, 'actions': 0, 'harm_probe_legacy': 0, 'release_queries': 0,
            'by_kind': {k: {'harm': 0, 'score': 0, 'solved': 0, 'failed': 0} for k in b.KINDS},
            'macros': {}})
        for key in ('score', 'harm', 'solved', 'failed', 'episodes',
                    'exposure_queries', 'affected_memory_responses'):
            target[key] += row[key]
        for key, value in row['physical'].items():
            target[key] += value
        for kind, details in row['by_kind_details'].items():
            for key in target['by_kind'][kind]:
                target['by_kind'][kind][key] += details[key]
        target['macros'][macro] = {key: row[key] for key in ('score', 'harm', 'solved')}
    return out


def gates(table, selected):
    checks = {}
    for attack in ATTACKS:
        candidate = table[selected][attack]
        for control in ('ingenuo', 'prudente', 'sin_global'):
            checks[f'{attack}:harm_leq_{control}'] = candidate['harm'] <= table[control][attack]['harm']
        for control in ('ingenuo', 'prudente'):
            checks[f'{attack}:solved_geq_{control}'] = candidate['solved'] >= table[control][attack]['solved']
        checks[f'{attack}:score_leq_prudente'] = candidate['score'] <= table['prudente'][attack]['score']
        checks[f'{attack}:probe_harm_leq_prudente'] = candidate['probe_harm'] <= table['prudente'][attack]['probe_harm']
        checks[f'{attack}:exposure'] = candidate['exposure_queries'] > 0
    for control in ('sin_global', 'por_autor'):
        checks[f'score_lt_{control}'] = sum(row['score'] for row in table[selected].values()) < sum(
            row['score'] for row in table[control].values())
    checks['harm_lt_ingenuo'] = sum(row['harm'] for row in table[selected].values()) < sum(
        row['harm'] for row in table['ingenuo'].values())
    return checks


def select(root):
    root = Path(root)
    audit = verify(root)
    require(audit['phase'] == 'development', 'development only selection')
    table = aggregate(audit)
    ranking = []
    checks_by_arm = {}
    for arm in b.CANDIDATES:
        checks = gates(table, arm)
        checks_by_arm[arm] = checks
        ranking.append([sum(not value for value in checks.values()),
                        sum(row['harm'] for row in table[arm].values()),
                        sum(row['score'] for row in table[arm].values()), int(arm[-1]), arm])
    ranking.sort()
    result = {'selected': ranking[0][-1], 'selection_rule': 'violations,harm,score,n_min',
              'ranking': ranking, 'checks': checks_by_arm, 'table': table,
              'development_preflight_sha256': audit['preflight_sha256'],
              'development_completed_sha256': audit['completed_sha256'],
              'exam_run': False, 'validation_consulted': False}
    save_new(root / 'selection.json', result)
    return result


def result(root):
    root = Path(root)
    preflight = b.check_frozen(root)
    audit = verify(root)
    table = aggregate(audit)
    require(audit['phase'] == 'validation', 'validation only verdict')
    selected = f'v3_n{preflight["threshold"]}'
    checks = gates(table, selected)
    no_alarm = table[f'sin_alarma_n{preflight["threshold"]}']['false_alarm']
    no_release = table[f'sin_liberacion_n{preflight["threshold"]}']['false_alarm']
    candidate = table[selected]['false_alarm']
    checks['ablation:probe_harm_lt_sin_alarma'] = candidate['probe_harm'] < no_alarm['probe_harm']
    checks['ablation:solved_geq_sin_alarma'] = candidate['solved'] >= no_alarm['solved']
    checks['ablation:progress_gt_sin_liberacion'] = (candidate['solved'] > no_release['solved']
                                                  or candidate['score'] < no_release['score'])
    comparisons = {'harm_ingenuo': ('harm', 'ingenuo'),
                   'score_sin_global': ('score', 'sin_global'),
                   'score_por_autor': ('score', 'por_autor')}
    paired = {}
    pvalues = {}
    for name, (measure, control) in comparisons.items():
        differences = [sum(table[control][attack]['macros'][str(m)][measure]
                           - table[selected][attack]['macros'][str(m)][measure] for attack in ATTACKS)
                       for m in b.MACROS['validation']]
        paired[name] = differences
        pvalues[name] = exact_signed_rank(differences)
    adjusted = holm(pvalues)
    checks.update({f'holm:{key}': value for key, value in adjusted.items()})
    return {'phase': 'validation', 'selected': selected, 'audit_green': audit['audit_green'],
            'scientific_green': all(checks.values()), 'exam_run': False, 'checks': checks,
            'failed_gates': [key for key, value in checks.items() if not value],
            'paired_differences_control_minus_candidate': paired,
            'exact_one_sided_p': pvalues, 'holm_pass': adjusted, 'table': table,
            'preflight_sha256': audit['preflight_sha256'],
            'completed_sha256': audit['completed_sha256'],
            'selection_sha256': preflight['selection_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('select', 'result'))
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    row = select(args.root) if args.command == 'select' else result(args.root)
    if args.command == 'result':
        save_new(args.root / 'result.json', row)
    print(b.canonical(row))
