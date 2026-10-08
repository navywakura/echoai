"""Private, precomputed machine tape and integer kinematic receipts; no Gazebo claim."""
import copy
import random
from .core import Host, signal, extract
from echoai.nexus0.cause1.core import wsp


def tape(seed):
    rng = random.Random(seed)
    identities = [0, 1]
    rng.shuffle(identities)
    rows = []
    now, seq = 1_000_000_000, 0
    for phase in range(3):
        for repetition in range(8):
            keys = [(s, symbol, context) for s in range(2) for symbol in range(1, 5) for context in range(2)]
            rng.shuffle(keys)
            for source, symbol, context in keys:
                good = identities[source] == ((symbol+context+seed+phase % 2) & 1)
                action = 0 if good else 1
                seq += 1
                claim = dict(source=source, sign=signal(symbol), context=context, seq=seq, wsp=wsp(action),
                             target_mm=[0, 1000, 2500], published_ns=now)
                # Public measured successor, not the source's assertion or button reward.
                actual = [rng.randint(-20, 20), (1000 if action == 0 else -1000)+rng.randint(-20, 20), 2500]
                receipt = dict(seq=seq, wsp=wsp(action), ack_ns=now+1, after_ns=now+100_000_000,
                               received_ns=now+110_000_000, accepted=True, complete=True,
                               position_mm=actual, extract=extract(actual))
                rows.append(dict(phase=phase, repetition=repetition, claim=claim, receipt=receipt))
                now += 1_000_000_000
    return rows


class Local:
    def call(self, request):
        if request['op'] == 'init':
            self.agent = Host(request['policy'])
            return dict(ready=True)
        op, args = request['op'], request['args']
        return getattr(self.agent, op)(*args)


def episode(seed, policy, consumer=None):
    consumer = consumer or Local()
    consumer.call(dict(op='init', policy=policy))
    machine = tape(seed)  # Complete before any consumer output. No feedback API exists.
    trace, evaluations = [], []
    transitions = {}
    prior = {}
    for index, event in enumerate(machine):
        c, r = event['claim'], event['receipt']
        key = (c['source'], c['sign'], c['context'])
        before = consumer.call(dict(op='authority', args=list(key)))
        published = consumer.call(dict(op='publish', args=[c, c['published_ns']]))
        after_button = consumer.call(dict(op='authority', args=list(key)))
        observed = consumer.call(dict(op='observe', args=[r, r['received_ns']]))
        after = consumer.call(dict(op='authority', args=list(key)))
        if event['phase'] and event['repetition'] == 0:
            prior[key] = before['trusted']
        if event['phase'] and after['trusted'] != prior[key]:
            transitions.setdefault((event['phase'],)+key, event['repetition']+1)
        trace.append(dict(**copy.deepcopy(event), before=before, published=published, after_button=after_button,
                          observed=observed, after=after))
        if (index+1) % 128 == 0:
            phase = event['phase']
            # Examination is read-only. Machine's prerecorded instructions determine utility.
            for symbol in range(1, 5):
                for context in range(2):
                    chosen = consumer.call(dict(op='choose', args=[[1, 0], signal(symbol), context]))
                    choices = [e for e in machine if e['phase'] == phase and e['repetition'] == 7
                               and e['claim']['sign'] == signal(symbol) and e['claim']['context'] == context]
                    chosen_row = next((e for e in choices if e['claim']['source'] == chosen), None)
                    useful = chosen_row is not None and chosen_row['receipt']['position_mm'][1] > 0
                    evaluations.append(dict(phase=phase, symbol=symbol, context=context, chosen=chosen, useful=useful))
    dropped = recovered = 0
    for phase in (1, 2):
        for source in range(2):
            for symbol in range(1, 5):
                for context in range(2):
                    key = (source, signal(symbol), context)
                    previous = next(e for e in trace if e['phase'] == phase and e['repetition'] == 0
                                    and (e['claim']['source'], e['claim']['sign'], e['claim']['context']) == key)['before']['trusted']
                    lag = transitions.get((phase,)+key)
                    dropped += previous and lag is not None and lag <= 3
                    recovered += not previous and lag is not None and lag <= 6
    return dict(seed=seed, policy=policy, tape=machine, trace=trace, evaluations=evaluations,
                useful=sum(e['useful'] for e in evaluations), total=len(evaluations), dropped=dropped,
                recovered=recovered, no_button_updates=all(t['before'] == t['after_button'] for t in trace),
                snapshot=consumer.call(dict(op='snapshot', args=[])))


def audit_episode(record):
    return record == episode(record['seed'], record['policy'])
