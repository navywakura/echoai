#!/usr/bin/env python3
"""GUI-4 tests.

These guard the contract in ``docs/GUI4-DESIGN.md``, not the pixels:

* custody: no new file under ``nexus0/``, no pinned file touched;
* observer: the renderer never mutates the snapshot it is handed;
* origin: every case and every exported figure declares where it came from;
* catalogue: no orphan case, and a blocked case explains itself;
* bench: real contrasts with a visible denominator and traceable export.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ECHOAI = Path(__file__).resolve().parents[1]
if str(ECHOAI.parent) not in sys.path:
    sys.path.insert(0, str(ECHOAI.parent))

from echoai.gui4 import ORIGIN_BENCH, ORIGIN_EVIDENCE, ORIGIN_LIVE, ORIGINS
from echoai.gui4 import benchmark, capture, catalog, evidence, neural


class Custody(unittest.TestCase):
    """GUI-4 must not disturb the sealed phases."""

    def test_gui4_adds_nothing_under_nexus0(self):
        offenders = [p for p in (ECHOAI / "nexus0").rglob("*.py")
                     if "gui4" in p.parts]
        self.assertEqual(offenders, [],
                         "GUI-4 code under nexus0 would break the rglob locks "
                         "of safe1, power1, host1 and cause1")

    def test_gui4_lives_outside_nexus0(self):
        self.assertTrue((ECHOAI / "gui4" / "app.py").exists())
        self.assertFalse((ECHOAI / "nexus0" / "gui4").exists())

    def test_drone3_lock_inventory_is_untouched(self):
        lock = json.loads((ECHOAI / "lab/drone3/lock.json").read_text())
        for name in lock["inventory"]:
            path = (ECHOAI.parent / name[3:]) if name.startswith("../") else (ECHOAI / name)
            self.assertTrue(path.exists(), f"pinned file vanished: {name}")
            self.assertNotIn("gui4", path.parts)


class Origins(unittest.TestCase):
    """Nothing is displayed without saying where it came from."""

    def test_every_case_declares_a_known_origin(self):
        for case in catalog.CASES:
            self.assertIn(case.origin, ORIGINS, case.ident)

    def test_every_case_declares_shows_control_and_limit(self):
        for case in catalog.CASES:
            for field in ("shows", "control", "limit", "title"):
                self.assertTrue(getattr(case, field).strip(),
                                f"{case.ident} has no {field}")

    def test_case_identifiers_are_unique(self):
        idents = [case.ident for case in catalog.CASES]
        self.assertEqual(len(idents), len(set(idents)))

    def test_blocked_cases_explain_themselves(self):
        for case in catalog.blocked():
            runnable, reason = case.availability()
            self.assertFalse(runnable)
            self.assertTrue(reason.strip(), f"{case.ident} is blocked in silence")

    def test_the_blocking_mechanism_still_reports_a_reason(self):
        """Today nothing is blocked, so check the machinery on a fake case."""
        case = catalog.Case("ficticio", "NADA", ORIGIN_BENCH, "t", "s", "c", "l",
                            _unavailable="motivo declarado")
        runnable, reason = case.availability()
        self.assertFalse(runnable)
        self.assertEqual(reason, "motivo declarado")

    def test_every_case_is_runnable_on_this_machine(self):
        """The three container-bound cases were replaced by real replays."""
        blocked = [case.ident for case in catalog.blocked()]
        self.assertEqual(blocked, [])

    def test_replay_benches_beat_or_match_their_control(self):
        cause = catalog.BENCH_RUNNERS["atribucion"]()
        arms = {arm.name: arm for arm in cause.arms}
        self.assertGreater(arms["attribution"].numerator, arms["temporal"].numerator)
        self.assertEqual(arms["attribution"].denominator,
                         arms["temporal"].denominator)

    def test_ground_replay_reads_driver_event_names(self):
        """``ev`` is 'driver' and the real name lives in ``event``."""
        result = catalog.BENCH_RUNNERS["suelo-wsp"]()
        lifecycle = next(a for a in result.arms if a.name == "lifecycle")
        self.assertGreater(lifecycle.denominator, 0)
        self.assertEqual(lifecycle.numerator, lifecycle.denominator)

    def test_no_orphan_case(self):
        """Every case resolves to a task, a runner or an evidence reader."""
        for case in catalog.CASES:
            if case.origin == ORIGIN_LIVE:
                self.assertTrue(case.task, case.ident)
            elif case.origin == ORIGIN_BENCH:
                self.assertIn(case.ident, catalog.BENCH_RUNNERS, case.ident)
            else:
                has_reader = case.reader in evidence.READERS
                self.assertTrue(has_reader or case.availability()[1],
                                f"{case.ident} has neither reader nor reason")

    def test_bench_runners_all_have_a_case(self):
        for ident in catalog.BENCH_RUNNERS:
            self.assertIn(ident, catalog.BY_ID)


class EvidenceReading(unittest.TestCase):
    """Sealed reports are read, never recomputed and never invented."""

    def test_missing_report_is_reported_not_guessed(self):
        record = evidence.read("no-existe")
        self.assertFalse(record.available)
        self.assertTrue(record.reason)
        self.assertEqual(record.figures, [])

    def test_drone3_reads_the_sealed_numbers(self):
        record = evidence.read("drone3")
        if not record.available:
            self.skipTest("lab/echo3_drone3_report.json not present")
        values = {figure.label: figure.value for figure in record.figures}
        self.assertEqual(values["Validación · vuelos"], "12/12")
        self.assertEqual(values["Confirmación · vuelos"], "12/12")
        self.assertTrue(record.limit)
        self.assertEqual(len(record.sha8), 8)

    def test_transfer3_reads_the_sealed_campaign(self):
        record = evidence.read("transfer3")
        if not record.available:
            self.skipTest("TRANSFER-3 campaign not present")
        values = {figure.label: figure.value for figure in record.figures}
        self.assertEqual(values["Validación B · bloques"], "38/0")
        self.assertEqual(values["Confirmación C · bloques"], "48/1")

    def test_dig_never_raises_on_a_missing_path(self):
        self.assertIsNone(evidence.dig({"a": [1]}, "a", 9, "b"))
        self.assertEqual(evidence.dig(None, "x", default="d"), "d")


class Benches(unittest.TestCase):
    """The reduced benches produce real contrasts, with the denominator shown."""

    def test_compose_beats_the_reactive_control(self):
        result = catalog.BENCH_RUNNERS["composicion"]()
        arms = {arm.name: arm for arm in result.arms}
        self.assertIn("echo32", arms)
        self.assertIn("q", arms)
        self.assertGreater(arms["echo32"].numerator, arms["q"].numerator)
        self.assertEqual(arms["echo32"].denominator, arms["q"].denominator)
        self.assertTrue(result.seeds)

    def test_power_beats_the_fixed_percentage(self):
        result = catalog.BENCH_RUNNERS["energia"]()
        arms = {arm.name: arm for arm in result.arms}
        self.assertGreater(arms["cost"].numerator, arms["fixed"].numerator)

    def test_every_bench_arm_has_a_denominator(self):
        for ident, run in catalog.BENCH_RUNNERS.items():
            result = run()
            self.assertTrue(result.arms, ident)
            for arm in result.arms:
                self.assertGreater(arm.denominator, 0, f"{ident}:{arm.name}")
                self.assertLessEqual(arm.numerator, arm.denominator, f"{ident}:{arm.name}")

    def test_export_is_traceable_and_says_it_is_not_a_certificate(self):
        runner = benchmark.Runner(["energia"])
        runner.start()
        runner.thread.join(timeout=120)
        self.assertTrue(runner.results)
        with tempfile.TemporaryDirectory() as directory:
            path = runner.export(Path(directory) / "bench.json")
            document = json.loads(path.read_text())
        self.assertEqual(document["origin"], ORIGIN_BENCH)
        self.assertIn("no es un certificado", document["note"].lower())
        case = document["cases"][0]
        self.assertTrue(case["seeds"])
        self.assertGreater(case["denominator"], 0)
        self.assertTrue(case["limit"])
        self.assertTrue(case["control"])

    def test_unknown_case_is_dropped_not_invented(self):
        runner = benchmark.Runner(["no-existe"])
        self.assertEqual(runner.cases, [])


class Observer(unittest.TestCase):
    """The view never writes into what it is shown."""

    def _row(self):
        return {"turn": 3, "lif_a": [1, 0, 2], "lif_b": [0, 1],
                "alif_spikes": 0b1011, "alif_adaptation": [8, 0, 8, 4],
                "q": [1, -2, 0], "action": 0, "gate": 1, "reward": -16,
                "q_delta": -4, "wsp_bytes": list(range(16)), "wsp": "YO OBSERVAR AQUI"}

    def test_history_does_not_mutate_the_snapshot(self):
        row = self._row()
        before = json.dumps(row, sort_keys=True)
        history = neural.SpikeHistory(width=8, bands=4)
        history.push(row)
        neural.Renderer(size=(420, 320)).render(history, row, "en vivo", "prueba")
        self.assertEqual(json.dumps(row, sort_keys=True), before)

    def test_render_survives_an_empty_history_and_no_row(self):
        image = neural.Renderer(size=(420, 320)).render(
            neural.SpikeHistory(width=8, bands=4), None, "", "")
        self.assertEqual(image.size, (420, 320))

    def test_adaptive_lif_bitmask_is_expanded_not_iterated(self):
        """``TemporalHead.spikes`` is an int mask; treating it as a list fails."""
        values = neural._alif({"alif_spikes": 0b1010, "alif_adaptation": [0] * 4})
        self.assertEqual(values[:4], [0.0, 1.0, 0.0, 1.0])

    def test_band_uses_population_rate_not_max(self):
        self.assertAlmostEqual(neural._band([0, 0, 0, 4], 1)[0], 1.0)

    def test_gate_names_cover_the_three_verdicts(self):
        self.assertEqual(neural.GATE_NAME, ("OK", "MODIFY", "BLOCK"))


class Recording(unittest.TestCase):
    """A clip is labelled, and works with or without ffmpeg."""

    def test_manifest_carries_case_origin_and_turn_range(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            recording = capture.Recording(Path(directory), "prueba", ORIGIN_LIVE)
            image = Image.new("RGB", (16, 16))
            recording.add(image, turn=10)
            recording.add(image, turn=11)
            manifest = recording.close()
        self.assertEqual(manifest["frames"], 2)
        self.assertEqual(manifest["first_turn"], 10)
        self.assertEqual(manifest["last_turn"], 11)
        self.assertEqual(manifest["origin"], ORIGIN_LIVE)
        self.assertEqual(manifest["origin_label"], ORIGINS[ORIGIN_LIVE])

    def test_closing_twice_is_harmless(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = capture.Recording(Path(directory), "prueba", ORIGIN_EVIDENCE)
            self.assertEqual(recording.close(), recording.close())

    def test_encode_without_frames_refuses_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = capture.Recording(Path(directory), "prueba", ORIGIN_BENCH)
            ok, message = recording.encode()
            self.assertFalse(ok)
            self.assertTrue(message)


class Window(unittest.TestCase):
    """The module imports headless; the window itself needs a display."""

    def test_app_imports_without_a_display(self):
        from echoai.gui4 import app
        self.assertIn("GUI-4", app.TUTORIAL)
        self.assertIn("no demuestra", app.TUTORIAL)

    def test_tutorial_states_the_three_origins(self):
        from echoai.gui4 import app
        for label in ORIGINS.values():
            self.assertIn(label, app.TUTORIAL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
