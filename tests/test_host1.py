import ast
import copy
from pathlib import Path
import unittest
from echoai.nexus0.host1.core import Host, signal, decode_signal
from echoai.nexus0.host1.world import tape, episode, audit_episode
from echoai.nexus0.host1.probes import communication
from echoai.nexus0.cause1.core import decode as motion


def sample():
    return copy.deepcopy(tape(20263901)[0])


class HostTests(unittest.TestCase):
    def test_learning_vs_button(self):
        a, b = [episode(20263901, p) for p in ('consequence', 'button')]
        self.assertEqual((a['useful'], b['useful']), (24, 12))
        self.assertEqual((a['dropped'], a['recovered']), (16, 16))
        self.assertTrue(a['no_button_updates'])
        self.assertFalse(b['no_button_updates'])

    def test_machine_tape_is_policy_independent(self):
        a, b = [episode(20263902, p) for p in ('consequence', 'button')]
        self.assertEqual(a['tape'], b['tape'])
        self.assertTrue(audit_episode(a))

    def test_button_absence_cancel_do_not_learn(self):
        h = Host()
        row = sample()
        before = h.snapshot()['bits']
        self.assertTrue(h.publish(row['claim'], row['claim']['published_ns']))
        self.assertEqual(h.snapshot()['bits'], before)
        h.cancel()
        self.assertEqual(h.snapshot()['bits'], before)
        self.assertEqual(h.snapshot()['counts'], [0]*512)

    def test_no_decay_or_recovery_with_time(self):
        h = Host()
        r = sample()
        h.publish(r['claim'], r['claim']['published_ns'])
        h.observe(r['receipt'], r['receipt']['received_ns'])
        bits, counts = h.snapshot()['bits'], h.snapshot()['counts']
        h.communicate(dict(now_ns=10**15, symbol=0, opportunity=False, budget=100, reserve=40,
                           busy=False, safe=True, flight=None))
        self.assertEqual((h.bits, h.counts), (bits, counts))

    def test_key_dimensions(self):
        h = Host()
        self.assertEqual(len({h.key(s, signal(a), c) for s in range(8) for a in range(1, 5) for c in range(16)}), 512)

    def test_unknown_is_not_trusted(self):
        self.assertIsNone(Host().choose([0, 1], signal(1), 0))

    def test_replay_receipt_and_claim(self):
        h = Host()
        e = sample()
        c, r = e['claim'], e['receipt']
        self.assertTrue(h.publish(c, c['published_ns']))
        self.assertTrue(h.observe(r, r['received_ns'])['updated'])
        state = h.snapshot()
        self.assertFalse(h.observe(r, r['received_ns'])['updated'])
        self.assertFalse(h.publish(c, r['received_ns']))
        self.assertEqual(h.snapshot(), state)

    def test_bad_receipts_never_learn(self):
        for field, value in [('seq', 99), ('wsp', 'ff'*16), ('ack_ns', 0), ('after_ns', 0),
                             ('received_ns', 0), ('accepted', False), ('complete', False),
                             ('extract', 'trust me'), ('position_mm', [True, 0, 2500])]:
            with self.subTest(field=field):
                h = Host()
                e = sample()
                h.publish(e['claim'], e['claim']['published_ns'])
                now = e['receipt']['received_ns']
                e['receipt'][field] = value
                self.assertFalse(h.observe(e['receipt'], now)['updated'])
                self.assertEqual(h.counts, [0]*512)

    def test_freshness_and_clock(self):
        h = Host()
        e = sample()
        c, r = e['claim'], e['receipt']
        self.assertFalse(h.publish(c, c['published_ns']-1))
        self.assertTrue(h.publish(c, c['published_ns']))
        self.assertFalse(h.observe(r, r['after_ns']+250_000_001)['updated'])
        self.assertFalse(h.observe(r, r['received_ns'])['updated'])

    def test_pending_claim_cannot_live_forever(self):
        h = Host()
        e = sample()
        h.publish(e['claim'], e['claim']['published_ns'])
        r = e['receipt']
        r['after_ns'] += 20_000_000_000
        r['received_ns'] += 20_000_000_000
        self.assertFalse(h.observe(r, r['received_ns'])['updated'])

    def test_physical_replay_is_not_duplicate_training(self):
        from echoai.nexus0.host1.replay import replay
        value = replay()
        self.assertTrue(value['valid'])
        self.assertEqual(value['flights'], 3)
        self.assertEqual([v['n'] for v in value['authority']], [3, 3])
        self.assertFalse(any(v['trusted'] for v in value['authority']))

    def test_bad_claims(self):
        for field, value in [('source', 8), ('context', -1), ('seq', True), ('sign', signal(0)),
                             ('sign', signal(1, False)), ('target_mm', [0, 0]), ('wsp', 'ff'*16)]:
            e = sample()
            e['claim'][field] = value
            self.assertFalse(Host().publish(e['claim'], 1_000_000_000))

    def test_receipt_cannot_supply_reward_or_source(self):
        for key in ('reward', 'source', 'sign', 'context'):
            e = sample()
            h = Host()
            h.publish(e['claim'], e['claim']['published_ns'])
            e['receipt'][key] = 1
            self.assertFalse(h.observe(e['receipt'], e['receipt']['received_ns'])['updated'])

    def test_snapshot_and_claim_are_copied(self):
        e = sample()
        h = Host()
        h.publish(e['claim'], e['claim']['published_ns'])
        e['claim']['target_mm'][0] = 9999
        self.assertEqual(h.pending['target_mm'][0], 0)
        s = h.snapshot()
        s['bits'][0] = 255
        s['pending']['target_mm'][0] = 8888
        self.assertEqual(h.bits[0], 0)
        self.assertEqual(h.pending['target_mm'][0], 0)

    def test_wsp_and_communication_gate(self):
        self.assertTrue(all(r['ok'] for r in communication()))
        for symbol in range(1, 5):
            self.assertEqual(decode_signal(signal(symbol)), symbol)
            self.assertEqual(len(bytes.fromhex(signal(symbol, False))), 16)
            with self.assertRaises(ValueError):
                motion(signal(symbol, False))

    def test_integer_core(self):
        path = Path(__file__).resolve().parents[1]/'nexus0/host1/core.py'
        tree = ast.parse(path.read_text())
        self.assertFalse(any(isinstance(n, ast.Constant) and type(n.value) is float for n in ast.walk(tree)))
        self.assertFalse(any(isinstance(n, ast.Div) for n in ast.walk(tree)))

    def test_flight_candidate_still_needs_safe_gate(self):
        import json
        from echoai.nexus0.safe1.core import Supervisor
        from echoai.nexus0.safe1.functional import fixture
        root = Path(__file__).resolve().parents[1]
        model = json.loads((root/'lab/power1/model.json').read_text())
        h, r, e = fixture(1)
        candidate = Host().communicate(dict(now_ns=h['now_ns'], symbol=1, opportunity=True,
                       budget=100, reserve=40, busy=False, safe=True, flight=r['wsp']))
        self.assertEqual(candidate['channel'], 'flight_candidate')
        h['frame']['failsafe'] = True
        self.assertFalse(Supervisor(model).submit(dict(r, wsp=candidate['wsp']), h, e)['allowed'])

    def test_communication_shares_pending_and_clock(self):
        h = Host()
        e = sample()
        h.publish(e['claim'], e['claim']['published_ns'])
        pending = h.snapshot()['pending']
        output = h.communicate(dict(now_ns=e['claim']['published_ns']+2, symbol=1, opportunity=True,
                                    budget=100, reserve=40, busy=True, safe=True, flight=None))
        self.assertEqual(output['channel'], 'silence')
        self.assertEqual(h.snapshot()['pending'], pending)
        self.assertTrue(h.observe(e['receipt'], e['receipt']['received_ns'])['updated'])

    def test_mutants_and_record_corruptions(self):
        from echoai.nexus0.host1.controls import mutants, corruptions
        self.assertTrue(all(mutants().values()))
        self.assertTrue(all(corruptions().values()))


if __name__ == '__main__':
    unittest.main()
