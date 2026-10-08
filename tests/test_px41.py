"""PX4-1 transport boundary, acknowledgement and completion regressions."""
import copy
import unittest
from echoai.nexus0.cause1.core import wsp
from echoai.nexus0.px41.core import Gateway, TTL, ACK_TIMEOUT, EXEC_TIMEOUT


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_000_000_000
        self.gate = Gateway()
        self.request = dict(wsp=wsp(0), seq=1, published_ns=self.now)
        self.frame = dict(received_ns=self.now, position_mm=[0, 0, 2500], speed_mm_s=0,
                          armed=True, authority=True, failsafe=False)

    def propose(self, request=None, frame=None, now=None):
        return self.gate.propose(self.request if request is None else request,
                                 self.frame if frame is None else frame, self.now if now is None else now)

    def ack(self, **changes):
        value = dict(system=1, component=1, command=192, result=0, received_ns=self.now+1)
        value.update(changes)
        return self.gate.acknowledge(value, self.now+1)

    def test_legal(self):
        self.assertEqual(self.propose()['target_mm'], [0, 1000, 2500])

    def test_south_and_hold(self):
        for action, target in [(1, -1000), (6, 0)]:
            self.gate = Gateway()
            self.assertEqual(self.propose(dict(self.request, wsp=wsp(action)))['target_mm'][1], target)

    def test_bad_wsp(self):
        for value in ['', '00', 'gg'*16, wsp(0).upper(), 1, None, wsp(0)[:-2]+'01']:
            # The all-numeric canonical packet is unchanged by uppercase.
            if value == wsp(0):
                continue
            self.assertFalse(self.propose(dict(self.request, wsp=value))['allowed'])

    def test_schema(self):
        for request in [None, {}, [], dict(self.request, extra=1), dict(self.request, seq=True),
                        dict(self.request, published_ns=1.0), dict(self.request, seq=-1)]:
            self.assertFalse(self.gate.propose(request, self.frame, self.now)['allowed'])

    def test_expiry_and_future(self):
        for stamp in [self.now-TTL-1, self.now+1, -1]:
            self.assertFalse(self.propose(dict(self.request, published_ns=stamp))['allowed'])

    def test_envelope(self):
        for position in [[5001, 0, 2500], [0, 4001, 2500], [0, 0, 1799], [0, 0, 3201]]:
            self.assertFalse(self.propose(frame=dict(self.frame, position_mm=position))['allowed'])

    def test_authority(self):
        for key, value in [('authority', False), ('armed', False), ('failsafe', True)]:
            self.assertFalse(self.propose(frame=dict(self.frame, **{key: value}))['allowed'])

    def test_telemetry(self):
        for change in [dict(received_ns=self.now-TTL-1), dict(received_ns=self.now+1),
                       dict(position_mm=[0, 0, 2.5]), dict(position_mm=[0, 0]),
                       dict(speed_mm_s=-1), dict(armed=1), dict(speed_mm_s=3001)]:
            self.assertFalse(self.propose(frame=dict(self.frame, **change))['allowed'])

    def test_busy_and_replay(self):
        self.assertTrue(self.propose()['allowed'])
        self.assertFalse(self.propose()['allowed'])
        self.assertFalse(self.propose(dict(self.request, seq=2))['allowed'])

    def test_ack_not_arrival(self):
        self.propose()
        self.assertTrue(self.ack())
        self.assertEqual(self.gate.state, 'executing')

    def test_wrong_ack(self):
        self.propose()
        for change in [dict(system=2), dict(component=2), dict(command=400),
                       dict(received_ns=self.now), dict(result=True)]:
            self.assertFalse(self.ack(**change))
        self.assertEqual(self.gate.state, 'await_ack')

    def test_rejected_latches(self):
        self.propose()
        self.assertFalse(self.ack(result=2))
        self.assertEqual(self.gate.state, 'fault')
        self.assertFalse(self.propose()['allowed'])

    def test_ack_timeout(self):
        self.propose()
        frame = dict(self.frame, received_ns=self.now+ACK_TIMEOUT+1)
        self.assertEqual(self.gate.observe(frame, frame['received_ns']), 'fault')

    def test_execution_timeout(self):
        self.propose()
        self.ack()
        frame = dict(self.frame, received_ns=self.now+EXEC_TIMEOUT+1)
        self.assertEqual(self.gate.observe(frame, frame['received_ns']), 'fault')

    def test_three_distinct_samples(self):
        self.propose()
        self.ack()
        for step in range(2, 5):
            frame = dict(self.frame, received_ns=self.now+step, position_mm=[0, 1000, 2500])
            state = self.gate.observe(frame, self.now+step)
            self.assertEqual(state, 'complete' if step == 4 else 'executing')
            self.assertEqual(self.gate.observe(frame, self.now+step), state)
        self.assertFalse(self.propose()['allowed'])

    def test_arrival_requires_slow(self):
        self.propose()
        self.ack()
        for step in range(2, 10):
            frame = dict(self.frame, received_ns=self.now+step, position_mm=[0, 1000, 2500], speed_mm_s=151)
            self.assertEqual(self.gate.observe(frame, self.now+step), 'executing')

    def test_loss_latches(self):
        self.propose()
        self.ack()
        self.assertEqual(self.gate.observe(dict(self.frame, authority=False), self.now+2), 'fault')
        self.assertFalse(self.propose()['allowed'])

    def test_no_input_mutation(self):
        before = copy.deepcopy((self.request, self.frame))
        self.propose()
        self.assertEqual(before, (self.request, self.frame))

    def test_return_value_not_capability(self):
        decision = self.propose()
        decision['target_mm'][0] = 999999
        self.assertEqual(self.gate.pending['target_mm'], [0, 1000, 2500])

    def test_envelope_lost(self):
        self.propose()
        self.ack()
        self.assertEqual(self.gate.observe(dict(self.frame, position_mm=[6000, 0, 2500]), self.now+2), 'fault')


if __name__ == '__main__':
    unittest.main()
