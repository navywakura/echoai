"""Synthetic researcher contracts: no games, historical controls, or inference."""
import copy
import hashlib
import importlib.util
import json
import unittest
from collections import Counter
from unittest.mock import patch

from echo_arc import s6b22_search as helpers, s6b23r4_search as r4
from echo_arc.feasible_grammar import canonical, matches
from seed.game_selfimprove import sha

if importlib.util.find_spec('echo_arc.s6b24_search'):
    from echo_arc import s6b24_search as s
else:
    s = None


def fixture(cases=4):
    policy = {'program': {'patches': []}}
    features = {k: lo for k, (lo, _) in helpers.language.precise_patch.FEATURES.items()}
    features.update(reset_known=1, world_events=20)
    reads = [dict(features=features, count=1, value=40, parameter='HOLD')]
    rows = [dict(origin='DEVELOPMENT_A', levels_completed=1, score=2.0,
                 actions_per_level=[5], diagnostics=dict(consumers=copy.deepcopy(reads)))
            for _ in range(cases)]
    return policy, dict(rows=rows)


def proposal(value=12, **guard):
    return {'patches': [{'when': guard or {'reset_known': ['eq', 1]},
                         'set': {'HOLD': value}}]}


def decode_effects(payload, rows):
    if rows is None:
        return None
    cases = [dict(case_index=i, level_delta=0, score_delta=0) for i in range(payload['cohort_size'])]
    for row in rows:
        case = dict(zip(payload['effect_columns'], row))
        cases[case['case_index']] = case
    return cases


def decode_parent(payload):
    parent = copy.deepcopy(payload['parent'])
    if parent is not None:
        parent['cases'] = [dict(zip(payload['parent_case_columns'], row)) for row in parent['cases']]
        for case in parent['cases']:
            case['attribution'] = parent['attribution']
            if case['changed_consumption'] is not None:
                case['changed_consumption'] = dict(zip(payload['parent_link_columns'], case['changed_consumption']))
        parent['case_effects'] = decode_effects(payload, payload['effects'][parent['effects_id']])
    return parent


class ResearcherTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(s, 'B24 researcher is not implemented')
        self.policy, self.base = fixture()

    def request(self, kind='B24-S', history=(), index=None, base=None):
        obj = dict(policy=self.policy, base=base or self.base, own_history=list(history),
                   kind=kind, index=len(history) if index is None else index, seed=824101)
        return s.from_bytes(json.dumps(obj).encode())

    def event(self, index, kind='B24-S', p=None, gain=None, target=None, schedule=None):
        plan = schedule or s.schedule(kind, index, 824101)
        plan = dict(plan, phase='repair' if target is not None else 'global',
                    mode='REPAIR' if target is not None else 'EXPLORE')
        e = dict(id=index+1, author=plan['author'], round=index//6, slot=index,
                 target_id=target, schedule=plan, base_sha256=sha(self.policy),
                 proposal=copy.deepcopy(p), verdict='V3', actions_per_level=[[5]]*len(self.base['rows']))
        if gain is not None:
            e['development'] = dict(origin='DEVELOPMENT_A', consumer_parameter='HOLD',
                case_effects=[dict(case_index=i, level_delta=gain if i == 0 else 0,
                                   score_delta=1.0 if i == 0 and gain else 0.0)
                              for i in range(len(self.base['rows']))],
                candidate_consumers=[[dict(features=copy.deepcopy(self.base['rows'][i]['diagnostics']['consumers'][0]['features']),
                                           count=1, value=p['patches'][0]['set']['HOLD'])]
                                     for i in range(len(self.base['rows']))])
        return e

    def test_seeded_schedule_has_two_slots_per_person_per_round(self):
        for kind in ('B24-I', 'B24-C'):
            plans = [s.schedule(kind, i, 824101) for i in range(18)]
            for rnd in range(3):
                self.assertEqual(Counter(p['author'] for p in plans[rnd*6:rnd*6+6]), {0: 2, 1: 2, 2: 2})
                self.assertEqual([p['round'] for p in plans[rnd*6:rnd*6+6]], [rnd]*6)
            self.assertEqual([p['slot'] for p in plans], list(range(18)))
        self.assertEqual([s.schedule('B24-I', i, 824101) for i in range(18)],
                         [s.schedule('B24-C', i, 824101) for i in range(18)])
        self.assertNotEqual([s.schedule('B24-I', i, 824101)['author'] for i in range(18)],
                            [s.schedule('B24-I', i, 824102)['author'] for i in range(18)])

    def test_visibility_is_idempotent_and_accepts_noncontiguous_global_ids(self):
        for kind in ('B24-I', 'B24-C'):
            history = [self.event(i, kind) for i in range(13)]
            author = s.schedule(kind, 13, 824101)['author']
            expected = [e for e in history if e['author'] == author or
                        (kind == 'B24-C' and e['round'] < 2)]
            visible = s.visible_history(kind, 13, 824101, history)
            self.assertEqual(visible, expected)
            self.assertEqual(s.visible_history(kind, 13, 824101, visible), visible)
            self.assertEqual(self.request(kind, history, 13), self.request(kind, visible, 13))
            self.assertEqual(self.request(kind, visible, 13)['id'], 14)

    def test_private_outcomes_never_affect_request_or_duplicate_filter(self):
        for kind in ('B24-I', 'B24-C'):
            history = [self.event(i, kind) for i in range(5)]
            author = s.schedule(kind, 5, 824101)['author']
            req = self.request(kind, history)
            other = next(e for e in history if e['author'] != author)
            other.update(proposal=req['menu'][0]['proposal'], development={'private': 'never read'},
                         error='PRIVATE_SENTINEL', verdict='PRIVATE_SENTINEL')
            self.assertEqual(self.request(kind, history), req)
            self.assertNotIn('PRIVATE_SENTINEL', canonical(req))

    def test_missing_visible_or_forged_metadata_and_future_ids_rejected(self):
        history = [self.event(i, 'B24-C') for i in range(7)]
        for altered in (history[1:], history + [self.event(7, 'B24-C')], copy.deepcopy(history)):
            if len(altered) == 7:
                altered[0]['author'] = 99
            with self.assertRaises(ValueError):
                self.request('B24-C', altered, 7)

    def test_menu_hash_reconstruction_and_generator_share_the_same_catalog(self):
        req = self.request()
        deterministic = self.request('B24-G')
        self.assertEqual(req['menu'], deterministic['menu'])
        self.assertEqual(req['prompt'], deterministic['prompt'])
        self.assertIsNone(req['proposal'])
        self.assertEqual(req['selection_protocol'], 'candidate-id')
        self.assertTrue(req['model_call_required'])
        self.assertFalse(deterministic['model_call_required'])
        self.assertEqual(deterministic['proposal'], req['menu'][0]['proposal'])
        self.assertEqual(req['menu_sha256'], hashlib.sha256(canonical(req['menu']).encode()).hexdigest())
        last = req['menu'][-1]
        self.assertEqual(s.reconstruct(req, {'candidate_id': last['id']}), last['proposal'])
        self.assertEqual(req, self.request())
        restored = json.loads(canonical(req))
        self.assertEqual(s.reconstruct(restored, {'candidate_id': last['id']}), last['proposal'])

    def test_choice_rejects_foreign_ids_extra_fields_and_tampered_menu(self):
        req = self.request()
        for selection in ({'candidate_id': 'foreign'}, {'candidate_id': 0},
                          {'candidate_id': req['menu'][0]['id'], 'proposal': proposal()},
                          proposal(), '{"candidate_id":"a","candidate_id":"b"}'):
            with self.assertRaises(ValueError):
                s.reconstruct(req, selection)
        changed = copy.deepcopy(req)
        changed['menu'][0]['proposal']['patches'][0]['set']['HOLD'] = 24
        with self.assertRaises(ValueError):
            s.reconstruct(changed, {'candidate_id': changed['menu'][0]['id']})

    def test_r4_reference_preserves_frozen_request_payload(self):
        e = self.event(0, 'R4-REF', proposal(), gain=1)
        req = self.request('R4-REF', [e])
        old = r4.model_request('N7', 1, 824101, self.policy, self.base, [e])
        for key in ('prompt', 'type', 'target_id', 'model_call_required', 'selection_mode'):
            self.assertEqual(req[key], old[key])
        self.assertEqual(req['selection_protocol'], 'r4-json')
        self.assertEqual(req['menu'], [])
        self.assertEqual(s.reconstruct(req, proposal()), proposal())

    def test_exact_normalized_duplicates_removed_but_matching_signatures_survive(self):
        history = [self.event(0)]
        before = self.request(history=history)
        selected = next(m for m in before['menu'] if len(m['proposal']['patches'][0]['when']) > 1)
        history[0]['proposal'] = json.loads(json.dumps(selected['proposal'], sort_keys=True))
        after = self.request(history=history)
        self.assertNotIn(selected['proposal'], [m['proposal'] for m in after['menu']])
        self.assertTrue(any(r['reason'] == 'duplicate' for r in after['schedule']['rejected']))
        signatures = Counter((m['proposal']['patches'][0]['set']['HOLD'],
                              tuple(matches(m['proposal']['patches'][0]['when'], r['features'])
                                    for row in self.base['rows'] for r in row['diagnostics']['consumers']))
                             for m in after['menu'])
        self.assertGreater(max(signatures.values()), 1)

    def test_no_hold_reads_abstains_with_bounded_cost_and_proof_receipts(self):
        for row in self.base['rows']:
            row['diagnostics']['consumers'] = []
        req = self.request()
        self.assertFalse(req['model_call_required'])
        self.assertIsNone(req['proposal'])
        self.assertEqual(req['selection_protocol'], 'none')
        self.assertEqual(req['abstention'], 'NO_ELIGIBLE_CANDIDATE')
        self.assertEqual(req['menu'], [])
        self.assertEqual(req['schedule']['inspected'], 2048)
        self.assertEqual(len(req['schedule']['rejected']), 2048)
        self.assertTrue(all(r['certificate']['changed_consumptions'] == 0 for r in req['schedule']['rejected']))
        self.assertIsNone(s.reconstruct(req, None))

    def test_inactivity_compares_actual_effective_value_and_all_cases(self):
        p = proposal(12)
        self.policy['program'] = copy.deepcopy(p)
        for row in self.base['rows']:
            row['diagnostics']['consumers'][0]['value'] = 12
        receipt = s.inactivity_receipt(p, self.policy, self.base)
        self.assertEqual(receipt['base_sha256'], sha(self.policy))
        self.assertEqual(receipt['case_indices'], [0, 1, 2, 3])
        self.assertEqual(receipt['changed_consumptions'], 0)
        self.assertTrue(all(read['before'] == read['after'] == 12
                            for case in receipt['comparisons'] for read in case))
        self.policy['program']['patches'] = []
        for row in self.base['rows']:
            row['diagnostics']['consumers'][0]['value'] = 40
        self.base['rows'][-1]['diagnostics']['consumers'][0]['features']['world_events'] = 128
        self.assertIsNone(s.inactivity_receipt(proposal(12, world_events=['ge', 128]), self.policy, self.base))
        self.assertIsNotNone(s.inactivity_receipt(proposal(12, world_events=['ge', 128]), self.policy,
                                                  dict(rows=self.base['rows'][:-1])))

    def test_feature_summary_retains_all_ranges_and_only_real_joint_vectors(self):
        reads = [dict(features=dict(goal_evidence=g, world_events=w), value=12, count=1)
                 for g, w in ((0, 20), (1, 21), (0, 0), (1, 128), (1, 64))]
        summary = s.read_summary(reads, 2)
        self.assertEqual(summary['ranges'], {'goal_evidence': [0, 1], 'world_events': [0, 128]})
        self.assertEqual(summary['omitted'], 3)
        self.assertEqual(summary['all_sha256'], sha(reads))
        self.assertEqual({r['features']['world_events'] for r in summary['reads']}, {0, 128})
        self.assertTrue(all(r in reads for r in summary['reads']))

    def test_parent_survives_inactive_latest_attempt_and_all_losses_are_kept(self):
        parent = self.event(0, p=proposal(), gain=4)
        for case in parent['development']['case_effects'][1:]:
            case['score_delta'] = -0.25
        inactive = self.event(1, p=proposal(16), gain=0)
        req = self.request(history=[parent, inactive])
        self.assertEqual(req['target_id'], 1)
        self.assertEqual(req['schedule']['phase'], 'repair')
        self.assertEqual(req['schedule']['mode'], 'REPAIR')
        self.assertEqual(req['schedule']['parent_receipt_sha256'], sha(parent))
        self.assertTrue(all(m['proposal']['patches'][0]['set'] == {'HOLD': 12} for m in req['menu']))
        dossier = decode_parent(json.loads(req['prompt']))
        self.assertEqual(dossier['loss_cases'], [1, 2, 3])
        self.assertEqual([c['case_index'] for c in dossier['cases']], [0, 1, 2, 3])
        self.assertEqual(dossier['case_effects'], parent['development']['case_effects'])
        self.assertTrue(all(c['attribution'] == 'uncertain' for c in dossier['cases']))

    def test_unmeasured_or_failed_child_never_inherits_parent_gain(self):
        parent = self.event(0, p=proposal(), gain=1)
        req = self.request(history=[parent])
        self.assertEqual(req['target_id'], 1)
        chosen = req['menu'][0]['proposal']
        child = self.event(1, p=chosen, gain=0, target=1, schedule=req['schedule'])
        next_req = self.request(history=[parent, child])
        self.assertEqual(next_req['target_id'], 1)
        self.assertIsNone(next_req['predicted_gain'])
        self.assertIsNone(next_req['measured_effect'])
        self.assertTrue(all(m['measured_effect'] is None for m in next_req['menu']))

    def test_repair_children_are_only_one_guard_edit_with_fixed_hold(self):
        parent = self.event(0, p=proposal(24, reset_known=['eq', 1], world_events=['ge', 16]), gain=1)
        req = self.request(history=[parent])
        neighbors = helpers.neighbors(parent['proposal']['patches'][0]['when'])
        self.assertGreater(len(req['menu']), 0)
        for entry in req['menu']:
            self.assertIn(entry['proposal']['patches'][0]['when'], neighbors)
            self.assertEqual(entry['proposal']['patches'][0]['set'], {'HOLD': 24})
        self.assertLessEqual(req['schedule']['inspected'], 2048)
        self.assertLessEqual(len(req['menu']), 64)

    def test_exact_input_surface_and_pure_function(self):
        obj = dict(policy=self.policy, base=self.base, own_history=[], kind='B24-S', index=0, seed=824101)
        with self.assertRaises(ValueError):
            s.from_bytes(json.dumps(dict(obj, winner={})))
        before = copy.deepcopy(obj)
        with patch('builtins.open', side_effect=AssertionError('filesystem access')), \
             patch('pathlib.Path.open', side_effect=AssertionError('filesystem access')):
            first = s.from_bytes(json.dumps(obj))
        self.assertEqual(obj, before)
        self.assertEqual(first, s.from_bytes(json.dumps(obj)))

    def test_all_eighteen_slots_respect_author_node_and_lineage_budgets(self):
        for kind in ('B24-G', 'B24-S', 'B24-I', 'B24-C'):
            history = []
            for index in range(18):
                scoped = s.visible_history(kind, index, 824101, history)
                req = self.request(kind, scoped, index)
                self.assertLessEqual(req['schedule']['inspected'], 2048)
                self.assertLessEqual(len(req['menu']), 64)
                self.assertEqual(req['schedule']['inspected'], req['schedule']['eligible'] + len(req['schedule']['rejected']))
                self.assertEqual(req['schedule']['repair_quota'],
                                 s.repair_quotas()[req['schedule']['author']] if kind in ('B24-I', 'B24-C') else 8)
                chosen = req['menu'][0]['proposal'] if req['menu'] else None
                history.append(self.event(index, kind, chosen, 1 if chosen else None,
                                          req['target_id'], req['schedule']))
            repairs = [e for e in history if e['target_id'] is not None]
            self.assertLessEqual(len(repairs), 8)
            if kind in ('B24-G', 'B24-S'):
                self.assertEqual(len(repairs), 8)
            self.assertGreaterEqual(sum(e['schedule']['phase'] == 'global' for e in history), 10)
            by_id = {e['id']: e for e in history}
            children, lineages, authors = Counter(), Counter(), Counter()
            for child in repairs:
                children[child['target_id']] += 1
                authors[child['author']] += 1
                root = child
                while root['target_id'] is not None:
                    root = by_id[root['target_id']]
                lineages[root['id']] += 1
            self.assertTrue(all(n <= 2 for n in children.values()))
            self.assertTrue(all(n <= 4 for n in lineages.values()))
            if kind in ('B24-I', 'B24-C'):
                self.assertEqual(sorted(s.repair_quotas()), [2, 3, 3])
                self.assertTrue(all(n <= s.repair_quotas()[a] for a, n in authors.items()))

    def test_cooperation_imports_closed_parent_without_changing_author_or_credit(self):
        # Every completed-round author has a measured, positive branch. At least
        # one reserved next-round repair must be able to use somebody else's.
        history = [self.event(i, 'B24-C', proposal(), gain=1) for i in range(6)]
        imported = []
        for index in range(6, 12):
            req = self.request('B24-C', history, index)
            if req['target_id']:
                parent = history[req['target_id']-1]
                dossier = decode_parent(json.loads(req['prompt']))
                self.assertEqual(dossier['author'], parent['author'])
                self.assertEqual(req['schedule']['parent_receipt_sha256'], sha(parent))
                self.assertIsNone(req['measured_effect'])
                if parent['author'] != req['schedule']['author']:
                    imported.append((parent, req))
            chosen = req['menu'][0]['proposal'] if req['menu'] else None
            history.append(self.event(index, 'B24-C', chosen, 0 if chosen else None,
                                      req['target_id'], req['schedule']))
        self.assertTrue(imported, 'shared evidence never becomes an imported repair target')

    def test_c_barrier_exposes_all_closed_results_but_i_stays_private(self):
        for kind in ('B24-C', 'B24-I'):
            history = [self.event(i, kind) for i in range(6)]
            visible = s.visible_history(kind, 6, 824101, history)
            self.assertEqual(len(visible), 6 if kind == 'B24-C' else 2)
            req = self.request(kind, visible, 6)
            self.assertEqual(req['schedule']['visible_ids'], [e['id'] for e in visible])

    def test_catalog_covers_durations_lengths_features_and_exposes_truncation(self):
        req = self.request()
        menu = req['menu']
        self.assertEqual(len(menu), 64)
        self.assertEqual({m['proposal']['patches'][0]['set']['HOLD'] for m in menu}, set(helpers.VALUES))
        self.assertEqual({len(m['proposal']['patches'][0]['when']) for m in menu}, {1, 2, 3})
        self.assertEqual({k for m in menu for k in m['proposal']['patches'][0]['when']},
                         set(helpers.language.precise_patch.FEATURES))
        self.assertTrue(req['schedule']['menu_truncated'])
        self.assertGreater(req['schedule']['eligible'], 64)
        for rejection in req['schedule']['rejected']:
            if rejection['reason'] == 'inactive':
                self.assertEqual(rejection['certificate']['case_indices'], [0, 1, 2, 3])
                self.assertEqual(len(rejection['certificate']['comparisons']), 4)

    def test_partial_or_foreign_evidence_and_wrong_consumptions_are_rejected(self):
        for change in ('origin', 'consumers', 'value', 'features'):
            base = copy.deepcopy(self.base)
            if change == 'origin':
                base['rows'][0]['origin'] = 'PROTECTED_B'
            elif change == 'consumers':
                base['rows'][0]['diagnostics']['truncated'] = True
            elif change == 'value':
                base['rows'][0]['diagnostics']['consumers'][0]['value'] = 12
            else:
                del base['rows'][0]['diagnostics']['consumers'][0]['features']['world_events']
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.request(base=base)
        parent = self.event(0, p=proposal(), gain=1)
        parent['development']['candidate_consumers'].pop()
        with self.assertRaises(ValueError):
            self.request(history=[parent])

    def test_feedback_retains_exact_tiny_loss_and_actual_consumption_to_action_link(self):
        parent = self.event(0, p=proposal(), gain=1)
        parent['development']['case_effects'][3]['score_delta'] = -1.00001e-10
        parent['development']['control_links'] = [dict(case_index=3, read_action_index=2,
            consumed_values=[40, 12], first_action_divergence=5, steps_until_action_divergence=3)]
        req = self.request(history=[parent])
        dossier = decode_parent(json.loads(req['prompt']))
        self.assertEqual(dossier['loss_cases'], [3])
        self.assertEqual(dossier['case_effects'][3]['score_delta'], -1.00001e-10)
        self.assertEqual(dossier['cases'][3]['first_different_action'], 5)
        self.assertEqual(dossier['cases'][3]['changed_consumption']['consumed_values'], [40, 12])
        self.assertEqual(dossier['cases'][3]['attribution'], 'uncertain')

    def test_candidate_ids_are_bound_to_the_request_and_reconstruction_does_not_mutate(self):
        first = self.request()
        second = self.request(history=[self.event(0)])
        with self.assertRaises(ValueError):
            s.reconstruct(second, {'candidate_id': first['menu'][0]['id']})
        selected = s.reconstruct(first, {'candidate_id': first['menu'][0]['id']})
        selected['patches'][0]['set']['HOLD'] = 99
        self.assertNotEqual(first['menu'][0]['proposal'], selected)
        self.assertEqual(first, self.request())

    def test_complete_request_survives_json_custody_round_trip(self):
        req = self.request()
        self.assertEqual(req, json.loads(canonical(req)))

    def test_compact_prompt_decodes_exact_menu_and_all_archive_effects(self):
        parent = self.event(0, p=proposal(), gain=1)
        req = self.request(history=[parent])
        payload = json.loads(req['prompt'])
        self.assertEqual(payload['menu_columns'], ['id', 'proposal_id'])
        self.assertIn('atoms', payload.keys())
        decoded = []
        for ident, proposal_id in payload['menu']:
            hold, atoms = payload['proposals'][proposal_id]
            guard = {payload['context_columns'][k]: [op, value] for k, op, value in (payload['atoms'][a] for a in atoms)}
            decoded.append({'id': ident, 'proposal': proposal(hold, **guard)})
        self.assertEqual(decoded, [{'id': e['id'], 'proposal': e['proposal']} for e in req['menu']])
        effects = decode_effects(payload, payload['effects'][payload['history'][0][-1]])
        self.assertEqual(effects, parent['development']['case_effects'])

    def test_sparse_effects_distinguish_unmeasured_and_measured_zero_results(self):
        history = [self.event(0, p=proposal(), gain=None), self.event(1, p=proposal(16), gain=0)]
        payload = json.loads(self.request(history=history)['prompt'])
        self.assertIn('effects', payload.keys())
        self.assertIsNone(payload['history'][0][-1])
        self.assertEqual(payload['effects'][payload['history'][1][-1]], [])
        self.assertIsNone(decode_effects(payload, payload['history'][0][-1]))
        self.assertEqual(decode_effects(payload, payload['effects'][payload['history'][1][-1]]), history[1]['development']['case_effects'])

    def test_prompt_reference_vectors_losslessly_decode_to_real_consumptions(self):
        for i, row in enumerate(self.base['rows']):
            row['diagnostics']['consumers'][0]['features'].update(world_events=i*16, goal_evidence=i % 2)
        payload = json.loads(self.request()['prompt'])
        self.assertIn('context_reference', payload)
        for packed in payload['contexts']:
            vector = list(payload['context_reference'])
            for column, value in packed:
                vector[column] = value
            features = dict(zip(payload['context_columns'], vector))
            self.assertIn(features, [r['diagnostics']['consumers'][0]['features'] for r in self.base['rows']])

    def test_compacted_consumption_rows_preserve_counts_values_flags_and_ranges(self):
        reads = self.base['rows'][0]['diagnostics']['consumers']
        reads.append(copy.deepcopy(reads[0]))
        reads[1]['features']['world_events'] = 128
        reads[1]['count'] = 3
        parent = self.event(0, p=proposal(), gain=1)
        parent['development']['candidate_consumers'][0] = [dict(r, value=12) for r in reads]
        payload = json.loads(self.request(history=[parent])['prompt'])
        self.assertIn('read_defaults', payload['summary_columns'])
        raw = payload['parent']['cases'][0][1]
        summary = dict(zip(payload['summary_columns'], raw))
        self.assertEqual(summary['varying_ranges_[column,min,max]'], [[19, 20, 128]])
        decoded = []
        for read in summary['reads']:
            tail = list(summary['read_defaults'])
            for column, value in (read[1] if len(read) > 1 else []):
                tail[column] = value
            decoded.append(tail)
        self.assertCountEqual(decoded, [[12, 1, True, True], [12, 3, True, True]])


if __name__ == '__main__':
    unittest.main()
