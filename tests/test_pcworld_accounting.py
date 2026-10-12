"""T13/T14: one shared ledger, including failed work and controller fuel.

Run with system Python: python3 -B -m unittest tests.test_pcworld_accounting -v
"""

from concurrent.futures import ThreadPoolExecutor
import importlib
from threading import Barrier
import unittest


class AccountingTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module('pcworld.accounting')
        except ModuleNotFoundError as exc:
            if exc.name != 'pcworld.accounting':
                raise
            self.fail('Budget implementation is absent')
        self.Budget = self.api.Budget
        self.Exceeded = self.api.BudgetExceeded

    def test_nonnegative_integer_limits_require_fuel(self):
        for limits in ({}, {'tokens': 1}, {'fuel': -1}, {'fuel': True},
                       {'fuel': 1.0}, {'fuel': '2'}, {1: 4, 'fuel': 1}, []):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                self.Budget(limits)
        budget = self.Budget({'fuel': 0, 'tokens': 0})
        with self.assertRaises(self.Exceeded):
            budget.reserve({})

    def test_reserves_maximum_then_charges_real_retries_and_errors(self):
        budget = self.Budget({'fuel': 5, 'tokens': 100, 'tools': 3,
                              'cpu_us': 1000, 'llm_calls': 3, 'critic_calls': 1})
        ticket = budget.reserve({'tokens': 100, 'tools': 3, 'cpu_us': 1000,
                                 'llm_calls': 3, 'critic_calls': 1})
        self.assertIsInstance(ticket, str)
        self.assertTrue(ticket)
        report = budget.report()
        self.assertEqual(report['remaining']['tokens'], 0)
        self.assertEqual(report['reserved']['llm_calls'], 3)
        self.assertEqual(report['used']['fuel'], 1)
        # Three billed attempts include two errors; the caller supplies totals.
        budget.settle(ticket, {'tokens': 72, 'tools': 3, 'cpu_us': 875,
                               'llm_calls': 3, 'critic_calls': 1})
        report = budget.report()
        self.assertEqual(report['used']['tokens'], 72)
        self.assertEqual(report['used']['llm_calls'], 3)
        self.assertEqual(report['remaining'], {'fuel': 4, 'tokens': 28,
                                             'tools': 0, 'cpu_us': 125,
                                             'llm_calls': 0, 'critic_calls': 0})
        self.assertTrue(all(value == 0 for value in report['reserved'].values()))

    def test_T13_two_specialists_contend_for_last_reservation(self):
        budget = self.Budget({'fuel': 2, 'tokens': 9, 'tools': 1})
        barrier = Barrier(2)

        def attempt():
            barrier.wait(timeout=5)
            try:
                return budget.reserve({'tokens': 9, 'tools': 1})
            except self.Exceeded:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        tickets = [result for result in results if result is not None]
        self.assertEqual(len(tickets), 1)
        report = budget.report()
        self.assertEqual(report['reserved'], {'fuel': 0, 'tokens': 9, 'tools': 1})
        self.assertEqual(report['used']['fuel'], 2)
        budget.settle(tickets[0], {'tokens': 8, 'tools': 1})
        self.assertEqual(budget.report()['used']['tokens'], 8)

    def test_failed_multidimensional_reservation_is_atomic(self):
        budget = self.Budget({'fuel': 3, 'tokens': 10, 'tools': 0})
        with self.assertRaises(self.Exceeded):
            budget.reserve({'tokens': 10, 'tools': 1})
        self.assertEqual(budget.report()['reserved']['tokens'], 0)
        ticket = budget.reserve({'tokens': 10})
        budget.settle(ticket, {'tokens': 10})
        self.assertEqual(budget.report()['remaining']['tokens'], 0)

    def test_T14_invalid_attempts_consume_fuel_until_exhaustion(self):
        budget = self.Budget({'fuel': 5, 'tokens': 2})
        for request in ({'tokens': -1}, {'tokens': True}, {'tokens': 1.5},
                        {'unknown': 1}, []):
            with self.subTest(request=request), self.assertRaises(ValueError):
                budget.reserve(request)
        self.assertEqual(budget.report()['remaining']['fuel'], 0)
        self.assertEqual(budget.report()['used']['fuel'], 5)
        with self.assertRaises(self.Exceeded):
            budget.reserve({})
        self.assertEqual(budget.report()['used']['fuel'], 5)

    def test_T14_parse_empty_block_retry_each_consume_fuel(self):
        budget = self.Budget({'fuel': 4})
        for reason in ('parse error', 'empty message', 'blocked', 'retry'):
            budget.consume_fuel(reason)
        self.assertEqual(budget.report()['remaining']['fuel'], 0)
        with self.assertRaises(self.Exceeded):
            budget.consume_fuel('retry again')

    def test_invalid_fuel_reason_is_still_an_attempt(self):
        budget = self.Budget({'fuel': 2})
        for reason in ('', None):
            with self.assertRaises(ValueError):
                budget.consume_fuel(reason)
        self.assertEqual(budget.report()['remaining']['fuel'], 0)

    def test_fuel_in_reservation_is_prepaid_and_cannot_be_refunded(self):
        budget = self.Budget({'fuel': 5, 'tokens': 10})
        ticket = budget.reserve({'fuel': 3, 'tokens': 10})
        self.assertEqual(budget.report()['remaining']['fuel'], 2)
        self.assertEqual(budget.report()['reserved']['fuel'], 0)
        budget.settle(ticket, {'fuel': 0, 'tokens': 0})
        self.assertEqual(budget.report()['remaining']['fuel'], 2)
        ticket = budget.reserve({'fuel': 0})
        budget.settle(ticket, {})
        self.assertEqual(budget.report()['remaining']['fuel'], 1)

    def test_refused_fuel_request_burns_one_attempt_without_partial_hold(self):
        budget = self.Budget({'fuel': 2, 'tokens': 10})
        with self.assertRaises(self.Exceeded):
            budget.reserve({'fuel': 3, 'tokens': 10})
        self.assertEqual(budget.report()['remaining'], {'fuel': 1, 'tokens': 10})

    def test_overrun_records_full_actual_freezes_and_keeps_other_settlements(self):
        budget = self.Budget({'fuel': 4, 'tokens': 10, 'tools': 2})
        first = budget.reserve({'tokens': 6, 'tools': 1})
        second = budget.reserve({'tokens': 4, 'tools': 1})
        with self.assertRaises(self.Exceeded):
            budget.settle(first, {'tokens': 14, 'tools': 1})
        report = budget.report()
        self.assertTrue(report['frozen'])
        self.assertEqual(report['used']['tokens'], 14)
        self.assertEqual(report['remaining']['tokens'], -8)
        with self.assertRaises(self.Exceeded):
            budget.reserve({})
        budget.settle(second, {'tokens': 3, 'tools': 1})
        self.assertEqual(budget.report()['used']['tokens'], 17)
        self.assertEqual(budget.report()['remaining']['tokens'], -7)
        self.assertEqual(budget.report()['used']['fuel'], 3)

    def test_exceeding_ticket_maximum_freezes_even_with_spare_global_capacity(self):
        budget = self.Budget({'fuel': 3, 'tokens': 100})
        ticket = budget.reserve({'tokens': 1})
        with self.assertRaises(self.Exceeded):
            budget.settle(ticket, {'tokens': 2})
        self.assertEqual(budget.report()['used']['tokens'], 2)
        self.assertTrue(budget.report()['frozen'])

    def test_actual_unbudgeted_resource_is_recorded_then_freezes(self):
        budget = self.Budget({'fuel': 2})
        ticket = budget.reserve({})
        with self.assertRaises(self.Exceeded):
            budget.settle(ticket, {'cpu_us': 19})
        self.assertEqual(budget.report()['used']['cpu_us'], 19)
        self.assertEqual(budget.report()['remaining']['cpu_us'], -19)
        self.assertTrue(budget.report()['frozen'])

    def test_actual_fuel_overrun_is_fully_charged_without_refund(self):
        budget = self.Budget({'fuel': 2})
        ticket = budget.reserve({'fuel': 2})
        with self.assertRaises(self.Exceeded):
            budget.settle(ticket, {'fuel': 5})
        self.assertEqual(budget.report()['used']['fuel'], 5)
        self.assertEqual(budget.report()['remaining']['fuel'], -3)

    def test_bad_actual_keeps_ticket_open_for_corrected_accounting(self):
        budget = self.Budget({'fuel': 1, 'tokens': 9})
        ticket = budget.reserve({'tokens': 9})
        for actual in ({'tokens': -1}, {'tokens': True}, {'tokens': 1.0}, []):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                budget.settle(ticket, actual)
        self.assertEqual(budget.report()['reserved']['tokens'], 9)
        budget.settle(ticket, {'tokens': 8})
        self.assertEqual(budget.report()['used']['tokens'], 8)

    def test_ticket_is_single_use_and_unknown_ticket_cannot_change_cost(self):
        budget = self.Budget({'fuel': 2, 'tools': 2})
        ticket = budget.reserve({'tools': 1})
        budget.settle(ticket, {'tools': 1})
        for bad_ticket in (ticket, 'unknown', None, []):
            with self.subTest(ticket=bad_ticket), self.assertRaises(ValueError):
                budget.settle(bad_ticket, {'tools': 1})
        self.assertEqual(budget.report()['used']['tools'], 1)

    def test_concurrent_settlement_cannot_charge_a_ticket_twice(self):
        budget = self.Budget({'fuel': 1, 'tools': 1})
        ticket = budget.reserve({'tools': 1})
        barrier = Barrier(2)

        def finish():
            barrier.wait(timeout=5)
            try:
                budget.settle(ticket, {'tools': 1})
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: finish(), range(2)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(budget.report()['used']['tools'], 1)

    def test_external_mutation_cannot_replenish_limits_or_change_reservations(self):
        limits = {'fuel': 2, 'tokens': 2}
        budget = self.Budget(limits)
        limits['fuel'] = 100
        request = {'tokens': 2}
        ticket = budget.reserve(request)
        request['tokens'] = 0
        report = budget.report()
        report['limits']['fuel'] = 100
        report['used']['fuel'] = 0
        report['reserved']['tokens'] = 0
        budget.settle(ticket, {'tokens': 2})
        self.assertEqual(budget.report()['remaining'], {'fuel': 1, 'tokens': 0})


if __name__ == '__main__':
    unittest.main()
