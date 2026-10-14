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
