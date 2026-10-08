"""Three existing nominal flights: new source hypotheses, no new physical flights."""
import json
from echoai.nexus0.compose1.bench import ECHOAI
from echoai.nexus0.safe1_v2.evaluate import audit
from echoai.nexus0.px41.evaluate import digest
from .core import Host, signal, extract


def replay():
    roots = [ECHOAI/'lab/safe1/development/nominal', ECHOAI/'lab/safe1-v2/validation/nominal',
             ECHOAI/'lab/safe1-v2/confirmation/nominal']
    inputs = []
    for root in roots:
        proof = audit(root)
        if not proof['valid']:
            raise ValueError('invalid physical parent '+str(proof))
        rows = [json.loads(line) for line in (root/'out/trace.jsonl').read_text().splitlines()]
        send = next(r for r in rows if r['kind'] == 'send')
        ack = next(r['ack'] for r in rows if r['kind'] == 'ack')
        # Predictions depend only on the prior command, never on the measured arrival.
        targets = [list(send['target_mm']), list(send['target_mm'])]
        targets[1][1] += -2000 if bytes.fromhex(send['wsp'])[13] == 0 else 2000
        claims = [dict(source=s, sign=signal(1), context=0, seq=len(inputs)+1,
                       wsp=send['wsp'], target_mm=targets[s], published_ns=send['now_ns']) for s in range(2)]
        done = next(r for r in rows if r['kind'] == 'complete')
        after = next(r for r in rows if r['kind'] == 'sample' and r['now_ns'] >= done['now_ns'])
        pos = after['estimate']['position_mm']
        receipt = dict(seq=len(inputs)+1, wsp=send['wsp'], ack_ns=ack['received_ns'],
                       after_ns=after['now_ns'], received_ns=after['now_ns'], accepted=True, complete=True,
                       position_mm=pos, extract=extract(pos))
        inputs.append(dict(root=str(root.relative_to(ECHOAI)), claims=claims, receipt=receipt,
                           trace_sha256=digest(root/'out/trace.jsonl'),
                           ulog_sha256=digest(next(root.rglob('*.ulg'))), native=proof))
    host = Host()
    trials = []
    for source in range(2):
        for i, value in enumerate(inputs):
            # Explicit per-session epoch mapping; raw clocks are retained above.
            offset = (source*3+i+1)*10**12
            c = dict(value['claims'][source], published_ns=value['claims'][source]['published_ns']+offset)
            r = dict(value['receipt'])
            for key in ('ack_ns', 'after_ns', 'received_ns'):
                r[key] += offset
            published = host.publish(c, c['published_ns'])
            result = host.observe(r, r['received_ns'])
            trials.append(dict(source=source, flight=i, published=published, result=result))
    authorities = [host.authority(s, signal(1), 0) for s in range(2)]
    valid = (all(t['published'] and t['result']['updated']
                 and t['result']['outcome'] == ('confirmed' if t['source'] == 0 else 'contradicted') for t in trials)
             and [a['n'] for a in authorities] == [3, 3]
             and [a['score'] for a in authorities] == [256, 0]
             and not any(a['trusted'] for a in authorities))
    return dict(valid=valid, flights=3, source_observations=6, inputs=inputs, trials=trials, authority=authorities,
                scope='offline replay, three observations per source, insufficient for trusted status')
