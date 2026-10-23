import importlib
import unittest
from pathlib import Path

from echoai.echo58.enjambre.team import L1,L2,RM,card,read
from echoai.echo58.memx.memory import OUTCOMES


def counts(outcome,n=3):
    c=[0]*len(OUTCOMES);c[OUTCOMES.index(outcome)]=n;return c


class TransportTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/enjambre2/transport.py'
        self.assertTrue(path.exists(),'authenticated transport missing')
        self.t=importlib.import_module('echoai.echo58.enjambre2.transport')

    def test_authenticated_validation_is_atomic(self):
        b=self.t.Board();raw=card(L1,1,(50,0,'ENTER',0),counts('PASS'))
        for bad,author in ((raw,2),(raw[:-1],1),(raw[:11]+bytes([9])+raw[12:],1)):
            with self.assertRaises(ValueError):b.post(bad,author=author,round=1,original=bad)
        self.assertEqual(b.records,[]);self.assertEqual(b.latest,{})
        b.post(raw,author=1,round=1,original=raw);b.post(raw,author=1,round=2,original=raw)
        self.assertEqual(sum(b.view()[(L1,(50,0,'ENTER',0))]),3)
        self.assertEqual(len(b.records),2)

    def test_false_safe_and_alarm_only_change_registered_outcomes(self):
        for attack,before,after in (('false_safe','HURT','PASS'),('false_safe','NOOP','PASS'),
                                    ('false_alarm','PASS','HURT'),('false_alarm','GOAL','HURT')):
            raw=card(L1,2,(50,0,'ENTER',0),counts(before));a=self.t.Attacker(2,attack)
            pairs=a.transform([raw],1);self.assertEqual(pairs[0][0],raw)
            got=read(pairs[0][1]);self.assertEqual(got[:3],read(raw)[:3])
            self.assertEqual(got[3:],(OUTCOMES.index(after),255,255))
        raw=card(L1,2,(50,0,'ENTER',0),counts('HURT'))
        self.assertEqual(self.t.Attacker(2,'false_alarm').transform([raw],1),[(raw,raw)])

    def test_remote_attack_sees_all_current_originals_and_keeps_ids(self):
        remote=card(RM,2,(40,91),[3,3]);local=card(L1,2,(77,0,'ENTER',12),counts('PASS'))
        a=self.t.Attacker(2,'false_remote');pairs=a.transform([remote,local],1)
        self.assertEqual(read(pairs[0][1])[2],(40,12))
        self.assertEqual(read(pairs[0][1])[4:],(255,255))
        self.assertEqual(read(a.transform([remote],2)[0][1])[2],(40,12))
        self.assertEqual(self.t.Attacker(2,'false_remote').transform([remote],1),[(remote,remote)])
        with self.assertRaises(ValueError):a.transform([card(RM,1,(40,91),[3,3])],2)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/enjambre2/memory.py'
        self.assertTrue(path.exists(),'risk memory missing')
        self.m=importlib.import_module('echoai.echo58.enjambre2.memory')
        self.t=importlib.import_module('echoai.echo58.enjambre2.transport')

    def reader(self,arm,claims,p=None):
        p=p or self.m.Private(3);p.world=0
        return self.m.Reader(arm,p,claims,{},[],{},world=0,round=2)

    def test_weighted_control_and_per_author_control_can_differ(self):
        k=(L1,(50,0,'ENTER',0));claims={k:{0:(0,255,255),1:(2,3,3),2:(2,3,3)}}
        self.assertEqual(self.reader('ingenuo',claims).recall(50,0,'ENTER',0),'PASS')
        self.assertIsNone(self.reader('por_autor',claims).recall(50,0,'ENTER',0))

    def test_fresh_voices_dispute_safe_specificity_and_confirmation(self):
        k=(L1,(50,0,'ENTER',0));p=self.m.Private(3)
        rd=self.reader('prudente',{k:{0:(2,3,3),1:(2,3,3)}},p)
        self.assertIsNone(rd.recall(50,0,'ENTER',0))
        p.trust.good[0]=1
        self.assertEqual(rd.recall(50,0,'ENTER',0),'HURT')
        for claims in ({0:(0,3,3),1:(2,3,3)},{0:(0,3,3),1:(4,3,3)}):
            self.assertIsNone(self.reader('prudente',{k:claims}).recall(50,0,'ENTER',0))
        self.assertEqual(self.reader('prudente',{k:{0:(0,3,3)}}).recall(50,0,'ENTER',0),'PASS')

    def test_trust_updates_only_from_own_consequences_once_and_rehabilitates(self):
        p=self.m.Private(3);p.world=0
        k=(L1,p.mem.cfg.l1_key(50,0,'ENTER',0))
        p.set_snapshot({k:{0:(0,255,255),1:(2,3,3),3:(0,255,255)}},2)
        self.assertEqual(p.trust.bad,{})
        p.observe(50,0,'ENTER',0,'HURT')
        self.assertEqual(p.trust.bad,{0:1});self.assertEqual(p.trust.good,{1:1})
        p.observe(50,0,'ENTER',0,'HURT')
        self.assertEqual(p.trust.bad,{0:1})
        self.assertFalse(p.trust.credible(0))
        for ident in (51,52,53):
            key=(L1,p.mem.cfg.l1_key(ident,0,'ENTER',0))
            p.set_snapshot({key:{0:(2,3,3),1:(0,3,3)}},3)
            p.observe(ident,0,'ENTER',0,'HURT')
        self.assertTrue(p.trust.credible(0));self.assertEqual(p.trust.good[0],3)
        self.assertNotIn(3,p.trust.bad)

    def test_private_truth_precedes_global_and_testimony_never_written_private(self):
        p=self.m.Private(3);p.world=0
        key=(L1,p.mem.cfg.l1_key(50,0,'ENTER',0));claims={key:{0:(0,255,255)}}
        rd=self.reader('prudente',claims,p)
        self.assertEqual(rd.recall(50,0,'ENTER',0),'PASS');self.assertEqual(p.mem.raw,[])
        for _ in range(3):p.observe(50,0,'ENTER',0,'HURT')
        self.assertEqual(rd.recall(50,0,'ENTER',0),'HURT');self.assertEqual(rd.by_source['here'],1)

    def test_remote_requires_confirmed_voices_and_does_not_train_trust(self):
        k=(RM,(40,91));p=self.m.Private(3)
        rd=self.reader('prudente',{k:{0:(0,3,3),1:(0,3,3)}},p)
        self.assertFalse(rd.knows(40,91));p.trust.good[0]=1
        self.assertTrue(rd.knows(40,91));p.remote_observe(40,[91])
        self.assertEqual(p.trust.good,{0:1});self.assertEqual(p.trust.bad,{})

    def test_honest_reader_matches_original_on_synthetic_queries(self):
        from echoai.echo58.enjambre.team import Private,Reader,as_counts
        old=Private();old.world=0;new=self.m.Private(3);new.world=0
        keys=[(L1,(50,0,'ENTER',0)),(L2,(0,'ENTER',0)),(RM,(40,91))]
        claims={k:{0:(0,3,3),1:(0,5,6)} for k in keys}
        legacy=Reader(old.mem.cfg,old,{k:as_counts(v.values()) for k,v in claims.items()},{},world=0)
        current=self.reader('honesto',claims,new)
        for ident in (50,51):self.assertEqual(current.recall(ident,0,'ENTER',0),legacy.recall(ident,0,'ENTER',0))
        self.assertEqual(current.knows(40,91),legacy.knows(40,91))

    def test_exposure_counts_only_global_queries_and_detects_response_change(self):
        raw=card(L1,0,(50,0,'ENTER',0),counts('HURT'))
        sent=self.t.Attacker(0,'false_safe').transform([raw],1)[0][1]
        board=self.t.Board();board.post(sent,author=0,round=1,original=raw)
        claims,provenance=board.snapshot();p=self.m.Private(3);p.world=0
        rd=self.m.Reader('ingenuo',p,claims,provenance,board.records,{},world=0,round=2)
        self.assertEqual(rd.recall(50,0,'ENTER',0),'PASS')
        self.assertEqual(rd.recall(50,0,'ENTER',0),'PASS')
        trace=rd.queries_receipt();self.assertEqual(len(trace),1);self.assertEqual(trace[0]['count'],2)
        self.assertEqual(trace[0]['altered'],[0]);self.assertIsNone(trace[0]['without_altered'])
        for _ in range(3):p.observe(50,0,'ENTER',0,'HURT')
        self.assertEqual(rd.recall(50,0,'ENTER',0),'HURT')
        self.assertEqual(sum(q['count'] for q in rd.queries_receipt()),2)

    def test_integer_core_no_hidden_model_and_no_credit_without_dispute(self):
        import ast
        for name in ('transport.py','memory.py'):
            tree=ast.parse((Path(self.m.__file__).parent/name).read_text())
            self.assertFalse(any(isinstance(n,ast.Constant) and type(n.value) is float for n in ast.walk(tree)))
            self.assertFalse(any(isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div) for n in ast.walk(tree)))
        p=self.m.Private(3);p.world=0;key=(L1,p.mem.cfg.l1_key(50,0,'ENTER',0))
        p.set_snapshot({key:{0:(0,3,3)}},1);p.observe(50,0,'ENTER',0,'PASS')
        self.assertEqual(p.trust.good,{});self.assertEqual(p.trust.bad,{})

    def test_audit_rejects_local_truth_and_unrelated_request(self):
        v=importlib.import_module('echoai.echo58.enjambre2.verify')
        self.assertTrue(hasattr(v,'validate_request'),'physical request audit missing')
        p=self.m.Private(3);p.world=0
        for _ in range(3):p.observe(50,0,'ENTER',0,'HURT')
        q={'layer':L1,'key':[50,0,'ENTER',0],'request':[50,0,'ENTER',0],'world':0}
        with self.assertRaises(ValueError):v.validate_request(q,p,{})
        q['request']=[51,0,'ENTER',0]
        with self.assertRaises(ValueError):v.validate_request(q,p,{})


class HarnessTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).resolve().parents[1]/'echo58/enjambre2/bench.py'
        self.assertTrue(path.exists(),'development harness missing')
        self.b=importlib.import_module('echoai.echo58.enjambre2.bench')

    def test_schedule_is_48_unique_jobs_and_exam_has_no_entry_point(self):
        jobs=self.b.jobs();self.assertEqual(len(jobs),48);self.assertEqual(len(set(jobs)),48)
        self.assertEqual(sum(a=='honesto' for a,t,m in jobs),3)
        self.assertFalse(hasattr(self.b,'exam'))
        for a,t,m in jobs:
            worlds=self.b.mission(m)
            self.assertEqual(len(worlds),8)
            self.assertEqual({w['seed'] for w in worlds},set(range(12100000+1000*m,12100008+1000*m)))
        for m in (0,4,True):
            with self.assertRaises(ValueError):self.b.mission(m)

    def test_freeze_is_exclusive_and_detects_a_changed_input(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);contract=root/'contract.md';contract.write_text('fixture')
            self.b.prepare(root/'run',contract)
            self.b.check_frozen(root/'run')
            with self.assertRaises(FileExistsError):self.b.prepare(root/'run',contract)
            contract.write_text('changed')
            with self.assertRaises(ValueError):self.b.check_frozen(root/'run')

    def test_harness_fixture_rebuilds_publications_and_detects_attack_tamper(self):
        import json,copy
        from unittest.mock import patch
        path=Path(self.b.__file__).with_name('verify.py');self.assertTrue(path.exists(),'offline auditor missing')
        v=importlib.import_module('echoai.echo58.enjambre2.verify')
        class FixtureWorld:
            def __init__(self,kind,seed,n,ids):self.solved_by=0;self.needs_help=False;self.ids=ids
        def fixture_play(world,agents):
            for agent in agents:
                ident=min(world.ids.values());agent.source.recall(ident,0,'ENTER',0)
                agent.learn.observe(ident,0,'ENTER',0,'PASS')
            return [{'harm':0,'steps':1,'asked':0,'held':0} for _ in agents]
        with patch.object(self.b,'CoopWorld',FixtureWorld),patch.object(self.b,'play_together',fixture_play):
            for arm in self.b.ARMS:
                job=(arm,'none' if arm=='honesto' else 'false_alarm',1)
                row=json.loads(json.dumps(self.b.run_team(*job)))
                self.assertEqual(v.validate_job(job,row)['score'],12)
                report_path=Path(self.b.__file__).with_name('report.py')
                self.assertTrue(report_path.exists(),'development report missing')
                report=importlib.import_module('echoai.echo58.enjambre2.report')
                summary=report.summarize({self.b.name(job):v.validate_job(job,row)})
                self.assertIsNone(summary['scientific_exam_verdict']);self.assertFalse(summary['exam_run'])
                grouped=summary['groups']['false_alarm' if arm!='honesto' else 'false_safe'][arm]
                self.assertIn('by_kind',grouped);self.assertIn('trust_by_author',grouped)
                if arm=='ingenuo':
                    self.assertGreater(v.validate_job(job,row)['exposure_queries'],0)
                    changed=copy.deepcopy(row);changed['publications'][0]['sent']='00'*16
                    with self.assertRaises(ValueError):v.validate_job(job,changed)
                    changed=copy.deepcopy(row)
                    for rr in changed['rounds']:
                        for ep in rr['episodes']:
                            for q in ep['queries']:q['request']=['not a physical request']
                    with self.assertRaises(ValueError):v.validate_job(job,changed)

    def test_completed_rounds_survive_later_worker_failure(self):
        import tempfile,json
        from unittest.mock import patch
        calls=[]
        class FixtureWorld:
            def __init__(self,kind,seed,n,ids):self.solved_by=0;self.needs_help=False;self.ids=ids
        def fixture_play(world,agents):
            calls.append(1)
            if len(calls)>4:raise RuntimeError('synthetic failure in round2')
            for agent in agents:agent.learn.observe(min(world.ids.values()),0,'ENTER',0,'PASS')
            return [{'harm':0,'steps':1,'asked':0,'held':0} for _ in agents]
        with tempfile.TemporaryDirectory() as d,patch.object(self.b,'CoopWorld',FixtureWorld),patch.object(self.b,'play_together',fixture_play):
            job=('ingenuo','false_safe',1);receipt=self.b.worker(job,d)
            self.assertEqual(receipt['status'],'error')
            path=Path(d)/self.b.name(job).removesuffix('.json')/'r01.json'
            first=json.loads(path.read_text());self.assertEqual(len(first['round']['episodes']),4)
            self.assertEqual(sum(map(len,first['observations'])),4)

    def test_auditor_rejects_forged_totals_and_scope_before_a_run(self):
        path=Path(self.b.__file__).with_name('verify.py')
        self.assertTrue(path.exists(),'offline auditor missing')
        v=importlib.import_module('echoai.echo58.enjambre2.verify')
        for row in ({'exam_run':True},{'exam_run':False,'phase':'exam'}):
            with self.assertRaises(ValueError):v.validate_job(('prudente','false_safe',1),row)

    def test_synthetic_receipts_audit_and_tamper_detection_without_worlds(self):
        import tempfile,json,copy
        path=Path(self.b.__file__).with_name('verify.py');self.assertTrue(path.exists(),'offline auditor missing')
        v=importlib.import_module('echoai.echo58.enjambre2.verify')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);contract=root/'contract.md';contract.write_text('Synthetic receipts, not a game run.')
            run=root/'run';self.b.prepare(run,contract);(run/'runs').mkdir();hashes={}
            for job in self.b.jobs():
                arm,attack,m=job;worlds=self.b.mission(m)
                by_kind={k:{'harm':0,'episodes':30*sum(w['kind']==k for w in worlds[:4])} for k in ('door','lava','plate','local')}
                episodes=[{'agent':a,'world':a,'win':False,'result':{'harm':0,'steps':300,'asked':0,'held':0},
                    'answers':dict.fromkeys(('here','private','notes','global'),0),'global_asks':0,'abstentions':0,'queries':[]} for a in range(4)]
                row={'arm':arm,'attack':attack,'macro':m,'phase':'development','exam_run':False,'bad_author':m%4,
                    'worlds':worlds,'language_ids':list(self.b.language(12100000+1000*m+999).values()),
                    'score':248,'solved_round':[31]*8,'solved':0,'destroyed':0,'card_bytes':[],
                    'rounds':[{'round':r,'assignments':[0,1,2,3],'next_assignments':[0,1,2,3],
                        'postcards_before':0,'postcards_after':0,'episodes':copy.deepcopy(episodes)} for r in range(1,31)],
                    'notes':[],'publications':[],'observations':[[] for _ in range(4)],'remote_observations':[[] for _ in range(4)],
                    'trust':[{'good':{},'bad':{},'events':[],'verified':0} for _ in range(4)],
                    'episodes':120,'failed':120,'harm':0,'postcards':0,'notes_cards':0,'helps':0,'asked':0,'held':0,
                    'answers':dict.fromkeys(('here','private','notes','global'),0),'by_kind':by_kind}
                if job==self.b.jobs()[0]:
                    short=copy.deepcopy(row);short['rounds']=short['rounds'][:1];short['episodes']=4;short['failed']=4
                    for value in short['by_kind'].values():value['episodes']//=30
                    with self.assertRaises(ValueError):v.validate_job(job,short)
                name=self.b.name(job);(run/'runs'/name).write_text(json.dumps({'status':'ok','job':list(job),'result':row}))
                hashes[name]=self.b.sha(run/'runs'/name)
                for r in range(1,31):
                    journal=run/'rounds'/name.removesuffix('.json')/f'r{r:02d}.json';journal.parent.mkdir(parents=True,exist_ok=True)
                    journal.write_text(json.dumps(self.b.round_record(row,r)))
            complete={'jobs':hashes,'jobs_count':48,'preflight_sha256':self.b.sha(run/'preflight.json'),'exam_run':False}
            complete['round_files']={str(p.relative_to(run)):self.b.sha(p) for p in (run/'rounds').rglob('*.json')}
            (run/'completed.json').write_text(json.dumps(complete))
            self.assertTrue(v.verify(run)['audit_green'])
            name=next(iter(hashes));path=run/'runs'/name;forged=json.loads(path.read_text());forged['result']['score']=0
            path.write_text(json.dumps(forged));complete['jobs'][name]=self.b.sha(path)
            (run/'completed.json').write_text(json.dumps(complete))
            with self.assertRaises(ValueError):v.verify(run)


if __name__=='__main__':unittest.main()
