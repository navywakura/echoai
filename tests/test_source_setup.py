import unittest,tempfile,json,hashlib,importlib.util
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('source_setup',Path(__file__).resolve().parents[1]/'tools/source_setup.py')
setup=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)

class SourceSetupTests(unittest.TestCase):
 def fixture(self,root):
  (root/'core').mkdir();(root/'core/representation.py').write_text('verified source\n')
  files={'core/representation.py':hashlib.sha256((root/'core/representation.py').read_bytes()).hexdigest()}
  (root/'SOURCE-MANIFEST.json').write_text(json.dumps({'files':files,'project':'echoai','version':'4.5.0b1'}))
 def test_valid_then_modified_source_is_rejected(self):
  with tempfile.TemporaryDirectory() as p:
   root=Path(p);self.fixture(root);self.assertTrue(setup.verify(root)['valid'])
   (root/'core/representation.py').write_text('modified\n');r=setup.verify(root);self.assertFalse(r['valid']);self.assertEqual(r['changed'],['core/representation.py'])
 def test_missing_source_is_rejected(self):
  with tempfile.TemporaryDirectory() as p:
   root=Path(p);self.fixture(root);(root/'core/representation.py').unlink();self.assertFalse(setup.verify(root)['valid'])
 def test_traversal_and_symlink_are_rejected(self):
  with tempfile.TemporaryDirectory() as p:
   root=Path(p);self.fixture(root);d=json.loads((root/'SOURCE-MANIFEST.json').read_text());d['files']['../outside']='a'*64
   (root/'SOURCE-MANIFEST.json').write_text(json.dumps(d));self.assertFalse(setup.verify(root)['valid'])
   d['files'].pop('../outside');(root/'SOURCE-MANIFEST.json').write_text(json.dumps(d));(root/'core/representation.py').unlink();(root/'core/representation.py').symlink_to('/etc/hosts');self.assertFalse(setup.verify(root)['valid'])
 def test_unknown_and_shell_commands_are_rejected(self):
  for command in ('S6-exam','test; rm -rf /','unknown'):
   with self.assertRaises(ValueError):setup.command(Path('/tmp'), 'echoai',command)
 def test_manifest_must_have_files(self):
  with tempfile.TemporaryDirectory() as p:
   root=Path(p);(root/'SOURCE-MANIFEST.json').write_text('{"files":{}}');self.assertFalse(setup.verify(root)['valid'])

if __name__=='__main__':unittest.main()
