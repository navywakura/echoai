"""Private inference handoff: no live network or GPU in these tests."""
import base64
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARE = runpy.run_path(str(ROOT/'ECHO-5.1/scripts/prepare_kaggle_repair.py'))['prepare']
DOWNLOAD = runpy.run_path(str(ROOT/'ECHO-5.1/scripts/kaggle_repair_worker.py'))['download']


class GPUHandoff(unittest.TestCase):
    def test_unsuccessful_local_repair_does_not_enable_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir()
            (run/'result.json').write_text(json.dumps({'episodes':[
                {'counterexamples_repaired':False,'final_cases_passed':False}]}))
            with self.assertRaisesRegex(ValueError,'prerequisite'):
                PREPARE(run,root/'upload','owner/private-test')
            self.assertFalse((root/'upload').exists())

    def test_upload_is_private_and_contains_no_private_oracle_or_receipt_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir()
            (run/'result.json').write_text(json.dumps({'episodes':[
                {'task':'example','arm':'E','counterexamples_repaired':True,'final_cases_passed':True}]}))
            task={k:'public' for k in ('description','property','checker','input_schema','preconditions')}
            task.update(id='example',input_json_schema={'type':'array'},
                        development_inputs=['PRIVATE_ORACLE_SENTINEL'])
            (run/'tasks.json').write_text(json.dumps([task]))
            ep=run/'example-E';tree=ep/'snapshots'/'version'/'tree';tree.mkdir(parents=True)
            (tree/'solution.py').write_text('print(0)')
            body={'role':'propose','snapshot':'version','repair_feedback':{
                'failures':[{'input':[1],'observed':0,'expected':1}], 'public_examples':[]}}
            (ep/'thought.jsonl').write_text(json.dumps({'body':body})+'\n')
            (ep/'authority').mkdir();(ep/'authority/key').write_text('AUTHORITY_SECRET_SENTINEL')
            out=root/'upload';PREPARE(run,out,'owner/private-test')
            self.assertIs(json.loads((out/'kernel-metadata.json').read_text())['is_private'],True)
            payload=(out/'input-local.json').read_text()
            self.assertNotIn('PRIVATE_ORACLE_SENTINEL',payload)
            self.assertNotIn('development_inputs',payload)
            self.assertNotIn('AUTHORITY_SECRET_SENTINEL',payload)
            self.assertIn('print(0)',payload)
            sources=json.loads((out/'upload-manifest.json').read_text())
            self.assertEqual(set(sources),{'repair-input.json','connector/pcworld/__init__.py',
                'connector/pcworld/provider.py','connector/pcworld/protocol.py','proposer-worker.py'})
            compile((out/'kernel.py').read_text(),'kernel.py','exec')

    def test_wrong_download_hash_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_bytes(b'wrong bytes')
            dest=root/'model'
            with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
                DOWNLOAD(source.as_uri(),dest,hashlib.sha256(b'expected').hexdigest())
            self.assertFalse(dest.exists())
