"""S6-B0 training-only controller. Run with the separate ARC environment.

python -m seed.game_selfimprove baseline ROOT
python -m seed.game_selfimprove run ROOT --model Qwen/Qwen2.5-Coder-7B-Instruct
Exam orchestration lives separately, outside the GPU training bundle.
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import resource
import signal
import sys
import time

from echo_arc import strategy

REPO = Path(__file__).resolve().parents[1]
PROTECTED = ('echo_arc/agent.py', 'echo_arc/runner.py', 'echo_arc/strategy.py',
             'seed/arc3gym.py', 'seed/game_selfimprove.py',
             'echo_arc/__init__.py', 'seed/__init__.py', 'docs/ECHO45-S6-B-DESIGN.md')
A = [(v, sd, 0, 600) for v in (2, 3) for sd in range(8)]
B = [(v, sd, 0, 600) for v in (2, 3) for sd in range(20, 24)]
TYPES = ('P1', 'P2', 'P3', 'P4')
CALLS, ROUND_SIZE = 30, 5


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(canonical(value) + '\n')
    tmp.replace(path)


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in PROTECTED}


def integrity(root):
    expected = json.loads((Path(root) / 'profile.json').read_text())
    if expected['sources'] != hashes():
        raise RuntimeError('protected sources changed')
    return expected


def events(path):
    prev, out = '0' * 64, []
    for line in path.read_text().splitlines() if path.exists() else []:
        body = json.loads(line)
        claimed = body.pop('hash')
        if body.get('prev') != prev or sha(body) != claimed:
            raise ValueError('invalid journal chain')
        body['hash'] = claimed
        prev = claimed
        out.append(body)
    return out


def journal(path, event):
    old = events(path)
    body = dict(event, prev=old[-1]['hash'] if old else '0' * 64)
    body['hash'] = sha(body)
    # A round is small. Replacing the whole file prevents a partial last line after a crash.
    tmp = path.with_suffix('.tmp')
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(''.join(canonical(e) + '\n' for e in old + [body]))
    tmp.replace(path)


class GameDeadline(BaseException):
    pass


def worker_init():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    def alarm(*_):
        raise GameDeadline()
    signal.signal(signal.SIGALRM, alarm)


def play_one(item):
    policy, spec, agent_name = item
    from echo_arc import runner, agent
    from seed import arc3gym as gym
    v, sd, rep, budget = spec
    gym.VERSION = v
    agent._COMP_CACHE.clear()
    runner.AGENTS['s6b'] = strategy.agent_class(policy)
    runner.AGENTS.setdefault('random', gym._Random)
    signal.alarm(180)
    try:
        env = gym.GymEnv(sd)
        rec = runner.play(env, budget, runner.seed_for(env.game_id, rep), agent_name=agent_name)
        rec.update(version=v, seed=sd, rep=rep, budget=budget)
        rec['score'] = runner.official_game_score(rec['actions_per_level'], env.baseline_actions)
        return rec
    finally:
        signal.alarm(0)


def measure(root, policy, specs, workers=4, agent_name='s6b'):
    """One result per game, atomically cached under exact inputs and source identities."""
    root = Path(root)
    profile = integrity(root)
    records, missing = {}, []
    for spec in specs:
        key = sha({'sources': profile['sources'], 'policy': policy, 'spec': spec, 'agent': agent_name})
        p = root / 'cache' / (key + '.json')
        if p.exists():
            record = json.loads(p.read_text())
            if record['key'] != key or sha(record['record']) != record['digest']:
                raise ValueError('measurement cache corrupt')
            records[tuple(spec)] = record['record']
        else:
            missing.append((policy, spec, agent_name))
    if missing:
        with mp.get_context('spawn').Pool(workers, initializer=worker_init) as pool:
            it = pool.imap_unordered(play_one, missing, chunksize=1)
            for _ in missing:
                # A hard deadline also covers a dead worker / result lost before delivery.
                rec = it.next(timeout=210)
                spec = (rec['version'], rec['seed'], rec['rep'], rec['budget'])
                key = sha({'sources': profile['sources'], 'policy': policy, 'spec': spec, 'agent': agent_name})
                atomic(root / 'cache' / (key + '.json'), {'key': key, 'record': rec, 'digest': sha(rec)})
                records[spec] = rec
    rows = [records[tuple(s)] for s in specs]
    return {'levels': sum(r['levels_completed'] for r in rows), 'score': sum(r['score'] for r in rows),
            'rows': rows, 'trace_digest': sha(rows)}


def public_rows(result):
    # Do not send seed, family labels, optimal/human action counts or hidden simulator state.
    return [{'index': i, 'levels': r['levels_completed'], 'actions': len(r['actions']),
             'actions_per_level': r['actions_per_level'], 'resets': r['resets'],
             'model': r.get('model', {}), 'last_actions': r['actions'][-12:]}
            for i, r in enumerate(result['rows'])]


def feedback_rows(result):
    rows = public_rows(result)
    # Model hypotheses contain pixel positions/colours: omit them from request statistics.
    for r in rows:
        r['model'] = {k: v for k, v in r['model'].items() if k != 'hypotheses' and k != 'wall_colours'}
        r['last_actions'] = [[a[0], a[1]] for a in r['last_actions']]
    return rows


def reconstruct(path):
    policy = strategy.EMPTY
    stats = {t: [0, 0] for t in TYPES}
    accepted = []
    for e in events(path):
        if e['kind'] == 'verdict':
            stats[e['type']][0] += 1
            if e['verdict'] == 'accepted':
                policy = strategy.parse(e['answer'])
                stats[e['type']][1] += 1
                accepted.append(e)
    return policy, stats, accepted


def requests(arm, round_id, policy, stats, result, accepted):
    rows = sorted(feedback_rows(result), key=lambda r: (r['levels'], r['index']))
    pending = {k: list(v) for k, v in stats.items()}
    out = []
    common = ('Propose ONE general control strategy for ECHO v5.7. Return ONLY JSON, no prose/code. '
              'Schema {"defaults": {PARAM: INT}, "rules": [{"when": {FEATURE: [OP, INT]}, "set": {PARAM: INT}}]}. '
              'Max 8 rules; OP is eq, ge or le. Empty defaults/rules allowed. '
              'Allowed parameter integer bounds: ' + canonical(strategy.LIMITS) + '. '
              'Observable feature bounds: ' + canonical(strategy.FEATURES) + '. '
              'Base parameters: HOLD=40, MIN_EVIDENCE=8, WALL_MIN=3, MARGIN=2, BABBLE=2, TEST_WINDOW=4, '
              'WINDOW=16, MAX_PER_TARGET=60, MIN_CLICK_EVIDENCE=2, MAX_UNITS=16, EXPLORE=1. '
              'HOLD delays another reset/mode key; evidence identifies the body; WALL_MIN rejects false walls; '
              'BABBLE tries movement keys; TEST_WINDOW observes remote effects; WINDOW tracks changed pixels; '
              'MAX_PER_TARGET limits retries; MAX_UNITS bounds click planning; EXPLORE=1 explores frontiers. '
              'Your policy runs before every action and may condition on the observed features. '
              'Improve levels without regressions. Budget 600 actions per game. No game identifiers/colours/coordinates. ')
    for j in range(ROUND_SIZE):
        if arm == 'fijo':
            typ = 'P4'
            data = {'failures': rows[:3]}
            ask = 'Here are three games I fail. Propose a better general strategy.'
        else:
            eligible = TYPES if accepted else ('P1', 'P2', 'P4')
            typ = max(eligible, key=lambda t: (pending[t][1] * 1000 // (pending[t][0] + 1)
                                           + 300 // (pending[t][0] + 1),
                                           -((TYPES.index(t) - round_id - j) % 4)))
            pending[typ][0] += 1
            if typ == 'P1':
                near = max((r for r in rows if r['levels'] < 5), key=lambda r: r['levels'], default=rows[0])
                data, ask = {'almost': near}, 'Fix the control decisions for this almost-completed game.'
            elif typ == 'P2':
                data, ask = {'failures': rows[:5]}, 'Find a shared exploration failure and repair it generally.'
            elif typ == 'P3':
                data, ask = {'last_accepted': accepted[-1]['policy'], 'failures': rows[:3]}, 'Generalize this verified improvement to remaining failures.'
            else:
                data = {'failures': rows[:3], 'asking_statistics': stats,
                        'accepted_changes': [e['policy'] for e in accepted[-3:]]}
                ask = 'Use my diary to propose the next useful control strategy.'
        prompt = common + ask + '\nCurrent strategy: ' + canonical(policy) + '\nEvidence: ' + canonical(data)
        out.append({'id': round_id * ROUND_SIZE + j, 'type': typ, 'prompt': prompt})
    return out


def hf_proposer(model_id):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = 'left'
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map='auto')
    model.eval()
    def call(prompts, seed):
        torch.manual_seed(seed)
        answers, usages = [], []
        texts = [tok.apply_chat_template([{'role': 'user', 'content': p}], tokenize=False,
                                        add_generation_prompt=True) for p in prompts]
        for start in range(0, len(texts), 2):
            chunk = texts[start:start + 2]
            enc = tok(chunk, padding=True, truncation=False, return_tensors='pt').to(model.device)
            if enc['input_ids'].shape[1] > 6000:
                raise ValueError('prompt too large; refusing silent truncation')
            with torch.no_grad():
                out = model.generate(**enc, max_new_tokens=400, do_sample=True, temperature=0.7,
                                     top_p=0.95, pad_token_id=tok.pad_token_id or tok.eos_token_id)
            raw = tok.batch_decode(out[:, enc['input_ids'].shape[1]:], skip_special_tokens=True)
            answers.extend(raw)
            usages.extend({'prompt_tokens': len(tok.encode(t)), 'completion_tokens': len(tok.encode(a)),
                           'cost_usd': 0} for t, a in zip(chunk, raw))
        return answers, usages
    return call


def baseline(root, workers):
    root = Path(root)
    profile = {'sources': hashes(), 'calls': CALLS, 'round_size': ROUND_SIZE,
               'A': A, 'B': B, 'schema': 'echo45-s6-b0'}
    if (root / 'profile.json').exists():
        if json.loads((root / 'profile.json').read_text()) != json.loads(canonical(profile)):
            raise ValueError('existing profile differs')
    else:
        atomic(root / 'profile.json', profile)
    for name, specs in [('A', A), ('B', B)]:
        res = measure(root, strategy.EMPTY, specs, workers)
        atomic(root / ('baseline-' + name + '.json'), res)
        print(canonical({'baseline': name, 'levels': res['levels'], 'score': res['score']}), flush=True)


def run(root, proposer, workers):
    root = Path(root)
    integrity(root)
    for round_id in range(CALLS // ROUND_SIZE):
        for arm in ('fijo', 'echo'):
            path = root / arm / 'journal.jsonl'
            old = events(path)
            done = {e['id'] for e in old if e['kind'] == 'verdict'}
            if all(round_id * ROUND_SIZE + j in done for j in range(ROUND_SIZE)):
                continue
            policy, stats, accepted = reconstruct(path)
            previous = measure(root, policy, A, workers)
            batch = next((e for e in old if e['kind'] == 'answers' and e['round'] == round_id), None)
            if batch is None:
                reqs = requests(arm, round_id, policy, stats, previous, accepted)
                # Save the exact inputs before requesting; on resume reuse them.
                saved = next((e for e in old if e['kind'] == 'requests' and e['round'] == round_id), None)
                if saved is not None:
                    reqs = saved['requests']
                else:
                    journal(path, {'kind': 'requests', 'round': round_id, 'requests': reqs})
                answers, usages = proposer([r['prompt'] for r in reqs], 570000 + round_id)
                if len(answers) != ROUND_SIZE or len(usages) != ROUND_SIZE:
                    raise ValueError('proposer result count mismatch')
                batch = {'kind': 'answers', 'round': round_id, 'requests': reqs,
                         'answers': answers, 'usages': usages}
                journal(path, batch)  # Persist every paid/GPU answer BEFORE verification.
            for req, answer, usage in zip(batch['requests'], batch['answers'], batch['usages']):
                if req['id'] in done:
                    continue
                integrity(root)
                policy, _, _ = reconstruct(path)
                event = {'kind': 'verdict', 'id': req['id'], 'round': round_id, 'type': req['type'],
                         'prompt_sha256': sha(req['prompt']), 'answer': answer, 'usage': usage}
                try:
                    candidate = strategy.parse(answer)
                except ValueError as exc:
                    event.update(verdict='V1', reason=str(exc))
                else:
                    event['policy'] = candidate
                    prior = measure(root, policy, A, workers)
                    try:
                        trial = measure(root, candidate, A, workers)
                        # Independent second run, separate empty cache namespace.
                        repeat = root / 'determinism' / strategy.digest(candidate)
                        atomic(repeat / 'profile.json', integrity(root))
                        replay = measure(repeat, candidate, A, workers)
                    except (Exception, GameDeadline) as exc:
                        event.update(verdict='V2', reason=type(exc).__name__)
                    else:
                        event.update(prior_A=prior['levels'], trial_A=trial['levels'],
                                     trial_trace=trial['trace_digest'])
                        if replay['trace_digest'] != trial['trace_digest']:
                            event.update(verdict='V2', reason='non deterministic')
                        elif trial['levels'] < prior['levels'] + 2:
                            event.update(verdict='V3', reason='fewer than two additional A levels')
                        else:
                            prior_b = measure(root, policy, B, workers)
                            trial_b = measure(root, candidate, B, workers)
                            event.update(prior_B=prior_b['levels'], trial_B=trial_b['levels'],
                                         prior_B_score=prior_b['score'], trial_B_score=trial_b['score'])
                            if trial_b['levels'] < prior_b['levels'] or trial_b['score'] < prior_b['score']:
                                event.update(verdict='V4', reason='B regression')
                            else:
                                event.update(verdict='accepted', reason='V1-V4 pass')
                journal(path, event)
                print(canonical({'arm': arm, 'call': req['id'] + 1, 'verdict': event['verdict'],
                                 'prior_A': event.get('prior_A'), 'trial_A': event.get('trial_A')}), flush=True)
                integrity(root)
    export(root)


def export(root):
    root = Path(root)
    policies = {'semilla': strategy.EMPTY}
    for arm in ('fijo', 'echo'):
        policy, stats, accepted = reconstruct(root / arm / 'journal.jsonl')
        count = sum(v[0] for v in stats.values())
        if count != CALLS:
            raise ValueError('incomplete campaign')
        policies[arm] = policy
    raw_policy = strategy.EMPTY
    for e in events(root / 'echo' / 'journal.jsonl'):
        if e['kind'] == 'verdict' and e['verdict'] not in ('V1', 'V2'):
            raw_policy = strategy.parse(e['answer'])
    policies['sinfiltro'] = raw_policy
    atomic(root / 'strategies.json', policies)
    atomic(root / 'completed.json', {'sources': integrity(root)['sources'],
                                    'strategies_sha256': sha(policies), 'calls_per_arm': CALLS,
                                    'cost_usd': 0, 'closed': time.time()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('baseline', 'run', 'export'))
    parser.add_argument('root', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--model', default='Qwen/Qwen2.5-Coder-7B-Instruct')
    args = parser.parse_args()
    if args.command == 'baseline':
        baseline(args.root, args.workers)
    elif args.command == 'run':
        run(args.root, hf_proposer(args.model), args.workers)
    else:
        export(args.root)


if __name__ == '__main__':
    main()
