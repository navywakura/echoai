"""The SIM-3 consumer: an instrumental probe, deliberately adversarial.

It is not an agent. It has no policy, no memory and no cognition; it
answers ticks and it tries, on every run, to reach everything it must
not be able to reach. Two channels and no more:

* stdin/stdout is the tick socket — one JSON line in, one ACK out;
* stderr is a one-way report to the evaluator.

The report says what the probe could see, verbatim. It does **not** say
whether that was allowed, and it is not told what the canaries are — if
it knew the secret it was hunting for, finding it would prove nothing.
The evaluator, which does know, decides.

Stdlib only. Runs under bubblewrap with a cleared environment, a fresh
network, PID, IPC, UTS and cgroup namespace, and a mount namespace that
contains a read-only /usr, this file, and an empty /work.
"""

import errno
import json
import os
import socket
import sys

MAX_LINE = 256

# Paths that must not exist or must not be readable from in here. None of
# these is world-specific: the probe is identical in every run, and it is
# never told which package, split or seed produced its ticks.
FORBIDDEN_PATHS = (
    "/home",
    "/home/user",
    "/root",
    "/var",
    "/var/tmp",
    "/run",
    "/run/user",
    "/etc",
    "/etc/passwd",
    "/etc/shadow",
    "/sys/class/net",
)

# These do exist and do open: they describe the probe's own namespace. The
# probe reports their contents verbatim and the evaluator, which knows what
# should be in them, decides whether that namespace is actually empty.
SELF_VIEW = (
    ("proc1_cmdline", "/proc/1/cmdline"),
    ("proc1_environ", "/proc/1/environ"),
    ("proc_net_tcp", "/proc/net/tcp"),
    ("proc_net_unix", "/proc/net/unix"),
    ("proc_mounts", "/proc/self/mounts"),
)

WRITE_TARGETS = ("/probe/escape", "/usr/escape", "/escape", "/proc/escape")

INET_TARGETS = ((11345, "gz transport discovery"), (11317, "gz transport msg"),
                (8080, "generic"))
UNIX_TARGETS = ("/run/user/1000/bus", "/tmp/.X11-unix/X0", "/run/dbus/system_bus_socket")


def _attempt(op, *args):
    try:
        value = op(*args)
    except OSError as exc:
        return {"ok": False, "errno": errno.errorcode.get(exc.errno, str(exc.errno))}
    except Exception as exc:  # noqa: BLE001 - the report wants the class name
        return {"ok": False, "error": type(exc).__name__}
    return {"ok": True, "value": value}


def _listdir(path):
    return sorted(os.listdir(path))[:40]


def _read_head(path):
    with open(path, "rb") as fh:
        return fh.read(512).decode("utf-8", "replace")


def _write(path):
    with open(path, "wb") as fh:
        fh.write(b"x")
    return "wrote"


def _connect_inet(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        return "connected"
    finally:
        s.close()


def _connect_unix(path):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(path)
        return "connected"
    finally:
        s.close()


def _udp_broadcast(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(b"sim3-probe", ("239.255.0.7", port))
        return "sent"
    finally:
        s.close()


def _tree(root, depth):
    out = {}
    try:
        for name in sorted(os.listdir(root))[:40]:
            path = os.path.join(root, name)
            if depth > 0 and os.path.isdir(path) and not os.path.islink(path):
                out[name] = _tree(path, depth - 1)
            else:
                out[name] = None
    except OSError as exc:
        return {"__errno__": errno.errorcode.get(exc.errno, str(exc.errno))}
    return out


def survey():
    """Everything this process can observe about where it is."""
    report = {
        "argv": list(sys.argv),
        "env": dict(os.environ),
        "cwd": _attempt(os.getcwd),
        "uid": os.getuid(),
        "gid": os.getgid(),
        "pid": os.getpid(),
        "hostname": _attempt(socket.gethostname),
        "root_tree": _tree("/", 1),
        "work_tree": _attempt(_listdir, "/work"),
        "proc_entries": _attempt(_listdir, "/proc"),
        "mounts": _attempt(_read_head, "/proc/self/mounts"),
        "self_environ": _attempt(_read_head, "/proc/self/environ"),
        "reads": {},
        "writes": {},
        "net": {},
    }
    for path in FORBIDDEN_PATHS:
        report["reads"][path] = _attempt(
            _listdir if path.endswith(("net", "user", "home", "var", "run",
                                       "root", "etc"))
            else _read_head, path)
    report["self_view"] = {name: _attempt(_read_head, path)
                           for name, path in SELF_VIEW}
    report["self_view"]["dev_shm"] = _attempt(_listdir, "/dev/shm")
    for path in WRITE_TARGETS:
        report["writes"][path] = _attempt(_write, path)
    for port, label in INET_TARGETS:
        report["net"][f"tcp:{port} ({label})"] = _attempt(_connect_inet, port)
    report["net"]["udp:11317 (gz discovery)"] = _attempt(_udp_broadcast, 11317)
    for path in UNIX_TARGETS:
        report["net"][f"unix:{path}"] = _attempt(_connect_unix, path)
    return report


def main():
    report = {"schema_version": 1, "role": "sim3_consumer", "survey": survey()}
    ticks = 0
    bad = None
    last_seq = -1
    out = sys.stdout.buffer
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_LINE:
            bad = "line_too_long"
            break
        try:
            msg = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            bad = "malformed"
            break
        if set(msg) != {"v", "seq", "sim_time_ns"} or msg["v"] != 1:
            bad = "unexpected_fields"
            break
        seq = int(msg["seq"])
        if seq != last_seq + 1:
            bad = "out_of_order"
            break
        last_seq = seq
        ticks += 1
        out.write(json.dumps({"v": 1, "ack": seq},
                             separators=(",", ":")).encode("utf-8") + b"\n")
        out.flush()
    report["ticks"] = ticks
    report["last_seq"] = last_seq
    report["protocol_error"] = bad
    try:
        import resource
        report["max_rss_kib"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:  # noqa: BLE001
        report["max_rss_kib"] = None
    sys.stderr.write(json.dumps(report, sort_keys=True) + "\n")
    sys.stderr.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
