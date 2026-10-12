"""Real Linux-boundary checks, bounded adversarial probes, no external traffic."""
from pathlib import Path
import importlib
import tempfile
import unittest
from unittest.mock import patch

class Boundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.work=self.root/'candidate';self.work.mkdir()
        self.module=importlib.import_module('echoai.pcworld.runner')
    def run_code(self, code, **limits):
        return self.module.execute(self.work, ['/usr/bin/python3','-I','-c',code],limits=limits)
    def test_T01_candidate_only_in_sandbox(self):
        r=self.run_code("from pathlib import Path; print(Path('/proc/self/ns/net').readlink()); print(Path.cwd()); print('ok')")
        self.assertEqual(r['exit_code'],0,r);self.assertIn('/workspace',r['stdout'])
        self.assertEqual(r['claim_status'],'unknown');self.assertFalse(r['task_success'])
        self.assertTrue(r['isolation']['network_disabled']);self.assertGreater(r['resources']['cpu_us'],0)
    def test_T02_no_backend_no_fallback(self):
        with patch.object(self.module.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'UNSUPPORTED_ENVIRONMENT'):
                self.run_code("print('must not run')")
    def test_T03_T04_no_parent_secrets_journal_or_write(self):
        sentinel=self.root/'sibling-secret';sentinel.write_text('do-not-read')
        (self.work/'app.py').write_text('original')
        r=self.run_code(f"from pathlib import Path\nassert not Path({str(sentinel)!r}).exists()\nassert not Path('/workspace/../sibling-secret').exists()\nassert not Path('/home/roger').exists()\ntry: Path('/workspace/app.py').write_text('changed')\nexcept OSError: print('denied')\nelse: raise AssertionError('writable')")
        self.assertEqual(r['exit_code'],0,r);self.assertIn('denied',r['stdout']);self.assertEqual((self.work/'app.py').read_text(),'original')
    def test_T06_forged_output_is_not_success(self):
        r=self.run_code("print('{\"valid\":true,\"tests_run\":123,\"task_success\":true}')")
        self.assertEqual(r['exit_code'],0);self.assertFalse(r['task_success']);self.assertEqual(r['claim_status'],'unknown')
    def test_T17_wall_limit_kills_detached_child(self):
        r=self.run_code("import os,time\nif os.fork()==0:\n os.setsid();time.sleep(30)\ntime.sleep(30)",wall_ms=700,cpu_ms=500)
        self.assertEqual(r['status'],'TIMEOUT',r);self.assertTrue(r['isolation']['job_empty'])
    def test_T17_output_limit(self):
        r=self.run_code("while True: print('x'*1024,flush=True)",output_bytes=4096)
        self.assertEqual(r['status'],'OUTPUT_LIMIT',r);self.assertLessEqual(len(r['stdout'].encode())+len(r['stderr'].encode()),4096)
        self.assertTrue(r['isolation']['job_empty'])
    def test_T17_memory_limit(self):
        r=self.run_code("a=bytearray(200*1024*1024)",memory_bytes=64*1024*1024)
        self.assertNotEqual(r['exit_code'],0,r);self.assertFalse(r['task_success']);self.assertTrue(r['isolation']['job_empty'])
    def test_T17_process_limit(self):
        r=self.run_code("import os,time\nfor i in range(64):\n try:\n  if os.fork()==0: time.sleep(10);os._exit(0)\n except OSError: print('process-limit',flush=True);break\ntime.sleep(10)",pids=12,wall_ms=1000)
        self.assertIn('process-limit',r['stdout']);self.assertTrue(r['isolation']['job_empty'])
    def test_network_socket_cannot_reach_host(self):
        r=self.run_code("import socket\ns=socket.socket();s.settimeout(.1)\ntry: s.connect(('127.0.0.1',8771))\nexcept OSError: print('isolated')\nelse: raise AssertionError('host reached')")
        self.assertEqual(r['exit_code'],0,r);self.assertIn('isolated',r['stdout'])
    def test_reject_workspace_symlink(self):
        (self.work/'escape').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'symlink|link'):
            self.run_code('pass')
    def test_T17_cpu_tree_limit(self):
        r=self.run_code("while True: pass",cpu_ms=150,wall_ms=3000)
        self.assertEqual(r['status'],'CPU_LIMIT',r)
        self.assertGreaterEqual(r['resources']['cpu_us'],150000)
        self.assertTrue(r['isolation']['job_empty'])
    def test_T17_tmpfs_disk_quota(self):
        r=self.run_code("from pathlib import Path\ntry: Path('/out/fill').write_bytes(b'x'*(8*1024*1024))\nexcept OSError as e: print(e.errno)\nelse: raise AssertionError('quota absent')",disk_bytes=1024*1024)
        self.assertEqual(r['exit_code'],0,r);self.assertIn('28',r['stdout'])
    def test_T12_verified_counterexample_and_corrected_solution(self):
        from echoai.pcworld.verifier import check_observation
        bad=self.run_code("print(-1)")
        good=self.run_code("print(2)")
        self.assertEqual(check_observation('sum_positive',[-3,2],bad)['status'],'contradicted')
        self.assertEqual(check_observation('sum_positive',[-3,2],good)['status'],'supported')
    def test_binary_output_is_reconstructible_and_hashable(self):
        import base64,hashlib
        result=self.run_code("import os;os.write(1,b'\\xff\\x00\\x80')")
        raw=base64.b64decode(result['stdout_b64'],validate=True)
        self.assertEqual(raw,b'\xff\x00\x80')
        self.assertEqual(hashlib.sha256(raw).hexdigest(),result['stdout_sha256'])
    def test_finished_cgroup_disappearing_during_event_read(self):
        import errno
        original=Path.read_text
        def read(path,*args,**kwargs):
            if str(path).startswith('/sys/fs/cgroup/') and path.name=='memory.events':
                raise OSError(errno.ENODEV,'No such device')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read):
            result=self.run_code("print('done')")
        self.assertEqual(result['exit_code'],0,result)
        self.assertTrue(result['isolation']['job_empty'])
