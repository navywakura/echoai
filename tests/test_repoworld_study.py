import json
from pathlib import Path
import tempfile
import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.study import schedule_for,write_gate,require_gate,require_launch


class StudyTests(unittest.TestCase):
    def test_unstarted_rows_remain_in_frozen_denominator_and_cannot_hide_attempts(self):
        from echoai.repoworld.study import record_not_started
        from echoai.repoworld.evaluator import freeze_set,validate_frozen_set
        from echoai.pcworld.receipts import ReceiptStore
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);store=ReceiptStore(p/'receipts',p/'authority')
            cell={'cell_id':'one','instance_id':'fixture__repo-1','arm':'S','seed':73}
            value=record_not_started(store,cell,'global cap')
            self.assertEqual(value,record_not_started(store,cell,'global cap'))
            freeze_set(p/'frozen',[cell],{'one':value},lock_sha256='a'*64)
            self.assertTrue(validate_frozen_set(p/'frozen',[cell],lock_sha256='a'*64))
            attempted={**cell,'cell_id':'two'}
            store.append({'event':'repoworld.cell-start','cell_id':'two'})
            with self.assertRaises(ValueError):record_not_started(store,attempted,'global cap')

    def test_calibration_rejects_gate_for_another_registry_before_provider(self):
        from unittest.mock import patch
        from echoai.repoworld.study import calibrate_remote
        sample=ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json'
        contract=json.loads((ROOT/'ECHO-5.1/docs/SWE-CONTRACT.json').read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);registry=p/'registry.json';registry.write_text('{}')
            report={'valid':True,'registry_sha256':'0'*64}
            with patch('echoai.repoworld.study.require_gate',return_value=report),patch('echoai.repoworld.study.RepoProvider',side_effect=AssertionError('must not initialize remote')):
                with self.assertRaisesRegex(ValueError,'registry/sample/dataset'):
                    calibrate_remote(registry,contract,sample,preflight_dir=p,curator_dir=p,smoke_dir=p,
                        provider_config={},instance_id='psf__requests-2148',output=p/'run')

    def test_model_settings_are_fixed_but_a_tunnel_origin_can_rotate(self):
        from echoai.repoworld.provider import validate_model_config,provider_identity
        contract=json.loads((ROOT/'ECHO-5.1/docs/SWE-CONTRACT.json').read_bytes())
        config=dict(backend='llama_cpp',revision=contract['model']['revision'],context_tokens=4096,
            max_output_tokens=768,temperature_milli=200,timeout_seconds=240,endpoint='https://a.invalid/completion')
        validate_model_config(config,contract)
        with self.assertRaises(ValueError):validate_model_config({**config,'temperature_milli':1000},contract)
        self.assertEqual(provider_identity(config),provider_identity({**config,'endpoint':'https://b.invalid/completion'}))

    def test_study_cannot_mix_two_valid_locks_in_one_output(self):
        from echoai.repoworld.study import bind_study
        from echoai.pcworld.receipts import ReceiptStore
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);store=ReceiptStore(p/'receipts',p/'authority')
            bind_study(store,{'lock':'a'*64})
            bind_study(store,{'lock':'a'*64})
            with self.assertRaises(ValueError):bind_study(store,{'lock':'b'*64})
            self.assertEqual(len(store.records),1)

    def test_changing_sources_during_a_gate_invalidates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            value=write_gate(tmp,{'kind':'mock-smoke','valid':True},source_before={'old.py':'1'*64})
            self.assertFalse(value['valid'])
            with self.assertRaises(ValueError):require_gate(tmp,'mock-smoke')

    def test_curator_command_keeps_virtualenv_interpreter_path(self):
        from echoai.repoworld.evaluator import curator_command
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);real=p/'python-real';real.touch()
            venv=p/'env/bin/python';venv.parent.mkdir(parents=True);venv.symlink_to(real)
            self.assertEqual(curator_command(venv,'--controls','request.json')[0],str(venv))

    def test_schedule_includes_controls_and_memory_before_any_final_release(self):
        c=json.loads((ROOT/'ECHO-5.1/docs/SWE-CONTRACT.json').read_bytes())
        s=json.loads((ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json').read_bytes())
        rows=schedule_for(c,s)
        self.assertEqual(len(rows),150)
        self.assertEqual(len({r['cell_id'] for r in rows}),150)
        self.assertEqual(sum(r['phase']=='primary' for r in rows),96)

    def test_missing_or_tampered_gate_does_not_create_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'missing'
            with self.assertRaises((ValueError,FileNotFoundError)):require_gate(p,'offline-preflight')
            self.assertFalse(p.exists())
            write_gate(p,{'kind':'offline-preflight','valid':False,'gpu_hours':0})
            with self.assertRaises(ValueError):require_gate(p,'offline-preflight')
            data=json.loads((p/'report.json').read_bytes());data['report']['valid']=True
            (p/'report.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):require_gate(p,'offline-preflight')

    def test_design_contract_cannot_launch_even_with_fabricated_flags(self):
        with self.assertRaises(ValueError):require_launch({'status':'design','launch_enabled':False},None,None)

    def test_unsigned_seal_cannot_launch_even_if_json_hashes_are_recomputed(self):
        from echoai.repoworld.study import validate_seal
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ('SWE-CONTRACT.json','SWE-RUN-LOCK.json','schedule.json'):(p/name).write_text('{}')
            with self.assertRaises(ValueError):validate_seal(p,ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json')
            self.assertFalse((p/'authority').exists())
