"""ARC integration, hidden-state controls and passive observer parity."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HAS_ARC = all(importlib.util.find_spec(m) is not None for m in ("numpy", "arcengine"))


@unittest.skipUnless(HAS_ARC, "requires the separately managed ARC environment")
class TemporalArcTests(unittest.TestCase):
    def test_click_pseudo_keys_do_not_enter_the_keyboard_controller(self):
        from echo_arc.temporal_agent import Arc3EchoV58
        a = Arc3EchoV58([6], 123)
        a.me, a.pos = (3, 9), (10, 10)
        a.my_cells = [[(y, x) for y in range(4, 7) for x in range(4, 7)]]
        a.keys = [100, 101]
        a.rule = {100: (6, 0), 101: (0, 6)}
        a.pkey_xy = {100: (40, 40), 101: (40, 50)}
        for k in a.keys:
            a.key_tries[k] = a.babble
        self.assertFalse(a._motor_ready())

    def test_order_is_learned_with_roles_at_either_position_and_other_palettes(self):
        from echo_arc.temporal_runner import play
        from seed import arc3gym as gym
        version0 = gym.VERSION
        try:
            gym.VERSION = 3
            for reverse in (False, True):
                lv = gym.Level("H1", 7, 5)
                lv.start, lv.goal = (0, 2), (6, 2)
                lv.switch, lv.switch2 = ((4, 3), (2, 1)) if reverse else ((2, 1), (4, 3))
                lv.gate, lv.walls = {(5, 2)}, {(6, 1), (6, 3)}
                lv.optimal = len(lv.solve())
                game = gym.Game.__new__(gym.Game)
                game.cs, game.ox, game.oy = 4, 2, 2
                cols = list(range(12)) if not reverse else list(reversed(range(12)))
                game.pal = dict(zip(("out", "floor", "wall", "me", "goal", "switch", "gate",
                                     "box", "on", "off", "dummy", "bar"), cols))
                game.available = [1, 2, 3, 4]
                game.levels, game.baseline = [lv] * 5, [lv.optimal] * 5
                env = gym.GymEnv.__new__(gym.GymEnv)
                env.game, env.level, env.s = game, 0, None
                rec = play(env, 1500, 6789)
                self.assertEqual(rec["levels_completed"], 5)
                expected = [game.pal["switch"], game.pal["dummy"]]
                rules = rec["model"]["temporal"]["orders"]
                learned = [r for r in rules if r["sequence"] == expected]
                self.assertTrue(learned, rules)
                self.assertGreaterEqual(learned[0]["supports"], 2)
        finally:
            gym.VERSION = version0

    def test_remote_effect_excludes_body_motion_and_clock(self):
        import numpy as np
        from echo_arc.temporal_agent import Arc3EchoV58
        a = Arc3EchoV58([1, 2, 3, 4], 123)
        a.passed[0] = 10
        old = [(4, 4), (4, 5), (5, 4), (5, 5)]
        new = [(4, 6), (4, 7), (5, 6), (5, 7)]
        a.my_cells = [new]
        before = np.zeros((20, 20), dtype=np.int8)
        after = before.copy()
        for y, x in old:
            before[y, x] = 3
        for y, x in new:
            after[y, x] = 3
        before[-1, :] = 9
        self.assertIsNone(a._remote_change(before, after, [old]))
        before[12:14, 12:14] = 9
        effect = a._remote_change(before, after, [old])
        self.assertEqual(effect["change"], "removed")
        self.assertEqual(effect["region"], [12, 12, 13, 13])

    def test_no_memory_ablation_preserves_v57_and_observation_preserves_v58(self):
        from echo_arc import agent, runner
        from echo_arc.temporal_runner import play
        from echo_arc.observe import Journal
        from seed import arc3gym as gym
        version0 = gym.VERSION
        registry = dict(runner.AGENTS)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for version, seed in ((2, 0), (3, 0), (3, 4)):
                    gym.VERSION = version
                    agent._COMP_CACHE.clear()
                    control = runner.play(gym.GymEnv(seed), 180, 12345, agent_name="v5.7")
                    agent._COMP_CACHE.clear()
                    off = play(gym.GymEnv(seed), 180, 12345, agent_name="v5.8-nomemory")
                    off["model"].pop("temporal")
                    self.assertEqual(off, control)
                    agent._COMP_CACHE.clear()
                    naked = play(gym.GymEnv(seed), 180, 12345)
                    agent._COMP_CACHE.clear()
                    journal = Journal(Path(tmp) / f"{version}-{seed}.jsonl")
                    try:
                        observed = play(gym.GymEnv(seed), 180, 12345, journal=journal)
                    finally:
                        journal.close()
                    self.assertEqual(observed, naked)
                    rows = [json.loads(line) for line in journal.path.read_text().splitlines()]
                    decisions = [r for r in rows if r["kind"] == "decision"]
                    self.assertTrue(all(r["returns"] for r in decisions))
                    self.assertTrue(any("temporal_state" in r["after"] for r in decisions))
                    self.assertEqual(runner.AGENTS, registry)
        finally:
            gym.VERSION = version0

    def test_observed_reset_clears_episode_and_new_level_clears_coordinates(self):
        from echo_arc.temporal_agent import Arc3EchoV58
        a = Arc3EchoV58([1, 2, 3, 4], 123)
        a.markers[(10, 20)] = 7
        a.order_memory.enter(7)
        a.order_memory.enter(8, effect=True)
        a.count_memory.complete = True
        a.count_memory.position((10, 20), 7, effect=True)
        a.temporal_queue.append((10, 20))
        a._reset_temporal(False)
        self.assertEqual(a.count_memory.counts, {})
        self.assertEqual(list(a.order_memory.history), [])
        self.assertEqual(list(a.temporal_queue), [])
        self.assertEqual(a.count_memory.threshold(7), 1)
        self.assertEqual(a.order_memory.candidates(), [(7, 8)])
        self.assertEqual(a.markers, {(10, 20): 7})
        a._reset_temporal(True)
        self.assertEqual(a.markers, {})

    def test_actor_learns_non_three_thresholds_from_frames_only(self):
        from echo_arc import agent
        from echo_arc.temporal_runner import play
        from seed import arc3gym as gym

        class CountingLevel(gym.Level):
            def __init__(self, threshold):
                super().__init__("H3", 7, 5)
                self.threshold = threshold
                self.start, self.switch, self.goal = (0, 2), (2, 1), (6, 2)
                self.gate, self.walls = {(5, 2)}, {(6, 1), (6, 3)}
                self.optimal = len(self.solve())

            def _hstep(self, state, action):
                pos, opened, box, lit, count = state
                if action not in gym.DIRS:
                    return state
                dx, dy = gym.DIRS[action]
                new = (pos[0] + dx, pos[1] + dy)
                if not self.free(new, opened):
                    return state
                if new == self.switch and not opened:
                    count += 1
                    opened = count >= self.threshold
                return new, opened, box, lit, count

        class SurfaceOnly:
            """The actor's runner can only reset/step; private state is not exposed."""
            def __init__(self, env):
                self._reset = env.reset
                self._step = env.step
            def reset(self):
                return self._reset()
            def step(self, action, data=None):
                return self._step(action, data)

        old_version = gym.VERSION
        try:
            gym.VERSION = 3
            for threshold in (2, 4, 5):
                with self.subTest(threshold=threshold):
                    game = gym.Game.__new__(gym.Game)
                    game.cs, game.ox, game.oy = 4, 2, 2
                    game.pal = dict(zip(("out", "floor", "wall", "me", "goal", "switch", "gate",
                                         "box", "on", "off", "dummy", "bar"), range(12)))
                    game.available = [1, 2, 3, 4]
                    game.levels = [CountingLevel(threshold) for _ in range(5)]
                    game.baseline = [lv.optimal for lv in game.levels]
                    game.game_id = "controlled-count"
                    env = gym.GymEnv.__new__(gym.GymEnv)
                    env.game, env.level, env.s = game, 0, None
                    # Hidden counter and closed gate render identically for counts below threshold.
                    lv = game.levels[0]
                    s = list(lv.init())
                    frames = []
                    for count in range(threshold):
                        s[4] = count
                        frames.append(game.render(lv, tuple(s), 100, 100).tobytes())
                    self.assertEqual(len(set(frames)), 1)
                    agent._COMP_CACHE.clear()
                    rec = play(SurfaceOnly(env), 1500, 12345)
                    self.assertEqual(rec["levels_completed"], 5)
                    rules = rec["model"]["temporal"]["thresholds"]
                    best = [r for r in rules if r["kind"] == game.pal["switch"] and r["entries"] == threshold]
                    self.assertTrue(best, rules)
                    self.assertGreaterEqual(best[0]["supports"], 2)
        finally:
            gym.VERSION = old_version


if __name__ == "__main__":
    unittest.main()
