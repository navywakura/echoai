"""Lazy, per-arm curriculum cost comparison; no contract/artifact reads.

Only public input generation is shared. Prediction caches belong to one arm,
and the phase requesting a missing prediction pays for its real execution.
The default reuses the old selector, full evidence filter and consensus.
An opt-in comparison adds bounded selection and survivor-only evidence work;
all arms still use the original unanimous heldout prediction semantics.
This exploratory instrument does not modify or certify the closed curriculum.
"""

from collections import Counter
from collections.abc import Sequence
import copy
import json
import math
import random

from . import curriculum as c
from .budget import Budget, BudgetExceeded
from .evaluation import exact_success


SCHEMA = 'echo5-curriculum-lazy-v1'
EFFICIENT_SCHEMA = 'echo5-curriculum-efficient-v1'
CONDITIONS = c.CONDITIONS
EFFICIENT_CONDITIONS = (*CONDITIONS, 'adaptive_efficient')
POOL_SIZE = 6
HELDOUT_CASES = 8
BOOTSTRAP_SAMPLES = 512
LEARNING_PHASES = ('preparation', 'selection', 'acquisition', 'update')
PHASES = (*LEARNING_PHASES, 'heldout_evaluation')


class _Row(Sequence):
    def __init__(self, table, index, budget, field):
        self.table, self.index, self.budget, self.field = table, index, budget, field

    def __len__(self):
        return len(self.table.hypotheses)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(self[i] for i in range(*index.indices(len(self))))
        index = range(len(self))[index]  # Bounds check before any charged work.
        return self.table.get(self.index, index, self.budget)[self.field]


class _Rows(Sequence):
    def __init__(self, table, budget, field):
        self.table, self.budget, self.field = table, budget, field

    def __len__(self):
        return len(self.table.challenges)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(self[i] for i in range(*index.indices(len(self))))
        index = range(len(self))[index]
        return _Row(self.table, index, self.budget, self.field)


class _LazyTable:
    """Public-input-only adapter; cache keys are (pool position, hypothesis).

    A view does no prediction work. Reading a cell executes it at most once
    in this table, charges the supplied budget and retains the paid result.
    Failed executions retain their costs and are cached just like old None
    predictions. BudgetExceeded is never converted into a prediction failure.
    Repeated grid IDs at different positions remain distinct paid draws.
    """
    def __init__(self, challenges, hypotheses, hypothesis_ids):
        self.challenges = tuple(challenges)
        self.hypotheses = tuple(hypotheses)
        self.hypothesis_ids = tuple(hypothesis_ids)
        self._cache = {}

    def get(self, index, hypothesis, budget):
        key = index, hypothesis
        budget.consume('prediction_cache_lookups')
        if key not in self._cache:
            budget.consume('hypothesis_executions')
            try:
                predicted = c.execute(self.hypotheses[hypothesis],
                                      self.challenges[index].input, budget=budget)
                predicted = tuple(tuple(row) for row in predicted)
            except (ValueError, TypeError):
                predicted = None
            budget.consume('prediction_fingerprint_cells',
                           1 if predicted is None else sum(map(len, predicted)))
            fingerprint = c._digest(predicted)
            budget.consume('prediction_cache_stores')
            self._cache[key] = predicted, fingerprint
        return self._cache[key]

    def view(self, budget):
        # These read-only sequences implement exactly the accesses used by the
        # original functions; no exhaustive arrays or labels are constructed.
        return c.PredictionTable(self.challenges, _Rows(self, budget, 0),
                                 _Rows(self, budget, 1), self.hypothesis_ids)


def choose_challenge_efficient(table, survivors, budget):
    """Preserve exhaustive adaptive argmax, executing only a needed prefix.

    One survivor implies no possible disagreement; choose index zero without
    prediction reads. Otherwise fully score each candidate until its score
    reaches S*(S-1)//2. No later candidate can beat that bound, and the old
    tie break keeps the first index. None scores mean unmeasured, not zero.
    Only the public table and live hypothesis indices enter this policy.
    """
    if not table.challenges or not survivors:
        raise ValueError('nonempty pool and survivors required')
    budget.consume('selection_survivor_checks')
    budget.consume('selection_score_slots', len(table.challenges))
    scores = [None] * len(table.challenges)
    if len(survivors) == 1:
        budget.consume('selection_index')
        return 0, scores
    budget.consume('selection_discrimination_bounds')
    maximum = len(survivors) * (len(survivors) - 1) // 2
    selected = 0
    for index, keys in enumerate(table.fingerprints):
        counts = Counter()
        for h in survivors:
            budget.consume('selection_prediction_reads')
            counts[keys[h]] += 1
        same = 0
        for count in counts.values():
            budget.consume('selection_histogram_bins')
            same += count * (count - 1) // 2
        budget.consume('selection_candidates')
        scores[index] = maximum - same
        if index:
            budget.consume('selection_rank_comparisons')
            if scores[index] > scores[selected]:
                selected = index
        budget.consume('selection_bound_checks')
        if scores[index] == maximum:
            break
    return selected, scores


def _learn_survivors(table, index, label, survivors, budget):
    """Intersect only entering survivors; return nullable compatibility.

    An earlier counterexample permanently removes a hypothesis from this
    monotone version space. Its compatibility with a new label is unknown
    unless executed here; None must never become a fabricated False/True.
    Shape validation and full-cell comparisons match the original filter.
    """
    if not survivors:
        raise ValueError('nonempty survivors required')
    budget.consume('evidence_compatibility_slots', len(table.hypothesis_ids))
    compatibility = [None] * len(table.hypothesis_ids)
    result = []
    for h in survivors:
        predicted = table.predictions[index][h]
        budget.consume('evidence_hypothesis_comparisons')
        if predicted is None or len(predicted) != len(label) or any(
                len(a) != len(b) for a, b in zip(predicted, label)):
            raise ValueError('grammar prediction shape violates acquisition contract')
        mismatches = 0
        for a, b in zip(predicted, label):
            for cell, truth in zip(a, b):
                budget.consume('evidence_cells')
                mismatches += cell != truth
        compatibility[h] = not mismatches
        budget.consume('survivor_intersections')
        if not mismatches:
            result.append(h)
    if not result:
        raise ValueError('teacher eliminated every hypothesis; instrument error')
    return result, compatibility


class _Phase:
    """Charge one shared arm allowance and one disjoint phase counter."""
    def __init__(self, allowance):
        self.allowance = allowance
        self.counts = Counter()

    def consume(self, kind, amount=1):
        self.allowance.consume(kind, amount)
        self.counts[kind] += amount

    add = consume

    @property
    def remaining(self):
        return self.allowance.remaining

    @property
    def used(self):
        return sum(self.counts.values())

    def snapshot(self):
        return {'used': self.used, 'counts': dict(sorted(self.counts.items()))}


def _event(journal, kind, **facts):
    if journal is not None:
        # An observer may retain or mutate its arguments, never the learner.
        journal.write(kind=kind, **copy.deepcopy(facts))


def _family(witness):
    step = witness['steps'][0]
    suffix = '_' + witness['steps'][1]['op'] if len(witness['steps']) == 2 else ''
    return step['role'] + '_' + step['relation'] + '_recolor' + suffix


def _config(seed, runs, acquisition_steps, budget, efficient=False):
    values = dict(seed=seed, runs=runs, acquisition_steps=acquisition_steps, budget=budget)
    bounds = {'seed': (0, 2**63 - 1), 'runs': (1, 256),
              'acquisition_steps': (1, 8), 'budget': (1, 10**10)}
    for name, (low, high) in bounds.items():
        if type(values[name]) is not int or not low <= values[name] <= high:
            raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    if type(efficient) is not bool:
        raise ValueError('efficient must be a boolean')
    if efficient:
        values['efficient'] = True
    return {**values, 'pool_size': POOL_SIZE, 'heldout_cases': HELDOUT_CASES,
            'bootstrap_samples': BOOTSTRAP_SAMPLES}


def _prepare(config, run_index):
    # A new namespace cannot accidentally reopen the old confirmation cohort.
    run_seed = c._seed(config['seed'], SCHEMA, 'run', run_index)
    preparation = Budget(config['budget'])
    hypotheses = c.grammar()
    preparation.consume('grammar_nodes', sum(1 + len(h['steps']) for h in hypotheses))
    preparation.consume('hypothesis_identities', len(hypotheses))
    ids = tuple(c.program_id(h) for h in hypotheses)
    preparation.consume('private_target_draws')
    witness = hypotheses[random.Random(c._seed(run_seed, 'private-target')).randrange(len(hypotheses))]
    pools, seen, repetitions = [], set(), 0
    for step in range(config['acquisition_steps']):
        pool = []
        for index in range(POOL_SIZE):
            challenge = c._scene(c._seed(run_seed, 'acquisition', step, index),
                                 holdout=False, budget=preparation)
            repetitions += challenge.id in seen
            seen.add(challenge.id)
            pool.append(challenge)
        pools.append(tuple(pool))
    evaluation = Budget(preparation.remaining)
    heldout, truths, heldout_seen, heldout_repetitions = [], [], set(), 0
    for index in range(HELDOUT_CASES):
        challenge = c._scene(c._seed(run_seed, 'evaluation', index), holdout=True, budget=evaluation)
        if challenge.id in seen:
            raise ValueError('acquisition/heldout input overlap')
        heldout_repetitions += challenge.id in heldout_seen
        heldout_seen.add(challenge.id)
        heldout.append(challenge)
        truths.append(c._label(challenge, witness, evaluation))
    return {'run_index': run_index, 'run_seed': str(run_seed), 'hypotheses': hypotheses,
            'hypothesis_ids': ids, 'witness': witness, 'family': _family(witness),
            'pools': tuple(pools), 'heldout': tuple(heldout), 'truths': truths,
            'preparation': c._add_work(preparation.snapshot()),
            'heldout_preparation': c._add_work(evaluation.snapshot()),
            'repeated_acquisition_inputs': repetitions,
            'repeated_heldout_inputs': heldout_repetitions}


def _cost(prepared, phases):
    result = {name: phase.snapshot() for name, phase in phases.items()}
    result['exclusive'] = c._add_work(*result.values())
    result['preparation'] = prepared['preparation']
    result['heldout_evaluation'] = c._add_work(prepared['heldout_preparation'],
                                              result['heldout_evaluation'])
    result['learning'] = c._add_work(*(result[name] for name in LEARNING_PHASES))
    result['total'] = c._add_work(result['learning'], result['heldout_evaluation'])
    return result


def _run_arm(config, prepared, condition, journal):
    efficient = config.get('efficient', False)
    if condition not in (EFFICIENT_CONDITIONS if efficient else CONDITIONS):
        raise ValueError('unknown curriculum condition')
    survivor_update = efficient and condition != 'adaptive'
    common = c._add_work(prepared['preparation'], prepared['heldout_preparation'])
    if common['used'] > config['budget']:
        raise BudgetExceeded('shared input preparation exceeds the arm allowance')
    allowance = Budget(config['budget'] - common['used'])
    phases = {name: _Phase(allowance) for name in PHASES if name != 'preparation'}
    hypotheses, ids = prepared['hypotheses'], prepared['hypothesis_ids']
    survivors, archive, prefixes = list(range(len(ids))), [], []
    rng = random.Random(c._seed(config['seed'], SCHEMA, prepared['run_index'], 'public-selection'))
    for step, pool in enumerate(prepared['pools']):
        # New cache each round and each arm: no free work from another actor.
        table = _LazyTable(pool, hypotheses, ids)
        before = list(survivors)
        selection, acquisition, update = (phases[name] for name in ('selection', 'acquisition', 'update'))
        if condition == 'adaptive_efficient':
            index, scores = choose_challenge_efficient(table.view(selection), tuple(survivors), selection)
        else:
            index, scores = c.choose_challenge(table.view(selection), tuple(survivors),
                                               selection, mode=condition, rng=rng)
        challenge = pool[index]
        _event(journal, 'curriculum_lazy_selection', run_index=prepared['run_index'],
               condition=condition, step=step, case_id=challenge.id, selected_index=index,
               disagreement_scores=scores, live_hypotheses=len(survivors))
        # This evaluator-owned teacher executes only after selection. It is
        # never an argument to the selector or the public prediction table.
        acquisition.consume('teacher_queries')
        label = c._label(challenge, prepared['witness'], acquisition)
        acquisition.consume('teacher_label_cells', sum(map(len, label)))
        label = tuple(tuple(cell for cell in row) for row in label)
        if survivor_update:
            survivors, compatibility = _learn_survivors(table.view(update), index, label, survivors, update)
            compatible = list(survivors)
        else:
            survivors, compatible = c._learn(table.view(update), index, label, survivors, update)
        record = {'step': step, 'case_id': challenge.id, 'selected_index': index,
                  'disagreement_scores': scores, 'before': before, 'compatible': compatible,
                  'after': list(survivors), 'queried_label': [list(row) for row in label],
                  'rejected': [h for h in before if h not in survivors]}
        if survivor_update:
            record.update(compatibility_scope='entering_survivors', compatibility=compatibility)
        archive.append(record)
        _event(journal, 'curriculum_lazy_evidence', run_index=prepared['run_index'],
               condition=condition, step=step, case_id=challenge.id, survivors=survivors,
               rejected=record['rejected'], learning_cost=_cost(prepared, phases)['learning'])
        prefixes.append({'prefix': step + 1, 'survivors': list(survivors),
                         'hypotheses_sha256': c._digest([ids[h] for h in survivors]),
                         'learning_cost': _cost(prepared, phases)['learning']})

    # Evaluate saved states only after acquisition is complete. This private
    # heldout cache cannot be read by any acquisition selector or update.
    table = _LazyTable(prepared['heldout'], hypotheses, ids)
    evaluation = phases['heldout_evaluation']
    for prefix in prefixes:
        current = []
        for index, challenge in enumerate(prepared['heldout']):
            before = evaluation.counts.copy()
            evaluation.consume('evaluation_predictions')
            result = c._predict(table.view(evaluation), index, tuple(prefix['survivors']), evaluation)
            expected = [[list(row) for row in prepared['truths'][index]]]
            evaluation.consume('external_adjudications')
            success = exact_success(result, expected)
            delta = evaluation.counts - before
            current.append({'id': challenge.id, 'query_index': index, 'result': result,
                            'expected': expected, 'success': success,
                            'work': {'used': sum(delta.values()), 'counts': dict(sorted(delta.items()))}})
            _event(journal, 'curriculum_lazy_external_result', run_index=prepared['run_index'],
                   condition=condition, prefix=prefix['prefix'], case_id=challenge.id,
                   success=success, status=result['status'])
        prefix['evaluations'] = current
        prefix['accuracy'] = sum(row['success'] for row in current) / len(current)
    cost = _cost(prepared, phases)
    counts = cost['total']['counts']
    opportunities = {name: counts.get(name, 0) for name in (
        'teacher_queries', 'evidence_hypothesis_comparisons', 'evidence_cells',
        'evaluation_predictions', 'external_adjudications')}
    steps = config['acquisition_steps']
    comparisons = sum(len(r['before']) for r in archive) if survivor_update else steps * len(ids)
    if opportunities != {'teacher_queries': steps, 'evidence_hypothesis_comparisons': comparisons,
                          'evidence_cells': comparisons * 225,
                          'evaluation_predictions': steps * HELDOUT_CASES,
                          'external_adjudications': steps * HELDOUT_CASES}:
        raise ValueError('unmatched acquisition/evaluation opportunities')
    return {'run_index': prepared['run_index'], 'condition': condition, 'family': prepared['family'],
            'hypothesis_ids': list(ids), 'task_ids': {
                'acquisition': [[q.id for q in pool] for pool in prepared['pools']],
                'heldout': [q.id for q in prepared['heldout']]},
            'archive': archive, 'survivors': list(survivors), 'prefixes': prefixes,
            'mean_prefix_accuracy': math.fsum(p['accuracy'] for p in prefixes) / steps,
            'final_accuracy': prefixes[-1]['accuracy'], 'opportunities': opportunities, 'cost': cost}


def _audit_labels(prepared, results, limit):
    """All-input witness checks, including unselected candidates; no learning.

    This is producer-side validation, not the separate full report replay.
    Its work cannot dilute any learner's cost comparison or fund its budget.
    """
    work = Budget(limit)
    verified = 0
    for step, pool in enumerate(prepared['pools']):
        for index, challenge in enumerate(pool):
            truth = c._label(challenge, prepared['witness'], work)
            verified += 1
            for result in results:
                receipt = result['archive'][step]
                if receipt['selected_index'] == index:
                    work.consume('audit_label_comparisons')
                    if receipt['queried_label'] != [list(row) for row in truth]:
                        raise ValueError('acquired label disagrees with audit renderer')
    for index, challenge in enumerate(prepared['heldout']):
        truth = c._label(challenge, prepared['witness'], work)
        verified += 1
        expected = [[list(row) for row in truth]]
        for result in results:
            for prefix in result['prefixes']:
                row = prefix['evaluations'][index]
                work.consume('audit_label_comparisons')
                work.consume('audit_adjudications')
                if (row['expected'] != expected or row['result']['test_verified'] is not False or
                        row['success'] != c.exact_success(row['result'], expected)):
                    raise ValueError('heldout receipt disagrees with external audit')
    return {'work': c._add_work(work.snapshot()), 'verified_challenges': verified}


def _pair_rows(results, control, adaptive='adaptive'):
    by_run = {}
    for result in results:
        by_run.setdefault(result['run_index'], {})[result['condition']] = result
    rows = []
    for index, arms in sorted(by_run.items()):
        a, b = arms[adaptive], arms[control]
        regressions, gains = [], []
        for ap, bp in zip(a['prefixes'], b['prefixes']):
            regressions.append(sum(br['success'] and not ar['success']
                                   for ar, br in zip(ap['evaluations'], bp['evaluations'])))
            gains.append(sum(ar['success'] and not br['success']
                             for ar, br in zip(ap['evaluations'], bp['evaluations'])))
        delta = a['cost']['learning']['used'] - b['cost']['learning']['used']
        rows.append({'run_index': index, 'family': a['family'],
                     'utility_delta': a['mean_prefix_accuracy'] - b['mean_prefix_accuracy'],
                     'final_accuracy_delta': a['final_accuracy'] - b['final_accuracy'],
                     'learning_cost_delta': delta,
                     'relative_learning_cost_delta': delta / b['cost']['learning']['used'],
                     'total_cost_delta': a['cost']['total']['used'] - b['cost']['total']['used'],
                     'phase_cost_deltas': {p: a['cost'][p]['used'] - b['cost'][p]['used'] for p in PHASES},
                     'prefix_case_regressions': regressions, 'prefix_case_gains': gains,
                     'final_case_regressions': regressions[-1]})
    return rows


def _comparisons(conditions):
    pairs = [('adaptive', control) for control in CONDITIONS[:2]]
    if 'adaptive_efficient' in conditions:
        pairs.extend(('adaptive_efficient', control) for control in CONDITIONS)
    return pairs


def _pairs(results, seed, conditions=CONDITIONS):
    comparisons = {}
    if not results:
        return comparisons
    for adaptive, control in _comparisons(conditions):
        pairs = _pair_rows(results, control, adaptive)
        bootstrap_seed = (c._seed(seed, SCHEMA, 'bootstrap', control) if adaptive == 'adaptive'
                          else c._seed(seed, EFFICIENT_SCHEMA, 'bootstrap', adaptive, control))
        summary = c.paired_uncertainty(
            [p['utility_delta'] for p in pairs], [p['learning_cost_delta'] for p in pairs],
            relative_cost_deltas=[p['relative_learning_cost_delta'] for p in pairs],
            seed=bootstrap_seed, samples=BOOTSTRAP_SAMPLES)
        # Explicitly rename the inherited generic fields: this denominator is
        # learning only, never shared heldout work, auditing or unused budget.
        for old, new in (
                ('mean_accuracy_delta', 'mean_utility_delta'),
                ('accuracy_delta_ci95', 'utility_delta_ci95'),
                ('mean_total_work_delta', 'mean_learning_cost_delta'),
                ('total_work_delta_ci95', 'learning_cost_delta_ci95'),
                ('mean_relative_total_work_overhead', 'mean_relative_learning_cost_delta'),
                ('relative_total_work_overhead_ci95', 'relative_learning_cost_delta_ci95'),
                ('maximum_relative_total_work_overhead', 'maximum_relative_learning_cost_delta')):
            summary[new] = summary.pop(old)
        summary.update(run_pairs=pairs, intervals_descriptive_only=True,
                       mean_final_accuracy_delta=math.fsum(p['final_accuracy_delta'] for p in pairs) / len(pairs),
                       mean_total_cost_delta=math.fsum(p['total_cost_delta'] for p in pairs) / len(pairs),
                       observed_mean_cost_saving=summary['mean_learning_cost_delta'] < 0)
        comparisons[adaptive + '_vs_' + control] = summary
    return comparisons


def _family_summary(results, conditions=CONDITIONS):
    families = {}
    for witness in c.grammar():
        family = _family(witness)
        current = [r for r in results if r['family'] == family]
        arms = {}
        for condition in conditions:
            selected = [r for r in current if r['condition'] == condition]
            n = len(selected)
            final = [row for r in selected for row in r['prefixes'][-1]['evaluations']]
            arms[condition] = {
                'runs': n, 'cases': len(final), 'successes': sum(row['success'] for row in final),
                'abstentions': sum(row['result']['status'] == 'ambiguous' for row in final),
                'incorrect_answers': sum(row['result']['status'] == 'solved' and not row['success'] for row in final),
                'final_accuracy': math.fsum(r['final_accuracy'] for r in selected) / n if n else None,
                'mean_prefix_accuracy': math.fsum(r['mean_prefix_accuracy'] for r in selected) / n if n else None,
                'cost': {p: c._add_work(*(r['cost'][p] for r in selected)) for p in (*PHASES, 'learning', 'total')}}
        families[family] = {'paired_runs': len(current) // len(conditions), 'arms': arms,
                            'pairs': {adaptive + '_vs_' + control: _pair_rows(current, control, adaptive)
                                      for adaptive, control in _comparisons(conditions)}}
    return families


def run_benchmark(*, seed=4_400_000, runs=4, acquisition_steps=4, budget=2_000_000,
                  journal=None, efficient=False):
    """Return deterministic JSON data; raise on instrument/budget failure.

    ``budget`` is an equal standalone-equivalent ceiling per arm, including
    heldout evaluation. The separate all-input audit has the same ceiling per
    paired run. Logical counts are not seconds. Optional ``journal`` uses the
    existing Recorder.write protocol and has no influence on returned data.
    BudgetExceeded is logged distinctly as resource exhaustion and re-raised;
    callers must not classify it as a broken instrument or a completed study.

    The default retains the complete lazy-v1 receipt. ``efficient=True`` adds
    adaptive_efficient and gives the random/sequential controls the same
    survivor-only update. Old adaptive remains the unmodified reference.
    """
    config = _config(seed, runs, acquisition_steps, budget, efficient)
    conditions = EFFICIENT_CONDITIONS if efficient else CONDITIONS
    results, preparation, heldout, audits, tasks = [], [], [], [], []
    try:
        for index in range(runs):
            prepared = _prepare(config, index)
            _event(journal, 'curriculum_lazy_prepared', run_index=index,
                   acquisition_inputs=acquisition_steps * POOL_SIZE, heldout_inputs=HELDOUT_CASES)
            current = [_run_arm(config, prepared, condition, journal) for condition in conditions]
            audit = _audit_labels(prepared, current, budget)
            results.extend(current)
            preparation.append(prepared['preparation'])
            heldout.append(prepared['heldout_preparation'])
            audits.append(audit)
            tasks.append({'run_index': index, 'run_seed': prepared['run_seed'],
                          'family': prepared['family'], 'witness': prepared['witness'],
                          'repeated_acquisition_inputs': prepared['repeated_acquisition_inputs'],
                          'repeated_heldout_inputs': prepared['repeated_heldout_inputs']})
            _event(journal, 'curriculum_lazy_validated', run_index=index,
                   verified_challenges=audit['verified_challenges'], audit_work=audit['work'])
    except BudgetExceeded as exc:
        _event(journal, 'curriculum_lazy_budget_exhausted', completed_pairs=len(tasks),
               budget=budget, scientific_result='budget_exhausted', instrument_error=False,
               error=str(exc))
        raise
    except ValueError as exc:
        _event(journal, 'curriculum_lazy_instrument_error', completed_pairs=len(tasks), error=str(exc))
        raise
    shared_preparation, shared_heldout = c._add_work(*preparation), c._add_work(*heldout)
    audit_work = c._add_work(*(a['work'] for a in audits))
    physical = c._add_work(shared_preparation, shared_heldout, *(r['cost']['exclusive'] for r in results))
    arms = {condition: {phase: c._add_work(*(r['cost'][phase] for r in results if r['condition'] == condition))
                        for phase in (*PHASES, 'learning', 'total', 'exclusive')}
            for condition in conditions}
    return {'schema': EFFICIENT_SCHEMA if efficient else SCHEMA,
            'config': config, 'grammar': c.grammar(), 'tasks': tasks,
            'results': results, 'pairs': _pairs(results, seed, conditions),
            'perfamily': _family_summary(results, conditions),
            'cost': {'arms': arms, 'shared_preparation': shared_preparation,
                     'shared_heldout_evaluation': shared_heldout, 'audit_overhead': audit_work,
                     'physical_protocol': physical, 'physical_with_audit': c._add_work(physical, audit_work)},
            'audit': {'verified_challenges': sum(a['verified_challenges'] for a in audits),
                      'scope': 'all_input_witness_and_label_validation', 'independent_replay_performed': False},
            'instrument_valid': True, 'independent_replay_required': True,
            'scientific_superiority': False, 'scientific_result': 'inconclusive',
            'scope': 'descriptive cost and learning utility within the existing finite synthetic grammar',
            'promotion': False, 'llm_calls': 0, 'timing_measured': False}


def run_efficient_benchmark(*, seed=4_400_000, runs=8, acquisition_steps=4,
                            budget=2_000_000, journal=None):
    """Stable runner API: four matched arms under equal total-work ceilings.

    This opts into efficient-v1 without changing run_benchmark's defaults.
    Freeze sources before experiments; keep CPU/wall-time process receipts
    outside this deterministic report. audit_report accepts either schema.
    """
    return run_benchmark(seed=seed, runs=runs, acquisition_steps=acquisition_steps,
                         budget=budget, journal=journal, efficient=True)


def audit_report(report):
    """Regenerate/replay every arm and compare the complete JSON receipt.

    No files are read or written. Run in a fresh frozen-source process for
    independent custody. A valid report need not show scientific superiority.
    Replay and receipt-comparison costs are separate from the original study.
    """
    if (type(report) is not dict or report.get('schema') not in (SCHEMA, EFFICIENT_SCHEMA)
            or type(report.get('config')) is not dict):
        raise ValueError('invalid lazy curriculum report envelope')
    config = report['config']
    try:
        kwargs = {key: config[key] for key in ('seed', 'runs', 'acquisition_steps', 'budget')}
        if report['schema'] == EFFICIENT_SCHEMA:
            kwargs['efficient'] = config['efficient']
            if config['efficient'] is not True:
                raise ValueError('efficient report requires explicit opt-in')
        if config != _config(**kwargs):
            raise ValueError('lazy curriculum configuration mismatch')
        claimed = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('invalid lazy curriculum receipt') from exc
    replay = run_benchmark(**kwargs)
    actual = json.dumps(replay, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    # Serialized comparison rejects bool/int and int/float substitutions too.
    if actual != claimed:
        raise ValueError('lazy curriculum report differs from deterministic replay')
    comparison = {'used': len(claimed) + len(actual) + 1,
                  'counts': {'audit_receipt_serialized_bytes': len(claimed) + len(actual),
                             'audit_receipt_comparisons': 1}}
    work = replay['cost']['physical_with_audit']
    audit_schema = ('echo5-curriculum-efficient-audit-v1' if report['schema'] == EFFICIENT_SCHEMA
                    else 'echo5-curriculum-lazy-audit-v1')
    return {'schema': audit_schema, 'valid': True, 'instrument_valid': True,
            'replayed': True, 'scientific_superiority': replay['scientific_superiority'],
            'scientific_result': replay['scientific_result'], 'promotion': False,
            'replay_work': work, 'receipt_comparison_work': comparison,
            'total_work': c._add_work(work, comparison), 'timing_measured': False}
