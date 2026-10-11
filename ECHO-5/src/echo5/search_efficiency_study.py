"""Paired search interventions over public tasks; truth stays in this evaluator."""
from collections import Counter
from copy import deepcopy

from .budget import Budget
from . import transfer_independent as data
from . import transfer
from .solver import solve
from .evaluation import digest

STRATEGIES = ('baseline', 'memoized', 'certified', 'certified_bound')


def _score(case, result, evaluation=None):
    # Legacy templates predate the category field. Adapt the evaluator's view,
    # preserving the original receipt and never sending this metadata to solve.
    category = data._category(case['family'])
    if 'category' in case and case['category'] != category:
        raise ValueError('generator category differs from its registered family')
    return data.score_result({**case, 'category': category}, result, ledger=evaluation)


def normalize_config(config):
    defaults = {'seed': 2700000, 'cases_per_family': 3, 'budget': 2000000,
                'families': list(data.FAMILIES),
                'template_families': list(data.COMPARABLE_FAMILIES),
                'strategies': list(STRATEGIES)}
    if type(config) is not dict or set(config)-set(defaults):
        raise ValueError('unknown search study configuration')
    cfg = {**defaults, **deepcopy(config)}
    if type(cfg['seed']) is not int or not 0 <= cfg['seed'] < 2**63:
        raise ValueError('integer study seed required')
    if type(cfg['cases_per_family']) is not int or not 1 <= cfg['cases_per_family'] <= 12:
        raise ValueError('bounded cohort required')
    if type(cfg['budget']) is not int or cfg['budget'] != 2000000 or cfg['strategies'] != list(STRATEGIES):
        raise ValueError('all four strategies at the original 2M work limit required')
    for key, allowed in (('families', data.FAMILIES), ('template_families', data.COMPARABLE_FAMILIES)):
        if (type(cfg[key]) is not list or len(set(cfg[key])) != len(cfg[key])
                or any(f not in allowed for f in cfg[key])):
            raise ValueError('invalid study families')
    if not cfg['families']:
        raise ValueError('independent tasks required')
    return cfg


def _cohort(cfg, preparation):
    for generator, families in (('independent', cfg['families']), ('template', cfg['template_families'])):
        for family in families:
            for index in range(cfg['cases_per_family']):
                seed = data._seed(cfg['seed'], generator, family, index, preparation)
                yield generator, family, seed


def summarize(rows, config):
    cfg = normalize_config(config)
    expected = {(g, f, seed, s) for g, f, seed in _cohort(cfg, Budget(1000000)) for s in STRATEGIES}
    keyed = {(r['generator'], r['family'], r['case']['seed'], r['strategy']): r for r in rows}
    if len(keyed) != len(rows) or set(keyed) != expected:
        raise ValueError('missing, duplicated or unregistered search result')
    for g, f, seed in _cohort(cfg, Budget(1000000)):
        group = [keyed[(g, f, seed, s)] for s in STRATEGIES]
        if len({r['case']['public_sha256'] for r in group}) != 1:
            raise ValueError('paired strategies saw different inputs')
        for row in group:
            result = row['result']
            if result['metrics']['used'] > cfg['budget'] or result['metrics']['used'] != sum(result['metrics']['counts'].values()):
                raise ValueError('invalid work ledger')
            if result['test_verified'] is not False:
                raise ValueError('actor crossed query verification boundary')
            score = _score(row['case'], result)
            if any(row[k] != score[k] for k in score):
                raise ValueError('external score mismatch')
    summary = {}
    for generator, families in (('independent', cfg['families']), ('template', cfg['template_families'])):
        summary[generator] = {}
        for family in [*families, 'supported_total']:
            subset = [r for r in rows if r['generator'] == generator and
                      (r['family'] == family if family != 'supported_total' else r['family'] in data.SUPPORTED_FAMILIES)]
            arms = {}
            for strategy in STRATEGIES:
                arm = [r for r in subset if r['strategy'] == strategy]
                arms[strategy] = {'cases': len(arm), 'exact': sum(r['outcome'] == 'exact' for r in arm),
                                  'wrong': sum(r['outcome'] == 'wrong' for r in arm),
                                  'false_commitments': sum(r['false_commitment'] for r in arm),
                                  'work': sum(r['result']['metrics']['used'] for r in arm),
                                  'statuses': dict(Counter(r['result']['status'] for r in arm))}
            summary[generator][family] = arms
    return summary


def run_benchmark(config, *, journal=None, progress=None):
    cfg = normalize_config(config)
    rows, preparation = [], Budget(20000000)
    cohort = list(_cohort(cfg, preparation))
    for generator, family, seed in cohort:
        if generator == 'independent':
            case = data.make_case(seed, family)
        else:
            case = transfer.make_case(seed, family, split='development', budget=preparation,
                                      demonstrations=3, queries=2)
        for strategy in STRATEGIES:
            evaluation = Budget(20000000)
            public = data.public_task(case, ledger=evaluation)
            if digest(public) != case['public_sha256']:
                raise ValueError('public input mismatch')
            if journal:
                journal.write(kind='efficiency_case_begin', generator=generator, family=family,
                              case_seed=seed, strategy=strategy, public_sha256=case['public_sha256'])
            result = solve(public, budget=cfg['budget'], cache_policy='interned', journal=journal,
                           synthesis={'max_depth': 4, 'beam_width': 24, 'max_candidates': 12000,
                                      'grammar': None,
                                      'strategy': 'certified' if strategy == 'certified_bound' else strategy,
                                      'ranking_bound': strategy == 'certified_bound'})
            score = _score(case, result, evaluation)
            rows.append({'generator': generator, 'family': family, 'case': case, 'strategy': strategy,
                         'result': result, **score, 'evaluation': evaluation.snapshot()})
            if journal:
                journal.write(kind='efficiency_case_result', generator=generator, family=family,
                              case_seed=seed, strategy=strategy, **score,
                              work=result['metrics']['used'], status=result['status'])
            if progress:
                progress(completed=len(rows), total=len(STRATEGIES)*len(cohort), last={
                    'generator': generator, 'family': family, 'strategy': strategy,
                    'status': result['status'], **score})
    return {'schema': 'echo5.search-efficiency.v1', 'config': cfg, 'rows': rows,
            'summary': summarize(rows, cfg), 'preparation': preparation.snapshot(),
            'instrument_valid': True, 'promotion': False,
            'scope': 'paired bounded full-DSL search; same generators, distinct registered seeds'}
