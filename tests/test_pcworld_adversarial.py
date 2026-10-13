import unittest


class AdversarialRouting(unittest.TestCase):
    def test_echo_routes_csv_split_candidate_to_unquoted_delimiter_case(self):
        from echoai.pcworld.adversarial import choose_category
        task={'property':'repair.csv'}
        source="result=x.strip().split(',')"
        self.assertEqual(choose_category('E',task,source,()),'quoted-delimiter')

    def test_echo_uses_record_key_collision_when_candidate_builds_a_dict(self):
        from echoai.pcworld.adversarial import choose_category
        task={'property':'repair.records'}
        source="result=list({p['id']:p for p in x}.values())"
        self.assertEqual(choose_category('E',task,source,()),'duplicate-keys')

    def test_probe_category_is_checked_against_the_actual_input(self):
        from echoai.pcworld.adversarial import matches_category
        task={'property':'repair.records'}
        self.assertTrue(matches_category(task,'duplicate-keys',[
            {'id':'a','value':1},{'id':'a','value':2}]))
        self.assertFalse(matches_category(task,'duplicate-keys',[
            {'id':'a','value':1},{'id':'b','value':2}]))
        path={'property':'repair.path'}
        self.assertTrue(matches_category(path,'dotdot-cancellation','/a/../b'))
        self.assertFalse(matches_category(path,'dotdot-cancellation','/a/b'))

    def test_echo_does_not_repeat_a_probe_category_already_in_cam_history(self):
        from echoai.pcworld.adversarial import choose_category
        task={'property':'repair.path'}
        source="result='/'+'/'.join(p for p in x.split('/') if p and p!='.')"
        self.assertEqual(choose_category('E',task,source,('dotdot-cancellation',)),
                         'root-boundary')

    def test_fixed_critic_uses_preregistered_order_independent_of_candidate(self):
        from echoai.pcworld.adversarial import choose_category
        task={'property':'repair.dependencies'}
        simple="result=sorted(x['nodes'])"
        complex_source="def dfs(n): return dfs(n)"
        self.assertEqual(choose_category('F',task,simple,()),'disconnected-lex-order')
        self.assertEqual(choose_category('F',task,complex_source,()),'disconnected-lex-order')
        self.assertEqual(choose_category('E',task,simple,()),'self-and-multinode-cycles')

    def test_holdout_variants_are_seeded_valid_and_distinct_from_public_examples(self):
        from echoai.pcworld.repairs import repair_task_variants,repair_domain
        first=repair_task_variants(12,seed=41)
        self.assertEqual(first,repair_task_variants(12,seed=41))
        self.assertEqual(len(first),12)
        self.assertEqual(len({t['id'] for t in first}),12)
        for task in first:
            self.assertTrue(task['id'].startswith('repair-v2-'))
            self.assertTrue(all(repair_domain(task['property'],x)
                                for x in task['public_inputs']+task['development_inputs']))
            self.assertTrue(set(map(repr,task['public_inputs'])).isdisjoint(
                            set(map(repr,task['development_inputs']))))
            for category in __import__('echoai.pcworld.adversarial',fromlist=['ATTACKS']).ATTACKS[task['family']]:
                self.assertTrue(any(__import__('echoai.pcworld.adversarial',fromlist=['matches_category'])
                                    .matches_category(task,category,value)
                                    for value in task['development_inputs']),
                                (task['id'],category))

    def test_critic_prompt_requires_valid_distinct_case_and_recovers_schema_error(self):
        from echoai.pcworld.adversarial import critic_instructions
        task={'property':'repair.path','description':'Normalize an absolute path'}
        prompt=critic_instructions(task,'dotdot-cancellation',
                                   seen_inputs=['/ok/path'],
                                   rejection='INPUT_OUT_OF_DOMAIN: expected an absolute path string')
        self.assertIn('/dotdot-cancellation',prompt)
        self.assertIn('Do not repeat',prompt)
        self.assertIn('INPUT_OUT_OF_DOMAIN',prompt)
        self.assertIn('Do not copy the task description into input',prompt)

    def test_out_of_domain_critic_input_gets_feedback_and_retries_before_evidence(self):
        import tempfile
        from pathlib import Path
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider

        class OODOnce(FixtureProvider):
            def __init__(self): self.probes=[]
            def call(self,role,task,context,**kw):
                if role=='critic':
                    self.probes.append(context.get('probe',{}))
                    if len(self.probes)==1:
                        return {'claim_id':task['property'],'input':task['description'],
                                'oracle_reference':task['checker'],'preconditions':task['preconditions']}, \
                               {'tokens':0,'llm_calls':0,'fixture_calls':1}
                    return {'claim_id':task['property'],'input':[{'id':'b','value':2},{'id':'b','value':3}],
                            'oracle_reference':task['checker'],'preconditions':task['preconditions']}, \
                           {'tokens':0,'llm_calls':0,'fixture_calls':1}
                return super().call(role,task,context,**kw)

        from echoai.pcworld.repairs import repair_tasks
        with tempfile.TemporaryDirectory() as d:
            provider=OODOnce();episode=Episode(Path(d)/'run',repair_tasks()[1],'E',provider)
            result=episode._probe(episode.base,'duplicate-keys')
            self.assertEqual(result['status'],'contradicted')
            self.assertEqual(len(provider.probes),2)
            self.assertIn('INPUT_OUT_OF_DOMAIN',provider.probes[1]['rejection'])
            self.assertEqual(episode.counterexamples,[ [{'id':'b','value':2},{'id':'b','value':3}] ])
            self.assertGreater(episode.memory.lookup_work,0)
            self.assertGreater(episode.budget.report()['used']['tools'],0)

    def test_fixed_critic_requires_two_distinct_valid_probe_categories_before_acceptance(self):
        import tempfile
        from pathlib import Path
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider
        from echoai.pcworld.repairs import repair_tasks

        class PassingCritic(FixtureProvider):
            def __init__(self): self.categories=[]
            def call(self,role,task,context,**kw):
                if role=='propose':
                    fixed="import json,sys\nx=json.load(sys.stdin)\nresult=[]\nseen=set()\nfor row in x:\n if row['id'] not in seen: seen.add(row['id']); result.append(row)\nprint(json.dumps(result))\n"
                    return {'content':fixed},{'tokens':0,'llm_calls':0,'fixture_calls':1}
                if role=='critic':
                    self.categories.append(context['probe']['category'])
                    value=([] if len(self.categories)==1 else
                           [{'id':'b','value':2},{'id':'a','value':1},{'id':'b','value':3}])
                    return {'claim_id':task['property'],'input':value,
                            'oracle_reference':task['checker'],'preconditions':task['preconditions']}, \
                           {'tokens':0,'llm_calls':0,'fixture_calls':1}
                return super().call(role,task,context,**kw)

        with tempfile.TemporaryDirectory() as d:
            provider=PassingCritic();episode=Episode(Path(d)/'run',repair_tasks()[1],'F',provider)
            result=episode.run()
            self.assertEqual(len(provider.categories),2)
            self.assertEqual(len(set(provider.categories)),2)
            self.assertEqual(result['probe_categories'],provider.categories)
            self.assertTrue(result['development_accepted'])

    def test_critic_arm_cannot_accept_incorrect_code_regardless_of_coverage(self):
        import tempfile
        from pathlib import Path
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.repairs import repair_tasks
        from echoai.pcworld.tasks import FixtureProvider
        task=repair_tasks()[0]
        with tempfile.TemporaryDirectory() as d:
            episode=Episode(Path(d)/'run',task,'E',FixtureProvider())
            fixed="import json,sys\nx=json.load(sys.stdin)\nresult=[]\nfor lo,hi in sorted(x):\n if result and lo <= result[-1][1]: result[-1][1]=hi\n else: result.append([lo,hi])\nprint(json.dumps(result))\n"
            candidate=episode.apply_content(episode.base,fixed)
            result=episode.finish(candidate)
            self.assertFalse(result['development_accepted'])
            self.assertEqual(result['probe_categories'],[])


class EmptyCategoryInstructions(unittest.TestCase):
    def test_records_empty_or_singleton_uses_actual_contract_fields(self):
        from echoai.pcworld.adversarial import critic_instructions
        text=critic_instructions({'property':'repair.records'},'empty-singleton')
        self.assertIn('exactly zero or one',text)
        self.assertIn('[]',text)
        self.assertIn('"value": 1',text)
        self.assertNotIn('"val":',text)
