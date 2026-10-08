"""HEAT-1b: two integer homeostatic variables with a causal trade-off."""
from __future__ import annotations

import hashlib
import json
import pickle
import random
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Sequence
from unittest.mock import patch

from echoai.nexus0.constants import (
    ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT, N_ACTIONS, R_THREAT,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import Cell, KIND_EMPTY, KIND_OBJECT
from echoai.nexus0.gen1 import _memory_fingerprint
from echoai.nexus0.loop import Agent
from echoai.nexus0.qtable import QTable
from echoai.nexus0.world import World


DOMAIN = "ECHO-AI/HEAT-1b/2026-09-09"
N_SEEDS = 12
LIVES = 60
LAST_WINDOW = 20
PHASE_MODULUS = 10000
MAX_TURNS = 512
INITIAL_H = 32
INITIAL_TEMPERATURE = 64
TEMPERATURE_BANDS = 8
SCHEMA = 1


def derived_seeds() -> tuple[int, ...]:
    return tuple(int.from_bytes(hashlib.sha256(
        f"{DOMAIN}/{index}".encode("ascii")).digest()[:4], "big")
                 for index in range(N_SEEDS))


SEEDS = derived_seeds()


def seeds_hash(seeds: Sequence[int]) -> str:
    body = ";".join(str(int(seed)) for seed in seeds)
    return hashlib.sha256(body.encode("ascii")).hexdigest()


def _fingerprint(value) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=4)).hexdigest()


def _memories(agent: Agent) -> dict:
    return {name: _fingerprint(getattr(agent, name))
            for name in ("cam", "q", "t")}


def thermal_band(temperature: int) -> int:
    if type(temperature) is not int or not 0 <= temperature <= 127:
        raise ValueError("temperature must be an integer in 0..127")
    return 0 if temperature == 0 else (temperature - 1) // 16


class ThermalDockEnv:
    """A charger heats its battery; active cooling spends its charge."""

    def __init__(self) -> None:
        self.kind = [KIND_EMPTY] * 32
        self.kind[0] = KIND_OBJECT
        self.reset()

    def reset(self) -> None:
        self.i = 0
        self.last_reward = 0
        self.last_cause = ""

    def cell(self) -> Cell:
        return Cell(index=0, kind=KIND_OBJECT)

    def step_homeostatic(self, action: int, h: int, temperature: int):
        if type(h) is not int or not 1 <= h <= 127:
            raise ValueError("only a living integer H can act")
        if (type(temperature) is not int
                or not 1 <= temperature <= 126):
            raise ValueError("only a viable integer temperature can act")
        aa = int(action) % N_ACTIONS
        if aa == ACTION_APPROACH:
            h_next = min(127, h + 3)
            temperature_next = min(127, temperature + 24)
            reward = 8
        elif aa == ACTION_AVOID:
            h_next = max(0, h - 4)
            temperature_next = max(0, temperature - 24)
            reward = 0
        else:
            h_next = max(0, h - 1)
            temperature_next = min(127, temperature + 16)
            reward = 0
        cause = ("heat" if temperature_next == 127 else
                 "cold" if temperature_next == 0 else
                 "energy" if h_next == 0 else "")
        if cause:
            reward = R_THREAT
        self.last_reward = reward
        self.last_cause = cause
        return reward, self.cell(), h_next, temperature_next

    def step(self, _action: int):
        raise RuntimeError("HEAT-1b requires step_homeostatic")

    def teleport(self, _index: int) -> Cell:
        return self.cell()

    def reveal(self, _extract: str) -> bool:
        return False


def new_agent(observe_temperature: bool = True) -> Agent:
    return Agent(env=ThermalDockEnv(), initial_h=INITIAL_H,
                 initial_temperature=INITIAL_TEMPERATURE,
                 observe_temperature=observe_temperature, ask=False,
                 temperature_bands=TEMPERATURE_BANDS,
                 remainder=True, explore_flat=True)


def _median2(values: Sequence[int]) -> int:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        raise ValueError("median requires values")
    return ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]


def frozen_probe(agent: Agent) -> dict:
    """Read two learned rows; restore registers and never run physics."""
    h_before = agent.H
    temperature_before = agent.temperature
    memory_before = _memories(agent)
    rows = []
    for temperature in (80, 112):
        agent.H = INITIAL_H
        agent.temperature = temperature
        wsp = agent.observation(agent.env.cell())
        slot = agent.cam.get(wsp)
        rows.append({
            "h": INITIAL_H, "temperature": temperature, "wsp": wsp.hex(),
            "slot": slot, "q": [] if slot < 0 else agent.q.row(slot),
            "action": ACTION_WAIT if slot < 0 else agent.q.best(slot),
        })
    agent.H = h_before
    agent.temperature = temperature_before
    return {"rows": rows, "source_unchanged": memory_before == _memories(agent)}


def run_arm(seed: int, mode: str) -> dict:
    if mode not in ("joint", "blind", "reset", "no_q"):
        raise ValueError("unknown HEAT-1b arm")
    agent = new_agent(observe_temperature=mode != "blind")
    rng = random.Random(int(seed))
    phases = [rng.randrange(PHASE_MODULUS) for _ in range(LIVES)]
    birth = _memories(agent)
    birth_state = _memory_fingerprint(agent)
    initial_q = _fingerprint((agent.q.q, agent.q.rem))
    cam_identity = id(agent.cam)
    identities = (id(agent.cam), id(agent.q), id(agent.t))
    identity_preserved = True
    q_t_resets = 0
    rows = []
    context = (patch.object(agent.q, "update", return_value=0)
               if mode == "no_q" else nullcontext())
    with context:
        for life, phase in enumerate(phases):
            if life:
                agent.respawn()
                if mode == "reset":
                    agent.q = QTable(remainder=True, explore_flat=True)
                    agent.t = World()
                    q_t_resets += 1
                else:
                    identity_preserved &= identities == (
                        id(agent.cam), id(agent.q), id(agent.t))
            actions = []
            reward_sum = 0
            band_actions = [[0] * N_ACTIONS
                            for _ in range(TEMPERATURE_BANDS)]
            while not agent.episode_terminal and agent.life_turns < MAX_TURNS:
                band = thermal_band(agent.temperature)
                action = agent.turn(life * PHASE_MODULUS + phase
                                    + agent.life_turns)
                actions.append(action)
                band_actions[band][action] += 1
                reward_sum += agent.last_reward
            rows.append({
                "life": life + 1, "phase": phase, "turns": agent.life_turns,
                "actions": actions, "band_actions": band_actions,
                "reward_sum": reward_sum, "terminal": agent.episode_terminal,
                "h": agent.H, "temperature": agent.temperature,
                "cause": agent.env.last_cause,
            })
    final_q = _fingerprint((agent.q.q, agent.q.rem))
    values = [row["turns"] for row in rows]
    return {
        "mode": mode, "seed": int(seed), "phases": phases, "lives": rows,
        "total_turns": sum(values),
        "median2_last20": _median2(values[-LAST_WINDOW:]),
        "band_actions": [[sum(row["band_actions"][band][action]
                              for row in rows) for action in range(N_ACTIONS)]
                         for band in range(TEMPERATURE_BANDS)],
        "probe": frozen_probe(agent), "birth": birth,
        "birth_state": birth_state, "final": _memories(agent),
        "final_state": _memory_fingerprint(agent), "deaths": agent.deaths,
        "q_t_resets": q_t_resets,
        "identity_preserved": identity_preserved,
        "cam_identity_preserved": id(agent.cam) == cam_identity,
        "q_unchanged": initial_q == final_q,
        "false_facts": agent.metrics.false_facts,
        "destroyed": agent.cam.destroyed,
        "cortex_calls": agent.metrics.cortex_calls,
        "cam_occupied": sum(slot.occupied != 0 for slot in agent.cam.slot),
    }


def _headline(rows: Sequence[dict]) -> dict:
    modes = ("joint", "blind", "reset", "no_q")
    totals = {mode: sum(row[mode]["total_turns"] for row in rows)
              for mode in modes}
    median_wins = {mode: sum(
        row["joint"]["median2_last20"] > row[mode]["median2_last20"]
        for row in rows) for mode in modes[1:]}
    total_wins = {mode: sum(
        row["joint"]["total_turns"] > row[mode]["total_turns"]
        for row in rows) for mode in modes[1:]}
    causes = {cause: sum(
        life["cause"] == cause for row in rows for life in row["joint"]["lives"])
        for cause in ("heat", "cold", "energy")}
    return {
        "total_turns": totals, "median_wins": median_wins,
        "total_wins": total_wins, "joint_death_causes": causes,
        "joint_temperate_actions": [sum(
            row["joint"]["band_actions"][band][action]
            for row in rows for band in (4, 5))
            for action in range(N_ACTIONS)],
        "joint_hot_actions": [sum(
            row["joint"]["band_actions"][band][action]
            for row in rows for band in (6, 7))
            for action in range(N_ACTIONS)],
    }


def experiment() -> dict:
    rows = []
    for seed in SEEDS:
        rows.append({"seed": seed, **{
            mode: run_arm(seed, mode)
            for mode in ("joint", "blind", "reset", "no_q")}})
    return {
        "schema": SCHEMA, "slice": "HEAT-1b",
        "protocol": {
            "domain": DOMAIN, "seeds": list(SEEDS),
            "seeds_hash": seeds_hash(SEEDS), "lives": LIVES,
            "last_window": LAST_WINDOW, "phase_modulus": PHASE_MODULUS,
            "max_turns": MAX_TURNS, "initial_h": INITIAL_H,
            "initial_temperature": INITIAL_TEMPERATURE,
            "charge_delta": [3, 24, 8], "cool_delta": [-4, -24, 0],
            "temperature_bands": TEMPERATURE_BANDS,
            "wait_delta": [-1, 16, 0], "terminal_reward": R_THREAT,
        },
        "rows": rows, "headline": _headline(rows),
    }


def _replay_life(row: dict) -> bool:
    try:
        env = ThermalDockEnv()
        h = INITIAL_H
        temperature = INITIAL_TEMPERATURE
        reward_sum = 0
        bands = [[0] * N_ACTIONS for _ in range(TEMPERATURE_BANDS)]
        for index, action in enumerate(row["actions"]):
            if action not in range(N_ACTIONS) or h == 0 or temperature in (0, 127):
                return False
            bands[thermal_band(temperature)][action] += 1
            reward, _cell, h, temperature = env.step_homeostatic(
                action, h, temperature)
            reward_sum += reward
            if env.last_cause and index != len(row["actions"]) - 1:
                return False
        return (row["turns"] == len(row["actions"])
                and 0 < row["turns"] < MAX_TURNS
                and row["terminal"] is True
                and row["h"] == h and row["temperature"] == temperature
                and row["cause"] == env.last_cause
                and row["cause"] in ("heat", "cold", "energy")
                and row["reward_sum"] == reward_sum
                and row["band_actions"] == bands)
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def _valid_arm(arm: dict, seed: int, mode: str) -> bool:
    try:
        rng = random.Random(int(seed))
        phases = [rng.randrange(PHASE_MODULUS) for _ in range(LIVES)]
        if (arm["mode"] != mode or arm["seed"] != seed
                or arm["phases"] != phases or len(arm["lives"]) != LIVES
                or arm["deaths"] != LIVES
                or arm["q_t_resets"] != (LIVES - 1 if mode == "reset" else 0)
                or arm["cam_identity_preserved"] is not True
                or any(arm[k] != 0 for k in
                       ("false_facts", "destroyed", "cortex_calls"))
                or not 0 < arm["cam_occupied"] <= 4096
                or arm["probe"]["source_unchanged"] is not True):
            return False
        if any(arm["birth_state"][key] != 0 for key in
               ("cam_occupied", "q_nonzero", "rem_nonzero", "t_known")):
            return False
        if mode != "reset" and arm["identity_preserved"] is not True:
            return False
        if mode == "no_q":
            if (arm["q_unchanged"] is not True
                    or arm["final"]["q"] != arm["birth"]["q"]
                    or arm["final_state"]["q_nonzero"] != 0
                    or arm["final_state"]["rem_nonzero"] != 0):
                return False
        totals = [[0] * N_ACTIONS for _ in range(TEMPERATURE_BANDS)]
        for index, row in enumerate(arm["lives"]):
            if (row["life"] != index + 1 or row["phase"] != phases[index]
                    or not _replay_life(row)):
                return False
            for band in range(TEMPERATURE_BANDS):
                for action in range(N_ACTIONS):
                    totals[band][action] += row["band_actions"][band][action]
        values = [row["turns"] for row in arm["lives"]]
        return (arm["total_turns"] == sum(values)
                and arm["median2_last20"] == _median2(values[-LAST_WINDOW:])
                and arm["band_actions"] == totals)
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def green(report: dict) -> bool:
    try:
        expected_protocol = {
            "domain": DOMAIN, "seeds": list(SEEDS),
            "seeds_hash": seeds_hash(SEEDS), "lives": LIVES,
            "last_window": LAST_WINDOW, "phase_modulus": PHASE_MODULUS,
            "max_turns": MAX_TURNS, "initial_h": INITIAL_H,
            "initial_temperature": INITIAL_TEMPERATURE,
            "charge_delta": [3, 24, 8], "cool_delta": [-4, -24, 0],
            "temperature_bands": TEMPERATURE_BANDS,
            "wait_delta": [-1, 16, 0], "terminal_reward": R_THREAT,
        }
        if (report["schema"] != SCHEMA or report["slice"] != "HEAT-1b"
                or report["protocol"] != expected_protocol
                or len(report["rows"]) != N_SEEDS
                or [row["seed"] for row in report["rows"]] != list(SEEDS)):
            return False
        total = {mode: 0 for mode in ("joint", "blind", "reset", "no_q")}
        median_wins = {mode: 0 for mode in ("blind", "reset", "no_q")}
        for row in report["rows"]:
            seed = row["seed"]
            births = [row[mode]["birth"] for mode in total]
            if any(birth != births[0] for birth in births[1:]):
                return False
            for mode in total:
                if not _valid_arm(row[mode], seed, mode):
                    return False
                total[mode] += row[mode]["total_turns"]
            joint = row["joint"]
            if any(joint["total_turns"] <= row[mode]["total_turns"]
                   for mode in median_wins):
                return False
            for mode in median_wins:
                median_wins[mode] += int(
                    joint["median2_last20"] > row[mode]["median2_last20"])
            temperate = [sum(joint["band_actions"][band][action]
                             for band in (4, 5))
                         for action in range(N_ACTIONS)]
            hot = [sum(joint["band_actions"][band][action]
                       for band in (6, 7))
                   for action in range(N_ACTIONS)]
            if not (temperate[ACTION_APPROACH] > temperate[ACTION_AVOID]
                    and hot[ACTION_AVOID] > hot[ACTION_APPROACH]):
                return False
            joint_probe = joint["probe"]["rows"]
            blind_probe = row["blind"]["probe"]["rows"]
            if ([probe["action"] for probe in joint_probe]
                    != [ACTION_APPROACH, ACTION_AVOID]
                    or any(len(probe["wsp"]) != 32
                           for probe in joint_probe + blind_probe)
                    or joint_probe[0]["wsp"] == joint_probe[1]["wsp"]
                    or blind_probe[0]["wsp"] != blind_probe[1]["wsp"]
                    or blind_probe[0]["q"] != blind_probe[1]["q"]
                    or blind_probe[0]["action"] != blind_probe[1]["action"]):
                return False
        if report["headline"] != _headline(report["rows"]):
            return False
        return (all(total["joint"] >= 2 * total[mode]
                    for mode in median_wins)
                and all(wins >= 8 for wins in median_wins.values()))
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_heat1b_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    summary = [{"seed": row["seed"], **{
        mode: {"median2_last20": row[mode]["median2_last20"],
               "total_turns": row[mode]["total_turns"]}
        for mode in ("joint", "blind", "reset", "no_q")}}
               for row in report["rows"]]
    print(json.dumps({"green": report["green"], "rows": summary,
                      "report": str(path)}, indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
