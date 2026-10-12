import json
from pathlib import Path
import tempfile
import unittest
from echoai.echo4.code_mcp import Server

class McpBoundary(unittest.TestCase):
    def test_T01_MCP_observes_but_does_not_certify_success(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.echoai').mkdir()
            (root/'.echoai/checks.json').write_text(json.dumps({'fake':['/usr/bin/python3','-c','print("{\\"valid\\":true}")']}))
            s=Server(root);r=s.call('echo_run_check',{'name':'fake'})
            self.assertTrue(r['ok']);self.assertEqual(r['exit'],0)
            self.assertIn('isolation',r);self.assertEqual(r['isolation']['backend'],'bubblewrap+cgroup-v2')
            self.assertEqual(s.call('echo_verify_claim',{'claim':{'type':'tests_pass','check':'fake'}})['status'],'unknown')
            self.assertEqual(s.call('echo_verify_claim',{'claim':{'type':'check_exit_zero','check':'fake'}})['status'],'supported')
    def test_T08_changed_check_invalidates_exit_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'.echoai').mkdir();p=root/'.echoai/checks.json'
            p.write_text(json.dumps({'x':['/usr/bin/true']}));s=Server(root);s.call('echo_run_check',{'name':'x'})
            p.write_text(json.dumps({'x':['/usr/bin/false']}))
            self.assertEqual(s.call('echo_verify_claim',{'claim':{'type':'check_exit_zero','check':'x'}})['status'],'unknown')
