import dataclasses
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.dataset import public_task, read_fixed_dataset, select_public_tasks, validate_launch


def row():
    return dict(instance_id='org__repo-123', repo='org/repo', base_commit='a'*40,
                problem_statement='Fix the public issue', patch='SECRET_PATCH',
                test_patch='SECRET_TEST', FAIL_TO_PASS='SECRET_F2P',
                PASS_TO_PASS='SECRET_P2P', hints_text='SECRET_HINT',
                new_future_private_field='SECRET_FUTURE')


class DatasetTests(unittest.TestCase):
    def test_exact_allowlist_not_a_denylist(self):
        task = public_task(row())
        self.assertEqual(dataclasses.asdict(task), {k:row()[k] for k in
                         ('instance_id','repo','base_commit','problem_statement')})
        self.assertNotIn('SECRET', repr(task))
        with self.assertRaises(dataclasses.FrozenInstanceError): task.repo = 'elsewhere'

    def test_bad_public_fields(self):
        for key,value in [('base_commit','HEAD'), ('repo','../repo'),
                          ('instance_id','wrong-123'), ('problem_statement',None)]:
            data=row(); data[key]=value
            with self.assertRaises(ValueError): public_task(data)

    def test_fixed_read_rejects_hash_duplicates_and_schema(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'dataset.json'
            path.write_text(json.dumps([row()]))
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(read_fixed_dataset(path,digest),[dataclasses.asdict(public_task(row()))])
            with self.assertRaises(ValueError): read_fixed_dataset(path,'0'*64)
            for data in [[row(),row()],{'rows':[row()]},[{'repo':'missing'}]]:
                path.write_text(json.dumps(data)); digest=hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError): read_fixed_dataset(path,digest)

    def test_roster_and_commit_must_match(self):
        reference={k:row()[k] for k in ('instance_id','repo','base_commit')}
        self.assertEqual(select_public_tasks([row()],[reference]),[public_task(row())])
        with self.assertRaises(ValueError): select_public_tasks([], [reference])
        with self.assertRaises(ValueError): select_public_tasks([row()], [reference,reference])
        reference['base_commit']='b'*40
        with self.assertRaises(ValueError): select_public_tasks([row()],[reference])

    def test_design_contract_and_missing_lock_cannot_launch(self):
        contract=json.loads((ROOT/'ECHO-5.1/docs/SWE-CONTRACT.json').read_text())
        sample=ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json'
        with self.assertRaises(ValueError): validate_launch(contract,sample,None)
        contract.update(status='sealed',launch_enabled=True)
        with self.assertRaises(ValueError): validate_launch(contract,sample,None)
        with self.assertRaises(ValueError): validate_launch(contract,sample,{'schema_version':'wrong'})

    def test_parquet_projection_does_not_load_sealed_columns(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.parquet'; pq.write_table(pa.Table.from_pylist([row()]),p)
            rows=read_fixed_dataset(p,hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(rows,[dataclasses.asdict(public_task(row()))])
            self.assertNotIn('SECRET',json.dumps(rows))
