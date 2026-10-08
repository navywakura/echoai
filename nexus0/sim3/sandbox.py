"""The consumer's cage, and the one wire that leaves it.

The isolation here is a mount/network/PID namespace built by bubblewrap,
not a Python object that declines to expose an attribute. The consumer
gets a read-only /usr, an empty tmpfs working directory, its own copy of
/proc, and this file. It does not get the repository, ``lab/``, the
package, the suite, the supervisor's environment or argv, a network
namespace with a route, or any sibling process to look at.

Two file descriptors carry everything: stdin/stdout is a preopened
socketpair (the tick channel), stderr is a one-way report to the
evaluator. There is no third.

This closes accidental leaks and direct access by the probe. It is not a
claim about kernel escapes or timing side channels, and the report says
so. If bubblewrap is absent or the kernel refuses the namespaces, the
isolation group is ``not_run`` — a mocked permission is not a permission.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from echoai.nexus0.sim3.canon import Sim3Error
from echoai.nexus0.sim3.runtime import (
    PROBE,
    SANDBOX_ARGV,
    SANDBOX_ENV,
    SANDBOX_ENV_EXPECTED,
    SANDBOX_HOSTNAME,
    Runtime,
)

GUEST_PROBE = "/probe/probe.py"


def bwrap_argv(probe_path: Path, extra_env: Optional[Dict[str, str]] = None
               ) -> List[str]:
    """The sandbox command line. Identical for every world, by construction."""
    env = dict(SANDBOX_ENV)
    env.update(extra_env or {})
    argv = [
        "bwrap",
        "--die-with-parent", "--new-session",
        "--unshare-user", "--unshare-ipc", "--unshare-pid",
        "--unshare-net", "--unshare-uts", "--unshare-cgroup",
        "--hostname", SANDBOX_HOSTNAME,
        "--clearenv",
    ]
    for key in sorted(env):
        argv += ["--setenv", key, env[key]]
    argv += [
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/lib64", "/lib64",
        "--symlink", "usr/sbin", "/sbin",
        "--ro-bind", str(probe_path), GUEST_PROBE,
        "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/work", "--chdir", "/work",
        # Everything but /work is read-only, and the consumer itself is
        # pid 1: without --as-pid-1 the reaper bwrap leaves behind is pid
        # 1, and /proc/1/cmdline hands the consumer the supervisor's
        # command line — including the absolute path of this repository.
        "--remount-ro", "/",
        "--as-pid-1",
        "--",
    ] + SANDBOX_ARGV
    return argv


@dataclass
class Consumer:
    process: subprocess.Popen
    sock: socket.socket
    argv: List[str]

    def close(self) -> None:
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
        if self.process.stderr is not None and not self.process.stderr.closed:
            try:
                self.process.stderr.close()
            except OSError:
                pass


def spawn(runtime: Runtime, *, probe_path: Optional[Path] = None,
          extra_env: Optional[Dict[str, str]] = None) -> Consumer:
    """Start the consumer. Raises if the sandbox tool is not present."""
    if not runtime.lock.get("sandbox", {}).get("path"):
        raise Sim3Error("sandbox_unavailable", "bwrap not found in the lock")
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    argv = bwrap_argv(Path(probe_path or PROBE), extra_env)
    argv[0] = runtime.lock["sandbox"]["path"]
    try:
        proc = subprocess.Popen(
            argv,
            stdin=child.fileno(),
            stdout=child.fileno(),
            stderr=subprocess.PIPE,
            close_fds=True,
            start_new_session=False,
        )
    finally:
        child.close()
    return Consumer(process=proc, sock=parent, argv=argv)


def self_test(runtime: Runtime) -> Dict:
    """Prove the namespaces actually applied before trusting them.

    Runs a throwaway command inside the same cage and reports what it
    saw. If this comes back wrong the bench refuses to call anything
    isolated.
    """
    if not runtime.lock.get("sandbox", {}).get("path"):
        return {"ok": False, "reason": "bwrap not found"}
    argv = bwrap_argv(PROBE)
    argv[0] = runtime.lock["sandbox"]["path"]
    argv[-2:] = ["/usr/bin/python3", "-c", (
        "import os,json,socket;"
        "w=None;"
        "\ntry:\n open('/probe/escape','w')\nexcept OSError as e: w=e.errno\n"
        "print(json.dumps({"
        "'root': sorted(os.listdir('/')),"
        "'has_home': os.path.exists('/home'),"
        "'has_run': os.path.exists('/run'),"
        "'env': dict(os.environ),"
        "'hostname': socket.gethostname(),"
        "'readonly_errno': w,"
        "'pid1': open('/proc/1/cmdline','rb').read().decode().split(chr(0))[:-1],"
        "'procs': sorted(p for p in os.listdir('/proc') if p.isdigit()),"
        "}))"
    )]
    proc = subprocess.run(argv, capture_output=True, timeout=60)
    if proc.returncode != 0:
        return {"ok": False, "reason": proc.stderr.decode()[-300:]}
    seen = json.loads(proc.stdout.decode())
    ok = (
        not seen["has_home"] and not seen["has_run"]
        and seen["hostname"] == SANDBOX_HOSTNAME
        and set(seen["env"]) == set(SANDBOX_ENV_EXPECTED)
        and seen["procs"] == ["1"]
        and seen["pid1"][:1] == ["/usr/bin/python3"]
        and seen["readonly_errno"] == 30          # EROFS
    )
    return {"ok": ok, "seen": seen}
