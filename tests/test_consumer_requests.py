import json
import unittest

from echo_arc import consumer_requests as c, precise_patch as p
from echo_arc.parameter_first_grammar import Grammar
from echo_arc.precise_patch_grammar import Grammar as Previous


class ConsumerRequests(unittest.TestCase):
    def test_reordering_preserves_all_control_and_guard_options(self):
        old=Previous(lambda text:list(text.encode()),256)
        new=Grammar(lambda text:list(text.encode()),256)
        self.assertEqual(set(old.options[1]),set(new.options[3]))
        self.assertEqual(set(old.options[3]),set(new.options[1]))
        proposal={'patches':[{'set':{'COOLDOWN_CAP':7},'when':{'body_known':['eq',0]}}]}
        text=json.dumps(proposal,separators=(',',':'));tokens=list(text.encode())
        for i,token in enumerate(tokens):self.assertIn(token,new.allowed(tokens[:i]))
        self.assertIn(256,new.allowed(tokens))
        self.assertEqual(p.parse(text),p.validate(proposal))

    def test_no_private_identifiers_or_protected_feedback_in_prompts(self):
        row={'origin':'DEVELOPMENT_A','levels_completed':4,'seed':'secret-task',
             'family':'hidden-family','diagnostics':{'consumers':[], 'witnesses':{}}}
        history=[{'verdict':'V4','reason':'reserved-answer','B':{'secret':'private-grid'}}]
        for arm in ('echo','fijo'):
            reqs=c.requests(arm,0,2,{'program':p.EMPTY},{'rows':[row]},history)
            text=str(reqs)
            for secret in ('secret-task','hidden-family','reserved-answer','private-grid'):
                self.assertNotIn(secret,text)
            self.assertEqual([r['id'] for r in reqs],[0,1])
        with self.assertRaises(ValueError):c.evidence([dict(row,origin='PROTECTED_B')],'echo',[],0)

    def test_echo_selects_observed_consumption_and_fixed_selects_lowest_scores(self):
        low={'origin':'DEVELOPMENT_A','levels_completed':0,'diagnostics':{'consumers':[], 'witnesses':{}}}
        high={'origin':'DEVELOPMENT_A','levels_completed':4,'diagnostics':{'consumers':[
            {'parameter':'HOLD','value':40,'remaining_before':0,'count':1,
             'secret':'reserved-string','features':dict({k:lo for k,(lo,_) in p.FEATURES.items()},private='hidden-value')}], 'witnesses':{}}}
        echo,_=c.evidence([low,high],'echo',[],0)
        fixed,_=c.evidence([low,high],'fijo',[],0)
        self.assertEqual(echo[0]['levels'],4)
        self.assertEqual(fixed[0]['levels'],0)
        self.assertEqual(echo[0]['actual_wait_control_reads'][0]['value'],40)
        self.assertNotIn('reserved-string',str(echo))
        self.assertNotIn('hidden-value',str(echo))
        self.assertIn('inserted operations may create new reads',echo[0]['scope'])
        packed=c.compact_cases(echo)
        for before,after in zip(echo,packed['cases']):
            for old,new in zip(before['actual_wait_control_reads'],after['actual_wait_control_reads']):
                self.assertEqual(old['features'],dict(packed['common_read_features'],**new['features']))
        self.assertEqual(c.compact_cases([]),{'common_read_features':{},'cases':[]})


if __name__=='__main__':unittest.main()
