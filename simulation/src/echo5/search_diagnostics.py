"""Evaluator-side witness autopsy; the search never receives its witness.

Instrumentation diagnoses a particular path, not universal solvability. No
query answer or retrospective witness-based ordering is supplied to the actor.
"""
from copy import deepcopy
from collections import Counter

from .budget import Budget, BudgetExceeded
from .evaluation import digest, exact_success
from .programs import Program, execute, expand, synthesis_atoms
from .solver import solve, validate_synthesis


class _Tap:
    """Passive journal tap, forwarding facts to the existing Recorder if given."""
    def __init__(self, downstream):
        self.downstream, self.events = downstream, []

    def write(self, **event):
        self.events.append(deepcopy(event))
        if self.downstream is not None:
            self.downstream.write(**event)


def diagnose(task, witness, *, synthesis, budget=2000000, journal=None):
    # Intentionally drop proposals and query outputs: witness is not a proposal.
    public = {'train': deepcopy(task['train']),
              'test': [{'input': deepcopy(r['input'])} for r in task['test']]}
    trace = _Tap(journal)
    result = solve(public, synthesis=synthesis, budget=budget, diagnostic=True,
                   journal=trace, cache_policy='interned')
    audit = Budget(10000000)
    report = {'schema': 'echo5.search-autopsy.v1', 'result': result,
              'public_task_sha256': digest(public), 'witness_passed_to_solver': False,
              'prefixes': [], 'trace': trace.events, 'instrument_valid': False}
    analysis_completed = False
    try:
        steps = expand(witness, budget=audit)
        config = validate_synthesis(synthesis)
        alphabet = [expand(atom, budget=audit) for atom in synthesis_atoms(config['grammar'])]
        fits = True
        for demo in public['train']:
            out = execute(witness, demo['input'], budget=audit)
            audit.consume('witness_compare_cells', sum(map(len, demo['output'])))
            fits &= [list(r) for r in out] == demo['output']
        report['witness_fits_demonstrations'] = fits
        if not fits:
            report['diagnosis'] = 'invalid_witness'
        elif any((step,) not in alphabet for step in steps):
            report['diagnosis'] = 'witness_outside_search_alphabet'
        elif len(steps) > config['max_depth']:
            report['diagnosis'] = 'witness_outside_depth_limit'
        else:
            candidates = {}
            selections = {}
            for event in trace.events:
                audit.consume('diagnostic_event_reads')
                if event['kind'] == 'synthesis_candidate':
                    candidates.setdefault(digest(event['program']), []).append(event)
                if event['kind'] == 'synthesis_selection':
                    selections[event['depth']] = {digest(p) for p in event['retained']}
            first_loss = None
            for depth in range(1, len(steps)+1):
                program = Program(steps[:depth]).to_dict()
                key = digest(program)
                events = candidates.get(key, [])
                # A repeated identity can be seen at several depths. Keep only
                # this tier; semantic replacement does not imply path destruction.
                event = next((e for e in events if e['depth'] == depth and e['disposition'] != 'syntactic_duplicate'), None)
                state = 'not_reached'
                if event:
                    state = event['disposition']
                    if state == 'evaluated' and depth in selections:
                        state = 'retained' if key in selections[depth] else 'beam_pruned'
                    elif state == 'evaluated' and event['loss'] == 0:
                        state = 'demonstration_fit_reached'
                row = {'depth': depth, 'program': program, 'disposition': state}
                if event and 'loss' in event:
                    row['training_loss'] = event['loss']
                if event and 'representative' in event:
                    row['representative'] = event['representative']
                report['prefixes'].append(row)
                if first_loss is None and state not in ('retained', 'demonstration_fit_reached'):
                    first_loss = state
            if result['status'] == 'solved':
                report['diagnosis'] = 'solver_found_consensus_witness_path_optional'
            elif result['status'] == 'ambiguous' and result['metrics'].get('query_undefined', 0):
                report['diagnosis'] = 'query_execution_undefined'
                report['also_conflicting_predictions'] = result['metrics'].get('unique_predictions', 0) > 1
            elif result['status'] == 'ambiguous':
                report['diagnosis'] = 'demonstrations_underdetermine_query'
            elif first_loss == 'beam_pruned':
                report['diagnosis'] = 'known_witness_prefix_pruned'
            elif first_loss == 'semantic_duplicate':
                report['diagnosis'] = 'equivalent_prefix_replacement_requires_lineage_followup'
            elif first_loss == 'invalid_execution':
                report['diagnosis'] = 'witness_execution_failure'
            elif result['status'] in ('budget_exhausted', 'search_exhausted'):
                report['diagnosis'] = ('resource_limit_before_tier_complete'
                    if result['metrics'].get('consistent_programs', 0) else 'resource_limit_before_witness_path')
            else:
                report['diagnosis'] = 'path_not_reached_or_deduplicated_no_completeness_claim'
        analysis_completed = True
    except (ValueError, KeyError, TypeError) as exc:
        report['diagnosis'] = 'invalid_or_unsupported_witness'
        report['witness_error'] = str(exc)
    except BudgetExceeded:
        report['diagnosis'] = 'diagnostic_budget_exhausted'
    report['diagnostic_work'] = audit.snapshot()
    report['instrument_valid'] = bool(analysis_completed and report.get('witness_fits_demonstrations')
        and result['status'] in ('solved','unsolved','ambiguous','budget_exhausted','search_exhausted'))
    if journal:
        journal.write(kind='search_autopsy_result', diagnosis=report['diagnosis'],
                      public_task_sha256=report['public_task_sha256'],
                      search_work=result['metrics']['used'], diagnostic_work=audit.used,
                      witness_passed_to_solver=False)
    return report


def run_benchmark(*, seed=3400000, budget=2000000, beam_width=24, journal=None):
    from .transfer import make_case, public_task, SUPPORTED_FAMILIES, load_contract
    if type(seed) is not int or not 3400000 <= seed < 3490000:
        raise ValueError('diagnostic development seed range required')
    config = {**load_contract()['defaults']['synthesis'], 'beam_width': beam_width}
    preparation = Budget(10000000)
    rows = []
    for i, family in enumerate(SUPPORTED_FAMILIES):
        case = make_case(seed+i, family, split='development', budget=preparation)
        row = diagnose(public_task(case), case['witness'], synthesis=config, budget=budget, journal=journal)
        row.update(id=case['id'], family=family, expected=case['expected'],
                   exact=exact_success(row['result'], case['expected']))
        rows.append(row)
    return {'schema': 'echo5.search-diagnostics-pilot.v1',
            'config': {'seed': seed, 'budget': budget, 'beam_width': beam_width},
            'preparation': preparation.snapshot(), 'rows': rows,
            'diagnoses': dict(Counter(r['diagnosis'] for r in rows)),
            'exact': sum(r['exact'] for r in rows), 'cases': len(rows),
            'instrument_valid': all(r['instrument_valid'] for r in rows),
            'promotion': False, 'scope': 'development witness autopsy, not autonomous discovery'}
