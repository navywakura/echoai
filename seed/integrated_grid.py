"""Additive ARC grid candidate: 3E receipts, cached synthesis and bounded views.

No test outputs are consumed. All arms share the same executed-program budget;
primitive work, cache use and memory retrieval are separately recorded.
"""
from __future__ import annotations

from copy import deepcopy
import itertools

from echoai.seed import dsl
from echoai.seed.refinement import (GEOMETRY, RefinementLibrary, VIEWS, canonical_program,
                                   inverse, solver_input, transform)
from seed.arc_memory import sha


def error_score(outputs, targets):
    shape = sum((len(a),len(a[0])) != (len(b),len(b[0])) for a,b in zip(outputs,targets))
    pixels = sum(1000 if (len(a),len(a[0])) != (len(b),len(b[0])) else
                 1000*sum(x!=y for ra,rb in zip(a,b) for x,y in zip(ra,rb))//(len(b)*len(b[0]))
                 for a,b in zip(outputs,targets))
    palette = sum(len(dsl.palette(a)^dsl.palette(b)) for a,b in zip(outputs,targets))
    return (shape, pixels, palette)


def solve(task, library=None, *, memory=None, guide=None, max_trials=2000, max_depth=4,
          beam_width=12, views=True, refinement=True, consistency=True, memory_limit=24,
          journal=None, verification_window=96):
    if not 1 <= max_trials <= 20000 or not 1 <= max_depth <= 6 or not 1 <= beam_width <= 32:
        raise ValueError("bounded search required")
    if not 0 <= verification_window <= max_trials or not 1 <= memory_limit <= 256:
        raise ValueError("bounded verification and retrieval required")
    public = solver_input(task)
    lib = deepcopy(library or RefinementLibrary())
    train = tuple(p["input"] for p in public["train"])
    targets = tuple(p["output"] for p in public["train"])
    tests = tuple(p["input"] for p in public["test"])
    incoming = set().union(*(dsl.palette(g) for g in train))
    outgoing = set().union(*(dsl.palette(g) for g in targets))
    if guide is not None:
        lib.guide = guide.probs(public)
    moves = tuple(dict.fromkeys(tuple(m) if not isinstance(m,str) else m for m in lib.moves(incoming,outgoing)))
    allowed = set(moves)
    metrics = {"trials": 0, "primitive_calls": 0, "cache_hits": 0, "invalid": 0,
               "memory_reads": 0, "memory_verified": 0, "view_trials": 0,
               "refinement_trials": 0, "first_solution_trial": None}
    # Cache includes every demonstration and every test input; two programs are
    # not merged merely because they agree on demonstrations.
    prefix_cache = {(): train+tests}
    attempted = set()
    valid = {}
    valid_origin = {}
    nodes = []
    counter = itertools.count()

    def exhausted():
        first = metrics["first_solution_trial"]
        return metrics["trials"] >= max_trials or (first is not None and metrics["trials"] >= first+verification_window)

    def note(kind, **data):
        if journal is not None:
            journal.write(kind=kind, agent="echo45-integrated-grid", origin="DEVELOPMENT", **data)

    def execute(program):
        if program in prefix_cache:
            metrics["cache_hits"] += 1
            return prefix_cache[program]
        previous = execute(program[:-1])
        if previous is None:
            prefix_cache[program] = None
            return None
        values = []
        try:
            for g in previous:
                metrics["primitive_calls"] += 1
                values.append(lib.apply(g, program[-1]))
        except (ValueError, IndexError, ZeroDivisionError, KeyError):
            prefix_cache[program] = None
            return None
        prefix_cache[program] = tuple(values)
        return tuple(values)

    def evaluate(program, origin, view=()):
        original = canonical_program(tuple((n,) for n in view)+tuple(program)+tuple((n,) for n in inverse(view)), lib)
        if original in attempted or exhausted():
            return None
        attempted.add(original)
        metrics["trials"] += 1
        metrics["view_trials"] += int(bool(view))
        metrics["refinement_trials"] += int(origin=="refinement")
        values = execute(original)
        if values is None:
            metrics["invalid"] += 1
            return None
        score = error_score(values[:len(train)], targets)
        if score == (0,0,0):
            valid[original] = values[len(train):]
            valid_origin[original] = origin
            if metrics["first_solution_trial"] is None:
                metrics["first_solution_trial"] = metrics["trials"]
            metrics["memory_verified"] += int(origin=="memory")
            note("verified_hypothesis", program=original, origin_detail=origin,
                 demonstrations=len(train), test_verified=False)
        if values == train+tests and score != (0,0,0):
            return None
        return (score, len(original), next(counter), tuple(program), tuple(view), original)

    selected_views = VIEWS if views else VIEWS[:1]
    evaluate((), "identity")
    if memory is not None:
        records = memory.candidates(public, memory_limit)
        metrics["memory_reads"] = len(records)
        for record in records:
            program = tuple(tuple(s) for s in record["program"])
            if len(program) > max_depth or any(step not in allowed for step in program):
                continue
            node = evaluate(program, "memory")
            if node:
                nodes.append(node)
        note("refinement_round", iteration=0, trials=metrics["trials"], verified=len(valid),
             memory_receipts=[r["receipt"] for r in records])

    # Every single primitive is considered before deeper search; prior/guide
    # determines ordering within that fixed budget, not truth or acceptance.
    for move in moves:
        node = evaluate((move,), "single")
        if node is not None and node[0] != (0,0,0):
            nodes.append(node)
        if exhausted():
            break
    if refinement and not exhausted():
        # Exact backward constraints for invertible final operations. These
        # use demonstration targets only and count their actual computation.
        preimages = {}
        for name in GEOMETRY:
            metrics["primitive_calls"] += len(targets)
            predecessor = tuple(transform(g,inverse((name,))) for g in targets)
            preimages.setdefault(predecessor,[]).append(name)
        for node in list(nodes):
            before = prefix_cache[node[5]][:len(train)]
            for name in preimages.get(before,()):
                candidate = node[5]+((name,),)
                if len(candidate)<=max_depth:
                    evaluate(candidate,"refinement")
                if exhausted():
                    break
            if exhausted():
                break
    view_start = metrics["trials"]
    for move in moves:
        for view in selected_views[1:]:
            if exhausted() or metrics["trials"]-view_start >= max_trials//5:
                break
            node = evaluate((move,), "single", view)
            if node is not None and node[0] != (0,0,0):
                nodes.append(node)
        if exhausted() or metrics["trials"]-view_start >= max_trials//5:
            break

    def select(nodes):
        chosen, states = [], set()
        for node in sorted(nodes):
            key = (prefix_cache[node[5]],node[4])
            if key in states:
                continue
            states.add(key)
            chosen.append(node)
            if len(chosen)==beam_width:
                break
        return chosen

    beam = select(nodes)
    for depth in range(2, max_depth+1):
        if not refinement or exhausted() or not beam:
            break
        next_beam = []
        # Round-robin over hypotheses avoids starving all but the first prefix.
        for move in moves:
            for node in beam:
                candidate = node[3]+(move,)
                if len(candidate) > max_depth:
                    continue
                new = evaluate(candidate, "refinement", node[4])
                if new is not None and new[0] != (0,0,0):
                    next_beam.append(new)
                if exhausted():
                    break
            if exhausted():
                break
        # Keep several outcomes per error score; don't freeze the identity or
        # an already solved hypothesis at the front of every subsequent round.
        beam = select(next_beam)
        note("refinement_round", iteration=depth, trials=metrics["trials"], verified=len(valid),
             best_errors=[list(n[0]) for n in beam[:3]])

    groups = {}
    for program, predictions in valid.items():
        groups.setdefault(predictions, []).append(program)
    if consistency:
        # Distinct operator families, not arbitrary numbers of equivalent views.
        ranked = sorted(groups.items(), key=lambda pair: (
            -len({tuple(step[0] for step in p) for p in pair[1]}),
            min(len(p) for p in pair[1]), repr(pair[0])))
    else:
        ranked = list(groups.items())
    programs = [min(ps,key=lambda p:(len(p),repr(p))) for _,ps in ranked[:2]]
    attempts = [[[list(row) for row in g] for g in predictions] for predictions,_ in ranked[:2]]
    result = {"status": "NO_VERIFIED_PROGRAM" if not ranked else "AMBIGUOUS" if len(ranked)>1 else "CONSISTENT",
              "program": programs[0] if programs else None, "programs": programs,
              "predictions": attempts[0] if attempts else [], "attempts": attempts,
              "verified_programs": len(valid), "prediction_groups": len(groups),
              "test_ok": None, "test_verified": False, "model_calls": 0, "weight_updates": 0,
              "input_sha256": sha(public), "metrics": metrics,
              "winning_origin": valid_origin.get(programs[0]) if programs else None}
    note("refinement_result", status=result["status"], trials=metrics["trials"], verified=len(valid),
         prediction_groups=len(groups), test_verified=False)
    return result
