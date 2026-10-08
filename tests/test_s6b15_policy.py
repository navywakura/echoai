import copy
import json
import unittest

from echo_arc import repair_experiments as e
from echo_arc.contrastive_grammar import choices, witnesses
from echo_arc.feasible_grammar import matches
from seed import s6b15_prompt as p
from seed import s6b13 as engine
from tests.test_s6b14_policy import measured_row, observed_event


def event(current, index, parameter, *, gain=0, kind='WAIT', behavior=None):
    item = observed_event(current, index, kind=kind, gain=gain)
    item['proposal']['patches'][0]['set'] = {parameter: 1 + index % 2}
    item['development']['behavior_sha256'] = behavior or str(index)
    return item


class PolicyTests(unittest.TestCase):
    def test_requested_WAIT_does_not_credit_waiting_when_measured_REVALIDATE(self):
        current = engine.strategy()
        history = [event(current, 0, 'REVALIDATE_NOOP')]
        stats = e.statistics(current, history)
        self.assertEqual(stats['REVALIDATE_NOOP']['measured_total'], 1)
        self.assertEqual(stats['HOLD']['measured_total'], 0)
        self.assertEqual(e.select([measured_row()], 'echo', current, history, 1)['parameter'], 'HOLD')

    def test_unmeasured_invalid_attempt_consumes_call_but_is_not_an_exploration(self):
        current = engine.strategy()
        value = dict(id=0, type='WAIT', verdict='V1', experiment={'call_consumed': True})
        self.assertTrue(all(v['measured_total'] == 0 for v in e.statistics(current, [value]).values()))

    def test_incorporated_gain_not_carried_into_new_base_credit(self):
        old, current = engine.strategy(), engine.strategy(program={'patches': [
            {'set': {'REVALIDATE_NOOP': 1}, 'when': {'reset_known': ['eq', 1]}}]})
        history = [event(old, 0, 'REVALIDATE_NOOP', gain=13)]
        history[0]['verdict'] = 'accepted'
        stat = e.statistics(current, history)['REVALIDATE_NOOP']
        self.assertEqual((stat['measured_total'], stat['measured_on_base'], stat['residual_gain']), (1, 0, 0))

    def test_numeric_alternation_pauses_whole_family(self):
        current = engine.strategy()
        history = [event(current, i, 'REVALIDATE_NOOP') for i in range(2)]
        self.assertEqual(e.paused_family(current, history), 'prediction')
        for arm in ('echo', 'fijo'):
            chosen = e.select([measured_row()], arm, current, history, 3)
            self.assertIn(chosen['parameter'], ('HOLD', 'COOLDOWN_CAP'))
        history.append(event(current, 2, 'HOLD'))
        self.assertIsNone(e.paused_family(current, history))

    def test_fixed_schedule_covers_three_operators(self):
        self.assertEqual([e.select([measured_row()], 'fijo', engine.strategy(), [], i)['parameter']
                          for i in range(3)], list(p.compact.PARAMETERS))

    def test_family_pause_does_not_empty_sole_available_family(self):
        current = engine.strategy()
        history = [event(current, i, 'REVALIDATE_NOOP') for i in range(2)]
        selected = e.select([measured_row(hold=False)], 'echo', current, history, 3)
        self.assertEqual(selected['parameter'], 'REVALIDATE_NOOP')
        self.assertIsNone(selected['paused_family'])

    def test_WAIT_grammar_and_checker_reject_other_operator(self):
        current = engine.strategy()
        req = p.request('fijo', 1, current, {'rows': [measured_row()]}, [])
        self.assertEqual({param for param, _, _ in choices(req['guard_schema'])}, {'HOLD'})
        other = json.dumps({'patches': [{'set': {'REVALIDATE_NOOP': 2}, 'when': {'reset_known': ['eq', 1]}}]})
        with self.assertRaises(ValueError):
            p.check_answer(other, req)

    def test_guard_cannot_borrow_witness_from_unselected_case(self):
        rows = [measured_row(i, hold=False) for i in range(4)]
        for i, row in enumerate(rows):
            for w in row['diagnostics']['contradiction_features']:
                w['features']['reset_known'] = int(i == 3)
            row['levels_completed'] = 5 if i == 3 else 0
        req = p.request('fijo', 0, engine.strategy(), {'rows': rows}, [])
        self.assertNotIn(3, req['selected_cases'])
        self.assertTrue(choices(req['guard_schema']))
        for param, _, guards in choices(req['guard_schema']):
            selected = witnesses([rows[i] for i in req['selected_cases']])[param]
            self.assertTrue(all(any(matches(g, w['features']) for w in selected) for g in guards))
            self.assertFalse(any(g.get('reset_known') == ['eq', 1] for g in guards))

    def test_numeric_extrema_and_frequencies_are_actual_joint_observations(self):
        row = measured_row()
        template = row['diagnostics']['consumers'][0]
        row['diagnostics']['consumers'] = []
        for n in (14, 89, 104, 899):
            w = copy.deepcopy(template)
            w['features']['world_events'], w['count'] = n, 2
            row['diagnostics']['consumers'].append(w)
        new = e.case_data([row], 'HOLD', 2)[0]['observations']
        old = e.case_data([row], 'HOLD', 2, numeric=False)[0]['observations']
        self.assertEqual(new['columns'], ['world_events'])
        self.assertEqual(new['points'], [[14], [899]])
        self.assertEqual(new['ranges']['world_events'], [14, 899])
        self.assertEqual(new['frequencies'], [2, 2])
        self.assertNotEqual(new['points'], old['points'])

    def test_all_context_sizes_keep_latest_receipt(self):
        current = engine.strategy()
        history = [event(current, 0, 'REVALIDATE_NOOP')]
        req = p.context('echo', 1, current, {'rows': [measured_row()]}, history)
        for variant in req['prompt_variants']:
            data = json.loads(variant.split('DATA=', 1)[1].split('\nJSON only.', 1)[0])
            self.assertEqual(data['latest_attempt'], p.receipt(history[-1]))

    def test_absent_control_readings_have_no_invented_ranges(self):
        summary = e.case_data([measured_row(hold=False)], 'HOLD')[0]['observations']
        self.assertEqual(summary['points'], [])
        self.assertEqual(summary['ranges'], {})
        self.assertEqual(summary['constant'], {})

    def test_private_rows_rejected_before_selection_or_summary(self):
        row = measured_row()
        row['origin'] = 'PROTECTED_B'
        with self.assertRaises(ValueError):
            e.case_data([row], 'HOLD')
        with self.assertRaises(ValueError):
            p.request('echo', 0, engine.strategy(), {'rows': [row]}, [])


if __name__ == '__main__':
    unittest.main()
