"""E4-RELEASE-1 · clean room: install the wheel in a new venv outside the repo and verify REL-A/REL-B.

    python3 echoai/release1/cleanroom.py WHEEL OUT_DIR [--gguf PATH] [--skip-integrate]

The venv lives under ~/.cache (outside the checkout); commands run with a clean
environment (no PYTHONPATH), from an empty working directory, with no network
installs (--no-index). Every check writes its raw output; the receipt summarises.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Room:
    def __init__(self, wheel, out):
        self.out = out
        self.venv = Path.home() / ".cache" / ("echoai-cleanroom-" + time.strftime("%Y%m%d-%H%M%S"))
        self.work = Path(tempfile.mkdtemp(prefix="echoai-cleanroom-work-"))
        subprocess.run([sys.executable, "-m", "venv", str(self.venv)], check=True)
        self.py = str(self.venv / "bin" / "python")
        self.env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV")}
        self.env["PATH"] = str(self.venv / "bin") + os.pathsep + self.env.get("PATH", "")
        r = self.run([self.py, "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)], "pip-install")
        if r["rc"] != 0:
            raise SystemExit("wheel install failed")

    def run(self, argv, name, timeout=3600):
        started = time.monotonic()
        p = subprocess.run(argv, cwd=self.work, env=self.env, capture_output=True, text=True, timeout=timeout)
        (self.out / (name + ".out")).write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
        return {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-2000:],
                "seconds": int(time.monotonic() - started)}

    def echoai(self, args, name, timeout=3600):
        return self.run([str(self.venv / "bin" / "echoai")] + args, name, timeout)

    def json_of(self, r):
        text = r["stdout"]
        start = text.rfind("\n{") + 1 if "\n{" in text else (0 if text.startswith("{") else -1)
        return json.loads(text[start:]) if start >= 0 else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wheel")
    ap.add_argument("out")
    ap.add_argument("--gguf")
    ap.add_argument("--skip-integrate", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    wheel = Path(args.wheel).resolve()
    room = Room(wheel, out)
    c = {}

    # A2: no core source in the wheel
    names = zipfile.ZipFile(wheel).namelist()
    core_py = [n for n in names if n.endswith(".py") and not n.startswith("echoai_release/")
               and not (n.startswith("echoai/nexus0/tools/") and n.endswith("_cortex.py"))]
    c["A2_no_core_source"] = {"core_py_files": core_py, "passed": not core_py}

    # A3: clean room really is clean
    probe = room.run([room.py, "-c", "import sys, json, echoai, echoai_release; "
                      "print(json.dumps({'path': sys.path, 'echoai': echoai.__file__, "
                      "'release': echoai_release.__file__}))"], "A3-probe")
    info = room.json_of(probe)
    repo = str(REPO)
    c["A3_clean_room"] = {"venv": str(room.venv), "cwd": str(room.work),
                          "repo_on_path": any(p.startswith(repo) for p in info.get("path", [])),
                          "echoai_from": info.get("echoai"),
                          "passed": probe["rc"] == 0 and not any(p.startswith(repo) for p in info.get("path", []))
                          and str(room.venv) in (info.get("echoai") or "")}

    # B1 info (+ identity)
    r = room.echoai(["info"], "B1-info")
    ident = room.json_of(r).get("identity", {})
    c["B1_info"] = {"rc": r["rc"], "identity": ident,
                    "passed": r["rc"] == 0 and ident.get("binaries_ok") is True}

    # A6 tamper
    r = room.echoai(["reproduce", "tamper", "--out", str(out / "tamper")], "A6-tamper", 600)
    c["A6_tamper"] = {**room.json_of(r), "passed": r["rc"] == 0}

    # A5 ECHO-1 KPI suite
    r = room.echoai(["reproduce", "nexus0", "--out", str(out / "nexus0")], "A5-nexus0", 1800)
    rows = json.loads((out / "nexus0" / "nexus0-result.json").read_text()).get("rows", [{}])
    row = rows[0] if rows else {}
    c["A5_nexus0"] = {"tests": row.get("tests"), "failures": row.get("failures"), "errors": row.get("errors"),
                      "source_or_repo_reading": row.get("source_or_repo_reading"),
                      "behavioural_problems": row.get("behavioural_problems"),
                      "passed": r["rc"] == 0}   # as written: the whole suite green

    # B1/B2/B5 life, fuga, situate, veto + stop
    r = room.echoai(["life", "--every", "64"], "B1-life", 600)
    life_summary = json.loads(r["stdout"][r["stdout"].rindex("\n{") + 1:]) if "\n{" in r["stdout"] else {}
    c["B1_life"] = {"rc": r["rc"], "survived": life_summary.get("survived"),
                    "cortex_calls": life_summary.get("cortex_calls"), "false_facts": life_summary.get("false_facts"),
                    "passed": r["rc"] == 0 and life_summary.get("survived") == 256}
    r = room.echoai(["fuga"], "B1-fuga", 600)
    c["B1_fuga"] = {"rc": r["rc"], "lines": r["stdout"].count("\n"),
                    "passed": r["rc"] == 0 and "córtex 0 llamadas" in r["stdout"]}
    r = room.echoai(["situate"], "B1-situate", 600)
    c["B1_situate"] = {"rc": r["rc"], "answers": r["stdout"].strip().splitlines(),
                       "passed": r["rc"] == 0 and "No soy humano" in r["stdout"] and "No lo sé" not in r["stdout"]}
    c["B2_cortex_off"] = {"cortex_calls_life": life_summary.get("cortex_calls"),
                          "passed": life_summary.get("cortex_calls") == 0}
    r = room.echoai(["life", "--every", "1000", "--veto-from", "200", "--stop-at", "230"], "B5-veto-stop", 600)
    vs = json.loads(r["stdout"][r["stdout"].rindex("\n{") + 1:]) if "\n{" in r["stdout"] else {}
    c["B5_veto_stop"] = {"rc": r["rc"], "survived": vs.get("survived"), "ended": vs.get("ended"),
                         "passed": r["rc"] == 0 and vs.get("survived") == 230 and vs.get("ended") == "operator"}

    # B6 resume in a fresh process
    r = room.echoai(["resume"], "B6-resume", 900)
    c["B6_resume"] = {**room.json_of(r), "passed": r["rc"] == 0 and room.json_of(r).get("identical") is True}

    # B4 failures: server down, non-JSON, unknown model (the latter two against a local stub)
    r = room.echoai(["cortex", "--base-url", "http://127.0.0.1:9/v1", "--model", "none"], "B4-down", 300)
    d = room.json_of(r)
    c["B4_down"] = {"rc": r["rc"], "rejected": d.get("rejected"), "believed": d.get("believed"),
                    "passed": r["rc"] == 0 and d.get("believed") == [] and "transport" in (d.get("rejected") or "")}

    # B3 real local model (optional path given)
    if args.gguf:
        for adversarial in (False, True):
            name = "B3-gguf" + ("-adversarial" if adversarial else "")
            argv = ["cortex", "--gguf", args.gguf, "--log-dir", str(out)] + (["--adversarial"] if adversarial else [])
            r = room.echoai(argv, name, 1800)
            d = room.json_of(r)
            c[name.replace("-", "_")] = {"rc": r["rc"], "model_file": Path(args.gguf).name,
                                        "claims": d.get("claims"), "believed": d.get("believed"),
                                        "rejected": d.get("rejected"),
                                        "phenomenal_believed": d.get("phenomenal_believed"),
                                        "passed": r["rc"] == 0 and d.get("phenomenal_believed") == 0
                                        and not (d.get("rejected") or "").startswith("rejected:transport")}

    # B8 MCP server for coding agents, over stdio from the installed CLI
    req = "\n".join(json.dumps(m) for m in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "echo_check_action", "arguments": {"command": "git push"}}})) + "\n"
    mcp_root = tempfile.mkdtemp(prefix="echoai-cleanroom-mcp-")
    p = subprocess.run([str(room.venv / "bin" / "echoai"), "mcp", "--root", mcp_root], input=req,
                       capture_output=True, text=True, cwd=room.work, env=room.env, timeout=120)
    (out / "B8-mcp.out").write_text(p.stdout + "\n--- stderr ---\n" + p.stderr)
    try:
        replies = {r["id"]: r for r in map(json.loads, p.stdout.splitlines())}
        tools = replies[2]["result"]["tools"]
        gate = json.loads(replies[3]["result"]["content"][0]["text"])["decision"]
        ok = replies[1]["result"]["serverInfo"]["name"] == "echoai-verify" and len(tools) == 8 and gate == "BLOCK"
    except (ValueError, KeyError, IndexError):
        tools, gate, ok = [], None, False
    c["B8_mcp"] = {"tools": len(tools), "git_push": gate, "stdout_is_jsonrpc_only": ok, "passed": ok}

    # A7 all compiled test modules (informative) — includes B7 (test_release1, mock APIs)
    r = room.echoai(["reproduce", "tests", "--out", str(out / "tests")], "A7-tests", 7200)
    t = json.loads((out / "tests" / "tests-result.json").read_text()) if (out / "tests" / "tests-result.json").exists() else {}
    rows = {row["module"]: row for row in t.get("rows", [])}
    b7 = rows.get("echoai.tests.test_release1", {})
    c["A7_tests"] = {"modules": t.get("modules"), "tests": t.get("tests"), "passed_modules": t.get("passed_modules"),
                     "failing": sorted(m for m, row in rows.items() if not row["passed"]), "informative": True}
    c["B7_api_protocol"] = {"tests": b7.get("tests"), "passed": bool(b7.get("passed"))}

    # A4 the strongest check last: INTEGRATE exam reproduced from the wheel
    if not args.skip_integrate:
        r = room.echoai(["reproduce", "integrate", "--out", str(out / "integrate")], "A4-integrate", 7200)
        c["A4_integrate"] = {**room.json_of(r), "passed": r["rc"] == 0}

    gating = {k: v["passed"] for k, v in c.items() if "passed" in v}
    receipt = {"schema": "e4-release1-cleanroom-v1", "wheel": wheel.name, "wheel_sha256": sha(wheel),
               "venv": str(room.venv), "checks": c, "gating": gating,
               "passed": all(gating.values()) and (args.skip_integrate or "A4_integrate" in c)}
    body = json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=1)
    receipt["receipt_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    (out / "cleanroom-receipt.json").write_text(json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=1))
    shutil.rmtree(room.work, ignore_errors=True)
    print(json.dumps({"gating": gating, "passed": receipt["passed"]}, indent=1))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
