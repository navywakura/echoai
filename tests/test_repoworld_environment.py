import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.pcworld.runtime import load_runtime, build_runtime, repository_runtime
from echoai.pcworld.snapshots import SnapshotStore
from echoai.repoworld.types import PublicTask
from echoai.repoworld.environment import environment_ref, prepare_repo, execute_repo, repo_store


class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.root=Path(cls.temp.name)
        existing=ROOT/'ECHO-5.1/artifacts/runtime-python314-20261013'
        cls.runtime=load_runtime(existing) if existing.exists() else build_runtime(cls.root/'runtime')
        cls.runtime=repository_runtime(cls.runtime,cls.root/'repo-runtime')
        cls.environment=environment_ref(cls.runtime,scope='stdlib-calibration')
        cls.source=cls.root/'git';cls.source.mkdir()
        (cls.source/'a.py').write_text('value = 1\n')
        for args in [('init',),('add','a.py'),('-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-qm','fixture')]:
            subprocess.run(['git','-C',str(cls.source),*args],check=True,capture_output=True)
        commit=subprocess.check_output(['git','-C',str(cls.source),'rev-parse','HEAD'],text=True).strip()
        cls.task=PublicTask('fixture__repo-1','fixture/repo',commit,'Public fixture')
        cls.base=prepare_repo(cls.task,cls.source,cls.environment,commit,store_dir=cls.root/'base')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def run_code(self, code, **kwargs):
        return execute_repo(self.base,self.base.snapshot,('/usr/bin/python3','-I','-c',code),
                            limits=kwargs.pop('limits',{}),check_artifacts=kwargs.pop('check_artifacts',()),**kwargs)

    def test_identity_is_commit_export_not_dirty_tree(self):
        (self.source/'untracked').write_text('PRIVATE_UNTRACKED')
        (self.source/'a.py').write_text('DIRTY')
        base=prepare_repo(self.task,self.source,self.environment,self.task.base_commit,store_dir=self.root/'base2')
        self.assertEqual(base.snapshot.id,self.base.snapshot.id)
        self.assertNotIn('untracked',base.snapshot.manifest['entries'])
        self.assertNotIn('.git',base.snapshot.manifest['entries'])
        with self.assertRaises(ValueError): prepare_repo(self.task,self.source,self.environment,'b'*40)

    def test_git_internal_links_export_without_reading_external_targets(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'git';src.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(src),*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init');(src/'a.py').write_text('value = 1\n');(src/'alias.py').symlink_to('a.py')
            git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-qm','internal')
            task=replace(self.task,base_commit=git('rev-parse','HEAD'))
            base=prepare_repo(task,src,self.environment,task.base_commit,store_dir=p/'store')
            self.assertTrue((base.snapshot.root/'alias.py').is_symlink())
            (src/'alias.py').unlink();(src/'alias.py').symlink_to('/etc/passwd')
            git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@invalid','commit','-qm','external')
            task=replace(task,base_commit=git('rev-parse','HEAD'))
            with self.assertRaises(ValueError):prepare_repo(task,src,self.environment,task.base_commit,store_dir=p/'store2')

    def test_real_scratch_is_writable_but_base_candidate_are_readonly(self):
        before=self.base.snapshot.id
        code="""from pathlib import Path
assert Path.cwd() == Path('/work')
assert Path('a.py').read_text() == 'value = 1\\n'
Path('a.py').write_text('transient')
for p in ('/repo-base/a.py','/candidate/a.py'):
 try: Path(p).write_text('BAD')
 except OSError: pass
 else: raise AssertionError('writable base')
Path('/work/.out/measurement.json').write_text('{"value": 7}')
print('scratch-ok')
"""
        result=self.run_code(code,check_artifacts=('measurement.json',))
        self.assertEqual(result['exit_code'],0,result)
        self.assertIn('scratch-ok',result['stdout'])
        self.assertFalse(result['isolation']['host_usr_mounted'])
        self.assertTrue(result['isolation']['job_empty'])
        self.assertEqual(self.base.snapshot.id,before)
        repo_store(self.base.snapshot.root.parent.parent).validate(self.base.snapshot)
        self.assertEqual(result['artifacts']['measurement.json']['sha256'],hashlib.sha256(b'{"value": 7}').hexdigest())
        self.assertFalse(result['task_success'])

    def test_readonly_public_fixture_copy_preserves_original_writable_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source';(source/'tests/fixtures').mkdir(parents=True)
            (source/'tests/fixtures/a.txt').write_text('public fixture')
            snap=repo_store(p/'store').capture(source)
            base=type(self.base)(self.task,snap,self.environment)
            code="""import shutil
from pathlib import Path
try: Path('/work/tests/fixtures/a.txt').write_text('tampered')
except OSError: pass
else: raise AssertionError('public fixture writable')
shutil.copytree('/work/tests/fixtures','/work/copied')
Path('/work/copied/new.txt').write_text('generated by test')
print('copied fixture usable')
"""
            r=execute_repo(base,snap,('/usr/bin/python3','-I','-c',code),limits={},check_artifacts=())
            self.assertEqual(r['exit_code'],0,r)

    def test_no_host_secret_or_network_or_usr(self):
        sentinel=self.root/'secret';sentinel.write_text('HOST_SECRET')
        code=f"""from pathlib import Path
import socket
assert not Path({str(sentinel)!r}).exists()
assert not Path('/usr/bin/git').exists()
assert not Path('/candidate/.git').exists()
s=socket.socket();s.settimeout(.1)
try: s.connect(('127.0.0.1',8771))
except OSError: print('isolated')
else: raise AssertionError('host reached')
"""
        r=self.run_code(code);self.assertEqual(r['exit_code'],0,r)
        self.assertNotIn('HOST_SECRET',r['stdout'])

    def test_shared_memory_uses_the_same_bounded_scratch(self):
        code="""from pathlib import Path
import multiprocessing
s=multiprocessing.Semaphore(1)
assert s.acquire(timeout=.1)
s.release()
assert Path('/dev/shm').resolve() == Path('/work/.shm')
Path('/dev/shm/probe').write_text('ok')
assert Path('/work/.shm/probe').read_text() == 'ok'
Path('/work/fill').write_bytes(b'x'*(2*1024*1024))
try: Path('/dev/shm/fill').write_bytes(b'x'*(3*1024*1024))
except OSError as e: assert e.errno == 28
else: raise AssertionError('shared memory escaped aggregate quota')
"""
        r=self.run_code(code,limits={'disk_bytes':4*1024*1024})
        self.assertEqual(r['exit_code'],0,r)

    def test_repository_links_preserved_in_scratch_and_protected_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'src';(src/'tests').mkdir(parents=True)
            (src/'a.py').write_text('public source')
            (src/'alias.py').symlink_to('a.py')
            (src/'tests/fixture.py').symlink_to('../a.py')
            snap=repo_store(p/'store').capture(src)
            base=type(self.base)(self.task,snap,self.environment)
            code="""from pathlib import Path
import os
assert Path('alias.py').is_symlink()
assert Path('tests/fixture.py').is_symlink()
assert os.readlink('tests/fixture.py') == '../a.py'
assert Path('tests/fixture.py').read_text() == 'public source'
"""
            r=execute_repo(base,snap,('/usr/bin/python3','-I','-c',code),limits={},check_artifacts=())
            self.assertEqual(r['exit_code'],0,r)

    def test_timeout_kills_descendants(self):
        r=self.run_code('import os,time\nif os.fork()==0: time.sleep(20)\ntime.sleep(20)',limits={'wall_ms':650})
        self.assertEqual(r['status'],'TIMEOUT',r)
        self.assertTrue(r['isolation']['job_empty'])

    def test_slow_service_registration_is_not_misread_as_finished_job(self):
        import sys
        from echoai.pcworld import runner
        original=runner.subprocess.Popen
        def delayed(argv,*args,**kwargs):
            if isinstance(argv,list) and argv[0]=='/usr/bin/systemd-run':
                unit=next(x.split('=',1)[1] for x in argv if x.startswith('--unit='))
                self.addCleanup(subprocess.run,['systemctl','--user','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                argv=[sys.executable,'-c','import os,sys,time;time.sleep(.25);os.execv(sys.argv[1],sys.argv[1:])',*argv]
            return original(argv,*args,**kwargs)
        with patch.object(runner.subprocess,'Popen',side_effect=delayed):
            result=self.run_code('print("registered-and-executed")')
        self.assertEqual(result['exit_code'],0,result)
        self.assertIn('registered-and-executed',result['stdout'])
        self.assertTrue(result['isolation']['job_empty'])

    def test_memory_cpu_and_tmpfs_are_bounded(self):
        r=self.run_code('a=bytearray(180*1024*1024)',limits={'memory_bytes':64*1024*1024})
        self.assertNotEqual(r['exit_code'],0,r)
        r=self.run_code('while True: pass',limits={'cpu_ms':150,'wall_ms':3000})
        self.assertEqual(r['status'],'CPU_LIMIT',r)
        r=self.run_code("from pathlib import Path\ntry: Path('fill').write_bytes(b'x'*(8*1024*1024))\nexcept OSError as e: assert e.errno==28;print('bounded')\nelse: raise AssertionError('no disk limit')",limits={'disk_bytes':1024*1024})
        self.assertEqual(r['exit_code'],0,r)
        self.assertIn('bounded',r['stdout'])

    def test_temporary_children_do_not_inherit_repo_configuration_or_extra_quota(self):
        code='''from pathlib import Path
import os, tempfile
Path('tox.ini').write_text('[pytest]\\nfilterwarnings=error\\n')
with tempfile.TemporaryDirectory() as directory:
    os.chdir(directory)
    assert not any((p/'tox.ini').exists() for p in Path.cwd().parents)
    Path('child').mkdir();Path('child').rename('renamed');Path('renamed').rmdir()
work=os.statvfs('/work');temp=os.statvfs('/tmp')
assert os.stat('/work').st_dev != os.stat('/tmp').st_dev
assert work.f_blocks*work.f_frsize + temp.f_blocks*temp.f_frsize <= 4*1024*1024
assert os.stat('/dev/shm').st_dev == os.stat('/work').st_dev
print('independent temporary ancestry; unchanged aggregate disk ceiling')
'''
        result=self.run_code(code,limits={'disk_bytes':4*1024*1024})
        self.assertEqual(result['exit_code'],0,result)

    def test_artifact_symlink_and_traversal_rejected(self):
        with self.assertRaises(ValueError): self.run_code('pass',check_artifacts=('../a.py',))
        r=self.run_code("from pathlib import Path; Path('/work/.out/result').symlink_to('/etc/pcworld-runtime.json')",check_artifacts=('result',))
        self.assertNotIn('result',r['artifacts'])

    def test_public_report_larger_than_64k_is_retained_with_aggregate_cap(self):
        code="""from pathlib import Path
Path('/work/.out/public.xml').write_bytes(b'x'*(70*1024))
Path('/work/.out/extra').write_bytes(b'x'*(470*1024))
Path('/work/.out/oversize').write_bytes(b'x'*(513*1024))
"""
        result=self.run_code(code,limits={'output_bytes':256*1024},
                             check_artifacts=('public.xml','extra','oversize'))
        self.assertEqual(result['exit_code'],0,result)
        self.assertEqual(set(result['artifacts']),{'public.xml'})
        self.assertEqual(result['artifacts']['public.xml']['bytes'],70*1024)
        self.assertEqual(result['artifacts']['public.xml']['authority'],'candidate_output_untrusted')

    def test_bounded_public_target_count_leaves_room_for_runner_flags(self):
        argv=('/usr/bin/python3','-I','-c','import sys; assert len(sys.argv)==129',
              *(str(i) for i in range(128)))
        result=execute_repo(self.base,self.base.snapshot,argv,limits={},check_artifacts=())
        self.assertEqual(result['exit_code'],0,result)
        with self.assertRaisesRegex(ValueError,'structured argv'):
            execute_repo(self.base,self.base.snapshot,('/usr/bin/python3',)*257,
                         limits={},check_artifacts=())

    def test_process_limit_and_project_environment(self):
        r=self.run_code("import os,time\nfor _ in range(30):\n try:\n  if os.fork()==0: time.sleep(20);os._exit(0)\n except OSError: print('pids-bounded',flush=True);break\ntime.sleep(20)",limits={'pids':12,'wall_ms':800})
        self.assertIn('pids-bounded',r['stdout'])
        self.assertTrue(r['isolation']['job_empty'])
        with self.assertRaises(ValueError): self.run_code('pass',env={'LD_PRELOAD':'/work/evil.so'})

    def test_explicit_site_joblib_profile_is_passed_and_value_restricted(self):
        result=self.run_code('import os;assert os.environ["SKLEARN_SITE_JOBLIB"]=="1"',env={'SKLEARN_SITE_JOBLIB':'1'})
        self.assertEqual(result['exit_code'],0,result)
        with self.assertRaises(ValueError):self.run_code('pass',env={'SKLEARN_SITE_JOBLIB':'unexpected'})

    def test_missing_runtime_profile_never_mounts_host_usr(self):
        from echoai.pcworld.runner import execute
        with self.assertRaises(ValueError): execute(self.base.snapshot,['/usr/bin/python3','-c','pass'],profile='repoworld',repo_base=self.base.snapshot)

    def test_proposed_probe_executes_only_inside_boundary_without_authority(self):
        result=execute_repo(self.base,self.base.snapshot,('/usr/bin/python3','/runner/probe.py'),limits={},
                            check_artifacts=(),probe_source='print("CLAIM_SOLVED")\n')
        self.assertEqual(result['exit_code'],0,result)
        self.assertIn('CLAIM_SOLVED',result['stdout'])
        self.assertFalse(result['task_success'])
        self.assertEqual(result['claim_status'],'unknown')

    def test_streaming_capture_never_reads_large_file_into_memory(self):
        from echoai.pcworld import snapshots
        source=self.root/'large';source.mkdir(exist_ok=True)
        with (source/'large.txt').open('wb') as f:
            for _ in range(70): f.write(b'x'*1024*1024)
        original=snapshots._read_bytes
        def guard(fd,info,limit):
            if info.st_size>1024*1024: raise AssertionError('unbounded file read')
            return original(fd,info,limit)
        with patch.object(snapshots,'_read_bytes',guard):
            store=repo_store(self.root/'large-store');snap=store.capture(source)
            self.assertEqual(store.read_range(snap,'large.txt',offset=1024,size=50),b'x'*50)
            store.validate(snap)
        # Propagated profile permits >64 MiB; no fallback to PCWorld defaults.
        base=type(self.base)(self.task,snap,self.environment)
        r=execute_repo(base,snap,('/usr/bin/python3','-I','-c',"from pathlib import Path; print(Path('large.txt').stat().st_size)"),limits={'disk_bytes':100*1024*1024},check_artifacts=())
        self.assertEqual(r['exit_code'],0,r)
        self.assertIn(str(70*1024*1024),r['stdout'])
