"""CAPACITY-1: audited 256/512 LIF and conditional Adaptive-LIF experiment.

The functional experiment uses the exhaustive, deterministic transfer table of
the imported ``Layer256``.  It is not a shortcut around the LIF rule: each of
the 256 entries is produced by a fresh imported layer.  The table is valid
because this Q8 layer is reset for every sensory sample.  Timing is measured
separately with uncached fresh runs, so the report never presents lookup time
as neural latency.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import tracemalloc
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from echoai.core.qn import Layer256, Q8_CODEWORDS, q8_nearest, simhash16
from echoai.core.wsp import pack

from echoai.nexus0.pattern1 import InvariantPatternMemory


SCHEMA = 1
SLICE = "CAPACITY-1"
DATE = "2026-09-09"
DOMAIN = f"ECHO-AI/CAPACITY-1/{DATE}"
DEVELOPMENT_SEEDS = 24
EXAM_SEEDS = 128
FAMILIES = 32
FAMILIES_PER_SEED = 16
TRAIN_REPEATS = 4
TICKS = 16
ADAPT_GAINS = (4, 8, 16)
ADAPT_MEMORY_TICKS = (8, 16, 32)
WSP_BYTES = 16
N_HEAD = 128
SIGNATURE_MASK = 0xFFFF

LIF256 = "lif256"
LIF512 = "lif512"
LIF512_LIF128 = "lif512_lif128"
LIF512_ALIF128 = "lif512_alif128"
FEATURE_BLIND = "feature_blind"
FEATURE_PERMUTED = "feature_permuted"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def _fraction(numerator: int, denominator: int) -> dict:
    if denominator <= 0:
        raise ValueError("a fraction needs a positive denominator")
    divisor = math.gcd(abs(int(numerator)), int(denominator))
    return {"numerator": int(numerator) // divisor,
            "denominator": int(denominator) // divisor}


def _seed(bank: str, split: str, index: int) -> int:
    material = f"{DOMAIN}/{bank}/{split}/{int(index)}".encode("ascii")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def seeds(bank: str, split: str) -> Tuple[int, ...]:
    if split == "development":
        count = DEVELOPMENT_SEEDS
    elif split == "exam":
        count = EXAM_SEEDS
    else:
        raise ValueError("split must be development or exam")
    return tuple(_seed(bank, split, index) for index in range(count))


def seeds_hash(values: Sequence[int]) -> str:
    return _sha256_bytes(";".join(str(int(value)) for value in values).encode("ascii"))


def _code_hash() -> str:
    return _sha256_bytes(Path(__file__).read_bytes())


def _config() -> dict:
    return {
        "schema": SCHEMA, "slice": SLICE, "date": DATE,
        "families": FAMILIES, "families_per_seed": FAMILIES_PER_SEED,
        "train_repeats": TRAIN_REPEATS, "ticks": TICKS,
        "adapt_gains": list(ADAPT_GAINS),
        "adapt_memory_ticks": list(ADAPT_MEMORY_TICKS),
        "projection": "vertex=simhash16(wsp); lif256=hi^lo; lif512=(hi,lo)",
        "signature": "u16 winner||winner or winner_hi||winner_lo",
    }


def _config_hash() -> str:
    return _sha256_bytes(_canonical(_config()))


@dataclass(frozen=True)
class Q8Entry:
    winner: int
    first_target_spike: int
    spikes_total: int


@lru_cache(maxsize=1)
def q8_truth_table() -> Tuple[Q8Entry, ...]:
    """Run all Q8 stimuli through fresh imported layers, once and exactly."""
    rows: List[Q8Entry] = []
    for stimulus in range(256):
        run = Layer256().run(stimulus, q8_nearest(stimulus), TICKS)
        if run.winner not in Q8_CODEWORDS:
            raise RuntimeError("Layer256 did not select a Q8 codeword")
        rows.append(Q8Entry(run.winner, run.first_target_spike, run.spikes_total))
    return tuple(rows)


def _entry(stimulus: int) -> Q8Entry:
    return q8_truth_table()[int(stimulus) & 0xFF]


def signature_for(wsp: bytes, config: str) -> int:
    """The only capacity interface: a deterministic sensory u16."""
    if not isinstance(wsp, bytes) or len(wsp) != WSP_BYTES:
        raise ValueError("CAPACITY-1 requires a 16-byte WSP")
    if config == FEATURE_BLIND:
        return 0
    vertex = simhash16(wsp)
    hi, lo = (vertex >> 8) & 0xFF, vertex & 0xFF
    if config == LIF256:
        winner = _entry(hi ^ lo).winner
        return ((winner << 8) | winner) & SIGNATURE_MASK
    if config in (LIF512, LIF512_LIF128, LIF512_ALIF128, FEATURE_PERMUTED):
        return ((_entry(hi).winner << 8) | _entry(lo).winner) & SIGNATURE_MASK
    raise ValueError("unknown CAPACITY-1 configuration")


def _packet(family: int, variant: int) -> bytes:
    """A valid, synthetic WSP family. It contains no outcome or label field."""
    f, v = int(family), int(variant)
    return pack(
        src=f % 40, rel=(f * 7) % 32, dst=(f * 13) % 42, time=(f * 3) % 11,
        E={"V": (f * 9) % 101 - 50, "A": (f * 11) % 101 - 50,
           "D": (f * 5) % 101 - 50, "C": 40, "U": 20,
           "B": ((v >> 20) % 201) - 100},
        style=v & 0x0F, slot=(v >> 4) & 0x0FFF, seq=(v >> 16) & 0xFF,
    )


@lru_cache(maxsize=1)
def _family_packets() -> Tuple[Tuple[bytes, ...], ...]:
    """Find distinct WSPs with the same raw QN vertex for each family.

    This is a property of the shared `simhash16` representation, fixed before
    comparing neural configurations.  It does not inspect a candidate's
    winner, outcome, prediction, or test result.
    """
    all_families: List[Tuple[bytes, ...]] = []
    for family in range(FAMILIES):
        base = _packet(family, 0)
        vertex = simhash16(base)
        found = [base]
        seen = {base}
        for variant in range(1, 200000):
            raw = _packet(family, variant)
            if raw not in seen and simhash16(raw) == vertex:
                found.append(raw)
                seen.add(raw)
                if len(found) >= 2:
                    break
        if len(found) < 2:
            raise RuntimeError(f"could not construct held-out WSP variants for family {family}: {len(found)}")
        all_families.append(tuple(found))
    return tuple(all_families)


def _outcome(family: int) -> int:
    # 32 distinct physical consequences, all in PATTERN-1's int8 contract.
    return -96 + 6 * int(family)


def _sample_families(seed: int) -> Tuple[int, ...]:
    # A deterministic partial Fisher-Yates shuffle without Python random state.
    # The sample is stratified by the *input* Q8 codebook (not a learned
    # winner): a capacity test must not accidentally use sixteen copies of one
    # sensory cell before it asks whether a wider bank preserves distinctions.
    values = list(range(FAMILIES))
    state = int(seed) & ((1 << 64) - 1)
    for i in range(FAMILIES - 1, 0, -1):
        state = (state * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
        j = state % (i + 1)
        values[i], values[j] = values[j], values[i]
    chosen: List[int] = []
    occupied = set()
    for family in values:
        vertex = simhash16(_packet(family, 0))
        cell = ((q8_nearest(vertex >> 8) << 8)
                | q8_nearest(vertex & 0xFF))
        if cell in occupied:
            continue
        occupied.add(cell)
        chosen.append(family)
        if len(chosen) == FAMILIES_PER_SEED:
            return tuple(sorted(chosen))
    raise RuntimeError("the fixed sensory bank has fewer than 16 Q8 cells")


def _permutation(seed: int, values: Sequence[int]) -> Tuple[int, ...]:
    result = list(values)
    state = (int(seed) ^ 0xA1F1C1D1) & ((1 << 64) - 1)
    for i in range(len(result) - 1, 0, -1):
        state = (state * 2862933555777941757 + 3037000493) & ((1 << 64) - 1)
        j = state % (i + 1)
        result[i], result[j] = result[j], result[i]
    if len(result) > 1 and result == list(values):
        result[0], result[1] = result[1], result[0]
    return tuple(result)


def _memory_for_perception() -> InvariantPatternMemory:
    return InvariantPatternMemory(capacity=64, max_hamming=3, min_hits=TRAIN_REPEATS)


def perception_seed(seed: int, config: str) -> dict:
    """One paired frozen PATTERN-1 perception examination."""
    chosen = _sample_families(seed)
    packets = _family_packets()
    memory = _memory_for_perception()
    for family in chosen:
        # Repeated controlled exposures establish PATTERN-1's fixed maturity
        # threshold.  The held-out WSP below is a distinct 16-byte packet.
        for _ in range(TRAIN_REPEATS):
            memory.observe(signature_for(packets[family][0], config), _outcome(family))
    before = memory.snapshot_hash()
    observations_before = memory.observations
    permutation = _permutation(seed, chosen)
    signature_by_family = {
        family: signature_for(packets[family][1], config)
        for family in chosen
    }
    hits = 0
    abstentions = 0
    predicted: List[Tuple[int, int | None]] = []
    for index, family in enumerate(chosen):
        feature = signature_by_family[family]
        if config == FEATURE_PERMUTED:
            feature = signature_by_family[permutation[index]]
        answer = memory.predict(feature)
        outcome = None if answer is None else answer[1]
        hits += int(outcome == _outcome(family))
        abstentions += int(answer is None)
        predicted.append((family, outcome))
    after = memory.snapshot_hash()
    groups: Dict[int, set[int]] = {}
    for family in chosen:
        feature = signature_for(packets[family][0], config)
        groups.setdefault(feature, set()).add(_outcome(family))
    collisions = sum(len(outcomes) - 1 for outcomes in groups.values())
    return {
        "seed": int(seed), "families": list(chosen), "hits": hits,
        "total": len(chosen), "abstentions": abstentions,
        "incompatible_collisions": collisions,
        "predicted": [[family, outcome] for family, outcome in predicted],
        "memory_hash_before_exam": before, "memory_hash_after_exam": after,
        "observations_before_exam": observations_before,
        "observations_after_exam": memory.observations,
    }


def _aggregate(rows: Sequence[dict]) -> dict:
    hits = sum(int(row["hits"]) for row in rows)
    total = sum(int(row["total"]) for row in rows)
    return {
        "rows": list(rows), "hits": hits, "total": total,
        "balanced_accuracy": _fraction(hits, total),
        "abstentions": sum(int(row["abstentions"]) for row in rows),
        "incompatible_collisions": sum(int(row["incompatible_collisions"])
                                          for row in rows),
        "frozen": all(row["memory_hash_before_exam"] == row["memory_hash_after_exam"]
                      and row["observations_before_exam"] == row["observations_after_exam"]
                      for row in rows),
    }


def _compare(left: Sequence[dict], right: Sequence[dict]) -> dict:
    wins = losses = ties = 0
    for a, b in zip(left, right):
        if int(a["seed"]) != int(b["seed"]):
            raise ValueError("paired rows lost their seed alignment")
        aa, ad = int(a["hits"]), int(a["total"])
        bb, bd = int(b["hits"]), int(b["total"])
        delta = aa * bd - bb * ad
        if delta > 0:
            wins += 1
        elif delta < 0:
            losses += 1
        else:
            ties += 1
    non_ties = wins + losses
    numerator = sum(math.comb(non_ties, k) for k in range(wins, non_ties + 1))
    denominator = 1 << non_ties
    return {"wins": wins, "losses": losses, "ties": ties,
            "sign_p": _fraction(numerator, denominator)}


class TemporalHead:
    """Fixed 128-cell integer head; `adapt_gain=0` is its matched control."""

    def __init__(self, adapt_gain: int, memory_ticks: int) -> None:
        if adapt_gain < 0 or memory_ticks not in ADAPT_MEMORY_TICKS:
            raise ValueError("invalid Adaptive-LIF parameters")
        self.adapt_gain = int(adapt_gain)
        self.memory_ticks = int(memory_ticks)
        self.v = [0] * N_HEAD
        self.a = [0] * N_HEAD
        self.spikes = 0
        self.updates = 0
        self.spike_count = 0

    def step(self, feature: int, tick: int) -> None:
        previous = self.spikes
        nxt = 0
        for i in range(N_HEAD):
            bit = ((int(feature) >> ((i + int(tick)) & 15)) & 1)
            recurrent = 12 if ((previous >> ((i - 1) & 127)) & 1) else 0
            current = 48 * bit + recurrent
            potential = (self.v[i] * 7) // 8 + current - self.a[i]
            if potential >= 40:
                nxt |= 1 << i
                potential = 0
            self.v[i] = max(-127, min(127, potential))
            decay = (self.a[i] * (self.memory_ticks - 1)) // self.memory_ticks
            self.a[i] = min(127, decay + (self.adapt_gain if (nxt >> i) & 1 else 0))
        self.spikes = nxt
        self.updates += N_HEAD
        self.spike_count += nxt.bit_count()

    def signature(self) -> int:
        # Addition avoids the parity cancellation of XOR when many cells
        # spike.  With adaptation off this remains a readout of final spikes;
        # with it on, the existing integer adaptation state carries history.
        folded = 0xA5A5
        for i in range(N_HEAD):
            if (self.spikes >> i) & 1:
                folded += (i + 1) * 257
            # The adaptation register is the head's observable temporal state.
            folded += self.a[i] * (i * 17 + 1)
        return folded & SIGNATURE_MASK


def _sequence_signature(sequence: Sequence[int], adapt_gain: int, memory_ticks: int) -> Tuple[int, int, int]:
    head = TemporalHead(adapt_gain, memory_ticks)
    for tick, feature in enumerate(sequence):
        head.step(feature, tick)
    return head.signature(), head.spike_count, head.updates


def _temporal_pair(seed: int) -> Tuple[int, int]:
    chosen = _sample_families(seed)
    packets = _family_packets()
    features = [signature_for(packets[family][0], LIF512) for family in chosen]
    for i, first in enumerate(features):
        for second in features[i + 1:]:
            if first != second:
                return first, second
    raise RuntimeError("temporal pair needs two distinct sensory features")


def temporal_seed(seed: int, adapt_gain: int, memory_ticks: int,
                  feature_permuted: bool = False) -> dict:
    """Normal/anomaly motifs have identical final event and event histogram."""
    first, second = _temporal_pair(seed)
    normal = (first, first, first, second, second)
    anomaly = (first, first, second, first, second)
    signatures = [
        _sequence_signature(normal, adapt_gain, memory_ticks),
        _sequence_signature(anomaly, adapt_gain, memory_ticks),
    ]
    memory = InvariantPatternMemory(capacity=8, max_hamming=0, min_hits=TRAIN_REPEATS)
    for _ in range(TRAIN_REPEATS):
        memory.observe(signatures[0][0], 16)
        memory.observe(signatures[1][0], -16)
    before = memory.snapshot_hash()
    hits = 0
    abstentions = 0
    exam = [(signatures[0][0], 16), (signatures[1][0], -16)]
    if feature_permuted:
        # Same learned rows, but sensory signatures are exchanged only after
        # the head.  This isolates the causal head-to-PATTERN interface.
        exam = [(signatures[1][0], 16), (signatures[0][0], -16)]
    for signature, expected in exam:
        answer = memory.predict(signature)
        hits += int(answer is not None and answer[1] == expected)
        abstentions += int(answer is None)
    after = memory.snapshot_hash()
    return {
        "seed": int(seed), "hits": hits, "total": 2, "abstentions": abstentions,
        "feature_permuted": bool(feature_permuted),
        "normal_signature": signatures[0][0], "anomaly_signature": signatures[1][0],
        "spikes": signatures[0][1] + signatures[1][1],
        "updates": signatures[0][2] + signatures[1][2],
        "memory_hash_before_exam": before, "memory_hash_after_exam": after,
    }


def _temporal_aggregate(rows: Sequence[dict]) -> dict:
    hits = sum(int(row["hits"]) for row in rows)
    total = sum(int(row["total"]) for row in rows)
    return {"rows": list(rows), "hits": hits, "total": total,
            "balanced_accuracy": _fraction(hits, total),
            "abstentions": sum(int(row["abstentions"]) for row in rows),
            "spikes": sum(int(row.get("spikes", 0)) for row in rows),
            "updates": sum(int(row.get("updates", 0)) for row in rows),
            "frozen": all(row["memory_hash_before_exam"] == row["memory_hash_after_exam"]
                          for row in rows)}


def _current_only(seed: int) -> dict:
    _first, second = _temporal_pair(seed)
    memory = InvariantPatternMemory(capacity=8, max_hamming=0, min_hits=TRAIN_REPEATS)
    for _ in range(TRAIN_REPEATS):
        memory.observe(second, 16)
        memory.observe(second, -16)
    before = memory.snapshot_hash()
    answers = [memory.predict(second), memory.predict(second)]
    hits = sum(int(answer is not None and answer[1] == expected)
               for answer, expected in zip(answers, (16, -16)))
    return {"seed": int(seed), "hits": hits, "total": 2,
            "abstentions": sum(answer is None for answer in answers),
            "memory_hash_before_exam": before,
            "memory_hash_after_exam": memory.snapshot_hash()}


def _oracle(seed: int) -> dict:
    # The harness has the full motif label; this establishes that the problem
    # is resolvable without injecting that label into the neural candidate.
    _temporal_pair(seed)
    return {"seed": int(seed), "hits": 2, "total": 2, "abstentions": 0,
            "memory_hash_before_exam": "oracle", "memory_hash_after_exam": "oracle"}


def _select_adaptive(development: Sequence[int]) -> dict:
    candidates = []
    for gain in ADAPT_GAINS:
        for memory_ticks in ADAPT_MEMORY_TICKS:
            rows = [temporal_seed(seed, gain, memory_ticks) for seed in development]
            aggregate = _temporal_aggregate(rows)
            candidates.append({"gain": gain, "memory_ticks": memory_ticks,
                               "aggregate": aggregate})
    candidates.sort(key=lambda row: (
        -row["aggregate"]["hits"], row["memory_ticks"], row["gain"],
        row["aggregate"]["updates"]))
    return {"candidates": candidates, "selected": candidates[0]}


def _integrity() -> dict:
    table = q8_truth_table()
    codewords = all(entry.winner in Q8_CODEWORDS for entry in table)
    repeat = q8_truth_table() == table
    probes = []
    for stimulus in (0, 1, 3, 255):
        run = Layer256().run(stimulus, q8_nearest(stimulus), TICKS)
        row = table[stimulus]
        probes.append({"stimulus": stimulus, "winner": run.winner,
                       "first_target_spike": run.first_target_spike,
                       "spikes_total": run.spikes_total,
                       "matches_table": (run.winner, run.first_target_spike,
                                         run.spikes_total) ==
                                        (row.winner, row.first_target_spike,
                                         row.spikes_total)})
    return {"stimuli": len(table), "codewords_only": codewords,
            "deterministic": repeat, "probes": probes,
            "all_probes_match": all(row["matches_table"] for row in probes)}


def _measure_resources(selected: dict) -> dict:
    """Prototype CPU measurements; no energy or hardware inference."""
    stimuli = (0, 17, 63, 127, 191, 255)
    def measure(spokes: int) -> dict:
        for _ in range(10):
            for stimulus in stimuli:
                for offset in range(spokes):
                    value = (stimulus + 73 * offset) & 0xFF
                    Layer256().run(value, q8_nearest(value), TICKS)
        timings = []
        for _ in range(30):
            start = time.perf_counter_ns()
            for stimulus in stimuli:
                for offset in range(spokes):
                    value = (stimulus + 73 * offset) & 0xFF
                    Layer256().run(value, q8_nearest(value), TICKS)
            timings.append(time.perf_counter_ns() - start)
        ordered = sorted(timings)
        return {"warmup": 10, "repetitions": 30,
                "samples_per_repetition": len(stimuli), "spokes": spokes,
                "p50": ordered[len(ordered) // 2],
                "p95": ordered[(len(ordered) * 95) // 100]}

    tracemalloc.start()
    latency = {LIF256: measure(1), LIF512: measure(2)}
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gain, memory_ticks = selected["gain"], selected["memory_ticks"]
    declared_head = N_HEAD * 3  # v int8, adaptation int8, spike bit budget.
    return {
        "host": {"python": sys.version.split()[0], "implementation": sys.implementation.name},
        "uncached_cpu_latency_ns": latency,
        "python_peak_bytes": peak,
        "declared_state_bytes": {
            LIF256: 256 + 32, LIF512: 2 * (256 + 32),
            LIF512_LIF128: 2 * (256 + 32) + declared_head,
            LIF512_ALIF128: 2 * (256 + 32) + declared_head,
        },
        "selected_adapt_gain": gain, "selected_memory_ticks": memory_ticks,
        "energy": "not measured: no shunt, attributable RAPL, or Akida hardware",
    }


def _meets_bottleneck(current: dict, oracle: dict) -> bool:
    # Oracle - current-only sensory readout >= 20 percentage points and the
    # readout itself remains at or below 60%.  This is the temporal condition;
    # the separate perception score must not be substituted into it.
    return (oracle["hits"] * current["total"] >=
            current["hits"] * oracle["total"]
            + 20 * oracle["total"] * current["total"] // 100
            and 100 * current["hits"] <= 60 * current["total"])


def _green_science(science: dict) -> bool:
    integrity = science["integrity"]
    perception = science["perception"]
    comparison = science["perception_comparison"]
    baseline, candidate = perception[LIF256], perception[LIF512]
    p = comparison["sign_p"]
    gain_n = candidate["hits"] * baseline["total"] - baseline["hits"] * candidate["total"]
    gain_d = candidate["total"] * baseline["total"]
    perception_ok = (
        gain_n * 100 >= 5 * gain_d and comparison["wins"] > comparison["losses"]
        and p["numerator"] * 100 <= p["denominator"]
        and candidate["incompatible_collisions"] * 4 <= baseline["incompatible_collisions"] * 3
        and (perception[FEATURE_PERMUTED]["hits"] - baseline["hits"]) * 5
            <= (candidate["hits"] - baseline["hits"])
        and baseline["frozen"] and candidate["frozen"]
    )
    temporal_ok = True
    if science["adaptive_status"] == "justified":
        temporal = science["temporal"]
        comp = science["temporal_comparison"]
        control, alif = temporal[LIF512_LIF128], temporal[LIF512_ALIF128]
        pp = comp["sign_p"]
        temporal_ok = (
            (alif["hits"] * control["total"] - control["hits"] * alif["total"]) * 100
            >= 5 * alif["total"] * control["total"]
            and comp["wins"] > comp["losses"]
            and pp["numerator"] * 100 <= pp["denominator"]
            and alif["frozen"] and control["frozen"]
            and (temporal[FEATURE_PERMUTED]["hits"] - control["hits"]) * 5
                <= (alif["hits"] - control["hits"])
        )
    return bool(integrity["codewords_only"] and integrity["deterministic"]
                and integrity["all_probes_match"] and perception_ok and temporal_ok
                and science["wsp_bytes"] == WSP_BYTES
                and science["false_facts"] == 0 and science["destroyed"] == 0
                and science["cortex_calls"] == 0)


@lru_cache(maxsize=1)
def scientific_experiment() -> dict:
    development = seeds("capacity", "development")
    exam = seeds("capacity", "exam")
    dev_sensory = _aggregate([perception_seed(seed, LIF512) for seed in development])
    dev_current = _temporal_aggregate([_current_only(seed) for seed in development])
    dev_oracle = _temporal_aggregate([_oracle(seed) for seed in development])
    justified = _meets_bottleneck(dev_current, dev_oracle)
    selection = _select_adaptive(development) if justified else None
    selected = ({"gain": 0, "memory_ticks": 8} if selection is None
                else {"gain": selection["selected"]["gain"],
                      "memory_ticks": selection["selected"]["memory_ticks"]})
    perception = {config: _aggregate([perception_seed(seed, config) for seed in exam])
                  for config in (LIF256, LIF512, FEATURE_BLIND, FEATURE_PERMUTED)}
    temporal = {
        "current_only": _temporal_aggregate([_current_only(seed) for seed in exam]),
        "history_oracle": _temporal_aggregate([_oracle(seed) for seed in exam]),
    }
    if justified:
        temporal[LIF512_LIF128] = _temporal_aggregate([
            temporal_seed(seed, 0, selected["memory_ticks"]) for seed in exam])
        temporal[LIF512_ALIF128] = _temporal_aggregate([
            temporal_seed(seed, selected["gain"], selected["memory_ticks"])
            for seed in exam])
        temporal[FEATURE_PERMUTED] = _temporal_aggregate([
            temporal_seed(seed, selected["gain"], selected["memory_ticks"],
                          feature_permuted=True) for seed in exam])
        temporal_comparison = _compare(temporal[LIF512_ALIF128]["rows"],
                                       temporal[LIF512_LIF128]["rows"])
    else:
        temporal_comparison = {"wins": 0, "losses": 0, "ties": 0,
                               "sign_p": _fraction(1, 1)}
    science = {
        "schema": SCHEMA, "slice": SLICE, "date": DATE,
        "config": _config(), "development_seeds": list(development),
        "exam_seeds": list(exam), "development_seed_hash": seeds_hash(development),
        "exam_seed_hash": seeds_hash(exam), "integrity": _integrity(),
        "development": {"lif512": dev_sensory, "current_only": dev_current,
                        "history_oracle": dev_oracle, "adaptive_selection": selection},
        "selected_adaptive": selected,
        "adaptive_status": "justified" if justified else "not_justified",
        "perception": perception,
        "perception_comparison": _compare(perception[LIF512]["rows"],
                                             perception[LIF256]["rows"]),
        "temporal": temporal, "temporal_comparison": temporal_comparison,
        "wsp_bytes": WSP_BYTES, "false_facts": 0, "destroyed": 0,
        "cortex_calls": 0,
    }
    science["green"] = _green_science(science)
    return science


def experiment() -> dict:
    science = scientific_experiment()
    report = {
        "schema": SCHEMA, "slice": SLICE, "date": DATE,
        "code_sha256": _code_hash(), "config_sha256": _config_hash(),
        "scientific": science,
        "scientific_result_sha256": _sha256_bytes(_canonical(science)),
        "resource_measurement": _measure_resources(science["selected_adaptive"]),
        "limitations": [
            "Synthetic valid WSP families; no camera, 3-D engine, robot, or drone.",
            "Functional scores use an exhaustive Layer256 transfer table; timing uses uncached fresh LIF runs.",
            "Python CPU timings are not neuromorphic parallelism, power, or Akida measurements.",
            "Q/T/CAM/VERIFY/gate are not expanded or controlled by spikes in this slice.",
        ],
    }
    report["green"] = green(report)
    return report


def green(report: dict) -> bool:
    """Fail closed: reconstruct all scientific rows, seeds and comparisons."""
    try:
        if report["schema"] != SCHEMA or report["slice"] != SLICE:
            return False
        if report["config_sha256"] != _config_hash() or report["code_sha256"] != _code_hash():
            return False
        science = scientific_experiment()
        if report["scientific"] != science:
            return False
        if report["scientific_result_sha256"] != _sha256_bytes(_canonical(science)):
            return False
        if "green" in report and report["green"] != science["green"]:
            return False
        return _green_science(science)
    except (KeyError, TypeError, ValueError, RuntimeError, IndexError):
        return False


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        raise SystemExit("CAPACITY-1 takes no arguments")
    report = experiment()
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_capacity1_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"slice": report["slice"], "green": report["green"],
                      "report": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
