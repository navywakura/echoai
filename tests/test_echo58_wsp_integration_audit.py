"""Review regressions against the preserved development integration receipts."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from echoai.echo58.wspfiles.integration import audit

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'lab/echo58/wspfiles/agent-integration-20261023'


@unittest.skipUnless((DATA/'results.json').exists(),'development integration receipts unavailable')
class AuditRegressions(unittest.TestCase):
    def test_rejects_changed_world_count_and_per_world_summary(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'receipts';shutil.copytree(DATA,target)
            result=json.loads((target/'results.json').read_text())
            result['worlds']=999;result['summary'][0]['outcomes']['wsp']['harm']=999
            (target/'results.json').write_text(json.dumps(result))
            with self.assertRaises((ValueError,AssertionError)):audit(target)

    def test_optimized_python_must_not_claim_audited_validity(self):
        p=subprocess.run([sys.executable,'-O','-m','echoai.echo58.wspfiles.integration','audit',str(DATA)],
                         cwd=ROOT.parent,capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('"valid": true',p.stdout)


if __name__=='__main__':unittest.main()
