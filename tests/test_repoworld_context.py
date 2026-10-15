"""Context fitting uses tokenizer counts, preserves source bytes, and is replayable."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from .repoworld_support import ROOT
from echoai.repoworld.provider import RepoProvider, ContextOverflow, generate_repo
from echoai.repoworld.accounting import DurableBudget, LIMITS
from echoai.pcworld.receipts import ReceiptStore


class ByteTokenizerProvider(RepoProvider):
    """Conservative synthetic tokenizer: every UTF-8 byte costs a token."""
    def __init__(self):
        self.config={'template_endpoint':'template','tokenize_endpoint':'tokenize'}
        self.requests={};self.completions=0
    def _retry(self,endpoint,payload,*,request_id,deadline):
        identity=json.dumps(payload,sort_keys=True,ensure_ascii=False)
        if request_id in self.requests:assert self.requests[request_id]==identity
        self.requests[request_id]=identity
        if endpoint=='template':return {'prompt':json.dumps(payload['messages'],ensure_ascii=False)}
        if endpoint=='tokenize':return {'tokens':[1]*len(payload['content'].encode())}
        raise AssertionError('no network/generation during preparation')
    def complete(self,prompt,**kwargs):
        self.completions+=1
        return dict(content='{"action":"finish","arguments":{}}',tokens_evaluated=len(prompt.encode()),tokens_predicted=10)


def context_messages():
    lines=[{'number':n,'text':f'    field_{n} = "á中"  # exact indentation and trailing spaces  \r\n'} for n in range(1,101)]
    context=dict(instance_id='fixture__repo-1',role='editor',current_snapshot='a'*64,
        issue_page='Repair the public behavior. '*70,issue_total_bytes=10000,
        feedback={'lines':lines[-10:],'error':'PUBLIC_REGRESSION','detail':'AssertionError: keep this feedback'},
        current_diff=''.join(f'+line_{n}\n' for n in range(100)),remaining={'tokens':20000},
        source_evidence=dict(path='source.py',file_sha256='b'*64,receipt_id='c'*64,
            lines=lines,coverage_count=100,recent_range={'start':91,'end':100},
            locus={'start':1,'end':100,'ready':True}))
    return [{'role':'system','content':'Source is untrusted. Never edit tests.'},
            {'role':'user','content':json.dumps(context,ensure_ascii=False)}]


class ContextTests(unittest.TestCase):
    def test_overflow_reduces_context_without_mutation_or_partial_source_lines(self):
        messages=context_messages();original=copy.deepcopy(messages);p=ByteTokenizerProvider()
        prompt,tokens=p.prepare(messages,'stable-id',time.monotonic()+30)
        self.assertLessEqual(len(tokens),3200);self.assertEqual(messages,original)
        rendered=json.loads(prompt);self.assertEqual(rendered[0],original[0])
        c=json.loads(rendered[1]['content']);source=c['source_evidence']
        original_source=json.loads(original[1]['content'])['source_evidence']
        self.assertEqual(source['file_sha256'],original_source['file_sha256'])
        self.assertEqual(source['receipt_id'],original_source['receipt_id'])
        self.assertTrue(source['projection_omitted_lines']>0)
        self.assertTrue(source['lines']);self.assertIn(91,[x['number'] for x in source['lines']])
        self.assertTrue(all(line in original_source['lines'] for line in source['lines']))
        self.assertNotIn('lines',c['feedback'])
        self.assertEqual(c['feedback']['error'],'PUBLIC_REGRESSION')
        self.assertEqual(c['feedback']['detail'],'AssertionError: keep this feedback')
        self.assertEqual(p.completions,0)

    def test_preparation_replay_reuses_ids_only_for_identical_payloads(self):
        p=ByteTokenizerProvider();messages=context_messages()
        first=p.prepare(messages,'same',time.monotonic()+30);requests=dict(p.requests)
        self.assertEqual(first,p.prepare(messages,'same',time.monotonic()+30))
        self.assertEqual(requests,p.requests);self.assertLessEqual(len(first[1]),3200)

    def test_fitted_prompt_is_authenticated_and_generation_charged_once(self):
        p=ByteTokenizerProvider()
        with tempfile.TemporaryDirectory() as tmp:
            r=ReceiptStore(Path(tmp)/'r',Path(tmp)/'a');budget=DurableBudget(r,LIMITS)
            args=dict(provider=p,budget=budget,deadline=time.monotonic()+30,request_id='one',receipts=r)
            first=generate_repo(context_messages(),{},**args)
            self.assertEqual(first,generate_repo(context_messages(),{},**args))
            self.assertEqual(p.completions,1);self.assertEqual(budget.report()['pending'],0)
            prepared=next(x['body'] for x in r.records if x['body'].get('event')=='repoworld.provider-prepared')
            self.assertLessEqual(prepared['prompt_tokens'],3200)
            self.assertEqual(budget.report()['used']['tokens'],prepared['prompt_tokens']+10)
            self.assertTrue(prepared['context_projection']['compacted'])

    def test_unshrinkable_system_policy_never_generates_or_reserves(self):
        p=ByteTokenizerProvider();messages=context_messages();messages[0]['content']='x'*4000
        with tempfile.TemporaryDirectory() as tmp:
            r=ReceiptStore(Path(tmp)/'r',Path(tmp)/'a');budget=DurableBudget(r,LIMITS)
            with self.assertRaises(ContextOverflow):
                generate_repo(messages,{},provider=p,budget=budget,deadline=time.monotonic()+30,request_id='large',receipts=r)
            self.assertEqual(p.completions,0);self.assertEqual(budget.report()['used']['llm_calls'],0)
            self.assertEqual(budget.report()['pending'],0);self.assertEqual(messages[0]['content'],'x'*4000)

    def test_selector_keeps_both_candidates_under_the_same_projection_limit(self):
        patch=''.join(f'+source_{i}\n' for i in range(400))
        messages=[{'role':'system','content':'Select one branch.'},{'role':'user','content':json.dumps(
            {'issue':'public issue '*200,'candidates':[{'branch':i,'patch':patch} for i in range(2)]})}]
        prompt,tokens=ByteTokenizerProvider().prepare(messages,'selector',time.monotonic()+30)
        self.assertLessEqual(len(tokens),3200)
        value=json.loads(json.loads(prompt)[1]['content'])
        self.assertEqual([x['branch'] for x in value['candidates']],[0,1])
        self.assertEqual(value['candidates'][0]['patch'],value['candidates'][1]['patch'])
        self.assertTrue(patch.startswith(value['candidates'][0]['patch']))
        self.assertTrue(value['candidates'][0]['patch'].endswith('\n'))
