"""Run every immutable v2 test with an absent, isolated test report.

The v2 freeze-gate test redirects ROOT but not REPORT. Once its real report
exists, the unrelated 'already frozen' guard fires before the tested gate.
This fixture isolates only that report path; no assertion or test is skipped.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from echoai.nexus0.pattern1r_v2 import campaign
from echoai.tests import test_pattern1r_v2


def main():
    with tempfile.TemporaryDirectory() as tmp, patch.object(campaign,'REPORT',Path(tmp)/'report.json'):
        suite=unittest.defaultTestLoader.loadTestsFromModule(test_pattern1r_v2)
        return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()


if __name__=='__main__':raise SystemExit(0 if main() else 1)
