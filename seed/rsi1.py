"""Private bounded library self-improvement, independent of all S6 cohorts.

The initial condition uses an existing local GGUF through llama-cli, without
network, paid inference or edits to the core. No generated Python is executed.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))
from echoai.seed import dsl, learn

ROOT = REPO / 'lab/research/echo-rsi1-20261001'
ARMS = ('frozen', 'random', 'llm_only', 'echo_reset', 'echo_recursive')
OPS = tuple(dsl.NO_ARG)  # Full original argument-free S0 vocabulary, no weakened baseline.
RECIPES = ((('crop',), ('rot90',)),
           (('gravity_down',), ('crop',), ('up2',)),
           (('sym_h',), ('gravity_left',), ('crop',)),
           (('largest_object',), ('up2',), ('flipud',)),
           (('gravity_right',), ('sym_v',), ('crop',), ('rot90',)),
           (('sym_h',), ('gravity_down',), ('crop',), ('mirror_h',), ('transpose',)))
SOURCES = ('seed/rsi1.py', 'seed/rsi1_queue.py', 'seed/dsl.py', 'seed/learn.py',
           'tests/test_rsi1.py', 'docs/ECHO-RSI1-DESIGN.md')
CFG = {'generations': 5, 'replicas': [311, 719, 1201], 'dev_per_generation': 12,
       'anchors': 12, 'exam_tasks': 48, 'research_tasks': 12,
       'research_calls_per_condition': 2, 'max_expansions': 60, 'max_depth': 4,
       'max_model_calls': 57, 'max_output_tokens': 384, 'call_timeout_s': 600,
       'max_wall_s': 28800, 'cpu_threads': 4, 'spend_eur': 0,
       'scope': 'synthetic closed-DSL ECHO-SEED library evolution; not ARC or S6'}


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(canonical(value) + '\n')
    tmp.replace(path)


def status(stage, **fields):
    value = dict(at=now(), stage=stage, **fields)
    atomic(ROOT / 'status.json', value)
    print(canonical(value), flush=True)


def checked_program(value):
    if type(value) is not list or not 2 <= len(value) <= 3:
        raise ValueError('a proposal must contain two or three primitive steps')
    if any(type(s) is not list or len(s) != 1 or type(s[0]) is not str or s[0] not in OPS for s in value):
        raise ValueError('only whitelisted argument-free DSL operations are allowed')
    return deepcopy(value)


def parse_reply(text):
    # Ignore prose; never interpret source, paths, commands or alleged facts.
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            return checked_program(value['steps'])
        except (ValueError, KeyError, TypeError):
            pass
    raise ValueError('no valid structured DSL proposal')


def execute(grid, steps):
    out = dsl.G(grid)
    for step in steps:
        out = dsl.apply_step(out, tuple(step))
    return [list(row) for row in out]


class Library(learn.Library):
    """Reuse ECHO's library, search and integer priority; limit this vocabulary."""
    def moves(self, colors_in, colors_out):
        moves = list(self.concepts) + [(name,) for name in OPS]
        return sorted(moves, key=lambda m: -self.prior.get(self.key(m), 0))


def public(task):
    return {'train': deepcopy(task['train']), 'test': [{'input': deepcopy(p['input'])} for p in task['test']]}


def corpus(replica, partition, n):
    """New synthetic inputs only; no official ARC data or S6 artifacts."""
    rng = random.Random(int(sha([replica, partition])[:16], 16))
    tasks = []
    for i in range(n):
        recipe = RECIPES[i % len(RECIPES)]
        pairs = []
        for _ in range(4):
            h, w = rng.randint(3, 5), rng.randint(3, 5)
            inner = [[rng.randrange(4) for _ in range(w)] for _ in range(h)]
            inner[0][0] = rng.randint(1, 3)
            inp = [[0] * (w + 2)] + [[0] + row + [0] for row in inner] + [[0] * (w + 2)]
            pairs.append({'input': inp, 'output': execute(inp, recipe)})
        tasks.append({'id': f'{replica}/{partition}/{i:03d}', 'family': i % len(RECIPES),
                      'train': pairs[:3], 'test': pairs[3:]})
    return tasks


def state(library):
    return {'concepts': deepcopy(library.concepts), 'prior': dict(library.prior)}


def restore(value):
    return Library(value['concepts'], value['prior'])


def measure(tasks, library, direct=False):
    rows = []
    for task in tasks:
        visible = public(task)
        if direct:
            result = {'program': None, 'expansions': 0, 'predictions': []}
            for name in library.concepts:
                steps = library.concepts[name]['steps']
                try:
                    if all(execute(p['input'], steps) == p['output'] for p in visible['train']):
                        result = {'program': [name], 'expansions': 0,
                                  'predictions': [execute(p['input'], steps) for p in visible['test']]}
                        break
                except (ValueError, IndexError, ZeroDivisionError):
                    continue
        else:
            result = learn.solve(visible, library, max_expansions=CFG['max_expansions'],
                                 max_depth=CFG['max_depth'])
        ok = bool(result['program']) and result['predictions'] == [p['output'] for p in task['test']]
        rows.append({'task': task['id'], 'family': task['family'], 'correct': bool(ok),
                     'program': result['program'], 'expansions': result['expansions']})
    return rows


def decision(before, after):
    old = {r['task']: r['correct'] for r in before}
    gains = [r['task'] for r in after if r['correct'] and not old[r['task']]]
    losses = [r['task'] for r in after if not r['correct'] and old[r['task']]]
    return {'accepted': len(gains) >= 2 and not losses, 'gains': gains, 'losses': losses}


def propose(prompt, call_id, profile):
    output = ROOT / 'calls' / (call_id + '.json')
    if output.exists():
        saved = json.loads(output.read_text())
        if saved['prompt_sha256'] != sha(prompt):
            raise RuntimeError('saved model request differs; stop')
        return saved
    budget = ROOT / 'budget.json'
    value = json.loads(budget.read_text()) if budget.exists() else {
        'model_calls_reserved': 0, 'reserved_call_ids': [], 'spend_eur': 0}
    if call_id in value['reserved_call_ids']:
        raise RuntimeError('interrupted model call requires a declared recovery; no automatic retry')
    if value['model_calls_reserved'] >= CFG['max_model_calls']:
        raise RuntimeError('model call budget exhausted')
    value['model_calls_reserved'] += 1
    value['reserved_call_ids'].append(call_id)
    atomic(budget, value)  # Interrupted calls count, and are not invisibly retried.
    request = ROOT / 'prompts' / (call_id + '.txt')
    request.parent.mkdir(parents=True, exist_ok=True)
    request.write_text('<|im_start|>system\nReturn one JSON object with steps only. No prose.'
                       '<|im_end|>\n<|im_start|>user\n' + prompt +
                       '<|im_end|>\n<|im_start|>assistant\n')
    started = time.monotonic()
    proc = subprocess.run([profile['llama_cli'], '-m', profile['model_path'], '-ngl', '0',
        '-t', str(CFG['cpu_threads']), '-tb', str(CFG['cpu_threads']), '-c', '4096',
        '-b', '128', '-ub', '64', '-n', str(CFG['max_output_tokens']),
        '--seed', str(int(sha(call_id)[:7], 16)), '--temp', '0', '--no-conversation',
        '--no-display-prompt', '--simple-io', '-f', str(request)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=CFG['call_timeout_s'], check=False)
    (request.with_suffix('.stderr.log')).write_text(proc.stderr[-16000:])
    if proc.returncode:
        raise RuntimeError(f'local model process exited {proc.returncode}; no automatic retry')
    try:
        program, error = parse_reply(proc.stdout), None
    except ValueError as exc:
        program, error = None, str(exc)
    saved = {'prompt_sha256': sha(prompt), 'reply': proc.stdout, 'program': program,
             'error': error, 'seconds': round(time.monotonic() - started, 3)}
    atomic(output, saved)
    return saved


def prompt_for(tasks, rows, library, adaptive):
    failed = {r['task'] for r in rows if not r['correct']}
    pool = [t for t in tasks if t['id'] in failed] if adaptive else tasks
    chosen = (pool or tasks)[:2]
    # No identifiers, recipes, final exam, private test outputs or S6 patches.
    examples = [public(t)['train'][:2] for t in chosen]
    return canonical({'instruction': 'Propose a reusable composition solving these demonstrated transforms.',
                      'allowed_operations': OPS, 'schema': {'steps': [['operation'], ['operation']]},
                      'max_steps': 3, 'demonstrations': examples,
                      'verified_macros': {k: v['steps'] for k, v in library.concepts.items()} if adaptive else {},
                      'verified_prior': library.prior if adaptive else {}})


def attempt(library, tasks, before, proposal, generation, direct=False):
    if proposal is None:
        return library, before, {'accepted': False, 'reason': 'invalid proposal', 'gains': [], 'losses': []}
    checked_program(proposal)
    if any(c['steps'] == proposal for c in library.concepts.values()):
        return library, before, {'accepted': False, 'reason': 'duplicate', 'gains': [], 'losses': []}
    candidate = restore(state(library))
    cid = f'rsi{len(candidate.concepts) + 1:03d}'
    candidate.concepts[cid] = {'steps': proposal, 'tasks': [], 'round': generation}
    after = measure(tasks, candidate, direct)
    verdict = decision(before, after)
    # Replay all tasks, comparing canonical records rather than tuple/list identity.
    if verdict['accepted']:
        replay = measure(tasks, candidate, direct)
        if sha(replay) != sha(after):
            raise RuntimeError('development replay differs; stop without a negative verdict')
        candidate.concepts[cid]['tasks'] = verdict['gains']
        return candidate, after, verdict
    return library, before, verdict


def hashes():
    return {p: file_sha(REPO / p) for p in SOURCES}


def prepare(model_path, llama_cli):
    if (ROOT / 'profile.json').exists():
        return integrity()
    model_path, llama_cli = Path(model_path).resolve(), Path(llama_cli).resolve()
    with model_path.open('rb') as model:
        if model.read(4) != b'GGUF':
            raise ValueError('not a GGUF model')
    profile = {'at': now(), 'sources': hashes(), 'configuration': CFG, 'arms': ARMS,
               'runtime': sys.version, 'model_path': str(model_path), 'model_sha256': file_sha(model_path),
               'model_bytes': model_path.stat().st_size, 'llama_cli': str(llama_cli),
               'llama_cli_sha256': file_sha(llama_cli), 'closed_weight_api_calls': 0,
               'scientific_scope': CFG['scope']}
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(ROOT, 0o700)
    for p in SOURCES:
        dest = ROOT / 'source-archive' / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((REPO / p).read_bytes())
    atomic(ROOT / 'profile.json', profile)
    status('PREPARED', model_calls_started=False, spend_eur=0)
    return profile


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    if value['sources'] != hashes() or value['runtime'] != sys.version \
            or value['configuration'] != json.loads(canonical(CFG)) \
            or value['llama_cli_sha256'] != file_sha(value['llama_cli']):
        raise RuntimeError('RSI sources, runtime, configuration or executable changed')
    return value


def checkpoint(replica, arm, generation):
    return ROOT / 'generations' / str(replica) / arm / f'{generation}.json'


def research(replica, final_library, profile):
    tasks = corpus(replica, 'research', CFG['research_tasks'])
    out = []
    for condition, library in (('fresh', Library()), ('retained', restore(state(final_library)))):
        before = measure(tasks, library)
        accepted, elapsed = 0, 0.0
        for i in range(CFG['research_calls_per_condition']):
            reply = propose(prompt_for(tasks, before, library, True), f'research-{replica}-{condition}-{i}', profile)
            library, before, verdict = attempt(library, tasks, before, reply['program'], 6)
            accepted += verdict['accepted']; elapsed += reply['seconds']
        out.append({'condition': condition, 'accepted': accepted, 'model_seconds': elapsed,
                    'accepted_per_call': accepted / CFG['research_calls_per_condition']})
    return out


def run():
    profile = integrity()
    started = time.monotonic()
    if file_sha(profile['model_path']) != profile['model_sha256']:
        raise RuntimeError('local model weights changed')
    with (ROOT / 'process.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finals = {}
        for replica in CFG['replicas']:
            anchors = corpus(replica, 'anchors', CFG['anchors'])
            for arm in ARMS:
                library, seen = Library(), anchors[:]
                for generation in range(1, CFG['generations'] + 1):
                    if time.monotonic() - started > CFG['max_wall_s']:
                        raise RuntimeError('wall budget reached; preserve partial run')
                    integrity()
                    seen += corpus(replica, f'dev-{generation}', CFG['dev_per_generation'])
                    path = checkpoint(replica, arm, generation)
                    if path.exists():
                        saved = json.loads(path.read_text())
                        library = restore(saved['library']); continue
                    if arm == 'echo_reset':
                        library = Library()
                    direct = arm == 'llm_only'
                    before = measure(seen, library, direct)
                    elapsed = 0.0
                    if arm == 'frozen':
                        verdict = {'accepted': False, 'reason': 'frozen control', 'gains': [], 'losses': []}
                        after = before
                    else:
                        if arm == 'random':
                            rng = random.Random(int(sha([replica, generation])[:12], 16))
                            proposal = [[rng.choice(OPS)] for _ in range(rng.choice((2, 3)))]
                        else:
                            reply = propose(prompt_for(seen, before, library, arm != 'llm_only'),
                                            f'{replica}-{arm}-{generation}', profile)
                            proposal, elapsed = reply['program'], reply['seconds']
                        library, after, verdict = attempt(library, seen, before, proposal, generation, direct)
                    # ECHO updates its existing verified prior, not the frozen core.
                    if arm in ('echo_reset', 'echo_recursive') and verdict['accepted']:
                        proposed_prior = learn.prior_from({r['task']: r['program'] for r in after if r['correct']})
                        ranked = restore(state(library)); ranked.prior = proposed_prior
                        check = measure(seen, ranked)
                        if not decision(after, check)['losses']:
                            if sha(check) != sha(measure(seen, ranked)):
                                raise RuntimeError('prior update replay differs')
                            library, after = ranked, check
                    saved = {'replica': replica, 'arm': arm, 'generation': generation,
                             'library': state(library), 'before': before, 'after': after,
                             'verdict': verdict, 'model_seconds': elapsed,
                             'development_only': True, 'at': now()}
                    atomic(path, saved)
                    status('DEVELOPMENT', replica=replica, arm=arm, generation=generation,
                           accepted=verdict['accepted'], observed_gains=len(verdict['gains']))
                finals[replica, arm] = library
        # All generation snapshots are sealed before any private final task is measured.
        atomic(ROOT / 'exam-freeze.json', {'at': now(), 'profile_sha256': sha(profile),
            'libraries': {f'{r}/{a}': sha(state(v)) for (r, a), v in finals.items()}})
        results = []
        for replica in CFG['replicas']:
            exam = corpus(replica, 'final-exam', CFG['exam_tasks'])
            for arm in ARMS:
                library = finals[replica, arm]
                rows = measure(exam, library, arm == 'llm_only')
                if sha(rows) != sha(measure(exam, library, arm == 'llm_only')):
                    raise RuntimeError('final replay differs')
                # Score each stored generation only now; never return these answers to a model.
                curve = []
                for gen in range(1, 6):
                    snapshot = restore(json.loads(checkpoint(replica, arm, gen).read_text())['library'])
                    curve.append(sum(r['correct'] for r in measure(exam, snapshot, arm == 'llm_only')))
                result = {'replica': replica, 'arm': arm, 'rows': rows, 'curve': curve,
                          'solved': sum(r['correct'] for r in rows), 'total': len(rows), 'replay_ok': True}
                atomic(ROOT / 'exam' / f'{replica}-{arm}.json', result)
                results.append(result)
        # Separate research efficiency assay; final libraries are not changed by it.
        assays = {str(rep): research(rep, finals[rep, 'echo_recursive'], profile) for rep in CFG['replicas']}
        atomic(ROOT / 'research.json', assays)
        accepted_rows = [json.loads(p.read_text()) for p in (ROOT / 'generations').glob('*/*/*.json')]
        green_capability = all(next(r['solved'] for r in results if r['replica'] == rep and r['arm'] == 'echo_recursive')
            >= max(r['solved'] for r in results if r['replica'] == rep and r['arm'] != 'echo_recursive') + 3
            for rep in CFG['replicas'])
        green_research = all(rows[1]['accepted_per_call'] > rows[0]['accepted_per_call'] for rows in assays.values())
        repeat_improvements = all(sum(row['verdict']['accepted'] for row in accepted_rows
            if row['replica'] == rep and row['arm'] == 'echo_recursive') >= 2 for rep in CFG['replicas'])
        summary = {'at': now(), 'scope': CFG['scope'], 'S6_green': False, 'capability_green': green_capability,
                   'research_green': green_research, 'successive_improvements': repeat_improvements,
                   'RSI1_green': green_capability and green_research and repeat_improvements,
                   'exam': [{k: r[k] for k in ('replica', 'arm', 'solved', 'total', 'curve', 'replay_ok')} for r in results],
                   'research': assays, 'spend_eur': 0, 'profile_sha256': sha(profile)}
        integrity()
        atomic(ROOT / 'result.json', summary)
        write_report(summary)
        status('DONE', RSI1_green=summary['RSI1_green'], S6_green=False)


def write_report(summary):
    # Rendering is separate from measurement; exported figures show measured scores.
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'matplotlib-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = dict(zip(ARMS, ('#999999', '#ffb454', '#8fc7ff', '#ffffff', '#c190ff')))
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#140c23')
    ax.set_facecolor('#140c23')
    for arm in ARMS:
        rows = [r['curve'] for r in summary['exam'] if r['arm'] == arm]
        for row in rows:
            ax.plot(range(1, 6), row, color=colors[arm], alpha=.25, linewidth=1)
        ax.plot(range(1, 6), [sum(row[i] for row in rows)/len(rows) for i in range(5)],
                color=colors[arm], marker='o', linewidth=2, label=arm)
    ax.set(xlabel='Generación', ylabel='Tareas exactas / 48', xticks=range(1, 6), ylim=(0, 48),
           title='ECHO RSI 1 · banco sintético reservado')
    ax.legend(loc='best'); ax.grid(alpha=.15)
    fig.text(.1, .01, 'Líneas finas: réplicas individuales. Líneas gruesas: media. No es puntuación ARC.', fontsize=9)
    fig.tight_layout(rect=(0, .035, 1, 1))
    fig.savefig(ROOT / 'generation-scores.svg'); fig.savefig(ROOT / 'generation-scores.png', dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4), facecolor='#140c23'); ax.set_facecolor('#140c23')
    for i, (replica, rows) in enumerate(summary['research'].items()):
        ax.bar(i-.18, rows[0]['accepted_per_call'], width=.35, color='#999999', label='Fresco' if i == 0 else None)
        ax.bar(i+.18, rows[1]['accepted_per_call'], width=.35, color='#c190ff', label='Retenido' if i == 0 else None)
    ax.set(xticks=range(len(summary['research'])), xticklabels=list(summary['research']),
           ylabel='Mejoras aceptadas / llamada', xlabel='Réplica', ylim=(0, 1),
           title='Productividad del investigador · dos llamadas por condición')
    ax.legend();fig.tight_layout();fig.savefig(ROOT / 'research-productivity.svg');plt.close(fig)
    (REPO / 'docs/ECHO-RSI1-RESULTS.md').write_text('# ECHO RSI 1 resultados privados\n\n'
        + 'Banco sintético de biblioteca DSL; S6 y ARC no cambian.\n\n```json\n'
        + json.dumps(summary, indent=2) + '\n```\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run', 'status'))
    parser.add_argument('--model', type=Path)
    parser.add_argument('--llama-cli', type=Path, default=Path('/usr/bin/llama-cli'))
    args = parser.parse_args()
    if args.command == 'prepare':
        if args.model is None:
            parser.error('--model is required')
        prepare(args.model, args.llama_cli)
    elif args.command == 'run':
        try:
            run()
        except Exception as exc:
            status('BLOCKED', error=type(exc).__name__, message=str(exc))
            raise
    else:
        print((ROOT / 'status.json').read_text())


if __name__ == '__main__':
    main()
