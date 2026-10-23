"""Public reporting fixtures only; no benchmark dataset or protected tests."""
import hashlib
import json
import os
import unittest

from .repoworld_support import ROOT
from echoai.repoworld import official_curator as curator

IMAGE='swebench/sweb.eval.x86_64.pytest-dev_1776_pytest-7168:latest'


class ReportingProfileTests(unittest.TestCase):
    def test_profile_is_fixed_to_runtime_and_rendering_only(self):
        self.assertTrue(callable(getattr(curator,'pytest_reporting_profile',None)))
        profile=curator.pytest_reporting_profile(IMAGE)
        digest=profile.pop('sha256')
        self.assertEqual(profile['environment'],{'PYTEST_ADDOPTS':'--tb=no'})
        self.assertEqual(profile['image'],IMAGE)
        self.assertEqual(profile['image_digest'],'sha256:fa2614449afb464c272c3bd0c5ebc66d7cd6a046b4a98ac65ee1b0df2594a9ff')
        self.assertEqual(digest,hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':')).encode()).hexdigest())
        self.assertIsNone(curator.pytest_reporting_profile('swebench/sweb.eval.x86_64.sympy_1776_sympy-19007:latest'))

    def test_final_rejects_missing_changed_or_unexpected_reporting_profile(self):
        self.assertTrue(callable(getattr(curator,'validate_reporting_lock',None)))
        profile=curator.pytest_reporting_profile(IMAGE)
        for lock in ({},{'reporting_profile_sha256':'0'*64}):
            with self.assertRaises(ValueError):curator.validate_reporting_lock(profile,lock)
        curator.validate_reporting_lock(profile,{'reporting_profile_sha256':profile['sha256']})
        with self.assertRaises(ValueError):
            curator.validate_reporting_lock(None,{'reporting_profile_sha256':profile['sha256']})
        curator.validate_reporting_lock(None,{})

    def test_lock_schema_accepts_only_well_formed_optional_reporting_digest(self):
        import jsonschema
        item=json.loads((ROOT/'repository/docs/swebench/SWE-RUN-LOCK.schema.json').read_bytes())['properties']['instances']['items']
        row=dict(instance_id='pytest-dev__pytest-7168',base_commit='a'*40,
            online_rootfs_sha256='b'*64,online_tree_sha256='c'*64,public_checks_sha256='d'*64,
            official_image_digest='sha256:'+'e'*64,official_eval_script_sha256='f'*64,
            sealed_tests_sha256='1'*64,empty_patch_resolved=False,gold_patch_resolved=True,preflight_valid=True)
        validator=jsonschema.Draft202012Validator(item)
        self.assertTrue(validator.is_valid(row))
        self.assertTrue(validator.is_valid({**row,'reporting_profile_sha256':'2'*64}))
        self.assertFalse(validator.is_valid({**row,'reporting_profile_sha256':'invalid'}))


@unittest.skipUnless(os.environ.get('REPOWORLD_CURATOR_INTEGRATION')=='1',
                     'requires explicit curator integration flag and Docker SDK')
class RealReportingProfileTests(unittest.TestCase):
    def test_reporting_crash_becomes_an_explicit_failure_without_masking_it(self):
        import docker
        curator.restrict_containers()
        client=docker.from_env()
        container=client.containers.create(IMAGE,command='sleep 120',detach=True,
                                         environment={'PYTEST_ADDOPTS':'--maxfail=1'})
        try:
            container.start();container.reload()
            self.assertEqual(container.attrs['HostConfig']['NetworkMode'],'none')
            probe=r'''
import os, pathlib, subprocess, sys, tempfile
assert os.environ['PYTEST_ADDOPTS']=='--tb=no'
source="""class PublicProbe:
    @property
    def __class__(self):
        raise RuntimeError
    def __repr__(self):
        raise RuntimeError
def test_public_failure():
    value=PublicProbe()
    assert value == 1
def test_ordinary_failure():
    assert 1 == 2
def test_public_success():
    assert 1 == 1
"""
with tempfile.TemporaryDirectory() as folder:
    pathlib.Path(folder,'test_public.py').write_text(source)
    env=dict(os.environ);env.pop('PYTEST_ADDOPTS',None)
    baseline=subprocess.run([sys.executable,'-m','pytest','-rA','test_public.py'],cwd=folder,
        env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    assert baseline.returncode==3 and b'INTERNALERROR' in baseline.stdout
    rendered=subprocess.run([sys.executable,'-m','pytest','-rA','test_public.py'],cwd=folder,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    assert rendered.returncode==1 and b'INTERNALERROR' not in rendered.stdout
    lines=rendered.stdout.decode().splitlines()
    for name in ('test_public_failure','test_ordinary_failure'):
        assert any(line.startswith('FAILED test_public.py::'+name) for line in lines)
    assert any(line.startswith('PASSED test_public.py::test_public_success') for line in lines)
print('public-reporting-profile-verified')
'''
            result=container.exec_run([curator.SERVICE_PYTHON,'-c',probe],workdir='/testbed')
            self.assertEqual(result.exit_code,0,result.output.decode(errors='replace'))
            self.assertIn(b'public-reporting-profile-verified',result.output)
        finally:
            container.remove(force=True);client.close()
