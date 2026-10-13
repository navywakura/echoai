"""Analysis safeguards; fixtures are invented, never SWE-bench measurements."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / 'scripts' / (name + '.py')
    if not path.exists():
        raise AssertionError(f'Missing requested analysis tool: {path.name}')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fixture():
    rows = []
    for instance in ['a', 'b']:
        for arm in ['S', 'I2', 'F', 'E']:
            rows.append(dict(instance_id=instance, repo='example/repo', arm=arm,
                seed=73, status='resolved' if instance == 'a' else 'budget_exhausted',
                official_raw_resolved=True if instance == 'a' else None,
                echo_verified_resolved=instance == 'a', validity_reason=None,
                tokens=100, wall_seconds=10, proposed_patches=2,
                public_regressions=1, regressions_blocked=1 if arm == 'E' else 0))
    return dict(schema_version='repoworld.analysis.v1', data_kind='synthetic',
        contract_sha256='0' * 64, audit_report_sha256=None,
        primary_instances=['a', 'b'], primary_seeds=[73], primary=rows,
        memory_chains=[], memory=[])


class AnalysisTests(unittest.TestCase):
    def test_failures_are_in_denominator_and_cost(self):
        plot = module('plot_swebench_results')
        result = plot.summarize(fixture())
        self.assertEqual(result['arms']['E']['resolved'], 1)
        self.assertEqual(result['arms']['E']['n'], 2)
        self.assertEqual(result['arms']['E']['tokens_per_resolved'], 200)

    def test_missing_arm_cannot_disappear_from_plot(self):
        plot = module('plot_swebench_results')
        data = fixture(); data['primary'].pop()
        with self.assertRaises(ValueError):
            plot.validate(data)

    def test_duplicate_or_nonfinite_or_bad_regression_counts_rejected(self):
        plot = module('plot_swebench_results')
        for change in ['duplicate', 'infinity', 'regressions']:
            data = fixture()
            if change == 'duplicate': data['primary'].append(data['primary'][0])
            if change == 'infinity': data['primary'][0]['wall_seconds'] = float('inf')
            if change == 'regressions': data['primary'][0]['regressions_blocked'] = 3
            with self.assertRaises(ValueError, msg=change): plot.validate(data)

    def test_zero_solutions_has_no_fictitious_cost_per_solution(self):
        plot = module('plot_swebench_results')
        data = fixture()
        for row in data['primary']:
            row.update(status='unresolved', official_raw_resolved=False, echo_verified_resolved=False)
        self.assertIsNone(plot.summarize(data)['arms']['E']['tokens_per_resolved'])

    def test_unstarted_rows_cannot_be_presented_as_a_complete_campaign(self):
        plot = module('plot_swebench_results')
        data = fixture(); data['primary'][0].update(status='not_started',
            official_raw_resolved=None, echo_verified_resolved=False)
        self.assertFalse(plot.summarize(data)['complete'])

    def test_measured_export_without_custody_reference_is_rejected(self):
        plot = module('plot_swebench_results')
        data = fixture(); data['data_kind'] = 'measured'
        with self.assertRaises(ValueError): plot.validate(data)

    def test_removing_a_whole_issue_is_rejected_against_registration(self):
        plot = module('plot_swebench_results')
        data = fixture(); data.update(data_kind='measured', audit_report_sha256='1'*64)
        registration = dict(primary_instances=['a','b'], primary_seeds=[73],
            contract_sha256='0'*64, repos={'a':'example/repo','b':'example/repo'},memory_chains=[])
        plot.validate(data, registration=registration)
        data['primary_instances'].remove('b')
        data['primary'] = [r for r in data['primary'] if r['instance_id'] != 'b']
        with self.assertRaises(ValueError): plot.validate(data, registration=registration)

    def test_registration_binds_the_actual_sample_bytes(self):
        plot = module('plot_swebench_results')
        contract = ROOT / 'ECHO-5.1/docs/SWE-CONTRACT.json'
        sample = ROOT / 'ECHO-5.1/docs/swebench/SWE-SAMPLE.json'
        registered = plot.load_registration(contract, sample)
        self.assertEqual(len(registered['primary_instances']),24)
        with tempfile.TemporaryDirectory() as tmp:
            altered = Path(tmp)/'sample.json'
            altered.write_bytes(sample.read_bytes()+b' ')
            with self.assertRaises(ValueError): plot.load_registration(contract,altered)

    def test_raw_and_verified_disagreement_is_visible_and_requires_reason(self):
        plot = module('plot_swebench_results')
        data = fixture(); data['primary'][0].update(status='invalid_evidence',
            echo_verified_resolved=False, validity_reason='required test skipped')
        counts = plot.summarize(data)['arms']['S']
        self.assertEqual(counts['official_raw_resolved'], 1)
        self.assertEqual(counts['resolved'], 0)
        self.assertEqual(counts['discrepancies'], 1)
        data['primary'][0]['validity_reason'] = None
        with self.assertRaises(ValueError): plot.validate(data)

    def test_resolution_extremes_are_renderable(self):
        plot = module('plot_swebench_results')
        for success in (False,True):
            data = fixture(); data['primary_instances'] = [str(i) for i in range(24)]
            data['primary'] = [dict(fixture()['primary'][j],instance_id=str(i),
                status='resolved' if success else 'unresolved',
                official_raw_resolved=success,echo_verified_resolved=success)
                for i in range(24) for j in range(4)]
            with tempfile.TemporaryDirectory() as tmp:
                plot.render(data,Path(tmp))
                self.assertTrue((Path(tmp)/'01_resolution.png').exists())

    def test_memory_counts_acquisition_once_and_pairs_targets(self):
        plot = module('plot_swebench_results')
        data = fixture()
        data['memory_chains'] = [dict(chain_id='x', repo='example/repo',
            donor_tokens=300, donor_wall_seconds=30, target_instances=['c','d'])]
        for rank, instance in enumerate(['c','d'], 1):
            for condition in ['empty','shared']:
                data['memory'].append(dict(chain_id='x', instance_id=instance,
                    position=rank, condition=condition, status='resolved',
                    official_raw_resolved=True, echo_verified_resolved=True, validity_reason=None,
                    tokens=50 if condition == 'shared' else 100, wall_seconds=5))
        summary = plot.summarize(data)['memory']
        self.assertEqual(summary['shared_full_tokens'], 400)
        self.assertEqual(summary['empty_tokens'], 200)
        data['memory'].pop()
        with self.assertRaises(ValueError): plot.validate(data)

    def test_synthetic_export_produces_four_labelled_figures_and_provenance(self):
        plot = module('plot_swebench_results')
        with tempfile.TemporaryDirectory() as tmp:
            plot.render(fixture(), Path(tmp))
            files = list(Path(tmp).iterdir())
            self.assertEqual(len([f for f in files if f.suffix == '.pdf']), 4)
            self.assertEqual(len([f for f in files if f.suffix == '.png']), 4)
            self.assertTrue(all(f.stat().st_size > 1000 for f in files if f.suffix in ('.png','.pdf')))
            info = json.loads((Path(tmp) / 'summary.json').read_text())
            self.assertEqual(info['data_kind'], 'synthetic')
            self.assertFalse(info['custody_verified_by_plotter'])


class SamplingTests(unittest.TestCase):
    def test_selection_independent_of_metadata_order_and_contains_no_gold(self):
        sample = module('select_swebench_subset')
        path = ROOT / 'ECHO-5.1/docs/swebench/SWE-LITE-PUBLIC-METADATA.json'
        self.assertTrue(path.exists(), 'public metadata projection required')
        data = json.loads(path.read_text())
        a = sample.select(data)
        reverse = copy.deepcopy(data); reverse['instances'].reverse()
        self.assertEqual(a, sample.select(reverse))
        self.assertEqual(len(a['primary']), 24)
        self.assertEqual(len({x['repo'] for x in a['primary']}), 12)
        ids = [r['instance_id'] for r in a['primary'] + a['calibration']]
        for chain in a['memory_chains']:
            ids += [chain['donor']['instance_id']] + [x['instance_id'] for x in chain['targets']]
            self.assertTrue(all(x['created_at'] > chain['donor']['created_at'] for x in chain['targets']))
        self.assertEqual(len(ids), len(set(ids)))
        dirty = copy.deepcopy(data); dirty['instances'][0]['patch'] = 'gold'
        with self.assertRaises(ValueError): sample.select(dirty)


if __name__ == '__main__':
    unittest.main()
