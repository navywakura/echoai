"""Public entrypoints work together in one installation."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from echoai import cli, __version__

class PublicReleaseTests(unittest.TestCase):
    def capture(self, args):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): code=cli.main(args)
        return code,json.loads(out.getvalue())

    def test_official_identity_and_current_backend(self):
        code,value=self.capture(['info'])
        self.assertEqual(code,0)
        self.assertEqual(value['version'],__version__)
        self.assertEqual(value['status'],'stable')
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'XDG_STATE_HOME':tmp}):
            config=json.loads(cli.backend().read_text())
        self.assertIn(__version__,config['name'])
        self.assertNotIn('research',config['name'])

    def test_demo_transfers_role_and_reloads_exact_memory(self):
        from echoai.echo58.wspfiles.memory import load_memory
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'memory.wsp'
            code,value=self.capture(['demo','--memory',str(path)])
            self.assertEqual(code,0)
            self.assertEqual(value['observations'],3)
            self.assertEqual(value['new_object_prediction'],'HURT')
            m=load_memory(path)
            self.assertEqual(m.recall(99,16,'ENTER',0),'HURT')
            original=path.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(['demo','--memory',str(path)]),2)
            self.assertEqual(path.read_bytes(),original)

    def test_memory_subcommand_forwards_arguments(self):
        from unittest.mock import patch
        with patch.object(cli.subprocess,'call',return_value=2) as call:
            self.assertEqual(cli.main(['memory','verify','bad.wsp']),2)
        self.assertEqual(call.call_args.args[0][-2:],['verify','bad.wsp'])

if __name__=='__main__':unittest.main()
