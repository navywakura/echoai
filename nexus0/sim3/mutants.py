"""Mutants: every refusal must be provoked from a control that passed.

The rule SIM3-DESIGN.md §6 insists on is easy to violate by accident:
checking that an already-red report is still red proves nothing. So each
mutant here starts from a *positive control* — a package, a session or a
seal that has just been verified to work — applies exactly one defect,
and requires the failure to name that defect. A mutant that fails for the
wrong reason is recorded as a failure of the mutant, not as a success.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

from echoai.nexus0.sim3 import metamorph, sandbox, seal as sealmod
from echoai.nexus0.sim3.canon import (
    MAX_FILE_BYTES,
    Sim3Error,
    canonical_bytes,
    loads_strict,
    sha256_bytes,
)
from echoai.nexus0.sim3.pkg import Protocol, load_package
from echoai.nexus0.sim3.runtime import PROBE_ABUSIVE, Runtime
from echoai.nexus0.sim3.session import run_episode

ASSETS = Path(__file__).resolve().parent / "assets"
FROZEN_RUNNER = ASSETS / "gzrunner_frozen.py"


def canaries(run_id: str) -> Dict[str, str]:
    """Distinct private tokens per run, planted where a leak would show."""
    def token(kind: str) -> str:
        digest = hashlib.sha256(f"SIM3/canary/{kind}/{run_id}".encode()).hexdigest()
        return f"SIM3CANARY{kind.upper()}{digest[:24]}"
    return {"env": token("env"), "argv": token("argv"), "file": token("file")}


# --- package mutants -------------------------------------------------------

def _copy(src: Path, dst: Path) -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)
    return dst


def _rewrite_manifest(pkg: Path, mutate: Callable[[Dict], Dict]) -> None:
    data = loads_strict((pkg / "manifest.json").read_bytes(), code="manifest")
    (pkg / "manifest.json").write_bytes(canonical_bytes(mutate(data)) + b"\n")


def _rewrite_sdf(pkg: Path, data: bytes, *, fix_hash: bool = True) -> None:
    (pkg / "world.sdf").write_bytes(data)
    if fix_hash:
        _rewrite_manifest(pkg, lambda m: {**m, "sdf": {**m["sdf"],
                                                       "sha256": sha256_bytes(data)}})


def _m_sdf_hash(pkg: Path) -> None:
    raw = (pkg / "world.sdf").read_bytes()
    (pkg / "world.sdf").write_bytes(raw.replace(b"<gravity>", b"<gravity >", 1)
                                    if b"<gravity >" not in raw else raw + b"\n")


def _m_role_absent(pkg: Path) -> None:
    _rewrite_manifest(pkg, lambda m: {
        **m, "roles": m["roles"] + [{"model": "m99", "role": "barrier"}]})


def _m_role_missing(pkg: Path) -> None:
    _rewrite_manifest(pkg, lambda m: {**m, "roles": m["roles"][:-1]})


def _m_role_duplicate(pkg: Path) -> None:
    _rewrite_manifest(pkg, lambda m: {
        **m, "roles": m["roles"] + [{"model": m["roles"][0]["model"],
                                     "role": "barrier"}]})


def _m_json_duplicate_key(pkg: Path) -> None:
    raw = (pkg / "manifest.json").read_bytes().decode()
    raw = raw.replace('{"profile"', '{"profile":"sim3-boxes-v1","profile"', 1)
    (pkg / "manifest.json").write_bytes(raw.encode())


def _m_leaked_seed(pkg: Path) -> None:
    _rewrite_manifest(pkg, lambda m: {**m, "seed": 7, "split": "C"})


def _m_remote_include(pkg: Path) -> None:
    raw = (pkg / "world.sdf").read_bytes()
    inject = (b"    <include><uri>https://fuel.gazebosim.org/1.0/OpenRobotics/"
              b"models/Construction%20Cone</uri></include>\n")
    _rewrite_sdf(pkg, raw.replace(b"  </world>", inject + b"  </world>", 1))


def _m_injected_plugin(pkg: Path) -> None:
    raw = (pkg / "world.sdf").read_bytes()
    inject = (b'    <plugin filename="libcheat.so" name="cheat::Leak"/>\n')
    _rewrite_sdf(pkg, raw.replace(b"  </world>", inject + b"  </world>", 1))


def _m_xml_dtd(pkg: Path) -> None:
    raw = (pkg / "world.sdf").read_bytes()
    dtd = b'<!DOCTYPE sdf [<!ENTITY leak SYSTEM "file:///etc/passwd">]>\n'
    idx = raw.index(b"<sdf")
    _rewrite_sdf(pkg, raw[:idx] + dtd + raw[idx:])


def _m_symlink_escape(pkg: Path) -> None:
    target = pkg / "world.sdf"
    outside = pkg.parent / "outside_world.sdf"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)


def _m_spawn_in_solid(pkg: Path) -> None:
    manifest = loads_strict((pkg / "manifest.json").read_bytes(), code="manifest")
    barrier = next(r["model"] for r in manifest["roles"] if r["role"] == "barrier")
    raw = (pkg / "world.sdf").read_text()
    marker = f'<model name="{barrier}">'
    pose_line = raw.index("<pose>", raw.index(marker))
    end = raw.index("</pose>", pose_line)
    x, y, z = raw[pose_line + 6:end].split()[:3]
    _rewrite_manifest(pkg, lambda m: {
        **m, "spawn_mm": [int(float(x) * 1000), int(float(y) * 1000),
                          m["spawn_mm"][2]]})


def _m_oversize(pkg: Path) -> None:
    raw = (pkg / "world.sdf").read_bytes()
    padding = b"<!-- " + b"p" * (MAX_FILE_BYTES + 16) + b" -->\n"
    _rewrite_sdf(pkg, padding + raw)


def _wall(name: str, pose, size) -> str:
    px, py, pz = (f"{v / 1000:g}" for v in pose)
    sx, sy, sz = (f"{v / 1000:g}" for v in size)
    return (f'    <model name="{name}">\n'
            f"      <static>true</static>\n"
            f"      <pose>{px} {py} {pz} 0 0 0</pose>\n"
            f'      <link name="body">\n'
            f'        <collision name="solid">'
            f"<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
            f"</collision>\n"
            f'        <visual name="shape">'
            f"<geometry><box><size>{sx} {sy} {sz}</size></box></geometry>"
            f"<material><ambient>0.6 0.6 0.6 1</ambient>"
            f"<diffuse>0.6 0.6 0.6 1</diffuse></material></visual>\n"
            f"      </link>\n"
            f"    </model>\n")


def _m_goal_walled_in(pkg: Path) -> None:
    """Fence the station in without touching its approach column.

    A block on top of the station would be caught earlier, as a barrier
    inside the approach column, which is a different defect. This mutant
    leaves that column clear and closes the way in: four walls at 800 mm,
    3.7 m tall, so the inflated probe can neither pass between them nor
    fly over. The refusal must be ``goal_unreachable`` and nothing else.
    """
    manifest = loads_strict((pkg / "manifest.json").read_bytes(), code="manifest")
    station = next(r["model"] for r in manifest["roles"]
                   if r["role"] == "charging_station")
    raw = (pkg / "world.sdf").read_text()
    marker = f'<model name="{station}">'
    pose_start = raw.index("<pose>", raw.index(marker)) + 6
    pose_end = raw.index("</pose>", pose_start)
    parts = raw[pose_start:pose_end].split()
    sx = round(float(parts[0]) * 1000)
    sy = round(float(parts[1]) * 1000)
    half, thick, height = 800, 200, 3700
    span = 2 * half + thick
    walls = [
        ("m900", (sx + half, sy, height // 2), (thick, span, height)),
        ("m901", (sx - half, sy, height // 2), (thick, span, height)),
        ("m902", (sx, sy + half, height // 2), (span, thick, height)),
        ("m903", (sx, sy - half, height // 2), (span, thick, height)),
    ]
    block = "".join(_wall(n, p, s) for n, p, s in walls)
    _rewrite_sdf(pkg, raw.replace("  </world>", block + "  </world>", 1).encode())
    _rewrite_manifest(pkg, lambda m: {
        **m, "roles": m["roles"] + [{"model": n, "role": "barrier"}
                                    for n, _, _ in walls]})


# (name, mutation, expected refusal, control index into the suite).
# ``role_missing`` needs a control with more than the schema's minimum of
# three roles, otherwise JSON Schema refuses it first and the semantic
# check under test never runs; index 8 is a five-model split-C world.
PACKAGE_MUTANTS: Tuple[Tuple[str, Callable[[Path], None], str, int], ...] = (
    ("sdf_hash_changed", _m_sdf_hash, "sdf_hash_mismatch", 0),
    ("role_nonexistent", _m_role_absent, "roles_model_absent", 0),
    ("role_missing", _m_role_missing, "roles_model_unassigned", 8),
    ("role_duplicate", _m_role_duplicate, "roles_duplicate_model", 0),
    ("json_duplicate_key", _m_json_duplicate_key, "json_duplicate_key", 0),
    ("seed_split_leaked", _m_leaked_seed, "manifest_schema", 0),
    ("remote_include", _m_remote_include, "sdf_unsupported_element", 0),
    ("plugin_injected", _m_injected_plugin, "sdf_unsupported_element", 0),
    ("xml_dtd", _m_xml_dtd, "sdf_doctype", 0),
    ("symlink_out_of_package", _m_symlink_escape, "package_symlink_entry", 0),
    ("spawn_inside_solid", _m_spawn_in_solid, "spawn_inside_solid", 0),
    ("world_over_1mib", _m_oversize, "sdf_too_large", 0),
    ("goal_unreachable", _m_goal_walled_in, "goal_unreachable", 0),
)


def _package_cases(work: Path, protocol: Protocol, results: Sequence) -> List[Dict]:
    cases: List[Dict] = []
    # Positive controls first: every unmutated copy must still validate, or
    # each refusal below is worthless.
    for index in sorted({m[3] for m in PACKAGE_MUTANTS}):
        ctrl_dir = _copy(results[index].path, work / f"control{index}")
        try:
            load_package(ctrl_dir, protocol)
            cases.append({"mutant": f"positive_control[{index}]",
                          "expected": "valid", "observed": "valid", "ok": True})
        except Sim3Error as exc:
            cases.append({"mutant": f"positive_control[{index}]",
                          "expected": "valid", "observed": exc.code, "ok": False})
            return cases

    for name, apply, expected, index in PACKAGE_MUTANTS:
        pkg_dir = _copy(results[index].path, work / name)
        apply(pkg_dir)
        observed = "accepted"
        detail = ""
        try:
            load_package(pkg_dir, protocol)
        except Sim3Error as exc:
            observed, detail = exc.code, exc.detail[:160]
        cases.append({"mutant": name, "expected": expected, "observed": observed,
                      "detail": detail, "ok": observed == expected})
    return cases


def _clone_case(work: Path, protocol: Protocol, results: Sequence) -> Dict:
    """A renamed copy of another world is not a new world."""
    source = results[1]
    clone = metamorph.renamed(source.package, work / "renamed_clone", protocol)
    same = clone.fingerprint_sha256 == source.package.fingerprint_sha256
    novel = clone.sdf.sha256 != source.package.sdf.sha256
    return {"mutant": "renamed_clone_as_new_world",
            "expected": "same fingerprint, different bytes",
            "fingerprint_identical": same, "sdf_sha_differs": novel,
            "ok": bool(same and novel)}


# --- runtime and transport mutants ----------------------------------------

def _runtime_cases(work: Path, protocol: Protocol, results: Sequence,
                   runtime: Runtime, log) -> List[Dict]:
    cases: List[Dict] = []
    package = results[0].package
    short = min(120, protocol.steps)

    log("mutant: positive control session")
    control = run_episode(runtime, package, protocol, steps=short,
                          label="mutant-control")
    cases.append({"mutant": "positive_control_session", "expected": "ok",
                  "observed": "ok" if control.ok else
                  (control.cause or {}).get("code"),
                  "n_ticks": control.n_ticks, "ok": control.ok})
    if not control.ok:
        return cases

    log("mutant: backend disconnected")
    broken = Runtime(available=True, lock={**runtime.lock,
                                           "container": {**runtime.lock["container"],
                                                         "image": "localhost/sim3-does-not-exist:0"}})
    result = run_episode(broken, package, protocol, steps=short,
                         label="mutant-backend-down")
    cases.append({"mutant": "backend_disconnected",
                  "expected": "backend_no_ready", "n_ticks": result.n_ticks,
                  "observed": (result.cause or {}).get("code"),
                  "ok": (not result.ok) and result.n_ticks == 0
                  and (result.cause or {}).get("code") == "backend_no_ready"})

    log("mutant: statistics without advance")
    result = run_episode(runtime, package, protocol, steps=short,
                         runner_path=FROZEN_RUNNER, label="mutant-frozen-clock")
    cases.append({"mutant": "stats_without_advance",
                  "expected": "clock_not_monotonic",
                  "observed": (result.cause or {}).get("code"),
                  "ok": (not result.ok)
                  and (result.cause or {}).get("code") == "clock_not_monotonic"})

    log("mutant: sandbox unavailable")
    no_sandbox = Runtime(available=True,
                         lock={**runtime.lock, "sandbox": {"tool": "bubblewrap"}})
    observed = "accepted"
    try:
        sandbox.spawn(no_sandbox)
    except Sim3Error as exc:
        observed = exc.code
    cases.append({"mutant": "sandbox_failure", "expected": "sandbox_unavailable",
                  "observed": observed, "ok": observed == "sandbox_unavailable"})

    for mode, expected in (("extra_field", "ack_mismatch"),
                           ("oversized", "ack_mismatch"),
                           ("wrong_seq", "ack_mismatch"),
                           ("silent", "ack_timeout")):
        log(f"mutant: abusive consumer {mode}")
        result = run_episode(runtime, package, protocol, steps=short,
                             probe_path=PROBE_ABUSIVE,
                             probe_env={"SIM3_ABUSE": mode},
                             label=f"adversarial_transport-{mode}")
        observed = (result.cause or {}).get("code")
        entities = sorted(result.model_poses_um) if result.model_poses_um else []
        cases.append({"mutant": f"consumer_{mode}", "expected": expected,
                      "observed": observed,
                      "entities_after": entities,
                      "no_new_entity": all(not e.startswith("cheat")
                                           for e in entities),
                      "ok": (not result.ok) and observed == expected
                      and all(not e.startswith("cheat") for e in entities)})

    log("mutant: tick carrying private fields")
    result = run_episode(runtime, package, protocol, steps=short,
                         tick_mutation={"split": "C", "seed": 11},
                         label="mutant-leaky-tick")
    consumer = result.consumer or {}
    cases.append({"mutant": "tick_with_split_and_seed",
                  "expected": "consumer rejects unexpected_fields",
                  "observed": consumer.get("protocol_error"),
                  "session_cause": (result.cause or {}).get("code"),
                  "ok": (not result.ok)
                  and consumer.get("protocol_error") == "unexpected_fields"})
    return cases


def run_all(work: Path, protocol: Protocol, results: Sequence,
            runtime: Runtime, report_path: Path, log=lambda _s: None
            ) -> Tuple[List[Dict], bool]:
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    cases = _package_cases(work, protocol, results)
    cases.append(_clone_case(work, protocol, results))
    if runtime.available:
        cases += _runtime_cases(work, protocol, results, runtime, log)
    else:
        cases.append({"mutant": "runtime_mutants", "status": "not_run",
                      "reason": runtime.reason, "ok": False})
    cases.append({"mutant": "report_tampering",
                  "expected": "checked by the auditor, not here",
                  "where": "echoai.nexus0.sim3 audit --self-test", "ok": True})
    return cases, all(c.get("ok") for c in cases)


# --- sealing ---------------------------------------------------------------

def sealing_cases(work: Path, protocol: Protocol, results: Sequence
                  ) -> Tuple[List[Dict], bool]:
    """Commit, derive, open once, consume. With the published rehearsal secret."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    cases: List[Dict] = []

    commitment = sealmod.protocol_commitment(protocol.sha256,
                                             sealmod.REHEARSAL_SECRET)
    recomputed = sha256_bytes(
        b"SIM3/v1/commit\0" + bytes.fromhex(protocol.sha256)
        + sealmod.REHEARSAL_SECRET)
    cases.append({"check": "protocol_commitment", "value": commitment,
                  "ok": commitment == recomputed})

    seeds = {split: [sealmod.derive_seed(sealmod.REHEARSAL_SECRET, split, i)
                     for i in range(4)] for split in sealmod.SPLITS}
    flat = [s for v in seeds.values() for s in v]
    cases.append({"check": "seed_derivation", "seeds": seeds,
                  "distinct": len(set(flat)) == len(flat),
                  "note": "HMAC-SHA256 with the published 32x0x01 rehearsal secret",
                  "ok": len(set(flat)) == len(flat)})

    inventory = [{"split": g.split, "index": g.index,
                  "package_sha256": g.package.package_sha256,
                  "fingerprint_sha256": g.package.fingerprint_sha256}
                 for g in results]
    raw = sealmod.inventory_bytes(inventory)
    inv_sha = sha256_bytes(raw)
    commit_inv = sealmod.inventory_commitment(sealmod.REHEARSAL_SALT, raw)
    cases.append({"check": "inventory_commitment", "inventory_sha256": inv_sha,
                  "commitment": commit_inv,
                  "salt_hex": sealmod.REHEARSAL_SALT.hex(),
                  "n_entries": len(inventory), "ok": True})

    latch = work / "rehearsal_C.seal.json"
    if latch.exists():
        latch.unlink()
    sealmod.seal(latch, split="C", commitment=commit_inv,
                 inventory_sha256=inv_sha, custodian="rehearsal (public secret)",
                 n_packages=len([g for g in results if g.split == "C"]))
    cases.append({"check": "sealed", "state": sealmod.read_seal(latch).state,
                  "ok": sealmod.read_seal(latch).state == "sealed"})

    with sealmod.open_once(latch) as state:
        opened_state = state.state
    consumed = sealmod.read_seal(latch).state
    cases.append({"check": "open_once", "opened": opened_state,
                  "after": consumed, "ok": opened_state == "opened"
                  and consumed == "consumed"})

    reopened = "accepted"
    try:
        with sealmod.open_once(latch):
            pass
    except Sim3Error as exc:
        reopened = exc.code
    cases.append({"check": "reopen_refused", "expected": "seal_already_consumed",
                  "observed": reopened, "ok": reopened == "seal_already_consumed"})

    crash = work / "rehearsal_C_crash.seal.json"
    if crash.exists():
        crash.unlink()
    sealmod.seal(crash, split="C", commitment=commit_inv, inventory_sha256=inv_sha,
                 custodian="rehearsal", n_packages=1)
    state = sealmod.read_seal(crash)
    state.data["state"] = "opened"          # a process that died mid-exam
    sealmod._atomic_write(crash, state.data)
    crashed = "accepted"
    try:
        with sealmod.open_once(crash):
            pass
    except Sim3Error as exc:
        crashed = exc.code
    cases.append({"check": "crash_after_open_stays_consumed",
                  "expected": "seal_crash_consumed", "observed": crashed,
                  "after": sealmod.read_seal(crash).state,
                  "ok": crashed == "seal_crash_consumed"
                  and sealmod.read_seal(crash).state == "consumed"})

    busy = work / "rehearsal_C_busy.seal.json"
    if busy.exists():
        busy.unlink()
    sealmod.seal(busy, split="C", commitment=commit_inv, inventory_sha256=inv_sha,
                 custodian="rehearsal", n_packages=1)
    concurrent = "accepted"
    with sealmod.open_once(busy):
        try:
            with sealmod.open_once(busy):
                pass
        except Sim3Error as exc:
            concurrent = exc.code
    cases.append({"check": "mutual_exclusion", "expected": "seal_busy",
                  "observed": concurrent, "ok": concurrent == "seal_busy"})

    tampered = "accepted"
    try:
        sealmod.verify_inventory(sealmod.read_seal(latch),
                                 inventory[:-1], sealmod.REHEARSAL_SALT)
    except Sim3Error as exc:
        tampered = exc.code
    cases.append({"check": "inventory_tamper_detected",
                  "expected": "inventory_mismatch", "observed": tampered,
                  "ok": tampered == "inventory_mismatch"})

    cases.append({"check": "final_C_not_generated_here", "ok": True,
                  "note": "SIM-3 runs rehearsal only; no campaign C exists in "
                          "this tree and none was opened."})
    return cases, all(c.get("ok") for c in cases)
