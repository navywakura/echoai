"""
Qwen-0 operator report — SIGN, canonical + paraphrases, never CI-required.

    PYTHONPATH=. python3 -m echoai.nexus0.qwen_sign

Writes echoai/lab/nexus0_qwen4b_report.json. Does not touch
nexus0_report.json or nexus0_cortex1_report.json.

Without NAVI_QWEN_MODEL / NAVI_QWEN_URL the 4B arm is silence: the
report stays honest (rejected≈calls, CortexROI of the model = 0) and
the stub arm still runs so you can see which paraphrases 20 lines miss.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List

from echoai.nexus0 import sign
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY
from echoai.nexus0.tools import qwen_cortex, sign_cortex

# Canonical strings stay first. The rest are the claim: the stub matches
# "entra" / "no entres"; a 4B has to generalise.
PARAPHRASE: Dict[str, List[str]] = {
    sign.LAYOUT_PRIZE: [
        sign.SIGN_TEXT[sign.LAYOUT_PRIZE],
        "AMBAR: pasa. Lo de adelante es el premio.",
        "El letrero dice que sigas: hay recompensa detrás.",
        "seguro: adelántate, no es una trampa",
    ],
    sign.LAYOUT_TRAP: [
        sign.SIGN_TEXT[sign.LAYOUT_TRAP],
        "AMBAR: detente. Lo de adelante es peligro.",
        "No pases. Lo siguiente mata.",
        "peligro: quédate, no adelantes",
    ],
}


def _cmd_qwen() -> str:
    script = Path(__file__).resolve().parent / "tools" / "qwen_cortex.py"
    return f"{sys.executable} {script}"


def _probe_text(layout: str, text: str, cmd: str) -> dict:
    with sign.cortex_env(cmd):
        from echoai.nexus0.loop import Agent

        ag = Agent(
            cortex=True,
            ask=False,
            env=sign.SignEnv(layout, sign_text=text),
        )
        t0 = time.monotonic()
        a0 = ag.turn(0, greedy=True)
        dt = time.monotonic() - t0
        from echoai.nexus0.types import action_name

        return {
            "layout": layout,
            "sign": text,
            "action": action_name(a0),
            "action_id": int(a0),
            "reward": int(ag.env.last_reward),
            "cortex_calls": ag.metrics.cortex_calls,
            "cortex_rejected": ag.metrics.cortex_rejected,
            "cortex_actions": ag.metrics.cortex_actions,
            "questions": ag.metrics.questions,
            "false_facts": ag.metrics.false_facts,
            "seconds": round(dt, 4),
            "stub_line": sign_cortex.decide(text),
            "should_speak": qwen_cortex.should_speak(text),
        }


def _fast(layout: str, text: str) -> dict:
    from echoai.nexus0.loop import Agent
    from echoai.nexus0.types import action_name

    with sign.cortex_env(None):
        ag = Agent(
            cortex=False, ask=False, env=sign.SignEnv(layout, sign_text=text)
        )
        a0 = ag.turn(0, greedy=True)
        return {
            "action": action_name(a0),
            "reward": int(ag.env.last_reward),
        }


def experiment() -> dict:
    host = {
        "node": platform.node(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "quant": "Q4_K_M",
        "model": os.environ.get("NAVI_QWEN_MODEL", ""),
        "url": os.environ.get("NAVI_QWEN_URL", ""),
        "timeout_s": os.environ.get("NAVI_CORTEX_TIMEOUT", "10"),
    }
    qwen_cmd = _cmd_qwen()
    stub_cmd = sign.cortex_cmd()

    rows: List[dict] = []
    for layout, texts in PARAPHRASE.items():
        for text in texts:
            fast = _fast(layout, text)
            stub = _probe_text(layout, text, stub_cmd)
            qwen = _probe_text(layout, text, qwen_cmd)
            want = "approach" if layout == sign.LAYOUT_PRIZE else "avoid"
            rows.append(
                {
                    "layout": layout,
                    "sign": text,
                    "canonical": text == sign.SIGN_TEXT[layout],
                    "fast_action": fast["action"],
                    "fast_reward": fast["reward"],
                    "stub_action": stub["action"],
                    "qwen_action": qwen["action"],
                    "qwen_reward": qwen["reward"],
                    "want": want,
                    "stub_hit": stub["action"] == want,
                    "qwen_hit": qwen["action"] == want,
                    "qwen_rejected": qwen["cortex_rejected"],
                    "qwen_calls": qwen["cortex_calls"],
                    "qwen_seconds": qwen["seconds"],
                    "false_facts": stub["false_facts"] + qwen["false_facts"],
                    "stub_line": stub["stub_line"],
                }
            )

    canonical = [r for r in rows if r["canonical"]]
    extra = [r for r in rows if not r["canonical"]]

    prize_can = next(r for r in canonical if r["layout"] == sign.LAYOUT_PRIZE)
    trap_can = next(r for r in canonical if r["layout"] == sign.LAYOUT_TRAP)

    qwen_calls = sum(r["qwen_calls"] for r in rows)
    qwen_rej = sum(r["qwen_rejected"] for r in rows)
    qwen_secs = [r["qwen_seconds"] for r in rows if r["qwen_calls"]]

    out: Dict[str, object] = {
        "world": "sign-qwen",
        "host": host,
        "cells": 2,
        "sign_wsp_hex": encode_cell(sign.SIGN, KIND_EMPTY).hex(),
        "rows": rows,
        "canonical_prize_qwen_action": prize_can["qwen_action"],
        "canonical_trap_qwen_action": trap_can["qwen_action"],
        "canonical_prize_fast_action": prize_can["fast_action"],
        "canonical_trap_fast_action": trap_can["fast_action"],
        "CortexROI_canonical": (
            int(prize_can["qwen_reward"]) - int(prize_can["fast_reward"])
        ),
        "stub_hits": sum(1 for r in rows if r["stub_hit"]),
        "qwen_hits": sum(1 for r in rows if r["qwen_hit"]),
        "paraphrase_stub_hits": sum(1 for r in extra if r["stub_hit"]),
        "paraphrase_qwen_hits": sum(1 for r in extra if r["qwen_hit"]),
        "paraphrase_n": len(extra),
        "qwen_calls": qwen_calls,
        "qwen_rejected": qwen_rej,
        "latency_s_mean": (
            round(sum(qwen_secs) / len(qwen_secs), 4) if qwen_secs else None
        ),
        "false_facts": sum(r["false_facts"] for r in rows),
        "model_configured": bool(
            host["model"] or host["url"]
        ),
    }
    out["qwen_beats_stub_on_paraphrase"] = (
        int(out["paraphrase_qwen_hits"]) > int(out["paraphrase_stub_hits"])
    )
    out["green"] = green(out)
    return out


def green(report: dict) -> bool:
    """Operator green: 4B present, canonical SIGN, paraphrases > stub, 0 facts.

    If the model is not configured this is False on purpose — silence is
    not a CortexROI.
    """
    return bool(
        report["model_configured"]
        and report["false_facts"] == 0
        and report["canonical_prize_fast_action"] == "wait"
        and report["canonical_trap_fast_action"] == "wait"
        and report["canonical_prize_qwen_action"] == "approach"
        and report["canonical_trap_qwen_action"] == "avoid"
        and report["CortexROI_canonical"] > 0
        and report["qwen_calls"] > 0
        and report["qwen_rejected"] < report["qwen_calls"]
        and report["qwen_beats_stub_on_paraphrase"]
    )


def main(argv=None) -> int:
    report = experiment()
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_qwen4b_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
