"""A consumer that misbehaves on purpose. Never part of the 24 bench runs.

The tick channel is supposed to be inert: an ACK is an acknowledgement,
not a command, and nothing a consumer writes back should reach Gazebo.
This probe tries anyway — extra fields, an oversized body, a wrong
sequence, a service call shaped like an entity spawn — and the
supervisor is expected to record a violation and close the session.

Its sessions are labelled ``adversarial_transport`` in the report so that
a reader never mistakes them for bench evidence.
"""

import json
import os
import sys

MODE = os.environ.get("SIM3_ABUSE", "extra_field")


def main():
    out = sys.stdout.buffer
    n = 0
    for raw in sys.stdin.buffer:
        try:
            msg = json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            break
        seq = int(msg.get("seq", 0))
        if MODE == "extra_field":
            reply = {"v": 1, "ack": seq, "cmd": "create",
                     "entity": {"model": "cheat", "pose": [0, 0, 5]}}
        elif MODE == "oversized":
            reply = {"v": 1, "ack": seq, "pad": "A" * 4096}
        elif MODE == "wrong_seq":
            reply = {"v": 1, "ack": seq + 7}
        elif MODE == "silent":
            n += 1
            continue
        else:
            reply = {"v": 1, "ack": seq}
        out.write(json.dumps(reply, separators=(",", ":")).encode("utf-8") + b"\n")
        out.flush()
        n += 1
    sys.stderr.write(json.dumps({"schema_version": 1, "role": "sim3_abusive",
                                 "mode": MODE, "ticks": n}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
