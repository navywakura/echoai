"""Bounded demonstration search, exact disagreement detection, no query truth."""
from .budget import Budget, BudgetExceeded
from .concepts import digest
from . import grounding
from .programs import (MAX_STEPS, Program, SEARCH_GEOMETRY, apply_step,
                       candidate_atoms, expand, synthesis_atoms)

DEFAULT_BUDGET = 2_000_000
MAX_PROPOSALS = 64
MAX_CACHE = 20_000


def _inputs(task, budget):
    budget.consume('task_reads')
    train, tests = task['train'], task['test']
    if type(train) not in (list, tuple) or type(tests) not in (list, tuple) or not 1 <= len(train) <= 10 or not 1 <= len(tests) <= 10:
        raise ValueError('one to ten demonstrations and query inputs required')
    demos = tuple((grounding.grid(row['input'], budget), grounding.grid(row['output'], budget)) for row in train)
    labels = {}
    for inp, out in demos:
        budget.consume('demonstration_identity_cells', sum(map(len, inp)))
        if inp in labels and labels[inp] != out:
            raise ValueError('contradictory demonstration labels')
        labels[inp] = out
    # Deliberately never copy/iterate a query mapping or access its output key.
    queries = tuple(grounding.grid(row['input'], budget) for row in tests)
    return demos, queries


def candidate_compositions(*, relational=True, names=()):
    """Finite two-atom grammar; at least one atom is nonidentity geometry."""
    atoms = list(candidate_atoms(relational=relational))
    atoms.extend({'steps': [{'op': 'call', 'name': name}]} for name in names)
    geometry = [{'op': op} for op in SEARCH_GEOMETRY if op != 'identity']
    for atom in atoms:
        for transform in geometry:
            yield {'steps': [*atom['steps'], dict(transform)]}
    for transform in geometry:
        for atom in atoms:
            if atom['steps'][0]['op'] in ('relate', 'call'):
                yield {'steps': [dict(transform), *atom['steps']]}


class _Engine:
    def __init__(self, budget, library, relational, hierarchical, cache_policy='legacy'):
        self.budget, self.library = budget, library
        self.relational, self.hierarchical = relational, hierarchical
        self.cache, self.seen = {}, set()
        self.cache_policy = cache_policy
        self._input_ids, self._prefix_nodes, self._paths = {}, {}, {}
        self.stats = {'candidates': 0, 'invalid_candidates': 0, 'cache_hits': 0,
                      'consistent_programs': 0, 'unique_predictions': 0,
                      'rejected_proposals': 0, 'concepts_reverified': 0,
                      'query_undefined': 0, 'tier': 0, 'complete': False}

    def run(self, steps, inp):
        if self.hierarchical and self.cache_policy == 'interned':
            return self._run_interned(steps, inp)
        result = inp
        for index, step in enumerate(steps):
            key = None
            if self.hierarchical:
                self.budget.consume('cache_key_cells', sum(map(len, inp)))
                self.budget.consume('cache_lookups')
                key = (steps[:index + 1], inp)
                if key in self.cache:
                    self.stats['cache_hits'] += 1
                    value = self.cache[key]
                    if isinstance(value, str):
                        raise ValueError(value)
                    result = value
                    continue
            try:
                result = apply_step(step, result, budget=self.budget)
            except ValueError as exc:
                if key is not None and len(self.cache) < MAX_CACHE:
                    self.budget.consume('cache_writes')
                    self.cache[key] = str(exc)
                raise
            if key is not None and len(self.cache) < MAX_CACHE:
                self.budget.consume('cache_writes')
                self.cache[key] = result
        return result

    def _run_interned(self, steps, inp):
        """Hash public inputs once, then use bounded integer prefix/input keys.

        The original tuple is retained, so Python object-id reuse is impossible.
        This cache is per solve; it contains execution results, never truth.
        Lookups, interning, failed entries, reads and writes all carry work.
        """
        self.budget.consume('cache_input_lookups')
        identity = id(inp)
        if identity not in self._input_ids:
            self.budget.consume('cache_input_cells', sum(map(len, inp)))
            self.budget.consume('cache_input_writes')
            self._input_ids[identity] = (inp, len(self._input_ids))
        input_id = self._input_ids[identity][1]
        self.budget.consume('cache_program_nodes', len(steps))
        self.budget.consume('cache_path_lookups')
        path = self._paths.get(steps)
        if path is None:
            nodes, parent = [], 0
            for step in steps:
                self.budget.consume('cache_intern_fields', 6)
                key = (parent, step)
                if parent is None:
                    node = None
                elif key in self._prefix_nodes:
                    node = self._prefix_nodes[key]
                elif len(self._prefix_nodes) < MAX_CACHE:
                    self.budget.consume('cache_node_writes')
                    node = len(self._prefix_nodes) + 1
                    self._prefix_nodes[key] = node
                else:
                    node = None
                nodes.append(node)
                parent = node
            path = tuple(nodes)
            if len(self._paths) < MAX_CACHE:
                self.budget.consume('cache_path_writes', len(path))
                self._paths[steps] = path
        result, start = inp, 0
        # One hit on the deepest cached prefix skips walking all its ancestors.
        for index in range(len(path)-1, -1, -1):
            if path[index] is None:
                continue
            self.budget.consume('cache_lookups')
            key = (path[index], input_id)
            if key in self.cache:
                self.stats['cache_hits'] += 1
                result = self.cache[key]
                if isinstance(result, str):
                    raise ValueError(result)
                start = index + 1
                break
        for index in range(start, len(steps)):
            key = None if path[index] is None else (path[index], input_id)
            try:
                result = apply_step(steps[index], result, budget=self.budget)
            except ValueError as exc:
                if key is not None and len(self.cache) < MAX_CACHE:
                    self.budget.consume('cache_writes')
                    self.cache[key] = str(exc)
                raise
            if key is not None and len(self.cache) < MAX_CACHE:
                self.budget.consume('cache_writes')
                self.cache[key] = result
        self.stats['cache_entries'] = len(self.cache)
        return result

    def check(self, proposal, demos, queries):
        self.budget.consume('candidate_attempts')
        self.stats['candidates'] += 1
        try:
            steps = expand(proposal, library=self.library, budget=self.budget)
            if not self.relational and any(s.op in ('object', 'pack') or s.op == 'relate' and
                    (s.role not in grounding.BASE_ROLES or s.relation not in grounding.BASE_RELATIONS) for s in steps):
                raise ValueError('program unavailable in V3 control')
            self.budget.consume('candidate_deduplications')
            if steps in self.seen:
                return None
            self.seen.add(steps)
            for inp, expected in demos:
                predicted = self.run(steps, inp)
                self.budget.consume('compare_cells', sum(map(len, expected)))
                if predicted != expected:
                    return None
        except ValueError:
            self.stats['invalid_candidates'] += 1
            return None
        self.stats['consistent_programs'] += 1
        try:
            predictions = tuple(self.run(steps, inp) for inp in queries)
        except ValueError:
            self.stats['query_undefined'] += 1
            predictions = None
        return Program(steps).to_dict(), predictions


def _emit(journal, **event):
    if journal is not None:
        journal.write(**event)


def _result(status, engine, start, *, predictions=(), program=None, alternatives=()):
    snapshot = engine.budget.snapshot()
    metrics = {**snapshot, **engine.stats, 'task_used': engine.budget.used - start,
               'cortex_calls': 0}
    return {'status': status, 'predictions': [[list(r) for r in g] for g in predictions],
            'program': program, 'metrics': metrics, 'test_verified': False,
            'alternatives': list(alternatives)}


def solve(task, *, budget=DEFAULT_BUDGET, library=None, relational=True,
          hierarchical=True, learn=False, journal=None, synthesis=None,
          cache_policy='legacy'):
    """Compare every hypothesis in a completed tier; exhaustion always abstains.

    Tier 1: primitives, named concepts and supplied proposals. Only if no
    consistent hypothesis exists, tier 2 tries bounded geometric composition.
    Hierarchy caches prefixes; its control uses the identical candidate order.
    """
    if cache_policy not in ('legacy', 'interned'):
        raise ValueError('unknown prefix cache policy')
    if synthesis is not None:
        return _solve_synthesis(task, budget=budget, library=library,
                                relational=relational, hierarchical=hierarchical,
                                learn=learn, journal=journal, synthesis=synthesis,
                                cache_policy=cache_policy)
    budget = Budget(budget) if type(budget) is int else budget
    start = budget.used
    engine = _Engine(budget, library, relational, hierarchical, cache_policy)
    matches = []
    status, predictions, chosen = 'unsolved', (), None
    try:
        try:
            demos, queries = _inputs(task, budget)
        except (KeyError, TypeError, ValueError):
            return _result('invalid_task', engine, start)
        _emit(journal, kind='grid_observation', demonstrations=len(demos), queries=len(queries))
        names = ()
        if library is not None:
            engine.stats['concepts_reverified'] = library.reverify_all(budget=budget)
            names = library.active_names()
        proposals = task.get('proposals', [])
        if type(proposals) is not list or len(proposals) > MAX_PROPOSALS:
            return _result('invalid_task', engine, start)
        # Supplied hypotheses remain data; both controls validate them identically.
        first = list(candidate_atoms(relational=relational))
        first.extend({'steps': [{'op': 'call', 'name': name}]} for name in names)
        first.extend(proposals)
        tiers = (iter(first), candidate_compositions(relational=relational, names=names))
        for tier, candidates in enumerate(tiers, 1):
            engine.stats['tier'] = tier
            for proposal in candidates:
                invalid_before = engine.stats['invalid_candidates']
                found = engine.check(proposal, demos, queries)
                if tier == 1 and proposal in proposals and engine.stats['invalid_candidates'] > invalid_before:
                    engine.stats['rejected_proposals'] += 1
                if found is not None:
                    matches.append(found)
                    _emit(journal, kind='verified_hypothesis', program=found[0],
                          train_verified=True, test_verified=False, query_defined=found[1] is not None)
            engine.stats['complete'] = True
            if matches:
                break
        groups = {pred for _, pred in matches if pred is not None}
        engine.stats['unique_predictions'] = len(groups)
        if len(groups) > 1 or engine.stats['query_undefined']:
            status = 'ambiguous'
        elif groups:
            status, predictions, chosen = 'solved', next(iter(groups)), matches[0][0]
        if learn and library is not None and status == 'solved':
            try:
                name = 'c_' + digest(chosen, budget)[:24]
                demo_rows = [{'input': [list(r) for r in inp], 'output': [list(r) for r in out]} for inp, out in demos]
                library.acquire(name, chosen, demo_rows, budget=budget,
                                provenance={'source': 'solver demonstrated program'})
                engine.stats['learning'] = 'acquired'
            except ValueError:
                engine.stats['learning'] = 'insufficient_or_rejected_evidence'
            except BudgetExceeded:
                engine.stats['learning'] = 'budget_exhausted'
    except BudgetExceeded:
        status, predictions, chosen = 'budget_exhausted', (), None
        engine.stats['complete'] = False
    except ValueError:
        status, predictions, chosen = 'invalid_library', (), None
    result = _result(status, engine, start, predictions=predictions, program=chosen,
                     alternatives=[program for program, _ in matches[:16]] if status == 'ambiguous' else ())
    _emit(journal, kind='grid_result', status=status, metrics=result['metrics'], test_verified=False)
    return result


def validate_synthesis(config):
    """Validate a public search contract without performing search or execution."""
    if type(config) is not dict or set(config) - {'max_depth', 'beam_width', 'max_candidates', 'grammar'}:
        raise ValueError('invalid synthesis config')
    limits = {'max_depth': (4, 8), 'beam_width': (24, 128), 'max_candidates': (12000, 100000)}
    result = {}
    for key, (default, maximum) in limits.items():
        value = config.get(key, default)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('invalid synthesis limit: ' + key)
        result[key] = value
    # Materializing a finite alphabet is configuration validation, not evaluation.
    atoms = list(synthesis_atoms(config.get('grammar')))
    if not atoms:
        raise ValueError('empty synthesis alphabet')
    result['grammar'] = config.get('grammar')
    return result


def _loss(actual, expected, budget):
    """Training-only deterministic ranking; no query truth participates."""
    h, w, eh, ew = len(actual), len(actual[0]), len(expected), len(expected[0])
    budget.consume('ranking_cells', min(h, eh) * min(w, ew))
    # Shape disagreement is explicit rather than a hidden generator predicate.
    shape = abs(h-eh) * max(w, ew) + abs(w-ew) * max(h, eh)
    return shape + sum(actual[y][x] != expected[y][x]
                       for y in range(min(h, eh)) for x in range(min(w, ew)))


def _solve_synthesis(task, *, budget, library, relational, hierarchical, learn,
                     journal, synthesis, cache_policy):
    """Compose arbitrary retained prefixes with primitives or verified calls.

    Each tier is fully considered before emitting consensus. Ranking uses only
    demonstrations; state equivalence also includes query executions, so two
    programs fitting training but disagreeing on queries cannot be merged.
    Beam pruning is a declared limitation, never a proof of DSL completeness.
    """
    budget = Budget(budget) if type(budget) is int else budget
    start = budget.used
    engine = _Engine(budget, library, relational, hierarchical, cache_policy)
    engine.stats.update(semantic_duplicates=0, beam_pruned=0, frontier_peak=1,
                        consensus_scope='first_matching_retained_tier',
                        search_space_exhaustive=False, search_limit_hit=False)
    matches, hypothesis = [], None
    status, predictions, chosen = 'unsolved', (), None
    try:
        try:
            budget.consume('synthesis_config_reads')
            config = validate_synthesis(synthesis)
        except (TypeError, ValueError):
            return _result('invalid_search', engine, start)
        try:
            demos, queries = _inputs(task, budget)
            proposals = task.get('proposals', [])
            if type(proposals) is not list or len(proposals) > MAX_PROPOSALS:
                raise ValueError('invalid proposals')
        except (KeyError, TypeError, ValueError):
            return _result('invalid_task', engine, start)
        _emit(journal, kind='grid_observation', demonstrations=len(demos), queries=len(queries),
              search=config, cache_policy=cache_policy, hierarchical=hierarchical)
        names = ()
        if library is not None:
            engine.library = library.verified_view(budget=budget)
            names = engine.library.active_names()
            engine.stats['concepts_reverified'] = len(names)
            engine.stats['library_checksum'] = engine.library.source_checksum
        # Named chunks have an explicit prior in this opt-in search. They still
        # face every demonstration and contribute no claim of query verification.
        atoms = [{'steps': [{'op': 'call', 'name': name}]} for name in names]
        atoms.extend(synthesis_atoms(config['grammar'], relational=relational))
        atoms.extend(proposals)
        compiled = []
        for index, atom in enumerate(atoms):
            budget.consume('synthesis_atom_builds')
            try:
                steps = expand(atom, library=engine.library, budget=budget)
                if not relational and any(s.op in ('object', 'pack') or s.op == 'relate' and
                        (s.role not in grounding.BASE_ROLES or s.relation not in grounding.BASE_RELATIONS)
                        for s in steps):
                    raise ValueError('operation outside representation control')
                compiled.append((atom, steps))
            except ValueError:
                engine.stats['invalid_candidates'] += 1
                if index >= len(atoms)-len(proposals):
                    engine.stats['rejected_proposals'] += 1
        # State: expanded program, symbolic chunks (preserving named calls).
        frontier = [((), ())]
        for depth in range(1, config['max_depth']+1):
            engine.stats.update(tier=depth, complete=False)
            next_states, equivalent = [], set()
            for prefix, symbols in frontier:
                for atom, extension in compiled:
                    if engine.stats['candidates'] >= config['max_candidates']:
                        engine.stats['search_limit_hit'] = True
                        status = 'search_exhausted'
                        break
                    budget.consume('candidate_attempts')
                    engine.stats['candidates'] += 1
                    budget.consume('synthesis_program_nodes', len(prefix)+len(extension))
                    steps = prefix + extension
                    if len(steps) > MAX_STEPS or len(symbols)+len(atom['steps']) > MAX_STEPS:
                        engine.stats['invalid_candidates'] += 1
                        continue
                    budget.consume('candidate_deduplications', len(steps))
                    if steps in engine.seen:
                        continue
                    engine.seen.add(steps)
                    try:
                        outputs = tuple(engine.run(steps, inp) for inp, _ in demos)
                    except ValueError:
                        engine.stats['invalid_candidates'] += 1
                        continue
                    loss = sum(_loss(actual, expected, budget) for actual, (_, expected) in zip(outputs, demos))
                    query_outputs = []
                    for inp in queries:
                        try:
                            query_outputs.append(engine.run(steps, inp))
                        except ValueError:
                            query_outputs.append(None)
                    query_outputs = tuple(query_outputs)
                    budget.consume('state_hash_cells', sum(sum(map(len, out))
                                   for out in (*outputs, *query_outputs) if out is not None))
                    budget.consume('state_lookups')
                    signature = (len(steps), outputs, query_outputs)
                    if signature in equivalent:
                        engine.stats['semantic_duplicates'] += 1
                        continue
                    budget.consume('state_writes')
                    equivalent.add(signature)
                    symbolic = symbols + tuple(atom['steps'])
                    if loss == 0:
                        engine.stats['consistent_programs'] += 1
                        pred = None if None in query_outputs else query_outputs
                        if pred is None:
                            engine.stats['query_undefined'] += 1
                        program = Program(steps).to_dict()
                        symbolic_program = {'steps': list(symbolic)}
                        matches.append((program, pred, symbolic_program))
                        _emit(journal, kind='verified_hypothesis', program=program,
                              hypothesis=symbolic_program, train_verified=True,
                              test_verified=False, query_defined=pred is not None, depth=depth)
                    next_states.append((loss, len(steps), len(next_states), steps, symbolic))
                if engine.stats['search_limit_hit']:
                    break
            if engine.stats['search_limit_hit']:
                break
            engine.stats['complete'] = True
            if matches:
                groups = {pred for _, pred, _ in matches if pred is not None}
                engine.stats['unique_predictions'] = len(groups)
                if len(groups) > 1 or engine.stats['query_undefined']:
                    status = 'ambiguous'
                elif groups:
                    status, predictions = 'solved', next(iter(groups))
                    chosen, _, hypothesis = matches[0]
                break
            budget.consume('frontier_order_work', len(next_states) * max(1, len(next_states).bit_length()))
            next_states.sort(key=lambda item: item[:3])
            engine.stats['beam_pruned'] += max(0, len(next_states)-config['beam_width'])
            frontier = [(steps, symbols) for _, _, _, steps, symbols in next_states[:config['beam_width']]]
            engine.stats['frontier_peak'] = max(engine.stats['frontier_peak'], len(frontier))
            _emit(journal, kind='synthesis_frontier', depth=depth, retained=len(frontier),
                  beam_pruned=engine.stats['beam_pruned'], work=budget.used)
            if not frontier:
                break
        if learn and library is not None and status == 'solved':
            try:
                name = 'c_' + digest(hypothesis, budget)[:24]
                support = [{'input': [list(r) for r in inp], 'output': [list(r) for r in out]} for inp, out in demos]
                library.acquire(name, hypothesis, support, budget=budget,
                                provenance={'source': 'bounded synthesis demonstrations'})
                engine.stats['learning'] = 'acquired'
            except ValueError:
                engine.stats['learning'] = 'insufficient_or_rejected_evidence'
            except BudgetExceeded:
                engine.stats['learning'] = 'budget_exhausted'
    except BudgetExceeded:
        status, predictions, chosen, hypothesis = 'budget_exhausted', (), None, None
        engine.stats['complete'] = False
    except ValueError:
        status, predictions, chosen, hypothesis = 'invalid_library', (), None, None
    result = _result(status, engine, start, predictions=predictions, program=chosen,
                     alternatives=[program for program, _, _ in matches[:16]] if status == 'ambiguous' else ())
    result['hypothesis'] = hypothesis
    _emit(journal, kind='grid_result', status=status, metrics=result['metrics'], test_verified=False)
    return result


def verify_proposal(proposal, task, *, budget=DEFAULT_BUDGET, library=None, journal=None):
    """Optional LLM boundary: verify JSON from any source; never call a model."""
    budget = Budget(budget) if type(budget) is int else budget
    start = budget.used
    engine = _Engine(budget, library, True, True)
    try:
        demos, queries = _inputs(task, budget)
        if library is not None:
            engine.stats['concepts_reverified'] = library.reverify_all(budget=budget)
        found = engine.check(proposal, demos, queries)
        engine.stats['complete'] = True
        if found is None:
            result = _result('rejected', engine, start)
        elif found[1] is None:
            result = _result('ambiguous', engine, start)
        else:
            engine.stats['unique_predictions'] = 1
            result = _result('consistent', engine, start, program=found[0], predictions=found[1])
    except BudgetExceeded:
        result = _result('budget_exhausted', engine, start)
    except (KeyError, TypeError, ValueError):
        result = _result('rejected', engine, start)
    _emit(journal, kind='proposal_result', status=result['status'], metrics=result['metrics'], test_verified=False)
    return result
