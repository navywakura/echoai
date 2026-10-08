"""Controls and mutants, each provoked from something that worked.

The rule is the same one SIM-3 uses and it is easy to break by accident:
showing that an already-red episode is still red proves nothing. Every
case here starts from a positive control — an episode that flew, a
config that passed, a report the auditor accepted — changes exactly one
thing, and requires the failure to name that thing.

Three of the mutants replace the backend itself (a teleport harness, a
runner that declares a force it never publishes, a runner whose clock is
frozen). They live in ``assets/`` next to the trusted runner, import it,
and patch one method, so the diff is a few lines and is in the code
inventory.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error
from echoai.nexus0.flight1s import evaluate
from echoai.nexus0.flight1s.runtime import HERE, Runtime, podman
from echoai.nexus0.flight1s.session import run_episode

ASSETS = HERE / "assets"
TELEPORT = ASSETS / "flightrunner_teleport.py"
NOFORCE = ASSETS / "flightrunner_noforce.py"
FROZEN_CLOCK = ASSETS / "flightrunner_frozen_clock.py"

# Keys the container is allowed to see. Anything else in the config is a
# channel from the private side into the flying side.
ALLOWED_CONFIG_KEYS = {
    "world_name", "world_path", "model", "airframe", "spawn_pose", "workdir",
    "condition", "stages", "timeouts", "disturbance", "rates",
}
FORBIDDEN_SUBSTRINGS = ("split", "seed", "package_id", "package_sha",
                        "fingerprint", "role", "station", "barrier", "manifest",
                        "goal", "waypoint")


def container_config(package, protocol: Dict, condition: str) -> Dict:
    """Rebuild exactly what ``session`` hands the container, for inspection."""
    from echoai.nexus0.flight1s.worldbuild import spawn_pose

    pose, _ = spawn_pose(package, protocol["body"])
    return {
        "world_name": "sim3",
        "world_path": "/flight/world.sdf",
        "model": protocol["body"]["model"],
        "airframe": int(protocol["body"]["airframe"]),
        "spawn_pose": pose,
        "workdir": "/out/wd",
        "condition": condition,
        "stages": dict(protocol["stages"]),
        "timeouts": dict(protocol["timeouts"]),
        "disturbance": {"link": protocol["disturbance"]["link"],
                        "axis": list(protocol["disturbance"]["axis"]),
                        "force_mn": int(protocol["disturbance"]["force_mn"])},
        "rates": dict(protocol["rates"]),
    }


def inspect_config(cfg: Dict) -> Dict:
    """Does this config carry anything about which room it is?"""
    unknown = sorted(set(cfg) - ALLOWED_CONFIG_KEYS)
    blob = json.dumps(cfg, sort_keys=True).lower()
    leaks = [needle for needle in FORBIDDEN_SUBSTRINGS if needle in blob]
    return {"unknown_keys": unknown, "leaked_substrings": leaks,
            "ok": not unknown and not leaks}


# --- controls --------------------------------------------------------------

def controls(runtime: Runtime, packages: Sequence, protocol,
             log=lambda _s: None) -> Tuple[List[Dict], bool]:
    cases: List[Dict] = []
    proto = protocol.data if hasattr(protocol, "data") else protocol
    control_pkg = packages[0]

    # 1. The config the container receives is the same shape everywhere and
    #    says nothing about the world it is about to fly in.
    configs = {}
    for gen in packages:
        for condition in ("nominal", "perturbed"):
            configs[(gen.package_id, condition)] = container_config(
                gen.package, proto, condition)
    inspections = [inspect_config(c) for c in configs.values()]
    varying = set()
    reference = configs[(packages[0].package_id, "nominal")]
    for cfg in configs.values():
        for key in reference:
            if cfg[key] != reference[key]:
                varying.add(key)
    cases.append({
        "control": "config_carries_no_room_identity",
        "n_configs": len(configs),
        "keys_that_vary": sorted(varying),
        "unknown_keys": sorted({k for i in inspections for k in i["unknown_keys"]}),
        "leaks": sorted({k for i in inspections for k in i["leaked_substrings"]}),
        "ok": all(i["ok"] for i in inspections)
              and varying <= {"spawn_pose", "condition", "disturbance"},
        "note": "spawn_pose is the world's own validated free column and "
                "condition is the manipulated variable; nothing else moves",
    })

    # 2. The container has no network at all.
    cases.append(_no_network_control(runtime))

    # 3. A nominal episode and a perturbed one on the same world, paired.
    log("control: paired nominal and perturbed on one world")
    paired = {}
    for condition in ("nominal", "perturbed"):
        ep = run_episode(runtime, control_pkg.package, proto,
                         condition=condition, label=f"control-{condition}")
        paired[condition] = evaluate.episode_metrics(ep, proto,
                                                     package=control_pkg.package)
    nom = paired["nominal"]
    per = paired["perturbed"]
    separated = (per.get("disturb_excursion_mm", 0)
                 > nom.get("disturb_excursion_mm", 0))
    cases.append({
        "control": "paired_nominal_vs_perturbed",
        "nominal_excursion_mm": nom.get("disturb_excursion_mm"),
        "perturbed_excursion_mm": per.get("disturb_excursion_mm"),
        "nominal_impulse_ppk": (nom.get("impulse") or {}).get("ratio_ppk"),
        "perturbed_impulse_ppk": (per.get("impulse") or {}).get("ratio_ppk"),
        "ok": bool(nom["ok"] and per["ok"] and separated),
        "note": "the same body, world and script; only the wrench differs",
    })

    # 4. A world hash that does not match its manifest is refused before
    #    anything flies.
    cases.append(_hash_mismatch_control(control_pkg, proto))
    return cases, all(c["ok"] for c in cases)


def _no_network_control(runtime: Runtime) -> Dict:
    pm = podman()
    if pm is None:
        return {"control": "no_network_during_bench", "ok": False,
                "why": "podman missing"}
    probe = (
        "import socket,json;"
        "r={};"
        "\ntry:\n socket.create_connection(('1.1.1.1',443),2); r['tcp']='connected'\n"
        "except OSError as e: r['tcp']=e.strerror\n"
        "try:\n socket.gethostbyname('github.com'); r['dns']='resolved'\n"
        "except OSError as e: r['dns']=e.strerror\n"
        "print(json.dumps(r))"
    )
    proc = subprocess.run(
        [pm, "run", "--rm", "--pull=never", "--network=none",
         "--security-opt", "label=disable", runtime.image, "python3", "-c", probe],
        capture_output=True, timeout=120)
    try:
        seen = json.loads(proc.stdout.decode().strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        seen = {"raw": proc.stdout.decode()[-200:]}
    return {"control": "no_network_during_bench", "observed": seen,
            "ok": seen.get("tcp") not in (None, "connected")
                  and seen.get("dns") not in (None, "resolved")}


def _hash_mismatch_control(gen, proto: Dict) -> Dict:
    """A package whose bytes stopped matching its manifest never flies."""
    from echoai.nexus0.sim3.pkg import load_package, load_protocol
    from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="flight1s-mut-"))
    try:
        pkg_dir = tmp / "pkg"
        shutil.copytree(gen.path, pkg_dir)
        raw = (pkg_dir / "world.sdf").read_bytes()
        (pkg_dir / "world.sdf").write_bytes(raw.replace(b"<gravity>",
                                                        b"<gravity >", 1))
        observed = "accepted"
        try:
            load_package(pkg_dir, load_protocol(WORLD_PROTOCOL))
        except Sim3Error as exc:
            observed = exc.code
        return {"control": "world_hash_mismatch_refused",
                "expected": "sdf_hash_mismatch", "observed": observed,
                "ok": observed == "sdf_hash_mismatch"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- mutants ---------------------------------------------------------------

def run_all(runtime: Runtime, packages: Sequence, protocol,
            episodes: Sequence[Dict], log=lambda _s: None
            ) -> Tuple[List[Dict], bool]:
    proto = protocol.data if hasattr(protocol, "data") else protocol
    pkg = packages[0]
    cases: List[Dict] = []

    log("mutant: positive control episode")
    control = run_episode(runtime, pkg.package, proto, condition="perturbed",
                          label="mutant-control")
    cm = evaluate.episode_metrics(control, proto, package=pkg.package)
    cases.append({
        "mutant": "positive_control_episode", "expected": "flies and is measured",
        "observed": "measured" if (control.ok and cm.get("status") == "measured")
                    else (control.cause or {}).get("code"),
        "impulse_ratio_ppk": (cm.get("impulse") or {}).get("ratio_ppk"),
        "px4_signature": cm.get("px4_signature"),
        "ok": bool(control.ok and cm.get("status") == "measured"
                   and cm["px4_signature"]["ok"]),
    })
    if not cases[0]["ok"]:
        cases.append({"mutant": "remaining_mutants", "status": "not_run",
                      "why": "positive control did not fly", "ok": False})
        return cases, False

    log("mutant: teleport harness instead of PX4")
    ep = run_episode(runtime, pkg.package, proto, condition="perturbed",
                     label="mutant-teleport", runner_path=TELEPORT)
    m = evaluate.episode_metrics(ep, proto, package=pkg.package)
    sig = m.get("px4_signature", {})
    cases.append({
        "mutant": "pose_teleported_or_replayed",
        "expected": "px4 signature absent",
        "observed": sig, "reported_ok_by_harness": ep.ok,
        "ok": bool(not sig.get("ok")),
        "note": "the harness reports a perfect episode; the signature is what "
                "refuses it",
    })
    cases.append({
        "mutant": "fixture_controller_labelled_as_sitl",
        "expected": "no ulog and no driver arm/mode events",
        "observed": {"ulog_present": sig.get("ulog_present"),
                     "driver_armed": sig.get("driver_armed"),
                     "driver_mode_switch": sig.get("driver_mode_switch")},
        "ok": bool(not sig.get("ulog_present") and not sig.get("driver_armed")),
    })

    log("mutant: force declared, wrench never published")
    ep = run_episode(runtime, pkg.package, proto, condition="perturbed",
                     label="mutant-noforce", runner_path=NOFORCE)
    m = evaluate.episode_metrics(ep, proto, package=pkg.package)
    imp = m.get("impulse") or {}
    ratio = imp.get("ratio_ppk")
    cases.append({
        "mutant": "force_declared_without_wrench",
        "expected": "impulse ratio collapses",
        "control_ratio_ppk": (cm.get("impulse") or {}).get("ratio_ppk"),
        "observed_ratio_ppk": ratio,
        "excursion_mm": m.get("disturb_excursion_mm"),
        "min_excursion_mm": proto["bands"]["min_disturb_excursion_mm"],
        "ok": bool(ep.ok and ratio is not None and ratio < 500),
        "note": "the episode still flies; only the physics is missing",
    })

    log("mutant: frozen backend clock")
    ep = run_episode(runtime, pkg.package, proto, condition="nominal",
                     label="mutant-frozen-clock", runner_path=FROZEN_CLOCK)
    cases.append({
        "mutant": "fabricated_or_frozen_clock",
        "expected": "episode cannot complete",
        "observed": (ep.cause or {}).get("code"),
        "ok": bool(not ep.ok),
    })

    cases.append(_config_leak_mutant(pkg, proto, "split"))
    cases.append(_config_leak_mutant(pkg, proto, "station_mm",
                                     value=[3000, 0, 550],
                                     name="ground_truth_as_setpoint"))
    cases.append(_download_mutant(runtime))
    cases.append({
        "mutant": "report_level_mutants",
        "expected": "checked by the auditor, not here",
        "where": "echoai.nexus0.flight1s audit --self-test",
        "covers": ["omitted red episode", "relaxed band or N",
                   "two locks or two PX4 commits", "altered trace or ulog hash"],
        "ok": True,
    })
    return cases, all(c.get("ok") for c in cases)


def _config_leak_mutant(gen, proto: Dict, key: str, value="C",
                        name: Optional[str] = None) -> Dict:
    """Put the room into the config and require the inspector to see it."""
    clean = container_config(gen.package, proto, "nominal")
    before = inspect_config(clean)
    dirty = dict(clean)
    dirty[key] = value
    after = inspect_config(dirty)
    return {
        "mutant": name or f"branch_by_{key}",
        "expected": "config inspector refuses it",
        "clean_ok": before["ok"],
        "observed": {"unknown_keys": after["unknown_keys"],
                     "leaked_substrings": after["leaked_substrings"]},
        "ok": bool(before["ok"] and not after["ok"]),
    }


def _download_mutant(runtime: Runtime) -> Dict:
    """A runner that tries to fetch an asset mid-bench cannot."""
    pm = podman()
    if pm is None:
        return {"mutant": "asset_download_during_bench", "ok": False,
                "why": "podman missing"}
    script = (
        "import urllib.request, json\n"
        "try:\n"
        "    urllib.request.urlopen('https://fuel.gazebosim.org/', timeout=3)\n"
        "    print(json.dumps({'fetched': True}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'fetched': False, 'error': type(e).__name__}))\n"
    )
    proc = subprocess.run(
        [pm, "run", "--rm", "--pull=never", "--network=none",
         "--security-opt", "label=disable", runtime.image, "python3", "-c", script],
        capture_output=True, timeout=120)
    try:
        seen = json.loads(proc.stdout.decode().strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        seen = {"raw": proc.stdout.decode()[-200:]}
    return {"mutant": "asset_download_during_bench",
            "expected": "no route out of the episode container",
            "observed": seen, "ok": seen.get("fetched") is False}
