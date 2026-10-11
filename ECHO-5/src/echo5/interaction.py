"""Finite interactive hypotheses and backward goal planning; no model calls.

The actor accepts only public observations. DiscreteWorld, case construction
and replay are evaluator facilities and are never handed to the actor.
Importing this module performs no experiment or legacy import.
"""

from collections import Counter, deque
from copy import deepcopy
import hashlib
import json
import random

from .budget import Budget, BudgetExceeded
from .legacy import module


EFFECTS = ((-1, 0), (0, 1), (1, 0), (0, -1), (0, 0))
ARMS = ('passive', 'active', 'no_planning')
SPLITS = ('novel_layout', 'novel_goal', 'changed_dynamics')
ACTION_LIMIT = 64
ACQUISITION_ACTIONS = 16
MAX_EVIDENCE = 4096
PUBLIC_KEYS = frozenset(('schema', 'width', 'height', 'walls', 'position',
                         'goal', 'actions', 'tick'))


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    return value


def _keys(value, expected, name):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'invalid {name} fields')


def _point(value, width, height):
    if type(value) not in (list, tuple) or len(value) != 2:
        raise ValueError('a position must contain two integers')
    return (_integer(value[0], 0, height - 1, 'row'),
            _integer(value[1], 0, width - 1, 'column'))


def validate_observation(value):
    """Validate and copy the complete public schema; unknown fields fail."""
    _keys(value, PUBLIC_KEYS, 'public observation')
    if value['schema'] != 'echo5.interaction.observation.v1':
        raise ValueError('unsupported observation version')
    width = _integer(value['width'], 2, 16, 'width')
    height = _integer(value['height'], 2, 16, 'height')
    _integer(value['tick'], 0, 10**9, 'tick')
    if (type(value['actions']) is not list or
            any(type(a) is not int for a in value['actions']) or
            value['actions'] != [0, 1, 2, 3]):
        raise ValueError('four generic action handles are required')
    walls = value['walls']
    if type(walls) not in (list, tuple) or len(walls) > width * height - 1:
        raise ValueError('invalid walls')
    points = tuple(_point(p, width, height) for p in walls)
    if len(set(points)) != len(points):
        raise ValueError('duplicate walls')
    position = _point(value['position'], width, height)
    goal = _point(value['goal'], width, height)
    if position in points or goal in points:
        raise ValueError('position and goal must be free cells')
    return dict(schema=value['schema'], width=width, height=height,
                walls=[list(p) for p in sorted(points)], position=list(position),
                goal=list(goal), actions=[0, 1, 2, 3], tick=value['tick'])


def _layout(obs):
    return obs['width'], obs['height'], tuple(map(tuple, obs['walls']))


def _advance(position, effect, layout):
    width, height, walls = layout
    nxt = (position[0] + effect[0], position[1] + effect[1])
    if 0 <= nxt[0] < height and 0 <= nxt[1] < width and nxt not in walls:
        return nxt
    return tuple(position)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _seal(payload):
    raw = _canonical(payload)
    return {'payload': json.loads(raw), 'sha256': hashlib.sha256(raw.encode()).hexdigest()}


def _unseal(checkpoint, budget):
    _keys(checkpoint, ('payload', 'sha256'), 'checkpoint')
    budget.consume('checkpoint_validate')
    try:
        raw = _canonical(checkpoint['payload'])
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError('checkpoint is not portable JSON') from exc
    if len(raw) > 8_000_000:
        raise ValueError('checkpoint too large')
    if hashlib.sha256(raw.encode()).hexdigest() != checkpoint['sha256']:
        raise ValueError('checkpoint hash mismatch')
    return json.loads(raw)


def _effects(value):
    if type(value) not in (tuple, list) or len(value) != 4:
        raise ValueError('four effects required')
    result = []
    for effect in value:
        if (type(effect) not in (tuple, list) or len(effect) != 2 or
                any(type(n) is not int for n in effect) or tuple(effect) not in EFFECTS):
            raise ValueError('effect outside the finite world class')
        result.append(tuple(effect))
    return tuple(result)


class DiscreteWorld:
    """Evaluator-owned grid with a private action mapping and optional change.

    ``change_at=N`` changes effects before action N+1. Observations reveal
    neither the mapping nor its change schedule. No introspection sandbox is
    claimed: callers must pass observation dictionaries across the boundary.
    """

    def __init__(self, *, width, height, walls=(), position, goal, effects,
                 change_at=None, changed_effects=None):
        obs = validate_observation(dict(schema='echo5.interaction.observation.v1',
            width=width, height=height, walls=list(walls), position=position,
            goal=goal, actions=[0, 1, 2, 3], tick=0))
        self._initial = obs
        self._current = deepcopy(obs)
        self._effects = _effects(effects)
        if (change_at is None) != (changed_effects is None):
            raise ValueError('a change requires a tick and replacement effects')
        self._change_at = (None if change_at is None else
                           _integer(change_at, 0, MAX_EVIDENCE, 'change_at'))
        self._changed = None if changed_effects is None else _effects(changed_effects)
        self._actions = []

    def observation(self):
        return deepcopy(self._current)

    def step(self, action, *, budget):
        _integer(action, 0, 3, 'action')
        if len(self._actions) >= MAX_EVIDENCE:
            raise ValueError('world history limit reached')
        budget.consume('environment_action')
        effects = self._effects
        if self._change_at is not None and self._current['tick'] >= self._change_at:
            effects = self._changed
        nxt = _advance(self._current['position'], effects[action], _layout(self._current))
        self._current['position'] = list(nxt)
        self._current['tick'] += 1
        self._actions.append(action)
        return self.observation()

    def checkpoint(self):
        return _seal(dict(schema='echo5.interaction.world.v1', initial=self._initial,
            effects=self._effects, change_at=self._change_at, changed_effects=self._changed,
            actions=self._actions, current=self._current))

    @classmethod
    def restore(cls, checkpoint, *, budget):
        payload = _unseal(checkpoint, budget)
        _keys(payload, ('schema', 'initial', 'effects', 'change_at', 'changed_effects',
                        'actions', 'current'), 'world checkpoint')
        if payload['schema'] != 'echo5.interaction.world.v1':
            raise ValueError('unsupported world checkpoint')
        initial = validate_observation(payload['initial'])
        current = validate_observation(payload['current'])
        actions = payload['actions']
        if (initial['tick'] != 0 or type(actions) is not list or
                len(actions) > MAX_EVIDENCE):
            raise ValueError('invalid world history')
        world = cls(width=initial['width'], height=initial['height'],
                    walls=initial['walls'], position=initial['position'], goal=initial['goal'],
                    effects=payload['effects'], change_at=payload['change_at'],
                    changed_effects=payload['changed_effects'])
        for action in actions:
            world.step(action, budget=budget)
        if world.observation() != current:
            raise ValueError('world checkpoint is inconsistent with its history')
        return world


class HypothesisAgent:
    """Factorized finite version spaces; observations are never predictions.

    Each action has five possible effects initially (5**4 joint mappings).
    The existing NEXUS World stores actual transitions in the current layout
    and epoch. It is not allowed to retain a stale majority after a conflict.
    """

    def __init__(self, *, mode='active', seed=0, journal=None):
        if mode not in ARMS:
            raise ValueError('unknown interaction control')
        self.mode = mode
        self.seed = _integer(seed, 0, 2**63 - 1, 'seed')
        self._hypotheses = [EFFECTS for _ in range(4)]
        self._support = [0] * 4
        self._evidence = []
        self._receipts = set()
        self._visits = Counter()
        self._epoch = 0
        self._contradictions = 0
        self._out_of_model = False
        self._cache = None
        self._cache_layout = None
        self._skill = None
        self._journal = journal

    @property
    def hypotheses(self):
        return tuple(self._hypotheses)

    @property
    def evidence(self):
        return deepcopy(self._evidence)

    @property
    def epoch(self):
        return self._epoch

    @property
    def skill(self):
        return deepcopy(self._skill)

    def _emit(self, kind, **facts):
        if self._journal is not None:
            self._journal.write(kind=kind, **deepcopy(facts))

    def _model(self):
        return dict(hypotheses=[[list(e) for e in h] for h in self._hypotheses],
                    support=list(self._support), epoch=self._epoch,
                    contradictions=self._contradictions, out_of_model=self._out_of_model)

    def observe(self, before, action, after, *, budget):
        before, after = validate_observation(before), validate_observation(after)
        _integer(action, 0, 3, 'action')
        if (any(before[k] != after[k] for k in PUBLIC_KEYS - {'position', 'tick'}) or
                after['tick'] != before['tick'] + 1):
            raise ValueError('transition must preserve layout/goal and advance one tick')
        if (self._evidence and before['tick'] != 0 and
                before != self._evidence[-1]['after']):
            raise ValueError('transition does not continue the current episode')
        if len(self._evidence) >= MAX_EVIDENCE:
            raise ValueError('agent evidence limit reached')
        layout, destination = _layout(before), tuple(after['position'])
        # Tick zero may start a new world, but an identical receipt is not
        # independent evidence. Rebuilt from evidence on checkpoint restore.
        receipt = (layout, tuple(before['goal']), tuple(before['position']),
                   before['tick'], action, destination)
        if receipt in self._receipts:
            raise ValueError('duplicate transition receipt in current dynamics epoch')
        surviving = []
        for effect in self._hypotheses[action]:
            budget.consume('hypothesis_filter')
            if _advance(before['position'], effect, layout) == destination:
                surviving.append(effect)
        contradiction = not surviving
        if contradiction:
            for effect in EFFECTS:
                budget.consume('hypothesis_reset_filter')
                if _advance(before['position'], effect, layout) == destination:
                    surviving.append(effect)
        # Reserve all remaining update work before mutating any learned state.
        reset_cache = self._cache is None or layout != self._cache_layout or contradiction
        budget.consume('evidence_update', 2 + int(reset_cache))
        cache = module('nexus0.world').World(n_actions=4) if reset_cache else self._cache
        if contradiction:
            self._epoch += 1
            self._contradictions += 1
            self._hypotheses = [EFFECTS for _ in range(4)]
            self._support = [0] * 4
            self._receipts.clear()
        self._out_of_model = self._out_of_model or not surviving
        self._hypotheses[action] = tuple(surviving)
        self._support[action] += 1
        self._cache, self._cache_layout = cache, layout
        width = before['width']
        cache.observe(before['position'][0] * width + before['position'][1], action,
                      after['position'][0] * width + after['position'][1])
        record = dict(before=before, action=action, after=after)
        self._evidence.append(record)
        self._receipts.add(receipt)
        self._visits[(layout, tuple(before['position']), action)] += 1
        self._skill = None
        outcome = dict(contradiction=contradiction, out_of_model=self._out_of_model,
                       epoch=self._epoch, candidates=[len(h) for h in self._hypotheses])
        self._emit('interaction_transition', **record, evidence=outcome)
        return outcome

    def _probe(self, obs, budget):
        if self.mode == 'passive':
            budget.consume('passive_selection')
            rng = random.Random(self.seed * 1000003 + len(self._evidence) * 9176 + obs['tick'])
            return dict(status='action', action=rng.randrange(4), reason='passive_probe',
                        disagreement=None, epoch=self._epoch)
        layout, position = _layout(obs), tuple(obs['position'])
        ranked = []
        for action, hypotheses in enumerate(self._hypotheses):
            predictions = Counter()
            for effect in hypotheses:
                budget.consume('probe_prediction')
                predictions[_advance(position, effect, layout)] += 1
            budget.consume('probe_score')
            # Ordered disagreeing hypothesis pairs; integers, no entropy estimate.
            disagreement = len(hypotheses)**2 - sum(n*n for n in predictions.values())
            ranked.append((-disagreement, self._visits[(layout, position, action)],
                           self._support[action], action))
        best = min(ranked)
        return dict(status='action', action=best[3], reason='disagreement_probe',
                    disagreement=-best[0], epoch=self._epoch)

    def plan(self, observation, *, budget, max_depth=64, effect_prior=None):
        """Plan from observations or an explicitly labelled nominal effect prior.

        The optional prior is not a transition receipt: it never changes
        hypotheses, support, cache, evidence or checkpoint. Mission adapters
        can reuse this planner without forging acquisition demonstrations.
        """
        obs = validate_observation(observation)
        _integer(max_depth, 0, 256, 'max_depth')
        prior = None if effect_prior is None else _effects(effect_prior)
        hypotheses_by_action = self._hypotheses if prior is None else [(e,) for e in prior]
        self._skill = None
        empty = dict(status='abstain', actions=[], epoch=self._epoch)
        if self.mode == 'no_planning':
            return dict(empty, reason='planning_disabled')
        if self._out_of_model:
            return dict(empty, reason='out_of_model')
        try:
            budget.consume('plan_request')
            layout, start, goal = _layout(obs), tuple(obs['position']), tuple(obs['goal'])
            if start == goal:
                return dict(status='reached', actions=[], epoch=self._epoch)
            incoming = {}
            for row in range(obs['height']):
                for col in range(obs['width']):
                    budget.consume('graph_state')
                    source = (row, col)
                    if source in layout[2]:
                        continue
                    for action, hypotheses in enumerate(hypotheses_by_action):
                        budget.consume('graph_edge')
                        if (prior is None and self._support[action] < 2) or not hypotheses:
                            continue
                        predictions = set()
                        for effect in hypotheses:
                            budget.consume('graph_prediction')
                            predictions.add(_advance(source, effect, layout))
                        if len(predictions) != 1:
                            continue
                        destination = next(iter(predictions))
                        if destination == source:
                            continue
                        provenance = 'inferred' if prior is None else 'declared_prior'
                        if prior is None and self._cache is not None and layout == self._cache_layout:
                            budget.consume('graph_observed_lookup')
                            observed = self._cache.predict(row * obs['width'] + col, action)
                            if observed is not None:
                                if observed != destination[0] * obs['width'] + destination[1]:
                                    return dict(empty, reason='inconsistent_observed_cache')
                                provenance = 'observed'
                        incoming.setdefault(destination, []).append((source, action, provenance))
            # Search backwards from goal: each predecessor is a precondition.
            frontier, visited, successor = deque([(goal, 0)]), {goal}, {}
            while frontier and start not in visited:
                node, depth = frontier.popleft()
                budget.consume('bfs_expand')
                if depth >= max_depth:
                    continue
                for predecessor, action, provenance in incoming.get(node, ()):
                    budget.consume('bfs_edge')
                    if predecessor in visited:
                        continue
                    visited.add(predecessor)
                    successor[predecessor] = (node, action, provenance)
                    frontier.append((predecessor, depth + 1))
            if start not in visited:
                return dict(empty, reason='no_supported_path')
            actions, positions, sources, node = [], [list(start)], [], start
            while node != goal:
                budget.consume('plan_extract')
                node, action, provenance = successor[node]
                actions.append(action)
                positions.append(list(node))
                sources.append(provenance)
            result = dict(status='planned', actions=actions, positions=positions,
                          edge_sources=sources, epoch=self._epoch,
                          certainty=('conditional_on_finite_hypotheses' if prior is None
                                     else 'conditional_on_declared_prior'))
            self._skill = deepcopy(result)
            self._emit('interaction_plan', observation=obs, plan=result)
            return result
        except BudgetExceeded:
            return dict(empty, reason='budget_exhausted')

    def choose(self, observation, *, budget, explore=False):
        obs = validate_observation(observation)
        if type(explore) is not bool:
            raise ValueError('explore must be boolean')
        try:
            budget.consume('decision')
            if self._out_of_model:
                result = dict(status='abstain', action=None, reason='out_of_model', epoch=self._epoch)
            elif not explore and obs['position'] == obs['goal']:
                result = dict(status='reached', action=None, reason='observed_goal', epoch=self._epoch)
            else:
                plan = (self.plan(obs, budget=budget) if not explore and self.mode != 'no_planning'
                        else None)
                if plan and plan['status'] == 'planned':
                    result = dict(status='action', action=plan['actions'][0], reason='learned_plan',
                                  epoch=self._epoch, plan=plan)
                elif plan and plan.get('reason') == 'budget_exhausted':
                    raise BudgetExceeded('planning exhausted the work limit')
                else:
                    result = self._probe(obs, budget)
        except BudgetExceeded:
            result = dict(status='abstain', action=None, reason='budget_exhausted', epoch=self._epoch)
        self._emit('interaction_decision', observation=obs, decision=result,
                   hypotheses=self._model())
        return result

    def checkpoint(self):
        return _seal(dict(schema='echo5.interaction.agent.v1', mode=self.mode, seed=self.seed,
                          evidence=self._evidence, model=self._model()))

    @classmethod
    def restore(cls, checkpoint, *, budget, journal=None):
        payload = _unseal(checkpoint, budget)
        _keys(payload, ('schema', 'mode', 'seed', 'evidence', 'model'), 'agent checkpoint')
        if (payload['schema'] != 'echo5.interaction.agent.v1' or
                type(payload['evidence']) is not list or len(payload['evidence']) > MAX_EVIDENCE):
            raise ValueError('invalid agent checkpoint')
        actor = cls(mode=payload['mode'], seed=payload['seed'])
        for record in payload['evidence']:
            _keys(record, ('before', 'action', 'after'), 'evidence')
            actor.observe(record['before'], record['action'], record['after'], budget=budget)
        if _canonical(actor._model()) != _canonical(payload['model']):
            raise ValueError('learned model disagrees with replayed evidence')
        actor._journal = journal
        actor._emit('interaction_restore', observations=len(actor._evidence), model=actor._model())
        return actor


def run_episode(agent, world, *, budget, action_limit=64, explore=False):
    """Run actual simulation steps, retaining a step even if its update exhausts."""
    _integer(action_limit, 0, ACTION_LIMIT, 'action_limit')
    if type(explore) is not bool:
        raise ValueError('explore must be boolean')
    transcript, status = [], 'action_limit'
    for _ in range(action_limit):
        before = world.observation()
        decision = agent.choose(before, budget=budget, explore=explore)
        if decision['action'] is None:
            status = decision['reason']
            break
        try:
            after = world.step(decision['action'], budget=budget)
        except BudgetExceeded:
            status = 'budget_exhausted'
            break
        row = dict(before=before, action=decision['action'], after=after, decision=decision)
        transcript.append(row)
        agent._emit('interaction_action', before=before, action=decision['action'], after=after)
        try:
            row['learning'] = agent.observe(before, decision['action'], after, budget=budget)
        except BudgetExceeded:
            status = 'budget_exhausted'
            break
        if not explore and after['position'] == after['goal']:
            status = 'observed_goal'
            break
    final = world.observation()
    return dict(status=status, success=final['position'] == final['goal'],
                actions=len(transcript), final=final, transcript=transcript)


def replay_episode(initial_checkpoint, transcript, *, budget):
    """Resimulate every action and compare full observations, ignoring success flags."""
    if type(transcript) is not list or len(transcript) > ACTION_LIMIT:
        raise ValueError('invalid episode transcript')
    world = DiscreteWorld.restore(initial_checkpoint, budget=budget)
    for row in transcript:
        if (type(row) is not dict or not {'before', 'action', 'after'} <= set(row) or
                set(row) - {'before', 'action', 'after', 'decision', 'learning', 'phase'}):
            raise ValueError('invalid transition record')
        before, after = validate_observation(row['before']), validate_observation(row['after'])
        budget.consume('audit_transition')
        if before != world.observation():
            raise ValueError('replay starting observation mismatch')
        if world.step(row['action'], budget=budget) != after:
            raise ValueError('replay transition mismatch')
    final = world.observation()
    return dict(verified=True, success=final['position'] == final['goal'],
                actions=len(transcript), final=final)


def _case_specs(seed, index, split, budget):
    # Charge constructive generation, including every candidate grid cell.
    width, height = (6 + index % 2, 6) if split == 'novel_layout' else (5, 5)
    budget.consume('case_generation', 1 + 25 + width * height + 4)
    rng = random.Random(seed + index * 104729)
    effects = list(EFFECTS[:4])
    rng.shuffle(effects)
    acquisition = dict(width=5, height=5, walls=(), position=(2, 2), goal=(4, 4),
                       effects=effects)
    evaluation = dict(acquisition)
    if split == 'novel_layout':
        gap = 1 + index % (height - 2)
        evaluation.update(width=width, height=height, position=(height - 1, 0),
            walls=tuple((row, 3) for row in range(1, height - 1) if row != gap),
            goal=(0, width - 1))
    elif split == 'novel_goal':
        evaluation['goal'] = ((0, 0), (0, 4), (4, 0))[(index // 3) % 3]
    else:
        evaluation['effects'] = effects[1:] + effects[:1]
    return acquisition, evaluation


def _benchmark_arm(seed, index, split, mode, limit, journal):
    work = Budget(limit)
    costs = dict(generation=0, acquisition=0, evaluation=0, audit=0)
    transcript, audit = [], dict(verified=False, success=False)
    status, actor = 'budget_exhausted', None
    initial_worlds, final_position, goal = {}, None, None
    phase = 'generation'
    start = 0
    try:
        acquisition, evaluation = _case_specs(seed, index, split, work)
        costs[phase] = work.used - start
        phase, start = 'acquisition', work.used
        work.consume('agent_initialize')
        # Policy randomness is independent of the privileged generator seed.
        actor = HypothesisAgent(mode=mode, seed=0, journal=journal)
        learning_world = DiscreteWorld(**acquisition)
        initial_learning = learning_world.checkpoint()
        initial_worlds['acquisition'] = initial_learning
        learned = run_episode(actor, learning_world, budget=work,
                              action_limit=ACQUISITION_ACTIONS, explore=True)
        for row in learned['transcript']:
            row['phase'] = 'acquisition'
        transcript.extend(learned['transcript'])
        costs[phase] = work.used - start
        phase, start = 'evaluation', work.used
        evaluation_world = DiscreteWorld(**evaluation)
        initial_evaluation = evaluation_world.checkpoint()
        initial_worlds['evaluation'] = initial_evaluation
        tested = run_episode(actor, evaluation_world, budget=work,
                             action_limit=ACTION_LIMIT - len(transcript))
        for row in tested['transcript']:
            row['phase'] = 'evaluation'
        transcript.extend(tested['transcript'])
        status = tested['status']
        final_position, goal = tested['final']['position'], tested['final']['goal']
        costs[phase] = work.used - start
        phase, start = 'audit', work.used
        replay_episode(initial_learning, learned['transcript'], budget=work)
        audit = replay_episode(initial_evaluation, tested['transcript'], budget=work)
        costs[phase] = work.used - start
    except BudgetExceeded:
        costs[phase] = work.used - start
        status = 'budget_exhausted'
    return dict(success=audit['verified'] and audit['success'], status=status,
                actions=len(transcript), work=work.snapshot(), costs=costs, audit=audit,
                final_position=final_position, goal=goal, initial_worlds=initial_worlds,
                actions_by_phase={p: sum(r['phase'] == p for r in transcript)
                                  for p in ('acquisition', 'evaluation')}, policy_seed=0,
                transcript=transcript, contradictions=0 if actor is None else actor._contradictions,
                model=None if actor is None else actor._model())


def run_benchmark(seed=30791, cases=24, budget=10000, *, journal=None):
    """Return a deterministic JSON-compatible paired finite-development report.

    ``budget`` is per case per arm, including acquisition and audit. Cases
    cycle over the three preregistered splits; no benchmark runs at import.
    Timing is intentionally separate from deterministic logical work.
    """
    _integer(seed, 0, 2**63 - 1, 'seed')
    _integer(cases, 0, 1000, 'cases')
    _integer(budget, 0, 10**9, 'budget')
    rows = []
    for index in range(cases):
        split = SPLITS[index % 3]
        arms = {mode: _benchmark_arm(seed, index, split, mode, budget, journal) for mode in ARMS}
        rows.append(dict(case_id=f'interaction-{index:04d}', split=split, arms=arms))
    aggregate = {}
    for mode in ARMS:
        outcomes = [row['arms'][mode] for row in rows]
        aggregate[mode] = dict(cases=cases, successes=sum(r['success'] for r in outcomes),
            actions=sum(r['actions'] for r in outcomes), total_work=sum(r['work']['used'] for r in outcomes),
            exhausted=sum(r['status'] == 'budget_exhausted' for r in outcomes),
            by_split={split: dict(cases=sum(row['split'] == split for row in rows),
                successes=sum(row['arms'][mode]['success'] for row in rows if row['split'] == split))
                for split in SPLITS})
    paired = {}
    for baseline in ('passive', 'no_planning'):
        counts = dict(success_wins=0, success_losses=0, success_ties=0,
                      equal_success_cost_wins=0, equal_success_cost_losses=0, equal_success_cost_ties=0)
        for row in rows:
            active, control = row['arms']['active'], row['arms'][baseline]
            if active['success'] != control['success']:
                counts['success_wins' if active['success'] else 'success_losses'] += 1
            else:
                counts['success_ties'] += 1
                delta = active['work']['used'] - control['work']['used']
                counts['equal_success_cost_' + ('wins' if delta < 0 else 'losses' if delta > 0 else 'ties')] += 1
        paired[baseline] = counts
    return dict(schema='echo5.interaction.benchmark.v1', seed=seed,
        config=dict(cases=cases, work_limit_per_case_arm=budget, action_limit=ACTION_LIMIT,
                    acquisition_actions=ACQUISITION_ACTIONS, policy_seed=0,
                    arms=list(ARMS), splits=list(SPLITS)),
        scope='finite_synthetic_cpu_development', cortex_calls=0,
        cases=rows, aggregate=aggregate, paired=paired,
        limitations=['Finite known effect alphabet; no physical validation or generality claim.',
                     'Public full geometry; only action effects are hidden.',
                     'Work units are logical operations, not elapsed time or energy.',
                     'Checkpoint hashes detect corruption, not a malicious evidence source.'])
