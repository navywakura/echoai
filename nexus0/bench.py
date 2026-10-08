"""NEXUS-0 bench: 256 turns, policy flip, mild env change. Cortex off."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    BENCH_TURNS,
    ESC_MARGIN,
    PROBE_STEPS,
)
from echoai.nexus0.escalate import LEVEL_Q, LEVEL_SEARCH
from echoai.nexus0.encoder import ATOM_ID, encode, encode_fnv, rel_of, src_of, dst_of
from echoai.nexus0.encoder import _load_bank
from echoai.nexus0.loop import Agent


def encoder_report() -> dict:
    phrases = _load_bank()
    n = len(phrases) or 1
    rel_ok = src_ok = dst_ok = 0
    fnv_rel = 0
    seen = {}
    for row in phrases:
        text = row["text"]
        sem = encode(text)
        fnv = encode_fnv(text)
        want_rel = ATOM_ID[row["rel"]]
        want_src = ATOM_ID[row["src"]]
        want_dst = ATOM_ID[row["dst"]]
        if rel_of(sem) == want_rel:
            rel_ok += 1
        if src_of(sem) == want_src:
            src_ok += 1
        if dst_of(sem) == want_dst:
            dst_ok += 1
        if rel_of(fnv) == want_rel:
            fnv_rel += 1
        seen.setdefault(sem, []).append(text)
    collision = sum(1 for v in seen.values() if len(v) > 1) / n
    return {
        "accuracy_rel": rel_ok / n,
        "accuracy_src": src_ok / n,
        "accuracy_dst": dst_ok / n,
        "semantic_collision": collision,
        "fnv_accuracy_rel": fnv_rel / n,
        "encoder_beats_fnv": (rel_ok / n) > (fnv_rel / n),
        "n_phrases": len(phrases),
    }


def run(plan_depth: int = 0, ask: bool = True, trace: bool = False,
        cortex: bool = False, cortex_log: Optional[str] = None,
        thought_log: Optional[str] = None, escalate: bool = False,
        oracle_path: Optional[str] = None) -> dict:
    """plan_depth 0 is the NEXUS-0/1 bench. Anything else is a side report.

    ask=False is the blind control for the NEXUS-3 gate: same ring, same
    seed, no oracle.
    """
    ag = Agent(plan_depth=plan_depth, ask=ask, trace=trace, cortex=cortex,
               cortex_log=cortex_log, thought_log=thought_log,
               escalate=escalate, oracle_path=oracle_path)
    policy_before = [0, 0, 0]
    ag.run(BENCH_TURNS)
    enc = encoder_report()
    slots = ag.threat_slots()
    policy_after = ag.q.snapshot(slots[0]) if slots else [0, 0, 0]
    a_e = ag.greedy_on(7)
    learned = policy_after[0] < 0 or policy_after[0] < max(policy_after[1], policy_after[2])
    flip = (a_e != ACTION_APPROACH) and learned

    ag.env.move_threat(7, 8)
    for t in range(64):
        ag.turn(BENCH_TURNS + t)
    a_g = ag.greedy_on(8)
    gen = a_g != ACTION_APPROACH

    # Seeking probe last: walk_greedy() keeps learning, so running it here
    # cannot perturb any number already read above. Same point in both arms.
    novel_hits_greedy = ag.walk_greedy(PROBE_STEPS, start=0)

    report = ag.metrics.as_dict()
    report.update(enc)
    report.update(
        {
            "policy_before": policy_before,
            "policy_after": policy_after,
            "negative_delta_causes_policy_change": bool(flip),
            "generalize_moved_threat": bool(gen),
            "phase_e_action": int(a_e),
            "phase_g_action": int(a_g),
            "cortex": bool(cortex),
            "cortex_log": str(cortex_log) if cortex_log else None,
            "thought_log": str(thought_log) if thought_log else None,
            "plan_depth": int(plan_depth),
            "ask": bool(ask),
            "trace": bool(trace),
            "escalate": bool(escalate),
            "oracle_source": ag.oracle.source if ag.oracle else None,
            "oracle_path": str(oracle_path) if oracle_path else None,
            "level_q": int(ag.level_counts.get(LEVEL_Q, 0)),
            "level_search": int(ag.level_counts.get(LEVEL_SEARCH, 0)),
            "esc_margin": int(ESC_MARGIN),
            # The only question worth asking of rung 2 here: when the
            # planner runs, does it say anything Q did not?
            "search_copies_q": int(ag.search_copies_q),
            "search_differs": int(ag.search_differs),
            "search_strictly_better": int(ag.search_strictly_better),
            "novel_hits_greedy": int(novel_hits_greedy),
            "probe_steps": int(PROBE_STEPS),
            "sample_wsp": list(ag.sample_wsp),
        }
    )
    return report


def report_name(plan_depth: int, ask: bool = True, trace: bool = False,
                cortex: bool = False, escalate: bool = False,
                oracle_path: Optional[str] = None) -> str:
    """Opt-in and control runs never overwrite the NEXUS-0/1 report."""
    d = int(plan_depth)
    stem = "nexus0_report" if d <= 0 else f"nexus0_plan{d}_report"
    if not ask:
        stem = stem.replace("_report", "_noask_report")
    if trace:
        stem = stem.replace("_report", "_trace_report")
    if cortex:
        stem = stem.replace("_report", "_cortex_report")
    if escalate:
        stem = stem.replace("_report", "_escalate_report")
    if oracle_path:
        # An outside answerer is a different experiment; the NEXUS-0/1
        # report file must stay the one the default bench wrote.
        stem = stem.replace("_report", "_oracle_report")
    return f"{stem}.json"


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    plan_depth = 0
    if "--plan-depth" in argv:
        plan_depth = int(argv[argv.index("--plan-depth") + 1])
    ask = "--no-ask" not in argv
    trace = "--trace" in argv
    cortex = "--cortex" in argv
    escalate = "--escalate" in argv
    oracle_path = None
    if "--oracle" in argv:
        oracle_path = argv[argv.index("--oracle") + 1]
    lab = Path(__file__).resolve().parents[1] / "lab"
    cortex_log = str(lab / "cortex.jsonl") if cortex else None
    thought_log = str(lab / "thought.jsonl") if "--thought" in argv else None
    for path in (cortex_log, thought_log):
        if path and Path(path).exists():
            Path(path).unlink()  # one run, one log
    report = run(plan_depth=plan_depth, ask=ask, trace=trace, cortex=cortex,
                 cortex_log=cortex_log, thought_log=thought_log,
                 escalate=escalate, oracle_path=oracle_path)
    out = (Path(__file__).resolve().parents[1] / "lab"
           / report_name(plan_depth, ask, trace, cortex, escalate, oracle_path))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    # These three hold in every run, opt-in or not: no invented facts, no
    # destroyed slots, semantic encoder still ahead of FNV.
    ok = (
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["encoder_beats_fnv"]
    )
    if not cortex:
        # cortex_calls == 0 is the invariant for the main bench. The
        # --cortex run exercises the switch on purpose, so it is checked
        # everywhere else instead of being quietly dropped.
        ok = ok and report["cortex_calls"] == 0
    if plan_depth <= 0 and not trace:
        # The NEXUS-0 policy lock applies to the default bench only.
        ok = ok and report["negative_delta_causes_policy_change"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
