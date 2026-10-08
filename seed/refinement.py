"""Bounded multi-view program synthesis; only demonstrations establish facts.

No model, executable source, global DSL mutation or parameter training. Optional
model proposals are closed DSL programs and face the same exact verifier.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json

from echoai.seed import dsl
from echoai.seed.learn import Library

GEOMETRY = {name: getattr(dsl, name) for name in
            ("rot90", "rot180", "rot270", "fliplr", "flipud", "transpose")}
VIEWS = ((), ("rot90",), ("rot180",), ("rot270",), ("fliplr",),
         ("flipud",), ("transpose",), ("rot90", "flipud"))
PROBE = dsl.G([[0, 1, 2], [3, 4, 5]])


def transform(grid, view):
    for name in view:
        grid = GEOMETRY[name](grid)
    return grid


def inverse(view):
    return next(v for v in VIEWS if transform(transform(PROBE, view), v) == PROBE)


def grid(rows):
    if type(rows) not in (list, tuple) or not rows:
        raise ValueError("nonempty grid required")
    if any(type(row) not in (list, tuple) or any(type(v) is not int or not 0 <= v <= 9 for v in row) for row in rows):
        raise ValueError("grid cells must be integer colours 0–9")
    return dsl.G(rows)


def solver_input(task):
    """Do not copy, inspect, serialize or pass on any test output."""
    if not task.get("train") or not task.get("test"):
        raise ValueError("demonstrations and test inputs required")
    if len(task["train"]) > 10 or len(task["test"]) > 10:
        raise ValueError("at most ten demonstrations and ten test inputs")
    return {"train": [{"input": grid(p["input"]), "output": grid(p["output"])} for p in task["train"]],
            "test": [{"input": grid(p["input"])} for p in task["test"]]}


def canonical_program(program, library):
    """Collapse adjacent geometric identities; don't count the same view twice."""
    steps = [tuple(s) for item in program for s in library.expand(item)]
    out, run = [], []

    def flush():
        if run:
            value = transform(PROBE, run)
            out.extend((name,) for name in next(v for v in VIEWS if transform(PROBE, v) == value))
            run.clear()

    for step in steps:
        if len(step) == 1 and step[0] in GEOMETRY:
            run.append(step[0])
        else:
            flush()
            out.append(step)
    flush()
    return tuple(out)


class RefinementLibrary(Library):
    """Import existing primitives and add four bounded object relations."""
    def moves(self, colors_in, colors_out):
        base = super().moves(colors_in, colors_out)
        relations = []
        for bg in sorted(colors_in):
            relations += [("objects_to_row", bg), ("marker_recolor", bg)]
            for color in sorted(colors_out - {bg}):
                relations += [("recolor_by_size", bg, color, "largest"),
                              ("recolor_by_size", bg, color, "smallest")]
        for color in sorted(colors_in | colors_out):
            relations += [("connect_color", color, "rows"), ("connect_color", color, "cols")]
        return base + relations

    def apply(self, g, item):
        if isinstance(item, str):
            return super().apply(g, item)
        name, *args = item
        if name == "objects_to_row":
            objs = dsl.objects(g, bg=args[0])
            if not objs:
                raise ValueError("no objects")
            return dsl.G([[color for color, cells in sorted(objs, key=lambda obj: (-len(obj[1]), obj[0]))]])
        if name == "marker_recolor":
            bg = args[0]
            objs = dsl.objects(g, bg=bg)
            markers = [(c, cells) for c, cells in objs if len(cells) == 1]
            if len(markers) != 1 or len(objs) < 2:
                raise ValueError("need one singleton marker and another object")
            color, cells = markers[0]
            y, x = cells[0]
            return dsl.G([[bg if (i, j) == (y, x) else color if v != bg else bg
                           for j, v in enumerate(row)] for i, row in enumerate(g)])
        if name == "recolor_by_size":
            bg, color, which = args
            objs = dsl.objects(g, bg=bg)
            if not objs:
                raise ValueError("no objects")
            size = (max if which == "largest" else min)(len(cells) for _, cells in objs)
            cells = {p for _, component in objs if len(component) == size for p in component}
            return dsl.G([[color if (i, j) in cells else v for j, v in enumerate(row)] for i, row in enumerate(g)])
        if name == "connect_color":
            color, axis = args
            src = dsl.transpose(g) if axis == "cols" else g
            rows = []
            for row in src:
                found = [i for i, v in enumerate(row) if v == color]
                rows.append([color if len(found) >= 2 and found[0] <= i <= found[-1] else v for i, v in enumerate(row)])
            out = dsl.G(rows)
            return dsl.transpose(out) if axis == "cols" else out
        return super().apply(g, item)


def execute(g, program, library):
    for step in program:
        g = library.apply(g, step)
    return grid(g)


def critique(outputs, targets):
    """Measured discrepancies, never a verbal guess about hidden reasoning."""
    detail = []
    for got, want in zip(outputs, targets):
        same_shape = (len(got), len(got[0])) == (len(want), len(want[0]))
        pixels = sum(a != b for ra, rb in zip(got, want) for a, b in zip(ra, rb)) if same_shape else None
        hist = Counter(v for row in got for v in row)
        target_hist = Counter(v for row in want for v in row)
        detail.append({"shape_matches": same_shape, "wrong_cells": pixels,
                       "color_count_error": sum(abs(hist[c] - target_hist[c]) for c in range(10)),
                       "object_count_error": abs(len(dsl.objects(got)) - len(dsl.objects(want))),
                       "exact": got == want})
    return detail


def quality(detail, targets, depth):
    return (sum(not d["shape_matches"] for d in detail),
            sum(1000 if d["wrong_cells"] is None else 1000 * d["wrong_cells"] // (len(t) * len(t[0]))
                for d, t in zip(detail, targets)),
            sum(d["object_count_error"] for d in detail), sum(d["color_count_error"] for d in detail), depth)


def refinements(beam, moves, max_depth):
    """Use failed hypotheses as seeds for append, replacement and deletion."""
    for node in beam:
        program = node[1]
        if len(program) < max_depth:
            for move in moves:
                yield program + (move,)
    for node in beam:
        program = node[1]
        for i in range(len(program)):
            for move in moves:
                yield program[:i] + (move,) + program[i + 1:]
            yield program[:i] + program[i + 1:]


def solve(task, library=None, max_trials=4000, max_depth=4, beam_width=12,
          rounds=4, max_hypotheses=32, views=True, proposals=(), journal=None):
    """Search several views under ONE global program-trial budget.

    Returns up to two candidate batches; exact demonstration fit never certifies
    a test answer. No wall-clock cutoff and no learned-library updates.
    """
    bounds = ((max_trials, 0, 100000), (max_depth, 1, 8), (beam_width, 1, 64),
              (rounds, 1, 16), (max_hypotheses, 1, 128))
    if any(type(n) is not int or not lo <= n <= hi for n, lo, hi in bounds):
        raise ValueError("bounded integer search limits required")
    public = solver_input(task)
    supplied = library or RefinementLibrary()
    library = deepcopy(supplied)             # no sleep/prior/weight updates
    before = deepcopy(vars(supplied))
    train_inputs = tuple(p["input"] for p in public["train"])
    targets = tuple(p["output"] for p in public["train"])
    tests = tuple(p["input"] for p in public["test"])
    colors_in = set().union(*(dsl.palette(g) for g in train_inputs))
    colors_out = set().union(*(dsl.palette(g) for g in targets))
    moves = tuple(dict.fromkeys(tuple(m) if not isinstance(m, str) else m for m in library.moves(colors_in, colors_out)))
    allowed = set(moves)
    selected_views = VIEWS if views else VIEWS[:1]
    trials, primitive_steps, rejected = 0, 0, []
    seen, verified = set(), {}

    def note(kind, **data):
        if journal is not None:
            journal.write(kind=kind, agent="echo-grid-refinement", origin="DEVELOPMENT", **data)

    def evaluate(program, view, iteration):
        nonlocal trials, primitive_steps
        original = canonical_program(tuple((n,) for n in view) + program + tuple((n,) for n in inverse(view)), library)
        if original in seen or trials >= max_trials:
            return None
        seen.add(original)
        trials += 1
        try:
            outputs = []
            for g in train_inputs:
                primitive_steps += len(original)
                outputs.append(execute(g, original, library))
            outputs = tuple(outputs)
            errors = critique(outputs, targets)
            score = quality(errors, targets, len(program))
        except (ValueError, IndexError, ZeroDivisionError, KeyError):
            return None
        if all(d["exact"] for d in errors):
            try:
                predictions = tuple(execute(g, original, library) for g in tests)
                primitive_steps += len(original) * len(tests)
            except (ValueError, IndexError, ZeroDivisionError, KeyError):
                return None
            if len(verified) < max_hypotheses:
                verified[original] = predictions
                note("verified_hypothesis", iteration=iteration, view=list(view),
                     program=original, demonstrations=len(targets), test_verified=False)
        return score, program, errors

    # External proposals are data in this finite language, never Python source.
    seeds = []
    for proposal in proposals:
        try:
            if type(proposal) not in (list, tuple) or len(proposal) > max_depth:
                raise ValueError("bounded program list required")
            program = tuple(m if isinstance(m, str) else tuple(m) for m in proposal)
            if any(move not in allowed for move in program):
                raise ValueError("operation outside the task DSL")
            node = evaluate(program, (), 0)
            if node is not None:
                seeds.append(node)
        except (TypeError, ValueError) as exc:
            rejected.append(str(exc))
    identity = evaluate((), (), 0)
    if identity is not None:
        seeds.append(identity)
    beam = sorted(seeds, key=lambda n: (n[0], repr(n[1])))[:beam_width]
    if not beam:
        beam = [((0, 0, 0, 0, 0), (), [])]
    identity_quality = identity[0] if identity is not None else quality(critique(train_inputs, targets), targets, 0)
    beams = [list(beam) if not view else [(identity_quality, (), critique(train_inputs, targets))]
             for view in selected_views]
    iterations = 0
    for iteration in range(1, rounds + 1):
        if trials >= max_trials:
            break
        iterations = iteration
        # Interleave views one trial at a time instead of multiplying the budget.
        generators = [iter(refinements(b, moves, max_depth)) for b in beams]
        active = set(range(len(generators)))
        next_beams = [list(b) for b in beams]
        while active and trials < max_trials:
            for index in sorted(tuple(active)):
                try:
                    proposal = next(generators[index])
                except StopIteration:
                    active.remove(index)
                    continue
                node = evaluate(proposal, selected_views[index], iteration)
                if node is not None:
                    next_beams[index].append(node)
                    next_beams[index].sort(key=lambda n: (n[0], repr(n[1])))
                    del next_beams[index][beam_width:]
                if trials >= max_trials:
                    break
        beams = next_beams
        note("refinement_round", iteration=iteration, trials=trials,
             verified=len(verified), best_errors=[b[0][2] for b in beams])
    groups = {}
    for program, predictions in verified.items():
        groups.setdefault(predictions, []).append(program)
    ranked = sorted(groups.items(), key=lambda pair: (-len(pair[1]), min(len(p) for p in pair[1]), repr(pair[0])))
    attempts = [[[list(row) for row in g] for g in predictions] for predictions, _ in ranked[:2]]
    winners = [min(programs, key=lambda p: (len(p), repr(p))) for _, programs in ranked[:2]]
    status = "NO_VERIFIED_PROGRAM" if not ranked else "AMBIGUOUS" if len(ranked) > 1 else "CONSISTENT"
    result = {"status": status, "program": list(winners[0]) if winners else None,
              "programs": [list(p) for p in winners], "predictions": attempts[0] if attempts else [],
              "attempts": attempts, "test_ok": None, "test_verified": False,
              "trials": trials, "primitive_steps_upper_count": primitive_steps, "iterations": iterations,
              "verified_programs": len(verified), "prediction_groups": len(ranked),
              "support": [len(programs) for _, programs in ranked[:2]], "rejected_proposals": rejected,
              "budget_exhausted": trials >= max_trials, "model_calls": 0, "weight_updates": 0,
              "input_sha256": hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()}
    assert vars(supplied) == before, "solver altered the supplied library"
    note("refinement_result", status=status, trials=trials, verified=len(verified),
         prediction_groups=len(ranked), test_verified=False)
    return result
