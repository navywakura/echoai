import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.checks import sanitize_output, parse_junit, compare_states, catalog_for


class CheckTests(unittest.TestCase):
    def test_offline_targets_are_bounded_structured_arguments(self):
        from echoai.repoworld.checks import validate_plan
        plan=catalog_for('mwaskom/seaborn')
        plan['public_targets']=['tests/test_utils.py::test_'+str(i) for i in range(20)]
        self.assertEqual(len(validate_plan(plan)),64)
        plan['public_targets']=['tests/test_utils.py']*65
        with self.assertRaises(ValueError):validate_plan(plan)
        for bad in ('--override-ini=bad','../private.py','tests/x.py;bad'):
            plan['public_targets']=[bad]
            with self.assertRaises(ValueError):validate_plan(plan)

    def test_output_keeps_failure_with_byte_and_line_caps(self):
        raw='noise 😀\n'*400+'  File "a.py", line 9\nAssertionError: incorrect value\n'
        text=sanitize_output(raw)
        self.assertLessEqual(len(text.encode()),1500)
        self.assertLessEqual(len(text.splitlines()),40)
        self.assertIn('AssertionError',text)
        self.assertIn('line 9',text)

    def test_real_identities_not_fake_stdout(self):
        xml='<testsuites><testsuite tests="2" failures="1" errors="0" skipped="0"><testcase classname="tests.test_x" name="a"/><testcase classname="tests.test_x" name="b"><failure>bad</failure></testcase></testsuite></testsuites>'
        states=parse_junit(xml,exit_code=1)
        self.assertEqual(states,{'tests.test_x::a':'PASSED','tests.test_x::b':'FAILED'})
        for code in (0,2):
            with self.assertRaises(ValueError): parse_junit(xml,exit_code=code)
        for bad in ('PASSED', '<testsuites/>', '<!DOCTYPE x><testsuites/>', '<testsuite tests="1"><testcase name="a"/><testcase name="a"/></testsuite>'):
            with self.assertRaises(ValueError): parse_junit(bad,exit_code=0)

    def test_missing_skip_and_flaky_never_silently_pass(self):
        base={'a':'PASSED','b':'FAILED'}
        self.assertEqual(compare_states(base,{'a':'SKIPPED','b':'PASSED'}),('a',))
        self.assertEqual(compare_states(base,{'b':'PASSED'}),('a',))
        self.assertEqual(compare_states(base,{'a':'PASSED','b':'FAILED'}),())

    def test_all_twelve_catalogs_and_native_commands(self):
        import json
        rows=json.loads((ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json').read_text())['primary']
        repos={r['repo'] for r in rows}
        self.assertEqual(len(repos),12)
        for repo in repos:
            p=catalog_for(repo)
            self.assertTrue(p['production_roots'])
            self.assertTrue(p['public_targets'])
        self.assertIn('runtests.py',str(catalog_for('django/django')['argv']))
        self.assertIn('bin/test',catalog_for('sympy/sympy')['argv'])

