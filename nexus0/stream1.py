"""STREAM-1: long external WSP streams with DynamicAlias measured.

An external producer supplies a transition as ``(wsp, action, next_wsp)``.
Frame sequence and chunk identifiers remain outside that interface.  They are
useful to audit a long stream, but they must not become a hidden state id in
the 16-byte packet or in CAM/T.

The processor reuses the Agent's existing CAM allocator and ``World`` table;
it neither chooses actions nor creates a second predictor.  DynamicAlias is
reported when one equal ``(wsp, action)`` pair has multiple observed next
packets.  The correct response in this slice is to measure it, never to hide
the chunk in domain, style or seq.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from echoai.core.qn import simhash16
from echoai.core.wsp import unpack

from echoai.nexus0.constants import ACTION_APPROACH, N_ACTIONS
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY
from echoai.nexus0.loop import Agent
from echoai.nexus0.types import default_e


LOCAL_STATES = 32
CHUNKS = 48
FRAMES_PER_CHUNK = LOCAL_STATES * N_ACTIONS
STREAM_FRAMES = CHUNKS * FRAMES_PER_CHUNK
ALTERED_STATE = 11


@dataclass(frozen=True)
class ExternalFrame:
    """Transport metadata plus one observed external transition.

    ``sequence`` and ``chunk`` intentionally never enter ``StreamProcessor``.
    They exist only to make the source and the alias audit reproducible.
    """

    sequence: int
    chunk: int
    wsp: bytes
    action: int
    next_wsp: bytes


def packet_of(local_state: int) -> bytes:
    """A local observation, repeated in every external chunk."""
    return encode_cell(int(local_state) % LOCAL_STATES, KIND_EMPTY)


def successor(local_state: int, action: int, altered: bool = False) -> int:
    state = int(local_state) % LOCAL_STATES
    aa = int(action) % N_ACTIONS
    if aa == ACTION_APPROACH:
        if altered and state == ALTERED_STATE:
            return (state + 2) % LOCAL_STATES
        return (state + 1) % LOCAL_STATES
    if aa == 1:
        return (state - 1) % LOCAL_STATES
    return state


def external_stream(*, altered_chunks: Iterable[int] = ()) -> List[ExternalFrame]:
    """A deterministic, chunked stream longer than the packet seq ceiling."""
    altered = {int(chunk) for chunk in altered_chunks}
    out: List[ExternalFrame] = []
    sequence = 0
    for chunk in range(CHUNKS):
        for state in range(LOCAL_STATES):
            for action in range(N_ACTIONS):
                out.append(ExternalFrame(
                    sequence=sequence,
                    chunk=chunk,
                    wsp=packet_of(state),
                    action=action,
                    next_wsp=packet_of(successor(state, action, chunk in altered)),
                ))
                sequence += 1
    return out


class StreamProcessor:
    """CAM/T ingestion boundary for an external stream.

    There is deliberately no ``chunk``, ``frame`` or object-id argument.  The
    fast path sees the same three values a real external transition can carry.
    """

    def __init__(self) -> None:
        self.agent = Agent(ask=False)
        self.frames = 0
        self.pred_known = 0
        self.pred_hits = 0
        self.rows: Dict[Tuple[bytes, int], Set[bytes]] = {}

    @staticmethod
    def _packet(raw: bytes) -> bytes:
        if not isinstance(raw, bytes) or len(raw) != 16:
            raise ValueError("external WSP must be exactly 16 bytes")
        return raw

    def ingest(self, wsp: bytes, action: int, next_wsp: bytes) -> None:
        wsp = self._packet(wsp)
        next_wsp = self._packet(next_wsp)
        aa = int(action) % N_ACTIONS
        vertex = simhash16(wsp)
        next_vertex = simhash16(next_wsp)
        slot = self.agent._slot_for(wsp, vertex, "", default_e(),
                                    source="stream1-external")
        next_slot = self.agent._slot_for(next_wsp, next_vertex, "", default_e(),
                                         source="stream1-external")
        predicted = self.agent.t.predict(slot, aa)
        if predicted is not None:
            self.pred_known += 1
            self.pred_hits += int(predicted == next_slot)
        self.agent.t.observe(slot, aa, next_slot)
        self.rows.setdefault((wsp, aa), set()).add(next_wsp)
        self.frames += 1

    def ingest_all(self, frames: Iterable[ExternalFrame]) -> None:
        for frame in frames:
            self.ingest(frame.wsp, frame.action, frame.next_wsp)

    def dynamic_alias(self) -> List[dict]:
        """Rows with one packet/action and more than one physical successor."""
        out: List[dict] = []
        for (wsp, action), successors in self.rows.items():
            if len(successors) > 1:
                out.append({
                    "wsp": wsp.hex(),
                    "action": action,
                    "successors": sorted(raw.hex() for raw in successors),
                })
        return sorted(out, key=lambda row: (row["wsp"], row["action"]))

    def snapshot_hash(self) -> str:
        h = hashlib.sha256()
        for value in (self.frames, self.pred_known, self.pred_hits,
                      self.agent.t.conflicts):
            h.update(int(value).to_bytes(8, "little", signed=False))
        for key in sorted(self.rows, key=lambda row: (row[0], row[1])):
            h.update(key[0])
            h.update(bytes([key[1]]))
            for successor_wsp in sorted(self.rows[key]):
                h.update(successor_wsp)
        return h.hexdigest()


def _packet_contract(frames: List[ExternalFrame]) -> dict:
    packets = {frame.wsp for frame in frames} | {frame.next_wsp for frame in frames}
    ext = [unpack(raw)["ext"] for raw in packets]
    return {
        "packets": len(packets),
        "packet_bytes": sorted({len(raw) for raw in packets}),
        "domain_zero": all(row["domain"] == 0 for row in ext),
        "style_zero": all(row["style"] == 0 for row in ext),
        "seq_local": all(0 <= row["seq"] < LOCAL_STATES for row in ext),
    }


def _run(frames: List[ExternalFrame]) -> dict:
    processor = StreamProcessor()
    processor.ingest_all(frames)
    aliases = processor.dynamic_alias()
    slots = sum(slot.occupied != 0 for slot in processor.agent.cam.slot)
    return {
        "frames": processor.frames,
        "cam_occupied": slots,
        "world_conflicts": processor.agent.t.conflicts,
        "prediction_known": processor.pred_known,
        "prediction_hits": processor.pred_hits,
        "dynamic_alias": len(aliases),
        "alias_rows": aliases,
        "snapshot": processor.snapshot_hash(),
        "cortex_calls": processor.agent.metrics.cortex_calls,
        "destroyed": processor.agent.cam.destroyed,
        "q_rows_changed": sum(any(row) for row in processor.agent.q.q),
    }


def experiment() -> dict:
    coherent = external_stream()
    # One physical chunk differs after long sharing.  Its WSP is unchanged.
    aliased = external_stream(altered_chunks=(CHUNKS // 2,))
    clean = _run(coherent)
    conflict = _run(aliased)
    return {
        "slice": "STREAM-1",
        "chunks": CHUNKS,
        "frames_per_chunk": FRAMES_PER_CHUNK,
        "stream_frames": STREAM_FRAMES,
        "sequence_last": coherent[-1].sequence,
        "external_frame_fields": ["sequence", "chunk", "wsp", "action", "next_wsp"],
        "processor_inputs": ["wsp", "action", "next_wsp"],
        "coherent_packet_contract": _packet_contract(coherent),
        "aliased_packet_contract": _packet_contract(aliased),
        "coherent": clean,
        "alias_control": conflict,
        "chunk_in_wsp": False,
        "cortex_calls": max(clean["cortex_calls"], conflict["cortex_calls"]),
        "destroyed": max(clean["destroyed"], conflict["destroyed"]),
    }


def green(report: dict) -> bool:
    """Recompute the long-stream and alias claims; fail closed."""
    try:
        if (report["slice"], report["chunks"], report["frames_per_chunk"],
                report["stream_frames"], report["sequence_last"]) != (
                    "STREAM-1", CHUNKS, FRAMES_PER_CHUNK, STREAM_FRAMES,
                    STREAM_FRAMES - 1):
            return False
        if report["processor_inputs"] != ["wsp", "action", "next_wsp"]:
            return False
        if report["chunk_in_wsp"] is not False:
            return False
        if report["cortex_calls"] != 0 or report["destroyed"] != 0:
            return False
        for name, expected_alias in (("coherent", 0), ("alias_control", 1)):
            row = report[name]
            if row["frames"] != STREAM_FRAMES:
                return False
            if row["cam_occupied"] != LOCAL_STATES or row["q_rows_changed"] != 0:
                return False
            if row["dynamic_alias"] != len(row["alias_rows"]):
                return False
            if row["dynamic_alias"] != expected_alias:
                return False
            if row["prediction_known"] <= 0 or row["prediction_hits"] <= 0:
                return False
            if row["cortex_calls"] != 0 or row["destroyed"] != 0:
                return False
        if report["coherent"]["world_conflicts"] != 0:
            return False
        if report["alias_control"]["world_conflicts"] <= 0:
            return False
        if report["alias_control"]["prediction_hits"] >= report["coherent"]["prediction_hits"]:
            return False
        for name in ("coherent_packet_contract", "aliased_packet_contract"):
            contract = report[name]
            if (contract["packets"], contract["packet_bytes"], contract["domain_zero"],
                    contract["style_zero"], contract["seq_local"]) != (
                        LOCAL_STATES, [16], True, True, True):
                return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_stream1_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())

