"""Real correspondence defects, identity controls and X500 route geometry."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from echoai.nexus0.pattern1r_v2 import contract as ct, evaluate as ev
from echoai.nexus0.pattern1r import contract as old
from echoai.nexus0.flight1s.v3 import campaign as c
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET

G = ev.G


def scan(hits):
    return [hits.get(i, float('inf')) for i in range(360)]


class CorrespondenceTests(unittest.TestCase):
    def test_wraparound_does_not_duplicate_an_object(self):
        beams = list(range(350, 360))+list(range(9))
        runs = G.segments(scan({i: 5.0 for i in beams}))
        self.assertEqual(len(runs), 1)
        self.assertEqual(set(runs[0]), set(beams))
        self.assertEqual(len(runs[0]), len(beams))

    def test_missing_echoes_are_not_invented(self):
        values = scan({150: 5.0, 151: 5.0, 155: 5.0, 156: 5.0})
        ground = G.Ground()
        ground.record('lidar', 100, 'ok', 0, True, values)
        self.assertEqual(ground.sighting_beams, [(150, 151, 155, 156)])

    def test_a_previous_track_can_only_be_claimed_once(self):
        ground = G.Ground()
        ground.tracks = [[178, 5375, 4000, 5]]
        values = scan(dict([(i, 5.0) for i in range(174, 178)] +
                           [(i, 5.75) for i in range(180, 184)]))
        ground.track(100, values)
        self.assertEqual(len(ground.tracks), 2)
        self.assertEqual(sum(t[2] == 4000 for t in ground.tracks), 1)
        self.assertIsNot(ground.tracks[0], ground.tracks[1])

    def test_skipping_small_silhouette_never_shifts_next_object(self):
        package = SimpleNamespace(roles={'m0':'floor', 'm1':'barrier', 'm2':'barrier'})
        def record(t, hits):
            return dict(source='lidar', capture_ns=t, status='ok', gap=0,
                        valid=True, values=scan(hits), raw={'body':[0]*7})
        records = [record(100, dict([(i,5.0) for i in range(20,23)] +
                                    [(i,5.0) for i in range(190,195)])),
                   record(200, {i:5.0 for i in range(20,25)})]
        with patch.object(ev.sev, 'boxes', return_value=[None]*3), \
             patch.object(ev, 'sensor_pose', return_value=(None,None)), \
             patch.object(ev, 'beam_box', side_effect=lambda R,o,e,b,i: 1 if i < 100 else 2):
            emitted, annotations = ev.annotated_sightings(records, package)
        self.assertEqual([r[0] for r in emitted], [100,200])
        self.assertEqual([r['who'] for r in annotations], [2,1])

    def test_invalid_scan_emits_wsp_but_no_signature(self):
        ground = G.Ground()
        ground.record('lidar', 100, 'stale', 1, False, [])
        self.assertEqual(ground.sightings, [])
        self.assertEqual(len(bytes.fromhex(ground.packets[0])), 16)


class IdentityTests(unittest.TestCase):
    def test_rare_fragment_is_unknown_until_it_has_enough_evidence(self):
        from echoai.nexus0.pattern1 import InvariantPatternMemory
        weak = InvariantPatternMemory(min_hits=4)
        cautious = InvariantPatternMemory(min_hits=ev.PATTERN_LIMITS['min_family_evidence'])
        for mem in (weak,cautious):
            for _ in range(8): mem.observe(G.signature(1600),0)
            for _ in range(64): mem.observe(G.signature(4000),0)
        self.assertIsNotNone(weak.predict(G.signature(1900)))
        self.assertIsNone(cautious.predict(G.signature(1900)))
        self.assertIsNotNone(cautious.predict(G.signature(4000)))

    def test_wrong_signature_is_scored_but_wrong_timestamp_is_invalid(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        package=SimpleNamespace(roles={'m0':'floor','m1':'barrier','m2':'barrier'})
        annotations=[]
        for start in (1,100):
            for i in range(80):
                annotations.append(dict(capture=start+i,signature=G.signature(1000 if i%2 else 4000),
                                        who=1 if i%2 else 2,why='barrier'))
        honest=[[a['capture'],a['signature']] for a in annotations]
        wrong=[[a['capture'],G.signature(1000)] for a in annotations]
        plan=[dict(begin=1,end=80,school=True),dict(begin=100,end=179,school=False)]
        with patch.object(ev,'annotated_sightings',return_value=(honest,annotations)), \
             patch.object(ev,'legs',return_value=plan), \
             patch.object(ev,'survey_geometry',return_value=[dict(name='test',ok=True)]):
            result=ev.identity({},[],package,dict(sightings=wrong))
            self.assertFalse(result['signatures_only'][0]['ok'])
            self.assertEqual(result['identity'][0]['accuracy'],1)
            self.assertTrue(cp.mutant_caught('constant_family',result['identity']))
            wrong[0][0]=0
            bad=ev.identity({},[],package,dict(sightings=wrong))
            self.assertEqual(bad['identity'][0]['name'],'aligned_sightings')
            self.assertFalse(bad['identity'][0]['ok'])

    def test_constant_family_is_collapse_even_if_accuracy_is_perfect(self):
        data = [(1,G.signature(1000))]*40+[(2,G.signature(1000))]*40
        result = ev.score_identity(data, data, {1,2})
        cases = {x['name']:x for x in result['identity']}
        self.assertEqual(cases['same_object']['accuracy'], 1.0)
        self.assertFalse(cases['objects_separated']['ok'])

    def test_confusion_has_a_real_count_and_denominator(self):
        school = [(1,G.signature(1000))]*40+[(2,G.signature(4000))]*40
        exam = [(2,s) if w == 1 else (1,s) for w,s in school]
        result = ev.score_identity(school, exam, {1,2})
        case = next(x for x in result['identity'] if x['name']=='other_object')
        self.assertEqual((case['confused'],case['exam'],case['confusion']), (80,80,1.0))

    def test_unseen_exam_object_cannot_disappear_from_denominator(self):
        school = [(1,G.signature(1000))]*40+[(2,G.signature(4000))]*40
        result = ev.score_identity(school, school[:40], {1,2})
        self.assertFalse(next(x for x in result['identity'] if x['name']=='each_object_examined')['ok'])

    def test_exam_freezes_learning_and_catches_writes(self):
        data = [(1,G.signature(1000))]*40+[(2,G.signature(4000))]*40
        honest = ev.score_identity(data, data, {1,2})
        dirty = ev.score_identity(data, data, {1,2}, mutant='frozen_write')
        self.assertTrue(all(x['ok'] for x in honest['identity']+honest['frozen']))
        self.assertFalse(dirty['frozen'][0]['ok'])


class GeometryTests(unittest.TestCase):
    def test_integer_parameter_uses_px4_bytewise_encoding(self):
        import ast, struct, time
        from unittest.mock import Mock
        from echoai.nexus0.pattern1r_v2 import session
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Driver')
        method=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='set_param')
        ns=dict(struct=struct,time=time,mavutil=SimpleNamespace(mavlink=SimpleNamespace(MAV_PARAM_TYPE_INT32=6)))
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),ns)
        for value in (0,1,42):
            wire=struct.unpack('<f',struct.pack('<i',value))[0]
            conn=SimpleNamespace(target_system=1,target_component=1,
                mav=SimpleNamespace(param_set_send=Mock()),
                recv_match=Mock(return_value=SimpleNamespace(param_id='EKF2_HGT_REF',param_value=wire)))
            driver=SimpleNamespace(conn=conn,log=Mock())
            self.assertTrue(ns['set_param'](driver,'EKF2_HGT_REF',value,6))
            self.assertEqual(conn.mav.param_set_send.call_args.args[-2:],(wire,6))
            self.assertEqual(driver.log.call_args.kwargs['value'],value)

    def test_driver_accepts_contract_and_checks_parameter_readback(self):
        import ast, json, math, os
        from unittest.mock import patch
        from echoai.nexus0.pattern1r_v2 import session
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ConfiguredDriver')
        class FakeDriver:
            def __init__(self): self.events=[]
            def connect(self, timeout): return True
            def set_param(self, name, value, ptype):
                if ptype != (6 if name=='EKF2_HGT_REF' else 9): return False
                self.events.append(dict(name=name,value=value))
                return True
        namespace=dict(Driver=FakeDriver,json=json,math=math,os=os,
                       mavutil=SimpleNamespace(mavlink=SimpleNamespace(MAV_PARAM_TYPE_REAL32=9,MAV_PARAM_TYPE_INT32=6)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),namespace)
        params=ct.configuration()['px4_parameters']
        with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(params)):
            driver=namespace['ConfiguredDriver']()
            self.assertTrue(driver.connect(10))
            self.assertEqual({e['name']:e['value'] for e in driver.events},params)
        with patch.dict(os.environ,FLIGHT1S_PARAMETERS='{"UNREGISTERED":1}'):
            with self.assertRaises(ValueError): namespace['ConfiguredDriver']().connect(10)
        with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(params)):
            with patch.object(FakeDriver,'set_param',lambda self,n,v,t: self.events.append(dict(value=v+1)) or True):
                with self.assertRaises(RuntimeError): namespace['ConfiguredDriver']().connect(10)

    def test_reposition_declares_global_altitude_not_relative(self):
        import ast
        from unittest.mock import Mock
        from echoai.nexus0.pattern1r_v2 import session
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        driver=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Driver')
        method=next(n for n in driver.body if isinstance(n,ast.FunctionDef) and n.name=='reposition')
        namespace=dict(mavutil=SimpleNamespace(mavlink=SimpleNamespace(
            MAV_FRAME_GLOBAL_INT=5,MAV_CMD_DO_REPOSITION=192,MAV_RESULT_ACCEPTED=0)),SURVEY_SPEED_MS=1.0)
        exec(compile(ast.Module(body=[method],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),namespace)
        self_mock=SimpleNamespace(conn=SimpleNamespace(target_system=1,target_component=1,
                                  mav=SimpleNamespace(command_int_send=Mock())),_ack=Mock(return_value=0),log=Mock())
        self.assertTrue(namespace['reposition'](self_mock,47.0,8.0,502.25,0.0))
        args=self_mock.conn.mav.command_int_send.call_args.args
        self.assertEqual(args[2],5)
        self.assertEqual(args[-1],502.25)
        self.assertEqual(ct.configuration()['px4_parameters']['EKF2_HGT_REF'],0)
    def test_segment_interior_not_just_endpoints(self):
        box = ((-100,-100,0),(100,100,2000))
        self.assertEqual(ct.segment_box_distance((-1000,0),(1000,0),box), 0)
        self.assertEqual(ct.segment_box_distance((-1000,500),(1000,500),box), 400)

    def test_all_twelve_routes_fit_body_old_arcs_do_not(self):
        with tempfile.TemporaryDirectory() as d:
            pk = generate_suite(Path(d), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                                [(ct.WORLD_SPLIT,i,s) for i,s in zip(ct.WORLD_INDEX,ct.WORLD_SEEDS)],
                                family_path=c.ECHOAI/ct.FAMILY_PATH)
            for world in pk:
                new, prior = ct.route_check(world.package), ct.route_check(world.package, old.arc_viewpoints(world.package))
                self.assertTrue(new['ok'], new)
                self.assertGreaterEqual(new['min_clearance_mm'], 1200)
                self.assertFalse(prior['ok'], prior)
                self.assertEqual(len(ct.survey(world.package)['viewpoints_mm']),48)


class CampaignTests(unittest.TestCase):
    def test_code_integrity_cannot_mask_exam_memory_writes(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        data=[(1,G.signature(1000))]*40+[(2,G.signature(4000))]*40
        result=ev.score_identity(data,data,{1,2},mutant='frozen_write')
        gs={'frozen':cp.group(result['frozen'])}
        with patch.object(cp,'inventory',return_value={'code':'same'}), \
                patch.object(cp,'history',return_value={'sha256':'same'}):
            cp.check_integrity(gs,dict(inventory={'code':'same'},history_sha256='same'))
        self.assertEqual(gs['integrity']['status'],'pass')
        self.assertEqual(gs['frozen']['status'],'fail')
        self.assertFalse(all(g['status']=='pass' for g in gs.values()))

    def test_incomplete_or_changed_candidate_cannot_open_acceptance(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        with tempfile.TemporaryDirectory() as d, patch.object(cp,'ROOT',Path(d)):
            self.assertFalse(cp.development_ready())
            with self.assertRaises(RuntimeError):
                cp.freeze()
            self.assertFalse((Path(d)/'lock.json').exists())
            code = {name:cp.sha256_bytes((cp.HERE/name).read_bytes())
                    for name in cp.CANDIDATE_FILES}
            cp.save(Path(d)/(cp.DEVELOPMENT_NAME+'-plan.json'),cp.seal(dict(worlds=list(range(6)),code=code)))
            rows=[]
            for i in range(6):
                row=cp.seal(dict(label=f'{cp.DEVELOPMENT_NAME}-w{i}',world_index=i,passed=True,
                                 groups={'identity':{'status':'pass'}}))
                (Path(d)/'dev'/row['label']).mkdir(parents=True)
                cp.save(Path(d)/'dev'/row['label']/'evaluation.json',row)
                rows.append(row)
            cp.save(Path(d)/(cp.DEVELOPMENT_NAME+'-report.json'),cp.seal(dict(passed=True,code_unchanged=True,results=rows)))
            self.assertTrue(cp.development_ready())
            with patch.object(cp,'sha256_bytes',return_value='changed'):
                self.assertFalse(cp.development_ready())

    def test_no_survey_control_is_explicit_and_does_not_change_honest_config(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        p = cp.protocol()
        before = dict(p['configuration'])
        self.assertIs(cp.flight_configuration(p, 'control').get('survey', True), False)
        self.assertIs(cp.flight_configuration(p, 'clean').get('survey', True), True)
        self.assertEqual(p['configuration'], before)

    def test_constant_mutant_is_caught_by_collapse_with_a_nonempty_exam(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        data = [(1,G.signature(1000))]*40+[(2,G.signature(1000))]*40
        result = ev.score_identity(data, data, {1,2})
        self.assertTrue(cp.mutant_caught('constant_family', result['identity']))
        self.assertFalse(cp.mutant_caught('constant_family', [dict(name='objects_separated',ok=False,objects=0)]))

    def test_control_is_expected_negative_and_pooled_confusion_counts(self):
        from echoai.nexus0.pattern1r_v2 import campaign as cp
        p = cp.protocol()
        def base():
            return {k:[dict(name='base',ok=True)] for k in cp.GROUPS}
        main = base()
        main['identity'] = [dict(name='same_object',ok=False,accuracy=0.5,same=50,exam=100),
                            dict(name='other_object',ok=False,confusion=0.5,confused=50,exam=100)]
        control = base()
        control['survey'] = [dict(name='legs_settled',ok=False,settled=0)]
        control['identity'] = [dict(name='same_object',ok=False,accuracy=None,exam=0)]
        control['geometry'] = [dict(name='observed_body_clearance',ok=False)]
        records = [dict(arm='clean',label='main'),dict(arm='control',label='c0'),dict(arm='control',label='c1')]
        with patch.object(cp.evaluate,'noise_verdict',return_value=(True,{})), \
             patch.object(cp.model,'check',return_value={'ok':True}):
            groups = cp.stage_groups(records,[main,control,control],'validation',p,3,{'ok':True})
        self.assertEqual(groups['controls']['status'],'pass')
        self.assertEqual(groups['survey']['status'],'pass')
        self.assertEqual(groups['geometry']['status'],'pass')
        self.assertEqual(groups['identity_pooled']['cases'][0]['confused'],50)
        self.assertEqual(groups['identity_pooled']['status'],'fail')

    def test_prior_dynamic_certificate_inventory_is_unchanged(self):
        import json
        from echoai.nexus0.dynamic1_v2 import campaign as d2
        lock = json.loads((d2.ROOT/'lock.json').read_text())
        self.assertEqual(d2.inventory(),lock['inventory'])


if __name__ == '__main__':
    unittest.main()
