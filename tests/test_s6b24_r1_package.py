"""R1 package checks, run by the owned validate.py in an isolated ZIP extraction."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "lab/kaggle/s6b24-r1-20261009"
PARENT = REPO / "lab/kaggle/s6b24-20261009"
OVERRIDES = {"seed/s6b24_model.py", "seed/s6b24.py", "docs/ECHO45-S6-B24-DESIGN.md"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


class R1Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from seed import s6b24 as runner, s6b24_model as model, s6b24_preflight as preflight
        cls.runner, cls.model, cls.preflight = runner, model, preflight
        cls.project = Path(os.environ["B24_R1_TEST_PROJECT"]).resolve()
        if Path(model.__file__).resolve() != cls.project / "seed/s6b24_model.py":
            raise AssertionError("test must import the isolated ZIP, not workspace sources")
        with zipfile.ZipFile(PARENT / "dataset/echo-b24-private.zip") as z:
            cls.parent_files = {n: z.read(n) for n in z.namelist()}
        cls.parent_intent = json.loads(cls.parent_files["b24-input/intent.json"])

    def setUp(self):
        guard = patch.object(self.model.subprocess, "run",
                             side_effect=AssertionError("native/model/game subprocess forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_only_logical_batch_changes_in_the_six_recorded_commands(self):
        archive = PARENT / "output-v1/b24-evidence.tar.gz"
        with tarfile.open(archive) as tf:
            registry = json.load(tf.extractfile("b24-results/input/models.json"))
            for case in self.preflight.all_cases()[:6]:
                name = f"b24-results/format-preflight/calls/{case['arm']}/{case['index']:03d}/command.json"
                before = json.load(tf.extractfile(name))
                expected = before.copy()
                expected[expected.index("-b") + 1] = "8192"
                after = self.model.command(registry["N7"], Path(before[-1]),
                                           self.preflight.SEED + case["index"], case["request"])
                with self.subTest(case=name):
                    self.assertEqual(after, expected)
                    self.assertEqual(after[after.index("-ub") + 1], "64")

    def test_configuration_declares_only_the_transport_delta(self):
        config = json.loads(self.runner.canonical(self.runner.config()))
        self.assertEqual(config["model"].pop("logical_batch_size", None), 8192)
        self.assertEqual(config["model"].pop("microbatch_size", None), 64)
        self.assertEqual(config["model"].pop("transport_revision", None), "B24-R1")
        self.assertEqual(config, self.parent_intent["configuration"])
        self.assertEqual(self.model.MAX_CALLS, 72)

    def test_zip_has_only_declared_source_changes_and_one_new_input(self):
        with zipfile.ZipFile(PACKAGE / "dataset/echo-b24-r1-private.zip") as z:
            current = {n: z.read(n) for n in z.namelist()}
        self.assertEqual(set(current) - set(self.parent_files), {"b24-input/recovery.json"})
        self.assertEqual(set(self.parent_files) - set(current), set())
        changed = {n for n in self.parent_files if current[n] != self.parent_files[n]}
        self.assertEqual(changed, OVERRIDES | {"b24-input/intent.json"})
        intent = json.loads(current["b24-input/intent.json"])
        self.assertEqual(set(intent["sources"]), set(self.parent_intent["sources"]))
        self.assertEqual(len(intent["sources"]), 100)
        self.assertEqual(intent["configuration"], json.loads(self.runner.canonical(self.runner.config())))
        for name, expected in intent["sources"].items():
            self.assertEqual(digest(current[name]), expected, name)
            self.assertEqual((self.project / name).read_bytes(), current[name], name)
            if name in OVERRIDES:
                self.assertEqual((PACKAGE / "source-override" / name).read_bytes(), current[name])
        for name, expected in intent["inputs"].items():
            self.assertEqual(digest(current["b24-input/" + name]), expected)
        self.assertEqual(intent["contract_sha256"], intent["sources"]["docs/ECHO45-S6-B24-DESIGN.md"])

    def test_recovery_binds_parent_failure_and_all_six_charged_calls(self):
        recovery = read(self.project / "b24-input/recovery.json")
        parent = recovery["parent"]
        self.assertEqual(parent["profile_sha256"],
                         "de1c1dc9c7206ebde60a3a9de2756d3ae6c8ac1eb6d4fe7904a333553c43b488")
        self.assertEqual(parent["bundle_sha256"], digest((PARENT / "dataset/echo-b24-private.zip").read_bytes()))
        self.assertEqual(parent["evidence_sha256"], digest((PARENT / "output-v1/b24-evidence.tar.gz").read_bytes()))
        self.assertEqual(parent["failed_case"], "FORMAT-ID/001")
        self.assertEqual(parent["charged_format_calls"], 6)
        self.assertEqual(parent["successful_format_calls"], 5)
        self.assertEqual(parent["science_games_started"], 0)
        self.assertEqual(parent["scientific_model_calls_started"], 0)
        self.assertEqual([c["call_id"] for c in parent["calls"]],
                         ["FORMAT-REF/000", "FORMAT-REF/001", "FORMAT-REF/002", "FORMAT-REF/003",
                          "FORMAT-ID/000", "FORMAT-ID/001"])
        with tarfile.open(PARENT / "output-v1/b24-evidence.tar.gz") as tf:
            for call in parent["calls"]:
                data = tf.extractfile("b24-results/format-preflight/calls/" + call["call_id"] + "/result.json").read()
                self.assertEqual(call["result_sha256"], digest(data))
        self.assertEqual(recovery["limits"], dict(prior_format_calls=6, current_format_calls=8,
                                                scientific_model_calls=72, cumulative_model_calls=86,
                                                scientific_games=8310))
        self.assertFalse(recovery["initial_checkpoint"])
        for name, hashes in recovery["source_overrides"].items():
            self.assertEqual(hashes["parent_sha256"], digest(self.parent_files[name]))
            self.assertEqual(hashes["r1_sha256"], digest((self.project / name).read_bytes()))

    def test_closure_separates_current_profile_and_cumulative_calls(self):
        r = self.runner
        recovery = read(self.project / "b24-input/recovery.json")
        for scientific in (0, 7, 72):
            with self.subTest(scientific=scientific), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                inputs = root / "input"
                inputs.mkdir()
                r.atomic(inputs / "models.json", {})
                r.atomic(inputs / "recovery.json", recovery)
                r.atomic(root / "format-preflight/receipt.json", {"model_calls": 8})
                with patch.object(r, "ROOT", root), patch.object(r, "INPUT", inputs), \
                     patch.object(r, "integrity", return_value={}), \
                     patch.object(r.model, "verify_registry"), patch.object(r.preflight, "run"), \
                     patch.object(r, "micro", return_value={"winners": {}}), \
                     patch("seed.s6b24_review.review", return_value={"completed_games": 0, "model_calls": scientific}), \
                     patch.object(r, "status"):
                    closed = r.follow()
                self.assertEqual(closed["model_calls"], scientific)
                self.assertEqual(closed.get("prior_format_calls"), 6)
                self.assertEqual(closed.get("current_profile_format_calls"), 8)
                self.assertEqual(closed["format_calls"], 14)
                self.assertEqual(closed.get("current_profile_total_model_calls"), scientific + 8)
                self.assertEqual(closed["total_model_calls"], scientific + 14)
                self.assertLessEqual(closed["total_model_calls"], 86)
                self.assertEqual(closed.get("recovery_sha256"), digest((inputs / "recovery.json").read_bytes()))
                self.assertFalse(closed["s6_green"])
                self.assertFalse(closed["exam_opened"])

    def test_parser_and_acceptance_remain_strict(self):
        with self.assertRaises(json.JSONDecodeError):
            self.model.answer(" [end of text]\n\n\n", self.preflight.all_cases()[5]["request"])
        self.assertFalse(self.runner.passes(dict(gain=4, loss_indices=[2])))
        self.assertFalse(self.runner.passes(dict(gain=1, loss_indices=[])))
        self.assertTrue(self.runner.passes(dict(gain=2, loss_indices=[])))
        self.assertEqual(len(self.preflight.all_cases()), 8)

    def test_recovery_input_tamper_fails_integrity_before_execution(self):
        r = self.runner
        intent = read(self.project / "b24-input/intent.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "input"
            inputs.mkdir()
            recovery = inputs / "recovery.json"
            recovery.write_bytes((self.project / "b24-input/recovery.json").read_bytes())
            manifest = dict(execution_root=str(root), configuration=intent["configuration"],
                            sources=intent["sources"], inputs={"recovery.json": digest(recovery.read_bytes())},
                            python=".".join(map(str, sys.version_info[:3])), numpy="test", arcengine="test")
            r.atomic(inputs / "manifest.json", manifest)
            with patch.object(r, "ROOT", root), patch.object(r, "INPUT", inputs), \
                 patch("importlib.metadata.version", return_value="test"):
                self.assertEqual(r.integrity(), manifest)
                altered = read(recovery)
                altered["parent"]["charged_format_calls"] = 0
                r.atomic(recovery, altered)
                with self.assertRaisesRegex(RuntimeError, "input changed: recovery.json"):
                    r.integrity()

    def test_dataset_has_exact_native_bytes_and_fresh_private_references(self):
        native = PACKAGE / "dataset/b24-native.bin"
        self.assertEqual(digest(native.read_bytes()),
                         "a0dac5390422129b6cf4eacda0746d4e1f7b1ee81edea6c96d9aa5f90128b2f8")
        self.assertEqual({p.name for p in native.parent.iterdir()},
                         {"b24-native.bin", "echo-b24-r1-private.zip", "dataset-metadata.json"})
        dataset = read(native.parent / "dataset-metadata.json")
        kernel = read(PACKAGE / "notebook/kernel-metadata.json")
        self.assertEqual(dataset["id"], "rogeernavarro/echo45-s6b24-r1-private-20261009")
        self.assertEqual(kernel["id"], "rogeernavarro/echo45-s6b24-r1-20261009")
        self.assertTrue(kernel["is_private"])
        self.assertEqual(kernel["dataset_sources"], [dataset["id"]])
        self.assertEqual(kernel["kernel_sources"], [])
        spec = importlib.util.spec_from_file_location("r1_notebook", PACKAGE / "notebook/run.py")
        notebook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(notebook)
        self.assertEqual(str(notebook.RESULTS), "/kaggle/working/b24-r1-results")
        self.assertEqual(str(notebook.PROJECT), "/kaggle/working/b24-r1-project")
        self.assertEqual(notebook.BUNDLE_SHA, digest((PACKAGE / "dataset/echo-b24-r1-private.zip").read_bytes()))
        self.assertEqual(notebook.NATIVE_SHA, digest(native.read_bytes()))
        # Missing native input must fail before the inherited network/build fallback.
        with patch.object(Path, "rglob", return_value=iter(())):
            with self.assertRaisesRegex(RuntimeError, "exactly one pinned native archive"):
                notebook.setup_llama()


if __name__ == "__main__":
    unittest.main()
