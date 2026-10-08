#!/usr/bin/env python3
"""
Regenerate the LEX table of `echoai/nexus0/lex.py` from
`legacy/kernel-navi/wsp_lex.c` (formerly `kernel/navi/wsp_lex.c`).

Reads the kernel file, never writes it. Rewrites only the region between
the BEGIN/END markers in lex.py, so the hand-written code around the table
survives. Row order is the C order and stays that way: first-match-wins is
the contract, and the 11 shadowed rows are shadowed in the C too.

    python3 -m echoai.nexus0.tools.gen_lex --check   # 0 = in sync, 1 = drift
    python3 -m echoai.nexus0.tools.gen_lex           # rewrite the table

Deterministic: same C in, same bytes out. A second run is a no-op.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[3]
C_PATH = ROOT / "legacy" / "kernel-navi" / "wsp_lex.c"
LEX_PATH = ROOT / "echoai" / "nexus0" / "lex.py"

BEGIN = "# --- BEGIN GENERATED TABLE — tools/gen_lex.py, from kernel/navi/wsp_lex.c ---"
END = "# --- END GENERATED TABLE ---"

_ROW = re.compile(r'^\s*L\("((?:[^"\\]|\\.)*)",\s*(.+?)\),\s*$')
_SECTION = re.compile(r"^\s*(/\*.*\*/)\s*$")

N_FIELDS = 13  # src rel dst time + 6 E + dom gen style


def render_table(c_text: Optional[str] = None) -> str:
    """The generated region: marker, LEX tuple, marker. No trailing newline."""
    if c_text is None:
        c_text = C_PATH.read_text(encoding="utf-8")
    out: List[str] = [BEGIN, "LEX: Tuple[Rule, ...] = ("]
    rows = 0
    for line in c_text.splitlines():
        m = _ROW.match(line)
        if not m:
            sec = _SECTION.match(line)
            # Keep the C section comments: they document the table order.
            if sec and "Longer" not in sec.group(1):
                out.append("")
                out.append("    # " + sec.group(1).strip("/* ").strip(" */"))
            continue
        key, rest = m.group(1), m.group(2)
        parts = [p.strip() for p in rest.split(",")]
        if len(parts) != N_FIELDS:
            raise ValueError(f"bad row ({len(parts)} fields): {line}")
        src, rel, dst, tm = (p.replace("WSP_", "") for p in parts[0:4])
        e = parts[4:10]
        dom = parts[10].replace("WSP_", "")
        gen = parts[11].replace("WSP_", "")
        st = parts[12]
        for v in (*e, st):
            int(v)  # integer literals only; no macro sneaks through
        out.append(
            f'    L("{key}", {src}, {rel}, {dst}, {tm}, '
            f'{",".join(e)}, {dom}, {gen}, {st}),'
        )
        rows += 1
    if not rows:
        raise ValueError(f"no L() rows found in {C_PATH}")
    out.append(")")
    out.append(END)
    return "\n".join(out)


def render_file(current: Optional[str] = None, c_text: Optional[str] = None) -> str:
    """`current` lex.py source with its generated region replaced."""
    if current is None:
        current = LEX_PATH.read_text(encoding="utf-8")
    start = current.find(BEGIN)
    end = current.find(END)
    if start < 0 or end < 0:
        raise ValueError(f"markers not found in {LEX_PATH}")
    return current[:start] + render_table(c_text) + current[end + len(END):]


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    current = LEX_PATH.read_text(encoding="utf-8")
    wanted = render_file(current)
    rows = wanted.count("\n    L(")
    if current == wanted:
        sys.stdout.write(f"in sync: {rows} rows\n")
        return 0
    if check:
        sys.stdout.write(f"DRIFT: lex.py differs from wsp_lex.c ({rows} rows)\n")
        return 1
    LEX_PATH.write_text(wanted, encoding="utf-8")
    sys.stdout.write(f"rewrote {LEX_PATH.name}: {rows} rows\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
