"""Category eligibility and unbiased fixed ordering, independently of oracles."""
import unittest
from echoai.pcworld import adversarial as a


def task(family,variant=0):
    return {'id':f'repair-v2-{family}-{variant:02d}', 'property':'repair.'+family,
            'probe_catalog':'expanded-v1','probe_order_seed':20261013}


class ExpandedPool(unittest.TestCase):
    def test_expanded_repair_and_replay_pass_the_probe_audit(self):
        import tempfile
        from pathlib import Path
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.repairs import repair_tasks
        from echoai.pcworld.tasks import FixtureProvider
        class RepairingCritic(FixtureProvider):
            def call(self,role,t,context,**kwargs):
                usage={'tokens':0,'llm_calls':0,'fixture_calls':1}
                if role=='propose':
                    code=t['initial']
                    if context.get('repair_feedback'):
                        code="import json,sys\nx=json.load(sys.stdin)\nr=[]\nseen=set()\nfor row in x:\n if row['id'] not in seen: r.append(row); seen.add(row['id'])\nprint(json.dumps(r))\n"
                    return {'content':code},usage
                if role=='critic':
                    rows=[{'id':'q','value':1},{'id':'z','value':2},{'id':'q','value':3}]
                    values={'duplicate-keys':rows,'first-occurrence-order':rows,
                            'empty-singleton':[],'unique-keys':rows[:2],
                            'extreme-values':[{'id':'v','value':10000}]}
                    return {'claim_id':t['property'],'input':values[context['probe']['category']],
                            'oracle_reference':t['checker'],'preconditions':t['preconditions']},usage
                return super().call(role,t,context,**kwargs)
        t=dict(repair_tasks()[1],**task('records'))
        for arm in ('E','F'):
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as d:
                ep=Episode(Path(d)/'run',t,arm,RepairingCritic());result=ep.run()
                self.assertIsNone(result['error'])
                if arm=='E':self.assertTrue(result['development_accepted'])
                self.assertEqual(a.audit_probe_records(t,arm,ep.receipts.records,
                    lambda sid:ep.store.read(ep.store.get(sid),'solution.py').decode()),[])

    def test_probe_audit_rejects_valid_but_wrong_fixed_order_and_retry_overflow(self):
        t=task('records');order=a.fixed_order(t)
        def record(category,attempt):
            return {'body':{'role':'critic','snapshot':'s','probe':{'category':category,'attempt':attempt}}}
        self.assertEqual(a.audit_probe_records(t,'F',[record(order[0],0)],lambda s:'result=None'),[])
        self.assertTrue(a.audit_probe_records(t,'F',[record(order[1],0)],lambda s:'result=None'))
        self.assertTrue(a.audit_probe_records(t,'F',[record(order[0],n) for n in range(4)],lambda s:'result=None'))

    def test_probe_audit_rejects_mislabeled_or_unwitnessed_coverage(self):
        t=task('records')
        prop={'snapshot':'s','input':[],'status':'supported'}
        t['public_inputs']=[]
        # Test result anchoring without checking routing here: prior probe
        # metadata must exist even when the category already has a property.
        valid=[{'body':{'kind':'property','property':prop}},
               {'body':dict(prop,operation='probe_result',category='empty-singleton')}]
        self.assertTrue(a.audit_probe_records(t,'E',valid,lambda s:'result=None'))
        valid.insert(0,{'body':{'role':'critic','snapshot':'s','probe':{'category':'empty-singleton','attempt':0},
                             'payload':{'claim_id':'repair.records','input':[],
                                        'oracle_reference':'pcworld-repair-reference-1',
                                        'preconditions':['repair-records-domain-v1']}}})
        # Find a neutral identity whose predetermined first category matches,
        # only for this audit fixture, never for pilot/control seed selection.
        for n in range(100):
            t['id']='audit-fixture-'+str(n)
            if a.fixed_order(t)[0]=='empty-singleton':break
        self.assertEqual(a.audit_probe_records(t,'E',valid,lambda s:'result=None'),[])
        self.assertTrue(a.audit_probe_records(t,'E',valid[2:],lambda s:'result=None'))
        valid[2]['body']['category']='duplicate-keys'
        self.assertTrue(a.audit_probe_records(t,'E',valid,lambda s:'result=None'))

    def test_invalid_probe_exhaustion_advances_both_arms_in_real_episode(self):
        import tempfile
        from pathlib import Path
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.repairs import repair_tasks
        from echoai.pcworld.tasks import FixtureProvider
        class InvalidCritic(FixtureProvider):
            def __init__(self):self.categories=[]
            def call(self,role,t,context,**kwargs):
                usage={'tokens':0,'llm_calls':0,'fixture_calls':1}
                if role=='propose':return {'content':t['initial']},usage
                if role=='critic':
                    self.categories.append(context['probe']['category'])
                    return {'claim_id':t['property'],'input':None},usage
                return super().call(role,t,context,**kwargs)
        t=dict(repair_tasks()[1],**task('records'))
        t['initial']='import json,sys\nx=json.load(sys.stdin)\nprint(json.dumps(x))\n'
        expected=[c for c in a.fixed_order(t)[:2] for _ in range(3)]
        for arm in ('F','E'):
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as d:
                provider=InvalidCritic();ep=Episode(Path(d)/'run',t,arm,provider)
                result=ep.run()
                self.assertIsNone(result['error'])
                self.assertEqual(provider.categories,expected)
                self.assertEqual(result['budget']['used']['critic_calls'],6)
                self.assertFalse(result['development_accepted'])
                self.assertEqual(a.audit_probe_records(t,arm,ep.receipts.records,
                    lambda sid:ep.store.read(ep.store.get(sid),'solution.py').decode()),[])

    def test_each_family_has_five_distinct_categories_without_changing_legacy(self):
        for family,legacy in a.ATTACKS.items():
            self.assertEqual(len(legacy),3)
            self.assertEqual(len(set(a.categories_for(task(family)))),5)

    def test_new_categories_have_valid_witnesses_and_reject_mislabeled_inputs(self):
        examples=[
            ('intervals','disjoint-intervals',[[0,1],[3,4]],[[0,3],[1,4]]),
            ('intervals','extreme-endpoints',[[-10000,0]],[[0,1]]),
            ('records','unique-keys',[{'id':'a','value':1},{'id':'b','value':2}],
             [{'id':'a','value':1},{'id':'a','value':2}]),
            ('records','extreme-values',[{'id':'a','value':10000}],[{'id':'a','value':2}]),
            ('path','plain-components','/alpha/beta','/a/../b'),
            ('path','root-only','/','/a'),
            ('csv','single-field','hello','hello,world'),
            ('csv','empty-fields','a,,b','a,b'),
            ('pagination','in-range',{'items':[1,2,3],'offset':1,'limit':1},
             {'items':[1,2],'offset':-1,'limit':1}),
            ('pagination','extreme-items',{'items':[-10000],'offset':0,'limit':1},
             {'items':[1],'offset':0,'limit':1}),
            ('dependencies','linear-chain',{'nodes':['c','b','a'],'edges':[['c','b'],['b','a']]},
             {'nodes':['a','b'],'edges':[['a','b'],['b','a']]}),
            ('dependencies','edgeless',{'nodes':['a','b'],'edges':[]},
             {'nodes':['a','b'],'edges':[['a','b']]})]
        for family,category,valid,wrong in examples:
            with self.subTest(category=category):
                self.assertTrue(a.matches_category(task(family),category,valid))
                self.assertFalse(a.matches_category(task(family),category,wrong))
                self.assertFalse(a.matches_category(task(family),category,None))
                self.assertIn(category,a.critic_instructions(task(family),category))
                self.assertFalse(a.matches_category({'property':'repair.'+family},category,valid))

    def test_fixed_order_is_complete_repeatable_and_independent_of_source_or_hidden_labels(self):
        for family in a.ATTACKS:
            t=task(family);seen=[]
            for _ in range(5):
                category=a.choose_category('F',t,'result={row["id"]:row for row in x}',seen)
                self.assertEqual(category,a.choose_category('F',dict(t,development_inputs=['SECRET']),
                                                            '# unrelated code',seen))
                self.assertNotIn(category,seen);seen.append(category)
            self.assertEqual(set(seen),set(a.categories_for(t)))
            self.assertIsNone(a.choose_category('F',t,'',seen))
            self.assertEqual(tuple(seen),a.fixed_order(t))

    def test_invalid_catalog_and_order_seed_fail_closed(self):
        for overrides in ({'probe_catalog':'unknown'},{'probe_order_seed':True},
                          {'probe_order_seed':-1}):
            with self.assertRaises(ValueError):a.fixed_order(dict(task('records'),**overrides))

    def test_ast_cues_ignore_comment_strings_and_accept_renamed_record_variables(self):
        t=task('records')
        self.assertEqual(a.source_risks(t,'result = {entry["id"]: entry for entry in items}'),
                         ('duplicate-keys',))
        self.assertEqual(a.source_risks(t,'# {p["id"]:p}\nnote="DictComp"\nresult=[]'),())
        self.assertEqual(a.choose_category('E',t,'result={v["id"]:v for v in data}',()),'duplicate-keys')
        self.assertEqual(a.source_risks(t,'invalid python !'),())

    def test_no_signal_echo_uses_same_fixed_order_and_never_repeats_seen_categories(self):
        for family in a.ATTACKS:
            t=task(family);order=a.fixed_order(t)
            for i in range(6):
                expected=order[i] if i<5 else None
                self.assertEqual(a.choose_category('E',t,'result=None',order[:i]),expected)

    def test_source_cues_cover_each_family_and_never_consult_final_inputs(self):
        examples={'intervals':('ok=a < b','touching-endpoints'),
                  'path':("result=x.split('/')",'dotdot-cancellation'),
                  'csv':("result=x.split(',')",'quoted-delimiter'),
                  'pagination':("result=x['items'][x['offset']:x['limit']]",'negative-bounds'),
                  'dependencies':("result=sorted(x['nodes'])",'self-and-multinode-cycles')}
        for family,(source,risk) in examples.items():
            self.assertIn(risk,a.source_risks(dict(task(family),development_inputs=['SECRET']),source))
