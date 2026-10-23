"""New PERCIBE-X protocol tests; synthetic inputs are not flight evidence."""
import unittest
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
import runpy
import os
import math
from unittest.mock import patch
from types import SimpleNamespace

from echoai.echo58.percibex.online import Online
from echoai.echo58.percibex.protocol import packet, unpack, SCHOOL, FREEZE, TICK, RECEIPT, INSPECT, family_key
from echoai.echo58.memx.memory import l1_key, l2_key
from echoai.echo58.percibex.bundle import build, ROOT, FROZEN
from echoai.echo58.percibex.resources import bounded_podman_args, install, THREADS, supervisor_limits, cleanup_owned_containers, LABEL
from echoai.echo58.percibex.flight import yaw_delta, yaw_target, inspection_angle_ok
from echoai.echo58.percibex.audit import report_schema_ok
from echoai.echo58.percibex import session as percibe_session
from echoai.echo58.percibex import campaign as percibe_campaign, audit as percibe_audit


class OnlineTests(unittest.TestCase):
    def test_contract_and_prior_reviews_are_in_source_inventory(self):
        with patch.object(percibe_campaign,'sha',return_value='0'*64):
            names = set(percibe_campaign.inventory())
        required = {'ECHO-5.8/docs/PERCIBEX-DESIGN-20261023.md',
                    'ECHO-5.8/docs/PERCIBEX-PLAN-20261023.md',
                    'lab/echo58/percibex/20261023-r1/resource-cleanup-review.json',
                    'lab/echo58/percibex/20261023-r1/contract-freeze-review.json',
                    'lab/echo58/closure-20261023/recovery-oom/p-container-cleanup-preflight.json'}
        self.assertTrue(required <= names, sorted(required-names))

    def test_editing_contract_after_prepare_invalidates_source_checks(self):
        with patch.object(percibe_campaign,'sha',return_value='0'*64):
            names = set(percibe_campaign.inventory())
        design = 'ECHO-5.8/docs/PERCIBEX-DESIGN-20261023.md'
        names.add(design)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in names:
                path = root/name; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text('fixture '+name+'\n')
            def bundle(path, **kw):
                path.write_bytes(b'fixture bundle')
                return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'files':{}}
            with patch.object(percibe_campaign,'ROOT',root), \
                 patch.object(percibe_campaign,'LAB',root/'lab/stage'), \
                 patch.object(percibe_campaign,'build',side_effect=bundle), \
                 patch.object(percibe_campaign.contract,'configuration',return_value={'timeouts':{}}):
                plan, _ = percibe_campaign.prepare('development')
            before = percibe_audit.check_sources(plan,root=root)
            self.assertTrue(all(before.values()))
            (root/design).write_text('fixture changed acceptance threshold\n')
            after = percibe_audit.check_sources(plan,root=root)
            self.assertFalse(after[design])
            self.assertTrue(all(v for k,v in after.items() if k != design))

    def test_cleanup_revalidates_exact_label_and_never_touches_foreign_or_invalid_ids(self):
        own, foreign, changed = 'a'*64, 'b'*64, 'c'*64
        inspected = {own:0, foreign:0, changed:0}
        calls = []
        def run(argv, **kw):
            calls.append(argv)
            self.assertLessEqual(kw['timeout'], 5)
            if argv[1]=='ps': return SimpleNamespace(returncode=0, stdout=own+'\n'+foreign+'\n'+changed+'\n--all\n', stderr='')
            if argv[1]=='inspect':
                ident = argv[-1]; inspected[ident] += 1
                value = LABEL.split('=',1)[1] if ident==own or (ident==changed and inspected[ident]==1) else LABEL.split('=',1)[1]+'-other'
                return SimpleNamespace(returncode=0,stdout=json.dumps({'echoai.study':value}),stderr='')
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        with patch('echoai.echo58.percibex.resources.subprocess.run', side_effect=run):
            receipt = cleanup_owned_containers('test-timeout')
        mutations = [a for a in calls if a[1] in ('stop','rm','kill')]
        self.assertTrue(mutations)
        self.assertTrue(all(a[-1] == own for a in mutations))
        self.assertIn('label='+LABEL, calls[0])
        self.assertEqual(receipt['invalid_ids'],1)
        self.assertEqual(set(receipt['ownership_rejected']), {foreign,changed})
        self.assertNotIn(LABEL.split('=',1)[1]+'-other',json.dumps(receipt))

    def test_cleanup_rechecks_before_remove_and_keeps_missing_ownership_honest(self):
        own = 'f'*64
        for final in (SimpleNamespace(returncode=0,stdout=json.dumps({'echoai.study':'foreign'}),stderr=''),
                      SimpleNamespace(returncode=125,stdout='',stderr='')):
            responses = [SimpleNamespace(returncode=0,stdout=own+'\n',stderr=''),
                         SimpleNamespace(returncode=0,stdout=json.dumps({'echoai.study':LABEL.split('=',1)[1]}),stderr=''),
                         SimpleNamespace(returncode=0,stdout=json.dumps({'echoai.study':LABEL.split('=',1)[1]}),stderr=''),
                         SimpleNamespace(returncode=0,stdout='',stderr=''),final]
            with patch('echoai.echo58.percibex.resources.subprocess.run',side_effect=responses) as run:
                receipt = cleanup_owned_containers('test')
                mutations = [c.args[0] for c in run.call_args_list if c.args[0][1] in ('stop','rm','kill')]
                self.assertEqual([a[1] for a in mutations],['stop'])
                self.assertNotIn('auto_removed',receipt)
                if final.returncode: self.assertEqual(receipt['unavailable_after_stop'],[own])

    def test_cleanup_listing_timeout_and_malformed_labels_cannot_escalate_scope(self):
        with patch('echoai.echo58.percibex.resources.subprocess.run',
                   side_effect=subprocess.TimeoutExpired('podman',5)) as run:
            r = cleanup_owned_containers('timeout')
            self.assertFalse(r['ok']); self.assertEqual(run.call_count,1)
        responses = [SimpleNamespace(returncode=0,stdout='d'*64+'\n',stderr=''),
                     SimpleNamespace(returncode=0,stdout='[]',stderr='')]
        with patch('echoai.echo58.percibex.resources.subprocess.run',side_effect=responses) as run:
            r = cleanup_owned_containers('bad-labels')
            self.assertEqual(run.call_count,2)
            self.assertEqual(r['operations'],[])

    def test_session_timeout_cleans_study_and_restores_imported_bindings(self):
        original = percibe_session.original
        before = (original.CONSUMER,original.TAP,original.Forwarder,original.sandbox.spawn,original.subprocess)
        def timed_out(*a, **kw):
            return original.subprocess.run(['podman','run'])
        fake_process = SimpleNamespace(run=lambda *a,**kw: (_ for _ in ()).throw(subprocess.TimeoutExpired('podman',1)),
                                       TimeoutExpired=subprocess.TimeoutExpired)
        with tempfile.TemporaryDirectory() as td, \
             patch.object(original,'subprocess',fake_process), \
             patch.object(original,'run_episode',side_effect=timed_out), \
             patch('echoai.echo58.percibex.session.cleanup_owned_containers',return_value={'ok':True}) as cleanup:
            with self.assertRaises(subprocess.TimeoutExpired):
                percibe_session.run_episode(None,None,None,{}, {},arm='MEMX',label='test',root=Path(td),
                    consumer_path=Path('consumer.pyz'),tap_path=Path('flight.pyz'))
            cleanup.assert_called_once_with('flight_subprocess_timeout')
            self.assertTrue((Path(td)/'operational-cleanup.jsonl').exists())
            self.assertIs(original.subprocess,fake_process)
        self.assertEqual((original.CONSUMER,original.TAP,original.Forwarder,original.sandbox.spawn,original.subprocess),before)

    def test_session_failure_cleans_once_and_success_does_not_clean(self):
        original = percibe_session.original
        for ok in (False,True):
            episode = SimpleNamespace(ok=ok,metrics={'container_returncode':0})
            with tempfile.TemporaryDirectory() as td, \
                 patch.object(original,'run_episode',return_value=(episode,{'consumer_returncode':0})), \
                 patch('echoai.echo58.percibex.session.cleanup_owned_containers',return_value={'ok':True}) as clean:
                returned, sensors = percibe_session.run_episode(None,None,None,{}, {},arm='MEMX',label='test',root=Path(td),
                    consumer_path=Path('consumer.pyz'),tap_path=Path('flight.pyz'))
                self.assertIs(returned,episode)
                self.assertEqual(clean.call_count,0 if ok else 1)
                self.assertEqual(len(sensors['operational_cleanup']),0 if ok else 1)

    def test_report_extra_channel_and_transport_field_are_rejected(self):
        report = dict(transport=dict(frames=0,schema_errors=0,invalid=0,header_digest='0'*64),
                      wsp=[],sightings=[],online={})
        self.assertTrue(report_schema_ok(report))
        self.assertFalse(report_schema_ok(dict(report,debug={})))
        report['transport']['pose'] = [1,2,3]
        self.assertFalse(report_schema_ok(report))

    def test_yaw_inspection_is_relative_bounded_and_wraps_both_frames(self):
        for baseline in (0., 1.5, -1.5, math.pi-.1, -math.pi+.1):
            target = yaw_target(baseline)
            self.assertAlmostEqual(yaw_delta(target,baseline), .4)
            self.assertTrue(inspection_angle_ok(yaw_delta(target,baseline)))
            self.assertTrue(inspection_angle_ok(-.4))
            self.assertFalse(inspection_angle_ok(2.))
            self.assertFalse(inspection_angle_ok(.2))
        self.assertAlmostEqual(yaw_delta(-math.pi+.1,math.pi-.1), .2)

    def test_generated_podman_wrapper_writes_real_jsonl_without_running_podman(self):
        with tempfile.TemporaryDirectory() as td:
            install(td, '/usr/bin/bwrap')
            log = str(Path(td)/'launches.jsonl')
            with patch.dict(os.environ, {'PERCIBEX_RESOURCE_LOG':log}), \
                 patch.object(sys,'argv',[str(Path(td)/'podman'),'run','image']), \
                 patch('os.execv', side_effect=SystemExit(0)) as execute:
                with self.assertRaises(SystemExit): runpy.run_path(str(Path(td)/'podman'))
            raw = Path(log).read_bytes()
            self.assertTrue(raw.endswith(b'\n'))
            self.assertEqual(len(raw.splitlines()), 1)
            event = json.loads(raw)
            self.assertEqual(event['event'], 'bounded_podman_run')
            self.assertEqual(execute.call_args.args[1], bounded_podman_args(['run','image']))

    def test_supervisor_guard_reads_effective_parent_memory_limits(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)/'cgroup'; child = root/'parent/child'; child.mkdir(parents=True)
            proc = Path(td)/'self'; proc.write_text('0::/parent/child\n')
            for key in ('memory.max','memory.high'): (child/key).write_text('max')
            (child.parent/'memory.max').write_text(str(2*1024**3))
            (child.parent/'memory.high').write_text(str(1536*1024**2))
            self.assertTrue(supervisor_limits(proc, root)['bounded'])
            (child.parent/'memory.max').write_text('max')
            self.assertFalse(supervisor_limits(proc, root)['bounded'])

    def test_podman_caps_and_thread_values_cannot_be_bypassed(self):
        args = bounded_podman_args(['run','--rm','--pull=never','image','python3'])
        for flag in ('--cpus=1.5','--memory=3g','--memory-swap=3g','--pids-limit=128'):
            self.assertIn(flag, args)
        for key in THREADS: self.assertIn(key+'=1', args)
        self.assertEqual(bounded_podman_args(['ps']), ['/usr/bin/podman','ps'])
        with self.assertRaises(ValueError): bounded_podman_args(['run','--memory=8g','image'])

    def test_cage_gate_applies_one_cpu_and_512_mib_before_exec(self):
        with tempfile.TemporaryDirectory() as td:
            details = install(td, '/usr/bin/bwrap')
            proc = subprocess.run([str(Path(td)/'bwrap-bounded'),'--resource-probe'],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            probe = json.loads(proc.stdout)
            self.assertEqual(len(probe['affinity']), 1)
            self.assertEqual(probe['rlimit_as'], [512*1024*1024]*2)
            self.assertEqual(details['cage_affinity_cpus'], 1)

    def test_bundle_sources_are_byte_identical_and_consumer_replies_before_eof(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'consumer.pyz'
            manifest = build(path)
            with zipfile.ZipFile(path) as z:
                for target, source in FROZEN.items():
                    self.assertEqual(z.read(target), (ROOT/source).read_bytes())
            p = subprocess.Popen([sys.executable, str(path)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            raw = packet(SCHOOL, 1)
            h = json.dumps(dict(v=1, source='wsp', payload_len=16,
                                payload_sha256=hashlib.sha256(raw).hexdigest())).encode()
            p.stdin.write(len(h).to_bytes(4,'big')+h+(16).to_bytes(4,'big')+raw); p.stdin.flush()
            self.assertEqual(unpack(p.stdout.read(16))[1], 1)
            self.assertIsNone(p.poll())
            p.stdin.close(); p.stdin = None
            _, stderr = p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0, stderr.decode())
            self.assertEqual(json.loads(stderr)['online']['mode'], 'school')

    def test_all_64_family_keys_survive_both_memx_normalizations(self):
        keys = [family_key(f) for f in range(64)]
        self.assertEqual(len({l1_key(i, s, 'TOGGLE', 0) for i, s in keys}), 64)
        self.assertEqual(len({l2_key(s, 'TOGGLE', 0) for i, s in keys}), 64)

    def test_wsp16_roundtrip_rejects_extra_and_wrong_envelope(self):
        p = packet(SCHOOL, 1)
        self.assertEqual(len(p), 16)
        self.assertEqual(unpack(p), (SCHOOL, 1, 0))
        for bad in (p+b'x', bytes(16), p[:4]+b'\x01'+p[5:]):
            with self.assertRaises(ValueError): unpack(bad)

    def trained(self, arm='MEMX'):
        a = Online(arm, min_hits=4)
        a.control(packet(SCHOOL, 1))
        for t in range(40):
            a.sighting(t, 0x000f)
            a.sighting(t, 0xffff)
        return a

    def test_learning_occurs_before_eof_and_freeze_is_read_only(self):
        a = self.trained()
        self.assertEqual(a.pattern.observations, 80)
        self.assertEqual(a.pattern.size, 2)
        a.control(packet(FREEZE, 2))
        before = a.pattern.snapshot_hash()
        a.sighting(42, 0x001f)
        self.assertEqual(before, a.pattern.snapshot_hash())
        self.assertEqual(a.events[-1]['trained'], False)

    def test_identity_memory_needs_three_physical_receipts(self):
        a = self.trained()
        seq = 2
        for _ in range(6):
            raw = a.control(packet(TICK, seq))
            self.assertEqual(unpack(raw)[2], INSPECT)
            seq += 1
            a.control(packet(RECEIPT, seq, 1))
            seq += 1
        self.assertEqual(len(a.memory.records), 6)
        self.assertEqual({r['i'] for r in a.memory.records}, {1, 2})
        for _ in range(2):
            self.assertEqual(unpack(a.control(packet(TICK, seq)))[2], 0)
            seq += 1
        self.assertEqual(a.memory.destroyed, 0)

    def test_failed_receipt_does_not_become_pass(self):
        a = self.trained()
        a.control(packet(TICK, 2))
        a.control(packet(RECEIPT, 3, 0))
        self.assertEqual(a.memory.records[-1]['o'], 'NOOP')

    def test_visits_control_can_skip_after_failures_but_memx_cannot(self):
        for arm in ('MEMX', 'VISITS'):
            a = self.trained(arm)
            seq = 2
            for _ in range(6):
                a.control(packet(TICK, seq)); a.control(packet(RECEIPT, seq+1, 0)); seq += 2
            self.assertEqual(unpack(a.control(packet(TICK, seq)))[2], INSPECT if arm == 'MEMX' else 0)

    def test_receipt_without_pending_and_replay_are_rejected(self):
        a = self.trained()
        with self.assertRaises(ValueError): a.control(packet(RECEIPT, 2, 1))
        with self.assertRaises(ValueError): a.control(packet(SCHOOL, 1))

    def test_exam_actions_and_receipts_write_no_memory(self):
        a = self.trained()
        a.control(packet(FREEZE, 2))
        head = a.memory.head
        a.control(packet(TICK, 3))
        a.control(packet(RECEIPT, 4, 1))
        self.assertEqual(a.memory.head, head)
        self.assertEqual(a.memory.records, [])

    def test_empty_and_visits_are_declared_controls(self):
        for arm in ('EMPTY', 'VISITS'):
            a = self.trained(arm)
            seq = 2
            for _ in range(6):
                self.assertEqual(unpack(a.control(packet(TICK, seq)))[2], INSPECT)
                a.control(packet(RECEIPT, seq+1, 1)); seq += 2
            self.assertEqual(unpack(a.control(packet(TICK, seq)))[2], INSPECT if arm == 'EMPTY' else 0)


if __name__ == '__main__': unittest.main()
