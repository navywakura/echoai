import copy
import random
import unittest
from echoai.nexus0.fusion1 import core as c, scenarios as s, judge
from echoai.nexus0.fusion1.integration import admit
from echoai.nexus0.constants import ACTION_WAIT, ACTION_APPROACH, GATE_BLOCK, GATE_OK
from echoai.nexus0.fusion1.replay import quantize
from echoai.core.wsp import pack


class FusionTests(unittest.TestCase):
    def test_contract_sequences(self):
        for case in s.generate(20261701,4):
            with self.subTest(case=case['condition']):
                self.assertEqual(judge.findings(case['commands'],c.run_commands(case['commands'])),[])

    def test_mutants_have_specific_witnesses(self):
        targets=dict(last_writer='conflict',no_expiry='expired',duplicate_votes='duplicates',
                     ignore_predicate='different_predicate',ignore_region='different_region',
                     erase_conflict='conflict',constant_confidence='no_return',unsafe_gate='blocked')
        for m,kind in targets.items():
            cmds=s.scenario(kind,random.Random(1))
            self.assertEqual(judge.findings(cmds,c.run_commands(cmds)),[])
            self.assertTrue(judge.findings(cmds,c.run_commands(cmds,m)),m)

    def test_prefix_cannot_revise_past(self):
        commands=s.scenario('recovery',random.Random(5))
        full=c.run_commands(commands)['decisions']
        for i in range(1,len(commands)+1):
            part=c.run_commands(commands[:i])['decisions']
            self.assertEqual(part,full[:len(part)])

    def test_packet_is_existing_layout(self):
        for v in (-1,0,1):
            w=c.packet(v,40)
            self.assertEqual(len(w),16)
            # navi10 pack is the authoritative layout; field name E is positional.
            self.assertEqual(w,pack(src=2,rel=31 if v==-1 else 14,dst=31 if v==-1 else 5 if v else 7,
                                   time=8,E=dict(V=0,A=10,D=0,C=40,U=0,B=0),
                                   domain=8,generator=7,style=1,slot=0,seq=0))

    def test_existing_gate_receives_inhibition(self):
        for value,confidence in ((-1,0),(0,40),(1,80)):
            self.assertEqual(admit(c.packet(value,confidence))[:2],(GATE_BLOCK,ACTION_WAIT))
        self.assertEqual(admit(c.packet(0,80))[:2],(GATE_OK,ACTION_APPROACH))

    def test_overflow_preserves_history_and_fails_closed(self):
        mem=c.EvidenceMemory()
        for i in range(c.CAPACITY+1):
            row=s.observe('depth',0,i);mem.ingest(bytes.fromhex(row.pop('wsp')),**{k:v for k,v in row.items() if k!='op'})
        before=copy.deepcopy(mem.records)
        self.assertEqual(c.unpack(mem.resolve(now_ns=c.CAPACITY))[:2],(-1,0))
        self.assertEqual(mem.records,before);self.assertEqual(len(before),c.CAPACITY)

    def test_no_return_is_not_free(self):
        for x in (float('nan'),float('inf'),-1.,0.,21.):self.assertEqual(quantize(x)[0],-1)
        self.assertEqual(quantize(2.)[0],-1)
        self.assertEqual(quantize(1.)[0],1)
        self.assertEqual(quantize(3.)[0],0)

    def test_extra_fields_rejected(self):
        row=s.observe('depth',0,1);row['world_name']='secret'
        with self.assertRaises(ValueError):c.run_commands([row])

    def test_clock_regressions_rejected(self):
        with self.assertRaises(ValueError):c.run_commands([s.query(3),s.query(2)])
        with self.assertRaises(ValueError):c.run_commands([s.query(3),s.observe('depth',0,2)])

    def test_ttl_boundary(self):
        rows=[s.observe('depth',0,0),s.observe('lidar',0,0),s.query(c.TTL),s.query(c.TTL+1)]
        out=c.run_commands(rows)['decisions']
        self.assertTrue(out[0]['allow_advance']);self.assertFalse(out[1]['allow_advance'])

    def test_false_extract_cannot_authorize(self):
        rows=[s.observe('depth',0,0,corrupt=True),s.observe('lidar',0,0),s.query(0)]
        self.assertFalse(c.run_commands(rows)['decisions'][0]['allow_advance'])

    def test_future_capture_cannot_poison_source_forever(self):
        rows=[s.observe('depth',1,999999999,arrival=0),s.observe('depth',0,1),
              s.observe('lidar',0,2),s.query(2)]
        out=c.run_commands(rows)
        self.assertTrue(out['decisions'][0]['allow_advance'])
        self.assertEqual(judge.findings(rows,out),[])

    def test_correlated_disagreement_is_not_two_senses(self):
        rows=[s.observe('depth',0,0),s.observe('rgb',1,1),s.query(1)]
        out=c.run_commands(rows)
        self.assertFalse(out['decisions'][0]['attend'])
        self.assertFalse(out['decisions'][0]['allow_advance'])
        self.assertEqual(judge.findings(rows,out),[])

    def test_auditor_detects_tampering_from_green(self):
        from echoai.nexus0.fusion1 import bench
        cases=s.generate(20261701,1)
        outputs=[c.run_commands(x['commands']) for x in cases]
        report=bench.seal(dict(cases=cases,outputs=outputs,assessment=bench.assess(cases,outputs)))
        self.assertTrue(bench.audit_stage(report,cases)['evidence_valid'])
        changes=bench.mutations(report,cases)
        self.assertEqual(len(changes),7)
        self.assertTrue(all(x['caught'] for x in changes))

    def test_judge_detects_wrong_output_even_if_label_says_green(self):
        from echoai.nexus0.fusion1 import bench
        cases=s.generate(20261701,1)
        outputs=[c.run_commands(x['commands']) for x in cases]
        outputs[0]['decisions'][0]['allow_advance']=False
        report=bench.seal(dict(cases=cases,outputs=outputs,assessment=dict(passed=True)))
        self.assertFalse(bench.audit_stage(report,cases)['evidence_valid'])


if __name__=='__main__':unittest.main()
