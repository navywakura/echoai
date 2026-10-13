"""Public service infrastructure only; never load the benchmark dataset."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from .repoworld_support import ROOT
from echoai.repoworld import official_curator as curator


IMAGE = 'swebench/sweb.eval.x86_64.psf_1776_requests-2148:latest'


class ServiceManifestTests(unittest.TestCase):
    def test_run_lock_can_pin_service_without_requiring_one_for_other_repos(self):
        import jsonschema
        schema=json.loads((ROOT/'ECHO-5.1/docs/swebench/SWE-RUN-LOCK.schema.json').read_bytes())['properties']['instances']['items']
        row=dict(instance_id='psf__requests-2148',base_commit='a'*40,
            online_rootfs_sha256='b'*64,online_tree_sha256='c'*64,public_checks_sha256='d'*64,
            official_image_digest='sha256:'+'e'*64,official_eval_script_sha256='f'*64,
            sealed_tests_sha256='1'*64,empty_patch_resolved=False,gold_patch_resolved=True,preflight_valid=True)
        validator=jsonschema.Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(row))
        self.assertTrue(validator.is_valid({**row,'service_manifest_sha256':'2'*64}),
                        'Service provenance cannot cross the sealed lock')
        self.assertFalse(validator.is_valid({**row,'service_manifest_sha256':'not-a-digest'}))

    def test_final_evaluation_rejects_missing_or_changed_preflight_service(self):
        self.assertTrue(callable(getattr(curator, 'validate_service_lock', None)),
                        'Final evaluation does not bind the preflight service')
        profile={'manifest_sha256':'a'*64}
        for lock in ({}, {'service_manifest_sha256':'b'*64}):
            with self.assertRaises(ValueError):curator.validate_service_lock(profile,lock)
        curator.validate_service_lock(profile,{'service_manifest_sha256':'a'*64})
        with self.assertRaises(ValueError):
            curator.validate_service_lock(None,{'service_manifest_sha256':'a'*64})
        curator.validate_service_lock(None,{})

    def test_requests_requires_pinned_service_and_other_repos_do_not(self):
        self.assertTrue(callable(getattr(curator, 'httpbin_profile', None)),
                        'Requests has no offline service boundary')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'service'):
                curator.httpbin_profile(IMAGE)
            self.assertIsNone(curator.httpbin_profile('swebench/sweb.eval.x86_64.sympy_1776_sympy-19007:latest'))

    def test_tampered_service_is_rejected_before_container_creation(self):
        self.assertTrue(callable(getattr(curator, 'httpbin_profile', None)),
                        'Service bytes are not checked')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'lib/httpbin').mkdir(parents=True)
            for name in ('dependency.py','ca.pem','key.pem','trust.pem','lib/httpbin/core.py'):
                (bundle/name).write_text('public dependency\n')
            manifest = root / 'services.json'
            manifest.write_text(json.dumps(dict(
                schema='repoworld.curator-httpbin.v1', bundle=str(bundle),
                image=IMAGE, image_digest='sha256:' + 'a' * 64,
                trust_store=curator.SERVICE_TRUST,off_host_redirect_alias='www.google.co.uk',
                files={name:hashlib.sha256(b'public dependency\n').hexdigest()
                       for name in ('dependency.py','ca.pem','key.pem','trust.pem','lib/httpbin/core.py')})))
            digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
            with patch.dict(os.environ, {
                'REPOWORLD_CURATOR_SERVICES': str(manifest),
                'REPOWORLD_CURATOR_SERVICES_SHA256': digest,
            }):
                self.assertIsNotNone(curator.httpbin_profile(IMAGE))
                (bundle / 'dependency.py').write_text('changed\n')
                with self.assertRaisesRegex(ValueError, 'service'):
                    curator.httpbin_profile(IMAGE)


@unittest.skipUnless(os.environ.get('REPOWORLD_CURATOR_INTEGRATION')=='1'
                     and os.environ.get('REPOWORLD_CURATOR_SERVICES'),
                     'requires explicit curator integration flag, bundle and Docker SDK')
class LoopbackServiceTests(unittest.TestCase):
    def test_real_httpbin_http_tls_semantics_and_network_isolation(self):
        """Fails if startup, TLS trust, upstream routes or isolation are missing."""
        import docker
        curator.restrict_containers()
        client = docker.from_env()
        container = client.containers.create(IMAGE, command='sleep 90', detach=True)
        try:
            container.start()
            container.reload()
            self.assertEqual(container.attrs['HostConfig']['NetworkMode'], 'none')
            probe = r'''
import gzip, json, socket, ssl, urllib.request, urllib.error
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile='/opt/repoworld-httpbin/ca.pem')))
def get(path, data=None, headers=None):
    return opener.open(urllib.request.Request(path, data=data, headers=headers or {}), timeout=10)
for scheme in ('http', 'https'):
    with get(scheme+'://httpbin.org/get?fixture=public') as response:
        assert json.load(response)['args'] == {'fixture':'public'}
with get('http://httpbin.org/post', b'fixture=public') as response:
    assert json.load(response)['form'] == {'fixture':'public'}
with get('http://httpbin.org/redirect/2') as response:
    assert response.geturl() == 'http://httpbin.org/get'
try: get('http://httpbin.org/status/418')
except urllib.error.HTTPError as error: assert error.code == 418
else: raise AssertionError('status endpoint fabricated success')
try: get('http://httpbin.org/basic-auth/user/pass')
except urllib.error.HTTPError as error: assert error.code == 401
else: raise AssertionError('authentication bypassed')
with get('http://httpbin.org/basic-auth/user/pass', headers={'Authorization':'Basic dXNlcjpwYXNz'}) as response:
    assert json.load(response)['authenticated'] is True
with get('http://httpbin.org/gzip') as response:
    assert json.loads(gzip.decompress(response.read()))['gzipped'] is True
assert {r[4][0] for r in socket.getaddrinfo('httpbin.org', 80)} == {'127.0.0.1'}
assert not any(line.split()[1]=='00000000' for line in open('/proc/net/route').readlines()[1:])
sock=socket.socket();sock.settimeout(.2)
try: sock.connect(('192.0.2.1',80))
except OSError: pass
else: raise AssertionError('external network reachable')
print('public-service-verified')
'''
            result = container.exec_run(['/opt/miniconda3/envs/testbed/bin/python', '-I', '-c', probe])
            self.assertEqual(result.exit_code, 0, result.output.decode(errors='replace'))
            self.assertIn(b'public-service-verified', result.output)
            # Public BASE also uses Session.send, which bypasses CA env vars,
            # and a second hostname to exercise off-host authentication removal.
            legacy_probe = r'''
import requests
session=requests.Session()
response=session.send(requests.Request('GET','https://httpbin.org/get').prepare())
assert response.status_code==200
response=requests.get('http://httpbin.org/redirect-to',
    params={'url':'http://www.google.co.uk'},auth=('user','pass'))
assert response.history[0].request.headers['Authorization']
assert not response.request.headers.get('Authorization')
try: requests.get('https://127.0.0.1/get')
except requests.exceptions.SSLError: pass
else: raise AssertionError('TLS hostname verification disabled')
print('public-legacy-client-verified')
'''
            result=container.exec_run([curator.SERVICE_PYTHON,'-c',legacy_probe],workdir='/testbed')
            self.assertEqual(result.exit_code,0,result.output.decode(errors='replace'))
            self.assertIn(b'public-legacy-client-verified',result.output)
        finally:
            container.remove(force=True)
            client.close()
