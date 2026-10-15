"""Atomic source pages, bounded envelopes and complete protocol feedback."""
import json
from pathlib import Path
import tempfile
import unittest
from .repoworld_support import ROOT
from .test_repoworld_arms import fixture,checks,FiniteProvider
from echoai.repoworld.workspace import Workspace
from echoai.repoworld.environment import repo_store
from echoai.repoworld.types import RepoBase
from echoai.repoworld.tools import dispatch_tool
from echoai.repoworld.protocol import run_episode

class AtomicViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.base=fixture(self.root)
    def session(self,text):
        (self.root/'src/a.py').write_bytes(text.encode())
        snap=repo_store(self.root/'atomic-store').capture(self.root/'src')
        base=RepoBase(self.base.task,snap,self.base.environment)
        return Workspace(self.root/'session',base)
    def request(self,session,**extra):
        return dict(tool='file_view',snapshot_id=session.current.id,path='a.py',start_line=1,line_count=100,cursor=None,**extra)
    def test_40_complete_lines_in_one_page(self):
        text=''.join(f'    value_{i} = calculate({i})\n' for i in range(40))
        s=self.session(text);reply=dispatch_tool(self.request(s),session=s)
        self.assertEqual(''.join(x['text'] for x in reply['lines']),text)
        self.assertIsNone(reply['cursor'])
        self.assertEqual(s.budget.report()['used']['output_tokens'],reply['output_tokens'])
        self.assertEqual(s.budget.report()['pending'],0)
    def test_pages_are_atomic_utf8_and_preserve_final_no_newline(self):
        text=('x = "'+('é'*80)+'"\r\n')*25+'last = 1'
        s=self.session(text);request=self.request(s);observed=[]
        for _ in range(10):
            reply=dispatch_tool(request,session=s);observed+=reply['lines']
            self.assertLessEqual(sum(len(x['text'].encode()) for x in reply['lines']),2500)
            for x in reply['lines']:self.assertEqual(x['text'],text.splitlines(True)[x['number']-1])
            if not reply['cursor']:break
            request['cursor']=reply['cursor']
        else:self.fail('cursor did not progress')
        self.assertEqual(''.join(x['text'] for x in observed),text)
    def test_oversized_line_explicit_error_no_partial_or_freeze(self):
        s=self.session('x'*2501+'\n')
        with self.assertRaisesRegex(ValueError,'complete line.*page budget'):
            dispatch_tool(self.request(s),session=s)
        self.assertFalse(s.budget.report()['frozen'])
        self.assertEqual(s.budget.report()['pending'],0)
    def test_large_page_reaches_next_prompt_unchanged(self):
        text=''.join(f'value_{i} = {i} # observed source line\n' for i in range(40))
        s=self.session(text)
        class Provider(FiniteProvider):
            def prepare(self,messages,*args):
                self.contexts=getattr(self,'contexts',[])+[json.loads(messages[-1]['content'])]
                return super().prepare(messages,*args)
        p=Provider([{'action':'file_view','arguments':{'path':'a.py','line_count':40}},
                    {'action':'finish','arguments':{}}])
        run_episode(s.base,'S',73,provider=p,output=self.root/'episode',check_plan={'public_targets':['positive']},check_fn=checks)
        self.assertEqual(''.join(x['text'] for x in p.contexts[1]['feedback']['lines']),text)

class SearchPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);base=fixture(self.root)
        self.path='sympy/matrices/expressions'
        d=self.root/'src'/self.path;d.mkdir(parents=True)
        (d/'blockmatrix.py').write_text('class BlockMatrix:\n    pass\n')
        snap=repo_store(self.root/'search-store').capture(self.root/'src')
        self.session=Workspace(self.root/'search-session',RepoBase(base.task,snap,base.environment))
    def search(self,path,cursor=None):
        return dispatch_tool(dict(tool='repo_search',snapshot_id=self.session.current.id,
            path=path,pattern='BlockMatrix',literal=True,cursor=cursor),session=self.session)
    def test_v4_trailing_slash_search_matches_and_records_canonical_argument(self):
        reply=self.search('  sympy/matrices/expressions///  ')
        self.assertEqual(reply['matches'],[dict(path=self.path+'/blockmatrix.py',line=1,match='BlockMatrix')])
        rows=[r['body'] for r in self.session.receipts.records if r['body'].get('event')=='repoworld.search-path']
        self.assertEqual(rows[-1]['original_path'],'  sympy/matrices/expressions///  ')
        self.assertEqual(rows[-1]['canonical_path'],self.path)
        self.assertEqual(self.session.budget.report()['pending'],0)
    def test_blank_directory_query_means_repository_root(self):
        for path in ('','  ','./'):
            with self.subTest(path=path):self.assertEqual(len(self.search(path)['matches']),1)
    def test_unsafe_search_paths_have_actionable_feedback_and_are_charged(self):
        for path in ('/','///',' /etc/ ','../','sympy/../','sympy//matrices/','sympy/./','sympy\\matrices','sympy\0/'):
            with self.subTest(path=path):
                before=self.session.budget.report()['used']['tools']
                with self.assertRaisesRegex(ValueError,'SEARCH_PATH_INVALID.*relative.*repo_search'):
                    self.search(path)
                self.assertEqual(self.session.budget.report()['used']['tools'],before+1)
                self.assertEqual(self.session.budget.report()['pending'],0)
    def test_v4_search_mock_recovers_then_reads_edits_and_checks(self):
        class RecoveringProvider(FiniteProvider):
            def prepare(self,messages,*args):
                self.ctx=json.loads(messages[-1]['content'])
                self.contexts=getattr(self,'contexts',[])+[self.ctx]
                return super().prepare(messages,*args)
            def complete(self,*args,**kw):
                ctx=self.ctx;feedback=ctx['feedback']
                if len(self.contexts)==1 or feedback.get('error'):
                    act={'action':'repo_search','arguments':{'path':'sympy/matrices/expressions/','pattern':'BlockMatrix'}}
                elif feedback.get('retained'):act={'action':'finish','arguments':{}}
                elif 'matches' in feedback:
                    act={'action':'file_view','arguments':{'path':'a.py'}}
                elif ctx['role']=='locator':act={'action':'finish','arguments':{}}
                elif ctx['role']=='editor':act={'action':'patch_apply','arguments':{'path':'a.py','search':'value = 1\n','replace':'value = 2\n'}}
                else:act={'action':'finish','arguments':{}}
                return dict(content=json.dumps(act),tokens_evaluated=100,tokens_predicted=10)
        p=RecoveringProvider([])
        result=run_episode(self.session.base,'E',73,provider=p,output=self.root/'episode',
            check_plan={'public_targets':['positive']},check_fn=checks,interface_version=2)
        self.assertIn('+value = 2',result['model_patch'])
        self.assertFalse(any(c['feedback'].get('error') for c in p.contexts), [(c['role'],c['feedback']) for c in p.contexts])
        self.assertEqual(result['budget']['used']['llm_calls'],5)

    def test_search_cursor_uses_canonical_query_across_path_spellings(self):
        (self.root/'src'/self.path/'blockmatrix.py').write_text('BlockMatrix = None\n'*12)
        snap=repo_store(self.root/'paging-store').capture(self.root/'src')
        self.session=Workspace(self.root/'paging-session',RepoBase(self.session.base.task,snap,self.session.base.environment))
        reply=self.search(self.path+'/');hits=list(reply['matches'])
        while reply['cursor']:
            reply=self.search(self.path,reply['cursor']);hits.extend(reply['matches'])
        self.assertEqual([x['line'] for x in hits],list(range(1,13)))
        self.assertFalse(any(x['body'].get('event')=='repoworld.cursor-reset' for x in self.session.receipts.records))

    def test_invented_cursor_feedback_explains_null_without_accepting_it(self):
        for token in ('issue','current'):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError,'cursor=null'):
                dispatch_tool(dict(tool='file_view',snapshot_id=self.session.current.id,path='a.py',start_line=1,line_count=1,cursor=token),session=self.session)
        self.assertEqual(self.session.budget.report()['pending'],0)
