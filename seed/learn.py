"""ECHO-SEED · wake (search with the library) and sleep (compress solved programs into concepts).

Wake: best-first search over programs = sequences of library items (primitives with colour
arguments, or learned concepts). A program is VERIFIED only if it reproduces every solved example
of the task; only verified programs enter the journal (facts). Sleep: sub-sequences that appear in
verified programs of at least two different tasks become new concepts (cost 1 in later searches),
so what took 3 steps yesterday takes 1 today. Nothing unverified is ever stored as a concept.
"""
import hashlib
import heapq
import itertools
import json
import time
from collections import Counter

from echoai.seed import dsl


def task_grids(task):
    train = [(dsl.G(p["input"]), dsl.G(p["output"])) for p in task["train"]]
    test = [(dsl.G(p["input"]), dsl.G(p["output"]) if "output" in p else None) for p in task["test"]]
    return train, test


def distance(state, targets):
    d = 0.0
    for g, t in zip(state, targets):
        if len(g) != len(t) or len(g[0]) != len(t[0]):
            d += 1.0
        else:
            d += sum(a != b for ra, rb in zip(g, t) for a, b in zip(ra, rb)) / (len(t) * len(t[0]))
    return d / len(targets)


class Library:
    """Primitives (fixed) plus learned concepts: {id: {"steps": [...], "tasks": [...], "round": n}}."""

    def __init__(self, concepts=None, prior=None):
        self.concepts = dict(concepts or {})
        self.prior = dict(prior or {})                        # S2 intuition: item key -> uses in verified programs
        self.guide = None                                     # S2 neural intuition for THIS task: name -> probability

    @staticmethod
    def key(item):
        return item if isinstance(item, str) else item[0]

    def step_cost(self, item):
        """Integer cost of one program step: what worked often is cheap, what never worked is dear."""
        if self.guide is not None and not (isinstance(item, str) or str(item[0]).startswith("@")):
            p = self.guide.get(item[0], 0.0)                  # the network only turns into 1, 2 or 3
            return 1 if p >= 0.3 else 2 if p >= 0.05 else 3
        if not self.prior:
            return 1
        n = self.prior.get(self.key(item), 0)
        return 1 if n >= 3 else 2 if n >= 1 else 3

    def expand(self, item):
        """Concept id -> primitive steps (recursively); a primitive step is returned as is.
        A parametric concept is called as ("@kNNN", c0, c1...): its "$i" slots take those colours."""
        if isinstance(item, str) and item in self.concepts:
            out = []
            for s in self.concepts[item]["steps"]:
                out += self.expand(s)
            return out
        if not isinstance(item, str) and str(item[0]).startswith("@"):
            args = list(item[1:])
            out = []
            for s in self.concepts[item[0][1:]]["steps"]:
                bound = [args[int(v[1:])] if isinstance(v, str) and v.startswith("$") else v for v in s]
                out += self.expand(tuple(bound))
            return out
        return [tuple(item)]

    def apply(self, g, item):
        for step in self.expand(item):
            g = dsl.apply_step(g, step)
        return g

    def moves(self, colors_in, colors_out):
        moves = [(name,) for name in dsl.NO_ARG]
        cols = sorted(colors_in | colors_out)
        moves += [(name, c) for name in dsl.ONE_COLOR for c in cols]
        moves += [("recolor", a, b) for a in sorted(colors_in) for b in sorted(colors_out) if a != b]
        moves += [("swap", a, b) for a, b in itertools.combinations(sorted(colors_in), 2)]
        concept_moves = []
        for cid, c in self.concepts.items():
            slots = c.get("slots", 0)
            if not slots:
                concept_moves.append(cid)
            else:                                             # S2: bind each slot to a colour of this task
                concept_moves += [("@" + cid,) + combo for combo in itertools.product(cols, repeat=slots)]
        moves = concept_moves + moves                         # concepts first: they were useful before
        if self.guide is not None:
            moves.sort(key=lambda m: -int(1000 * self.guide.get(self.key(m), 1.0 if (isinstance(m, str) or str(m[0]).startswith("@")) else 0.0)))
        elif self.prior:
            moves.sort(key=lambda m: -self.prior.get(self.key(m), 0))   # stable: ties keep the order
        return moves

    def sha(self):
        return hashlib.sha256(json.dumps(self.concepts, sort_keys=True).encode()).hexdigest()


def solve(task, library, max_expansions=400, max_depth=4, seconds=None):
    """Deterministic: only the expansion budget stops the search (a wall-clock limit made results
    depend on CPU load; removed 2026-09-25). `seconds` is kept for interactive use only."""
    """-> {"program": [...] or None, "expansions": n, "test_ok": bool|None, "predictions": [...]}"""
    train, test = task_grids(task)
    inputs, targets = tuple(g for g, _ in train), tuple(t for _, t in train)
    colors_in = set().union(*(dsl.palette(g) for g in inputs))
    colors_out = set().union(*(dsl.palette(t) for t in targets))
    moves = library.moves(colors_in, colors_out)
    start = time.monotonic()
    tie = itertools.count()
    frontier = [(distance(inputs, targets), next(tie), inputs, [], 0)]
    seen = {inputs}
    expansions = 0
    while frontier and expansions < max_expansions and (seconds is None or time.monotonic() - start < seconds):
        _, _, state, prog, cost = heapq.heappop(frontier)
        expansions += 1
        if len(prog) >= max_depth:
            continue
        for mv in moves:
            item = mv
            try:
                nxt = tuple(library.apply(g, item) for g in state)
            except (ValueError, IndexError, ZeroDivisionError):
                continue
            if nxt in seen:
                continue
            seen.add(nxt)
            nprog = prog + [item]
            if nxt == targets:
                return _finish(task, library, nprog, expansions, test)
            ncost = cost + library.step_cost(item)
            heapq.heappush(frontier, (ncost + 3 * distance(nxt, targets), next(tie), nxt, nprog, ncost))
    return {"program": None, "expansions": expansions, "test_ok": None, "predictions": []}


def _finish(task, library, prog, expansions, test):
    preds, ok = [], True
    for g, want in test:
        try:
            out = g
            for item in prog:
                out = library.apply(out, item)
        except (ValueError, IndexError, ZeroDivisionError):
            out = None
        preds.append([list(r) for r in out] if out else None)
        ok = ok and want is not None and out == want
    return {"program": [list(p) if isinstance(p, tuple) else p for p in prog], "expansions": expansions,
            "test_ok": ok if all(w is not None for _, w in test) else None, "predictions": preds}


def prior_from(verified):
    """S2 intuition: how many verified programs used each primitive name or concept id."""
    c = Counter()
    for prog in verified.values():
        for item in {Library.key(p if isinstance(p, str) else tuple(p)) for p in prog}:
            c[item] += 1
    return dict(c)


def sleep(library, verified, round_no, max_new=12, min_tasks=2):
    """verified: {task_id: program}. Adds concepts for sub-sequences shared by >= min_tasks tasks."""
    counts, where = Counter(), {}
    for tid, prog in verified.items():
        key_prog = [p if isinstance(p, str) else tuple(p) for p in prog]
        subs = set()
        for n in (2, 3):
            for i in range(len(key_prog) - n + 1):
                subs.add(tuple(key_prog[i:i + n]))
        for s in subs:
            counts[s] += 1
            where.setdefault(s, []).append(tid)
    norm = lambda seq: json.dumps([x if isinstance(x, str) else list(x) for x in seq])
    known = {norm(c["steps"]) for c in library.concepts.values()}
    added = []
    for sub, n in sorted(counts.items(), key=lambda kv: (-kv[1] * len(kv[0]), str(kv[0]))):
        if n < min_tasks or len(added) >= max_new or norm(sub) in known:
            continue
        cid = "k%03d" % (len(library.concepts) + 1)
        library.concepts[cid] = {"steps": [s if isinstance(s, str) else list(s) for s in sub],
                                 "tasks": sorted(where[sub]), "round": round_no}
        added.append(cid)
    added += sleep_parametric(library, verified, round_no, max_new=max_new, min_tasks=min_tasks)
    return added


def _slotify(seq):
    """Replace the colour arguments of a step sequence by slots "$0", "$1"… (same colour, same slot)."""
    slots, out = {}, []
    for step in seq:
        if isinstance(step, str):
            out.append(step)
            continue
        name, args = step[0], step[1:]
        out.append([name] + ["$%d" % slots.setdefault(a, len(slots)) for a in args])
    return out, [c for c, _ in sorted(slots.items(), key=lambda kv: kv[1])]


def sleep_parametric(library, verified, round_no, max_new=12, min_tasks=2, max_slots=2):
    """S2: sub-sequences with the same shape in >= min_tasks tasks but DIFFERENT colours become one
    concept with colour slots ("recolour X to Y" learned from recolour 1->2 and recolour 3->5)."""
    shapes, where, binds = Counter(), {}, {}
    for tid, prog in verified.items():
        steps = [p if isinstance(p, str) else tuple(p) for p in prog]
        seen = set()
        for n in (2, 3):                                       # one step is just a primitive with its colours
            for i in range(len(steps) - n + 1):
                sub = steps[i:i + n]
                if all(isinstance(x, str) or len(x) == 1 for x in sub):
                    continue                                   # no colours: the fixed concepts cover it
                shape, colours = _slotify(sub)
                key = json.dumps(shape)
                if key in seen or not 1 <= len(colours) <= max_slots:
                    continue
                seen.add(key)
                shapes[key] += 1
                where.setdefault(key, []).append(tid)
                binds.setdefault(key, set()).add(tuple(colours))
    known = {json.dumps(c["steps"]) for c in library.concepts.values()}
    added = []
    for key, n in sorted(shapes.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < min_tasks or len(binds[key]) < 2 or key in known or len(added) >= max_new:
            continue                                           # needs >= 2 different colourings
        shape = json.loads(key)
        cid = "k%03d" % (len(library.concepts) + 1)
        library.concepts[cid] = {"steps": shape, "slots": len(next(iter(binds[key]))),
                                 "tasks": sorted(where[key]), "round": round_no}
        added.append(cid)
    return added
