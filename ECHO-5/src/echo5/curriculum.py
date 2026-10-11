"""Matched *actual acquisition opportunities*, with unpadded selector costs.

The common prediction bank is executed once, without labels, and supplied to
all three actors. A private teacher labels only a selected acquisition input.
The old adversarial benchmark is deliberately not called or modified.
"""

from collections import Counter
import copy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random

from .adversarial import program_id
from .budget import Budget, BudgetExceeded
from .evaluation import exact_success
from .programs import execute


SCHEMA = 'echo5-curriculum-closure-v2'
CONDITIONS = ('sequential', 'random', 'adaptive')
CONTRACT_PATH = Path(__file__).resolve().parents[2] / 'docs' / 'CURRICULUM-CONTRACT.json'
DIRECTIONS = ('right', 'above', 'left', 'below')
SUFFIXES = (None, 'rot90', 'fliplr', 'flipud')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))


def _sources():
    """Local source identities; the parent must freeze before importing/running."""
    root = Path(__file__).resolve().parents[2]
    paths = [root / 'src' / 'echo5' / name for name in
             ('curriculum.py', 'adversarial.py', 'budget.py', 'programs.py',
              'grounding.py', 'legacy.py', 'evaluation.py', 'cases.py')]
    paths += [root.parent / 'seed' / name for name in
              ('dsl.py', 'relational_dsl.py', 'refinement.py', 'learn.py')]
    return {str(path.relative_to(root.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


def default_config(phase='confirmation'):
    """Return a detached configuration; development never passes closure."""
    if phase not in ('development', 'confirmation'):
        raise ValueError('phase must be development or confirmation')
    contract = _contract()
    config = copy.deepcopy(contract['config'])
    config['phase'] = phase
    if phase == 'development':
        config['seed'] = contract['development_seed']
    return config


def _config(value):
    if type(value) is not dict:
        raise ValueError('config must be a JSON object')
    config = default_config(value.get('phase', 'confirmation'))
    if set(value) - set(config):
        raise ValueError('unknown curriculum configuration option')
    config.update(copy.deepcopy(value))
    bounds = {'seed': (0, 2**63 - 1), 'paired_runs': (1, 256), 'rounds': (1, 8),
              'pool_per_round': (2, 16), 'confirmation_cases_per_run': (2, 32),
              'work_per_run': (1, 10**10), 'bootstrap_samples': (128, 65536)}
    for name, (low, high) in bounds.items():
        if type(config[name]) is not int or not low <= config[name] <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    if config['conditions'] != list(CONDITIONS):
        raise ValueError('conditions must be sequential, random, adaptive in that order')
    if config['phase'] == 'confirmation':
        expected = default_config()
        if config != expected:
            raise ValueError('confirmation must use the preregistered configuration exactly')
    elif config['seed'] == default_config()['seed']:
        raise ValueError('development may not use the confirmation seed')
    return config


def _seed(seed, *parts):
    return int(_digest([seed, *parts]), 16)


def grammar():
    """16 public programs; neither task identity nor witness enters this list."""
    return [{'steps': [{'op': 'relate', 'role': 'largest', 'relation': direction,
                        'effect': 'recolor'}] + ([{'op': suffix}] if suffix else [])}
            for direction in DIRECTIONS for suffix in SUFFIXES]


@dataclass(frozen=True)
class PublicChallenge:
    id: str
    input: tuple


@dataclass(frozen=True)
class PredictionTable:
    """Only public inputs and actor predictions: no labels, seeds or witness."""
    challenges: tuple
    predictions: tuple
    fingerprints: tuple
    hypothesis_ids: tuple


def _oracle(rows, witness, budget=None):
    """Independent coordinate renderer: no program executor/grounding calls.

    All generated scenes have zero background and disconnected monochrome
    objects. Reconstructing those objects here also makes the audit independent
    of the generator's bookkeeping and the actor's relation implementation.
    """
    def charge(kind, amount=1):
        if budget is not None:
            budget.consume(kind, amount)
    area = sum(map(len, rows))
    charge('oracle_grid_cells', area)
    remaining = {(y, x) for y, row in enumerate(rows) for x, c in enumerate(row) if c}
    objects = []
    while remaining:
        charge('oracle_component_seed_cells', len(remaining))
        start = min(remaining)
        color = rows[start[0]][start[1]]
        cells, stack = {start}, [start]
        remaining.remove(start)
        while stack:
            y, x = stack.pop()
            for neighbor in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                charge('oracle_neighbor_checks')
                if neighbor in remaining and rows[neighbor[0]][neighbor[1]] == color:
                    remaining.remove(neighbor)
                    cells.add(neighbor)
                    stack.append(neighbor)
        objects.append((color, cells))
    step = witness['steps'][0]
    key = lambda obj: -len(obj[1])
    charge('oracle_source_comparisons', 2 * len(objects))
    best = min(map(key, objects))
    selected = [obj for obj in objects if key(obj) == best]
    if len(selected) != 1:
        raise ValueError('oracle source is ambiguous')
    source = selected[0]
    charge('oracle_bounds_cells', 4 * len(source[1]))
    sy0, sy1 = min(y for y, _ in source[1]), max(y for y, _ in source[1])
    sx0, sx1 = min(x for _, x in source[1]), max(x for _, x in source[1])
    charge('oracle_render_cells', area)
    output = [list(row) for row in rows]
    for obj in objects:
        if obj is source:
            continue
        charge('oracle_bounds_cells', 6 * len(obj[1]))
        charge('oracle_direction_comparisons', 4)
        ys, xs = [y for y, _ in obj[1]], [x for _, x in obj[1]]
        matches = {'right': min(xs) > sx1, 'left': max(xs) < sx0,
                   'above': max(ys) < sy0, 'below': min(ys) > sy1}
        if matches[step['relation']]:
            for y, x in obj[1]:
                charge('oracle_paint_cells')
                output[y][x] = source[0]
    if len(witness['steps']) == 2:
        charge('oracle_geometry_cells', area)
        suffix = witness['steps'][1]['op']
        if suffix == 'rot90':
            output = [list(row) for row in zip(*output[::-1])]
        elif suffix == 'fliplr':
            output = [row[::-1] for row in output]
        elif suffix == 'flipud':
            output = output[::-1]
        else:
            raise ValueError('oracle suffix outside curriculum grammar')
    return output


def _scene(seed, *, holdout, budget):
    """Disjoint scene styles; pool ordering is never a difficulty ordering."""
    rng = random.Random(seed)
    def draw(method, *args):
        budget.consume('generation_random_draws')
        return getattr(rng, method)(*args)
    height, width = (21, 23) if holdout else (15, 15)
    budget.consume('generate_cells', height * width)
    rows = [[0] * width for _ in range(height)]
    y, x = (8, 10) if holdout else (draw('randrange', 5, 8), draw('randrange', 5, 8))
    # Every direction has a valid target, even in a visually uninformative
    # scene whose targets already share the source color. This preserves the
    # existing DSL's strict no-empty-binding rule without conditioning inputs
    # on the secret witness or rejecting/replacing difficult examples.
    positions = [(y, x), (2, x + draw('randrange', -1, 2)),
                 (16 if holdout else 12, x + draw('randrange', -1, 2)),
                 (y + draw('randrange', -1, 2), 2),
                 (y + draw('randrange', -1, 2), 19 if holdout else 12)]
    if holdout:
        positions += [(3, 18), (16, 3)]
    palette = draw('sample', (5, 6, 7, 8, 9) if holdout else (1, 2, 3, 4), 3)
    same_color_probability = 0.25 if holdout else draw('choice', (0.25, 0.75, 1.0))
    for i, (y, x) in enumerate(positions):
        color = palette[0] if i == 0 or draw('random') < same_color_probability else draw('choice', palette[1:])
        if i == 0:
            shape = (((0, 0), (0, 1), (0, 2), (1, 1), (2, 1), (2, 2)) if holdout
                     else ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2)))
        else:
            shape = ((0, 0), (0, 1)) if holdout else ((0, 0),)
        budget.consume('generate_object_cells', len(shape))
        for dy, dx in shape:
            rows[y+dy][x+dx] = color
    budget.consume('input_identity_cells', height * width)
    return PublicChallenge(_digest(rows), tuple(tuple(row) for row in rows))


def _label(challenge, witness, budget):
    area = len(challenge.input) * len(challenge.input[0])
    expected = _oracle(challenge.input, witness, budget)
    budget.consume('witness_executions')
    actual = execute(witness, challenge.input, budget=budget)
    budget.consume('witness_compare_cells', area)
    if [list(row) for row in actual] != expected:
        raise ValueError('invalid curriculum witness; instrument error, no replacement')
    return tuple(tuple(row) for row in expected)


def prediction_table(challenges, hypotheses, budget):
    """Execute each cell once; caller cannot pass hidden labels to this API."""
    outputs, fingerprints = [], []
    for challenge in challenges:
        row, keys = [], []
        for hypothesis in hypotheses:
            budget.consume('hypothesis_executions')
            try:
                predicted = execute(hypothesis, challenge.input, budget=budget)
                predicted = tuple(tuple(line) for line in predicted)
            except (ValueError, TypeError):
                predicted = None
            # Failed programs consume their attempted DSL work and a token.
            budget.consume('prediction_fingerprint_cells',
                           1 if predicted is None else sum(map(len, predicted)))
            row.append(predicted)
            keys.append(_digest(predicted))
        outputs.append(tuple(row))
        fingerprints.append(tuple(keys))
    return PredictionTable(tuple(challenges), tuple(outputs), tuple(fingerprints),
                           tuple(program_id(h) for h in hypotheses))


def choose_challenge(table, survivors, budget, *, mode, rng=None):
    """Return input index plus public scores; no teacher/oracle parameter."""
    if mode not in CONDITIONS or not table.challenges or not survivors:
        raise ValueError('nonempty pool, survivors and known condition required')
    if mode == 'sequential':
        budget.consume('selection_index')
        return 0, None
    if mode == 'random':
        if rng is None:
            raise ValueError('random condition requires an independent public RNG')
        budget.consume('selection_random_draw')
        return rng.randrange(len(table.challenges)), None
    scores = []
    for keys in table.fingerprints:
        counts = Counter()
        for h in survivors:
            budget.consume('selection_prediction_reads')
            counts[keys[h]] += 1
        # The number of unordered disagreeing pairs, without looking at truth.
        same = 0
        for count in counts.values():
            budget.consume('selection_histogram_bins')
            same += count * (count - 1) // 2
        budget.consume('selection_candidates')
        scores.append(len(survivors) * (len(survivors) - 1) // 2 - same)
    selected = 0
    for i in range(1, len(scores)):
        budget.consume('selection_rank_comparisons')
        if scores[i] > scores[selected]:
            selected = i
    return selected, scores


class _Teacher:
    """Evaluator-owned labels. No callable/reference is given to an actor."""
    def __init__(self, labels):
        self._labels = labels
        self._queried = set()

    def query(self, condition, round_index, challenge_id, budget):
        key = condition, round_index
        if (condition not in CONDITIONS or key in self._queried or
                (round_index, challenge_id) not in self._labels):
            raise ValueError('duplicate or non-acquisition teacher query')
        self._queried.add(key)
        budget.consume('teacher_queries')
        label = self._labels[round_index, challenge_id]
        budget.consume('teacher_label_cells', sum(map(len, label)))
        return tuple(tuple(cell for cell in row) for row in label)


def _learn(table, index, label, survivors, budget):
    """Compute a complete evidence compatibility vector, then intersect it.

    This is a table lookup/label comparison, never another execution of a
    program. Keeping the vector is the counterexample receipt for the finite
    grammar, including hypotheses rejected by earlier observations.
    """
    compatible = []
    for h, predicted in enumerate(table.predictions[index]):
        budget.consume('evidence_hypothesis_comparisons')
        if predicted is None or len(predicted) != len(label) or any(
                len(a) != len(b) for a, b in zip(predicted, label)):
            # Rotations of the square acquisition grids have equal dimensions.
            raise ValueError('grammar prediction shape violates acquisition contract')
        mismatches = 0
        for a, b in zip(predicted, label):
            for cell, truth in zip(a, b):
                budget.consume('evidence_cells')
                mismatches += cell != truth
        if not mismatches:
            compatible.append(h)
    result = []
    for h in survivors:
        budget.consume('survivor_intersections')
        if h in compatible:
            result.append(h)
    if not result:
        raise ValueError('teacher eliminated every hypothesis; instrument error')
    return result, compatible


def _predict(table, index, survivors, budget):
    outcomes = set()
    for h in survivors:
        budget.consume('consensus_prediction_reads')
        outcomes.add(table.fingerprints[index][h])
    prediction = table.predictions[index][survivors[0]] if len(outcomes) == 1 else None
    if prediction is not None:
        budget.consume('prediction_output_cells', sum(map(len, prediction)))
    return {'status': 'solved' if prediction is not None else 'ambiguous',
            'predictions': None if prediction is None else [[list(row) for row in prediction]],
            'test_verified': False}


def _add_work(*snapshots):
    counts = Counter()
    for snapshot in snapshots:
        counts.update(snapshot['counts'])
    return {'used': sum(counts.values()), 'counts': dict(sorted(counts.items()))}


def _event(journal, kind, **facts):
    if journal is not None:
        journal.write(kind=kind, **facts)


def _prepare(config, run_index):
    run_seed = _seed(config['seed'], config['phase'], 'run', run_index)
    hypotheses = grammar()
    witness = hypotheses[random.Random(_seed(run_seed, 'private-target')).randrange(len(hypotheses))]
    common = Budget(config['work_per_run'])
    common.consume('grammar_nodes', sum(1 + len(h['steps']) for h in hypotheses))
    common.consume('hypothesis_identities', len(hypotheses))
    pools, labels, cases, seen, repeated = [], {}, [], set(), 0
    for round_index in range(config['rounds']):
        challenges = []
        for index in range(config['pool_per_round']):
            challenge = _scene(_seed(run_seed, 'acquisition', round_index, index),
                               holdout=False, budget=common)
            # IID pools may repeat a public input. Keep and charge the draw;
            # neither silently resample nor pretend it is new evidence.
            repeated += challenge.id in seen
            seen.add(challenge.id)
            label = _label(challenge, witness, common)
            labels[round_index, challenge.id] = label
            challenges.append(challenge)
            cases.append({'id': challenge.id, 'split': 'acquisition', 'round': round_index,
                          'index': index, 'input': [list(row) for row in challenge.input],
                          'expected': [list(row) for row in label]})
        pools.append(prediction_table(challenges, hypotheses, common))
    acquisition_work = common.snapshot()
    evaluation = Budget(common.remaining)
    challenges, truths, evaluation_seen, evaluation_repeats = [], [], set(), 0
    for index in range(config['confirmation_cases_per_run']):
        challenge = _scene(_seed(run_seed, 'evaluation', index), holdout=True, budget=evaluation)
        if challenge.id in seen:
            raise ValueError('acquisition/evaluation input overlap')
        evaluation_repeats += challenge.id in evaluation_seen
        evaluation_seen.add(challenge.id)
        label = _label(challenge, witness, evaluation)
        challenges.append(challenge)
        truths.append([list(row) for row in label])
        cases.append({'id': challenge.id, 'split': 'evaluation', 'index': index,
                      'input': [list(row) for row in challenge.input],
                      'expected': [list(row) for row in label]})
    table = prediction_table(challenges, hypotheses, evaluation)
    common_work = _add_work(acquisition_work, evaluation.snapshot())
    if common_work['used'] > config['work_per_run']:
        raise BudgetExceeded('common preparation exceeds per-run allowance')
    return {'run_id': f'curriculum-{run_index:04d}', 'run_index': run_index,
            'run_seed': str(run_seed), 'witness': witness, 'hypotheses': hypotheses,
            'cases': cases, 'pools': pools, 'teacher': _Teacher(labels),
            'evaluation': table, 'truths': truths, 'common_work': common_work,
            'repeated_acquisition_inputs': repeated,
            'repeated_evaluation_inputs': evaluation_repeats,
            'common_acquisition_work': acquisition_work,
            'common_evaluation_work': evaluation.snapshot()}


def _run_pair(config, run_index, journal=None):
    prepared = _prepare(config, run_index)
    run_id, common = prepared['run_id'], prepared['common_work']
    rows, arms = [], {}
    hypothesis_ids = [program_id(h) for h in prepared['hypotheses']]
    witness = prepared['witness']
    family = (witness['steps'][0]['role'] + '_' + witness['steps'][0]['relation'] +
              '_recolor' + ('_' + witness['steps'][1]['op'] if len(witness['steps']) == 2 else ''))
    _event(journal, 'curriculum_prepared', run_id=run_id, family=family,
           verified_challenges=len(prepared['cases']), shared_work=common['used'])
    for condition in CONDITIONS:
        # The common table has already been paid for, never recomputed/padded.
        budget = Budget(config['work_per_run'] - common['used'])
        survivors, archive, prefixes = list(range(len(hypothesis_ids))), [], []
        acquisition_ledgers, evaluation_ledgers = [], []
        rng = random.Random(_seed(config['seed'], config['phase'], run_index, 'public-selection'))
        for round_index, table in enumerate(prepared['pools']):
            acquisition_budget = Budget(budget.remaining)
            before = list(survivors)
            selected, scores = choose_challenge(table, tuple(survivors), acquisition_budget,
                                                mode=condition, rng=rng)
            challenge = table.challenges[selected]
            _event(journal, 'curriculum_selection', run_id=run_id, condition=condition,
                   round=round_index, case_id=challenge.id, selected_index=selected,
                   disagreement_scores=scores, live_hypotheses=len(survivors))
            label = prepared['teacher'].query(condition, round_index, challenge.id, acquisition_budget)
            survivors, compatible = _learn(table, selected, label, survivors, acquisition_budget)
            acquisition_ledgers.append(acquisition_budget.snapshot())
            for kind, count in acquisition_budget.counts.items():
                budget.consume(kind, count)
            archive.append({'round': round_index, 'case_id': challenge.id,
                            'selected_index': selected, 'disagreement_scores': scores,
                            'before': before, 'compatible': compatible, 'after': list(survivors),
                            'queried_label': [list(row) for row in label],
                            'rejected': [h for h in before if h not in survivors]})
            _event(journal, 'curriculum_evidence', run_id=run_id, condition=condition,
                   round=round_index, case_id=challenge.id, survivors=list(survivors),
                   rejected=archive[-1]['rejected'], work=budget.used)
            prefix = round_index + 1
            frozen = _digest([hypothesis_ids[h] for h in survivors])
            for index, challenge in enumerate(prepared['evaluation'].challenges):
                ledger = Budget(budget.remaining)
                ledger.consume('evaluation_predictions')
                result = _predict(prepared['evaluation'], index, tuple(survivors), ledger)
                expected = [prepared['truths'][index]]
                # Labels and correctness belong to the evaluator. Neither is
                # an argument to the next selector or evidence update.
                ledger.consume('external_adjudications')
                success = exact_success(result, expected)
                for kind, count in ledger.counts.items():
                    budget.consume(kind, count)
                evaluation_ledgers.append(ledger.snapshot())
                row = {'id': challenge.id, 'run_id': run_id, 'run_index': run_index,
                       'prefix': prefix, 'query_index': index, 'condition': condition, 'family': family,
                       'result': result, 'expected': expected, 'success': success,
                       'work': ledger.snapshot(), 'hypotheses_sha256': frozen}
                rows.append(row)
                _event(journal, 'curriculum_external_result', run_id=run_id, condition=condition,
                       prefix=prefix, case_id=challenge.id, success=success,
                       status=result['status'], work=ledger.used)
            if frozen != _digest([hypothesis_ids[h] for h in survivors]):
                raise ValueError('prefix evaluation changed the learned hypothesis set')
            prefixes.append({'prefix': prefix, 'survivors': list(survivors),
                             'hypotheses_sha256': frozen,
                             'acquisition_work': _add_work(*acquisition_ledgers),
                             'evaluation_work': _add_work(*evaluation_ledgers),
                             'work': budget.snapshot(), 'total_work': common['used'] + budget.used})
        arms[condition] = {'archive': archive, 'survivors': survivors, 'prefixes': prefixes,
                           'hypotheses_sha256': frozen,
                           'acquisition_work': _add_work(*acquisition_ledgers),
                           'evaluation_work': _add_work(*evaluation_ledgers),
                           'work': budget.snapshot(),
                           'total_work': common['used'] + budget.used,
                           'opportunities': {
                               'acquisition_hypothesis_executions':
                                   prepared['common_acquisition_work']['counts'].get('hypothesis_executions', 0),
                               'evaluation_hypothesis_executions':
                                   prepared['common_evaluation_work']['counts'].get('hypothesis_executions', 0),
                               'private_hypothesis_executions': budget.counts.get('hypothesis_executions', 0),
                               'teacher_queries': budget.counts.get('teacher_queries', 0),
                               'evidence_hypothesis_comparisons':
                                   budget.counts.get('evidence_hypothesis_comparisons', 0),
                               'evidence_cells': budget.counts.get('evidence_cells', 0),
                               'evaluation_predictions': budget.counts.get('evaluation_predictions', 0),
                               'external_adjudications': budget.counts.get('external_adjudications', 0)}}
    record = {key: prepared[key] for key in ('run_id', 'run_index', 'run_seed', 'witness',
                                            'cases', 'common_work', 'common_acquisition_work',
                                            'common_evaluation_work', 'repeated_acquisition_inputs',
                                            'repeated_evaluation_inputs')}
    record.update(family=family, hypothesis_ids=hypothesis_ids, arms=arms)
    record['prediction_tables_sha256'] = _digest(
        [table.fingerprints for table in (*prepared['pools'], prepared['evaluation'])])
    record['physical_work'] = common['used'] + sum(arm['work']['used'] for arm in arms.values())
    return record, rows


def paired_uncertainty(accuracy_deltas, cost_deltas, *, seed, samples, relative_cost_deltas=None):
    """Resample whole run pairs, with common indices for accuracy and cost."""
    if not accuracy_deltas or len(accuracy_deltas) != len(cost_deltas):
        raise ValueError('nonempty paired run deltas required')
    if relative_cost_deltas is not None and len(relative_cost_deltas) != len(cost_deltas):
        raise ValueError('relative costs must have the same run pairs')
    if type(samples) is not int or samples < 2:
        raise ValueError('at least two bootstrap samples required')
    n = len(accuracy_deltas)
    rng = random.Random(seed)
    accuracy_bootstrap, cost_bootstrap, relative_bootstrap = [], [], []
    for _ in range(samples):
        indices = [rng.randrange(n) for _ in range(n)]
        accuracy_bootstrap.append(sum(accuracy_deltas[i] for i in indices) / n)
        cost_bootstrap.append(sum(cost_deltas[i] for i in indices) / n)
        if relative_cost_deltas is not None:
            relative_bootstrap.append(math.fsum(relative_cost_deltas[i] for i in indices) / n)
    def interval(values):
        values.sort()
        # Conservative order-statistic endpoints, deterministic without numpy.
        return [values[math.floor(.025 * (samples - 1))],
                values[math.ceil(.975 * (samples - 1))]]
    wins = sum(delta > 0 for delta in accuracy_deltas)
    losses = sum(delta < 0 for delta in accuracy_deltas)
    discordant = wins + losses
    p = (sum(math.comb(discordant, k) for k in range(wins, discordant + 1)) /
         2**discordant) if discordant else 1.0
    result = {'paired_runs': n, 'wins': wins, 'losses': losses, 'ties': n - wins - losses,
            'mean_accuracy_delta': sum(accuracy_deltas) / n,
            'accuracy_delta_ci95': interval(accuracy_bootstrap),
            'mean_total_work_delta': sum(cost_deltas) / n,
            'total_work_delta_ci95': interval(cost_bootstrap),
            'one_sided_sign_p': p, 'bootstrap_samples': samples,
            'unit': 'independent_acquisition_run'}
    if relative_cost_deltas is not None:
        result.update(mean_relative_total_work_overhead=math.fsum(relative_cost_deltas) / n,
                      relative_total_work_overhead_ci95=interval(relative_bootstrap),
                      maximum_relative_total_work_overhead=max(relative_cost_deltas))
    return result


def _summarize(config, runs, rows):
    # Success claims are deliberately ignored; the evaluator uses predictions.
    by_key = {(r['run_index'], r['condition'], r['prefix'], r['query_index']):
              exact_success(r['result'], r['expected']) for r in rows}
    prefixes = range(1, config['rounds'] + 1)
    queries = range(config['confirmation_cases_per_run'])
    expected = {(run['run_index'], condition, prefix, j)
                for run in runs for condition in CONDITIONS for prefix in prefixes for j in queries}
    if len(by_key) != len(rows) or set(by_key) != expected:
        raise ValueError('incomplete or duplicate prefix evaluation coverage')
    run_accuracies = {condition: [
        [sum(by_key[run['run_index'], condition, prefix, j] for j in queries) / len(queries)
         for prefix in prefixes] for run in runs] for condition in CONDITIONS}
    utilities = {condition: [math.fsum(curve) / config['rounds'] for curve in curves]
                 for condition, curves in run_accuracies.items()}
    totals, utility_totals, curves = {}, {}, []
    for condition in CONDITIONS:
        current = [row for row in rows if row['condition'] == condition and row['prefix'] == config['rounds']]
        successes = sum(exact_success(row['result'], row['expected']) for row in current)
        totals[condition] = {'successes': successes, 'cases': len(current),
                             'accuracy': successes / len(current),
                             'total_work': sum(run['arms'][condition]['total_work'] for run in runs),
                             'exclusive_work': sum(run['arms'][condition]['work']['used'] for run in runs)}
        utility_totals[condition] = {'mean_utility': math.fsum(utilities[condition]) / len(runs),
                                    'run_utilities': utilities[condition], 'paired_runs': len(runs)}
    for prefix in prefixes:
        curve = {'prefix': prefix, 'totals': {}, 'comparisons': {}}
        for condition in CONDITIONS:
            successes = sum(by_key[run['run_index'], condition, prefix, j] for run in runs for j in queries)
            count = len(runs) * len(queries)
            curve['totals'][condition] = {
                'successes': successes, 'cases': count, 'accuracy': successes / count,
                'run_accuracies': [values[prefix - 1] for values in run_accuracies[condition]],
                'total_work': sum(run['arms'][condition]['prefixes'][prefix - 1]['total_work'] for run in runs),
                'exclusive_work': sum(run['arms'][condition]['prefixes'][prefix - 1]['work']['used'] for run in runs)}
        for condition in CONDITIONS[:2]:
            pairs = [(by_key[run['run_index'], condition, prefix, j],
                      by_key[run['run_index'], 'adaptive', prefix, j]) for run in runs for j in queries]
            curve['comparisons']['adaptive_vs_' + condition] = {
                'mean_accuracy_delta': sum(b - a for a, b in pairs) / len(pairs),
                'case_regressions': sum(a and not b for a, b in pairs),
                'case_gains': sum(b and not a for a, b in pairs)}
        curves.append(curve)
    comparisons, utility_comparisons = {}, {}
    for condition in CONDITIONS[:2]:
        deltas, costs, relative_costs, regressions, gains = [], [], [], 0, 0
        for run in runs:
            i = run['run_index']
            control = [by_key[i, condition, config['rounds'], j] for j in queries]
            adaptive = [by_key[i, 'adaptive', config['rounds'], j] for j in queries]
            regressions += sum(a and not b for a, b in zip(control, adaptive))
            gains += sum(b and not a for a, b in zip(control, adaptive))
            deltas.append((sum(adaptive) - sum(control)) / len(control))
            costs.append(run['arms']['adaptive']['total_work'] - run['arms'][condition]['total_work'])
            relative_costs.append(costs[-1] / run['arms'][condition]['total_work'])
        comparison = paired_uncertainty(deltas, costs, seed=_seed(config['seed'], 'bootstrap', condition),
                                        samples=config['bootstrap_samples'], relative_cost_deltas=relative_costs)
        comparison.update(case_regressions=regressions, case_gains=gains,
                          accuracy_deltas=deltas, total_work_deltas=costs,
                          relative_total_work_overheads=relative_costs)
        comparisons['adaptive_vs_' + condition] = comparison
        utility_deltas = [a - b for a, b in zip(utilities['adaptive'], utilities[condition])]
        utility_comparison = paired_uncertainty(
            utility_deltas, costs, seed=_seed(config['seed'], 'bootstrap', condition),
            samples=config['bootstrap_samples'], relative_cost_deltas=relative_costs)
        utility_comparison['mean_utility_delta'] = utility_comparison.pop('mean_accuracy_delta')
        utility_comparison['utility_delta_ci95'] = utility_comparison.pop('accuracy_delta_ci95')
        prefix_comparisons = [curve['comparisons']['adaptive_vs_' + condition] for curve in curves]
        utility_comparison.update(
            utility_deltas=utility_deltas, total_work_deltas=costs,
            relative_total_work_overheads=relative_costs,
            prefix_case_regressions=sum(c['case_regressions'] for c in prefix_comparisons),
            prefix_case_regressions_by_prefix=[c['case_regressions'] for c in prefix_comparisons],
            prefix_case_gains=sum(c['case_gains'] for c in prefix_comparisons))
        utility_comparisons['adaptive_vs_' + condition] = utility_comparison
    return {'totals': totals, 'comparisons': comparisons, 'final_gain_descriptive_only': True,
            'primary_endpoint': 'mean_prefix_accuracy', 'curves': curves,
            'utility_totals': utility_totals, 'utility_comparisons': utility_comparisons,
            'common_work': sum(run['common_work']['used'] for run in runs),
            'physical_work': sum(run['physical_work'] for run in runs),
            'verified_challenges': sum(len(run['cases']) for run in runs),
            'repeated_acquisition_inputs': sum(run['repeated_acquisition_inputs'] for run in runs),
            'repeated_evaluation_inputs': sum(run['repeated_evaluation_inputs'] for run in runs),
            'paired_runs': len(runs), 'llm_calls': 0,
            'scope': _contract()['scope'], 'official_arc_score': None, 's6_green': False}


def _gates(config, runs, summary):
    limits = _contract()['acceptance']
    random_comparison = summary['utility_comparisons']['adaptive_vs_random']
    comparisons = list(summary['utility_comparisons'].values())
    final_comparisons = list(summary['comparisons'].values())
    expected = {'acquisition_hypothesis_executions': config['rounds'] * config['pool_per_round'] * 16,
                'evaluation_hypothesis_executions': config['confirmation_cases_per_run'] * 16,
                'private_hypothesis_executions': 0, 'teacher_queries': config['rounds'],
                'evidence_hypothesis_comparisons': config['rounds'] * 16,
                'evidence_cells': config['rounds'] * 16 * 225,
                'evaluation_predictions': config['rounds'] * config['confirmation_cases_per_run'],
                'external_adjudications': config['rounds'] * config['confirmation_cases_per_run']}
    gates = {
        'confirmation_protocol': config['phase'] == 'confirmation' and config == default_config(),
        'minimum_independent_runs': (len(runs) >= limits['minimum_paired_runs'] and
                                     len({run['run_seed'] for run in runs}) == len(runs)),
        'matched_actual_scoring_and_evidence': all(arm['opportunities'] == expected
                                                 for run in runs for arm in run['arms'].values()),
        'every_prefix_evaluated': len(summary['curves']) == config['rounds'] and all(
            curve['prefix'] == prefix and all(
                curve['totals'][condition]['cases'] == len(runs) * config['confirmation_cases_per_run']
                for condition in CONDITIONS) for prefix, curve in enumerate(summary['curves'], 1)),
        'all_challenges_verified_solvable': summary['verified_challenges'] == len(runs) * (
            config['rounds'] * config['pool_per_round'] + config['confirmation_cases_per_run']),
        'within_work_limit': all(arm['total_work'] <= config['work_per_run']
                                 for run in runs for arm in run['arms'].values()),
        'adaptive_final_accuracy': summary['totals']['adaptive']['accuracy'] >= limits['minimum_adaptive_final_accuracy'],
        'meaningful_utility_gain_vs_random': random_comparison['mean_utility_delta'] >=
                                            limits['minimum_mean_paired_utility_gain_vs_random'],
        'multiple_independent_wins': random_comparison['wins'] >= limits['minimum_winning_runs_vs_random'],
        'no_prefix_case_regressions_vs_random': random_comparison['prefix_case_regressions'] <=
                                               limits['maximum_prefix_case_regressions_vs_random'],
        'no_final_case_regressions': all(c['case_regressions'] <= limits['maximum_final_case_regressions_vs_either_control']
                                        for c in final_comparisons),
        'no_final_run_regressions': all(c['losses'] <= limits['maximum_final_losing_runs_vs_either_control']
                                       for c in final_comparisons),
        'paired_uncertainty_positive': random_comparison['utility_delta_ci95'][0] >
                                       limits['paired_mean_gain_ci_lower_exclusive'],
        'paired_sign_test': random_comparison['one_sided_sign_p'] <= limits['paired_sign_test_one_sided_maximum_p'],
        'sequential_noninferiority': summary['utility_comparisons']['adaptive_vs_sequential']['mean_utility_delta'] >=
                                     limits['minimum_mean_paired_utility_gain_vs_sequential'],
        'bounded_total_cost_overhead': all(
            c['mean_relative_total_work_overhead'] <= limits['maximum_mean_relative_total_work_overhead'] and
            c['relative_total_work_overhead_ci95'][1] <= limits['maximum_relative_total_work_overhead_ci_upper'] and
            c['maximum_relative_total_work_overhead'] <= limits['maximum_relative_total_work_overhead_per_run']
            for c in comparisons),
        'no_llm': summary['llm_calls'] == 0,
    }
    # Independent replay is a separate required receipt, never self-attested.
    return {**gates, 'scientific_success': all(gates.values()),
            'independent_audit_required': True, 'promotion': False}


def run_benchmark(config, journal=None):
    """Produce deterministic receipts; fail closed on instrument/budget errors.

    Scientific failures are normal returned gates. Instrument failures raise;
    the parent should preserve its exception/trace receipt and never substitute
    a smaller denominator. This function never runs tests or external services.
    """
    config = _config(config)
    sources = _sources()
    contract_sha256 = _digest(_contract())
    runs, rows = [], []
    try:
        for index in range(config['paired_runs']):
            record, current = _run_pair(config, index, journal)
            runs.append(record)
            rows.extend(current)
    except (BudgetExceeded, ValueError) as exc:
        _event(journal, 'curriculum_instrument_error', completed_pairs=len(runs), error=str(exc))
        raise
    summary = _summarize(config, runs, rows)
    if sources != _sources() or contract_sha256 != _digest(_contract()):
        raise ValueError('curriculum sources or contract changed during measurement')
    return {'schema': SCHEMA, 'config': config, 'contract_sha256': contract_sha256,
            'sources': sources,
            'grammar': grammar(), 'rows': rows, 'runs': runs, 'summary': summary,
            'gates': _gates(config, runs, summary)}


def audit_report(report):
    """Independent outputs first, then deterministic acquisition/ledger replay.

    Does not call run_benchmark or trust success booleans, embedded expected
    labels, costs, hashes, summary, or gates. Exact identity/coverage checks
    reject missing/duplicated rows and unexpected fields through replay.
    """
    try:
        if type(report) is not dict or set(report) != {
                'schema', 'config', 'contract_sha256', 'sources', 'grammar', 'rows', 'runs', 'summary', 'gates'}:
            raise ValueError('report envelope mismatch')
        if report['schema'] != SCHEMA or report['contract_sha256'] != _digest(_contract()):
            raise ValueError('schema/contract identity mismatch')
        if report['sources'] != _sources():
            raise ValueError('source identity mismatch')
        config = _config(report['config'])
        if report['grammar'] != grammar():
            raise ValueError('grammar identity mismatch')
        if len(report['runs']) != config['paired_runs'] or len(report['rows']) != (
                config['paired_runs'] * len(CONDITIONS) * config['rounds'] * config['confirmation_cases_per_run']):
            raise ValueError('missing or extra runs/rows')
        identities, replay_runs, replay_rows = set(), [], []
        for index in range(config['paired_runs']):
            run, rows = _run_pair(config, index)
            replay_runs.append(run)
            replay_rows.extend(rows)
            # Independent truth is derived from regenerated public inputs and
            # the private witness, not the producer's expected output field.
            queries = {c['index']: c for c in run['cases'] if c['split'] == 'evaluation'}
            start = index * len(CONDITIONS) * config['rounds'] * config['confirmation_cases_per_run']
            current = report['rows'][start:start + len(rows)]
            for claimed in current:
                key = claimed['run_index'], claimed['condition'], claimed['prefix'], claimed['query_index']
                if (key in identities or type(claimed['run_index']) is not int or claimed['run_index'] != index or
                        claimed['condition'] not in CONDITIONS or type(claimed['prefix']) is not int or
                        not 1 <= claimed['prefix'] <= config['rounds'] or type(claimed['query_index']) is not int or
                        not 0 <= claimed['query_index'] < config['confirmation_cases_per_run']):
                    raise ValueError('duplicate or misplaced row identity')
                identities.add(key)
                query = queries[claimed['query_index']]
                truth = [_oracle(query['input'], run['witness'])]
                if claimed['id'] != query['id'] or claimed['expected'] != truth:
                    raise ValueError('case or expected-output tampering')
                prefix_state = run['arms'][claimed['condition']]['prefixes'][claimed['prefix'] - 1]
                if claimed['hypotheses_sha256'] != prefix_state['hypotheses_sha256']:
                    raise ValueError('prefix hypothesis-state mismatch')
                if (type(claimed['success']) is not bool or claimed['success'] !=
                        exact_success(claimed['result'], truth) or claimed['result']['test_verified'] is not False):
                    raise ValueError('external success or actor authority mismatch')
        if _digest(report['runs']) != _digest(replay_runs) or _digest(report['rows']) != _digest(replay_rows):
            raise ValueError('deterministic replay mismatch (outputs, selection, evidence or work)')
        summary = _summarize(config, replay_runs, report['rows'])
        gates = _gates(config, replay_runs, summary)
        if _digest(report['summary']) != _digest(summary) or _digest(report['gates']) != _digest(gates):
            raise ValueError('summary or gate tampering')
        if report['sources'] != _sources() or report['contract_sha256'] != _digest(_contract()):
            raise ValueError('sources or contract changed during audit')
        return {'schema': 'echo5-curriculum-audit-v2', 'valid': True,
                'deterministic_replay': True, 'independent_output_adjudication': True,
                'paired_runs': len(replay_runs), 'rows': len(replay_rows),
                'prefixes_per_run': config['rounds'], 'primary_endpoint': 'mean_prefix_accuracy',
                'report_sha256': _digest(report), 'summary': summary, 'gates': gates,
                'closure_success': gates['scientific_success']}
    except (KeyError, IndexError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError('malformed curriculum report') from exc
