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
        plan['public_targets']=['tests/test_utils.py::test_'+str(i) for i in range(128)]
        self.assertEqual(len(validate_plan(plan)),64)
        plan['public_targets']=['tests/test_utils.py']*129
        with self.assertRaises(ValueError):validate_plan(plan)
        for bad in ('--override-ini=bad','../private.py','tests/x.py;bad'):
            plan['public_targets']=[bad]
            with self.assertRaises(ValueError):validate_plan(plan)

    def test_operator_targets_have_an_aggregate_utf8_byte_limit(self):
        from echoai.repoworld.checks import validate_plan
        plan=catalog_for('mwaskom/seaborn')
        plan['public_targets']=['tests/'+'a'*(8192-6), 'tests/'+'b'*(8192-6)]
        self.assertEqual(len(validate_plan(plan)),64)
        plan['public_targets'][1]+='b'
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

    def test_junit_accepts_large_reports_with_a_512_kib_byte_ceiling(self):
        prefix='<testsuite tests="1"><testcase classname="public" name="large"><system-out>'
        suffix='</system-out></testcase></testsuite>'
        expected={'public::large':'PASSED'}
        for size in (90*1024,512*1024):
            xml=prefix+'x'*(size-len(prefix+suffix))+suffix
            self.assertEqual(parse_junit(xml.encode(),exit_code=0),expected)
        oversized=prefix+'x'*(512*1024+1-len(prefix+suffix))+suffix
        multibyte=prefix+'é'*(256*1024)+suffix
        entity='<!DOCTYPE testsuite [<!ENTITY injected "payload">]><testsuite tests="1"><testcase name="&injected;"/></testsuite>'
        for xml in (oversized,multibyte,entity):
            with self.subTest(kind=xml[:40]):
                with self.assertRaises(ValueError):parse_junit(xml,exit_code=0)

    def test_junit_optional_skip_reasons_preserve_default_api(self):
        xml='<testsuite tests="2"><testcase classname="public" name="pass"/><testcase classname="public" name="skip"><skipped message="Python 2 &amp; legacy only">fixture location</skipped></testcase></testsuite>'
        expected={'public::pass':'PASSED','public::skip':'SKIPPED'}
        self.assertEqual(parse_junit(xml,exit_code=0),expected)
        self.assertEqual(parse_junit(xml,exit_code=0,include_skip_reasons=True),
                         (expected,{'public::skip':'Python 2 & legacy only'}))

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

    def test_public_catalogs_use_project_source_layout(self):
        self.assertIn('/work/lib',catalog_for('matplotlib/matplotlib')['env']['PYTHONPATH'].split(':'))
        self.assertEqual(catalog_for('pylint-dev/pylint')['public_targets'],['tests/lint/test_utils.py'])

    def test_site_joblib_is_an_explicit_sklearn_only_profile(self):
        from echoai.repoworld.checks import validate_plan
        plan=catalog_for('scikit-learn/scikit-learn');plan['env']['SKLEARN_SITE_JOBLIB']='1'
        self.assertEqual(len(validate_plan(plan)),64)
        plan['env']['SKLEARN_SITE_JOBLIB']='0'
        with self.assertRaises(ValueError):validate_plan(plan)
        plan=catalog_for('psf/requests');plan['env']['SKLEARN_SITE_JOBLIB']='1'
        with self.assertRaises(ValueError):validate_plan(plan)

