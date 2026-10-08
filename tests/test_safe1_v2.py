import unittest
from echoai.nexus0.safe1_v2.evaluate import normal_arming


def fixture():
    return ([dict(timestamp=100, param1=1, param2=0), dict(timestamp=200, param1=1, param2=0)],
            [dict(timestamp=101, result=1), dict(timestamp=201, result=0)],
            [dict(event='arm_rejected', result=1), dict(event='armed')], 300)


class ArmingAuditTests(unittest.TestCase):
    def test_normal_retry(self):
        self.assertTrue(normal_arming(*fixture()))

    def test_one_normal_arm(self):
        c, a, e, s = fixture()
        self.assertTrue(normal_arming(c[1:], a[1:], e[1:], s))

    def test_no_arm(self):
        self.assertFalse(normal_arming([], [], [], 300))

    def test_forcing_and_disarming(self):
        for field, value in [('param1', 0), ('param2', 21196), ('param2', float('nan'))]:
            c, a, e, s = fixture()
            c[1][field] = value
            self.assertFalse(normal_arming(c, a, e, s))

    def test_missing_ack(self):
        c, a, e, s = fixture()
        self.assertFalse(normal_arming(c, a[1:], e, s))

    def test_multiple_acceptances(self):
        c, a, e, s = fixture()
        a[0]['result'] = 0
        e[0] = dict(event='armed')
        self.assertFalse(normal_arming(c, a, e, s))

    def test_ack_timing(self):
        for stamp in (99, 100, 3_000_101):
            c, a, e, _ = fixture()
            a[0]['timestamp'] = stamp
            c[1]['timestamp'] = 5_000_000
            a[1]['timestamp'] = 5_000_001
            self.assertFalse(normal_arming(c, a, e, 6_000_000))

    def test_overlapping_retry(self):
        c, a, e, s = fixture()
        a[0]['timestamp'] = 200
        self.assertFalse(normal_arming(c, a, e, s))

    def test_event_mismatch(self):
        c, a, e, s = fixture()
        e[0]['result'] = 2
        self.assertFalse(normal_arming(c, a, e, s))

    def test_after_supervision(self):
        c, a, e, s = fixture()
        self.assertFalse(normal_arming(c, a, e, 200))

    def test_other_findings_never_waived(self):
        from unittest.mock import patch
        from pathlib import Path
        from echoai.nexus0.safe1_v2.evaluate import audit
        root = Path(__file__).resolve().parents[1]/'lab/safe1/development/nominal'
        with patch('echoai.nexus0.safe1_v2.evaluate.audit_v1', return_value=dict(valid=False,
                   findings=['forced_arm_or_disarm', 'heartbeat_without_permission'])):
            value = audit(root)
        self.assertFalse(value['valid'])
        self.assertEqual(value['findings'], ['heartbeat_without_permission'])


if __name__ == '__main__':
    unittest.main()
