"""
TALK-1 — posthumous subtitles. Never a thought, never a cause.

This file reads `thought.jsonl` and writes Spanish. That is all it does,
and the order of those two things is the whole claim: the turn already
happened, the animal already decided, the world already paid. What is
produced here is a **subtitle**, in the cinema sense — it arrives after
the scene and changes nothing in it.

So there is no import of `Agent`, of the loop, of CAM, of T, of Q, of the
gate, of the cortex or of any world; no `parse_reply`, no `NAVI_CORTEX_*`,
no network, no subprocess, no server. The file is opened read-only and its
bytes are the same afterwards. Nothing here is a callback, a pipe or a
file the animal reads back. Standard library only.

**No `porque`.** The log records what happened, not why. `attend_on` says
the slow clock woke; `action` says what the body did after the gate;
`cortex_action` says which proposal was spent this turn. Those are three
facts and this module prints them as three clauses. Joining them with a
conjunction would be inventing the one thing the record does not contain.
Even on the turn that spends a proposal the two stay apart, because
`gate_decision` still has the last word — that is the same separation
SIGN-Cc had to be fixed to make.

The output is controlled Spanish, not prose: a closed set of sixteen
labelled clauses, one line per record, in the order the records came in.
Each clause maps to exactly one field, and `Q` and `WSP` are reproduced
verbatim rather than interpreted. An auditor can therefore check the
subtitle against the record without ever calling `render`.

    python3 -m echoai.nexus0.talk echoai/lab/thought.jsonl

A malformed record is an error and a non-zero exit, never a default and
never a skipped line. The whole file is validated before a single subtitle
is emitted, so there is no such thing as half a narration that reads as a
whole one.

A future Qwen pass that polishes these lines into nicer Spanish would be
another **optional operator** consuming subtitles that were already
audited. It is not implemented here and must never be part of `green()`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# The 22 keys of `thought.KEYS`, duplicated on purpose: importing the
# animal at runtime is exactly what this module must not do. The tests pin
# this tuple against `thought.KEYS` so the copy cannot drift in silence.
KEYS = (
    "turn", "cell", "kind", "action", "reward", "wsp",
    "attend_on", "reason_name", "q_row", "t_pred",
    "questions", "cortex_calls",
    "n", "s", "delta", "cortex_action", "gate_decision",
    "x", "y", "z", "heading", "frame",
)

# Same discipline: `thought.ACTION_NAME`, copied, and pinned by the tests.
ACTION_NAME = ("approach", "avoid", "wait", "open")
KIND_NAME = ("EMPTY", "GOAL", "THREAT", "NOVEL", "OBJECT", "CLOSED")
REASON_NAME = ("off", "miss", "no_extract", "low_C", "novel", "no_map",
               "conflict")

# What the body did. Past tense, one phrase per action, and no two of them
# share a word — a subtitle that says `esperó` cannot be misread as any of
# the others, which is what makes the `wait` mutant checkable.
BODY: Dict[int, str] = {
    0: "se acercó",
    1: "se apartó",
    2: "esperó",
    3: "abrió",
}

# What the slow clock proposed. Infinitive, because a proposal is not a
# thing that happened: the gate may still have refused it.
PROPOSAL: Dict[int, str] = {
    0: "acercarse",
    1: "apartarse",
    2: "esperar",
    3: "abrir",
}

GATE: Dict[int, str] = {0: "aceptó", 1: "modificó", 2: "bloqueó"}

# One Spanish phrase per ATTEND reason. `off` is its own clause value, not
# a reason with a name: the switch did not fire.
REASON_ES: Dict[str, str] = {
    "off": "apagada",
    "miss": "despertó por fallo de CAM",
    "no_extract": "despertó por falta de extracto",
    "low_C": "despertó por falta de preferencia",
    "novel": "despertó por celda nueva",
    "no_map": "despertó por falta de mapa",
    "conflict": "despertó por conflicto",
}

# The clause labels, in the order they are emitted. A closed grammar: an
# auditor checks this exact list before looking at any value.
LABELS = (
    "turno", "celda", "pose", "cuerpo", "gate", "recompensa", "atención",
    "córtex", "T", "nuevo", "sorpresa", "δ", "preguntas", "llamadas",
    "Q", "WSP",
)

SEP = " · "


class BadRecord(ValueError):
    """A line that is not a turn this loop could have written."""


def _int(record: Dict[str, Any], key: str, where: str) -> int:
    v = record[key]
    if isinstance(v, bool) or not isinstance(v, int):
        raise BadRecord(f"{where}: `{key}` no es un entero: {v!r}")
    return v


def _opt_int(record: Dict[str, Any], key: str, where: str) -> Optional[int]:
    if record[key] is None:
        return None
    return _int(record, key, where)


def validate(record: Any, where: str = "registro") -> Dict[str, Any]:
    """Every key, every type, every closed set, and the two shapes.

    Nothing is defaulted and nothing is coerced. A record that this loop
    could not have written is an error with a reason, because a subtitle
    over a record nobody recognises is a caption over a photograph nobody
    took.
    """
    if not isinstance(record, dict):
        raise BadRecord(f"{where}: no es un objeto JSON")
    missing = sorted(set(KEYS) - set(record))
    extra = sorted(set(record) - set(KEYS))
    if missing or extra:
        raise BadRecord(
            f"{where}: claves {'faltan ' + ', '.join(missing) if missing else ''}"
            f"{' ' if missing and extra else ''}"
            f"{'sobran ' + ', '.join(extra) if extra else ''}".strip()
        )

    for key in ("turn", "cell", "reward", "questions", "cortex_calls",
                "action", "gate_decision", "n", "s", "delta"):
        _int(record, key, where)
    for key in ("t_pred", "x", "y", "z", "heading", "frame"):
        _opt_int(record, key, where)

    if record["action"] not in BODY:
        raise BadRecord(f"{where}: acción fuera de rango: {record['action']}")
    if record["gate_decision"] not in GATE:
        raise BadRecord(f"{where}: gate fuera de rango: {record['gate_decision']}")
    if record["cortex_action"] is not None:
        _int(record, "cortex_action", where)
        if record["cortex_action"] not in PROPOSAL:
            raise BadRecord(
                f"{where}: propuesta fuera de rango: {record['cortex_action']}")
    for key in ("n", "s", "delta"):
        if record[key] not in (0, 1):
            raise BadRecord(f"{where}: `{key}` no es 0 ni 1: {record[key]}")
    for key in ("turn", "cell", "questions", "cortex_calls"):
        if record[key] < 0:
            raise BadRecord(f"{where}: `{key}` es negativo: {record[key]}")

    if not isinstance(record["attend_on"], bool):
        raise BadRecord(f"{where}: `attend_on` no es booleano")
    if record["reason_name"] not in REASON_NAME:
        raise BadRecord(f"{where}: razón desconocida: {record['reason_name']!r}")
    # The loop's own form: ATTEND either fired with a reason or did not
    # fire at all. `attend_on` true with reason `off`, or false with a
    # reason, is the shape SIGN-Cb existed to make impossible, and a
    # subtitle must not paper over it if it ever comes back.
    if bool(record["attend_on"]) != (record["reason_name"] != "off"):
        raise BadRecord(
            f"{where}: attend_on={record['attend_on']} con razón "
            f"{record['reason_name']!r}")

    if record["kind"] not in KIND_NAME:
        raise BadRecord(f"{where}: kind desconocido: {record['kind']!r}")
    if not isinstance(record["wsp"], str) or not record["wsp"].strip():
        raise BadRecord(f"{where}: `wsp` vacío o no es texto")
    if SEP.strip() in record["wsp"]:
        raise BadRecord(f"{where}: `wsp` contiene el separador de cláusulas")

    row = record["q_row"]
    # Three gears, or the four of a world with a lid. Nothing else exists
    # in this repo, and a row of another width is a record some other loop
    # wrote — which is exactly what must not be narrated as if it were
    # this one's.
    if not isinstance(row, list) or len(row) not in (3, 4):
        raise BadRecord(f"{where}: `q_row` no es una fila de tres ni de cuatro")
    for v in row:
        if isinstance(v, bool) or not isinstance(v, int):
            raise BadRecord(f"{where}: `q_row` tiene un valor no entero: {v!r}")
    # The action has to be one the row that produced it could hold. An
    # `open` beside a three-wide row is a line from a world that had no
    # fourth gear, and a subtitle over it would be a caption on the wrong
    # photograph.
    if record["action"] >= len(row):
        raise BadRecord(
            f"{where}: acción {record['action']} con una fila Q de {len(row)}")
    if record["cortex_action"] is not None and record["cortex_action"] >= len(row):
        raise BadRecord(
            f"{where}: propuesta {record['cortex_action']} con una fila Q "
            f"de {len(row)}")

    pose = [record["x"], record["y"], record["z"]]
    if any(v is None for v in pose) and any(v is not None for v in pose):
        raise BadRecord(f"{where}: pose a medias: x/y/z = {pose}")
    # No pose means no pose: a heading or a frame without one is a world
    # that half-answered, and `_pose` would silently drop them.
    if pose[0] is None:
        for key in ("heading", "frame"):
            if record[key] is not None:
                raise BadRecord(f"{where}: `{key}` sin pose")
    return record


def _pose(record: Dict[str, Any]) -> str:
    if record["x"] is None:
        return "sin pose"
    out = f"({record['x']}, {record['y']}, {record['z']})"
    if record["heading"] is not None:
        out += f" rumbo {record['heading']}"
    if record["frame"] is not None:
        out += f" marco {record['frame']}"
    return out


def _reward(value: int) -> str:
    """Signed, always. `0` is neither a gain nor a loss and says so."""
    if value > 0:
        return f"+{value}"
    return str(value)


def render(record: Dict[str, Any], where: str = "registro") -> str:
    """One record, one line. Sixteen labelled clauses, no conjunctions.

    `cuerpo` and `córtex` are separate clauses even when they agree, and
    especially when they do not: a proposal of `esperar` that the gate
    turned into `se apartó` prints both, and credits the reflex to nobody.
    """
    validate(record, where)
    action = record["action"]
    proposal = record["cortex_action"]
    t_pred = record["t_pred"]
    clauses = (
        f"turno: {record['turn']}",
        f"celda: {record['cell']} ({record['kind']})",
        f"pose: {_pose(record)}",
        f"cuerpo: {BODY[action]}",
        f"gate: {GATE[record['gate_decision']]}",
        f"recompensa: {_reward(record['reward'])}",
        f"atención: {REASON_ES[record['reason_name']]}",
        "córtex: " + ("no propuso" if proposal is None
                      else f"propuso {PROPOSAL[proposal]}"),
        "T: " + ("no predijo" if t_pred is None else f"predijo {t_pred}"),
        f"nuevo: {'sí' if record['n'] else 'no'}",
        f"sorpresa: {'sí' if record['s'] else 'no'}",
        f"δ: {'sí' if record['delta'] else 'no'}",
        f"preguntas: {record['questions']}",
        f"llamadas: {record['cortex_calls']}",
        f"Q: {record['q_row']}",
        f"WSP: {record['wsp']}",
    )
    return SEP.join(clauses)


def read_records(path) -> List[Dict[str, Any]]:
    """Parse and validate the whole file before anything is narrated.

    Half a narration that reads as a whole one is worse than an error, so
    the file is either entirely a diary this module recognises or it is
    refused. Read-only, and the bytes are untouched.
    """
    text = Path(path).read_text(encoding="utf-8")
    out: List[Dict[str, Any]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{path}:{i}"
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise BadRecord(f"{where}: JSON ilegible: {exc}") from exc
        out.append(validate(record, where))
    return out


def translate(path) -> List[str]:
    """Every record of a diary, in order, one subtitle each."""
    records = read_records(path)
    return [render(r, f"{path}:{i}") for i, r in enumerate(records, start=1)]


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("uso: python3 -m echoai.nexus0.talk RUTA.jsonl\n")
        return 2
    try:
        lines = translate(args[0])
    except (BadRecord, OSError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    for line in lines:
        sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
