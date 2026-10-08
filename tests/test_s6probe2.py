import json
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import patch as mock

from echo_arc import stale_transition as patch
from echo_arc.contrastive_grammar import build_schema, validate_answer
from seed import s6probe1 as p1, s6probe2 as p2


def probe1_rows(value):
    """Read-only: PROBE1's cached A records (its base reproduced B12 exactly)."""
    profile = json.loads((p1.ROOT / 'profile.json').read_text())
    rows = []
    for spec in p1.A:
        key = p1.sha({'profile': p1.sha(profile), 'candidate': value, 'spec': tuple(spec), 'observed': True})
        rows.append(json.loads((p1.ROOT / 'cache/main' / (key + '.json')).read_text())['record'])
    return rows


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = p1.base_program()
        cls.rows = probe1_rows(cls.base)
        cls.value = p2.plan(cls.rows)
        cls.items = cls.value['plan']

    def test_base_rows_are_the_378_measurement(self):
        self.assertEqual(p2.sha(self.rows), p1.BASE_TRACE)

    def test_plan_is_preregistered(self):
        self.assertEqual((self.value['universe'], self.value['touching'], self.value['signatures']),
                         (p2.UNIVERSE, p2.TOUCHING, p2.SIGNATURES))
        self.assertEqual(p2.sha(self.items), p2.PLAN_SHA)
        self.assertEqual(p2.budget(self.items)['total'], p2.MAX_GAMES)
        self.assertEqual([x['index'] for x in self.items], list(range(len(self.items))))
        self.assertEqual(sum(x['stage'] == 1 for x in self.items), p2.SIGNATURES)

    def test_every_candidate_is_a_legal_single_hold_proposal(self):
        schema = build_schema(self.rows, [])
        seen = set()
        for x in self.items:
            item = x['proposal']['patches'][0]
            self.assertEqual(len(x['proposal']['patches']), 1)
            self.assertEqual(list(item['set']), ['HOLD'])
            self.assertIn(item['set']['HOLD'], p2.VALUES)
            self.assertTrue(set(item['when']) <= set(patch.FEATURES))   # observables only
            self.assertIn(p2.TARGET_GAME, x['touched_games'])
            validate_answer(json.dumps(x['proposal']), schema)
            seen.add(p2.canonical(x['proposal']))
        self.assertEqual(len(seen), len(self.items))

    def test_touch_rule_never_contradicted_by_probe1_hold_measurements(self):
        """PROBE1 measured 105 HOLD singles on all 80 games: untouched games never changed."""
        reads = p2.hold_reads(self.rows)
        checked = 0
        for path in sorted((p1.ROOT / 'singles').glob('*.json')):
            single = json.loads(path.read_text())
            item = single['proposal']['patches'][0]
            if list(item['set']) != ['HOLD'] or item['set']['HOLD'] == patch.DEFAULTS['HOLD']:
                continue
            touched = {g for g, fs in reads.items() if any(p2.matches(item['when'], f) for f in fs)}
            for g, dl, ds, changed in single['effects']:
                self.assertIn(g, touched, (single['index'], g))
            checked += 1
        self.assertEqual(checked, 105)

    def test_probe1_controls_are_in_the_plan(self):
        found = p2.controls(self.items)
        self.assertEqual(found, {77: 93, 178: 3})
        for index, position in found.items():
            single = json.loads((p1.ROOT / f'singles/{index:03d}.json').read_text())
            self.assertTrue({g for g, *_ in single['effects']} <= set(self.items[position]['touched_games']))

    def test_saved_plan_tampering_is_refused(self):
        with tempfile.TemporaryDirectory() as folder, mock.object(p2, 'ROOT', Path(folder)):
            tampered = dict(self.value, plan=self.items[1:])
            (Path(folder) / 'plan.json').write_text(json.dumps(tampered))
            with self.assertRaises(RuntimeError):
                p2.frozen_plan({'rows': self.rows})


class CustodyTests(unittest.TestCase):
    def test_play_one_is_picklable_from_probe2(self):
        self.assertIs(pickle.loads(pickle.dumps(p2.play_one)), p2.play_one)
        self.assertEqual(p2.play_one.__globals__['ROOT'], p2.ROOT)
        self.assertEqual(p2.play_one.__globals__['EPHEMERAL'], p2.EPHEMERAL)

    def test_protected_and_exam_specs_are_refused_before_playing_or_cache(self):
        base = p1.base_program()
        for spec in (p1.s6b11.B[0], (2, 25100, 0, 2000)):
            with self.assertRaises(ValueError):
                p2.play_one((base, spec, None))
            for measure in (p2.measure_kept, p2.measure_ephemeral):
                with self.assertRaises(ValueError):
                    measure('x', base, [spec])

    def test_budget_and_directories_are_probe2_own(self):
        self.assertEqual(p2.reserve_games.__globals__['MAX_GAMES'], p2.MAX_GAMES)
        self.assertEqual(p2.reserve_games.__globals__['ROOT'], p2.ROOT)
        self.assertNotEqual(p2.ROOT, p1.ROOT)

    def test_requires_independent_probe1_audit(self):
        with tempfile.TemporaryDirectory() as folder, \
                mock.object(p2, 'PROBE1_AUDIT', Path(folder) / 'audit.json'):
            with self.assertRaises(FileNotFoundError):
                p2.probe1_closure()
            (Path(folder) / 'audit.json').write_text(json.dumps(
                {'valid': True, 'sample_single_indices': [77], 'cache_root': folder}))
            with self.assertRaises(RuntimeError):
                p2.probe1_closure()                                  # 178 missing from the sample
            (Path(folder) / 'audit.json').write_text(json.dumps(
                {'valid': True, 'sample_single_indices': [77, 178], 'cache_root': str(p1.ROOT)}))
            with self.assertRaises(RuntimeError):
                p2.probe1_closure()                                  # same cache is not independent
            receipt = {'valid': True, 'sample_single_indices': [77, 178, 31, 2], 'cache_root': folder,
                       'probe1_profile_sha256': p1.sha(p1.integrity()),
                       'probe1_result_sha256': p2.PROBE1_RESULT_SHA,
                       'baseline_reproduced': True, 'source_archive_valid': True,
                       'plans_reconstructed': True, 'development_only': True,
                       'B_measured': False, 'exam_opened': False,
                       'sample_results': {str(i): {'equal_to_probe1': True, 'games': len(p1.A),
                           'trace_sha256': json.loads((p1.ROOT / f'singles/{i:03d}.json').read_text())['trace_sha256']}
                           for i in (2, 31, 77, 178)}}
            (Path(folder) / 'audit.json').write_text(json.dumps(receipt))
            self.assertEqual(p2.probe1_closure()['result_sha256'], p2.PROBE1_RESULT_SHA)
            for bad in (dict(receipt, probe1_profile_sha256='stale'),
                        dict(receipt, cache_root=str(p1.ROOT / 'cache')),
                        dict(receipt, sample_results={}), dict(receipt, B_measured=True)):
                (Path(folder) / 'audit.json').write_text(json.dumps(bad))
                with self.assertRaises(RuntimeError):
                    p2.probe1_closure()


class WordingTests(unittest.TestCase):
    def test_conclusions(self):
        verified = [{'passes_v3': True, 'replay_ok': True}]
        text = p2.conclusion([{}] * 3, [{}], verified, 3)
        self.assertEqual(text['passes'], 1)
        self.assertIn('no es descubrimiento autónomo', text['text'][0])
        none = p2.conclusion([{}] * 3, [], [], 3)['text'][0]
        self.assertIn('Sin solución en esta búsqueda dirigida y con este presupuesto', none)
        self.assertIn('No demuestra que el lenguaje esté agotado', none)
        self.assertIn('Medición incompleta', p2.conclusion([{}] * 2, [], [], 3)['text'][0])
        self.assertIn('Medición incompleta', p2.conclusion([{}] * 3, [{}] * 31, [{'passes_v3': False}] * 30, 3)['text'][0])


if __name__ == '__main__':
    unittest.main()
