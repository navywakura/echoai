"""ARC final receipts with explicit reset provenance and complete action counts."""
from types import FunctionType


class Counter:
    def __init__(self, env):
        self.env, self.started, self.game_over = env, False, False
        self.emitted, self.automatic = 0, []

    def reset(self):
        obs = self.env.reset()
        if obs is None:
            raise RuntimeError("reset failed")
        if self.started:
            if self.game_over:
                self.automatic.append(self.emitted)
            self.emitted += 1
        self.started, self.game_over = True, False
        return obs

    def step(self, action, data=None):
        obs = self.env.step(action, data=data)
        if obs is not None:
            self.emitted += 1
            self.game_over = obs.state.name == "GAME_OVER"
        return obs


def accounting(record):
    assert len(record["actions"]) + 1 == len(record["frames"]) == len(record["levels"])
    assert record["levels"][0] == 0
    automatic = set(record["automatic_reset_indices"])
    assert len(automatic) == len(record["automatic_reset_indices"]) == record["resets"]
    assert all(0 <= i < len(record["actions"]) and record["actions"][i] == ["R", 0, None] for i in automatic)
    assert len(record["actions"]) - len(automatic) <= record["budget"]
    historical, complete, h, c = [], [], 0, 0
    for i, action in enumerate(record["actions"]):
        c += 1
        if i not in automatic:
            h += 1
        if record["levels"][i + 1] > record["levels"][i]:
            assert record["levels"][i + 1] == record["levels"][i] + 1
            historical.append(h)
            complete.append(c)
            h, c = 0, 0
    assert historical == record["actions_per_level"]
    assert len(complete) == record["levels_completed"]
    assert record["levels_completed"] <= record["win_levels"]
    return {"historical_per_level": historical, "complete_per_level": complete,
            "decisions": len(record["actions"]) - len(automatic),
            "automatic_resets": len(automatic),
            "chosen_resets": sum(a[0] == "R" for a in record["actions"]) - len(automatic),
            "initial_reset_counted": False, "total_actions": len(record["actions"])}


def protocol_check(record):
    from arc_agi.scorecard import Card
    card = Card(game_id="counter-verification")
    card.inc_play_count("receipt")
    for i, action in enumerate(record["actions"]):
        if action[0] == "R":
            card.inc_reset_count("receipt")
        else:
            card.inc_action_count("receipt")
        card.set_levels_completed("receipt", record["levels"][i + 1])
    previous, per_level = 0, []
    for level, absolute in card.actions_by_level[0]:
        per_level.append(absolute - previous)
        previous = absolute
    assert per_level == accounting(record)["complete_per_level"]
    assert card.actions[0] == len(record["actions"])
    return True


def one(game, actor, budget=2000, environments=None):
    from pathlib import Path
    import arc_agi
    from echo_arc import agent, runner, local_patch
    from echo_arc.temporal_runner import play
    agent._COMP_CACHE.clear()
    if environments is None:
        environments = Path(__file__).resolve().parents[1] / "lab/arc3/environment_files"
    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=str(environments))
    desc = next(e for e in arcade.get_environments() if e.game_id == game)
    env = Counter(arcade.make(game, seed=0))
    if actor["kind"] == "seed":
        record = runner.play(env, budget, runner.seed_for(game), agent_name="v2")
    elif actor["kind"] == "base":
        record = play(env, budget, runner.seed_for(game), agent_name="v5.8")
    else:
        cls = local_patch.agent_class(actor["program"])
        fn = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=lambda _: cls),
                          runner.play.__name__, runner.play.__defaults__)
        record = fn(env, budget, runner.seed_for(game), agent_name="final-s6")
    assert env.emitted == len(record["actions"])
    record.update(game=game, actor=actor, budget=budget, baseline=list(desc.baseline_actions or []),
                  automatic_reset_indices=env.automatic)
    record["accounting"] = accounting(record)
    record["sdk_counter_verified"] = protocol_check(record)
    record["historical_score"] = runner.official_game_score(record["actions_per_level"], record["baseline"])
    record["contract_score"] = runner.official_game_score(record["accounting"]["complete_per_level"], record["baseline"])
    return record
