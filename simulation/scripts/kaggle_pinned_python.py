"""Prepare exact CPython 3.12.13 inside Kaggle's working directory, bounded.

Uses an existing exact interpreter first, then a checksum-pinned portable uv.
No apt/pip install, system writes, shell installer, or project inputs.
Official instructions: https://docs.astral.sh/uv/guides/install-python/
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request

PIN = "3.12.13"
UV_VERSION = "0.12.23"
UV_URL = ("https://github.com/astral-sh/uv/releases/download/" + UV_VERSION
          + "/uv-x86_64-unknown-linux-gnu.tar.gz")
UV_SHA256 = "9167d72b3319674b6303c4cbe071854bba13ebdf3d76b1a7cbdc175471fb66d6"
VERSION_CODE = (
    "import json,platform,sys;"
    "print(json.dumps(dict(version=platform.python_version(),full_version=sys.version,"
    "executable=sys.executable,isolated=sys.flags.isolated,no_site=sys.flags.no_site,"
    "dont_write_bytecode=sys.dont_write_bytecode)))"
)


def ensure_python(root):
    root = Path(root).resolve()
    if not root.is_relative_to(Path("/kaggle/working")):
        raise ValueError("portable runtime must stay under /kaggle/working")
    root.mkdir(exist_ok=False)
    started = time.monotonic()
    deadline = started + 180
    receipt = dict(schema="echo5.kaggle.python-runtime.v1", requested_python=PIN,
                   scope="runtime setup only", started_unix=time.time(), commands=[],
                   budget_seconds=180, system_install=False, gpu_requested=False)

    def save():
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        temporary = root.parent / "python-runtime.json.partial"
        temporary.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        temporary.replace(root.parent / "python-runtime.json")

    def left():
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("portable interpreter setup budget exhausted")
        return seconds

    def run(argv, seconds=15, env=None):
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, env=env,
                                   start_new_session=True)
        row = dict(argv=argv)
        stdout = stderr = ""
        try:
            stdout, stderr = process.communicate(timeout=min(seconds, left()))
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
            row["interrupted"] = True
            raise
        finally:
            row.update(returncode=process.returncode, stdout=stdout[:12000],
                       stderr=stderr[:12000])
            receipt["commands"].append(row)
            print(json.dumps({"observation": row}), flush=True)
            save()
        return process.returncode, stdout

    def exact_python(candidate):
        code, stdout = run([str(candidate), "-I", "-S", "-B", "-c", VERSION_CODE])
        identity = json.loads(stdout) if code == 0 else {}
        if identity.get("version") != PIN:
            return None
        receipt.update(status="exact_python_ready", identity=identity)
        with Path(candidate).resolve().open("rb") as stream:
            receipt["python_executable_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        save()
        return str(candidate)

    try:
        candidates = [shutil.which("python3.12"), "/usr/bin/python3.12",
                      "/usr/local/bin/python3.12", sys.executable]
        for candidate in dict.fromkeys(x for x in candidates if x):
            if Path(candidate).is_file():
                executable = exact_python(candidate)
                if executable:
                    receipt["route"] = "existing exact interpreter"
                    save()
                    return executable, receipt
        receipt["route"] = "portable uv python-build-standalone"
        receipt["uv"] = dict(version=UV_VERSION, url=UV_URL, archive_sha256=UV_SHA256,
                             checksum_source=UV_URL + ".sha256")
        save()
        archive = root / "uv.tar.gz"
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(UV_URL, timeout=min(20, left())) as response:
            with archive.open("xb") as stream:
                while block := response.read(1024 * 1024):
                    left()
                    size += len(block)
                    if size > 64 * 1024 * 1024:
                        raise ValueError("uv download exceeded 64 MiB bound")
                    digest.update(block)
                    stream.write(block)
        if digest.hexdigest() != UV_SHA256:
            raise ValueError("uv archive checksum mismatch")
        receipt["uv"]["download_bytes"] = size
        with tarfile.open(archive) as bundle:
            member = bundle.getmember("uv-x86_64-unknown-linux-gnu/uv")
            if not member.isfile() or member.size > 150 * 1024 * 1024:
                raise ValueError("unexpected portable uv archive member")
            uv = root / "uv"
            with bundle.extractfile(member) as source, uv.open("xb") as target:
                shutil.copyfileobj(source, target)
            uv.chmod(0o700)
        run([str(uv), "--version"])
        run([str(uv), "python", "list", PIN, "--only-downloads",
             "--output-format", "json", "--no-config"])
        temporary = root / "tmp"
        temporary.mkdir()
        env = dict(os.environ, TMPDIR=str(temporary),
                   UV_CACHE_DIR=str(root / "cache"),
                   UV_PYTHON_BIN_DIR=str(root / "bin"),
                   UV_NO_MODIFY_PATH="1")
        code, _ = run([str(uv), "python", "install", PIN,
                       "--install-dir", str(root / "python"), "--no-bin", "--no-cache",
                       "--no-config", "--no-progress"], seconds=left(), env=env)
        if code:
            raise RuntimeError("uv could not install the exact interpreter")
        candidates = sorted((root / "python").glob("cpython-3.12.13-*/bin/python3.12"))
        for candidate in candidates:
            executable = exact_python(candidate)
            if executable:
                return executable, receipt
        raise RuntimeError("exact installed CPython 3.12.13 executable not found")
    except BaseException as exc:
        receipt.update(status="runtime_setup_failed", error=type(exc).__name__ + ": " + str(exc))
        save()
        raise


def main():
    def timed_out(_signum, _frame):
        raise TimeoutError("runtime probe hard wall timeout")
    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(210)
    try:
        executable, receipt = ensure_python(Path("/kaggle/working/portable-runtime"))
        print(json.dumps(dict(python=executable, receipt=receipt)), flush=True)
        return 0
    except Exception as exc:
        print(type(exc).__name__ + ": " + str(exc), flush=True)
        return 1
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())
