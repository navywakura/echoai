import unittest
from harness.s6_publication import final_summary


class S6Publication(unittest.TestCase):
    def test_only_complete_consistent_audits_can_publish_green(self):
        closed={'at':'fixture','result':'EXAM_CLOSED','s6_green':True,'exam_opened':True}
        pilot={'promote':True,'paired_A':{'echo':2,'fijo':1},'accepted_echo':1}
        campaign=dict(pilot)
        audit={'green':True,'checks':{k:True for k in ['B1','B2','B3','B4','B5']}}
        self.assertTrue(final_summary(closed,pilot,campaign,audit)['green'])
        for k in audit['checks']:
            with self.subTest(criterion=k),self.assertRaises(ValueError):
                final_summary(closed,pilot,campaign,dict(audit,checks=dict(audit['checks'],**{k:False})))
        for phase in [None,dict(campaign,promote=False)]:
            with self.assertRaises(ValueError):final_summary(closed,pilot,phase,audit)
        with self.assertRaises(ValueError):final_summary(dict(closed,exam_opened=False),pilot,campaign,audit)

    def test_negative_closure_stays_negative_without_exposing_candidates(self):
        pilot={'promote':False,'paired_A':{'echo':1,'fijo':1},'accepted_echo':0,
               'verdicts':[{'candidate':'private program','counterexamples':'private B'}]}
        s=final_summary({'at':'fixture','result':'PILOT_NO_PROMOTION','s6_green':False,'exam_opened':False},pilot)
        self.assertFalse(s['green'])
        self.assertNotIn('verdicts',s['pilot'])
        self.assertFalse(s['arc_official_scores_changed'])
