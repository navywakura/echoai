import json
from pathlib import Path
import sys
import time
import unittest

from echoai.nexus0.safe1.core import Lease, Supervisor
from echoai.nexus0.safe1.functional import CONDITIONS, episode, fixture
from echoai.nexus0.safe1.ipc import Channel, ChannelError

ROOT = Path(__file__).resolve().parents[1]
MODEL = json.loads((ROOT/'lab/power1/model.json').read_text())
WORKER = ROOT/'nexus0/safe1/assets/worker.py'


class SafetyTests(unittest.TestCase):
    def test_fault_matrix(self):
        for case in CONDITIONS:
            for seed in range(20263401, 20263409):
                with self.subTest(case=case, seed=seed):
                    self.assertTrue(episode(MODEL, seed, case)['ok'])

    def test_health_schema_fail_closed(self):
        for field in ('now_ns', 'sensor_ns', 'frame', 'worker_alive'):
            health, _, _ = fixture(1)
            del health[field]
            self.assertFalse(Supervisor(MODEL).check(health))

    def test_invalid_types(self):
        for field in ('now_ns', 'sensor_ns', 'worker_alive'):
            for value in (None, 1.2, '0', [], {}):
                health, _, _ = fixture(1)
                health[field] = value
                self.assertFalse(Supervisor(MODEL).check(health))

    def test_clock_reversal_latches(self):
        guard = Supervisor(MODEL)
        self.assertTrue(guard.check(fixture(1)[0]))
        self.assertFalse(guard.check(fixture(1, 999_999_999)[0]))
        self.assertFalse(guard.check(fixture(1, 2_000_000_000)[0]))

    def test_idle_link_supervision(self):
        health = fixture(1)[0]
        health['frame']['received_ns'] -= 250_000_001
        self.assertFalse(Supervisor(MODEL).check(health))

    def test_sensor_ttl_boundaries(self):
        for age, expected in [(-1, False), (0, True), (250_000_000, True), (250_000_001, False)]:
            health = fixture(1)[0]
            health['sensor_ns'] -= age
            self.assertEqual(Supervisor(MODEL).check(health), expected)

    def test_continuous_fault_after_submission(self):
        for fault in ('sensor', 'worker', 'authority', 'armed', 'failsafe', 'envelope'):
            guard = Supervisor(MODEL)
            h, r, e = fixture(1)
            self.assertTrue(guard.submit(r, h, e)['allowed'])
            if fault == 'sensor':
                h['sensor_ns'] = None
            elif fault == 'worker':
                h['worker_alive'] = False
            elif fault == 'envelope':
                h['frame']['position_mm'][0] = 5001
            else:
                h['frame'][fault] = fault == 'failsafe'
            self.assertFalse(guard.check(h))
            self.assertTrue(guard.tripped)
            self.assertFalse(guard.check(fixture(1)[0]))

    def test_first_fault_retained(self):
        guard = Supervisor(MODEL)
        guard.trip('original')
        guard.trip('secondary')
        self.assertEqual(guard.reason, 'original')
        self.assertFalse(guard.acknowledge({}, 0))

    def test_model_not_mutated(self):
        before = json.dumps(MODEL, sort_keys=True)
        for case in CONDITIONS:
            episode(MODEL, 1, case)
        self.assertEqual(json.dumps(MODEL, sort_keys=True), before)

    def test_negative_controls(self):
        from echoai.nexus0.safe1.controls import mutants
        values = mutants(MODEL)
        self.assertEqual(len(values), 6)
        self.assertTrue(all(values.values()), values)

    def test_energy_clock_and_action(self):
        for mismatch in ('clock', 'action'):
            h, r, e = fixture(1)
            if mismatch == 'clock':
                e['now_ns'] -= 1
            else:
                e['routes']['out'] = [0]
            self.assertFalse(Supervisor(MODEL).submit(r, h, e)['allowed'])

    def test_ack_is_not_arrival(self):
        guard = Supervisor(MODEL)
        h, r, e = fixture(1)
        self.assertTrue(guard.submit(r, h, e)['allowed'])
        now = h['now_ns']+1
        self.assertTrue(guard.acknowledge(dict(system=1, component=1, command=192, result=0, received_ns=now), now))
        self.assertEqual(guard.gateway.state, 'executing')

    def test_lease_expiry_terminal(self):
        lease = Lease()
        self.assertTrue(lease.renew(0))
        self.assertTrue(lease.allowed(499_999_999))
        self.assertFalse(lease.allowed(500_000_000))
        self.assertFalse(lease.renew(500_000_001))

    def test_lease_cancel_and_bad_clock(self):
        for bad in (-1, True, 1.1, None):
            lease = Lease()
            lease.renew(10)
            self.assertFalse(lease.allowed(bad))
            self.assertFalse(lease.renew(20))
        lease = Lease()
        lease.cancel()
        self.assertFalse(lease.renew(0))

    def test_lease_renew_before_expiry(self):
        lease = Lease()
        self.assertTrue(lease.renew(0))
        self.assertTrue(lease.renew(400_000_000))
        self.assertTrue(lease.allowed(800_000_000))
        self.assertFalse(lease.allowed(900_000_000))

    def test_real_process_faults(self):
        for mode, expected in [('healthy', None), ('exit', 'eof'), ('hang', 'timeout'),
                               ('partial', 'timeout'), ('oversize', 'oversize'), ('sequence', 'schema')]:
            with self.subTest(mode=mode):
                channel = Channel([sys.executable, str(WORKER), mode])
                try:
                    started = time.monotonic()
                    if expected is None:
                        self.assertEqual(channel.call(fixture(1)[1]['wsp'])['wsp'], fixture(1)[1]['wsp'])
                    else:
                        with self.assertRaises(ChannelError) as error:
                            channel.call(fixture(1)[1]['wsp'])
                        self.assertIn(expected, str(error.exception))
                        with self.assertRaises(ChannelError):
                            channel.call(fixture(1)[1]['wsp'])
                    self.assertLess(time.monotonic()-started, .45)
                finally:
                    channel.close()
                self.assertIsNotNone(channel.process.poll())

    def test_operator_wait_services_main_thread(self):
        from echoai.nexus0.safe1.service import serviced_call
        import threading
        calls = []
        owner = threading.get_ident()
        result = serviced_call(lambda: (time.sleep(.08), 17)[1],
                               lambda: calls.append(threading.get_ident()), .3)
        self.assertEqual(result, 17)
        self.assertGreater(len(calls), 3)
        self.assertEqual(set(calls), {owner})

    def test_operator_wait_is_bounded(self):
        from echoai.nexus0.safe1.service import serviced_call
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            serviced_call(lambda: time.sleep(.1), lambda: None, .03)
        self.assertLess(time.monotonic()-started, .1)

    def test_operator_exception_preserved(self):
        from echoai.nexus0.safe1.service import serviced_call
        with self.assertRaises(ZeroDivisionError):
            serviced_call(lambda: 1//0, lambda: None, .3)


if __name__ == '__main__':
    unittest.main()
