"""Resume the frozen B10 pipeline in a user service, independent of this chat.

This supervisor is not an experimental source. It does not change proposals,
measurements, gates or retry policy. Logs are appended and jobs keep their IDs.
"""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from seed import s6b10 as s
from seed.game_selfimprove import atomic

UNIT = "echoai-s6b10"


def now():
    return datetime.now(timezone.utc).isoformat()


def active_workers(proc=Path("/proc")):
    found = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            args = (entry / "cmdline").read_bytes().decode().rstrip("\0").split("\0")
        except (OSError, UnicodeError):
            continue
        if "-m" in args and "seed.s6b10" in args:
            index = args.index("-m")
            if args[index + 1:index + 3] in (["seed.s6b10", "follow"], ["seed.s6b10", "audit"]):
                found.append(int(entry.name))
    return found


def check_audit_cache(root):
    """Refuse damaged restart artifacts before launching a verifier."""
    checked = 0
    for phase in ("pilot-audit", "campaign-audit"):
        for path in (root / phase / "cache").glob("*/*.json"):
            try:
                value = json.loads(path.read_text())
                valid = value["key"] == path.stem and s.sha(value["record"]) == value["digest"]
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Incomplete audit cache; preserve and recover before restarting: {path}") from exc
            if not valid:
                raise ValueError(f"Audit cache digest mismatch: {path}")
            checked += 1
    return checked


def check():
    profile = s.integrity()
    assert not (s.ROOT / "closed.json").exists(), "B10 already closed"
    assert not active_workers(), "a B10 worker is already running"
    submission = json.loads((s.BASE / "p0/submitted.json").read_text())
    assert submission["submitted"] and submission["ref"] == s.generator().metadata("p0")["id"]
    payload = json.loads((s.BASE / "p0/payload.json").read_text())
    answers = json.loads((s.BASE / "p0/output/answers.json").read_text())
    s.generator().check(answers, payload)
    cache_entries = check_audit_cache(s.ROOT)
    return {"at": now(), "profile_sha256": s.sha(profile), "recovered_ref": submission["ref"],
            "recovered_answers_sha256": s.sha(answers), "recovered_calls": sum(map(len, answers["arms"].values())),
            "verified_audit_cache_entries": cache_entries,
            "previous_status": json.loads((s.ROOT / "status.json").read_text()),
            "restart": "no", "unit": UNIT}


def run():
    with (s.ROOT / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not active_workers(), "another B10 worker is already running"
        s.integrity()
        atomic(s.ROOT / "supervisor.json", {"at": now(), "pid": os.getpid(), "state": "RUNNING", "unit": UNIT})
        with (s.BASE / "process-network.log").open("a") as log:
            log.write("\nB10 SUPERVISOR RESUMED " + now() + "\n")
            log.flush()
            result = subprocess.run([sys.executable, "-u", "-m", "seed.s6b10", "follow"],
                                    cwd=s.REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        with (s.ROOT / "report-process.log").open("a") as log:
            report = subprocess.run([sys.executable, "-u", "-m", "seed.s6b10_report"], cwd=s.REPO,
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        atomic(s.ROOT / "supervisor.json", {"at": now(), "pid": os.getpid(), "state": "FINISHED",
               "unit": UNIT, "exit_code": result.returncode, "report_exit_code": report.returncode})
        return result.returncode or report.returncode


def start():
    receipt = check()
    if (s.ROOT / "recovery.json").exists():
        archive = s.ROOT / "recovery-history" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        archive.mkdir(parents=True, exist_ok=False)
        for name in ("recovery.json", "supervisor.json", "status.json"):
            if (s.ROOT / name).exists():
                shutil.copy2(s.ROOT / name, archive / name)
    command = ["systemd-run", "--user", "--collect", "--unit=" + UNIT,
               "--property=Restart=no", "--property=KillMode=control-group",
               "--property=WorkingDirectory=" + str(s.REPO),
               "--property=StandardOutput=append:" + str(s.ROOT / "supervisor.log"),
               "--property=StandardError=inherit", sys.executable, "-u", "-m", "seed.s6b10_background", "run"]
    subprocess.run(command, check=True)
    atomic(s.ROOT / "recovery.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["start"]:
        start()
    elif sys.argv[1:] == ["run"]:
        raise SystemExit(run())
    elif sys.argv[1:] == ["check"]:
        print(json.dumps(check()), flush=True)
    else:
        raise SystemExit("use check, start or run")
