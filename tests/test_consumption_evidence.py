import unittest
from echo_arc import consumption_evidence as c, precise_patch as p


def decision(*, motor=0, before_hold=0, after_hold=40, action=("K",3,None)):
    f={k:0 for k in p.FEATURES};f.update(motor_ready=motor,hold_remaining=before_hold)
    return {"kind":"decision","before":{"hold":before_hold,"to_try":[3],"reset_keys":[3]},
            "after":{"hold":after_hold},"action":action,"repair_features":f}


def proposal(motor,value):
    return {"patches":[{"when":{"motor_ready":["eq",motor]},"set":{"HOLD":value}}]}


class Consumption(unittest.TestCase):
    def test_setting_at_early_return_is_not_counted_as_actual_assignment(self):
        rows=c.native_hold_sites([decision(),decision(motor=1,after_hold=0)],origin="DEVELOPMENT_A",native_policy=p.EMPTY)
        result=c.assess_hold(proposal(1,100),rows)
        self.assertEqual(result['observed_native_assignments'],1)
        self.assertEqual(result['matching_assignment_sites'],0)
        self.assertEqual(result['diagnosis'],'NO_OBSERVED_CONSUMPTION')

    def test_native_value_differs_from_changed_wait_but_neither_claims_success(self):
        rows=c.native_hold_sites([decision(),decision(before_hold=1)],origin="DEVELOPMENT_A",native_policy=p.EMPTY)
        self.assertEqual(c.assess_hold(proposal(0,40),rows)['diagnosis'],'NATIVE_VALUE')
        result=c.assess_hold(proposal(0,20),rows)
        self.assertEqual(result['would_change_assigned_wait'],2)
        self.assertEqual(result['action_improvement'],'UNMEASURED')

    def test_unrelated_waits_and_different_actions_do_not_prove_consumption(self):
        rows=c.native_hold_sites([decision(before_hold=40,after_hold=39),decision(action=('K',2,None))],
                                 origin="DEVELOPMENT_A",native_policy=p.EMPTY)
        self.assertEqual(rows,[])

    def test_rejects_protected_data_or_generalization_to_patched_actor(self):
        with self.assertRaises(ValueError):c.native_hold_sites([],origin="PROTECTED_B",native_policy=p.EMPTY)
        with self.assertRaises(ValueError):c.native_hold_sites([],origin="DEVELOPMENT_A",native_policy=proposal(0,20))
        with self.assertRaises(ValueError):c.assess_hold({'patches':[{'when':{'motor_ready':['eq',0]},'set':{'BABBLE':3}}]},[])


if __name__=='__main__':unittest.main()
