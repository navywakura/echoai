"""Pinned Python rootfs: real processes, archive identity, fail closed."""
import json
from pathlib import Path
import tempfile
import unittest
from echoai.pcworld.runtime import build_runtime, load_runtime, export_runtime, import_runtime
from echoai.pcworld.runner import execute, environment_identity

class PinnedRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        cls.runtime=build_runtime(cls.root/'image')
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def test_pinned_stdlib_without_host_tools(self):
        work=self.root/'work';work.mkdir(exist_ok=True)
        r=execute(work,['/usr/bin/python3','-I','-c',
            "import json,math,sqlite3,hashlib,zlib,csv; from pathlib import Path; "
            "assert not Path('/usr/bin/bash').exists(); "
            "assert not Path('/usr/bin/curl').exists(); "
            "print(json.dumps({'root':str(Path.cwd()),'sqrt':math.isqrt(49)}))"],runtime=self.runtime)
        self.assertEqual(r['exit_code'],0,r)
        self.assertEqual(json.loads(r['stdout']),{'root':'/workspace','sqrt':7})
        self.assertEqual(r['isolation']['runtime_snapshot'],self.runtime.id)
        self.assertFalse(r['isolation']['host_usr_mounted'])
        self.assertTrue(environment_identity(self.runtime)['dependencies_pinned'])
        self.assertFalse(environment_identity(self.runtime)['hermetic_cacheable'])
    def test_export_import_exact_identity(self):
        a=self.root/'one.tar';b=self.root/'two.tar'
        export_runtime(self.runtime,a);export_runtime(self.runtime,b)
        import hashlib
        self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(),hashlib.sha256(b.read_bytes()).hexdigest())
        restored=import_runtime(a,self.root/'restored',expected_id=self.runtime.id)
        self.assertEqual(restored.id,self.runtime.id)
        self.assertEqual(load_runtime(self.root/'restored').id,restored.id)
    def test_tampered_image_refused(self):
        image=build_runtime(self.root/'tamper')
        target=image.root/'usr/bin/python3'
        target.chmod(0o755);target.write_bytes(b'wrong');target.chmod(0o555)
        with self.assertRaises(ValueError): load_runtime(self.root/'tamper')
    def test_archive_identity_mismatch_refused(self):
        path=self.root/'mismatch.tar';export_runtime(self.runtime,path)
        with self.assertRaises(ValueError):
            import_runtime(path,self.root/'bad-restore',expected_id='0'*64)
    def test_rejects_extended_header_before_tar_expansion(self):
        import tarfile
        from unittest.mock import patch
        header=tarfile.TarInfo('pax');header.type=tarfile.XHDTYPE;header.size=512
        archive=self.root/'extended.tar';archive.write_bytes(header.tobuf()+b'\0'*2048)
        with patch.object(tarfile.TarInfo,'_proc_pax',side_effect=AssertionError('metadata expanded before validation')):
            with self.assertRaises(ValueError):
                import_runtime(archive,self.root/'extended',expected_id=self.runtime.id)
