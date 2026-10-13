"""Probe content, category semantics and historical-profile regressions."""
import json
import unittest
from unittest.mock import patch
from echoai.pcworld import adversarial as a
from echoai.pcworld.provider import HTTPProvider
from echoai.pcworld.repairs import repair_tasks, repair_domain
from tests.test_pcworld_provider import CONFIG


def graph_task():
    return dict(repair_tasks()[5], id='repair-v2-dependencies-00',
                probe_catalog='expanded-v2', probe_order_seed=20261013)


class ProbeContent(unittest.TestCase):
    def test_csv_example_is_data_not_description_for_critic_and_self_review(self):
        task=repair_tasks()[3]
        for role in ('critic','self_review'):
            provider=HTTPProvider(CONFIG);sent=[]
            def post(endpoint,payload,**kwargs):
                sent.append(payload)
                if endpoint.endswith('/tokenize'):return {'count':500}
                return {'model':'test-model','usage':{'prompt_tokens':500,'completion_tokens':10,'total_tokens':510},
                        'choices':[{'message':{'content':'{"abstention":"NO_COUNTEREXAMPLE_FOUND"}'}}]}
            with patch.object(provider,'_post',side_effect=post):
                provider.call(role,task,{},total_token_budget=1000)
            prompt=json.loads(sent[0]['messages'][1]['content'])
            self.assertNotEqual(prompt['format']['input'],task['input_schema'])
            self.assertTrue(repair_domain('repair.csv',prompt['format']['input']))
            self.assertEqual(prompt['input_json_schema'],task['input_json_schema'])
            self.assertIn('one CSV record',prompt['input_instructions'])
            self.assertNotIn('development_inputs',prompt)
            self.assertEqual(sent[0]['messages'],sent[1]['messages'])

    def test_both_arms_share_six_dependency_categories_and_keep_old_five(self):
        task=graph_task();cat='reverse-alphabetical-edges'
        self.assertIn(cat,a.categories_for(task))
        self.assertEqual(len(a.categories_for(task)),6)
        self.assertEqual(set(a.fixed_order(task)),set(a.categories_for(task)))
        old=dict(task,probe_catalog='expanded-v1')
        self.assertEqual(len(a.categories_for(old)),5)
        self.assertNotIn(cat,a.categories_for(old))
        self.assertEqual(a.choose_category('F',task,'sorted(x)',[]),a.fixed_order(task)[0])
        self.assertEqual(a.choose_category('E',task,'pass',[]),a.fixed_order(task)[0])

    def test_reverse_edges_require_in_domain_acyclic_order_conflict(self):
        task=graph_task();cat='reverse-alphabetical-edges'
        valid={'nodes':['a','z'],'edges':[['z','a']]}
        self.assertTrue(a.matches_category(task,cat,valid))
        for invalid in ({'deps':{'a':['z']}}, {'nodes':['a','z'],'edges':[['a','z']]},
                        {'nodes':['a','z'],'edges':[['z','a'],['a','z']]},
                        {'nodes':['a','z'],'edges':[['z','z']]},
                        {'nodes':['a','z'],'edges':[]}):
            self.assertFalse(a.matches_category(task,cat,invalid))
        self.assertTrue(a.matches_category(task,cat,{'nodes':['a','z'],'edges':[['z','a'],['z','a']]}))

    def test_sort_ast_prioritizes_reverse_edges_but_text_does_not(self):
        task=graph_task();cat='reverse-alphabetical-edges'
        for source in ('result=sorted(data)', 'data.sort()', 'sorted(data, reverse=True)'):
            self.assertEqual(a.source_risks(task,source),(cat,))
            self.assertEqual(a.choose_category('E',task,source,[]),cat)
            self.assertNotEqual(a.choose_category('E',task,source,[cat]),cat)
        for source in ('# sorted(data)\npass', 'x="data.sort()"', 'not python!'):
            self.assertEqual(a.source_risks(task,source),())
        old=dict(task,probe_catalog='expanded-v1')
        self.assertEqual(a.source_risks(old,"sorted(x['nodes'])"),('self-and-multinode-cycles',))

    def test_new_profile_audit_does_not_skip_invalid_order(self):
        task=graph_task()
        records=[{'body':{'role':'critic','snapshot':'s',
                         'probe':{'category':'edgeless','attempt':0}}}]
        self.assertTrue(a.audit_probe_records(task,'E',records,lambda s:'sorted(x)'))
        records[0]['body']['probe']['category']='reverse-alphabetical-edges'
        self.assertEqual(a.audit_probe_records(task,'E',records,lambda s:'sorted(x)'),[])
