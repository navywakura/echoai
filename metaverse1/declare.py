"""Write a world declaration that a modeller can rebuild from, and nothing else.

The declaration is the world's public description: regions, blocked cells,
start and goal.  Blender reads this JSON; it never imports echoAI, so the
asset pipeline cannot accidentally pull the agent into a renderer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .world import CELL_MM, MetaSpace


def declaration(space: MetaSpace) -> dict:
    described = space.describe()
    return {
        "schema": "echoai-metaverse1-world-v1",
        "seed": space.seed,
        "condition": space.condition,
        "detail": space.detail,
        "cell_m": CELL_MM / 1000,
        "size_m": described["size_m"],
        "regions": [
            {"id": region.ident, "origin": list(region.origin),
             "width": region.width, "height": region.height,
             "template": region.template}
            for region in space.blocks.regions
        ],
        "solids": sorted([list(cell) for cell in space.solids]),
        "domain": sorted([list(cell) for cell in space.domain]),
        "start": list(space.start),
        "goal": list(space.goal),
        "note": ("Descripción pública del mundo. La malla se regenera de aquí; "
                 "no es física, no es certificado."),
    }


def write(space: MetaSpace, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(declaration(space), indent=2, ensure_ascii=False)
                    + "\n", encoding="utf-8")
    return path


def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    from .world import minimal_regions, wide_regions

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7001)
    parser.add_argument("--condition", default="static")
    parser.add_argument("--cols", type=int, default=1)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    regions = (minimal_regions() if (args.cols, args.rows) == (1, 1)
               else wide_regions(args.cols, args.rows))
    space = MetaSpace(args.seed, args.condition, regions=regions)
    path = write(space, Path(args.out))
    print(json.dumps({"world": str(path), **space.describe()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
