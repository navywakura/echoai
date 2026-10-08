"""Integrated relational grid actor with exact verification and delayed cost policy."""
from __future__ import annotations

from echoai.seed import dsl
from echoai.seed.refinement import solver_input, VIEWS, inverse, canonical_program
from seed.relational_dsl import Work, Exhausted, RelationalLibrary, objects, steps

GEOMETRY = tuple((n,) for n in ('rot90', 'rot180', 'rot270', 'fliplr', 'flipud', 'transpose', 'up2', 'crop'))


def context(public, work):
    pair = public['train'][0]
    if (len(pair['input']), len(pair['input'][0])) != (len(pair['output']), len(pair['output'][0])):
        work.add('context_cells', len(pair['input'])*len(pair['input'][0]))
        return 'resize'
    try:
        return 'single' if len(objects(pair['input'], work).objects) == 1 else 'multiple'
    except ValueError:
        return 'multiple'


def solve(task, *, memory=None, policy=None, learn=False, episode=0, session='development',
          relational=True, refinement=True, views=False, consistency=True,
          order='recall_first', budget=500_000, beam_width=12, verification_window=32,
          journal=None):
    if type(budget) is not int or not 100 <= budget <= 20_000_000:
        raise ValueError('bounded logical budget required')
    if not 1 <= beam_width <= 32 or not 0 <= verification_window <= 256:
        raise ValueError('bounded beam and verification window required')
    if order not in ('recall_first', 'search_first'):
        raise ValueError('unknown search schedule')
    public = solver_input(task)
    work = Work(budget)
    lib = RelationalLibrary(work)
    train = tuple(p['input'] for p in public['train'])
    expected = tuple(p['output'] for p in public['train'])
    query = tuple(p['input'] for p in public['test'])
    all_inputs = train + query
    cache = {(): all_inputs}
    attempted = set()
    valid = {}
    rows = []
    metrics = {'trials': 0, 'invalid': 0, 'memory_reads': 0, 'memory_verified': 0,
               'view_trials': 0, 'first_solution_work': None, 'first_solution_trial': None,
               'budget_exhausted': False}
    ctx = context(public, work)
    action = 0 if order == 'recall_first' else 1
    if policy is not None:
        if learn:
            policy.mature(episode)
        action = policy.choose(ctx, learn)
    ticket = session + ':' + str(episode)
    if policy is not None and learn:
        policy.begin(ticket, ctx, action, work.used, episode)
    initial_work = work.used

    def note(kind, **data):
        if journal:
            journal.write(kind=kind, agent='echo45-relational-v3', origin='DEVELOPMENT', **data)

    note('observation', context=ctx, action=('recall_first', 'search_first')[action],
         policy_scores=policy.scores(ctx) if policy else None, budget=budget)

    def execute(program):
        if program in cache:
            return cache[program]
        before = execute(program[:-1])
        value = tuple(lib.apply(g, program[-1]) for g in before)
        cache[program] = value
        return value

    def stopped():
        first = metrics['first_solution_trial']
        return first is not None and metrics['trials'] >= first + verification_window

    def evaluate(body, view=(), origin='search'):
        program = canonical_program(tuple((n,) for n in view) + tuple(body) + tuple((n,) for n in inverse(view)), lib)
        if program in attempted or stopped():
            return None
        attempted.add(program)
        metrics['trials'] += 1
        metrics['view_trials'] += bool(view)
        try:
            values = execute(program)
        except (ValueError, IndexError, KeyError, ZeroDivisionError):
            metrics['invalid'] += 1
            return None
        work.add('verification_cells', sum(len(g)*len(g[0]) for g in expected))
        score = sum(10000 if (len(a), len(a[0])) != (len(b), len(b[0])) else
                    sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))
                    for a, b in zip(values[:len(train)], expected))
        if score == 0:
            valid[program] = values[len(train):]
            metrics['memory_verified'] += int(origin == 'memory')
            if metrics['first_solution_trial'] is None:
                metrics['first_solution_trial'] = metrics['trials']
                metrics['first_solution_work'] = work.used
            note('verified_hypothesis', program=program, demonstrations=len(train),
                 origin_detail=origin, test_verified=False)
        return (score, program, tuple(body), view, values)

    def recall():
        if memory is None or stopped():
            return
        work.add('recall_features', sum(len(g)*len(g[0])*8 for g in train))
        work.add('receipt_lookup', len(memory.actor.diary))
        records = memory.candidates(public, 24)
        metrics['memory_reads'] = len(records)
        for record in records:
            program = tuple(tuple(s) for s in record['program'])
            if not relational and any(s[0] == 'rel' for s in program):
                continue
            evaluate(program, origin='memory')
            if stopped():
                break

    incoming = set().union(*(dsl.palette(g) for g in train))
    outgoing = set().union(*(dsl.palette(g) for g in expected))
    # The control retains the complete previous DSL, not only geometry.
    legacy = tuple(sorted((tuple(m) for m in lib.moves(incoming, outgoing)), key=repr))
    base_moves = tuple(dict.fromkeys(GEOMETRY + (steps() if relational else ()) + legacy))
    selected_views = VIEWS if views else VIEWS[:1]
    try:
        evaluate(())
        if action == 0:
            recall()
        for move in base_moves:
            for view in selected_views if move[0] == 'rel' else VIEWS[:1]:
                row = evaluate((move,), view)
                if row is not None and row[0]:
                    rows.append(row)
                if stopped():
                    break
            if stopped() or work.used >= budget//3:
                break
        if action == 1:
            recall()
        if refinement and not stopped():
            beam, seen = [], set()
            for row in sorted(rows, key=lambda r: (r[0], len(r[1]), repr(r[1]))):
                if row[4] in seen:
                    continue
                seen.add(row[4]); beam.append(row)
                if len(beam) == beam_width:
                    break
            # Both relational prefixes and geometric prefixes may compose.
            for move in base_moves:
                for row in beam:
                    evaluate(row[2] + (move,), row[3], 'refinement')
                    if stopped():
                        break
                if stopped():
                    break
            note('refinement_round', iteration=2, trials=metrics['trials'],
                 verified=len(valid), best_errors=[r[0] for r in beam])
    except Exhausted:
        metrics['budget_exhausted'] = True
    groups = {}
    for program, prediction in valid.items():
        groups.setdefault(prediction, []).append(program)
    ambiguous = len(groups) > 1
    prediction = next(iter(groups), None) if not consistency or not ambiguous else None
    selected = next(iter(valid), None) if prediction is not None else None
    if policy is not None and learn:
        policy.charge(ticket, work.used-initial_work, event='solver-work')
        if valid:
            policy.verified(ticket, budget)
    metrics.update(work=work.used, counts=work.counts, context=ctx, action=action,
                   verified_programs=len(valid), prediction_groups=len(groups))
    result = {'status': 'AMBIGUOUS' if ambiguous else 'VERIFIED_DEMONSTRATIONS' if valid else 'NO_PROGRAM',
              'predictions': prediction, 'program': selected, 'programs': list(valid),
              'alternatives': list(groups), 'metrics': metrics, 'test_verified': False,
              'release_ready': False, 'S6_green': False}
    note('result', status=result['status'], metrics=metrics)
    return result
