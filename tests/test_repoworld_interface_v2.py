"""V2 editing must preserve bytes, provenance and transaction authority."""
import json
from pathlib import Path
import tempfile
import unittest
from .repoworld_support import ROOT
from .test_repoworld_arms import fixture, checks, FiniteProvider
from echoai.repoworld.workspace import Workspace, PatchFormatError
from echoai.repoworld.environment import repo_store
from echoai.repoworld.types import RepoBase
from echoai.repoworld.tools import dispatch_tool

class InterfaceV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.base=fixture(self.root)
    def session(self,text):
        (self.root/'src/a.py').write_bytes(text.encode())
        snap=repo_store(self.root/'store2').capture(self.root/'src')
        return Workspace(self.root/'session',RepoBase(self.base.task,snap,self.base.environment))
    def view(self,s,start=1,count=100):
        return dispatch_tool(dict(tool='file_view',snapshot_id=s.current.id,path='a.py',start_line=start,line_count=count,cursor=None),session=s)
    def edit(self,s,search,replace,**kw):
        return dispatch_tool(dict(tool='patch_apply',expected_snapshot_id=s.current.id,purpose='solution',path='a.py',search=search,replace=replace,**kw),session=s)
    def test_outline_paginates_complete_symbols(self):
        s=self.session('class Box:\n'+''.join(f'    def method_{i}(self):\n        return {i}\n' for i in range(70)))
        req=dict(tool='file_outline',snapshot_id=s.current.id,path='a.py',class_name='Box',cursor=None)
        names=[]
        for _ in range(30):
            reply=dispatch_tool(req,session=s);names += [x['symbol'] for x in reply['symbols']]
            if reply['cursor'] is None:break
            req['cursor']=reply['cursor']
        self.assertIn('Box.method_69',names);self.assertEqual(len(names),len(set(names)))
    def test_edit_requires_all_search_lines_observed(self):
        s=self.session('value = 1\nother = 2\n');self.view(s,1,1)
        with self.assertRaisesRegex(ValueError,'UNOBSERVED'):self.edit(s,'value = 1\nother = 2\n','value = 2\nother = 2\n')
        self.view(s,2,1);reply=self.edit(s,'value = 1\nother = 2\n','value = 2\nother = 2\n')
        self.assertNotEqual(reply['candidate_id'],s.current.id)
        self.assertEqual((s.current.root/'a.py').read_text(),'value = 1\nother = 2\n')
    def test_exact_bytes_crlf_and_no_final_newline(self):
        text='value = 1\r\nother = "keep  "'
        s=self.session(text);self.view(s)
        reply=self.edit(s,'value = 1\r\n','value = 2\r\n')
        self.assertEqual((s.snapshot(reply['candidate_id']).root/'a.py').read_bytes(),text.replace('1','2').encode())
    def test_ambiguous_rejected_even_if_one_occurrence_viewed(self):
        s=self.session('value = 1\nvalue = 1\n');self.view(s,1,1)
        with self.assertRaisesRegex(PatchFormatError,'AMBIGUOUS'):self.edit(s,'value = 1\n','value = 2\n')
    def test_syntax_error_never_staged(self):
        s=self.session('value = 1\n');self.view(s)
        with self.assertRaisesRegex(PatchFormatError,'SYNTAX'):self.edit(s,'value = 1\n','value = (\n')
        self.assertFalse(any(r['body'].get('event')=='repoworld.stage' for r in s.receipts.records))
    def test_no_prefix_or_indent_normalization(self):
        s=self.session('value = 1\n');self.view(s)
        with self.assertRaisesRegex(PatchFormatError,'NOT_FOUND'):self.edit(s,'L1: value = 1\n','value = 2\n')
    def test_observation_is_bound_to_content_and_replays(self):
        s=self.session('value = 1\n');self.view(s)
        restored=Workspace(s.directory)
        self.edit(restored,'value = 1\n','value = 2\n')
        record=next(r for r in s.receipts.records if r['body'].get('event')=='repoworld.source-observation')
        self.assertEqual(record['body']['lines'][0]['text'],'value = 1\n')
    def test_v2_mock_navigation_edit_and_rollback(self):
        from echoai.repoworld.protocol import run_episode
        view={'action':'file_view','arguments':{'path':'a.py'}}
        def edit(v):return {'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':f'value = {v}\n'}}
        p=FiniteProvider([view,edit(0),edit(2),{'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch']);self.assertEqual(result['budget']['pending'],0)
    def test_protected_path_rejected_before_compilation(self):
        s=self.session('value = 1\n');self.view(s)
        with self.assertRaisesRegex(ValueError,'protected'):
            dispatch_tool(dict(tool='patch_apply',expected_snapshot_id=s.current.id,purpose='solution',path='tests/test_a.py',search='value = 1\n',replace='value = 2\n'),session=s)
    def test_v2_replay_cannot_switch_interface(self):
        from echoai.repoworld.protocol import run_episode
        args=dict(provider=FiniteProvider([{'action':'finish','arguments':{}}]),output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks)
        run_episode(self.base,'S',73,interface_version=2,**args)
        with self.assertRaisesRegex(ValueError,'different inputs'):
            run_episode(self.base,'S',73,interface_version=1,**args)
    def test_v2_duplicate_refutation_charges_tools_not_second_patch(self):
        from echoai.repoworld.protocol import run_episode
        view={'action':'file_view','arguments':{'path':'a.py'}}
        bad={'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = (\n'}}
        p=FiniteProvider([view,bad,bad,{'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(result['budget']['used']['patches'],1)
        self.assertEqual(result['budget']['used']['tools'],5) # two baselines, read, edit, cached rejection

    def test_v2_locator_handoff_uses_observed_source(self):
        from echoai.repoworld.protocol import run_episode
        p=FiniteProvider([{'action':'file_view','arguments':{'path':'a.py'}},
            {'action':'finish','arguments':{}},
            {'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}},
            {'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch'])

    def test_v2_locator_repeated_reads_warn_and_hand_off_to_editor(self):
        from echoai.repoworld.protocol import run_episode
        view={'action':'file_view','arguments':{'path':'a.py'}}
        edit={'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}}
        p=FiniteProvider([view,view,view,edit,{'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch'])

    def test_v2_locator_quota_with_locus_hands_off_to_editor(self):
        from echoai.repoworld.protocol import run_episode
        # 1 initial view, then 7 outline calls to reach 8 localization calls total
        view={'action':'file_view','arguments':{'path':'a.py'}}
        outline={'action':'file_outline','arguments':{'path':'a.py'}}
        edit={'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}}
        p=FiniteProvider([view]+[outline]*7+[edit,{'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch'])

    def test_v2_locator_quota_without_locus_abandons(self):
        from echoai.repoworld.protocol import run_episode
        # 8 issue_page calls with no observed source file locus
        page={'action':'issue_page','arguments':{'offset':0}}
        p=FiniteProvider([page]*8)
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(result['status'],'finished')
        self.assertEqual(result['model_patch'],'')

    def test_v2_locator_token_budget_cap_reserves_editor_tokens(self):
        from echoai.repoworld.protocol import run_episode
        view={'action':'file_view','arguments':{'path':'a.py'}}
        edit={'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}}
        class HeavyLocatorProvider(FiniteProvider):
            def __init__(self,actions):
                super().__init__(actions);self.last_count=100;self.views=0
            def prepare(self,messages,*args):
                self.last_count=2700 if self.views<3 else 100
                return json.dumps(messages),[1]*self.last_count
            def complete(self,*args,**kw):
                act=next(self.actions)
                if act['action']=='file_view':self.views+=1
                return dict(content=json.dumps(act),tokens_evaluated=self.last_count,tokens_predicted=200)
        # 3 views: 3 * 2900 = 8700 tokens >= 8000 -> triggers automatic handoff to editor!
        p=HeavyLocatorProvider([view,view,view,edit,{'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch'])
        self.assertGreater(result['budget']['remaining']['tokens'],10000)

    def test_v5_partial_method_cannot_authorize_handoff_or_edit(self):
        from echoai.repoworld.protocol import run_episode
        text='value = 1\nclass Box:\n    def target(self, x):\n        first = x\n        second = first + 1\n        return second\n'
        s=self.session(text)
        class Recording(FiniteProvider):
            def prepare(self,messages,*args):
                self.contexts=getattr(self,'contexts',[])+[json.loads(messages[-1]['content'])]
                return super().prepare(messages,*args)
        p=Recording([
            {'action':'file_view','arguments':{'path':'a.py','start_line':6,'line_count':1}},
            {'action':'finish','arguments':{}},
            {'action':'patch_apply','arguments':{'path':'a.py','search':'        return second\n','replace':'        return second + 1\n'}},
            {'action':'file_view','arguments':{'path':'a.py','start_line':3,'line_count':4}},
            {'action':'finish','arguments':{}},
            {'action':'patch_apply','arguments':{'path':'a.py','search':'        return second\n','replace':'        return second + 1\n'}},
            {'action':'finish','arguments':{}}])
        result=run_episode(s.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(p.contexts[2]['role'],'locator')
        self.assertIn('EPISTEMIC_LOCUS_INCOMPLETE',json.dumps(p.contexts[2]['feedback']))
        self.assertEqual(p.contexts[3]['role'],'locator')
        self.assertEqual(p.contexts[1]['source_evidence']['locus']['next_view'],{'start_line':3,'line_count':3})
        self.assertIn('+        return second + 1',result['model_patch'])
        self.assertEqual(result['budget']['used']['patches'],1)

    def test_v5_retained_edit_hands_off_to_critic_despite_new_file_hash(self):
        from echoai.repoworld.protocol import run_episode
        class Recording(FiniteProvider):
            def prepare(self,messages,*args):
                self.contexts=getattr(self,'contexts',[])+[json.loads(messages[-1]['content'])]
                return super().prepare(messages,*args)
        p=Recording([{'action':'file_view','arguments':{'path':'a.py'}},
            {'action':'finish','arguments':{}},
            {'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}},
            {'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(p.contexts[3]['role'],'critic')
        self.assertIsNone(p.contexts[3]['source_evidence'])
        self.assertIn('+value = 2',result['model_patch'])

    def test_v5_revert_to_base_returns_editor_with_explicit_feedback(self):
        from echoai.repoworld.protocol import run_episode
        class Recording(FiniteProvider):
            def prepare(self,messages,*args):
                self.contexts=getattr(self,'contexts',[])+[json.loads(messages[-1]['content'])]
                return super().prepare(messages,*args)
        view={'action':'file_view','arguments':{'path':'a.py'}}
        p=Recording([view,{'action':'finish','arguments':{}},
            {'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}},view,
            {'action':'patch_apply','arguments':{'path':'a.py','search':'value = 2\n','replace':'value = 1\n'}},
            {'action':'finish','arguments':{}}])
        result=run_episode(self.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(p.contexts[-1]['role'],'editor')
        self.assertTrue(p.contexts[-1]['feedback']['base_restored'])
        self.assertEqual(result['model_patch'],'')

    def test_v5_redundant_partial_reads_abandon_without_editor(self):
        from echoai.repoworld.protocol import run_episode
        s=self.session('value = 1\ndef target(x):\n    a = x + 1\n    return a\n')
        view={'action':'file_view','arguments':{'path':'a.py','start_line':4,'line_count':1}}
        p=FiniteProvider([view]*3)
        result=run_episode(s.base,'E',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertEqual(result['status'],'finished')
        self.assertEqual(result['budget']['used']['llm_calls'],3)
        self.assertEqual(result['model_patch'],'')

    def test_v5_locus_coverage_coalesces_views_and_is_hash_scoped(self):
        from echoai.repoworld.source_evidence import projection
        s=self.session('value = 1\ndef target(x):\n    a = x + 1\n    return a\n')
        self.view(s,4,1);self.assertFalse(projection(s)['locus']['ready'])
        self.view(s,2,2);self.assertTrue(projection(s)['locus']['ready'])
        edit=self.edit(s,'    return a\n','    return a + 1\n')
        from echoai.repoworld.types import PatchCandidate
        row=next(x['body'] for x in s.receipts.records if x['body'].get('event')=='repoworld.stage')
        candidate=PatchCandidate(row['base'],s.snapshot(row['candidate']),row['patch_sha256'],row['operation_id'])
        # A checked retention creates a new content identity; old views cannot attest it.
        receipt=s.receipts.append(dict(event='repoworld.public-property',candidate=candidate.snapshot.id,
            property_status='supported',checker_id='fixture',scope='public'))
        s.retain(candidate,expected_head=s.current.id,public_receipt_ids=(receipt['sha256'],))
        self.assertIsNone(projection(s))
