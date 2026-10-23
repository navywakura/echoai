"""Bounded counterexample selection and empirical version-space repair.

This is not GAN training or formal proof. Every surviving program is executed;
an evaluator-owned witness only establishes solvability of a concrete case.
"""

import copy
import hashlib
import json
import random

from .cases import validate_witness
from .budget import Budget, BudgetExceeded


def program_id(program):
    return hashlib.sha256(json.dumps(program, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _matches(program, example, budget):
    from .programs import execute
    try:
        prediction = execute(program, example['input'], budget=budget)
        return [list(row) for row in prediction] == example['output']
    except (ValueError, TypeError):
        return False


def repair(hypotheses, examples, budget, *, journal=None):
    """Verify each child on all acquired examples; don't inherit parent scores."""
    survivors, rejected, seen = [], [], set()
    for proposal in hypotheses:
        budget.consume('proposal')
        key = program_id(proposal)
        if key in seen:
            continue
        seen.add(key)
        failure = None
        for index, example in enumerate(examples):
            if not _matches(proposal, example, budget):
                failure = index
                break
        if failure is None:
            survivors.append(copy.deepcopy(proposal))
        else:
            event = {'program_sha256': key, 'counterexample_index': failure,
                     'reason': 'observed_mismatch'}
            rejected.append(event)
            if journal:
                journal.write(kind='counterexample', **event)
    return {'survivors': survivors, 'rejected': rejected}


def choose_challenge(cases, hypotheses, budget, *, mode, seed, journal=None):
    """Credit requires a valid witness and measured failure, never text critique."""
    if mode not in ('reference', 'random', 'adaptive'):
        raise ValueError('unknown challenge strategy')
    ordering = list(range(len(cases)))
    if mode == 'random':
        random.Random(seed).shuffle(ordering)
    best, score, invalid, evaluations = None, -1, 0, 0
    for index in ordering:
        case = cases[index]
        budget.consume('challenge')
        if not validate_witness(case, budget):
            invalid += 1
            continue
        # Only development examples can be returned as feedback. Query labels
        # are used solely by witness validity, never by hypothesis selection.
        example = case['task']['train'][0]
        failures = sum(not _matches(p, example, budget) for p in hypotheses)
        evaluations += len(hypotheses)
        if failures > score:
            best, score = case, failures
        if mode != 'adaptive':
            break
    if journal:
        journal.write(kind='challenge_selection', mode=mode, invalid=invalid,
                      tested=evaluations, observed_failures=max(score, 0),
                      case_id=None if best is None else best['id'])
    return {'case': copy.deepcopy(best), 'observed_failures': max(score, 0),
            'invalid': invalid, 'hypothesis_evaluations': evaluations}


def predict(hypotheses, rows, budget):
    from .programs import execute
    outcomes = {}
    for hypothesis in hypotheses:
        try:
            output = [list(row) for row in execute(hypothesis, rows, budget=budget)]
        except (ValueError, TypeError):
            return {'status': 'ambiguous', 'predictions': None, 'test_verified': False}
        outcomes[digest_json(output)] = output
    if len(outcomes) != 1:
        return {'status': 'ambiguous' if outcomes else 'unsolved',
                'predictions': None, 'test_verified': False}
    return {'status': 'solved', 'predictions': [next(iter(outcomes.values()))],
            'test_verified': False}


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run_benchmark(config, *, journal=None):
    from .cases import make_case
    from .programs import candidate_atoms
    from .evaluation import exact_success, paired
    arms = {name: [] for name in config['conditions']}
    for index in range(config['paired_runs']):
        seed = config['seed'] + index*1000
        family = ('right_recolor', 'above_recolor')[index % 2]
        for mode in config['conditions']:
            budget = Budget(config['work_per_arm'])
            archive, hypotheses, exhausted = [], [], False
            evidence = []
            try:
                initial = make_case(seed, family, split='acquisition', budget=budget, easy=True)
                if not validate_witness(initial, budget):
                    raise RuntimeError('initial curriculum witness invalid')
                evidence = copy.deepcopy(initial['task']['train'][:2])
                hypotheses = repair(list(candidate_atoms()), evidence, budget)['survivors']
                for round_index in range(config['rounds']):
                    pool = [make_case(seed + 10 + round_index*10 + k, family,
                                      split='acquisition', budget=budget, easy=(k == 0))
                            for k in range(config['pool_per_round'])]
                    selected = choose_challenge(pool, hypotheses, budget, mode=mode,
                                                seed=seed + round_index, journal=journal)
                    if selected['case'] is None:
                        raise RuntimeError('curriculum contains no valid challenge')
                    example = selected['case']['task']['train'][0]
                    evidence.append(copy.deepcopy(example))
                    before = len(hypotheses)
                    repaired = repair(hypotheses, evidence, budget, journal=journal)
                    hypotheses = repaired['survivors']
                    archive.append({'round': round_index, 'case_id': selected['case']['id'],
                                    'failures': selected['observed_failures'],
                                    'before': before, 'after': len(hypotheses),
                                    'rejected': repaired['rejected']})
            except BudgetExceeded:
                exhausted = True
            frozen = digest_json(hypotheses)
            rows = []
            for query_index in range(config['confirmation_cases_per_run']):
                ledger = Budget(config['query_work_per_case'])
                # Generation has a fixed 3192-unit reservation. A smaller
                # allowance is a bad experiment configuration, not agent failure.
                if ledger.limit < 3192:
                    raise ValueError('query budget does not cover case generation')
                case = make_case(seed + 500 + query_index, family,
                                 split='confirmation', budget=ledger)
                try:
                    # Generation, witness validation and prediction all count.
                    if not validate_witness(case, ledger):
                        raise RuntimeError('invalid curriculum confirmation witness')
                    result = predict(hypotheses, case['task']['test'][0]['input'], ledger)
                except BudgetExceeded:
                    result = {'status': 'budget_exhausted', 'predictions': None,
                              'test_verified': False}
                rows.append({'id': case['id'], 'result': result, 'expected': case['expected'],
                             'success': exact_success(result, case['expected']), 'work': ledger.snapshot()})
            if frozen != digest_json(hypotheses):
                raise RuntimeError('curriculum evaluation changed hypotheses')
            arms[mode].append({'seed': seed, 'family': family, 'hypotheses': hypotheses,
                               'hypotheses_sha256': frozen, 'archive': archive,
                               'evidence': evidence, 'acquisition': budget.snapshot(),
                               'acquisition_budget_exhausted': exhausted, 'rows': rows})
    totals = {}
    for mode, runs in arms.items():
        rows = [row for run in runs for row in run['rows']]
        acquisition = sum(run['acquisition']['used'] for run in runs)
        evaluation = sum(row['work']['used'] for row in rows)
        totals[mode] = {'successes': sum(row['success'] for row in rows), 'cases': len(rows),
                        'acquisition_work': acquisition, 'evaluation_work': evaluation,
                        'total_work': acquisition + evaluation,
                        'acquisition_exhausted': sum(run['acquisition_budget_exhausted'] for run in runs)}
    comparisons = {}
    for control in ('reference', 'random'):
        comparisons['adaptive_vs_' + control] = paired(
            [r['success'] for run in arms[control] for r in run['rows']],
            [r['success'] for run in arms['adaptive'] for r in run['rows']])
        comparisons['adaptive_vs_' + control]['total_work_delta'] = (
            totals['adaptive']['total_work'] - totals[control]['total_work'])
    return {'scope': 'bounded empirical counterexample curriculum; fixed two transformation families',
            'reference': 'sequential selection with same repair, not a historic ECHO-4.5 score',
            'totals': totals, 'comparisons': comparisons, 'runs': arms, 'llm_calls': 0}
