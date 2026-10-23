import json
import hashlib
from contextlib import ExitStack, contextmanager
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.study import schedule_for,write_gate,require_gate,require_launch


class StudyTests(unittest.TestCase):
    @contextmanager
    def bounded_campaign(self, *, episode_seconds=0, phase_hours=6):
        """Real orchestration/ledger/freezing, simulated gates, model and repos."""
        from echoai.repoworld import study
        from echoai.pcworld.receipts import canonical
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root=Path(tmp);sealed=root/'sealed';sealed.mkdir();clock=[0.0]
            registry=root/'registry.json';registry.write_text('{}')
            sample=root/'sample.json';sample.write_text('{}')
            schedule=[dict(cell_id=f'cell-{i}',instance_id=f'fixture__repo-{i}',repo='fixture/repo',
                           arm='E',seed=73,phase='primary') for i in range(3)]
            contract={'gpu_budget':{'total_cap_hours':18,'phase_caps_hours':{'primary':phase_hours}}}
            lock={'code_manifest_sha256':hashlib.sha256(canonical({})).hexdigest(),
                  'schedule_sha256':hashlib.sha256(canonical(schedule)).hexdigest(),
                  'instances':[dict(instance_id=c['instance_id'],online_tree_sha256='tree',
                      online_rootfs_sha256='runtime',public_checks_sha256='checks') for c in schedule]}
            for name,data in [('SWE-CONTRACT.json',contract),('SWE-RUN-LOCK.json',lock),('schedule.json',schedule)]:
                (sealed/name).write_bytes(canonical(data))
            gate={'registry_sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),
                  'model_config_sha256':hashlib.sha256(canonical(study.provider_identity({}))).hexdigest()}
            tasks={c['instance_id']:SimpleNamespace(instance_id=c['instance_id']) for c in schedule}
            entries={k:{'check_plan':{}} for k in tasks}
            executed=[];provider=Mock();provider.stop.return_value={'stopped':True};provider.verify_worker.return_value={}
            def prepare(task,entry,output):
                return SimpleNamespace(task=task,snapshot=SimpleNamespace(id='tree'),
                                       environment=SimpleNamespace(rootfs_sha256='runtime'))
            def episode(base,arm,seed,**kwargs):
                executed.append(base.task.instance_id);clock[0]+=episode_seconds
                value=dict(instance_id=base.task.instance_id,arm=arm,seed=seed,status='finished',model_patch='')
                p=kwargs['output'];p.mkdir(parents=True,exist_ok=True);(p/'mock-result.json').write_bytes(canonical(value))
                return value
            replacements={'validate_seal':{'gates':{k:{'directory':root} for k in ('offline-preflight','remote-calibration')}},
                'require_gate':gate,'validate_model_config':None,'require_launch':None,'source_manifest':{},
                'load_registry':(tasks,entries,{}),'validate_plan':'checks','RepoProvider':provider}
            for name,value in replacements.items():stack.enter_context(patch.object(study,name,return_value=value))
            stack.enter_context(patch.object(study,'prepare_entry',side_effect=prepare))
            stack.enter_context(patch.object(study,'run_episode',side_effect=episode))
            stack.enter_context(patch.object(study.time,'monotonic',side_effect=lambda:clock[0]))
            stack.enter_context(patch.object(study.time,'time',side_effect=lambda:10000+clock[0]))
            stack.enter_context(patch('echoai.repoworld.audit.audit_episode',side_effect=lambda p:
                {'result':json.loads((Path(p)/'mock-result.json').read_bytes())}))
            yield SimpleNamespace(run=lambda **kw:study.run_study(sealed,registry,sample,{},root/'run',phase='primary',**kw),
                root=root,executed=executed,provider=provider)

    def test_batch_limit_pauses_before_next_cell_and_resumes_without_reexecution(self):
        from echoai.repoworld.evaluator import existing_receipts
        with self.bounded_campaign() as c:
            first=c.run(max_episodes=1)
            self.assertTrue(first['paused']);self.assertFalse(first['phase_complete'])
            self.assertEqual(first['completed'],1);self.assertEqual(first['not_started'],0)
            self.assertEqual(first['phase_remaining'],2);self.assertFalse(first['frozen'])
            rows=[r['body'] for r in existing_receipts(c.root/'run').records]
            self.assertEqual(sum(r['event']=='repoworld.cell-start' for r in rows),1)
            self.assertEqual(sum(r['event']=='repoworld.gpu-window-start' for r in rows),1)
            self.assertEqual(sum(r['event']=='repoworld.gpu-window-end' for r in rows),1)
            self.assertEqual(sum(r['event']=='repoworld.batch-paused' for r in rows),1)
            self.assertFalse((c.root/'run/frozen/freeze.json').exists())
            second=c.run(max_episodes=2)
            self.assertFalse(second['paused']);self.assertTrue(second['phase_complete']);self.assertTrue(second['frozen'])
            self.assertEqual(second['completed'],3);self.assertEqual(second['batch_completed'],2)
            self.assertEqual(c.executed,['fixture__repo-0','fixture__repo-1','fixture__repo-2'])
            third=c.run(max_episodes=1)
            self.assertEqual(third['batch_completed'],0);self.assertEqual(len(c.executed),3)
            self.assertEqual(c.provider.stop.call_count,3)

    def test_batch_wall_limit_reserves_episode_room_and_preserves_global_time(self):
        from echoai.repoworld.evaluator import existing_receipts
        with self.bounded_campaign(episode_seconds=1900) as c:
            result=c.run(batch_seconds=3600)
            self.assertTrue(result['paused']);self.assertEqual(result['completed'],1)
            self.assertEqual(result['not_started'],0)
            resumed=c.run(batch_seconds=3600)
            self.assertTrue(resumed['paused']);self.assertEqual(resumed['completed'],2)
            windows=[r['body'] for r in existing_receipts(c.root/'run').records if r['body']['event']=='repoworld.gpu-window-end']
            self.assertEqual(sum(r['seconds'] for r in windows),3800)

    def test_registered_cap_still_accounts_unstarted_cells_instead_of_batch_retry(self):
        with self.bounded_campaign(episode_seconds=1900,phase_hours=1) as c:
            result=c.run(batch_seconds=3600)
            self.assertFalse(result['paused']);self.assertTrue(result['phase_complete'])
            self.assertEqual((result['completed'],result['not_started']),(1,2));self.assertTrue(result['frozen'])

    def test_invalid_batch_limits_fail_before_provider_or_filesystem_access(self):
        from echoai.repoworld.study import run_study
        for options in ({'max_episodes':0},{'max_episodes':True},{'batch_seconds':1800},
                        {'batch_seconds':8400},{'batch_seconds':True}):
            with self.subTest(options=options),patch('echoai.repoworld.study.RepoProvider',side_effect=AssertionError('no provider')):
                with self.assertRaisesRegex(ValueError,'batch'):
                    run_study(None,None,None,{},None,**options)

    def test_seal_binds_offline_service_in_addition_to_official_image(self):
        from echoai.repoworld.study import validate_curator_binding
        row={k:'a'*64 for k in ('official_image_digest','official_eval_script_sha256','sealed_tests_sha256')}
        row.update(empty_patch_resolved=False,gold_patch_resolved=True)
        validate_curator_binding(row,row)
        served={**row,'service_manifest_sha256':'b'*64}
        validate_curator_binding(served,served)
        for changed in (row,{**served,'service_manifest_sha256':'c'*64}):
            with self.assertRaisesRegex(ValueError,'service'):
                validate_curator_binding(changed,served)

    def test_curator_calibration_scope_cannot_satisfy_full_controls_gate(self):
        from echoai.repoworld.study import curator_scope
        sample=json.loads((ROOT/'repository/docs/swebench/SWE-SAMPLE.json').read_bytes())
        kind,rows=curator_scope(sample,'calibration')
        self.assertEqual(kind,'official-calibration-controls')
        self.assertEqual({r['instance_id'] for r in rows},{r['instance_id'] for r in sample['calibration']})
        self.assertEqual(len(rows),4)
        full_kind,full_rows=curator_scope(sample,'all')
        self.assertEqual(full_kind,'official-controls');self.assertEqual(len(full_rows),36)
        with tempfile.TemporaryDirectory() as tmp:
            write_gate(tmp,{'kind':kind,'valid':True,'results':rows})
            with self.assertRaises(ValueError):require_gate(tmp,'official-controls')
        with self.assertRaises(ValueError):curator_scope(sample,'primary')

    def test_seal_binds_reporting_profile_including_its_absence(self):
        from echoai.repoworld.study import validate_curator_binding
        row={k:'a'*64 for k in ('official_image_digest','official_eval_script_sha256','sealed_tests_sha256')}
        row.update(empty_patch_resolved=False,gold_patch_resolved=True)
        reported={**row,'reporting_profile_sha256':'b'*64}
        validate_curator_binding(reported,reported)
        for left,right in ((row,reported),(reported,row),({**reported,'reporting_profile_sha256':'c'*64},reported)):
            with self.assertRaisesRegex(ValueError,'reporting'):
                validate_curator_binding(left,right)

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
        sample=ROOT/'repository/docs/swebench/SWE-SAMPLE.json'
        contract=json.loads((ROOT/'repository/docs/SWE-CONTRACT.json').read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);registry=p/'registry.json';registry.write_text('{}')
            report={'valid':True,'registry_sha256':'0'*64}
            with patch('echoai.repoworld.study.require_gate',return_value=report),patch('echoai.repoworld.study.RepoProvider',side_effect=AssertionError('must not initialize remote')):
                with self.assertRaisesRegex(ValueError,'registry/sample/dataset'):
                    calibrate_remote(registry,contract,sample,preflight_dir=p,curator_dir=p,smoke_dir=p,
                        provider_config={},instance_id='psf__requests-2148',output=p/'run')

    def test_model_settings_are_fixed_but_a_tunnel_origin_can_rotate(self):
        from echoai.repoworld.provider import validate_model_config,provider_identity
        contract=json.loads((ROOT/'repository/docs/SWE-CONTRACT.json').read_bytes())
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
        c=json.loads((ROOT/'repository/docs/SWE-CONTRACT.json').read_bytes())
        s=json.loads((ROOT/'repository/docs/swebench/SWE-SAMPLE.json').read_bytes())
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
            with self.assertRaises(ValueError):validate_seal(p,ROOT/'repository/docs/swebench/SWE-SAMPLE.json')
            self.assertFalse((p/'authority').exists())
