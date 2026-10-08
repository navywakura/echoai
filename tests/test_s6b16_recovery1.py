import copy
import unittest
from unittest.mock import patch

from seed import s6b16_recovery1 as recovery


def result():
    row=dict(actions=[['K',4,None]],frames=['frame'],levels_completed=5,
        actions_per_level=[1],resets=0,score=1.0,
        model={'hypotheses':[[1,['cause',(3,4)],'proposed']],
               'temporal':{'decision':{'target':(3,4)}}})
    return dict(rows=[row],levels=5,score=1.0,trace_digest=recovery.r.b.sha([row]))


class RecoveryTests(unittest.TestCase):
    def test_nested_report_tuples_normalize_without_altering_digest_or_original(self):
        live=result()
        original=copy.deepcopy(live)
        saved=recovery.canonical_baseline(live)
        self.assertEqual(saved['rows'][0]['model']['temporal']['decision']['target'],[3,4])
        self.assertEqual(live,original)
        self.assertEqual(saved['trace_digest'],live['trace_digest'])
        self.assertEqual(recovery.canonical_baseline(saved),saved)

    def test_a_real_trace_difference_is_never_normalized_away(self):
        live=result()
        live['rows'][0]['score']=2.0
        with self.assertRaisesRegex(RuntimeError,'digest mismatch'):
            recovery.canonical_baseline(live)

    def test_behavior_materialization_changes_fail_closed(self):
        live=result()
        live['rows'][0]['actions'][0]=('K',4,None)
        live['trace_digest']=recovery.r.b.sha(live['rows'])
        with self.assertRaisesRegex(RuntimeError,'changed behavior: actions'):
            recovery.canonical_baseline(live)

    def test_only_exact_micro_base_and_replay_labels_are_intercepted(self):
        live=result()
        with patch.object(recovery,'ORIGINAL_MEASUREMENT',return_value=lambda *a,**kw:live):
            measure=recovery.measurement('primary')
            for label in recovery.LABELS:
                self.assertIsNot(measure(label,{},[]),live)
            for label in ('pilot/base/A','micro/updated-740101/000/A','exam/echo','micro/baseline/B'):
                self.assertIs(measure(label,{},[]),live)


if __name__=='__main__':
    unittest.main()
