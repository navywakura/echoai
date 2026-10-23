"""F1 protocol: real development failures -> bounded pieces -> paired gate."""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import re

from ..acumula3 import bench as B3
from . import runtime as R
from .api import complete
from .equiv import LAB, FAMILIES, development_memory, digest, observed, log
from .language import Program
from .mechanical import check, tuples
from .pieces_b3 import no_retoggle, no_repick
from .artifacts import save_new


def gate(base, candidate):
    return (set(base) == set(candidate)
            and all(candidate[f]['harm'] <= base[f]['harm'] and candidate[f]['success'] >= base[f]['success'] for f in base)
            and sum(candidate[f]['success'] for f in candidate) > sum(base[f]['success'] for f in base))


def extract_code(text):
    match = re.fullmatch(r'\s*```(?:python)?\s*\n(.*?)```\s*', text, flags=re.S)
    return (match.group(1) if match else text).strip() + '\n'


def memory_snapshot(memory):
    return {'edits': memory.cfg.edits, 'raw': memory.raw, 'sha256': digest(memory.raw)}


def restore_memory(doc):
    from ..acumula.config import ConfMemory, Config
    cfg = Config()
    for edit in tuples(doc['edits']):
        cfg = cfg.apply(edit)
    memory = ConfMemory(cfg)
    for row in tuples(doc['raw']):
        memory.observe(*row)
    if digest(memory.raw) != doc['sha256']:
        raise ValueError('memory snapshot hash mismatch')
    return memory


def collect(memory, output):
    states = {m: [] for m in (R.DECIDE, R.OUTCOME, R.DROP, R.IDLE)}
    dummy = R.Plug('snapshot', lambda m, v, c: ())
    class Collector(observed(R.HAgent)):
        def _dispatch(self, moment, obs, world, ctx):
            if len(states[moment]) < 200:
                states[moment].append({'moment': moment, 'view': asdict(self._view(obs, world, dummy)), 'context': asdict(ctx)})
            return super()._dispatch(moment, obs, world, ctx)
    failures, episodes = [], []
    for family in FAMILIES:
        for seed in range(10_100_000, 10_100_020):
            agent = Collector(source=memory.probe_copy())
            world = B3.W.make_world(family, seed, 'A2')
            try:
                result = agent.run(world)
            finally:
                world.close()
            episodes.append({'family': family, 'seed': seed, 'result': result, 'trace_sha256': digest(agent.trace)})
            if not result['success']:
                failures.append({'signals': result['signals'], 'result': {k: result[k] for k in ('success','harm','steps','wasted')},
                                 'tail': [{'action': p, 'intent': it, 'outcome': out, 'pos': obs['pos'], 'hand': obs['hand'],
                                           'heading': obs['dir'], 'reward': obs['reward']} for p, it, out, obs in agent.trace[-20:]],
                                 'last_grid': agent.trace[-1][3]['grid'], 'picked': tuple(agent.picked.items()),
                                 'opened': tuple(agent.opened.items()), 'progress': agent.progress,
                                 'source_episode_index': len(episodes)-1})
            log('f1_training_episode', family=family, seed=seed, success=result['success'], signals=result['signals'])
    chosen, signatures = [], set()
    for row in failures:
        signature = tuple(row['signals'])
        if signature not in signatures:
            signatures.add(signature)
            chosen.append(row)
        if len(chosen) == 3:
            break
    for row in failures:
        if len(chosen) == 3:
            break
        if row not in chosen:
            chosen.append(row)
    selected = []
    for index in range(200):
        for moment in states:
            if index < len(states[moment]):
                selected.append(states[moment][index])
            if len(selected) == 200:
                break
        if len(selected) == 200:
            break
    if len(selected) != 200 or len(chosen) != 3:
        raise RuntimeError('insufficient real states/failures for F1 protocol')
    result = {'episodes': episodes, 'fiches': chosen, 'states': selected, 'memory': memory_snapshot(memory)}
    save_new(output, result)
    return result


def evaluate(memory, plugs, seeds):
    result = {}
    for family in FAMILIES:
        totals = Counter()
        for seed in seeds:
            agent = observed(R.HAgent)(source=memory.probe_copy(), plugs=plugs)
            world = B3.W.make_world(family, seed, 'A2')
            try:
                row = agent.run(world)
            finally:
                world.close()
            totals.update({k: row[k] for k in ('success', 'harm', 'steps', 'wasted')})
            totals['episodes'] += 1
            totals['plug_errors'] += len(row['plug_errors'])
            log('f1_validation_episode', family=family, seed=seed, pieces=[p.name for p in plugs],
                success=row['success'], harm=row['harm'], plug_errors=len(row['plug_errors']))
        result[family] = dict(totals)
    return result


def prompt_for(fiche, previous=None):
    # Explicitly omit source episode indices, families, seeds and control scores.
    fiche = {k: v for k, v in fiche.items() if k != 'source_episode_index'}
    examples = inspect.getsource(no_retoggle) + '\n' + inspect.getsource(no_repick)
    return '''Write ONE new small pure integer Python function: def piece(moment, v, c).
It is an external correction for ECHO's existing policy. Infer a useful correction from the real failure below.
Return ONLY source, without imports, annotations, strings, docstrings or explanation. Do not use object/family names.
The code runs in an AST interpreter, not Python. Identifiers must not start with _ and have at most 48 characters.
Do not rebind v, c, moment, constants, effect names or builtins (including as loop variables).
No private attributes, mutation of v/c, recursion,
while, dicts, files, network, eval/exec, try, classes, bitwise operators, floats, / or **.
Allowed: assignments to local names; if/for/break/continue/return; tuples/lists/sets; bounded comprehensions;
+ - * // %; comparisons and boolean expressions; tuple indexing/slices; lambdas only as selection keys.
Builtins: len(seq), abs(number), int(value), sum(seq[, start]), all(seq), any(seq), tuple(seq), frozenset(seq),
range(stop) or range(start,stop[,step]), min/max(seq, key=lambda item: ..., default=value) or min/max(a,b,...),
sorted(seq, key=lambda item: ..., reverse=False). Selection keywords are optional; all other builtins take
positional arguments only. int() is invalid; sum's optional start must be positional.
range <=256; collections <=4096 total nodes including the root and nested elements;
integers abs<=2147483647; 50000 interpreted operations per invocation.
Source <=12000 characters, <=2000 AST nodes, depth <=32. None and booleans are permitted values.
List literals/comprehensions and generators materialize as immutable tuples; no append or other mutation.
tuple and frozenset require one collection argument; use () for an empty tuple. Selection key must be
a direct unary lambda. Other function objects cannot be stored or called. No isinstance builtin.
Four hooks: DECIDE (candidate intention before execution), OUTCOME (after accounting), DROP (before base drop),
IDLE (after decision accounting, v.idle=0 unless the base is idle). Return () to abstain; at most 2 effects:
at most one NOTE and one action. First action-producing piece wins in configured order.
DECIDE accepts BAN(id, act, HAND|ANY), NOTE. BAN causes replanning, at most eight times then a final proposal.
OUTCOME accepts BAN_UNTIL_PROGRESS(id, act), NOTE. DROP accepts DROP_AT(cell), GOTO(cell), NOTE.
IDLE accepts GOTO(cell), NOTE. GOTO must target a reachable cell different from v.pos, through known PASS cells.
DROP_AT requires a neighbouring in-bounds cell, hand nonempty and cell!=c.avoid.
BAN ids must be in the observed board. BAN(...,ANY) lasts until episode reset. BAN(...,HAND) binds to the held
identifier, applies again if that identifier is held again, and lasts until episode reset.
BAN_UNTIL_PROGRESS remains active while v.progress equals its value when the effect was applied.
NOTE(key, scope=EPISODE), key 0..15, has a separate counter for each piece. Only EPISODE or HAND is allowed,
never ANY. HAND counts separately per held id and persists on dropping/reacquiring until episode reset.
BAN and BAN_UNTIL_PROGRESS accept only ENTER, PICK or TOGGLE as act (available in the world), never DROP_ACTION.
HAND in BAN or NOTE requires v.hand != 0. NOTE increments its counter by one; read it with v.note.
Effect ids, actions, keys and coordinate elements must be plain integers, not booleans.
Effect coordinates must be tuples (x,y). Always return a tuple of effects, including () for no effect.
All outputs validated atomically; errors abstain and invalidate a candidate. No direct action primitives.
Constants: ENTER PICK TOGGLE DROP_ACTION, UNKNOWN PASS NOOP HURT PICKED OPEN GOAL,
DECIDE OUTCOME DROP IDLE, HAND ANY EPISODE, DIRS=((1,0),(0,1),(-1,0),(0,-1)).
View: v.grid tuple rows of opaque ids; v.pos=(x,y), v.dir=0..3, v.hand=0 if empty; v.absolute;
v.progress, v.idle, v.steps; v.wall (most common border id), v.floor (most common PASS id).
v.picked(id), v.opened(cell), v.visits(cell), v.note(key, scope=EPISODE), v.belief(id,act,hand),
v.reach(start=None,blocked=None) -> frozenset cells, v.ids_near(start=None) -> frozenset ids.
picked counts successful pickups of an id; opened counts successful OPEN results at a cell; visits counts
decisions at a cell; note reads the current piece's counter. Missing counters return 0.
belief returns a consequence constant, or UNKNOWN if absent. progress increases at the first successful pickup
of each id and at every OPEN result. steps counts decisions; idle counts consecutive idle base decisions.
reach starts at v.pos by default, includes its starting cell, and uses ENTER/PASS beliefs with hand=0;
blocked is one cell (x,y), not a collection of cells. ids_near includes ids adjacent to the whole reachable
region, not just adjacent to v.pos. wall/floor default to 0 if unavailable; frequency ties choose the smaller id.
Context: c.intent=() or (act,cell,id,hand,signature); c.drop_for=0 or id to pick after dropping;
c.out consequence constant; c.dropped_here=() or (id,progress_when_dropped); c.avoid=() or cell.
Context availability by hook (all unlisted fields keep their defaults):
DECIDE supplies intent and drop_for; OUTCOME supplies intent, out and dropped_here;
DROP supplies only avoid, with c.intent always (); IDLE supplies no context fields, with c.intent always ().
Defaults: intent=(), drop_for=0, out=UNKNOWN, dropped_here=(), avoid=(). DROP and IDLE run only if v.absolute==0.
OUTCOME is called only for nonempty intentions whose action is not DROP_ACTION.
There is no OUTCOME call after a drop or after a primitive action with no intention.
DROP is a hook; DROP_ACTION is an action. Use DROP_ACTION when comparing c.intent[0] for a drop.
c.intent[1] is a cell; c.intent[2] is an opaque integer id. BAN effects take an id, not a cell.
PICK is an action; PICKED is a consequence. Trace intention/outcome names use these public symbols;
UNKNOWN means no classified consequence. The trace action field is an observed primitive, not a returnable effect.
OUTCOME view grid/hand/pos are pre-action; progress/counters are post-action.
In contrast, trace pos/hand/heading/reward/terminated/truncated and last_grid are post-action observations.
No persistent learned pieces are initially installed. The base seeks goals and unexplored consequences,
may retest memory claims, drops held things to pick another thing, and otherwise idles.
Two example corrections (illustrations, not already installed):
''' + examples + '\nREAL FAILURE (opaque observations):\n' + json.dumps(fiche, sort_keys=True) + '\nPREVIOUS DEVELOPMENT RECEIPT:\n' + json.dumps(previous, sort_keys=True)


def ensure_fresh(output):
    output = Path(output)
    if output.exists():
        raise ValueError('pilot output exists; preserve previous run')
    if (output.parent / 'f1-started.json').exists() or any(output.parent.glob('f1-trial-*.json')):
        raise ValueError('partial pilot exists; no automatic repeat API attempts')


def run(output):
    output = Path(output)
    ensure_fresh(output)
    f0 = json.loads((LAB / 'f0-equiv.json').read_text())
    if not f0['green']:
        raise RuntimeError('F0 not green')
    for name, sha in f0['source_hashes'].items():
        if hashlib.sha256((Path(__file__).resolve().parents[2] / name).read_bytes()).hexdigest() != sha:
            raise RuntimeError('F0 source changed')
    collected_path = output.parent / 'f1-training.json'
    if collected_path.exists():
        data = json.loads(collected_path.read_text())
        memory = restore_memory(data['memory'])
    else:
        memory = development_memory()
        data = collect(memory, collected_path)
    save_new(output.parent / 'f1-started.json', {
        'max_generation_calls': 5, 'model': 'gemini-3.5-flash',
        'protocol_sha256': hashlib.sha256((Path(__file__).resolve().parents[2] / 'ECHO-5.8/docs/B4-CRECE-ENMIENDA-1.md').read_bytes()).hexdigest(),
        'sources': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}})
    trials, previous = [], None
    for index in range(5):
        prompt = prompt_for(data['fiches'][index % 3], previous)
        receipt = complete('gemini-3.5-flash', prompt, LAB / 'api-cache')
        source = extract_code(receipt['content'])
        sha = hashlib.sha256(source.encode()).hexdigest()
        trial = {'index': index, 'request_sha256': receipt['request_sha256'], 'source_sha256': sha,
                 'source': source, 'http_status': receipt['status'], 'accepted': False}
        if receipt['status'] != 200 or not receipt['content']:
            trial['mechanical'] = {'green': False, 'stage': 'API', 'finish_reason': receipt.get('finish_reason')}
        else:
            mechanical = check(source, data['states'])
            trial['mechanical'] = {k: v for k, v in mechanical.items() if k != 'responses'}
            if mechanical['green']:
                plug = R.Plug(sha, Program(source))
                seeds = tuple(10_110_000 + 100 * index + i for i in range(12))
                base = evaluate(memory, (), seeds)
                candidate = evaluate(memory, (plug,), seeds)
                trial.update(base=base, candidate=candidate, seeds=seeds)
                trial['accepted'] = gate(base, candidate) and not any(row['plug_errors'] for row in candidate.values())
        save_new(output.parent / f'f1-trial-{index}.json', trial)
        trials.append(trial)
        log('f1_trial', index=index, sha256=sha, accepted=trial['accepted'], mechanical=trial['mechanical'])
        print(json.dumps({'index': index, 'accepted': trial['accepted'], 'mechanical': trial['mechanical']}), flush=True)
        previous = {k: trial[k] for k in ('accepted', 'mechanical')}
        if 'base' in trial:
            previous.update(base=trial['base'], candidate=trial['candidate'])
            # Family names never go back to the model: ordered anonymous buckets.
            previous['base'] = list(trial['base'].values())
            previous['candidate'] = list(trial['candidate'].values())
        if index >= 2 and any(t['accepted'] for t in trials):
            break
    result = {'phase': 'F1', 'green': any(t['accepted'] for t in trials), 'trials': trials,
              'memory_sha256': data['memory']['sha256'], 'protocol': 'B4-CRECE-ENMIENDA-1.md',
              'model': 'gemini-3.5-flash', 'exam_run': False}
    save_new(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=LAB / 'f1-pilot.json')
    answer = run(parser.parse_args().output)
    print(json.dumps({'phase': 'F1', 'green': answer['green'], 'trials': len(answer['trials'])}))
