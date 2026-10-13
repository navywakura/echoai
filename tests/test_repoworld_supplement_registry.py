import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.pcworld.receipts import canonical
from echoai.repoworld.study import load_registry, prepare_entry
from echoai.repoworld.checks import catalog_for
from echoai.repoworld.types import PublicTask

class SupplementRegistryTests(unittest.TestCase):
    def test_version_two_admits_only_pinned_supplement_descriptors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);sample=p/'sample.json'
            task={'instance_id':'psf__requests-1','repo':'psf/requests','base_commit':'a'*40,'problem_statement':'public'}
            sample.write_text('{}');registry=p/'registry.json'
            descriptor={'directory':'generated','manifest':'manifest.json','manifest_sha256':'b'*64}
            entry={'instance_id':task['instance_id'],'source':'source','runtime':'runtime','check_plan':catalog_for(task['repo']),'supplement':descriptor}
            data={'schema':'repoworld.environment-registry.v2','dataset':'dataset.parquet','entries':[entry]}
            contract={'dataset':{'parquet_sha256':'c'*64}}
            with patch('echoai.repoworld.study.read_fixed_dataset',return_value=[task]),patch('echoai.repoworld.study.sample_roster',return_value=[task]):
                registry.write_text(json.dumps(data));_,entries,_=load_registry(registry,contract,sample)
                self.assertEqual(entries[task['instance_id']]['supplement'],descriptor)
                for bad in ({**descriptor,'manifest_sha256':'bad'},{'directory':'generated'}, {**descriptor,'extra':1}):
                    entry['supplement']=bad;registry.write_text(json.dumps(data))
                    with self.assertRaises(ValueError):load_registry(registry,contract,sample)
                entry['supplement']=descriptor;data['schema']='repoworld.environment-registry.v1';registry.write_text(json.dumps(data))
                with self.assertRaises(ValueError):load_registry(registry,contract,sample)

    def test_supplement_hash_checked_before_source_or_runtime_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);manifest=p/'supplement.json';manifest.write_text('{}')
            entry={'source':'source','runtime':'runtime','supplement':{
                'directory':str(p/'generated'),'manifest':str(manifest),'manifest_sha256':'0'*64}}
            with patch('echoai.repoworld.study.load_image',side_effect=AssertionError('must reject tampered manifest first')):
                with self.assertRaisesRegex(ValueError,'supplement'):
                    prepare_entry(PublicTask('fixture-1','fixture/repo','a'*40,'public'),entry,p/'out')
