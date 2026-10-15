import dataclasses
import difflib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.environment import repo_store
from echoai.repoworld.types import PublicTask, EnvironmentRef, RepoBase
from echoai.repoworld.workspace import Workspace, stage_patch
from echoai.repoworld.tools import dispatch_tool


def diff(path,old,new):
    return ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+path,tofile='b/'+path))


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);source=self.root/'source';source.mkdir()
        for name,value in {'a.py':'value = 1\n','b.py':'value = 2\n','unicode.txt':('á'*80+'\n')*120+'second\n','tests/test_a.py':'assert True\n'}.items():
            (source/name).parent.mkdir(parents=True,exist_ok=True);(source/name).write_text(value)
        snap=repo_store(self.root/'base').capture(source)
        base=RepoBase(PublicTask('x__y-1','x/y','a'*40,'fixture'),snap,EnvironmentRef('b'*64,'c'*64,self.root/'unused'))
        self.session=Workspace(self.root/'session',base)

    def request(self,**kw): return dispatch_tool(kw,session=self.session)

    def test_second_hunk_failure_has_no_partial_write(self):
        current=self.session.current
        bad=diff('a.py','value = 1\n','value = 3\n')+diff('b.py','not here\n','BAD\n')
        with self.assertRaises(ValueError): self.session.stage(bad,current.id)
        self.assertEqual(self.session.current.id,current.id)
        self.assertEqual(self.session.store.read(current,'a.py'),b'value = 1\n')

    def test_stage_retain_cas_and_roundtrip(self):
        current=self.session.current
        candidate=self.session.stage(diff('a.py','value = 1\n','value = 4\n'),current.id)
        self.assertEqual(self.session.current.id,current.id)
        self.assertNotEqual(candidate.snapshot.id,current.id)
        with self.assertRaises(ValueError): self.session.retain(candidate,expected_head='0'*64,public_receipt_ids=())
        with self.assertRaises(ValueError): self.session.retain(candidate,expected_head=current.id,public_receipt_ids=())
        receipt=self.session.receipts.append({'event':'repoworld.public-property','candidate':candidate.snapshot.id,
                  'property_status':'supported','checker_id':'calibration-only','scope':'public'})
        self.session.retain(candidate,expected_head=current.id,public_receipt_ids=(receipt['sha256'],))
        self.assertEqual(self.session.current.id,candidate.snapshot.id)
        final=self.session.final_diff()
        reconstructed=stage_patch(self.session.base,self.session.base.snapshot,final,
                                  expected_snapshot_id=self.session.base.snapshot.id,purpose='solution')
        self.assertEqual(reconstructed.snapshot.id,candidate.snapshot.id)

    def test_paths_modes_tests_binary_and_oversize_denied(self):
        for path in ('../escape','/absolute','.git/config','tests/test_a.py','sub/conftest.py'):
            with self.assertRaises(ValueError): self.session.stage(diff(path,'value = 1\n','BAD\n'),self.session.current.id)
        for text in ('GIT binary patch\n','old mode 100644\nnew mode 100755\n','x'*65537):
            with self.assertRaises(ValueError): self.session.stage(text,self.session.current.id)

    def test_recovery_before_after_receipt_and_head_is_idempotent(self):
        for where in ('intent','receipt','head'):
            session=Workspace(self.root/where,self.session.base)
            old=session.current.id
            candidate=session.stage(diff('a.py','value = 1\n','value = 9\n'),old)
            receipt=session.receipts.append({'event':'repoworld.public-property','candidate':candidate.snapshot.id,
                           'property_status':'supported','checker_id':'calibration-only','scope':'public'})
            def fail(point):
                if point==where: raise OSError('simulated crash')
            with patch.object(session,'_crash_hook',side_effect=fail):
                with self.assertRaises(OSError): session.retain(candidate,expected_head=old,public_receipt_ids=(receipt['sha256'],))
            recovered=Workspace(self.root/where,self.session.base)
            self.assertEqual(recovered.current.id,candidate.snapshot.id)
            events=[r for r in recovered.receipts.records if r['body'].get('event')=='repoworld.retain']
            self.assertEqual(len(events),1)
            recovered.retain(candidate,expected_head=old,public_receipt_ids=(receipt['sha256'],))
            self.assertEqual(len([r for r in recovered.receipts.records if r['body'].get('event')=='repoworld.retain']),1)

    def test_cursor_reset_cross_tool_and_snapshot_but_not_forgery(self):
        from echoai.repoworld.tools import _cursor
        current=self.session.current.id
        search=dict(tool='repo_search',snapshot_id=current,pattern='value',path='.',literal=True,cursor=None)
        token=_cursor(self.session,search,100)
        view=dict(tool='file_view',snapshot_id=current,path='a.py',start_line=1,line_count=1,cursor=token)
        self.assertIn('value = 1',self.request(**view)['lines'][0]['text'])
        view_token=_cursor(self.session,dict(view,cursor=None),[999,1])
        self.assertEqual(len(self.request(**dict(search,cursor=view_token))['matches']),2)
        candidate=self.session.stage(diff('a.py','value = 1\n','value = 3\n'),current)
        self.assertIn('value = 3',self.request(**dict(view,snapshot_id=candidate.snapshot.id,cursor=view_token))['lines'][0]['text'])
        forged=token[:-1]+('0' if token[-1]!='0' else '1')
        with self.assertRaisesRegex(ValueError,'authentication'):
            self.request(**dict(view,cursor=forged))
        events=[r['body'] for r in self.session.receipts.records]
        self.assertEqual(sum(r.get('event')=='repoworld.cursor-reset' for r in events),3)

    def test_mismatch_eof_is_bounded_and_does_not_mutate(self):
        current=self.session.current.id
        text='--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,2 @@\n value = 1\n-'+('é'*4000)+'\n+x\n'
        with self.assertRaisesRegex(ValueError,"expected '<EOF>'") as caught:
            self.session.stage(text,current)
        self.assertLess(len(str(caught.exception).encode()),800)
        self.assertEqual(self.session.current.id,current)

    def test_unicode_atomic_line_paging_and_cursor_binding(self):
        request=dict(tool='file_view',snapshot_id=self.session.current.id,path='unicode.txt',start_line=1,line_count=100,cursor=None)
        text='';numbers=[]
        for _ in range(200):
            response=self.request(**request)
            self.assertLessEqual(len(json.dumps(response,ensure_ascii=False).encode()),8192)
            self.assertLessEqual(response['output_tokens'],6000)
            text+=''.join(r['text'] for r in response['lines']);numbers += [r['number'] for r in response['lines']]
            cursor=response['cursor']
            if not cursor: break
            if request['cursor'] is None:
                bad=dict(request,cursor=cursor,path='a.py')
                self.assertEqual(self.request(**bad)["lines"][0]["number"],1)
            request['cursor']=cursor
        else: self.fail('pagination did not terminate')
        self.assertEqual(text,('á'*80+'\n')*100)
        self.assertEqual(numbers[-1],100)
        self.assertIn(1,numbers)
        with self.assertRaises(ValueError): self.request(**dict(request,line_count=101))

    def test_search_is_literal_and_snapshot_scoped(self):
        r=self.request(tool='repo_search',snapshot_id=self.session.current.id,pattern='value =',path='.',literal=True,cursor=None)
        self.assertEqual({v['path'] for v in r['matches']},{'a.py','b.py'})
        r=self.request(tool='repo_search',snapshot_id=self.session.current.id,pattern='.*',path='.',literal=True,cursor=None)
        self.assertEqual(r['matches'],[])
        with self.assertRaises(ValueError): self.request(tool='repo_search',snapshot_id='e'*64,pattern='x',path='.',literal=True,cursor=None)

    def test_tool_fails_closed_for_unknown_check_and_budget(self):
        with self.assertRaises(ValueError): self.request(tool='test_run',candidate_id=self.session.current.id,check_id='shell rm',probe_id=None)
        from echoai.pcworld.accounting import Budget, BudgetExceeded
        self.session.budget=Budget({'fuel':1,'tools':1,'output_tokens':1,'cpu_us':1000000})
        with self.assertRaises(BudgetExceeded): self.request(tool='file_view',snapshot_id=self.session.current.id,path='a.py',start_line=1,line_count=2,cursor=None)

    def test_tampered_retained_pointer_is_not_a_completed_transaction(self):
        candidate=self.session.stage(diff('a.py','value = 1\n','value = 9\n'),self.session.current.id)
        (self.session.directory/'state.json').write_text(json.dumps(dict(head=candidate.snapshot.id,pending=None)))
        with self.assertRaises(ValueError): Workspace(self.session.directory,self.session.base)

    def test_forged_pending_transaction_without_evidence_is_refused(self):
        old=self.session.current.id
        candidate=self.session.stage(diff('a.py','value = 1\n','value = 9\n'),old)
        state=dict(head=old,pending={'from':old,'to':candidate.snapshot.id,'operation_id':candidate.operation_id,'public_receipt_ids':['0'*64]})
        (self.session.directory/'state.json').write_text(json.dumps(state))
        with self.assertRaises(ValueError): Workspace(self.session.directory,self.session.base)

    def test_search_pagination_covers_more_than_thirty_lines_in_one_file(self):
        candidate=self.session.stage(diff('a.py','value = 1\n','needle\n'*40),self.session.current.id)
        request=dict(tool='repo_search',snapshot_id=candidate.snapshot.id,pattern='needle',path='a.py',literal=True,cursor=None)
        hits=[]
        for _ in range(30):
            result=self.request(**request);hits.extend(row['line'] for row in result['matches'])
            if result['cursor'] is None: break
            request['cursor']=result['cursor']
        self.assertEqual(hits,list(range(1,41)))

    def test_existing_empty_line_and_out_of_range_view(self):
        result=self.request(tool='file_view',snapshot_id=self.session.current.id,path='a.py',start_line=1000,line_count=3,cursor=None)
        self.assertEqual(result['lines'],[])
        self.assertIsNone(result['cursor'])

    def test_tool_cpu_and_failed_requests_are_accounted(self):
        before=self.session.budget.report()['used']['cpu_us']
        self.request(tool='file_view',snapshot_id=self.session.current.id,path='a.py',start_line=1,line_count=2,cursor=None)
        after=self.session.budget.report()['used']['cpu_us']
        self.assertGreater(after,before)
        with self.assertRaises(ValueError): self.request(tool='file_view',snapshot_id=self.session.current.id,path='../escape',start_line=1,line_count=2,cursor=None)
        self.assertGreater(self.session.budget.report()['used']['cpu_us'],after)
        self.assertEqual(self.session.receipts.records[-1]['body']['event'],'repoworld.tool-error')

    def test_create_delete_and_missing_newline_roundtrip(self):
        from echoai.repoworld.workspace import _parse_diff
        source=self.session.current
        patch_text='--- /dev/null\n+++ b/newdir/new.py\n@@ -0,0 +1 @@\n+hello\n\\ No newline at end of file\n'
        candidate=self.session.stage(patch_text,source.id)
        self.assertEqual(self.session.store.read(candidate.snapshot,'newdir/new.py'),b'hello')
        receipt=self.session.receipts.append({'event':'repoworld.public-property','candidate':candidate.snapshot.id,
                           'property_status':'supported','checker_id':'fixture','scope':'public'})
        self.session.retain(candidate,expected_head=source.id,public_receipt_ids=(receipt['sha256'],))
        self.assertEqual(self.session.final_diff(),patch_text)

    def test_quote_heavy_page_cannot_overrun_or_freeze_budget(self):
        for text in ('"'*2000, '\x01'*2000, '\\'*2000):
            proposal=diff('a.py','value = 1\n',text+'\n')
            candidate=self.session.stage(proposal,self.session.current.id)
            request=dict(tool='file_view',snapshot_id=candidate.snapshot.id,path='a.py',start_line=1,line_count=1,cursor=None)
            if text.startswith('\x01'):
                with self.assertRaisesRegex(ValueError,'complete line.*page budget'):
                    self.request(**request)
            else:
                result=self.request(**request)
                self.assertLessEqual(result['output_tokens'],6000)
                self.assertEqual(result['lines'][0]['text'],text+'\n')
            self.assertFalse(self.session.budget.report()['frozen'])

    def test_cumulative_export_supports_multiple_bounded_proposals(self):
        for names in ([f'file{i}.py' for i in range(8)],['file8.py']):
            old=self.session.current.id
            text=''.join('--- /dev/null\n+++ b/'+name+'\n@@ -0,0 +1 @@\n+x = 1\n' for name in names)
            candidate=self.session.stage(text,old)
            r=self.session.receipts.append({'event':'repoworld.public-property','candidate':candidate.snapshot.id,
                         'property_status':'supported','checker_id':'fixture','scope':'public'})
            self.session.retain(candidate,expected_head=old,public_receipt_ids=(r['sha256'],))
        final=self.session.final_diff()
        self.assertEqual(final.count('+++ b/file'),9)

    def test_search_path_tolerance_does_not_relax_snapshot_or_patch_paths(self):
        from echoai.pcworld.snapshots import _parts
        for bad in ('/','a.py/','../a.py','tests/../a.py'):
            with self.subTest(path=bad):
                with self.assertRaises(ValueError):_parts(bad)
                with self.assertRaises(ValueError):self.session.stage(diff(bad,'value = 1\n','value = 3\n'),self.session.current.id)
        source=self.root/'links';source.mkdir();(source/'escape').symlink_to('/etc')
        with self.assertRaises(ValueError):repo_store(self.root/'unsafe-store').capture(source)
