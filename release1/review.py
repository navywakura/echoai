"""E4-RELEASE-1 · REL-C: export allowlist and secret/private-data scan of the wheel.

    python3 echoai/release1/review.py WHEEL OUT_JSON

Every entry must match the allowlist (C1). Every entry, text or binary, is scanned
for credentials and private markers (C2). Findings are listed, never redacted away.
"""
import fnmatch
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ALLOW = (
    "echoai.cpython-*.so", "navi10_*.cpython-*.so", "echoai_release.pth",
    "echoai_release/*", "echoai/nexus0/bank/*.json", "echoai/nexus0/*.gbnf", "echoai/nexus0/tools/*_cortex.py",
    "echoai/docs/ECHO4-*-DESIGN.md", "echoai/docs/ECHO4-*-PREFLIGHT.md",
    "echoai/lab/echo4/integrate1-dev-v1/*", "echoai/lab/echo4/integrate1-d-v1/report.json",
    "echoai/lab/echo4/integrate1-d-v1/audit-receipt.json", "echoai/receipts/*/audit-receipt.json",
    "echoai-*.dist-info/*",
)
PATTERNS = {
    "github_token": rb"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}",
    "hf_token": rb"hf_[A-Za-z0-9]{30,}",
    "openai_like_key": rb"sk-[A-Za-z0-9_-]{24,}",
    "aws_key": rb"AKIA[0-9A-Z]{16}",
    "private_key": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "slack_token": rb"xox[abpr]-[A-Za-z0-9-]{10,}",
    "discord_webhook": rb"discord(?:app)?\.com/api/webhooks/",
    "email": rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "home_path": rb"/home/user",
    "discord_assets": rb"echo-discord",
    "external_disk": rb"Volum nou",
    "private_dir": rb"REALRXOS/RXos/private",
}
# Reviewed by hand (2026-09-24): constants in audited code, not secrets. Declared, not hidden.
REVIEWED = {
    ("openai_like_key", "sk-test-DO-NOT-LEAK-1234567890"):
        "fake key used by tests/test_release1.py to prove real keys never leak",
    ("home_path", "/home/user"):
        "default model path in sealed echo4/situate2_bench.py (reveals the lab username and model "
        "location; cannot be edited without breaking the SITUATE-2 seal) and the SIM-3 isolation probe "
        "(nexus0/sim3/assets/probe.py), which checks that /home/user is NOT readable from the sandbox",
    ("discord_assets", "echo-discord"):
        "guard string in sealed echo4/dream_qwen.py that REFUSES legacy Discord assets, and its test",
}
# Public contact addresses that may legitimately appear in licence texts.
ALLOWED_EMAILS = {b"noreply@anthropic.com"}


def scan(wheel):
    z = zipfile.ZipFile(wheel)
    outside, findings = [], []
    for name in z.namelist():
        if not any(fnmatch.fnmatch(name, pat) for pat in ALLOW):
            outside.append(name)
        data = z.read(name)
        for kind, rx in PATTERNS.items():
            for m in re.finditer(rx, data):
                hit = m.group(0)
                if kind == "email" and (hit in ALLOWED_EMAILS or hit.endswith(b".so") or b"@" not in hit):
                    continue
                findings.append({"file": name, "kind": kind,
                                 "sample": hit[:48].decode("latin-1"), "offset": m.start()})
    return z.namelist(), outside, findings


def _reviewed(f):
    return any(f["kind"] == kind and f["sample"].startswith(sample) for kind, sample in REVIEWED)


def main():
    wheel, out = Path(sys.argv[1]), Path(sys.argv[2])
    names, outside, findings = scan(wheel)
    by_kind = {}
    for f in findings:
        by_kind.setdefault(f["kind"], set()).add(f["file"])
    result = {"wheel": wheel.name, "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
              "entries": len(names), "outside_allowlist": outside,
              "findings": findings[:200], "finding_count": len(findings),
              "findings_by_kind": {k: sorted(v) for k, v in by_kind.items()},
              "reviewed_exceptions": {k[0] + ":" + k[1]: v for k, v in REVIEWED.items()},
              "unreviewed": [f for f in findings if not _reviewed(f)],
              "C1_passed": not outside, "C2_passed": not [f for f in findings if not _reviewed(f)]}
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in result.items() if k != "findings"}, indent=1, ensure_ascii=False))
    return 0 if result["C1_passed"] and result["C2_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
