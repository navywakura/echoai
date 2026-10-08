"""Validation of frozen campaign, world-family and slice declarations.

These documents are reviewed inputs to an experiment. They are never mounted
into the consumer sandbox and none of their fields are observations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from echoai.nexus0.sim3.canon import Sim3Error, loads_strict, read_bounded, sha256_bytes
from echoai.nexus0.sim3.pkg import _validate_schema

SCHEMAS = Path(__file__).resolve().parents[2] / "docs" / "schemas"
KINDS = {
    "campaign": "sim3-campaign.schema.json",
    "family": "sim3-world-family.schema.json",
    "slice": "echo3-slice.schema.json",
}


def validate(kind: str, path: Path) -> Dict:
    if kind not in KINDS:
        raise Sim3Error("declaration_kind", kind)
    raw = read_bounded(Path(path), code=kind)
    data = loads_strict(raw, code=kind)
    schema = loads_strict(read_bounded(SCHEMAS / KINDS[kind], code="schema"),
                          code="schema")
    _validate_schema(data, schema, f"{kind}_schema")
    return {"valid": True, "kind": kind, "path": str(path),
            "sha256": sha256_bytes(raw), "data": data}
