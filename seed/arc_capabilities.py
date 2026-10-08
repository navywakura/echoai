"""Synthetic development diagnostics, separate from every reserved ARC exam.

Oracle outputs come from the generator's construction, never from ECHO's DSL.
All ablations use the same search engine and global trial ceiling. They are
diagnostics of these families, not estimates of official ARC performance.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))

FAMILIES = {
    'objects': 'isolate the largest connected object',
    'marker_relation': 'use the singleton colour on another object; remove the marker',
    'size_relation': 'order object colours by decreasing area',
    'composition': 'isolate the largest object, then rotate it clockwise',
}
ARMS = {
    'full': {'relations': True, 'composition': True},
    'without_relations': {'relations': False, 'composition': True},
    'without_composition': {'relations': True, 'composition': False},
}
CONFIG = {'seeds': [45101, 45103, 45107], 'train_examples': 3, 'test_examples': 2,
          'max_trials': 2000, 'max_depth': 4, 'rounds': 4, 'beam_width': 8,
          'max_hypotheses': 32, 'views': False, 'attempts_scored': 1,
          'workers': 1, 'model_calls': 0, 'weight_updates': 0}


def rotate(rows):
    return [list(row) for row in zip(*rows[::-1])]


def example(family, rng, index):
    """Vary colours, dimensions, placement and orientation; preserve the rule."""
    colors = rng.sample(range(1, 10), 3)
    size = 3 + index % 3
    shape = [[colors[0]] + [0] * (size - 1) for _ in range(2)]
    shape.append([colors[0]] * size)
    for _ in range(rng.randrange(4)):
        shape = rotate(shape)
    canvas = [[0] * 14 for _ in range(12)]
    oy, ox = rng.randrange(1, 3), rng.randrange(1, 4)
    for y, row in enumerate(shape):
        for x, color in enumerate(row):
            canvas[oy + y][ox + x] = color
    # Distant singleton and domino cannot merge with the largest component.
    my, mx = 10, 11
    canvas[my][mx] = colors[1]
    if family != 'marker_relation':
        canvas[10][1] = canvas[10][2] = colors[2]
    if family == 'objects':
        out = deepcopy(shape)
    elif family == 'composition':
        out = rotate(shape)
    elif family == 'marker_relation':
        out = [[colors[1] if c == colors[0] else 0 for c in row] for row in canvas]
    elif family == 'size_relation':
        out = [[colors[0], colors[2], colors[1]]]
    else:
        raise ValueError('unknown development family')
    return {'input': canvas, 'output': out}


def suite():
    tasks = []
    for family in FAMILIES:
        for seed in CONFIG['seeds']:
            rng = random.Random(str(seed) + '/' + family)
            examples = [example(family, rng, i) for i in range(5)]
            tasks.append({'id': family + '-' + str(seed), 'capabilities': [family],
                          'origin': 'SYNTHETIC_DEVELOPMENT',
                          'task': {'train': examples[:3], 'test': examples[3:]}})
    return tasks


def library_for(arm, state):
    from echoai.seed import refinement as r
    from echoai.seed.learn import Library
    settings = ARMS[arm]
    parent = r.RefinementLibrary if settings['relations'] else Library

    class DiagnosticLibrary(parent):
        def moves(self, colors_in, colors_out):
            moves = super().moves(colors_in, colors_out)
            if not settings['composition']:
                # A learned macro must not smuggle multiple primitive steps into
                # the one-step ablation. Views are disabled in EVERY arm.
                moves = [m for m in moves if len(self.expand(m)) <= 1]
            return moves

    return DiagnosticLibrary(deepcopy(state['concepts']), deepcopy(state['prior']))


def solve_public(public, arm, state, journal=None):
    from echoai.seed import refinement as r, sandbox
    sandbox._set_level(state['level'])
    lib = library_for(arm, state)
    depth = CONFIG['max_depth'] if ARMS[arm]['composition'] else 1
    result = r.solve(public, lib, max_trials=CONFIG['max_trials'], max_depth=depth,
                     rounds=CONFIG['rounds'], beam_width=CONFIG['beam_width'],
                     max_hypotheses=CONFIG['max_hypotheses'], views=CONFIG['views'], journal=journal)
    if result['trials'] > CONFIG['max_trials'] or result['test_ok'] is not None:
        raise ValueError('search budget or label isolation violated')
    for program in result['programs']:
        if not all(r.execute(r.grid(p['input']), program, lib) == r.grid(p['output']) for p in public['train']):
            raise ValueError('emitted program fails a demonstration')
        if not ARMS[arm]['composition'] and len(r.canonical_program(program, lib)) > 1:
            raise ValueError('composition escaped the ablation')
    return result


def compare(rows):
    from seed.arc_comparison import delta
    expected = {(t['id'], arm) for t in suite() for arm in ARMS}
    indexed = {(r['task'], r['arm']): r for r in rows}
    if len(indexed) != len(rows) or set(indexed) != expected:
        raise ValueError('missing, duplicated or foreign development cases')
    totals, contrasts = {}, {}
    for family in FAMILIES:
        totals[family] = {}
        for arm in ARMS:
            group = [r for r in rows if r['capabilities'] == [family] and r['arm'] == arm]
            totals[family][arm] = {'solved': sum(r['correct'] for r in group), 'tasks': len(group),
                                  'trials': sum(r['result']['trials'] for r in group),
                                  'primitive_steps_upper_count': sum(r['result']['primitive_steps_upper_count'] for r in group),
                                  'ambiguous': sum(r['result']['status'] == 'AMBIGUOUS' for r in group),
                                  'seconds': sum(r['seconds'] for r in group)}
        contrasts[family] = {arm: delta(totals[family][arm]['solved'], totals[family]['full']['solved'],
                                         totals[family]['full']['tasks'])
                             for arm in ARMS if arm != 'full'}
    return {'totals': totals, 'full_minus_ablation': contrasts,
            'origin': 'SYNTHETIC_DEVELOPMENT', 'official_arc_score': False,
            'reserved_exam': False, 'green': None,
            'scope': 'constructed families only; no causal claim about official ARC tasks'}


def run(root):
    from seed import arc_comparison as c
    from echo_arc.observe import Journal
    profile = c.prepared(root)
    state = c.read(c.HISTORICAL / 'profile.json')['learned']
    manifest = suite()
    c.require(c.digest(manifest) == profile['capability_suite_sha256'], 'development suite changed')
    output = root / 'development'
    c.require(not (output / 'summary.json').exists(), 'development already closed; retain original results')
    rows = []
    for task in manifest:
        for arm in ARMS:
            path = output / arm / (task['id'] + '.json')
            if path.exists():
                row = c.read(path)
                c.require(row['profile_sha256'] == c.digest(profile) and
                          row['task_sha256'] == c.digest(task['task']), 'changed development checkpoint')
            else:
                log = REPO / 'lab/observability/arc-comparison-dev-20260929/v2' / arm / task['id'] / 'arc-decisions.jsonl'
                # Interrupted diaries stay intact; recovery owns a new journal.
                if log.exists():
                    log = log.parent / c.now().replace(':', '-') / log.name
                journal = Journal(log)
                journal.write(kind='game', game='DESARROLLO / ' + arm + ' / ' + task['id'])
                start = time.monotonic()
                try:
                    result = solve_public(c.solver_input(task['task']), arm, state, journal)
                finally:
                    journal.close()
                row = {'task': task['id'], 'arm': arm, 'capabilities': task['capabilities'],
                       'task_sha256': c.digest(task['task']), 'profile_sha256': c.digest(profile),
                       'result': result, 'correct': c.judge(task['task'], result),
                       'seconds': time.monotonic() - start, 'origin': 'SYNTHETIC_DEVELOPMENT'}
                c.save(path, row)
            rows.append(row)
            c.save(output / 'status.json', {'completed': len(rows), 'total': len(manifest) * len(ARMS), 'at': c.now()})
    # Replay from stripped inputs in a new interpreter; no journal is attached.
    import subprocess
    subprocess.run([sys.executable, '-m', 'seed.arc_capabilities', 'audit', str(root)], check=True, cwd=REPO)
    c.prepared(root)
    summary = dict(compare(rows), at=c.now(), profile_sha256=c.digest(profile),
                   replay_audit=c.read(output / 'audit.json'))
    c.save(output / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


def audit(root):
    from seed import arc_comparison as c
    import os
    profile = c.prepared(root)
    state = c.read(c.HISTORICAL / 'profile.json')['learned']
    count = 0
    for task in suite():
        for arm in ARMS:
            saved = c.read(root / 'development' / arm / (task['id'] + '.json'))
            result = solve_public(c.solver_input(task['task']), arm, state)
            c.require(c.digest(saved['result']) == c.digest(result), 'independent development replay differs')
            c.require(saved['correct'] == c.judge(task['task'], result), 'judge result differs')
            c.require(saved['profile_sha256'] == c.digest(profile), 'wrong development profile')
            count += 1
    c.save(root / 'development/audit.json', {'valid': True, 'cases': count, 'pid': os.getpid(),
                                           'profile_sha256': c.digest(profile), 'at': c.now()})


if __name__ == '__main__':
    from seed.arc_comparison import ROOT
    if sys.argv[1:] == ['run']:
        run(ROOT)
    elif len(sys.argv) == 3 and sys.argv[1] == 'audit':
        audit(Path(sys.argv[2]))
    else:
        raise SystemExit('use run or audit ROOT')
