import unittest,asyncio,tempfile,sys,os
from pathlib import Path
from echo_nexus.connections import parse,describe
from echo_nexus.transport import OpenCodeCortex

class OpenCodeTests(unittest.IsolatedAsyncioTestCase):
 async def test_public_text_only_and_literal_prompt(self):
  with tempfile.TemporaryDirectory() as d:
   exe=Path(d)/'opencode';exe.write_text('#!'+sys.executable+'\nimport json,sys,os\nassert "--pure" in sys.argv\nassert json.loads(os.environ["OPENCODE_CONFIG_CONTENT"])["permission"]["*"]=="deny"\nassert sys.argv[-1].endswith("hello; touch nope")\nprint(json.dumps({"type":"reasoning","part":{"text":"private"}}))\nprint(json.dumps({"type":"tool_use","part":{"text":"not executed"}}))\nprint(json.dumps({"type":"text","part":{"text":"public answer"}}))\n');exe.chmod(0o755)
   client=OpenCodeCortex('provider/model',executable=str(exe));out=[]
   result=await client.ask('hello; touch nope',on_delta=out.append)
   self.assertEqual(result,'public answer');self.assertEqual(out,['public answer']);self.assertFalse((Path(d)/'nope').exists())
 async def test_timeout_is_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   exe=Path(d)/'opencode';exe.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(30)\n');exe.chmod(0o755)
   with self.assertRaises(RuntimeError):await OpenCodeCortex('provider/model',executable=str(exe),timeout=.05).ask('hello')
 def test_connection_profile(self):
  p=parse(['opencode','provider/model']);self.assertEqual(p['mode'],'opencode');self.assertIn('provider/model',describe(p))

if __name__=='__main__':unittest.main()
