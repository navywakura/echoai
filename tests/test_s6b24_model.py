"""Protocol and custody regression tests; no model or game runs."""
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from seed import s6b24_model as m

P={'patches':[{'when':{'body_known':['eq',0]},'set':{'HOLD':4}}]}

def request():
    return dict(selection_protocol='candidate-id',menu=[dict(id='C000',proposal=P)],
                prompt='select one',model_call_required=True)

class ModelProtocol(unittest.TestCase):
    def test_candidate_exact_reconstruction(self):
        with patch.object(m.search,'reconstruct',return_value=P) as reconstruct:
            self.assertEqual(m.answer('{"candidate_id":"C000"}',request()),P)
            reconstruct.assert_called_once_with(request(),{'candidate_id':'C000'})
    def test_real_preflight_selections_reconstruct(self):
        from seed import s6b24_preflight as preflight
        self.assertEqual(len(preflight.all_cases()),8)
        for case in preflight.all_cases():
            output=(json.dumps(case['expected']) if case['request']['selection_protocol']=='r4-json'
                    else '{"candidate_id":"C000"}')
            self.assertEqual(m.answer(output,case['request']),case['expected'])
            self.assertNotIn('base',case['request'])
    def test_actual_foreign_id_and_menu_tamper_rejected(self):
        from seed import s6b24_preflight as preflight
        req=preflight.all_cases()[4]['request']
        with self.assertRaises(ValueError):m.answer('{"candidate_id":"missing"}',req)
        req['menu'][0]['proposal']['patches'][0]['set']['HOLD']=32
        with self.assertRaisesRegex(ValueError,'hash'):m.answer('{"candidate_id":"C000"}',req)
    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ValueError):m.answer('{"candidate_id":"C000","candidate_id":"other"}',request())
    def test_ref_uses_original_grammar(self):
        self.assertEqual(m.grammar({'selection_protocol':'r4-json'}),m.r4.grammar())
    def test_dynamic_id_grammar(self):
        grammar=m.grammar(request())
        self.assertIn('candidate_id',grammar)
        self.assertIn('C000',grammar)
        self.assertNotIn('C001',grammar)
    def test_foreign_id_fails(self):
        with patch.object(m.search,'reconstruct',side_effect=ValueError('unknown ID')):
            with self.assertRaises(ValueError):m.answer('{"candidate_id":"other"}',request())
    def test_transport_preserves_pinned_options(self):
        spec=dict(cli='/cli',model='/weights',backend='cuda',gpu_layers=99,tensor_split='1,1')
        cmd=m.command(spec,Path('/prompt'),824101,request())
        self.assertIn('--grammar',cmd)
        self.assertEqual(cmd[-2:],['-f','/prompt'])
        self.assertIn('--no-context-shift',cmd)
    def test_interrupted_call_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'model-budget.json').write_text(json.dumps({'calls':['B24-S/000']}))
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                m.propose(root,{'N7':{}},'B24-S',0,request(),824101,'profile')

@unittest.skipUnless(os.environ.get('B23_GBNF_VALIDATOR'),'native parser checked on frozen Kaggle build')
class NativeIDGrammar(unittest.TestCase):
    def test_exact_catalog_language(self):
        req=request();req['menu']=[dict(id=f'C01{i:02d}',proposal=P) for i in range(64)]
        values=[(json.dumps({'candidate_id':x['id']}),True) for x in req['menu']]
        values += [('{"candidate_id":"C9999"}',False),('{"candidate_id":1}',False),
                   ('{"candidate_id":"C0100","candidate_id":"C0101"}',False),('[]',False)]
        with tempfile.TemporaryDirectory() as tmp:
            gp=Path(tmp)/'grammar.gbnf';jp=Path(tmp)/'case.json';gp.write_text(m.grammar(req))
            for text,valid in values:
                jp.write_text(text)
                result=subprocess.run([os.environ['B23_GBNF_VALIDATOR'],str(gp),str(jp)],capture_output=True,text=True,check=True)
                self.assertEqual('Input string is valid according to the grammar.' in result.stdout,valid,result.stdout)


if __name__=='__main__':unittest.main()
