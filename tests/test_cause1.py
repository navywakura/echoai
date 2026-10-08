"""Counterexamples to attribution, timing and public input boundaries."""
import copy
import unittest
from echoai.nexus0.cause1.core import attribute, decode, fresh, prepare, wsp
from echoai.nexus0.cause1.perception import project


def evidence(north=0, distance=6000, now=1_000_000_000):
    return dict(now_ns=now, capture_ns=now-20_000_000, delivered_ns=now-10_000_000,
                odometry_ns=now-10_000_000, north_mm=north, distance_mm=distance,
                yaw_mrad=1571, rays=7)


def trial(action=0, own=1000, external=0):
    before = evidence()
    after = evidence(own, 6000-own+external, 12_000_000_000)
    intention = wsp(action)
    prepared = prepare(intention, before)
    execution = dict(wsp=intention, sent_ns=1_010_000_000, ack_ns=1_050_000_000, accepted=True)
    return [intention, before, prepared, execution, after]


class CauseTests(unittest.TestCase):
    def test_factorial_and_identical_visual_change(self):
        cases = [(6, 0, 0, 'none'), (0, 1000, 0, 'self'),
                 (6, 0, -1000, 'external'), (0, 1000, -1000, 'both'),
                 (1, -1000, 0, 'self'), (1, -1000, 1000, 'both'),
                 (0, 1000, 1000, 'both')]
        for action, own, external, label in cases:
            result = attribute(*trial(action, own, external))
            self.assertEqual(result['label'], label)
            self.assertEqual(result['external_delta_mm'], external)
            self.assertEqual(len(bytes.fromhex(result['wsp'])), 16)
            self.assertFalse(result['has_fact'])
        self.assertEqual(attribute(*trial())['range_delta_mm'],
                         attribute(*trial(6, 0, -1000))['range_delta_mm'])

    def test_ack_is_not_execution(self):
        args = trial(0, 0, -1000)
        self.assertEqual(attribute(*args)['label'], 'unknown')
        self.assertNotEqual(attribute(*args, mutant='no_confirmation')['label'], 'unknown')

    def test_rejected_action_does_not_own_observed_motion(self):
        args = trial()
        args[3]['accepted'] = False
        self.assertEqual(attribute(*args)['label'], 'unknown')
        self.assertEqual(attribute(*args, mutant='no_ack')['label'], 'self')

    def test_stale_and_future_evidence(self):
        for field, value in [('capture_ns', 1), ('odometry_ns', 1),
                             ('capture_ns', 20_000_000_000)]:
            args = trial()
            args[4][field] = value
            self.assertEqual(attribute(*args)['label'], 'unknown')
        args = trial()
        args[4].update(capture_ns=11_000_000_000, delivered_ns=11_000_000_000,
                       odometry_ns=11_000_000_000)
        self.assertEqual(attribute(*args)['label'], 'unknown')
        self.assertEqual(attribute(*args, mutant='no_expiry')['label'], 'self')

    def test_prediction_and_time_order(self):
        args = trial()
        args[3]['sent_ns'] = 0
        self.assertEqual(attribute(*args)['label'], 'unknown')
        args = trial()
        args[3]['ack_ns'] = args[4]['now_ns']
        self.assertEqual(attribute(*args)['label'], 'unknown')
        args = trial()
        args[2]['predicted_north_mm'] = 999
        with self.assertRaises(ValueError):
            attribute(*args)

    def test_rotation_and_missing_returns_abstain(self):
        for key, value in [('yaw_mrad', 1800), ('rays', 0), ('distance_mm', -1)]:
            args = trial()
            args[4][key] = value
            self.assertEqual(attribute(*args)['label'], 'unknown')

    def test_no_odometry_conflates_self_and_external(self):
        self.assertEqual(attribute(*trial(), mutant='no_odometry')['label'], 'both')

    def test_packet_and_schema_reject_hidden_data(self):
        for action in (0, 1, 6):
            self.assertEqual(decode(wsp(action)), action)
        with self.assertRaises(ValueError):
            decode('00'*16)
        frame = evidence()
        frame['condition'] = 'self'
        self.assertFalse(fresh(frame))
        with self.assertRaises(ValueError):
            project({'world': 'secret'})

    def test_reads_do_not_mutate(self):
        args = trial()
        old = copy.deepcopy(args)
        attribute(*args)
        self.assertEqual(args, old)

    def test_denominators_and_green_are_not_self_certifying(self):
        from echoai.nexus0.cause1.bench import metrics, PROTOCOL, schedule
        from echoai.nexus0.cause1.session import CONDITIONS
        rows = [dict(seed=s, condition=c, evidence_valid=True, execution_green=True,
                     correct=True, baseline_correct=c in ('none', 'self'),
                     residual_error_mm=0, false_self=False)
                for s, c in schedule('validation')]
        self.assertTrue(metrics(rows)['stage_green'])
        self.assertEqual(metrics(rows)['sign_p'], 1/256)
        self.assertFalse(metrics(rows[:-1])['stage_green'])
        duplicate = copy.deepcopy(rows)
        duplicate[-1] = copy.deepcopy(duplicate[0])
        self.assertFalse(metrics(duplicate)['stage_green'])
        rows[0]['false_self'] = True
        self.assertFalse(metrics(rows)['stage_green'])

    def test_stale_before_never_requests_movement(self):
        before = evidence()
        before['odometry_ns'] = 0
        reply = prepare(wsp(0), before)
        self.assertFalse(reply['allowed'])
        self.assertEqual(reply['wsp'], wsp(6))
        self.assertIsNone(reply['predicted_north_mm'])

    def test_wait_with_unexplained_body_motion_is_unknown(self):
        self.assertEqual(attribute(*trial(6, 800, 0))['label'], 'unknown')

    def test_perception_abstains_outside_level_hover_domain(self):
        raw = dict(now_ns=1_000_000_000,
                   estimate=dict(position_mm=[0, 0, 2500], yaw_mrad=1571,
                                 received_ns=990_000_000, px4_boot_ms=990,
                                 tilt_mrad=0, speed_mm_s=0),
                   lidar=dict(capture_ns=980_000_000, delivered_ns=990_000_000,
                              angles_mrad=[-20, 0, 20], ranges_mm=[6000]*3))
        self.assertTrue(fresh(project(raw)))
        raw['estimate']['tilt_mrad'] = 100
        self.assertFalse(fresh(project(raw)))
        raw['estimate']['tilt_mrad'] = 0
        raw['estimate']['speed_mm_s'] = 200
        self.assertFalse(fresh(project(raw)))


if __name__ == '__main__':
    unittest.main()
