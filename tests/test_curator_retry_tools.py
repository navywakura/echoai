"""Administrative retry custody tests, separate from the frozen curator runtime."""
import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
TOOL=runpy.run_path(str(ROOT/'repository/scripts/retry_curator_infrastructure.py'),run_name='retry_tool')
from echoai.repoworld.study import write_gate

class CuratorRetryTests(unittest.TestCase):
    def test_mixed_roster_retries_only_infrastructure_and_preserves_graded_failure(self):
        roster=[dict(instance_id='infra',base_commit='a'*40),dict(instance_id='graded',base_commit='b'*40)]
        report={'results':[{**roster[0],'valid':False,'error':'BuildImageError'},
                           {**roster[1],'valid':False,'empty_patch_resolved':True,'gold_patch_resolved':True}]}
        original=copy.deepcopy(report)
        self.assertEqual(TOOL['select_failures'](report,roster),['infra'])
        self.assertEqual(report,original)

    def test_only_infrastructure_failures_and_complete_rosters_are_retryable(self):
        roster=[dict(instance_id='public-a',base_commit='a'*40),dict(instance_id='public-b',base_commit='b'*40)]
        passed={**roster[0],'valid':True,'empty_patch_resolved':False,'gold_patch_resolved':True,
                'controls':{'empty':{'valid':True},'gold':{'valid':True}}}
        failed={**roster[1],'valid':False,'error':'BuildImageError'}
        report={'results':[passed,failed]}
        self.assertEqual(TOOL['select_failures'](report,roster),['public-b'])
        for error in (None,'control_timeout','gold_patch_did_not_apply'):
            changed=copy.deepcopy(report);changed['results'][1]['error']=error
            with self.assertRaises(ValueError):TOOL['select_failures'](changed,roster)
        with self.assertRaises(ValueError):TOOL['select_failures']({'results':[passed,passed]},roster)
        changed=copy.deepcopy(report);changed['results'][1]['base_commit']='c'*40
        with self.assertRaises(ValueError):TOOL['select_failures'](changed,roster)

    def test_parent_authentication_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            write_gate(root,dict(kind='official-controls',scope='all',valid=False,source_unchanged=True,results=[]))
            self.assertFalse(TOOL['authenticated_parent'](root)['report']['valid'])
            path=root/'report.json';value=json.loads(path.read_bytes());value['report']['valid']=True
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'authentication'):TOOL['authenticated_parent'](root)

    def test_source_drift_rejected_even_with_authentic_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            write_gate(root,dict(kind='official-controls',scope='all',valid=False,source_unchanged=True,results=[]))
            function=TOOL['authenticated_parent']
            with patch.dict(function.__globals__,source_manifest=lambda:{'changed':'bytes'}):
                with self.assertRaisesRegex(ValueError,'sources changed'):function(root)

if __name__=='__main__':unittest.main()
