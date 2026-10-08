"""The final classifier is named from school, never from the exam."""
import unittest
from echoai.nexus0.pattern1r_v3 import evaluate as old
from echoai.nexus0.pattern1r_v4 import evaluate as new, campaign as cp, session, contract


class SchoolMappingTests(unittest.TestCase):
    def school(self):
        return [(1,511)]*349+[(2,4095)]*234+[(2,8191)]*134

    def test_late_family_creation_is_not_a_false_collapse(self):
        exam=[(1,511)]*100+[(2,4095)]*100
        prior=old.score_identity(self.school(),exam,{1,2})
        fixed=new.score_identity(self.school(),exam,{1,2})
        self.assertFalse(next(c for c in prior['identity'] if c['name']=='objects_separated')['ok'])
        self.assertTrue(all(c['ok'] for cs in fixed.values() for c in cs))
        self.assertEqual(fixed['identity'][0]['accuracy'],1.0)

    def test_exam_cannot_choose_the_school_labels(self):
        good=[(1,511)]*100+[(2,4095)]*100
        wrong=[(1,4095)]*100+[(2,511)]*100
        a=new.score_identity(self.school(),good,{1,2});b=new.score_identity(self.school(),wrong,{1,2})
        self.assertEqual(a['identity'][2]['school_homes'],b['identity'][2]['school_homes'])
        self.assertEqual(b['identity'][0]['accuracy'],0.0)

    def test_real_collapse_and_exam_writes_still_fail(self):
        school=[(1,511)]*100+[(2,511)]*100
        collapse=new.score_identity(school,school,{1,2})
        self.assertFalse(collapse['identity'][2]['ok'])
        dirty=new.score_identity(self.school(),self.school(),{1,2},mutant='frozen_write')
        self.assertFalse(next(c for c in dirty['frozen'] if c['name']=='exam_writes_nothing')['ok'])

    def test_physical_and_learning_code_are_identical_to_v3(self):
        for name in ('assets/consumer.py','assets/flightrunner_survey.py','memory.py','contract.py','session.py'):
            self.assertEqual((cp.HERE/name).read_bytes(),(cp.previous.HERE/name).read_bytes(),name)
        self.assertEqual(contract.configuration(),cp.previous.p1r.configuration())
        self.assertEqual(cp.protocol()['pattern_limits'],cp.previous.protocol()['pattern_limits'])


if __name__=='__main__':unittest.main()
