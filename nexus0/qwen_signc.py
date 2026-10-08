"""
Qwen-0 operator report — SIGN-C, canonical + paraphrases, never CI-required.

    PYTHONPATH=. python3 -m echoai.nexus0.qwen_signc

Writes echoai/lab/nexus0_qwen_signc_report.json and nothing else. It does
not touch nexus0_report.json, nexus0_signc_report.json,
nexus0_world3_report.json, nexus0_cortex1_report.json or
nexus0_qwen4b_report.json.

What the deterministic runner in `signc.py` closes is the *mechanism*: a
contradiction wakes the slow clock, once, with the origin's sentence, and
the atom that comes back is spent on the next turn. What it cannot close
is that the thing on the other end of the cable reads **language**. The
CI stub matches five words of Spanish; a paraphrase it has never seen is
silence. This harness runs the same bench with a local 4B in the same
socket and reports how many paraphrases each one gets.

The prompt the 4B receives is the sign and nothing else — no graph, no
node list, no route, no kinds. One atom comes back. There is no API here
with which it could choose a detour: the only thing it can do is read a
sentence and name a verb, and the gate still has the last word.

Without NAVI_QWEN_MODEL / NAVI_QWEN_URL the 4B arm is silence and the
report says so: `model_configured` is false and `green` is false. Silence
is not a CortexROI.

The 4B is constrained to `cortex_action.gbnf` for these calls and these
only: `YO → {UNIR | TEMER | OBSERVAR | NONE} → AQUI @AHORA`. The general
`cortex.gbnf` is untouched and is what every other consumer still gets.
The first real run needed it — asked what the hazard sign meant, the model
answered `AMOR → CAMBIAR → TEMER @AHORA`, which parses, is a fair reading,
and is not an action: `loop` proposes on the **rel**, and TEMER was in DST.
`qwen_rejected` was 0 and the gate was red anyway. The report records the
grammar's path and hash, and `green()` recomputes them.

What is graded is the **atom**, never the body. `gate` turns a proposed
`wait` at a hazard into `avoid` on its own, so the action alone credits a
cortex that said the wrong verb — or nothing at all — with the reflex's
+8. Every row therefore carries `*_proposal` and `*_action` as separate
keys, and `green()` keys on the proposal in both directions.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Dict, List

from echoai.nexus0 import signc
from echoai.nexus0.env import KIND_GOAL, KIND_THREAT
from echoai.nexus0.tools import qwen_cortex, signc_cortex

# Canonical first. The rest are the claim: the stub matches "entra" /
# "retrocede" and nothing else, so a sentence that says the same thing in
# other words is a sentence only a reader can follow.
PARAPHRASE: Dict[str, List[str]] = {
    "goal": [
        signc.SIGN_TEXT,
        "AMBAR: invirtieron la palanca; el peligro de ayer es el premio de hoy.",
        "El mecanismo se dio la vuelta: lo de delante recompensa en vez de morder.",
        "AMBAR: cambiaron el sentido. Lo que antes era trampa hoy da recompensa.",
    ],
    "threat": [
        signc.SIGN_TEXT_RETREAT,
        "AMBAR: invirtieron la palanca; el premio de ayer es el peligro de hoy.",
        "El mecanismo se dio la vuelta: lo de delante muerde en vez de recompensar.",
        "AMBAR: cambiaron el sentido. Lo que antes era premio hoy es una trampa.",
    ],
}

# What each landing kind makes the right verb. Not read by the model and
# not in its prompt: it is the answer key this report grades against.
WANT = {"goal": "approach", "threat": "avoid"}
KIND = {"goal": KIND_GOAL, "threat": KIND_THREAT}


def cortex_cmd() -> str:
    script = Path(__file__).resolve().parent / "tools" / "qwen_cortex.py"
    return f"{sys.executable} {script}"


# The operator-side grammar. `cortex.gbnf` stays the general WSP contract
# and is not touched — a cortex that can only name actions cannot think
# anything else, and Qwen-0 and every other consumer of `qwen_cortex.py`
# keep using it. This one asks the narrower question this report scores.
ACTION_GBNF = Path(__file__).resolve().parent / "cortex_action.gbnf"
GENERAL_GBNF = Path(__file__).resolve().parent / "cortex.gbnf"
ENV_GBNF = "NAVI_QWEN_GBNF"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextlib.contextmanager
def action_grammar():
    """Constrain the wrapper to an action, for these calls and no others.

    Set around the 4B arm only, and restored in `finally` — a row that
    raises must not leave the operator's shell, or the next slice's run,
    pointed at SIGN-C's grammar. An unset variable is restored to unset,
    not to the empty string, because `qwen_cortex._gbnf_path()` treats a
    blank value as "use the default" and the two must not be conflated.
    """
    old = os.environ.get(ENV_GBNF)
    os.environ[ENV_GBNF] = str(ACTION_GBNF)
    try:
        yield str(ACTION_GBNF)
    finally:
        if old is None:
            os.environ.pop(ENV_GBNF, None)
        else:
            os.environ[ENV_GBNF] = old


def _row(world: str, text: str, stub_cmd: str, qwen_cmd: str) -> dict:
    kind = KIND[world]
    fast = signc.arm("fast", None, landing_kind=kind, sign_text=text)
    stub = signc.arm("stub", stub_cmd, cortex_on=True, conflict_on=True,
                     landing_kind=kind, sign_text=text)
    with action_grammar():
        t0 = time.monotonic()
        qwen = signc.arm("qwen", qwen_cmd, cortex_on=True, conflict_on=True,
                         landing_kind=kind, sign_text=text)
        dt = time.monotonic() - t0
    want = WANT[world]

    def proposal(a: dict):
        """The verb the slow clock named, or None if it named none.

        Straight off the consuming turn's diary line: `cortex_action` is
        null on the turn that asks and the proposal on the turn that
        spends it. Not the body's move — see `hit()`.
        """
        return a["consume_line"]["cortex_action"]

    def hit(a: dict) -> bool:
        """Did the *slow clock* name the right verb?

        Not "was the atom consumed", and not "did the body do the right
        thing". Both of those were wrong here, in that order:

        - Grading the action alone credited silence: at a hazard landing
          the gate turns a proposed `wait` into `avoid` by itself
          (`u >= U_SHORT`), so a cortex that said nothing scored `avoid`
          for free on every threat row.
        - Requiring the atom to be consumed fixed silence and nothing
          else. `OBSERVAR` parses, is consumed, proposes `wait` — the
          wrong verb — and the very same gate rule turns that `wait` into
          `avoid` and pays +8. It scored as a hit. The gate's reflex was
          being credited to the reader.

        So the comparison is against the proposal. `UNIR` and silence
        already failed under the old rule; `OBSERVAR` is the reply that
        separates "it spoke" from "it named the right verb", and it is the
        mutant this gate is built around.
        """
        return bool(a["proposal_consumed_next_turn"] and proposal(a) == want)

    return {
        "world": world,
        "sign": text,
        "canonical": text == PARAPHRASE[world][0],
        "want": want,
        "attend_reason": qwen["attend_reason"],
        "conflict_wakes": qwen["conflict_wakes"],
        "fast_action": fast["action_at_landing"],
        "fast_reward": fast["reward_at_landing"],
        # Two different facts, two different keys. The atom the slow
        # clock named, and what the body actually did once the gate had
        # had its say — they differ on exactly the rows that matter.
        "stub_proposal": proposal(stub),
        "stub_action": stub["action_at_landing"],
        "stub_spoke": stub["proposal_consumed_next_turn"],
        "stub_hit": hit(stub),
        "qwen_proposal": proposal(qwen),
        "qwen_action": qwen["action_at_landing"],
        "qwen_spoke": qwen["proposal_consumed_next_turn"],
        "qwen_reward": qwen["reward_at_landing"],
        "qwen_hit": hit(qwen),
        "qwen_calls": qwen["cortex_calls"],
        "qwen_rejected": qwen["cortex_rejected"],
        "qwen_seconds": round(dt, 4),
        "stub_line": signc_cortex.decide(text),
        "should_speak": qwen_cortex.should_speak(text),
        "false_facts": stub["false_facts"] + qwen["false_facts"],
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
    stub_cmd = signc.cortex_cmd()
    qwen_cmd = cortex_cmd()

    rows: List[dict] = []
    for world, texts in PARAPHRASE.items():
        for text in texts:
            rows.append(_row(world, text, stub_cmd, qwen_cmd))

    canonical = {r["world"]: r for r in rows if r["canonical"]}
    extra = [r for r in rows if not r["canonical"]]
    goal = canonical["goal"]

    secs = [r["qwen_seconds"] for r in rows if r["qwen_calls"]]
    out: Dict[str, object] = {
        "world": "signc-qwen",
        "host": host,
        "base": "signc",
        "landing_node": signc.LANDING_NODE,
        "fork_node": signc.SIGN_NODE,
        "rows": rows,
        # Which grammar the 4B was actually constrained to, by path and by
        # content. A run made by accident with the general grammar records
        # the other hash and `green()` refuses it — the field is not a
        # label, it is the file.
        "action_grammar": True,
        "action_grammar_path": str(ACTION_GBNF),
        "action_grammar_name": ACTION_GBNF.name,
        "action_grammar_sha256": _sha256(ACTION_GBNF),
        "general_grammar_name": GENERAL_GBNF.name,
        "general_grammar_sha256": _sha256(GENERAL_GBNF),
        # The KPI turn: the landing node, with the atom the conflict wake
        # brought back. Named for the node WORLD-3 calls X.
        "attend_reason": goal["attend_reason"],
        "conflict_wakes": goal["conflict_wakes"],
        # `_proposal_` is what the 4B said; `_action_` is what the body
        # did. `CortexROI` and the `_at_X` action stay as descriptions of
        # the body, because that is what the world paid for.
        "qwen_proposal_at_X": goal["qwen_proposal"],
        "qwen_action_at_X": goal["qwen_action"],
        "qwen_reward_at_X": goal["qwen_reward"],
        "fast_action_at_X": goal["fast_action"],
        "fast_reward_at_X": goal["fast_reward"],
        "CortexROI": int(goal["qwen_reward"]) - int(goal["fast_reward"]),
        "canonical_threat_qwen_proposal": canonical["threat"]["qwen_proposal"],
        "canonical_threat_qwen_action": canonical["threat"]["qwen_action"],
        "canonical_threat_fast_action": canonical["threat"]["fast_action"],
        "stub_hits": sum(1 for r in rows if r["stub_hit"]),
        "qwen_hits": sum(1 for r in rows if r["qwen_hit"]),
        "paraphrase_stub_hits": sum(1 for r in extra if r["stub_hit"]),
        "paraphrase_qwen_hits": sum(1 for r in extra if r["qwen_hit"]),
        "paraphrase_n": len(extra),
        "qwen_calls": sum(r["qwen_calls"] for r in rows),
        "qwen_rejected": sum(r["qwen_rejected"] for r in rows),
        "latency_s_mean": round(sum(secs) / len(secs), 4) if secs else None,
        "false_facts": sum(r["false_facts"] for r in rows),
        "model_configured": bool(host["model"] or host["url"]),
    }
    # The proposals, counted by world, so a partial run reads as a number
    # rather than as a verdict. Nothing in `green()` requires these to be
    # perfect: the misses are the measurement.
    out["qwen_proposals"] = {
        world: [r["qwen_proposal"] for r in rows if r["world"] == world]
        for world in PARAPHRASE
    }
    out["qwen_beats_stub_on_paraphrase"] = bool(
        int(out["paraphrase_qwen_hits"]) > int(out["paraphrase_stub_hits"])
    )
    out["green"] = green(out)
    return out


def green(report: dict) -> bool:
    """Operator green: the 4B is present, the mechanism is the conflict,
    and the model reads sentences the twelve words of the stub do not."""
    return bool(
        report["model_configured"]
        and report["false_facts"] == 0
        # The output schema this report is about. Recomputed from the file,
        # so a run that says `action_grammar` while carrying the general
        # grammar's hash — or a stale hash of an edited file — is refused.
        and report.get("action_grammar") is True
        and report.get("action_grammar_name") == ACTION_GBNF.name
        and report.get("action_grammar_sha256") == _sha256(ACTION_GBNF)
        and report.get("action_grammar_sha256")
        != report.get("general_grammar_sha256")
        and report["attend_reason"] == "conflict"
        and report["conflict_wakes"] == 1
        and report["qwen_calls"] > 0
        and report["qwen_rejected"] < report["qwen_calls"]
        # The verbs the 4B named, in both directions. Neither the body's
        # action nor a positive reward is enough: at a hazard the gate
        # produces `avoid` off a wrong atom and off no atom at all, so a
        # gate keyed on the action would pass a model that never read the
        # sentence.
        and report["qwen_proposal_at_X"] == "approach"
        and report["canonical_threat_qwen_proposal"] == "avoid"
        # And the world still paid for it.
        and report["qwen_action_at_X"] == "approach"
        and report["fast_action_at_X"] == "wait"
        and report["CortexROI"] > 0
        and report["qwen_beats_stub_on_paraphrase"]
    )


def main(argv=None) -> int:
    report = experiment()
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_qwen_signc_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
