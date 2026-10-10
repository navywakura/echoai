"""Synthetic B24 review regressions: no games, models, network or saved results.

Run with: python3 -B -m unittest tests.test_s6b24_review -v

The control contains invented, arithmetically consistent receipts for all five
arms, including format/model calls. Nothing here is evidence of execution. Each
negative test changes one layer of that control and expects the real reviewer
to reject it. These rejection tests are deliberately red before findings 1/2
are fixed; do not mark them expectedFailure or replace the reviewer with a mock.
"""
import gzip
from pathlib import Path
import shutil
import tempfile
import unittest

from echo_arc import contrastive_evidence, precise_patch
from seed import s6b24 as runner
from seed import s6b24_model as model
from seed import s6b24_preflight as preflight
from seed import s6b24_review as reviewer


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(runner.canonical(value), encoding='utf-8')


def measurement(rows):
    return dict(rows=rows, levels=sum(r['levels_completed'] for r in rows),
                score=sum(r['score'] for r in rows), trace_digest=runner.sha(rows))


class SyntheticReview:
    """Complete on-disk fixture; only stdlib and pure production helpers run."""

    def __init__(self, root, *, broad_specs=None, broad_policy_override=None):
        self.root = root
        self.input = root / 'input'
        self.jobs = []
        self.broad_specs = runner.DEVELOPMENT if broad_specs is None else broad_specs
        self.broad_policy_override = broad_policy_override
        self.policy = runner.engine.strategy(program={'patches': []})
        self.base = self.make_measurement(runner.A, self.policy)
        self.registry = {'N7': dict(cli='/synthetic/never-execute-cli',
                                   model='/synthetic/no-weights', backend='cuda',
                                   gpu_layers=99, tensor_split='1,1')}
        write_json(self.input / 'baseline.json', dict(
            policy=self.policy, behavior=self.base['rows'], levels=61))
        write_json(self.input / 'models.json', self.registry)
        self.manifest = dict(
            configuration=runner.config(),
            sources={'seed/s6b24_review.py': runner.file_sha(Path(reviewer.__file__))},
            inputs={p.name: runner.file_sha(p) for p in self.input.glob('*.json')})
        write_json(self.input / 'manifest.json', self.manifest)
        self.profile = runner.sha(self.manifest)
        self.format_receipts()
        self.science_receipts()

    def make_measurement(self, specs, policy, *, improved=False):
        features = {k: bounds[0] for k, bounds in precise_patch.FEATURES.items()}
        features.update(reset_known=1, world_events=20)
        columns = list(contrastive_evidence.FEATURE_ORDER)
        rows = []
        for index, spec in enumerate(specs):
            # The 14 micro cases sum to 61, then 63 after the synthetic gain.
            levels = 5 if index < 12 else 1 if index == 12 else 0
            if improved and index == 13:
                levels = 2
            consumed = runner.search.effective('HOLD', features, policy)
            actions = [['K', 1, None] for _ in range(max(1, levels))]
            outcome = dict(changed=True, game_over=False, level_up=False)
            read = dict(parameter='HOLD', features=dict(features), count=1,
                        value=consumed, remaining_before=0)
            timeline_read = dict(read, decision_index=0, action_index=0,
                                 immediate_outcome=outcome)
            timeline_read.pop('count')
            row = dict(zip(('version', 'seed', 'rep', 'budget'), spec))
            row.update(origin='DEVELOPMENT_A', levels_completed=levels,
                       actions_per_level=[1] * levels, baseline=[1] * 5,
                       score=100 * sum(range(1, levels + 1)) / 15,
                       actions=actions, frames=['synthetic'] * (len(actions) + 1),
                       automatic_reset_indices=[], resets=0,
                       policy_sha256=runner.sha(policy),
                       diagnostics=dict(consumers=[read], trajectory=dict(
                           features=columns, steps=[dict(
                               f=[features[k] for k in columns],
                               outcome=[True, False, False]) for _ in actions]),
                           control_timeline=dict(version=1, reads=[timeline_read])))
            rows.append(row)
        return measurement(rows)

    def call_receipt(self, root, arm, index, req, seed, response):
        folder = root / 'calls' / arm / f'{index:03d}'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'prompt.txt').write_text(model.prior.chat(req['prompt']))
        (folder / 'stdout.txt').write_text(runner.canonical(response))
        (folder / 'stderr.txt').write_text('')
        write_json(folder / 'tokens.json', {'N7': [1]})
        write_json(folder / 'output-tokens.json', [2])
        write_json(folder / 'command.json', model.command(
            self.registry['N7'], folder / 'prompt.txt', seed, req))
        result = dict(arm=arm, seed=seed, request_sha256=runner.sha(req),
                      profile_sha256=self.profile, transport_ok=True,
                      returncode=0, error=None, seconds=1.0,
                      proposal=model.answer(runner.canonical(response), req),
                      usage=dict(model_calls=1, input_tokens=1, output_tokens=1,
                                 max_output_tokens=768,
                                 gpu_allocation_seconds_upper_bound=2.0),
                      files={name: runner.file_sha(folder / name) for name in (
                          'prompt.txt', 'tokens.json', 'command.json', 'stdout.txt',
                          'stderr.txt', 'output-tokens.json')})
        write_json(folder / 'result.json', result)
        return result

    def format_receipts(self):
        root = self.root / 'format-preflight'
        calls = []
        for case in preflight.all_cases():
            arm, index = case['arm'], case['index']
            response = case['expected'] if arm == 'FORMAT-REF' else {'candidate_id': 'C000'}
            self.call_receipt(root, arm, index, case['request'],
                              preflight.SEED + index, response)
            calls.append(f'{arm}/{index:03d}')
        write_json(root / 'model-budget.json', dict(calls=calls))
        write_json(root / 'receipt.json', dict(
            valid=True, profile_sha256=self.profile,
            cases_sha256=runner.sha(preflight.all_cases()), model_calls=8,
            games_started=False, calls=calls))

    def triple(self, namespace, label, policy, specs, result, request=None):
        task = dict(namespace=namespace, label=label, policy=policy,
                    specs=specs, request_receipt=request)
        write_json(self.root / 'audit-tasks' / (runner.sha(task) + '.json'), task)
        for ns, part, leaf in ((namespace, 'main', label),
                               (namespace, 'replay', label + '/replay'),
                               (namespace + '-audit', 'main', label)):
            write_json(self.root / ns / 'measurements' / (leaf + '.json'), result)
            for row in result['rows']:
                spec = [row[k] for k in ('version', 'seed', 'rep', 'budget')]
                key = runner.sha(dict(profile=self.profile, namespace=ns,
                                      policy=policy, spec=spec,
                                      observed=list(map(tuple, specs)) == runner.A,
                                      evaluation=leaf.removesuffix('/replay')))
                cache = f'{ns}/cache/{part}/{key}.json'
                job = dict(job_id=len(self.jobs), task_id=runner.sha([ns, part, key]),
                           key=key, spec=spec, policy_sha256=runner.sha(policy),
                           cache=cache, namespace=ns, label=leaf,
                           journal=(f'{ns}/journals/{part}/{key}'
                                    if list(map(tuple, specs)) == runner.A else None),
                           allocation=runner.allocation(ns), reserved_at='synthetic',
                           execution_root=str(self.root), input_root=str(self.input))
                self.jobs.append(job)
                write_json(self.root / cache, dict(key=key, digest=runner.sha(row),
                                                  record=row, job_id=job['job_id']))
                ident = dict(job_id=job['job_id'], task_id=job['task_id'], at='synthetic')
                write_json(self.root / 'executions/started' / f"{job['job_id']:06d}.json",
                           dict(ident, pid=0))
                write_json(self.root / 'executions/completed' / f"{job['job_id']:06d}.json",
                           dict(ident, namespace=ns, case=spec, elapsed=1.0,
                                cpu_seconds=1.0, max_rss_kib=0,
                                record_sha256=runner.sha(row)))
        write_json(self.root / namespace / 'audits' / (label + '.json'), dict(
            valid=True, measurement_sha256=runner.sha(result),
            task_sha256=runner.sha(task), independent_execution=True,
            profile_sha256=self.profile))

    def science_receipts(self):
        cells, winners, calls, transfer = [], {}, [], {}
        broad = self.make_measurement(self.broad_specs, self.policy)
        self.triple('v-broad', 'baseline', self.policy, self.broad_specs, broad)
        for arm in runner.CELLS:
            self.triple('s-' + arm, 'baseline', self.policy, runner.A, self.base)
            inputs = dict(policy=self.policy, base=self.base, own_history=[],
                          kind=arm, index=0, seed=runner.SEED)
            raw = runner.canonical(inputs).encode()
            digest = runner.sha(inputs)
            req = runner.search.from_bytes(raw)
            folder = self.root / 'investigator-inputs'
            folder.mkdir(exist_ok=True)
            (folder / (digest + '.json.gz')).write_bytes(gzip.compress(raw, mtime=0))
            relative = f'requests/{arm}/000.json'
            write_json(self.root / relative, dict(
                request=req, input_sha256=digest, request_sha256=runner.sha(req),
                profile_sha256=self.profile))
            if req['model_call_required']:
                response = ({'patches': [{'when': {'reset_known': ['eq', 1]},
                                         'set': {'HOLD': 12}}]} if arm == 'R4-REF'
                            else {'candidate_id': req['menu'][0]['id']})
                call = self.call_receipt(self.root, arm, 0, req, runner.SEED, response)
                proposal, usage = call['proposal'], call['usage']
                calls.append(arm + '/000')
            else:
                proposal = req['proposal']
                usage = dict(model_calls=0, input_tokens=0, output_tokens=0)
            candidate = runner.engine.strategy(program=runner.engine.patch.append(
                self.policy['program'], proposal))
            after = self.make_measurement(runner.A, candidate, improved=True)
            self.triple('s-' + arm, 'candidate/000', candidate, runner.A, after, relative)
            change = reviewer.diff(self.base, after)
            event = dict(id=1, type=req['type'], target_id=req['target_id'],
                         schedule=req['schedule'], base_sha256=runner.sha(self.policy),
                         proposal=proposal, usage=usage, candidate=candidate,
                         A=change, levels=after['levels'],
                         proposal_sha256=runner.sha(proposal),
                         policy_sha256=runner.sha(candidate),
                         trajectory_sha256=after['trace_digest'],
                         actions_per_level=[row['actions_per_level'] for row in after['rows']],
                         development=runner.guard_search.comparison(self.base, after, 'HOLD'),
                         verdict='A_ONLY_PASS', audited=True,
                         author=req['schedule']['author'], round=0, slot=0)
            write_json(self.root / 'steps' / arm / '000.json', dict(
                event=event, input_sha256=digest, request_sha256=runner.sha(req),
                seconds=1.0, cpu_seconds=1.0))
            write_json(self.root / 'timings' / arm / '000.json', dict(
                arm=arm, slot=0,
                segments=[dict(seconds=1.0, cpu_seconds=1.0, exit='complete')]))
            cells.append(dict(arm=arm, slot=1, verdict='A_ONLY_PASS', diff=change))
            winners[arm] = dict(slot=1, policy=candidate, policy_sha256=runner.sha(candidate))
            measured_policy = (self.broad_policy_override
                               if arm == 'B24-G' and self.broad_policy_override is not None
                               else candidate)
            after_broad = self.make_measurement(self.broad_specs, measured_policy)
            self.triple('v-broad', 'candidate/' + arm, measured_policy,
                        self.broad_specs, after_broad)
            write_json(self.root / 'validation/v-broad' / (arm + '.json'), dict(
                valid=True, passed=False, diff=reviewer.diff(broad, after_broad),
                policy_sha256=runner.sha(candidate), cohort_sha256=runner.sha(runner.DEVELOPMENT),
                audited=True, base_levels=broad['levels'], levels=after_broad['levels']))
            transfer[arm] = dict(broad='FAIL', retention='NOT_RUN')
        write_json(self.root / 'budget.json', dict(
            jobs=self.jobs, scheduled_games=len(self.jobs), cap=8310))
        micro = dict(valid=True, cells=cells, winners=winners,
                     profile_sha256=self.profile, s6_green=False, exam_opened=False)
        write_json(self.root / 'micro.json', micro)
        write_json(self.root / 'finalists.json', dict(selection=winners, micro_sha256=runner.sha(micro)))
        write_json(self.root / 'model-budget.json', dict(calls=calls))
        write_json(self.root / 'transfer.json', transfer)

    def review(self):
        return reviewer.review(self.root, self.input / 'manifest.json')


class ReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='b24-synthetic-review-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, **kwargs):
        return SyntheticReview(self.root, **kwargs)

    def test_complete_synthetic_control_is_accepted(self):
        fixture = self.fixture()
        result = fixture.review()
        self.assertTrue(result['valid'])
        self.assertEqual(result['logical_attempts'], 5)
        self.assertEqual(result['measurements'], 48)
        self.assertEqual(result['completed_games'], 3300)
        self.assertEqual(len({job['task_id'] for job in fixture.jobs}), 3300)

    def test_rejects_measurements_without_any_physical_execution(self):
        fixture = self.fixture()
        root = fixture.root
        shutil.rmtree(root / 'executions')
        for namespace in root.iterdir():
            if (namespace / 'cache').is_dir():
                shutil.rmtree(namespace / 'cache')
        write_json(root / 'budget.json', dict(jobs=[], scheduled_games=0, cap=8310))
        with self.assertRaisesRegex(RuntimeError, 'measurement lacks physical execution cache'):
            fixture.review()

    def test_rejects_measurement_rows_unbound_to_execution_cache(self):
        # Cache, completion receipt and cache digest agree with each other, but
        # the corresponding measurement still contains the original frame.
        fixture = self.fixture()
        job = next(j for j in fixture.jobs
                   if j['namespace'] == 's-B24-G' and j['label'] == 'candidate/000')
        path = fixture.root / job['cache']
        cache = reviewer.read(path)
        cache['record']['frames'][0] = 'different-but-self-consistent-cache'
        cache['digest'] = runner.sha(cache['record'])
        write_json(path, cache)
        completed = fixture.root / 'executions/completed' / f"{job['job_id']:06d}.json"
        receipt = reviewer.read(completed)
        receipt['record_sha256'] = cache['digest']
        write_json(completed, receipt)
        with self.assertRaisesRegex(RuntimeError, 'measurement row differs from execution cache'):
            fixture.review()

    def test_rejects_self_consistent_broad_receipts_for_wrong_cohort(self):
        # Every broad execution/task/cache/measurement agrees on the same
        # undeclared seed; pairing and arithmetic alone must not authorize it.
        specs = list(runner.DEVELOPMENT)
        version, _, rep, budget = specs[0]
        specs[0] = (version, 999999, rep, budget)
        fixture = self.fixture(broad_specs=specs)
        with self.assertRaisesRegex(RuntimeError, 'cohort'):
            fixture.review()

    def test_rejects_self_consistent_broad_receipts_for_wrong_policy(self):
        # All three physical receipts and the audit task identify the baseline
        # policy, while the frozen finalist is the selected candidate.
        base_policy = runner.engine.strategy(program={'patches': []})
        fixture = self.fixture(broad_policy_override=base_policy)
        with self.assertRaisesRegex(RuntimeError, 'measurement row uses wrong policy'):
            fixture.review()

    def test_rejects_forged_per_case_feedback_with_unchanged_measurements(self):
        fixture = self.fixture()
        path = fixture.root / 'steps/B24-G/000.json'
        saved = reviewer.read(path)
        saved['event']['development']['case_effects'][0]['level_delta'] += 7
        write_json(path, saved)
        with self.assertRaisesRegex(RuntimeError, 'research feedback differs from measured trajectories'):
            fixture.review()

    def test_rejects_forged_consumption_feedback_with_unchanged_measurements(self):
        fixture = self.fixture()
        path = fixture.root / 'steps/B24-G/000.json'
        saved = reviewer.read(path)
        saved['event']['development']['candidate_consumers'][0][0]['features']['world_events'] += 1
        write_json(path, saved)
        with self.assertRaisesRegex(RuntimeError, 'research feedback differs from measured trajectories'):
            fixture.review()


if __name__ == '__main__':
    unittest.main()
