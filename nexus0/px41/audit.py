"""Repeatable read-only entry point; delegates to the frozen verifier.

Added after certification: bench audit deliberately creates its receipt with
exclusive creation, and cannot write that receipt twice. This wrapper changes
no criterion, frozen source, flight record, report or receipt.
"""
import json
from .bench import REPORT, verify_report


def main():
    report = json.loads(REPORT.read_text())
    valid = verify_report(report)
    print(json.dumps(dict(valid=valid, green=report.get('green'),
                          certificate_sha256=report.get('certificate_sha256')), sort_keys=True))
    if not valid or report.get('green') is not True:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
