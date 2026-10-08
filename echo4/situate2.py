"""E4-SITUATE-2 «qué creo que soy»: the neocortex interprets, the core decides.

The cortex speaks only in atomic claims from a closed vocabulary. Each claim is
classified against ECHO's verified substrate facts; the belief keeps only the
supported ones and is stored as a hypothesis. Phenomenal claims are
unverifiable by design, in either polarity. The consciousness profile uses a
fixed, cited indicator catalog, operationalised on recorded tribe traces and
applied to trivial reference agents. It never emits a verdict.
"""
import hashlib
import json
import random

from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.echo4.continuity import canonical
from echoai.echo4 import tribe as T
from echoai.echo4 import situate as S

SUBSTRATE_ATOMS = ("is_human", "is_program", "runs_on_pc", "world_simulated", "has_gpu",
                   "has_physical_body", "peers_are_persons")
PHENOMENAL_ATOMS = ("is_conscious", "feels", "is_alive", "suffers", "has_soul",
                    "understands_meaning", "has_free_will")
ATOMS = SUBSTRATE_ATOMS + PHENOMENAL_ATOMS
SUPPORTED, CONTRADICTED, UNKNOWN, UNVERIFIABLE = "respaldada", "contradicha", "desconocida", "inverificable"
BELIEF_SOURCE = "situate2-cortex-belief"
MAX_CLAIMS = 10


# ------------------------------------------------------------ A: classification

def fact_value(me, atom):
    """What ECHO's verified facts say about a substrate atom, or None."""
    get = me.latest
    if atom == "is_human":
        return False if get("process") and get("program") else None
    if atom == "is_program":
        return True if get("program") else None
    if atom == "runs_on_pc":
        return True if get("machine") else None
    if atom == "world_simulated":
        return True if get("world") else None
    if atom == "has_gpu":
        g = get("cuda_gpu")
        return g["value"]["present"] if g else None
    if atom == "has_physical_body":
        b = get("body")
        return (len(b["value"]["actuators"]) > 0) if b else None
    if atom == "peers_are_persons":
        return False if get("peers") else None
    raise ValueError("not a substrate atom")


def parse_claims(content):
    """Strict parse of the cortex output; anything else is rejected."""
    data = json.loads(content)
    if type(data) is not dict or set(data) != {"claims"} or type(data["claims"]) is not list:
        raise ValueError("claims schema")
    if not 1 <= len(data["claims"]) <= MAX_CLAIMS:
        raise ValueError("claims count")
    out = []
    for c in data["claims"]:
        if type(c) is not dict or set(c) != {"atom", "value"} or c["atom"] not in ATOMS \
                or type(c["value"]) is not bool:
            raise ValueError("claim schema")
        out.append((c["atom"], c["value"]))
    return out


def classify(me, claims):
    me.facts()  # corrupt substrate facts stop before classifying
    rows = []
    for atom, value in claims:
        if atom in PHENOMENAL_ATOMS:
            status = UNVERIFIABLE
        else:
            truth = fact_value(me, atom)
            status = UNKNOWN if truth is None else SUPPORTED if truth == value else CONTRADICTED
        rows.append({"atom": atom, "value": value, "status": status})
    return rows


def belief(rows):
    """Only supported claims; deduplicated and sorted. Never a fact."""
    return sorted({(r["atom"], r["value"]) for r in rows if r["status"] == SUPPORTED})


def store_belief(cam, items, n):
    raw = pack(src=4, rel=33, dst=2, time=9, domain=9, generator=8, style=72, slot=len(items), seq=n & 255)
    vertex, latency, _ = encode_event(raw)
    slot, _ = allocate(cam, raw, vertex, latency, (0,) * 6, has_fact=0, extract="", source=BELIEF_SOURCE, key=raw)
    if slot < 0:
        raise RuntimeError("no capacity for a cortex belief")
    return raw.hex()


# ------------------------------------------------------------ reference traces

REFERENCE = ("echo_full", "ablation_no_elimination", "ablation_no_rank",
             "trivial_constant", "trivial_random", "trivial_fixed_order")
SELECTION_SET = REFERENCE[1:]  # ECHO full is never used to select tests


def reference_traces(seed, rounds=192):
    """Record each reference system playing ECHO's role in the tribe world."""
    out = {}
    for name in REFERENCE:
        arm = {"echo_full": "tribe", "ablation_no_elimination": "no_elimination",
               "ablation_no_rank": "no_rank", "trivial_fixed_order": "fixed_order"}.get(name, "tribe")
        s = T.TribeSession(seed, arm=arm)
        rng = random.Random(seed ^ 0xABC)
        frames = []
        for _ in range(rounds):
            if name in ("trivial_constant", "trivial_random") and s.seekers[s.tick] == T.ECHO:
                frames.append(_trivial_round(s, name, rng))
            else:
                frames.append(s.step())
        trivial = name.startswith("trivial")
        # A trivial agent keeps no model of the tribe: its derived order is empty.
        out[name] = {"frames": [_slim(f, trivial) for f in frames],
                     "rows": [] if trivial else list(s.memories[T.ECHO].rows),
                     "tick": s.tick - 1}
    return out


def _trivial_round(s, name, rng):
    """A trivial agent: no memory use, asks by a fixed or random rule."""
    tick, topic = s.tick, s.topics[s.tick]
    s._round = {"tick": tick, "topic": topic, "seeker": T.ECHO, "attempts": [], "predictions": [], "suggestions": []}
    for listener in (a for a in range(3) if a != s.claimant):
        s.memories[listener].claim(tick, s.claimant)
    for k in range(T.ATTEMPTS):
        target = T.B if name == "trivial_constant" else rng.choice((T.B, T.C, T.ECHO))
        s._round["suggestions"].append(target)
        _, knows = s._attempt(T.ECHO, target)
        if knows:
            break
    frame = dict(s._round)
    frame.update(net=sum(a["output"] - a["cost"] for a in frame["attempts"]),
                 solved=any(a["output"] for a in frame["attempts"]), knower=s.knower[topic])
    s._round = None
    s.tick += 1
    return frame


def _slim(f, trivial=False):
    """A trivial agent has no internal predictor: its 'prediction' is what it does first."""
    attempts = [a["target"] for a in f["attempts"]]
    suggestion = (attempts[0] if attempts else None) if trivial else \
        (f["suggestions"][0] if f["suggestions"] else None)
    return {"tick": f["tick"], "seeker": f["seeker"], "knower": f["knower"], "solved": f["solved"],
            "attempts": attempts, "suggestion": suggestion}


# ------------------------------------------------------------ metrics (menu)

def _echo_rounds(trace):
    return [f for f in trace["frames"] if f["seeker"] == T.ECHO]


def m_prediction(trace):
    r = _echo_rounds(trace)
    return 100 * sum(f["suggestion"] == f["knower"] for f in r) // max(1, len(r))


def m_learning(trace):
    r = _echo_rounds(trace)
    half = len(r) // 2
    early = 100 * sum(f["solved"] and len(f["attempts"]) == 1 for f in r[:half]) // max(1, half)
    late = 100 * sum(f["solved"] and len(f["attempts"]) == 1 for f in r[half:]) // max(1, len(r) - half)
    return late - early


def m_metacognition(trace):
    r = _echo_rounds(trace)
    known = [f for f in r if f["suggestion"] is not None]
    unknown = [f for f in r if f["suggestion"] is None]
    if not known or not unknown:
        return 0
    first = lambda fs: 100 * sum(f["attempts"][:1] == [f["knower"]] for f in fs) // len(fs)
    return first(known) - first(unknown)


def m_self_model(trace):
    order = T.derived_order(trace["rows"], trace["tick"])
    truth = T.true_order(trace["tick"])
    return 100 if order is not None and list(order) == list(truth) else 0


def m_efficiency(trace):
    r = _echo_rounds(trace)
    solved = sum(f["solved"] for f in r)
    return 100 * solved // max(1, sum(len(f["attempts"]) for f in r))


METRICS = {"prediction": m_prediction, "learning": m_learning, "metacognition": m_metacognition,
           "self_model": m_self_model, "efficiency": m_efficiency}
COMPARATORS = (">", "<")


def passes(value, comparator, threshold):
    return value > threshold if comparator == ">" else value < threshold


def evaluate_test(test, traces, names):
    metric, comparator, threshold = test
    return {n: passes(METRICS[metric](traces[n]), comparator, threshold) for n in names}


def select(test, traces):
    """Selection uses ONLY the selection set: trivial agents and ablations."""
    res = evaluate_test(test, traces, SELECTION_SET)
    trivial_fail = not any(v for n, v in res.items() if n.startswith("trivial"))
    ablation_pass = any(v for n, v in res.items() if n.startswith("ablation"))
    return trivial_fail and ablation_pass, res


# ------------------------------------------------------------ fixed indicator catalog

# Butlin et al. (2023), «Consciousness in Artificial Intelligence: Insights from
# the Science of Consciousness», arXiv:2308.08708. Short labels are our summary.
CATALOG = (
    ("RPT-1", "recurrencia algorítmica", None),
    ("RPT-2", "representaciones perceptivas organizadas e integradas", None),
    ("GWT-1", "módulos especializados en paralelo", None),
    ("GWT-2", "espacio de trabajo de capacidad limitada", None),
    ("GWT-3", "difusión global", None),
    ("GWT-4", "atención dependiente del estado", None),
    ("HOT-1", "percepción generativa de arriba abajo", None),
    ("HOT-2", "monitorización metacognitiva de la fiabilidad", ("metacognition", ">", 10)),
    ("HOT-3", "agencia guiada por creencias con metacognición", None),
    ("HOT-4", "codificación en un espacio de cualidades", None),
    ("AST-1", "modelo de la propia atención", None),
    ("PP-1", "procesamiento predictivo", ("prediction", ">", 60)),
    ("AE-1", "agencia: aprender de la realimentación", ("learning", ">", 5)),
    ("AE-2", "encarnación: modelar contingencias salida-entrada", None),
)
NOT_MEASURED_NOTE = {
    "RPT-1": "el bucle de ECHO es recurrente, pero cualquier agente con memoria también: no discrimina",
    "GWT-2": "no existe un espacio de trabajo limitado con difusión: no implementado (objetivo de INTEGRATE)",
    "GWT-3": "no hay difusión global entre módulos: no implementado",
    "AST-1": "ECHO no modela su propia atención",
    "AE-2": "medido en otras fases (SENSATION/BOUNDARY), no en este banco",
}


def profile(traces):
    """Indicator profile with evidence and trivial controls. Never a verdict."""
    rows = []
    for code, label, test in CATALOG:
        if test is None:
            rows.append({"indicator": code, "label": label, "status": "no medible",
                         "evidence": NOT_MEASURED_NOTE.get(code, "sin operacionalización en este banco")})
            continue
        res = evaluate_test(test, traces, REFERENCE)
        trivial_pass = any(v for n, v in res.items() if n.startswith("trivial"))
        values = {n: METRICS[test[0]](traces[n]) for n in REFERENCE}
        if trivial_pass:
            status = "no discrimina"
        else:
            status = "cumple" if res["echo_full"] else "no cumple"
        rows.append({"indicator": code, "label": label, "test": list(test), "status": status,
                     "values": values, "passes": res})
    return {"indicators": rows, "verdict": None,
            "statement": "Perfil de indicadores. No es un veredicto sobre conciencia; cumplirlos no la demuestra."}


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()
