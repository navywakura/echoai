"""Paired native-environment pilot with genuinely matched exploration skills.

No training, privileged world queries, mission overrides or automatic promotion.
All episode results are judged by native MiniGrid/BabyAI and replayable.
"""
from copy import deepcopy
import math
import time

from .sandbox import EXPLORATION_MODES, EXPLORATION_OPTIONS, Session
from .sandbox_eval import normalize_spec, replay_episode

PROFILES = {
    'objects_small': {'scenario': 'objects', 'environment_options': {'room_size': 5, 'num_dists': 3}},
    'objects_medium': {'scenario': 'objects', 'environment_options': {'room_size': 8, 'num_dists': 5}},
    'objects_large': {'scenario': 'objects', 'environment_options': {'room_size': 10, 'num_dists': 8}},
    'key_small': {'scenario': 'door_key', 'environment': 'MiniGrid-DoorKey-6x6-v0'},
    'key_medium': {'scenario': 'door_key', 'environment': 'MiniGrid-DoorKey-8x8-v0'},
    'ordered_doors': {'scenario': 'ordered_doors'},
    'put_next': {'scenario': 'put_next', 'environment_options': {'room_size': 8, 'num_objs': 6}},
}


def normalize_config(config):
    defaults = {'seed': 1400000, 'cases_per_profile': 4, 'actions': 256,
                'work': 750000, 'profiles': list(PROFILES),
                'modes': list(EXPLORATION_MODES), 'policy_seed': 0,
                'practical_success_difference': 0.1, 'confirmation': False}
    if type(config) is not dict or set(config) - set(defaults):
        raise ValueError('unknown exploration pilot configuration')
    value = {**defaults, **deepcopy(config)}
    for key, low, high in (('seed', 1400000, 1490000), ('cases_per_profile', 1, 32),
                           ('actions', 1, 1024), ('work', 1, 100000000)):
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError('invalid exploration limit: ' + key)
    modes = value['modes']
    if (type(modes) is not list or any(type(m) is not str for m in modes) or
            not (modes == list(EXPLORATION_MODES) or
                 (len(modes) == len(EXPLORATION_OPTIONS) and set(modes) == set(EXPLORATION_OPTIONS)))):
        raise ValueError('the original ordered three arms or all four matched arms are required')
    if type(value['policy_seed']) is not int or value['policy_seed'] != 0:
        raise ValueError('fixed policy seed 0 is required')
    profiles = value['profiles']
    if type(profiles) is not list or not profiles or len(set(profiles)) != len(profiles) or any(p not in PROFILES for p in profiles):
        raise ValueError('invalid or duplicate profiles')
    if value['confirmation'] is not False or value['practical_success_difference'] != 0.1:
        raise ValueError('this preregistered pilot cannot grant confirmation')
    return value


def case_specs(config):
    config = normalize_config(config)
    cases = []
    for profile in config['profiles']:
        for index in range(config['cases_per_profile']):
            # Stable profile offsets: changing a subset never renumbers worlds.
            seed = config['seed'] + list(PROFILES).index(profile)*1000 + index
            for mode in config['modes']:
                spec = normalize_spec({**PROFILES[profile], 'seed': seed, 'mode': mode,
                    'budget': {'actions': config['actions'], 'work': config['work']}})
                cases.append({'id': f'{profile}:{seed}', 'profile': profile, 'spec': spec})
    return cases


def paired_summary(control, treatment, *, comparisons=2):
    """Success differences; conservative finite-sample uncertainty for a pilot.

    Hoeffding bound for independent world-level paired differences in [-1,1].
    alpha=.05/comparisons; default .025 for the historical two comparisons.
    An all-tie sample does NOT produce an unjustified zero-width interval.
    """
    if not control or len(control) != len(treatment):
        raise ValueError('nonempty paired samples required')
    if type(comparisons) is not int or comparisons < 1:
        raise ValueError('positive comparison count required')
    n = len(control)
    wins = sum(b and not a for a, b in zip(control, treatment))
    losses = sum(a and not b for a, b in zip(control, treatment))
    m = wins + losses
    p = min(1.0, 2*sum(math.comb(m, k) for k in range(min(wins, losses)+1))/2**m) if m else 1.0
    delta = (wins-losses)/n
    alpha = 0.05/comparisons
    radius = math.sqrt(2*math.log(2/alpha)/n)
    return {'cases': n, 'wins': wins, 'losses': losses, 'ties': n-m,
            'success_difference': delta, 'discordance_exact_p_two_sided': p,
            'difference_interval': [max(-1., delta-radius), min(1., delta+radius)],
            'interval_method': 'Hoeffding paired bounded differences; alpha=' + str(alpha).lstrip('0'),
            'scope': 'descriptive pilot; no promotion or equivalence claim'}


def summarize(rows, config):
    config = normalize_config(config)
    expected = {(c['id'], c['spec']['mode']) for c in case_specs(config)}
    keyed = {(r['id'], r['mode']): r for r in rows}
    if len(keyed) != len(rows) or set(keyed) != expected:
        raise ValueError('missing, extra or duplicated paired episode')
    groups = {'all': rows}
    groups.update({p: [r for r in rows if r['profile'] == p] for p in config['profiles']})
    results = {}
    for name, subset in groups.items():
        ids = sorted({r['id'] for r in subset})
        arms = {}
        for mode in config['modes']:
            arm = [keyed[(case, mode)] for case in ids]
            arms[mode] = {'episodes': len(arm), 'successes': sum(r['success'] for r in arm),
                         'actions': sum(r['actions'] for r in arm),
                         'work': sum(r['work'] for r in arm),
                         'budget_exhausted': sum(r['status'] == 'budget_exhausted' for r in arm)}
        comparisons = {}
        treatment = config['modes'][0]
        for control in config['modes'][1:]:
            comparisons[control] = paired_summary([keyed[(case, control)]['success'] for case in ids],
                [keyed[(case, treatment)]['success'] for case in ids],
                comparisons=len(config['modes']) - 1)
            comparisons[control]['total_work_difference'] = arms[treatment]['work'] - arms[control]['work']
        results[name] = {'arms': arms, 'comparisons': comparisons}
    return {'complete_pairs': True, 'groups': results,
            'scientific_verdict': 'pilot_only_confirmation_not_run', 'promotion': False}


def run_benchmark(config, *, journal=None, progress=None):
    config = normalize_config(config)
    specs, rows = case_specs(config), []
    started = time.monotonic()
    for case in specs:
        if journal:
            journal.write(kind='exploration_episode_begin', case_id=case['id'], profile=case['profile'],
                          mode=case['spec']['mode'])
        with Session(case['spec'], journal=journal) as session:
            while not session.done:
                session.step()
            episode = session.result()
        payload = episode['receipt']['payload']
        row = {'id': case['id'], 'profile': case['profile'], 'mode': case['spec']['mode'],
               'success': payload['adjudication']['success'], 'actions': payload['actions'],
               'work': payload['work']['used'], 'status': payload['status'], 'episode': episode}
        rows.append(row)
        if journal:
            journal.write(kind='exploration_episode_result', **{k:v for k,v in row.items() if k != 'episode'})
        if progress:
            progress(completed=len(rows), total=len(specs), elapsed_seconds=time.monotonic()-started,
                     last={k:v for k,v in row.items() if k != 'episode'})
    return {'schema': 'echo5.exploration-pilot.v1', 'config': config, 'rows': rows,
            'summary': summarize(rows, config)}


def audit_benchmark(report, *, progress=None):
    """Use this in a fresh process; replay native world, actions and decisions."""
    rows, actions, work, validation = [], 0, 0, 0
    config = normalize_config(report['config'])
    expected_specs = {(c['id'], c['spec']['mode']): c for c in case_specs(config)}
    for index, row in enumerate(report['rows']):
        case = expected_specs[(row['id'], row['mode'])]
        payload = row['episode']['receipt']['payload']
        if payload['config'] != case['spec'] or row['profile'] != case['profile']:
            raise ValueError('episode is not from its registered world/arm')
        verified = replay_episode(row['episode'])
        measured = (verified['success'], verified['actions'], verified['work']['used'], payload['status'])
        if measured != (row['success'], row['actions'], row['work'], row['status']):
            raise ValueError('episode summary mismatch')
        actions += verified['actions']
        work += verified['work']['used']
        validation += verified['validation_work']['used']
        rows.append(row)
        if progress:
            progress(completed=index+1, total=len(report['rows']))
    summary = summarize(rows, config)
    if summary != report['summary']:
        raise ValueError('paired aggregate mismatch')
    return {'valid': True, 'episodes_replayed': len(rows), 'replay_actions': actions,
            'replay_work': work, 'receipt_validation_work': validation,
            'summary': summary, 'promotion': False}
