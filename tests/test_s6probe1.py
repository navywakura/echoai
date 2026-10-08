import json
import hashlib
import multiprocessing
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock

import numpy as np

from echo_arc.contrastive_grammar import build_schema, validate_answer
from echo_arc.contrastive_evidence import FEATURE_ORDER
from seed import s6probe1 as p


def b12_rows(value):
    """Read-only: the 80 A records B12 cached for its 378 program."""
    profile = json.loads((p.frozen.ROOT / 'profile.json').read_text())
    rows = []
    for spec in p.A:
        key = p.sha({'profile': p.sha(profile), 'candidate': value, 'spec': tuple(spec), 'observed': True})
        rows.append(json.loads((p.frozen.ROOT / 'cache/main' / (key + '.json')).read_text())['record'])
    return rows


class CensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = p.base_program()
        cls.rows = b12_rows(cls.base)
        cls.known = p.known_positive()
        cls.result = p.census(cls.rows, cls.base['program'], cls.known)

    def test_cached_rows_are_the_b12_378_measurement(self):
        self.assertEqual(sum(r['levels_completed'] for r in self.rows), p.BASE_LEVELS)
        self.assertEqual(p.sha(self.rows), p.BASE_TRACE)

    def test_census_counts(self):
        r = self.result
        self.assertEqual((r['decisions'], r['candidates'], len(r['inert'])), (39269, 70208, 154))
        self.assertEqual(r['classes_by_operator'], {'REVALIDATE_NOOP': 1374, 'HOLD': 9000, 'COOLDOWN_CAP': 5080})

    def test_inertness_never_contradicted_by_b12_measurements(self):
        sound = p.b12_soundness(self.result)
        self.assertEqual(sound['violations'], [])
        self.assertEqual(sum(sound['predicted_effect_vs_measured_change'].values()), 58)

    def test_known_positive_are_the_five_cooldown_caps(self):
        self.assertEqual(len(self.known), 5)
        self.assertTrue(all('COOLDOWN_CAP' in t for t in self.known))
        self.assertTrue(all(len(self.result['tracked'][t]) == 64 for t in self.known))

    def test_sample_is_deterministic_stratified_and_inside_grammar(self):
        first, second = p.sample(self.result, self.known), p.sample(self.result, self.known)
        self.assertEqual(first, second)
        self.assertEqual(p.sha(first), p.PLAN_SHA)
        self.assertEqual(p.sha({k: self.result[k] for k in ('inert', 'classes', 'tracked')}), p.E0_SHA)
        self.assertEqual(len(first), p.SINGLES)
        strata = Counter(item['stratum'] for item in first)
        self.assertEqual(strata['B12_POSITIVE'], 5)
        self.assertTrue(all(strata[k] >= p.MIN_PER_OPERATOR for k in p.PARAMETERS))
        classes = [item['class'] for item in first if item['class']]
        self.assertEqual(len(classes), len(set(classes)))
        self.assertFalse(set(classes) & {self.result['tracked'][t] for t in self.known})
        schema = build_schema(self.rows, [])
        for item in first:
            validate_answer(json.dumps(item['proposal']), schema)
            self.assertNotIn(p.canonical(item['proposal']), set(self.result['inert']))

    def test_pair_program_keeps_base_and_fits_rule_limit(self):
        x = {'proposal': json.loads(self.known[0])}
        y = {'proposal': json.loads(self.known[1])}
        program = p.pair_program(self.base, x, y)
        self.assertEqual(program['patches'][0], self.base['program']['patches'][0])
        self.assertEqual(len(program['patches']), 3)
        self.assertEqual(program, p.pair_program(self.base, y, x))


class RuleTests(unittest.TestCase):
    def single(self, index, operator, changed, gain=0, losses=()):
        return {'index': index, 'stratum': operator, 'changed_games': list(changed), 'gain_levels': gain,
                'loss_games': list(losses), 'proposal': {'patches': [{'set': {operator: index % 8 + 1},
                                                                      'when': {'level': ['ge', index]}}]}}

    def test_pairs_follow_the_preregistered_tiers(self):
        singles = [self.single(0, 'COOLDOWN_CAP', [1], 1), self.single(1, 'COOLDOWN_CAP', [2], 1, [2]),
                   self.single(2, 'HOLD', [3], 0), self.single(3, 'HOLD', [1], 0),
                   self.single(4, 'REVALIDATE_NOOP', [3, 4], 0)]
        plan = p.select_pairs(singles)
        tier1 = [tuple(x['pair']) for x in plan if x['tier'] == 1]
        tier2 = [tuple(x['pair']) for x in plan if x['tier'] == 2]
        self.assertEqual(tier1[0], (0, 1))                    # +2 predicted first
        self.assertIn((0, 2), tier1)                          # zero-gain partner allowed
        self.assertNotIn((2, 4), tier1)                       # no predicted gain, overlapping
        self.assertIn((2, 4), tier2)                          # interaction, both zero gain
        self.assertNotIn((0, 3), tier1)                       # overlapping games
        self.assertIn((0, 3), tier2)
        self.assertEqual(plan, p.select_pairs(singles))
        self.assertLessEqual(len(plan), p.PAIRS)

    def test_passes_v3_is_the_native_condition(self):
        row = lambda levels, score: {'levels_completed': levels, 'score': score}
        before = {'levels': 4, 'rows': [row(2, 1.0), row(2, 1.0)]}
        self.assertTrue(p.passes_v3(before, {'levels': 6, 'rows': [row(3, 1.0), row(3, 1.0)]}))
        self.assertFalse(p.passes_v3(before, {'levels': 5, 'rows': [row(3, 1.0), row(2, 1.0)]}))
        self.assertFalse(p.passes_v3(before, {'levels': 7, 'rows': [row(5, 1.0), row(2, 0.9)]}))

    def test_allocation_respects_floor_and_total(self):
        quota = p.allocate({'REVALIDATE_NOOP': 1374, 'HOLD': 9000, 'COOLDOWN_CAP': 5080}, 195, 30)
        self.assertEqual(quota, {'REVALIDATE_NOOP': 30, 'HOLD': 105, 'COOLDOWN_CAP': 60})
        self.assertEqual(p.allocate({'a': 10, 'b': 5000, 'c': 5000}, 195, 30), {'a': 10, 'b': 93, 'c': 92})

    def test_revalidate_changes_only_on_no_change_steps(self):
        F = np.zeros((4, len(FEATURE_ORDER)), np.int64)
        D = {'F': F, 'noop': np.array([True, False, True, False]), 'hold_read': np.zeros(4, bool)}
        mask = p.changed_mask(D, {'patches': []}, 'REVALIDATE_NOOP', 2, np.ones(4, bool))
        self.assertEqual(mask.tolist(), [True, False, True, False])
        self.assertFalse(p.changed_mask(D, {'patches': []}, 'HOLD', 40, np.ones(4, bool)).any())

    def test_protected_or_exam_specs_are_refused_before_playing(self):
        with mock.object(p, '_play', side_effect=AssertionError('must not play')):
            for spec in (p.s6b11.B[0], (2, 25100, 0, 2000)):
                with self.assertRaises(ValueError):
                    p.play_one((p.base_program(), spec, None))

    def test_prepare_requires_audited_b12_closure(self):
        with tempfile.TemporaryDirectory() as folder, mock.object(p.frozen, 'ROOT', Path(folder)):
            with self.assertRaises((FileNotFoundError, RuntimeError)):
                    p.b12_closure()


class EngineeringReviewTests(unittest.TestCase):
    def closure_fixture(self, root):
        original = {'kind': 'original'}
        recovery = {'original_profile_sha256': p.sha(original)}
        audit = {'valid': True, 'profile_sha256': p.sha(original)}
        campaign = {'promote': False, 'profile_sha256': p.sha(original)}
        p.atomic(root / 'campaign.json', campaign)
        r1 = {'valid': True, 'profile_sha256': p.sha(recovery),
              'original_audit_sha256': p.sha(audit),
              'campaign_sha256': hashlib.sha256((root / 'campaign.json').read_bytes()).hexdigest()}
        p.atomic(root / 'campaign-audit.json', audit)
        p.atomic(root / 'runtime-recovery1/campaign-audit.json', r1)
        p.atomic(root / 'closed.json', {'result': 'CAMPAIGN_NO_PROMOTION', 's6_green': False,
                 'exam_opened': False, 'recovery_profile_sha256': p.sha(recovery)})
        return original, recovery

    def test_requires_both_audits_linked_to_exact_campaign_and_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original, recovery = self.closure_fixture(root)
            with mock.object(p.frozen, 'ROOT', root), mock.object(p.frozen, 'integrity', return_value=original), \
                    mock.object(p.recovery, 'integrity', return_value=recovery):
                self.assertEqual(p.b12_closure()['result'], 'CAMPAIGN_NO_PROMOTION')
                checks = [('campaign-audit.json', 'valid', False),
                          ('runtime-recovery1/campaign-audit.json', 'valid', False),
                          ('runtime-recovery1/campaign-audit.json', 'campaign_sha256', 'bad'),
                          ('runtime-recovery1/campaign-audit.json', 'original_audit_sha256', 'bad'),
                          ('closed.json', 'recovery_profile_sha256', 'bad'),
                          ('closed.json', 'result', 'EXAM_CLOSED'),
                          ('closed.json', 'exam_opened', None)]
                for name, key, wrong in checks:
                    with self.subTest(name=name, key=key):
                        self.closure_fixture(root)
                        data = json.loads((root / name).read_text())
                        data[key] = wrong
                        p.atomic(root / name, data)
                        with self.assertRaises(RuntimeError):
                            p.b12_closure()

    def test_refuses_missing_recovery_audit_and_actual_opened_exam(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original, recovery = self.closure_fixture(root)
            with mock.object(p.frozen, 'ROOT', root), mock.object(p.frozen, 'integrity', return_value=original), \
                    mock.object(p.recovery, 'integrity', return_value=recovery):
                (root / 'runtime-recovery1/campaign-audit.json').unlink()
                with self.assertRaises(FileNotFoundError):
                    p.b12_closure()
                self.closure_fixture(root)
                p.atomic(root / 'exam/opened.json', {})
                with self.assertRaises(RuntimeError):
                    p.b12_closure()

    def test_measure_refuses_protected_cache_requests_before_integrity(self):
        for measure in (p.measure_kept, p.measure_ephemeral):
            with self.assertRaisesRegex(ValueError, 'development A only'):
                measure('must-not-read', {}, [p.s6b11.B[0]])

    def test_spawned_worker_rejects_protected_spec_without_playing(self):
        with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn')) as pool:
            task = pool.submit(p.play_one, ({}, p.s6b11.B[0], None))
            with self.assertRaisesRegex(ValueError, 'development A only'):
                task.result(timeout=30)

    def test_ephemeral_cleanup_only_after_durable_cache_and_keeps_failure_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ephemeral, live = root / 'ephemeral', root / 'live'
            profile, value, row = {'profile': 'test'}, p.strategy(), {'fake': 'no game executed'}
            spec = p.A[0]
            key = p.sha({'profile': p.sha(profile), 'candidate': value, 'spec': tuple(spec), 'observed': True})
            directory = ephemeral / 'main' / p.Execution.digest(value) / key
            directory.mkdir(parents=True)
            log = directory / 'arc-decisions.jsonl'
            log.write_text('test journal\n')
            p.atomic(root / 'profile.json', profile)
            with mock.object(p, 'ROOT', root), mock.object(p, 'EPHEMERAL', ephemeral), \
                    mock.object(p, 'LIVE', live), mock.object(p, '_play', return_value=row):
                real_atomic = p.atomic
                def checked_atomic(path, data):
                    if Path(path) == root / 'cache/main' / (key + '.json'):
                        self.assertTrue(log.exists())
                    return real_atomic(path, data)
                with mock.object(p, 'atomic', side_effect=checked_atomic):
                    self.assertEqual(p.play_one((value, spec, str(directory))), row)
                saved = json.loads((root / 'cache/main' / (key + '.json')).read_text())
                self.assertEqual(saved['record'], row)
                self.assertFalse(directory.exists())
                directory.mkdir(parents=True)
                log.write_text('failed game evidence\n')
                with mock.object(p, '_play', side_effect=RuntimeError('execution failed')):
                    with self.assertRaises(RuntimeError):
                        p.play_one((value, spec, str(directory)))
                self.assertTrue(log.exists())

    def test_journal_path_escape_refused_before_play(self):
        with mock.object(p, '_play') as play:
            for directory in (str(p.EPHEMERAL), str(p.EPHEMERAL / '..' / 'outside')):
                with self.assertRaises(ValueError):
                    p.play_one(({}, p.A[0], directory))
            play.assert_not_called()

    def test_replay_mismatch_stops_and_preserves_receipt(self):
        before = {'levels': 378, 'rows': []}
        after = {'levels': 380, 'trace_digest': 'first', 'rows': []}
        with tempfile.TemporaryDirectory() as tmp, mock.object(p, 'ROOT', Path(tmp)), \
                mock.object(p, 'measure_ephemeral', return_value=after), \
                mock.object(p, 'measure_kept', return_value={'trace_digest': 'different'}), \
                mock.object(p, 'passes_v3', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'replay mismatch'):
                p.evaluate('singles/000', {}, before, replay=False)
            receipt = json.loads((Path(tmp) / 'failures/singles/000.json').read_text())
            self.assertEqual(receipt['determinism'], 'failed')

    def test_negative_without_replay_is_explicitly_unchecked(self):
        value = {'levels': 378, 'trace_digest': 'first', 'rows': []}
        with mock.object(p, 'measure_ephemeral', return_value=value), mock.object(p, 'measure_kept') as repeat:
            row = p.evaluate('singles/001', {}, value, replay=False)
            self.assertEqual(row['determinism'], 'not_checked')
            repeat.assert_not_called()

    def test_no_unjustified_confidence_bound_in_conclusion(self):
        result = p.conclusion([{'passes_v3': False} for _ in range(200)], [])
        self.assertIn('No encontramos', result['text'][0])
        self.assertNotIn('95', ' '.join(result['text']))

    def test_saved_plan_hash_is_checked_on_resume_before_play(self):
        with tempfile.TemporaryDirectory() as tmp, mock.object(p, 'ROOT', Path(tmp)), \
                mock.object(p, 'prepare'), mock.object(p, 'measure_base', return_value=({}, {})), \
                mock.object(p, 'evaluate') as evaluate:
            e0 = {'inert': [], 'classes': {}, 'tracked': {}}
            p.atomic(Path(tmp) / 'e0.json', e0)
            p.atomic(Path(tmp) / 'singles-plan.json', {'plan': [{'changed': True}]})
            with mock.object(p, 'E0_SHA', p.sha(e0)):
                with self.assertRaisesRegex(RuntimeError, 'saved single-candidate plan'):
                    p.run(limit=5)
            evaluate.assert_not_called()

    def test_wait_estimate_stops_on_failed_b12_without_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.atomic(root / 'b12/supervisor.json', {'state': 'FINISHED', 'exit_code': 1})
            with mock.object(p, 'ROOT', root / 'probe'), mock.object(p.frozen, 'ROOT', root / 'b12'), \
                    mock.object(p, 'hashes', return_value={}), mock.object(p, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'without audited closure'):
                    p.wait_estimate()
                run.assert_not_called()

    def test_wait_estimate_starts_only_after_verified_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.atomic(root / 'b12/closed.json', {})
            with mock.object(p, 'ROOT', root / 'probe'), mock.object(p.frozen, 'ROOT', root / 'b12'), \
                    mock.object(p, 'hashes', return_value={}), mock.object(p, 'run') as run, \
                    mock.object(p, 'b12_closure', side_effect=RuntimeError('invalid R1')):
                with self.assertRaisesRegex(RuntimeError, 'invalid R1'):
                    p.wait_estimate()
                run.assert_not_called()

    def test_wait_estimate_never_starts_full_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p.atomic(root / 'b12/closed.json', {})
            with mock.object(p, 'ROOT', root / 'probe'), mock.object(p.frozen, 'ROOT', root / 'b12'), \
                    mock.object(p, 'hashes', return_value={}), mock.object(p, 'b12_closure'), \
                    mock.object(p, 'run') as run:
                p.wait_estimate()
                run.assert_called_once_with(limit=p.ESTIMATE_CANDIDATES)


if __name__ == '__main__':
    unittest.main()
