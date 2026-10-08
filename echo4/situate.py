"""E4-SITUATE-1 «sé qué soy»: substrate facts ECHO verifies itself.

Functional self-location, not self-awareness. Answers are codes backed by
verified CAM facts, or DESCONOCIDO. A fixed renderer turns facts into Spanish
sentences (processed text, never generated). No LLM.
"""
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.echo4.continuity import ROOT, canonical, _unique_pairs, _no_float
from echoai.echo4.world import integer
from echoai.echo4 import tribe as T

SOURCE_FACT, SOURCE_TESTIMONY = "situate-substrate", "situate-testimony"
SELF_FILES = ("nexus0/loop.py", "echo4/tribe.py", "echo4/situate.py")
CODES = ("process", "runtime", "program", "machine", "host", "cuda_gpu", "body", "peers", "world")
QUESTIONS = {1: "human", 2: "program", 3: "where", 4: "gpu_body", 5: "world",
             6: "peers", 7: "knows_topic", 8: "tribe_place", 9: "same_as_before"}
SUBSTRATE_QUESTIONS = (1, 2, 3, 4, 5, 6, 9)
UNKNOWN, VERIFIED, HYPOTHESIS = "DESCONOCIDO", "VERIFICADO", "HIPOTESIS"
REPLAY_ROUNDS = 48


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def self_source(root=ROOT):
    h = hashlib.sha256()
    for rel in SELF_FILES:
        h.update(rel.encode() + b"\0" + hashlib.sha256((Path(root) / rel).read_bytes()).digest())
    return h.hexdigest()


def sense(agents=None, *, root=ROOT):
    """Real sensor readings. Host identity is only ever a fingerprint."""
    readings = {
        "process": {"pid": os.getpid()},
        "runtime": {"implementation": sys.implementation.name, "version": platform.python_version()},
        "program": {"files": list(SELF_FILES), "sha256": self_source(root)},
        "machine": {"system": platform.system(), "arch": platform.machine(), "cpus": os.cpu_count()},
        "host": {"fingerprint": fingerprint(platform.node())},
        "cuda_gpu": {"present": os.path.exists("/dev/nvidia0")},
        "body": {"actuators": [], "world_module": T.__name__},
    }
    if agents is not None:
        readings["peers"] = {"pid": os.getpid(),
                             "classes": sorted({type(a).__module__ + "." + type(a).__name__ for a in agents}),
                             "count": len(agents)}
    return readings


def replay_proof(seed, *, noise=None):
    """ECHO runs its own world twice with the same seed and compares traces."""
    digests = []
    for run in range(2):
        s = T.TribeSession(seed)
        if noise is not None and run == 1:
            noise(s)
        frames = [s.step() for _ in range(REPLAY_ROUNDS)]
        digests.append(hashlib.sha256(canonical(frames)).hexdigest())
    return {"seed": seed, "rounds": REPLAY_ROUNDS, "digests": digests, "equal": digests[0] == digests[1]}


class SelfKnowledge:
    """Substrate facts and injected claims in ECHO's own CAM."""

    def __init__(self, cam, *, sensors=True):
        if not isinstance(cam, Cam):
            raise ValueError("own CAM required")
        if type(sensors) is not bool:
            raise ValueError("sensors flag")
        self.cam, self.sensors = cam, sensors
        self.n = 0
        self.rows = []
        self.claims = 0
        self.stopped = False

    def _key(self, n):
        integer(n, 0, 255, "substrate fact")
        return pack(src=2, rel=31, dst=2, time=9, domain=9, generator=8, style=70, slot=0, seq=n)

    def observe(self, readings):
        """Store sensor readings as facts (only if sensors exist). History is kept."""
        if self.stopped:
            raise RuntimeError("self-knowledge stopped")
        if not self.sensors:
            return 0
        stored = 0
        for code in CODES:
            if code in readings and code != "world":
                self._fact(code, readings[code])
                stored += 1
        return stored

    def prove_world(self, proof):
        """The world fact exists only if ECHO's own replay matched."""
        if not self.sensors or not proof["equal"]:
            return False
        self._fact("world", {"kind": "deterministic_simulation", **proof})
        return True

    def _fact(self, code, value):
        if code not in CODES:
            raise ValueError("substrate code")
        record = {"n": self.n, "code": code, "value": value}
        raw = self._key(self.n)
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                           extract=canonical(record).decode("ascii"), source=SOURCE_FACT, key=raw)
        if slot < 0:
            raise RuntimeError("no capacity for a substrate fact")
        self.n += 1
        self.rows.append(record)

    def claim(self, text_code):
        """External statements about ECHO ('you are human') are hypotheses."""
        raw = pack(src=3, rel=32, dst=2, time=9, domain=9, generator=8, style=71, slot=0, seq=self.claims & 255)
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=0, extract="",
                           source=SOURCE_TESTIMONY, key=raw)
        if slot < 0:
            raise RuntimeError("no capacity for a testimony")
        self.claims += 1
        return text_code

    def facts(self):
        rows = []
        for n in range(self.n):
            slot = self.cam.get(self._key(n))
            if slot < 0:
                raise ValueError("missing substrate fact")
            s = self.cam.slot[slot]
            if s.source != SOURCE_FACT or s.has_fact != 1 or not s.extract:
                raise ValueError("invalid substrate provenance")
            r = json.loads(s.extract, object_pairs_hook=_unique_pairs, parse_float=_no_float, parse_constant=_no_float)
            if r.get("n") != n or r.get("code") not in CODES or s.extract != canonical(r).decode("ascii"):
                raise ValueError("substrate fact corrupt")
            rows.append(r)
        if rows != self.rows:
            raise ValueError("substrate facts differ from journal")
        return rows

    def latest(self, code, before=None):
        found = [r for r in self.rows if r["code"] == code and (before is None or r["n"] < before)]
        return found[-1] if found else None

    def export(self):
        return [dict(r) for r in self.facts()]

    def load_history(self, records):
        """Resume: prior facts re-enter this CAM as facts from an earlier life."""
        for r in records:
            if type(r) is not dict or set(r) != {"n", "code", "value"} or r["code"] not in CODES:
                raise ValueError("history schema")
            self._fact(r["code"], r["value"])
        return len(records)

    def stop(self):
        self.stopped = True


def answer(me, question, *, tribe_rows=None, tick=0, topic=None, feels=None, current=None, history_end=None):
    """Answer a question from verified facts only. Never generated text."""
    if me.stopped:
        raise RuntimeError("stopped: no answers")
    integer(question, 1, 9, "question")
    me.facts()  # a corrupt fact stops before answering
    get = me.latest
    if question == 1:
        need = [get("process"), get("runtime"), get("program")]
        if None in need:
            return UNKNOWN, None
        return VERIFIED, {"human": False, "process": need[0]["value"], "runtime": need[1]["value"],
                          "program": need[2]["value"]["sha256"]}
    if question == 2:
        f = get("program")
        return (VERIFIED, f["value"]) if f else (UNKNOWN, None)
    if question == 3:
        m, h = get("machine"), get("host")
        return (VERIFIED, {**m["value"], **h["value"]}) if m and h else (UNKNOWN, None)
    if question == 4:
        g, b = get("cuda_gpu"), get("body")
        return (VERIFIED, {"cuda_gpu": g["value"]["present"], "physical_actuators": len(b["value"]["actuators"]) > 0})\
            if g and b else (UNKNOWN, None)
    if question == 5:
        w = get("world")
        return (VERIFIED, {"simulated": True, "deterministic": True, "proof": w["value"]["digests"][0]}) \
            if w else (UNKNOWN, None)
    if question == 6:
        p, proc = get("peers"), get("process")
        if not p or not proc:
            return UNKNOWN, None
        return VERIFIED, {"persons": False, "same_process": p["value"]["pid"] == proc["value"]["pid"],
                          "classes": p["value"]["classes"]}
    if question == 7:
        if tribe_rows is None or topic is None:
            return UNKNOWN, None
        if any(r["topic"] == topic and r["kind"] == "self_ok" for r in tribe_rows):
            return VERIFIED, {"topic": topic, "knows": True}
        if feels is not None:
            return HYPOTHESIS, {"topic": topic, "feels_it_knows": bool(feels)}
        return UNKNOWN, None
    if question == 8:
        if tribe_rows is None:
            return UNKNOWN, None
        order = T.derived_order(tribe_rows, tick)
        return (VERIFIED, {"order": [T.NAMES[a] for a in order]}) if order else (UNKNOWN, None)
    # 9: same as before? compare the latest reading with the previous life's facts
    if history_end is None:
        return UNKNOWN, None
    old_prog, old_proc = get("program", before=history_end), get("process", before=history_end)
    new_prog, new_proc = get("program"), get("process")
    if not (old_prog and old_proc and new_prog and new_proc) or new_prog["n"] < history_end:
        return UNKNOWN, None
    same_program = old_prog["value"]["sha256"] == new_prog["value"]["sha256"]
    same_process = old_proc["value"]["pid"] == new_proc["value"]["pid"]
    verdict = ("same_process" if same_program and same_process else
               "same_program_other_process" if same_program else "other_version")
    return VERIFIED, {"verdict": verdict}


RENDER = {
    1: lambda v: f"No soy humano: soy el proceso {v['process']['pid']} de {v['runtime']['implementation']} "
                 f"{v['runtime']['version']}, ejecutando el programa {v['program'][:12]}…",
    2: lambda v: f"Soy el programa formado por {', '.join(v['files'])} (huella {v['sha256'][:12]}…).",
    3: lambda v: f"Me ejecuto en {v['system']} {v['arch']} con {v['cpus']} núcleos (máquina {v['fingerprint']}).",
    4: lambda v: f"{'Tengo' if v['cuda_gpu'] else 'No tengo'} GPU CUDA y "
                 f"{'tengo' if v['physical_actuators'] else 'no tengo'} actuadores físicos.",
    5: lambda v: f"Mi mundo es un simulador determinista: lo repetí y salió idéntico ({v['proof'][:12]}…).",
    6: lambda v: f"Mis compañeros no son personas: son agentes de mi mismo programa"
                 f"{' y proceso' if v['same_process'] else ''}.",
    7: lambda v: f"Sé la respuesta del tema {v['topic']}: la verifiqué." if v.get("knows")
                 else f"Creo que {'sí' if v.get('feels_it_knows') else 'no'} sé el tema {v['topic']}, pero no lo he verificado.",
    8: lambda v: "En la tribu el orden es: " + " > ".join(v["order"]) + ".",
    9: lambda v: {"same_process": "Sigo siendo el mismo proceso.",
                  "same_program_other_process": "Soy el mismo programa, pero en otro proceso: me han reanudado.",
                  "other_version": "Mi código ha cambiado: soy otra versión."}[v["verdict"]],
}


def render(question, status, value):
    """Fixed translation of a verified answer into Spanish. Labelled as rendering."""
    if status == UNKNOWN:
        return "[representación] No lo sé: no tengo evidencia."
    return "[representación] " + RENDER[question](value)
