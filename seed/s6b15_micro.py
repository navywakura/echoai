"""Preregistered 2x2 transport/evidence ablation. DEVELOPMENT_A only.

The B14 accepted policy is a calibration fixture, not a main-arm starting state.
No PROBE2 winner, protected result or micro answer is supplied to pilot actors.
"""
import json
import time

from seed import s6b15 as r
from echo_arc import repair_experiments

CELLS = ((False, False), (True, False), (False, True), (True, True))
SEEDS = (730101, 730117, 730129)


def reference():
    root = r.PREVIOUS
    event = json.loads((root / 'steps/pilot/echo-698001/000.json').read_text())['event']
    measured = json.loads((root / 'primary/measurements/pilot/echo-698001/000/A.json').read_text())
    if event['verdict'] != 'accepted' or measured['levels'] != 378 \
            or measured['trace_digest'] != '4458a4c2e5f4d8ac6c46547fcbc62785e0aca93bd0bdecb6d23d7456d63c2d2c':
        raise RuntimeError('micro reference custody mismatch')
    if r.b.sha(measured['rows']) != measured['trace_digest']:
        raise RuntimeError('micro reference records were altered')
    return event['candidate'], measured, [event]


def gate(cells):
    return any(c['binding'] and c['numeric'] and c['passes_A'] and c['reproduced']
               and c['actual_operator'] == c['requested_operator'] and c.get('gain', 0) >= 2
               and not c.get('loss_indices') and c.get('levels') == 378 + c['gain'] for c in cells)


def evaluate(measure, label, response, req, policy, baseline):
    summary = dict(cell=label, binding=req['operator_binding'], numeric=req['numeric_summary'],
        requested_operator=req['requested_operator'], actual_operator=None, proposal=None,
        levels=None, gain=0, loss_indices=[], passes_A=False, reproduced=False,
        input_tokens=response['usage']['input_tokens'])
    try:
        proposal = r.prompts.check_answer(response['answer'], req)
        candidate = r.b.strategy(program=r.b.patch.append(policy['program'], proposal))
    except ValueError as exc:
        # A failed/truncated model proposal consumes its call. It is not a replay
        # failure, and it must not be re-sampled until something valid appears.
        return dict(summary, verdict='V1', reason=str(exc))
    result = r.b.reproduced(measure, label + '/A', candidate, r.b.A)
    diff = r.b.difference(baseline, result)
    return dict(summary, proposal=proposal, actual_operator=repair_experiments.operator({'proposal': proposal}),
        levels=result['levels'], gain=diff['gain'], loss_indices=diff['loss_indices'],
        passes_A=diff['gain'] >= 2 and not diff['loss_indices'], reproduced=True,
        trace_digest=result['trace_digest'], verdict='MEASURED')


def run():
    frozen = r.b.integrity()
    path = r.ROOT / 'micro.json'
    if path.exists():
        r.micro_gate()  # Validate custody; a negative result is still a valid result.
        return json.loads(path.read_text())
    r.publish('MICRO_RUNNING')
    started = time.monotonic()
    policy, old, history = reference()
    measure = r.measurement('primary')
    def only_a(name, candidate, specs, **kwargs):
        if list(map(tuple, specs)) != list(map(tuple, r.b.A)) or kwargs.get('observed', True) is not True:
            raise ValueError('micro can only measure the full observed development A partition')
        return measure(name, candidate, specs, **kwargs)
    baseline = r.b.reproduced(only_a, 'micro/baseline/A', policy, r.b.A)
    if baseline['trace_digest'] != old['trace_digest'] or baseline['levels'] != 378:
        raise RuntimeError('B14 378-level micro parity failed')
    summaries = []
    for seed in SEEDS:
        for binding, numeric in CELLS:
            label = f'micro/b{int(binding)}-n{int(numeric)}-{seed}'
            req = r.prompts.request('echo', 1, policy, baseline, history, numeric=numeric, bind=binding)
            if req['requested_operator'] != 'HOLD':
                raise RuntimeError('own-history initial waiting selection changed')
            result_path = r.ROOT / (label + '.json')
            if result_path.exists():
                record = json.loads(result_path.read_text())
                if record['request_sha256'] != r.b.sha(req) or record['profile_sha256'] != r.b.sha(frozen):
                    raise RuntimeError('micro result reconstruction differs')
                r.model.load(label, req, seed, r.ROOT, r.b.sha(frozen), audit_tokens=True)
                summaries.append(record['summary'])
                continue
            r.status('MICRO_PROPOSING', cell=label, completed=len(summaries), total=12)
            # An interrupted generation cannot be silently sampled again.
            if (r.ROOT / 'calls' / label / 'result.json').exists():
                response = r.model.load(label, req, seed, r.ROOT, r.b.sha(frozen), audit_tokens=True)
            else:
                response = r.model.propose(label, req, seed, r.ROOT, r.b.sha(frozen), r.b.MAX_CALLS)
            r.b.visible('requests', requests={label: [dict(id=1, type='MICRO_WAIT',
                        prompt=req['prompt_variants'][response['variant']])]})
            r.b.visible('answers', answers={'arms': {label: [dict(id=1, answer=response['answer'])]}})
            summary = dict(evaluate(only_a, label, response, req, policy, baseline), seed=seed)
            r.b.atomic(result_path, dict(summary=summary, profile_sha256=r.b.sha(frozen), request_sha256=r.b.sha(req)))
            summaries.append(summary)
            r.b.visible('proposal', type='MICRO_RESULT', verdict='A_PASS' if summary['passes_A'] else 'A_FAIL',
                        prompt=r.b.canonical(summary))
            r.status('MICRO_RESULT', completed=len(summaries), total=12,
                     cell=label, levels=summary['levels'], gain=summary['gain'], losses=len(summary['loss_indices']))
    artifacts = [r.ROOT / 'primary/measurements/micro/baseline/A.json',
                 r.ROOT / 'primary/measurements/micro/baseline/A/replay.json']
    for cell in summaries:
        artifacts += [r.ROOT / (cell['cell'] + '.json'), r.ROOT / 'calls' / cell['cell'] / 'result.json']
        if cell['reproduced']:
            artifacts += [r.ROOT / 'primary/measurements' / cell['cell'] / name
                          for name in ('A.json', 'A/replay.json')]
    result = dict(valid=True, promote=gate(summaries), cells=summaries, profile_sha256=r.b.sha(frozen),
        at=r.b.now(), seconds_this_invocation=time.monotonic()-started, model_calls=12,
        baseline_levels=378, baseline_digest=baseline['trace_digest'],
        protected_games=0, exam_opened=False, pilot_uses_micro_answers=False,
        artifacts={str(p.relative_to(r.ROOT)): r.model.digest_file(p) for p in artifacts})
    r.b.atomic(path, result)
    r.publish('MICRO_PASSED' if result['promote'] else 'MICRO_NO_PROMOTION')
    return result
