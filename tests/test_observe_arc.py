"""Real training-game parity. Run in the separately managed ARC environment."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HAS_ARC = all(importlib.util.find_spec(m) is not None for m in ("numpy", "arcengine"))


@unittest.skipUnless(HAS_ARC, "requires the managed ARC environment")
class ArcParityTests(unittest.TestCase):
    def test_observer_preserves_all_actions_frames_results_and_original_registry(self):
        from echo_arc import agent, runner
        from echo_arc.observe import Journal, observed_play
        from seed import arc3gym as gym
        old_version = gym.VERSION
        sources = (Path(agent.__file__), Path(runner.__file__), Path(gym.__file__))
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources]
        original_play, original_factory = runner.play, runner.agent_class
        registry = dict(runner.AGENTS)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for version in (2, 3):
                    gym.VERSION = version
                    for seed in (0, 1, 2, 3):
                        with self.subTest(version=version, seed=seed):
                            agent._COMP_CACHE.clear()
                            control = runner.play(gym.GymEnv(seed), 180, 12345 + seed, agent_name="v5.7")
                            agent._COMP_CACHE.clear()
                            path = Path(tmp) / f"v{version}-{seed}.jsonl"
                            journal = Journal(path)
                            try:
                                observed = observed_play(gym.GymEnv(seed), 180, 12345 + seed,
                                                         journal, agent_name="v5.7")
                            finally:
                                journal.close()
                            self.assertEqual(observed, control)
                            rows = [json.loads(line) for line in path.read_text().splitlines()]
                            decisions = [r for r in rows if r["kind"] == "decision"]
                            observations = [r for r in rows if r["kind"] == "observation"]
                            self.assertEqual(len(decisions), len(control["actions"]) - control["resets"])
                            self.assertEqual([r["frame"] for r in observations], control["frames"])
                            self.assertTrue(all(r["returns"] for r in decisions))
                            self.assertEqual(sum(r["kind"] == "result" for r in rows), len(decisions))
                self.assertIs(runner.play, original_play)
                self.assertIs(runner.agent_class, original_factory)
                self.assertEqual(runner.AGENTS, registry)
                self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in sources], before)
        finally:
            gym.VERSION = old_version
            agent._COMP_CACHE.clear()


if __name__ == "__main__":
    unittest.main()
