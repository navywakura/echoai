"""META-WORLD-2 bench: does enlarging the world change anything it must not?

Four measurements, each able to come out red:

1. **equivalence** — the lattice engine at minimal scale against the certified
   ``compose1_v3.Space``, trace by trace.  Any difference is red.
2. **detail** — raising visual fidelity must leave the collision geometry
   byte-identical.  A changed collision digest is red.
3. **scaling** — enlarged lattices must stay addressable in two bytes, keep
   every region within one byte of local index, and still answer distances.
4. **no_world_branches** — the engine must not branch on a seed or on a world
   name.  A literal seed comparison in the source is red.

The bench writes ``lab/metaverse1/metaworld2-report.json`` and never touches
another phase's evidence.
"""
from __future__ import annotations

import ast
import hashlib
import json
import platform
import random
import time
from pathlib import Path
from typing import Iterable, Optional

from echoai.nexus0.compose1_v3.space import Space

from . import sdf
from .world import (MAX_REGIONS, REGION_CAPACITY, MetaSpace, WorldError,
                    minimal_regions, wide_regions)

ECHOAI = Path(__file__).resolve().parents[1]
OUT = ECHOAI / "lab" / "metaverse1"
HERE = Path(__file__).resolve().parent

CONDITIONS = ("static", "closed", "low_energy", "dynamic")
SEEDS = tuple(range(7001, 7013))
STEPS = 40


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _trace(space, seed: int, steps: int) -> list:
    """One deterministic action script, applied to whichever world is given."""
    rng = random.Random(seed ^ 0xABCD)
    out = []
    for _ in range(steps):
        action = rng.randrange(7)
        out.append([space.scan(), space.step(action),
                    space.home_distance(space.pos), space.oracle_distance()])
    return out


def equivalence(seeds: Iterable[int] = SEEDS, conditions=CONDITIONS,
                steps: int = STEPS) -> dict:
    """The lattice at minimal scale must be the certified world exactly."""
    rows, differences = [], 0
    for seed in seeds:
        for condition in conditions:
            mine = _trace(MetaSpace(seed, condition, regions=minimal_regions()),
                          seed, steps)
            theirs = _trace(Space(seed, condition), seed, steps)
            same = _canonical(mine) == _canonical(theirs)
            differences += not same
            rows.append(dict(seed=seed, condition=condition, identical=same,
                             trace_sha256=hashlib.sha256(
                                 _canonical(mine).encode()).hexdigest()[:16]))
    return dict(kind="equivalence", pairs=len(rows), differences=differences,
                steps=steps, green=differences == 0, rows=rows)


def detail(seeds: Iterable[int] = SEEDS[:6], levels=(0, 1, 2)) -> dict:
    """Visual fidelity must not move a single collision box."""
    rows, breaks = [], 0
    for seed in seeds:
        for lattice, name in ((minimal_regions(), "minimal"),
                              (wide_regions(2, 2), "2x2")):
            space = MetaSpace(seed, "static", regions=lattice)
            digests, visuals = set(), {}
            for level in levels:
                document = sdf.source_sdf(space, detail=level)
                digests.add(sdf.collision_digest(document))
                visuals[level] = sdf.visual_count(document)
            stable = len(digests) == 1
            grew = all(visuals[b] >= visuals[a]
                       for a, b in zip(levels, levels[1:]))
            breaks += not (stable and grew)
            rows.append(dict(seed=seed, lattice=name, collision_stable=stable,
                             visuals_grow=grew, visuals=visuals,
                             collision_sha256=sorted(digests)[0][:16]))
    return dict(kind="detail", cases=len(rows), breaks=breaks,
                levels=list(levels), green=breaks == 0, rows=rows)


def scaling(lattices=((1, 1), (2, 2), (3, 2), (4, 4))) -> dict:
    """Bigger worlds must stay addressable in two bytes and still be solvable."""
    rows, faults = [], 0
    for cols, rows_count in lattices:
        regions = wide_regions(cols, rows_count)
        space = MetaSpace(7001, "static", regions=regions)
        addressable, over = True, 0
        for cell in space.domain:
            try:
                region, local = space.address(cell)
            except WorldError:
                addressable = False
                break
            if not (0 <= region < MAX_REGIONS and 0 <= local < REGION_CAPACITY):
                addressable = False
                break
        for region in regions:
            over += region.width * region.height > REGION_CAPACITY
        reachable = space.oracle_distance() is not None
        ok = addressable and not over and reachable
        faults += not ok
        described = space.describe()
        rows.append(dict(lattice=f"{cols}x{rows_count}", regions=len(regions),
                         cells=described["cells"], size_m=described["size_m"],
                         addressable=addressable, over_capacity=over,
                         reachable=reachable, ok=ok))
    return dict(kind="scaling", cases=len(rows), faults=faults,
                green=faults == 0, rows=rows)


def no_world_branches(module: Path = HERE / "world.py") -> dict:
    """The engine must not special-case a seed or a named world.

    Parsed, not grepped: a comparison against an integer literal that looks
    like a bench seed, or against a world name, is the failure this catches.
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    allowed = set(CONDITIONS) | {"room", "hall"}
    offences = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for comparator in node.comparators:
            if not isinstance(comparator, ast.Constant):
                continue
            value = comparator.value
            if isinstance(value, str) and value not in allowed:
                offences.append(dict(line=node.lineno, value=value))
            if isinstance(value, int) and value >= 1000:
                offences.append(dict(line=node.lineno, value=value))
    return dict(kind="no_world_branches", module=module.name,
                offences=offences, green=not offences)


def run(save: bool = True) -> dict:
    began = time.monotonic()
    parts = [equivalence(), detail(), scaling(), no_world_branches()]
    report = dict(
        schema="echoai-metaworld2-report-v1",
        phase="META-WORLD-2",
        parent_phase="METAVERSE-1",
        created=time.strftime("%Y-%m-%dT%H:%M:%S"),
        elapsed_s=round(time.monotonic() - began, 3),
        python=platform.python_version(),
        scope=("Functional geometry only. No physics was run, no flight, no "
               "hardware. Enlarging the world is not a claim about the agent."),
        limits=[
            "No demuestra nada sobre hardware ni vuelo real.",
            "No cierra DRONE-3 ni sube ECHO-3 de 14/15.",
            "La equivalencia se mide contra compose1_v3.Space, no contra Gazebo.",
            "Un mundo mayor no implica un agente mejor: aquí sólo crece el escenario.",
        ],
        measurements={part["kind"]: part for part in parts},
    )
    report["green"] = all(part["green"] for part in parts)
    payload = _canonical({k: v for k, v in report.items()
                          if k not in ("created", "elapsed_s")})
    report["certificate_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    if save:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "metaworld2-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
    return report


def main(argv: Optional[list[str]] = None) -> int:
    report = run()
    summary = {name: dict(green=part["green"],
                          **{k: v for k, v in part.items()
                             if k in ("differences", "breaks", "faults", "pairs",
                                      "cases", "offences")})
               for name, part in report["measurements"].items()}
    print(json.dumps(dict(green=report["green"],
                          certificate_sha256=report["certificate_sha256"],
                          measurements=summary), indent=2, ensure_ascii=False))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
