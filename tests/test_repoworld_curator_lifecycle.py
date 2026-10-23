"""Public fake image lifecycle and CLI checks; no hidden datasets or GPU."""
import sys,types,unittest,subprocess
from unittest.mock import Mock,patch
try:
 from .repoworld_support import ROOT
except ImportError:
 from repoworld_support import ROOT
from echoai.repoworld import official_curator as curator
class ImageLifecycleTests(unittest.TestCase):
 def lease(self,client,*,present=False,evict=True):
  class Missing(Exception):pass
  module=types.SimpleNamespace(errors=types.SimpleNamespace(ImageNotFound=Missing))
  image=types.SimpleNamespace(id='sha256:'+'a'*64)
  client.images.get.side_effect=None if present else Missing()
  client.images.get.return_value=image;client.images.pull.return_value=image;client.images.list.return_value=[]
  return module,image
 def test_only_new_images_are_evicted_even_after_failed_check(self):
  for present in (False,True):
   client=Mock();module,image=self.lease(client,present=present)
   with patch.dict(sys.modules,docker=module),patch('shutil.disk_usage',return_value=types.SimpleNamespace(free=30*1024**3)):
    with self.assertRaisesRegex(RuntimeError,'fixture failure'):
     with curator.control_image(client,'public/image:tag',allow_pull=True,evict=True) as actual:
      self.assertEqual(actual.id,image.id);raise RuntimeError('fixture failure')
   if present:client.images.remove.assert_not_called();client.images.pull.assert_not_called()
   else:client.images.remove.assert_called_once_with(image.id,force=False)
 def test_no_pull_or_low_disk_never_downloads(self):
  for allow,free in ((False,30*1024**3),(True,1)):
   client=Mock();module,_=self.lease(client)
   with patch.dict(sys.modules,docker=module),patch('shutil.disk_usage',return_value=types.SimpleNamespace(free=free)):
    with self.assertRaises(RuntimeError):
     with curator.control_image(client,'public/image:tag',allow_pull=allow,evict=True):pass
   client.images.pull.assert_not_called();client.images.remove.assert_not_called()
 def test_cli_accepts_remote_calibration_alias_without_starting_provider(self):
  result=subprocess.run([sys.executable,str(ROOT/'repository/scripts/run_repoworld.py'),'calibrate-remote','--help'],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('--provider',result.stdout)

 def test_pulled_tag_does_not_own_an_existing_untagged_image(self):
  client=Mock();module,image=self.lease(client)
  client.images.list.return_value=[image]
  with patch.dict(sys.modules,docker=module),patch('shutil.disk_usage',return_value=types.SimpleNamespace(free=30*1024**3)):
   with curator.control_image(client,'public/image:tag',allow_pull=True,evict=True):pass
  client.images.remove.assert_not_called()
