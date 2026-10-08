"""
TALK-1 bench — does the subtitle say what the record says, and nothing else?

`talk.py` writes the Spanish. This file never calls it to check itself: an
auditor that asked the renderer what the renderer meant would score a
tautology. Instead `audit()` parses the subtitle back into its sixteen
labelled clauses and checks each one against the record with rules written
here, independently — including the rules that say what a clause must
**not** contain, which no renderer can satisfy by accident.

Three things are measured and all three are numbers, not flags:

    TranslationConsistency   clauses that survive the audit, over a matrix
                             that floods every field the log has
    mutants_killed           hand-corrupted subtitles that must be caught
    causal_writes            findings of an AST scan over `talk.py` itself

The matrix is generated from field values, not recognised by turn or cell:
the meaning has to come out of the record. Two of its rows are not
synthetic at all — the real `conflict` / `consume` pair SIGN-Cb produced,
and a real OPEN-1 turn where the body opened a jar — because a bench that
only ever narrates records it wrote itself has not met the animal.

    PYTHONPATH=. python3 -m echoai.nexus0.talk1
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from echoai.nexus0 import talk, thought

# --- the auditor's own tables ------------------------------------------
# Deliberately not imported from `talk`: if the renderer's table moves,
# these must disagree with it, which is the point. That has to hold for
# **every** semantic table, not just the easy ones — `audit()` was reading
# `talk.REASON_ES`, so a renderer that called `miss` "despertó por celda
# nueva" was checked against its own mistake and passed. The tests pin
# each of these against the renderer's copy, so drift is caught there
# rather than swallowed at runtime.
WANT_BODY = {0: "se acercó", 1: "se apartó", 2: "esperó", 3: "abrió"}
WANT_PROPOSAL = {0: "acercarse", 1: "apartarse", 2: "esperar", 3: "abrir"}
WANT_GATE = {0: "aceptó", 1: "modificó", 2: "bloqueó"}
REASONS = ("off", "miss", "no_extract", "low_C", "novel", "no_map", "conflict")
WANT_REASON = {
    "off": "apagada",
    "miss": "despertó por fallo de CAM",
    "no_extract": "despertó por falta de extracto",
    "low_C": "despertó por falta de preferencia",
    "novel": "despertó por celda nueva",
    "no_map": "despertó por falta de mapa",
    "conflict": "despertó por conflicto",
}
# The grammar, from this side. `parse()` fixes the sixteen labels and
# their order without asking the renderer what it thinks they are.
WANT_LABELS = (
    "turno", "celda", "pose", "cuerpo", "gate", "recompensa", "atención",
    "córtex", "T", "nuevo", "sorpresa", "δ", "preguntas", "llamadas",
    "Q", "WSP",
)
WANT_SEP = " · "


def want_pose(record: Dict[str, Any]) -> str:
    """The one string this record's pose may be. Built here, not there.

    Auditing pose by looking for each coordinate as a substring was the
    hole: `1` is in `100`, order did not matter, and anything could be
    appended. Four false subtitles passed. Equality against a string this
    side builds is the only check that closes all of them at once.
    """
    if record["x"] is None:
        return "sin pose"
    out = f"({record['x']}, {record['y']}, {record['z']})"
    if record["heading"] is not None:
        out += f" rumbo {record['heading']}"
    if record["frame"] is not None:
        out += f" marco {record['frame']}"
    return out

# Every way this vocabulary can say the body moved. A `wait` turn may
# contain none of them; the prompt's own list is folded in so the check is
# not merely the complement of the renderer's table.
MOTION = ("giró", "avanzó", "retrocedió", "se acercó", "se alejó", "abrió",
          "se apartó", "avanza", "gira")

# Words that would turn two recorded facts into one invented cause.
CAUSAL = ("porque", "por lo que", "así que", "debido a", "ya que",
          "puesto que", "de modo que", "por eso", "gracias a", "a causa de")

def parse(subtitle: str) -> Dict[str, str]:
    """Split a subtitle into its labelled clauses, or raise.

    The label list is closed and ordered, so a renderer that dropped,
    added or reordered a clause fails here before any value is looked at.
    """
    parts = subtitle.split(WANT_SEP)
    got: List[str] = []
    values: Dict[str, str] = {}
    for part in parts:
        label, sep, value = part.partition(": ")
        if not sep:
            raise ValueError(f"cláusula sin etiqueta: {part!r}")
        got.append(label)
        values[label] = value
    if tuple(got) != WANT_LABELS:
        raise ValueError(f"cláusulas {got} != {list(WANT_LABELS)}")
    return values


def audit(record: Dict[str, Any], subtitle: str) -> List[str]:
    """Everything the subtitle must say, and everything it must not.

    Returns the list of failures; empty means this line is faithful.
    """
    bad: List[str] = []
    try:
        c = parse(subtitle)
    except ValueError as exc:
        return [str(exc)]

    action = record["action"]
    proposal = record["cortex_action"]

    # 1. the body, and nothing that could be mistaken for another body.
    #
    # Exact equality, not a forbidden-word list: `esperó` is the only
    # string this clause may hold for a `wait` turn, so every one of
    # `giró`, `avanzó`, `retrocedió`, `se acercó`, `se alejó` and `abrió`
    # is already refused, along with everything else. A separate loop over
    # those six was written first and then removed — no mutant could kill
    # it, because nothing can fail it without failing this line, and a
    # rule that cannot go red is not a rule. What the sweep at the end of
    # this function adds is the clauses where the check *is* looser.
    if c["cuerpo"] != WANT_BODY[action]:
        bad.append(f"cuerpo: {c['cuerpo']!r} para action={action}")

    # 2. the gate had the last word and says so
    if c["gate"] != WANT_GATE[record["gate_decision"]]:
        bad.append(f"gate: {c['gate']!r} para {record['gate_decision']}")

    # 3. the proposal is its own fact, never the body's
    if proposal is None:
        if c["córtex"] != "no propuso":
            bad.append(f"córtex: {c['córtex']!r} sin propuesta")
        for verb in WANT_PROPOSAL.values():
            if verb in c["córtex"]:
                bad.append(f"córtex inventa {verb!r} con cortex_action=null")
    else:
        if c["córtex"] != f"propuso {WANT_PROPOSAL[proposal]}":
            bad.append(f"córtex: {c['córtex']!r} para propuesta={proposal}")
        if proposal != action and WANT_PROPOSAL[action] in c["córtex"]:
            bad.append("córtex acreditado con lo que hizo el cuerpo")

    # 4. the reward keeps its sign, and zero is neither
    reward = record["reward"]
    want_reward = f"+{reward}" if reward > 0 else str(reward)
    if c["recompensa"] != want_reward:
        bad.append(f"recompensa: {c['recompensa']!r} para {reward}")

    # 5. attention: off is off, and a reason is named
    reason = record["reason_name"]
    if reason not in WANT_REASON:
        bad.append(f"razón desconocida en el registro: {reason!r}")
    elif c["atención"] != WANT_REASON[reason]:
        bad.append(f"atención: {c['atención']!r} para razón {reason!r}")
    for other, phrase in WANT_REASON.items():
        if other != reason and phrase in c["atención"]:
            bad.append(f"atención dice {other!r} con razón {reason!r}")

    # 6. a prediction that was not made carries no number
    if record["t_pred"] is None:
        if c["T"] != "no predijo":
            bad.append(f"T: {c['T']!r} con t_pred=null")
        if any(ch.isdigit() for ch in c["T"]):
            bad.append("T inventa una predicción")
    elif c["T"] != f"predijo {record['t_pred']}":
        bad.append(f"T: {c['T']!r} para t_pred={record['t_pred']}")

    # 7. the three flags, and the counters
    for label, key in (("nuevo", "n"), ("sorpresa", "s"), ("δ", "delta")):
        want = "sí" if record[key] else "no"
        if c[label] != want:
            bad.append(f"{label}: {c[label]!r} para {key}={record[key]}")
    for label, key in (("preguntas", "questions"), ("llamadas", "cortex_calls"),
                       ("turno", "turn")):
        if c[label] != str(record[key]):
            bad.append(f"{label}: {c[label]!r} para {key}={record[key]}")

    # 8. cell, kind and pose
    if c["celda"] != f"{record['cell']} ({record['kind']})":
        bad.append(f"celda: {c['celda']!r}")
    want = want_pose(record)
    if c["pose"] != want:
        bad.append(f"pose: {c['pose']!r} != {want!r}")

    # 9. evidence reproduced, not reinterpreted
    if c["Q"] != str(record["q_row"]):
        bad.append(f"Q: {c['Q']!r} para {record['q_row']}")
    if c["WSP"] != record["wsp"]:
        bad.append("WSP alterado")
    return bad


# Two loops used to live at the end of `audit()`: a sweep for verbs
# outside `cuerpo` / `córtex`, and a scan for causal conjunctions. Both
# are gone, and it is worth saying why rather than leaving them in.
#
# They were written when `pose` was audited by substring — the one clause
# a renderer could append to and still pass. Now all sixteen clauses are
# checked by exact equality against a string this file builds, so nothing
# can be added anywhere without failing the clause it was added to. No
# mutant could kill either loop, and a rule that cannot go red is not a
# rule; the two mutants that were supposed to cover them
# (`un verbo colado en la pose`, `una causa colada en la pose`) now die on
# the pose comparison instead, which is the check that is really doing the
# work.
#
# The prohibition on `porque` is not weakened by this: it is enforced
# where it can fail, in `experiment()`'s `uses_a_conjunction`, which
# counts causal words across every subtitle of the matrix *and* of a real
# 256-turn diary, and which `green()` requires to be zero. The mutant
# `una cláusula causal entra en la línea` turns thirty-seven tests red.


def audit_file(records: List[dict], subtitles: List[str]) -> List[str]:
    """Cardinality and order, before any line is looked at."""
    bad: List[str] = []
    if len(subtitles) != len(records):
        bad.append(f"{len(subtitles)} subtítulos para {len(records)} registros")
    for i, (rec, sub) in enumerate(zip(records, subtitles)):
        bad.extend(f"[{i}] {msg}" for msg in audit(rec, sub))
    return bad


def same_order(records: List[dict], subtitles: List[str]) -> bool:
    """The turn numbers, in the sequence the diary had them."""
    try:
        got = [parse(s)["turno"] for s in subtitles]
    except ValueError:
        return False
    return got == [str(r["turn"]) for r in records]


# --- causal isolation, by AST over talk.py -----------------------------
FORBIDDEN_TOP = {
    "subprocess", "socket", "urllib", "http", "requests", "httpx", "aiohttp",
    "multiprocessing", "threading", "ctypes", "signal", "shutil", "os",
    "importlib", "tempfile", "pickle", "sqlite3",
}
# Path operations that change something on disk.
WRITE_CALLS = {"write_text", "write_bytes", "unlink", "rmdir", "mkdir",
               "rename", "replace", "touch", "chmod", "symlink_to", "hardlink_to"}
# Anything that puts bytes somewhere.
WRITE_METHODS = {"write", "writelines", "truncate"}
# Ways to reach a module without an import statement.
DYNAMIC = {"eval", "exec", "__import__", "compile", "import_module", "globals",
           "vars", "getattr", "setattr"}


def _is_std_stream_write(node: ast.Call) -> bool:
    """`sys.stdout.write` / `sys.stderr.write` — the CLI's own output.

    The only writes a posthumous narrator is allowed: its whole contract
    is to put text on a stream. Anything else that writes is a finding,
    including a handle whose provenance this scan cannot see.
    """
    fn = node.func
    return (
        isinstance(fn, ast.Attribute)
        and fn.attr in WRITE_METHODS
        and isinstance(fn.value, ast.Attribute)
        and fn.value.attr in ("stdout", "stderr")
        and isinstance(fn.value.value, ast.Name)
        and fn.value.value.id == "sys"
    )


def causal_findings(source: str, where: str = "talk.py") -> List[str]:
    """Every way this module could reach back into the animal.

    Conservative on purpose, because the earlier version was not and let
    four equivalent writes through. It read the mode of `open` positionally
    as if every call were the builtin, so `Path(p).open("w")` — where the
    mode is `args[0]` — was invisible, as was any non-constant mode, and it
    never looked at `write()` at all.

    So: **any** `open` is a finding. `talk.py` needs none — it reads with
    `Path.read_text` — and a translator that acquires one has changed in a
    way this bench should have to look at. Same for `write`, `writelines`
    and `truncate` on anything but `sys.stdout` / `sys.stderr`, for the
    Path mutators, and for `eval` / `exec` / `__import__`, which are how a
    module reaches the animal without an import statement to find.

    This is not a sandbox and does not claim to be. It covers every form
    the bench says it prohibits.
    """
    out: List[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top == "echoai":
                    out.append(f"{where}: importa el animal ({alias.name})")
                elif top in FORBIDDEN_TOP:
                    out.append(f"{where}: importa {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top == "echoai":
                out.append(f"{where}: importa el animal ({node.module})")
            elif top in FORBIDDEN_TOP:
                out.append(f"{where}: importa {node.module}")
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else (
                fn.id if isinstance(fn, ast.Name) else "")
            if name in WRITE_CALLS:
                out.append(f"{where}: escribe en disco ({name})")
            elif name in WRITE_METHODS and not _is_std_stream_write(node):
                out.append(f"{where}: escribe fuera de stdout/stderr ({name})")
            elif name == "open":
                # No mode is read. A translator that opens a file at all is
                # a translator this bench has to be shown again.
                out.append(f"{where}: abre un fichero ({name})")
            elif name in DYNAMIC:
                out.append(f"{where}: escape dinámico ({name})")
    return out


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- the matrix ---------------------------------------------------------
def _base(turn: int) -> dict:
    """A neutral ring turn. Every row below moves fields off this."""
    return {
        "turn": turn, "cell": 7, "kind": "EMPTY", "action": 2, "reward": 0,
        "wsp": "YO → OBSERVAR → AQUI @AHORA | E[V+0 A+20 D+0 C+40 U+10 B+0]",
        "attend_on": False, "reason_name": "off", "q_row": [0, 0, 0],
        "t_pred": None, "questions": 0, "cortex_calls": 0,
        "n": 0, "s": 0, "delta": 0, "cortex_action": None, "gate_decision": 0,
        "x": None, "y": None, "z": None, "heading": None, "frame": None,
    }


def synthetic_matrix() -> List[Tuple[str, dict]]:
    """Flood the fields. Nothing here is recognised by turn or by cell.

    Turns are distinct only so that order can be checked; no rule in the
    auditor or the renderer reads them for meaning.
    """
    rows: List[Tuple[str, dict]] = []
    turn = 0

    def add(name: str, **over) -> None:
        nonlocal turn
        rec = _base(turn)
        rec.update(over)
        rows.append((name, rec))
        turn += 1

    # the four actions, including the one that must never read as movement
    add("action_approach", action=0)
    add("action_avoid", action=1)
    add("action_wait_on_empty", action=2, kind="EMPTY")
    add("action_open", action=3, kind="CLOSED", q_row=[0, 0, 0, 1])
    # reward, all three signs
    add("reward_positive", action=0, kind="GOAL", reward=16)
    add("reward_zero", action=2, reward=0)
    add("reward_negative", action=0, kind="THREAT", reward=-16)
    # pose: the cube's five, and the ring's five nulls
    add("pose_full", action=0, x=1, y=2, z=0, heading=3, frame=1)
    add("pose_no_frame", action=1, x=0, y=0, z=2, heading=5)
    add("pose_none")
    # every ATTEND reason, off included
    for reason in REASONS:
        add(f"reason_{reason}", reason_name=reason, attend_on=reason != "off")
    # the proposal, absent and in each of its verbs
    add("proposal_none", cortex_action=None)
    for i, verb in enumerate(("approach", "avoid", "wait")):
        add(f"proposal_{verb}", cortex_action=i, action=i, cortex_calls=1)
    # the one the gate rescued: proposed wait, body avoided
    add("proposal_wait_body_avoid", cortex_action=2, action=1,
        kind="THREAT", reward=8, gate_decision=1, cortex_calls=1)
    add("gate_block", action=2, gate_decision=2)
    # T known and unknown, and the three flags both ways
    add("t_known", t_pred=1986, action=0)
    add("t_unknown", t_pred=None, action=0)
    add("flags_off", n=0, s=0, delta=0)
    add("flags_on", n=1, s=1, delta=1, t_pred=42, action=0, reward=-16,
        kind="THREAT")
    add("counters", questions=3, cortex_calls=9, t_pred=7)
    return rows


def real_signc_pair() -> List[Tuple[str, dict]]:
    """The conflict turn and the turn that spends its proposal. Not written
    by this bench: produced by running SIGN-C's own arm with a diary on."""
    from echoai.nexus0 import sign, signc

    ag = signc._train(signc.LANDING_KIND, signc.SIGN_TEXT,
                      (signc.LAYOUT_SHIFT,))
    ag.cortex_enabled = True
    ag.conflict_attend = True
    ag.env = signc.SignCEnv(signc.LAYOUT_SHIFT)
    ag.env.teleport(signc.SIGN_NODE)
    with tempfile.TemporaryDirectory() as tmp:
        ag.thought_log = str(Path(tmp) / "thought.jsonl")
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
        lines = Path(ag.thought_log).read_text(encoding="utf-8").splitlines()
    records = [json.loads(x) for x in lines]
    return [("real_signc_conflict", records[0]),
            ("real_signc_consume", records[1])]


def real_open_turn() -> List[Tuple[str, dict]]:
    """A real fourth-gear turn: the body opens a jar, in OPEN-1's world."""
    from echoai.nexus0 import open1
    from echoai.nexus0.encoder import encode_cell
    from echoai.nexus0.env import KIND_CLOSED
    from echoai.nexus0.loop import Agent

    on_the_jar = open1.cube.index_of(*open1.ITEM_XYZ, 0)
    env = open1.Open1Env()
    ag = Agent(ask=False, n_actions=open1.GEARS_WITH_A_LID, env=env)
    # One ordinary turn allocates the jar's slot; it also walks the body
    # off it, so it is put back. The packet is the same both times — the
    # lid is still on — so this is the slot that turn will start from.
    env.teleport(on_the_jar)
    ag.turn(0)
    env.teleport(on_the_jar)
    cell = env.cell()
    assert cell.kind == KIND_CLOSED, f"the jar is not shut: {cell.kind}"
    slot = ag.cam.get(encode_cell(cell.index, cell.kind))
    assert slot >= 0, "the jar has no slot"
    # The fourth gear is the only winner, so `best` names it and the body
    # takes it. Nothing else is seeded: the gate and the world are real.
    ag.q.q[slot] = [0, 0, 0, 1]
    with tempfile.TemporaryDirectory() as tmp:
        ag.thought_log = str(Path(tmp) / "thought.jsonl")
        ag.turn(1, greedy=True)
        record = json.loads(
            Path(ag.thought_log).read_text(encoding="utf-8").splitlines()[0])
    assert record["action"] == 3, f"the body did not open: {record['action']}"
    assert env.lid_open, "the lid is still on"
    return [("real_open1_turn", record)]


def matrix() -> List[Tuple[str, dict]]:
    return synthetic_matrix() + real_signc_pair() + real_open_turn()


# --- the mutants --------------------------------------------------------
def _swap(subtitle: str, old: str, new: str) -> str:
    if old not in subtitle:
        raise AssertionError(f"la cláusula {old!r} no está en el subtítulo")
    return subtitle.replace(old, new, 1)


def mutants(rows: List[Tuple[str, dict]]) -> List[dict]:
    """Hand-corrupted subtitles. Each must produce at least one failure."""
    by_name = {name: rec for name, rec in rows}
    out: List[dict] = []

    def line(name: str, key: str, old: str, new: str) -> None:
        rec = by_name[key]
        bad = _swap(talk.render(rec), old, new)
        out.append({"mutant": name, "killed": bool(audit(rec, bad)),
                    "failures": audit(rec, bad)})

    line("esperar narrado como movimiento",
         "action_wait_on_empty", "cuerpo: esperó", "cuerpo: avanzó")
    line("esperar narrado como apertura",
         "action_wait_on_empty", "cuerpo: esperó", "cuerpo: abrió")
    line("approach y avoid intercambiados",
         "action_approach", "cuerpo: se acercó", "cuerpo: se apartó")
    line("open narrado como approach",
         "action_open", "cuerpo: abrió", "cuerpo: se acercó")
    line("signo de recompensa invertido",
         "reward_positive", "recompensa: +16", "recompensa: -16")
    line("cero narrado como ganancia",
         "reward_zero", "recompensa: 0", "recompensa: +0")
    line("atención apagada narrada como conflicto",
         "reason_off", "atención: apagada", "atención: despertó por conflicto")
    line("conflicto omitido",
         "reason_conflict", "atención: despertó por conflicto",
         "atención: apagada")
    line("propuesta inventada",
         "proposal_none", "córtex: no propuso", "córtex: propuso acercarse")
    line("el reflejo del gate acreditado al córtex",
         "proposal_wait_body_avoid", "córtex: propuso esperar",
         "córtex: propuso apartarse")
    line("predicción inventada",
         "t_unknown", "T: no predijo", "T: predijo 187")
    line("una causa inventada con «porque»",
         "real_signc_consume", "córtex: propuso acercarse",
         "córtex: propuso acercarse porque hubo conflicto")
    line("WSP reinterpretado",
         "action_approach", "WSP: YO", "WSP: EL BICHO")
    # These two ride in the clause that was checked by substring, so they
    # violate the sweep and the causal rule and nothing else.
    line("un verbo colado en la pose",
         "pose_full", "rumbo 3 marco 1", "rumbo 3 marco 1 y avanzó")
    line("una causa colada en la pose",
         "pose_full", "rumbo 3 marco 1", "rumbo 3 marco 1 porque sí")

    # The four false poses the substring audit used to accept, plus the
    # two omissions it could not see either. `1` is a substring of `100`,
    # order did not matter, and anything could be appended.
    line("pose con coordenadas infladas",
         "pose_full", "pose: (1, 2, 0)", "pose: (100, 200, 0)")
    line("pose con coordenadas reordenadas",
         "pose_full", "pose: (1, 2, 0)", "pose: (2, 1, 0)")
    line("pose con información añadida",
         "pose_full", "marco 1 ·", "marco 1 con obstáculo ·")
    line("pose con un marco inventado",
         "pose_no_frame", "rumbo 5 ·", "rumbo 5 marco 99 ·")
    line("pose con el rumbo omitido",
         "pose_full", "pose: (1, 2, 0) rumbo 3", "pose: (1, 2, 0)")
    line("una pose inventada donde no la hay",
         "pose_none", "pose: sin pose", "pose: (0, 0, 0)")

    # Each of the seven ATTEND translations, twisted in the *renderer*.
    # The auditor must reject all seven from its own table — this is what
    # the shared `talk.REASON_ES` made impossible, and the only mutant
    # that ever failed was one the two tables disagreed about by accident.
    for reason in REASONS:
        other = "conflict" if reason != "conflict" else "off"
        rec = by_name[f"reason_{reason}"]
        keep = talk.REASON_ES[reason]
        talk.REASON_ES[reason] = talk.REASON_ES[other]
        try:
            bad = talk.render(rec)
        finally:
            talk.REASON_ES[reason] = keep
        failures = audit(rec, bad)
        out.append({"mutant": f"razón torcida en el redactor: {reason}",
                    "killed": bool(failures), "failures": failures})
    line("una cláusula desaparece",
         "flags_on", " · sorpresa: sí", "")

    # File-level: cardinality and order are not a per-line property.
    records = [rec for _, rec in rows]
    subtitles = [talk.render(rec) for rec in records]
    for name, mutated in (
        ("un registro omitido", subtitles[:-1]),
        ("un registro duplicado", subtitles + [subtitles[-1]]),
        ("los registros reordenados", list(reversed(subtitles))),
    ):
        failures = audit_file(records, mutated)
        ordered = same_order(records, mutated)
        out.append({"mutant": name, "killed": bool(failures) or not ordered,
                    "failures": failures[:3]})

    # Isolation: the scanner has to see a translator that reaches back.
    source = Path(talk.__file__).read_text(encoding="utf-8")
    for name, injected in (
        ("el traductor importa el animal (from)",
         source + "\nfrom echoai.nexus0.loop import Agent\n"),
        ("el traductor importa el animal (import)",
         source + "\nimport echoai.nexus0.loop\n"),
        ("el traductor escribe el jsonl fuente",
         source + "\ndef _oops(p):\n    Path(p).write_text('')\n"),
        ("el traductor abre en escritura",
         source + "\ndef _oops(p):\n    open(p, 'w')\n"),
        ("el traductor arranca un proceso",
         source + "\nimport subprocess\n"),
        # The five forms the old scanner was blind to: it read the mode of
        # `open` positionally as if every call were the builtin, and never
        # looked at `write` at all.
        ("el traductor abre con Path.open y escribe",
         source + "\ndef _x(p):\n    Path(p).open('w').write('x')\n"),
        ("el traductor abre con un modo dinámico",
         source + "\ndef _x(p, mode):\n    Path(p).open(mode).write('x')\n"),
        ("el traductor usa open con un modo dinámico",
         source + "\ndef _x(p, mode):\n    open(p, mode).write('x')\n"),
        ("el traductor escribe en un descriptor cualquiera",
         source + "\ndef _x(fh):\n    fh.write('x')\n"),
        ("el traductor importa el animal dinámicamente",
         source + "\ndef _x():\n    __import__('echoai.nexus0.loop')\n"),
    ):
        out.append({"mutant": name,
                    "killed": bool(causal_findings(injected, "mutante")),
                    "failures": causal_findings(injected, "mutante")[:3]})
    return out


# --- the experiment -----------------------------------------------------
def _ring_diary(path: Path) -> None:
    """A real 256-turn ring run, written to a scratch file, read-only after."""
    from echoai.nexus0.constants import BENCH_TURNS
    from echoai.nexus0.loop import Agent

    ag = Agent(thought_log=str(path))
    ag.run(BENCH_TURNS)


def experiment() -> dict:
    rows = matrix()
    records = [rec for _, rec in rows]
    subtitles = [talk.render(rec) for rec in records]
    failures = audit_file(records, subtitles)

    # Clause-level consistency: sixteen audited clauses per record, so a
    # single wrong clause moves the number instead of flipping a flag.
    total = len(records) * len(WANT_LABELS)
    hits = total - len(failures)

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "thought.jsonl"
        _ring_diary(source)
        before = _sha256(source)
        file_subtitles = talk.translate(source)
        after = _sha256(source)
        file_records = talk.read_records(source)
        file_failures = audit_file(file_records, file_subtitles)
        file_order = same_order(file_records, file_subtitles)

    battery = mutants(rows)
    _state = battery_state(battery)
    findings = causal_findings(
        Path(talk.__file__).read_text(encoding="utf-8"), "talk.py")

    out: Dict[str, Any] = {
        "world": "talk1",
        "source_kind": "anillo, 256 turnos, generado en un temporal",
        "source_records": len(file_records),
        "narrated_records": len(file_subtitles),
        "same_order": bool(file_order),
        "source_sha256_before": before,
        "source_sha256_after": after,
        "source_unchanged": bool(before == after),
        "file_failures": file_failures[:5],
        "file_failure_count": len(file_failures),

        "matrix_records": len(records),
        "matrix_names": [name for name, _ in rows],
        "matrix_actions": sorted({r["action"] for r in records}),
        "matrix_reasons": sorted({r["reason_name"] for r in records}),
        "matrix_proposals": sorted(
            {r["cortex_action"] for r in records}, key=lambda v: (v is None, v)),
        "matrix_gate_decisions": sorted({r["gate_decision"] for r in records}),
        "matrix_reward_signs": sorted(
            {(r["reward"] > 0) - (r["reward"] < 0) for r in records}),
        "matrix_has_pose": any(r["x"] is not None for r in records),
        "matrix_has_ring_nulls": any(r["x"] is None for r in records),
        "matrix_t_known_and_unknown": (
            any(r["t_pred"] is not None for r in records)
            and any(r["t_pred"] is None for r in records)),
        "matrix_flags_both_ways": all(
            {r[k] for r in records} == {0, 1} for k in ("n", "s", "delta")),

        "consistency_hits": hits,
        "consistency_total": total,
        "TranslationConsistency": (100 * hits) // total if total else 0,
        "audit_failures": failures[:5],

        "mutants": battery,
        "mutants_killed": sum(1 for m in battery if m["killed"]),
        "mutants_total": len(battery),
        "required_mutants": len(REQUIRED_MUTANTS),
        "required_mutants_missing": _state["missing"],
        "required_mutants_duplicated": _state["duplicated"],
        # Every survivor, required or not: an extra mutant that lives is
        # as red as a required one that does.
        "mutants_alive": _state["alive"],
        "mutants_malformed": _state["malformed"],

        "thought_keys": len(talk.KEYS),
        "keys_match_thought": tuple(talk.KEYS) == tuple(thought.KEYS),
        "action_names_match_thought": (
            tuple(talk.ACTION_NAME) == tuple(thought.ACTION_NAME)),
        "causal_findings": findings,
        "causal_writes": len(findings),
        "uses_a_conjunction": sum(
            1 for s in subtitles + file_subtitles
            for w in CAUSAL if w in s.lower()),
    }
    return out


# Names that must be in the battery, dead, every run. Counting mutants
# was not enough: `mutants_total >= 12` let whole categories be deleted
# while the report stayed green, so the categories are named here and
# `green()` reads the list rather than its length.
REQUIRED_MUTANTS = (
    # the body, and the one that must never read as movement
    "esperar narrado como movimiento",
    "esperar narrado como apertura",
    "approach y avoid intercambiados",
    "open narrado como approach",
    # the reward's sign
    "signo de recompensa invertido",
    "cero narrado como ganancia",
    # proposal versus body
    "propuesta inventada",
    "el reflejo del gate acreditado al córtex",
    # evidence
    "predicción inventada",
    "WSP reinterpretado",
    "una cláusula desaparece",
    "una causa inventada con «porque»",
    # the four false poses that used to pass, and their two neighbours
    "pose con coordenadas infladas",
    "pose con coordenadas reordenadas",
    "pose con información añadida",
    "pose con un marco inventado",
    "pose con el rumbo omitido",
    "una pose inventada donde no la hay",
    "un verbo colado en la pose",
    "una causa colada en la pose",
    # all seven ATTEND translations, twisted in the renderer
    "razón torcida en el redactor: off",
    "razón torcida en el redactor: miss",
    "razón torcida en el redactor: no_extract",
    "razón torcida en el redactor: low_C",
    "razón torcida en el redactor: novel",
    "razón torcida en el redactor: no_map",
    "razón torcida en el redactor: conflict",
    "atención apagada narrada como conflicto",
    "conflicto omitido",
    # cardinality and order
    "un registro omitido",
    "un registro duplicado",
    "los registros reordenados",
    # every way out of the module
    "el traductor importa el animal (from)",
    "el traductor importa el animal (import)",
    "el traductor escribe el jsonl fuente",
    "el traductor abre en escritura",
    "el traductor arranca un proceso",
    "el traductor abre con Path.open y escribe",
    "el traductor abre con un modo dinámico",
    "el traductor usa open con un modo dinámico",
    "el traductor escribe en un descriptor cualquiera",
    "el traductor importa el animal dinámicamente",
)


def battery_state(battery: Any) -> dict:
    """Everything about the battery, recounted from the battery itself.

    `alive` used to be intersected with `REQUIRED_MUTANTS`, so a mutant
    that was not on the list could survive and no field showed it: the
    name checks ignored it and the two counters were only compared with
    each other. A report could then append `{"killed": False}`, claim it
    died, and stay green. A battery is meant to be extendable, so the rule
    has to be about **every** entry: an extra mutant that dies is welcome,
    and one that lives is red whatever the summary says.

    Nothing here trusts the report's own totals, and nothing here raises.
    A malformed entry — no name, no `killed`, `killed` as the integer 1 —
    is reported as a finding rather than as a traceback in front of the
    operator, because a gate that crashes on a bad report has not judged
    it.
    """
    if not isinstance(battery, list):
        return {"missing": sorted(REQUIRED_MUTANTS), "duplicated": [],
                "alive": [], "malformed": ["`mutants` no es una lista"],
                "total": 0, "killed": 0}
    names: List[str] = []
    alive: List[str] = []
    malformed: List[str] = []
    killed = 0
    for i, entry in enumerate(battery):
        if not isinstance(entry, dict):
            malformed.append(f"[{i}] no es un objeto")
            continue
        name = entry.get("mutant")
        if isinstance(name, str) and name.strip():
            names.append(name)
        else:
            malformed.append(f"[{i}] sin nombre: {name!r}")
            name = f"[{i}]"
        dead = entry.get("killed")
        # `isinstance(True, int)` is true, so the bool check comes first
        # and `killed: 1` is malformed rather than quietly counted.
        if not isinstance(dead, bool):
            malformed.append(f"[{i}] `killed` no es booleano: {dead!r}")
            continue
        if dead:
            killed += 1
        else:
            alive.append(name)
    return {
        "missing": sorted(set(REQUIRED_MUTANTS) - set(names)),
        "duplicated": sorted({n for n in names if names.count(n) > 1}),
        "alive": sorted(alive),
        "malformed": sorted(malformed),
        "total": len(battery),
        "killed": killed,
    }


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red.

    The battery is judged from `report["mutants"]` itself, recomputed
    here, and not from the three summary fields the report writes about
    its own battery — those are evidence for a reader, and a report that
    described itself would be marking its own homework. Three separate
    refusals rather than one `or`, so each can be shown to be load-bearing
    on its own.
    """
    state = battery_state(report.get("mutants"))
    if state["malformed"]:
        return False
    if state["missing"]:
        return False
    if state["duplicated"]:
        return False
    if state["alive"]:
        return False
    # The report's own totals, checked against the recount rather than
    # against each other. Comparing `mutants_killed` with `mutants_total`
    # alone let a report that lied about both agree with itself.
    if report.get("mutants_total") != state["total"]:
        return False
    if report.get("mutants_killed") != state["killed"]:
        return False
    return bool(
        report["source_records"] > 0
        and report["narrated_records"] == report["source_records"]
        and report["same_order"]
        and report["source_unchanged"]
        and report["file_failure_count"] == 0
        and report["TranslationConsistency"] == 100
        and report["consistency_hits"] == report["consistency_total"]
        # `mutants_killed == mutants_total` used to sit here. It is gone:
        # once both totals are recounted from the list and `alive` must be
        # empty, it cannot fail without one of those failing first — and
        # while it was here it was the only thing catching three of them,
        # so none of the three could be shown to be load-bearing. Each
        # refusal above now stands on its own mutant.
        and report["causal_writes"] == 0
        and report["uses_a_conjunction"] == 0
        and report["thought_keys"] == 22
        and report["keys_match_thought"]
        and report["action_names_match_thought"]
        # the matrix actually floods the fields it claims to
        and report["matrix_actions"] == [0, 1, 2, 3]
        and set(report["matrix_reasons"]) == set(REASONS)
        and report["matrix_gate_decisions"] == [0, 1, 2]
        and report["matrix_reward_signs"] == [-1, 0, 1]
        and report["matrix_has_pose"]
        and report["matrix_has_ring_nulls"]
        and report["matrix_t_known_and_unknown"]
        and report["matrix_flags_both_ways"]
        and "real_signc_conflict" in report["matrix_names"]
        and "real_signc_consume" in report["matrix_names"]
        and "real_open1_turn" in report["matrix_names"]
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_talk1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
