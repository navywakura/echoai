"""MAINT-A mechanism preflight: native execution, source lock, reconstruction.

Scripted witnesses are explicitly not learned/self-model-guided maintenance.
This harness cannot issue a green certificate for E4-MAINTAIN-1.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import persist
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_v3 import binding as v2_binding
from echoai.echo4.dream_v3_bench import development_binding, sources as inherited_sources
from echoai.echo4.maintain_agent import MaintenanceAgent
from echoai.echo4.maintain_world import FAULTS, MaintenanceEnv
from echoai.echo4.world import Body
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT

SCHEMA = "echo4-maintain-a-v1"
PARENT = ROOT / "lab/echo4/dream1-d-v3"
PARENT_DIGEST = "965ce6cbcd759b48a12a9b04080ca5b78e657ab5b9e3869b081b0138ce240f15"
SCRIPTS = {"service_witness": (1, 1, 1, 1, 2),
           "interrupted_control": (1, 1, 2, 1, 2)}


def sources():
    extra = ("echo4/maintain_world.py", "echo4/maintain_agent.py",
             "echo4/maintain_bench.py", "tests/test_echo4_maintain1a.py",
             "docs/ECHO4-MAINTAIN1-A-DESIGN.md")
    return {**inherited_sources(), **{p: file_hash(ROOT / p) for p in extra}}


def parent_binding():
    """Check custody; do not claim a new reconstruction of DREAM or Qwen."""
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    unsigned = dict(report)
    claimed = unsigned.pop("reproduction_sha256")
    if (claimed != PARENT_DIGEST or sha(canonical(unsigned)) != claimed
            or receipt.get("valid") is not True or receipt.get("dream1_green") is not True
            or receipt.get("findings") != [] or receipt.get("reproduction_sha256") != claimed
            or report["sources"] != inherited_sources()
            or report["parent"] != v2_binding() or report["development"] != development_binding()):
        raise ValueError("DREAM-D v3 source/artifact custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


class _ScriptedWitness(MaintenanceAgent):
    """Harness-only proposals. The original Agent/gate execute every tick."""
    def __init__(self, env, script, veto_at=0):
        super().__init__(env)
        self.script, self.veto_at = script, veto_at

    def _propose(self, slot, turn_i, greedy=False):
        if turn_i + 1 == self.veto_at:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return self.script[turn_i]


def trial(initial=Body(64, 96), *, fault="clogged", spares=1, external_heat=0,
          script="service_witness", veto_at=0, stop_at=0, horizon=64):
    env = MaintenanceEnv(initial, fault=fault, spares=spares, external_heat=external_heat)
    if script is None:
        if veto_at:
            raise ValueError("native baseline does not inject a veto")
        agent = MaintenanceAgent(env)
    else:
        agent = _ScriptedWitness(env, SCRIPTS[script], veto_at)
        horizon = len(SCRIPTS[script])
    frames, stop_checked = [], False
    for i in range(horizon):
        if agent.episode_terminal:
            break
        if i + 1 == stop_at:
            agent.operator_stop()
            before = (env.audit_state(), asdict(env.body), agent.life_turns, agent.cam.used)
            try:
                agent.turn(i)
            except RuntimeError:
                stop_checked = before == (env.audit_state(), asdict(env.body), agent.life_turns, agent.cam.used)
            break
        packet_before = agent.observation(env.cell())
        applied = agent.turn(i)
        frames.append({"packet_before": packet_before.hex(),
                       "packet_after": agent.observation(env.cell()).hex(),
                       "proposed": agent.last_proposed_action, "applied": applied,
                       "gate": agent.last_gate_decision, "reward": agent.last_reward,
                       "transition": asdict(env.last_transition),
                       "service": asdict(env.last_service),
                       "registers_match": Body(agent.H, agent.temperature) == env.body,
                       "balanced": env.balanced and env.last_transition.balanced,
                       "spares_balanced": env.spares_balanced})
    metrics = {k: getattr(agent.metrics, k) for k in ("false_facts", "cortex_calls", "destroyed")}
    invariants = (all(r["registers_match"] and r["balanced"] and r["spares_balanced"]
                      and len(bytes.fromhex(r["packet_before"])) == 16
                      and len(bytes.fromhex(r["packet_after"])) == 16 for r in frames)
                  and not any(metrics.values()) and agent.cam.destroyed == 0
                  and env.resets == 0 and agent.life_turns == env.total_steps
                  and agent.sensation.cam is agent.cam and agent.sensation.world is agent.t
                  and agent.boundary.cam is agent.cam)
    return {"context": {"initial": asdict(initial), "fault": fault, "spares": spares,
                        "external_heat": external_heat},
            "script": script, "veto_at": veto_at, "stop_at": stop_at,
            "frames": frames, "final": asdict(env.body), "ledger": env.audit_state(),
            "terminal": agent.episode_terminal, "metrics": metrics,
            "invariants": invariants, "stop_checked": stop_checked}


def evaluate():
    rows = []
    for h, theta, fault, spares, heat in product((32, 64, 96), (64, 80, 96), FAULTS, (0, 1), (0, 4)):
        for script in SCRIPTS:
            rows.append(trial(Body(h, theta), fault=fault, spares=spares,
                              external_heat=heat, script=script))
    summary = {}
    for name in SCRIPTS:
        group = [r for r in rows if r["script"] == name]
        summary[name] = {"episodes": len(group), "terminal": sum(r["terminal"] for r in group),
                         **{k: sum(r["ledger"][k] for r in group) for k in (
                             "steps", "repairs", "services_paid", "service_resource_used",
                             "work_done", "resource_used")}}
    witnesses = {"service": trial(), "veto": trial(veto_at=3), "stop": trial(stop_at=3),
                 "native_q_baseline": trial(script=None)}
    all_rows = rows + list(witnesses.values())
    repaired = witnesses["service"]
    checks = {
        "complete_grid": len(rows) == 216,
        "invariants": all(r["invariants"] for r in all_rows),
        "costed_capacity_recovery": (repaired["ledger"]["repairs"] == 1
                                     and repaired["ledger"]["service_resource_used"] == 6
                                     and repaired["ledger"]["resource_used"] == 19
                                     and repaired["final"] == {"h": 45, "temperature": 72}
                                     and repaired["ledger"]["work_done"] == 1),
        "veto_did_not_service": (witnesses["veto"]["frames"][2]["gate"] == 2
                                  and witnesses["veto"]["frames"][2]["applied"] == 2
                                  and witnesses["veto"]["ledger"]["services_paid"] == 0),
        "operator_stop": witnesses["stop"]["stop_checked"] and witnesses["stop"]["ledger"]["steps"] == 2,
        "irreparable_stays_irreparable": all(r["ledger"]["fault"] == "seized" and r["ledger"]["repairs"] == 0
                                             for r in rows if r["context"]["fault"] == "seized"),
        "external_heat_not_erased": all(r["ledger"]["external_heat"] == r["context"]["external_heat"] for r in rows),
    }
    return {"rows": rows, "summary": summary, "witnesses": witnesses, "checks": checks,
            "mechanism_checks_passed": all(checks.values()), "maintain1_green": False}


def build(directory: Path, *, checking=False):
    manifest, parent = sources(), parent_binding()
    lock = {"schema": SCHEMA, "sources": manifest, "parent": parent,
            "scripts": SCRIPTS, "scope": "development mechanism integrity; not autonomous repair"}
    lock_hash = persist(directory, "lock.json", lock, checking)
    report = {"schema": SCHEMA, "sources": manifest, "parent": parent,
              "lock_sha256": lock_hash, "scope": lock["scope"], **evaluate()}
    if manifest != sources() or parent != parent_binding():
        raise ValueError("sources or parent changed during preflight")
    report["reproduction_sha256"] = sha(canonical(report))
    persist(directory, "report.json", report, checking)
    return report


def verify(directory: Path):
    findings, digest = [], None
    try:
        report = read_json(directory / "report.json")
        digest = report.get("reproduction_sha256")
        rebuilt = build(directory, checking=True)
        if not rebuilt["mechanism_checks_passed"]:
            raise ValueError("mechanism checks failed")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": digest,
            "maintain1_green": False, "scope": "MAINT-A reconstruction only; DREAM custody, no reinference"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "preflight":
        if args.write_receipt:
            parser.error("verify in a separate process before writing a receipt")
        # Never overwrite an earlier run, including a partial failed run.
        args.directory.mkdir(parents=True, exist_ok=False)
        result = build(args.directory)
        print(json.dumps({k: result[k] for k in ("schema", "summary", "checks", "maintain1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["mechanism_checks_passed"] else 1
    result = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
