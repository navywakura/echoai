import json
from pathlib import Path
import tempfile
import unittest
from seed.s6b9_report import conclusion


class Report(unittest.TestCase):
    def test_running_job_does_not_become_a_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'status.json').write_text(json.dumps({'stage':'CPU_INFERENCE'}))
            self.assertIsNone(conclusion(root))

    def test_audited_tie_is_closed_without_green_or_exam(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data={'closed.json':{'result':'PILOT_NO_PROMOTION','s6_green':False},
                  'pilot.json':{'promote':False,'accepted_echo':1,'paired_A':{'echo':537,'fijo':537}},
                  'pilot-audit.json':{'valid':True}}
            for name,value in data.items():(root/name).write_text(json.dumps(value))
            self.assertFalse(conclusion(root)['green'])

    def test_green_flag_cannot_override_a_failed_exam_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'exam').mkdir()
            closed={'result':'EXAM_CLOSED','s6_green':True}
            audit={'green':True,'checks':{f'B{i}':i!=3 for i in range(1,6)},'sources':{},'strategies_sha256':'s'}
            (root/'closed.json').write_text(json.dumps(closed))
            (root/'exam/audit.json').write_text(json.dumps(audit))
            (root/'completed.json').write_text(json.dumps({'sources':{},'strategies_sha256':'s'}))
            with self.assertRaises(AssertionError):conclusion(root)


if __name__=='__main__':unittest.main()
