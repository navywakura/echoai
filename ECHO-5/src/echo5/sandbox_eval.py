"""Evaluator-owned native MiniGrid/BabyAI environments, paired trials and replay.

Only this module constructs environments or handles seeds/rewards/verifiers.
There is no toy fallback. Nothing starts at import, including holdout episodes.
"""

from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time

from .budget import Budget
from .interaction import _canonical, _integer, _keys, _unseal
from .sandbox import (ACTIONS, COLORS, MODES, EXPLORATION_OPTIONS, PINS, Session, UnsupportedMission,
                      dependency_status, parse_mission, sanitize_observation)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / 'config' / 'sandbox.json'
SCENARIOS = {
    'door_key': {'name': 'Key, locked door and goal',
                 'environment': 'MiniGrid-DoorKey-8x8-v0'},
    'objects': {'name': 'Find a described object among distractors',
                'environment': 'BabyAI-GoToLocal-v0',
                'options': {'room_size': 7, 'num_dists': 5}},
    'unlock_pickup': {'name': 'Unlock, enter and pick up the mission object',
                      'environment': 'BabyAI-UnlockPickupDist-v0'},
    'blocked_door': {'name': 'Relocate a blocker, unlock and retrieve an object',
                     'environment': 'MiniGrid-BlockedUnlockPickup-v0'},
    'dynamic': {'name': 'Reach the goal among moving obstacles',
                'environment': 'MiniGrid-Dynamic-Obstacles-8x8-v0',
                'options': {'n_obstacles': 3}},
    'ambiguous_objects': {'name': 'Disambiguate object type, color and initial location',
                          'environment': 'BabyAI-PickupLoc-v0',
                          'options': {'room_size': 8}},
    'ordered_doors': {'name': 'Open two doors in mission order',
                      'environment': 'BabyAI-OpenTwoDoors-v0'},
    'put_next': {'name': 'Put a described object next to another',
                 'environment': 'BabyAI-PutNextLocal-v0',
                 'options': {'room_size': 7, 'num_objs': 5}},
}
ENV_OPTIONS = {
    'MiniGrid-DoorKey-6x6-v0': (), 'MiniGrid-DoorKey-8x8-v0': (),
    'MiniGrid-BlockedUnlockPickup-v0': (),
    'MiniGrid-Dynamic-Obstacles-8x8-v0': ('n_obstacles',),
    'BabyAI-GoToLocal-v0': ('room_size', 'num_dists'),
    'BabyAI-UnlockPickup-v0': (), 'BabyAI-UnlockPickupDist-v0': (),
    'BabyAI-PickupLoc-v0': ('room_size',),
    'BabyAI-OpenTwoDoors-v0': ('first_color', 'second_color', 'strict'),
    'BabyAI-PutNextLocal-v0': ('room_size', 'num_objs'),
}


def normalize_spec(spec):
    """Validate a UI/evaluator request before loading packages or creating worlds."""
    allowed = {'scenario', 'environment', 'seed', 'mode', 'budget',
               'environment_options', 'mission'}
    if type(spec) is not dict or set(spec) - allowed:
        raise ValueError('Unknown Session fields; see SANDBOX.md')
    scenario = spec.get('scenario', 'door_key')
    if type(scenario) is not str or scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    row = SCENARIOS[scenario]
    environment = spec.get('environment', row['environment'])
    if type(environment) is not str or environment not in ENV_OPTIONS:
        raise ValueError('Environment is outside the native allowlist')
    seed = _integer(spec.get('seed', 101), 0, 2**32 - 1, 'seed')
    mode = spec.get('mode', 'informative')
    if mode not in MODES + EXPLORATION_OPTIONS:
        raise ValueError('Unknown mode')
    budget = spec.get('budget', {'actions': 192, 'work': 200000})
    if type(budget) is int:
        budget = {'actions': 192, 'work': budget}
    _keys(budget, ('actions', 'work'), 'sandbox budget')
    budget = {'actions': _integer(budget['actions'], 1, 1024, 'actions'),
              'work': _integer(budget['work'], 1, 100_000_000, 'work')}
    defaults = row.get('options', {}) if environment == row['environment'] else {}
    options = deepcopy(spec.get('environment_options', defaults))
    if type(options) is not dict or set(options) - set(ENV_OPTIONS[environment]) - {'agent_view_size'}:
        raise ValueError('Unsupported native environment options')
    bounds = {'room_size': (5, 10), 'num_dists': (1, 12), 'num_objs': (2, 10),
              'n_obstacles': (1, 5), 'agent_view_size': (3, 9)}
    for key, value in options.items():
        if key in bounds:
            _integer(value, *bounds[key], key)
            if key == 'agent_view_size' and value % 2 == 0:
                raise ValueError('agent_view_size must be odd')
        elif key in ('first_color', 'second_color'):
            if value not in COLORS:
                raise ValueError('Unsupported door color')
        elif key == 'strict' and type(value) is not bool:
            raise ValueError('strict must be boolean')
    if options.get('first_color') is not None and options.get('first_color') == options.get('second_color'):
        raise ValueError('Ordered doors require distinct colors')
    mission = spec.get('mission')
    if mission is not None:
        mission = parse_mission(mission)['text']
    return {'scenario': scenario, 'environment': environment, 'seed': seed,
            'mode': mode, 'budget': budget, 'environment_options': options,
            'mission': mission}


def _native_instruction(mission):
    """Create the *external* BabyAI verifier from a bounded public mission."""
    from minigrid.envs.babyai.core import verifier as v

    def desc(value):
        return v.ObjDesc(None if value['type'] == 'object' else value['type'],
                         value['color'], value['location'])

    atoms = []
    for step in mission['steps']:
        if step['verb'] == 'reach':
            raise UnsupportedMission('Reach applies only to native MiniGrid goal tasks')
        target = desc(step['target'])
        if step['verb'] == 'putnext':
            atom = v.PutNextInstr(target, desc(step['reference']))
        else:
            atom = {'goto': v.GoToInstr, 'pickup': v.PickupInstr,
                    'open': v.OpenInstr}[step['verb']](target)
        atoms.append(atom)
    if len(atoms) == 1:
        return atoms[0]
    return (v.AndInstr if mission['order'] == 'all' else v.BeforeInstr)(*atoms)


class ExternalEnvironment:
    """Private native adapter. ObservationActor is never given this object."""

    def __init__(self, spec):
        dependency_status(require=True)
        import gymnasium as gym
        from minigrid.envs.babyai.core import verifier
        # BabyAI reads this variable at import; reject both process and cached state.
        if os.environ.get('BABYAI_DONE_ACTIONS') or verifier.use_done_actions:
            raise RuntimeError('BABYAI_DONE_ACTIONS changes the pinned rule contract')
        self.spec = deepcopy(spec)
        self.env = None
        self.wall_seconds = 0.0
        self.finished = False
        self._outcome = {'reward': 0.0, 'terminated': False, 'truncated': False}
        started = time.perf_counter()
        try:
            self.env = gym.make(spec['environment'], render_mode=None,
                                disable_env_checker=True,
                                max_steps=spec['budget']['actions'],
                                **spec['environment_options'])
            raw, _info = self.env.reset(seed=spec['seed'])
            mission = spec['mission']
            if mission is not None:
                parsed = parse_mission(mission)
                native_parsed = parse_mission(raw['mission'])
                if parsed['steps'] != native_parsed['steps'] or parsed['order'] != native_parsed['order']:
                    if not spec['environment'].startswith('BabyAI-'):
                        raise UnsupportedMission('MiniGrid mission override must match its native goal')
                    located = any(desc.get('location') for step in parsed['steps']
                                  for desc in (step['target'], step.get('reference', {})))
                    if located and (self.env.unwrapped.num_rows != 1 or self.env.unwrapped.num_cols != 1):
                        raise UnsupportedMission('Operator location missions require a single-room BabyAI environment')
                    # Operator request defines an external BabyAI task. All matching
                    # and verification stay here; no object identities go to actor.
                    instruction = _native_instruction(parsed)
                    instruction.surface(self.env.unwrapped)  # rejects no-match descriptions
                    self.env.unwrapped.validate_instrs(instruction)
                    self.env.unwrapped.instrs = instruction
                    instruction.reset_verifier(self.env.unwrapped)
                self.env.unwrapped.mission = parsed['text']
                raw = self.env.unwrapped.gen_obs()
            self._observation = sanitize_observation(raw)
            self.actions = list(range(self.env.action_space.n))
        except Exception:
            if self.env is not None:
                self.env.close()
            raise
        finally:
            self.wall_seconds += time.perf_counter() - started

    def observation(self):
        return deepcopy(self._observation)

    def step(self, action):
        _integer(action, 0, 6, 'action')
        if self.finished:
            raise RuntimeError('Native episode is already terminal')
        if action not in self.actions:
            raise ValueError('Invalid native action')
        started = time.perf_counter()
        try:
            raw, reward, terminated, truncated, _info = self.env.step(action)
            self._observation = sanitize_observation(raw)
            self._outcome = {'reward': float(reward), 'terminated': bool(terminated),
                             'truncated': bool(truncated)}
            self.finished = bool(terminated or truncated)
            return self.observation()
        finally:
            self.wall_seconds += time.perf_counter() - started

    def outcome(self):
        return deepcopy(self._outcome)

    def adjudicate(self, status):
        outcome = self.outcome()
        # Only the native simulator/verifier, never actor completed-subgoal flags.
        success = outcome['terminated'] and outcome['reward'] > 0
        return {'schema': 'echo5.sandbox.adjudication.v1',
                'adjudicator': 'native_babyai_verifier' if self.spec['environment'].startswith('BabyAI-')
                               else 'native_minigrid_step',
                'success': success, 'environment_outcome': outcome,
                'status': 'success' if success else 'native_failure' if outcome['terminated']
                          else 'timeout' if outcome['truncated'] else status,
                'actor_claim_used': False, 'replay_verified': False}

    def close(self):
        if self.env is not None:
            self.env.close()


def source_manifest():
    """Portable source/dependency identities, not measurements or evidence of success."""
    local = ('src/echo5/sandbox.py', 'src/echo5/sandbox_eval.py',
             'src/echo5/budget.py', 'src/echo5/interaction.py',
             'config/sandbox.json', 'requirements-sandbox.lock')
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in local}
    external = {}
    for name in ('minigrid', 'gymnasium'):
        dist = importlib.metadata.distribution(name)
        hashes = {}
        for entry in sorted(dist.files or (), key=str):
            if str(entry).endswith('.py'):
                hashes[str(entry)] = hashlib.sha256(Path(dist.locate_file(entry)).read_bytes()).hexdigest()
        external[name] = {'version': dist.version,
                          'python_sources_sha256': hashlib.sha256(_canonical(hashes).encode()).hexdigest()}
    return {'files': files, 'external': external, 'pins': dict(PINS), 'python': '3.12.13'}


def replay_episode(result, journal=None):
    """Reexecute native steps and decisions; hashes alone never verify success.

    Accepts the full result from Session.result(). Wall timings are excluded.
    The actor still only receives observations, even during evaluator replay.
    """
    _keys(result, ('receipt', 'timing'), 'episode result')
    validation = Budget(10_000_000)
    payload = _unseal(result['receipt'], validation)
    if payload.get('schema') != 'echo5.sandbox.episode.v1':
        raise ValueError('Unsupported episode receipt')
    if payload.get('sources') != source_manifest():
        raise ValueError('Source/dependency identity changed; replay refused')
    transcript = payload.get('transcript')
    if type(transcript) is not list or len(transcript) > 1024:
        raise ValueError('Invalid transcript')
    with Session(payload['config'], journal=journal) as session:
        if session.snapshot()['observation'] != payload['initial_observation']:
            raise ValueError('Initial observation differs on native replay')
        for row in transcript:
            if type(row.get('manual')) is not bool:
                raise ValueError('Invalid action origin')
            session.step(row['action'] if row['manual'] else None)
        # Work can exhaust during decision before a new external action exists.
        if payload['status'] == 'budget_exhausted' and not session.done:
            session.step()
        if payload['status'] == 'closed':
            session.close()
        replayed = session.result()['receipt']['payload']
        if _canonical(replayed) != _canonical(payload):
            raise ValueError('Native replay/decision/evidence/adjudication mismatch')
        return {'verified': True, 'success': replayed['adjudication']['success'],
                'adjudicator': replayed['adjudication']['adjudicator'],
                'actions': replayed['actions'], 'work': replayed['work'],
                'external_calls': replayed['external_calls'],
                'timing': {'environment_seconds': session._environment.wall_seconds,
                           'policy_seconds': session._policy_seconds},
                'validation_work': validation.snapshot()}


def load_contract():
    return json.loads(CONTRACT_PATH.read_text())


def normalize_config(config):
    allowed = {'split', 'seed', 'cases_per_family', 'budget', 'families', 'modes', 'contract'}
    if type(config) is not dict or set(config) - allowed:
        raise ValueError('Invalid benchmark config fields; see sandbox.json')
    contract = load_contract()
    if config.get('contract', contract['schema']) != contract['schema']:
        raise ValueError('Benchmark contract version mismatch')
    split = config.get('split', 'development')
    if split not in ('development', 'confirmation'):
        raise ValueError('split must be development or confirmation')
    cohort = contract['splits'][split]
    seed = _integer(config.get('seed', cohort['seed_start']),
                    cohort['seed_start'], cohort['seed_end'], 'cohort seed')
    count = _integer(config.get('cases_per_family', 2), 1, 32, 'cases_per_family')
    families = config.get('families', list(cohort['families']))
    if (type(families) is not list or not families or
            any(f not in cohort['families'] for f in families) or len(set(families)) != len(families)):
        raise ValueError('Invalid family selection')
    modes = config.get('modes', list(MODES))
    if (type(modes) is not list or not modes or
            any(m not in MODES for m in modes) or len(set(modes)) != len(modes)):
        raise ValueError('Invalid policy selection')
    budget = normalize_spec({'budget': config.get('budget', contract['budget'])})['budget']
    if seed + (len(families) * count - 1) * 101 > cohort['seed_end']:
        raise ValueError('Generated seeds would leave the requested cohort')
    return {'split': split, 'seed': seed, 'cases_per_family': count,
            'families': list(families), 'modes': list(modes), 'budget': budget,
            'contract': contract['schema']}


def case_specs(config):
    """Pure construction. Does not draw grids, reveal outcomes or run episodes."""
    contract = load_contract()
    cohort = contract['splits'][config['split']]
    cases = []
    for family in config['families']:
        profile = cohort['families'][family]
        for i in range(config['cases_per_family']):
            index = len(cases)
            spec = normalize_spec(dict(profile, seed=config['seed'] + index * 101,
                                       budget=config['budget']))
            cases.append({'case_id': f'sandbox-{config["split"]}-{family}-{i:03d}',
                          'family': family, 'split': config['split'], 'spec': spec})
    return cases


def _summarize(rows, config):
    by_mode = {}
    for mode in config['modes']:
        selected = [r for r in rows if r['condition'] == mode]
        by_mode[mode] = {'cases': len(selected), 'successes': sum(r['success'] for r in selected),
            'actions': sum(r['actions'] for r in selected),
            'work': sum(r['costs']['execution_work']['used'] for r in selected),
            'replay_work': sum(r['costs']['replay_work']['used'] for r in selected),
            'budget_exhaustions': sum(r['result']['receipt']['payload']['status'] == 'budget_exhausted'
                                      for r in selected),
            'by_family': {family: {'cases': sum(r['family'] == family for r in selected),
                                  'successes': sum(r['success'] for r in selected if r['family'] == family)}
                          for family in config['families']}}
    indexed = {(r['case_id'], r['condition']): r for r in rows}
    paired = {}
    for control in config['modes']:
        if control == 'informative' or 'informative' not in config['modes']:
            continue
        wins = losses = ties = cost_wins = cost_losses = 0
        for key, active in indexed.items():
            if key[1] != 'informative':
                continue
            other = indexed[(key[0], control)]
            if active['success'] and not other['success']:
                wins += 1
            elif other['success'] and not active['success']:
                losses += 1
            else:
                ties += 1
                if active['success']:
                    cost_wins += active['costs']['execution_work']['used'] < other['costs']['execution_work']['used']
                    cost_losses += active['costs']['execution_work']['used'] > other['costs']['execution_work']['used']
        paired[control] = {'success_wins': wins, 'success_losses': losses, 'success_ties': ties,
                           'both_success_work_wins': cost_wins, 'both_success_work_losses': cost_losses}
    return {'by_mode': by_mode, 'paired': paired, 'case_count': len({r['case_id'] for r in rows}),
            'row_count': len(rows), 'llm_calls': 0, 'actor_network_calls': 0,
            'scope': 'bounded_native_minigrid_babyai_partial_observation'}


def compute_gates(rows, config, summary=None):
    """Arithmetic only. Does not bless un-replayed receipts or self-reported flags."""
    contract = load_contract()
    summary = _summarize(rows, config) if summary is None else summary
    expected = {(c['case_id'], mode) for c in case_specs(config) for mode in config['modes']}
    actual = {(r['case_id'], r['condition']) for r in rows}
    complete = actual == expected and len(actual) == len(rows)
    verified = bool(rows) and all(r['audit']['verified'] and
        r['success'] == r['audit']['success'] == r['adjudication']['success'] and
        not r['adjudication']['actor_claim_used'] for r in rows)
    equal = bool(rows) and all(r['result']['receipt']['payload']['config']['budget'] == config['budget']
                               for r in rows)
    informative = summary['by_mode'].get('informative', {'cases': 0, 'successes': 0})
    success_gate = (informative['cases'] > 0 and
                    informative['successes'] * 100 >= informative['cases'] *
                    contract['thresholds']['informative_success_percent'])
    by_family = informative.get('by_family', {})
    family_success = bool(config['families']) and all(
        by_family.get(family, {}).get('successes', 0) >=
        contract['thresholds']['minimum_informative_successes_per_family']
        for family in config['families'])
    advantage = {}
    for mode in MODES[1:]:
        paired = summary['paired'].get(mode)
        advantage[mode] = bool(paired and paired['success_wins'] - paired['success_losses'] >=
                              contract['thresholds']['minimum_paired_net_success_wins'])
    coverage = set(config['families']) == set(contract['splits'][config['split']]['families'])
    preregistered = (coverage and config['modes'] == list(MODES) and
                     config['budget'] == contract['budget'] and
                     config['cases_per_family'] >= contract['thresholds']['confirmation_cases_per_family'])
    gates = {'complete_paired_cases': complete, 'external_adjudication_and_replay': verified,
             'equal_action_and_work_limits': equal, 'family_coverage': coverage,
             'informative_success_threshold': success_gate,
             'informative_success_each_family': family_success,
             'informative_advantage': advantage,
             'preregistered_confirmation_config': preregistered,
             'confirmation_split': config['split'] == 'confirmation'}
    gates['closure'] = bool(complete and verified and equal and success_gate and family_success and
                            preregistered and config['split'] == 'confirmation' and all(advantage.values()))
    return gates


def run_benchmark(config, journal=None):
    """Run paired native episodes with fresh actor memory and external replay.

    Instrument errors propagate and are journaled; they are not excluded rows
    or negative agent scores. Caller owns persistence/custody and background work.
    """
    normalized = normalize_config(config)
    # API schema includes the normalized config, not Python objects or hidden handles.
    dependency_status(require=True)
    rows = []
    for case in case_specs(normalized):
        for mode in normalized['modes']:
            spec = dict(case['spec'], mode=mode)
            if journal is not None:
                journal.write(kind='sandbox_case_start', case_id=case['case_id'],
                              split=case['split'], family=case['family'], condition=mode)
            try:
                with Session(spec, journal=journal) as session:
                    while not session.done:
                        session.step()
                    result = session.result()
                audit = replay_episode(result)
            except Exception as exc:
                if journal is not None:
                    journal.write(kind='sandbox_instrument_error', case_id=case['case_id'],
                                  condition=mode, error_type=type(exc).__name__, error=str(exc))
                raise
            payload = result['receipt']['payload']
            verdict = dict(payload['adjudication'], replay_verified=audit['verified'])
            row = {'case_id': case['case_id'], 'split': case['split'], 'family': case['family'],
                   'condition': mode, 'environment': spec['environment'], 'seed': spec['seed'],
                   'success': audit['verified'] and audit['success'],
                   'actions': payload['actions'], 'adjudication': verdict,
                   'costs': {'execution_work': payload['work'], 'replay_work': audit['work'],
                             'replay_validation_work': audit['validation_work'],
                             'external_calls': payload['external_calls'],
                             'replay_external_calls': audit['external_calls'],
                             'execution_timing': result['timing'], 'replay_timing': audit['timing']},
                   'result': result, 'audit': audit}
            rows.append(row)
            if journal is not None:
                journal.write(kind='sandbox_adjudication', case_id=case['case_id'],
                              condition=mode, verdict=verdict, costs=row['costs'])
    summary = _summarize(rows, normalized)
    return {'schema': 'echo5.sandbox.benchmark.v1', 'config': normalized,
            'contract': load_contract(), 'sources': source_manifest(), 'rows': rows,
            'summary': summary, 'gates': compute_gates(rows, normalized, summary)}


def audit_benchmark(report, journal=None):
    """Recompute every external outcome, summary and gate in an independent process."""
    if report.get('schema') != 'echo5.sandbox.benchmark.v1':
        raise ValueError('Unsupported benchmark schema')
    config = normalize_config(report['config'])
    if report['config'] != config:
        raise ValueError('Benchmark configuration is not the recorded normalized configuration')
    if report['contract'] != load_contract() or report['sources'] != source_manifest():
        raise ValueError('Benchmark contract/sources changed')
    rows = deepcopy(report['rows'])
    cases = case_specs(config)
    expected = {(case['case_id'], mode): dict(case['spec'], mode=mode)
                for case in cases for mode in config['modes']}
    case_identity = {case['case_id']: (case['split'], case['family']) for case in cases}
    observed = [(r['case_id'], r['condition']) for r in rows]
    if len(set(observed)) != len(observed) or set(observed) != set(expected):
        raise ValueError('Benchmark case coverage/condition identity mismatch')
    for row in rows:
        payload = row['result']['receipt']['payload']
        expected_spec = expected[(row['case_id'], row['condition'])]
        if (row['split'], row['family']) != case_identity[row['case_id']]:
            raise ValueError('Case split/family was relabelled')
        if payload['config'] != expected_spec or row['seed'] != expected_spec['seed'] or row['environment'] != expected_spec['environment']:
            raise ValueError('Case seed/environment/config was relabelled')
        audit = replay_episode(row['result'], journal=journal)
        if not audit['verified'] or audit['success'] != row['success']:
            raise ValueError('Benchmark outcome disagrees with independent native replay')
        verdict = dict(payload['adjudication'], replay_verified=True)
        if row['adjudication'] != verdict or row['actions'] != payload['actions']:
            raise ValueError('Benchmark verdict/actions were relabelled')
        costs = row['costs']
        for key, actual in (('execution_work', payload['work']), ('replay_work', audit['work']),
                            ('replay_validation_work', audit['validation_work']),
                            ('external_calls', payload['external_calls']),
                            ('replay_external_calls', audit['external_calls'])):
            if costs[key] != actual:
                raise ValueError('Benchmark cost ledger disagrees with replay')
        row['audit'] = audit
    summary = _summarize(rows, config)
    gates = compute_gates(rows, config, summary)
    if summary != report['summary'] or gates != report['gates']:
        raise ValueError('Benchmark summary/gates disagree with recomputation')
    return {'verified': True, 'rows_replayed': len(rows), 'summary': summary, 'gates': gates}
