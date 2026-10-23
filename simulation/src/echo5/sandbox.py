"""Observation-only MiniGrid policy and step API. No experiment at import.

Environment construction, seeds and success adjudication live in sandbox_eval.
JSON snapshots are passive views, not a new cognitive bus or policy input.
"""

from collections import Counter
from copy import deepcopy
import heapq
import importlib.metadata
import platform
import random
import re
import time

from .budget import Budget, BudgetExceeded
from .interaction import _canonical, _integer, _keys, _seal

PINS = {'minigrid': '3.0.0', 'gymnasium': '1.2.0', 'numpy': '2.2.6',
        'pygame': '2.6.1', 'cloudpickle': '3.1.1',
        'Farama-Notifications': '0.0.4', 'typing_extensions': '4.14.1'}
MODES = ('informative', 'fixed', 'passive', 'no_memory', 'no_planning')
# Separate opt-in research controls; historical campaign defaults stay fixed.
EXPLORATION_MODES = ('frontier_information', 'frontier_nearest', 'frontier_random')
EXPLORATION_OPTIONS = EXPLORATION_MODES + ('frontier_hybrid',)
HYBRID_STAGNATION_STEPS = 8
HYBRID_INFORMATION_STEPS = 4
HYBRID_INFORMATION_SELECTIONS = 2
HYBRID_COOLDOWN_STEPS = 8
ACTIONS = ('left', 'right', 'forward', 'pickup', 'drop', 'toggle', 'done')
TYPES = ('unseen', 'empty', 'wall', 'floor', 'door', 'key', 'ball', 'box',
         'goal', 'lava', 'agent')
COLORS = ('red', 'green', 'blue', 'purple', 'yellow', 'grey')
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))
OBS_SCHEMA = 'echo5.sandbox.observation.v1'
SNAPSHOT_SCHEMA = 'echo5.sandbox.snapshot.v1'


class DependencyUnavailable(RuntimeError):
    """The external dependency is absent/mismatched; no synthetic fallback."""


def dependency_status(*, require=False):
    versions, errors = {}, []
    for name, pin in PINS.items():
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
        if versions[name] != pin:
            errors.append(f'{name}: expected {pin}, found {versions[name]}')
    if platform.python_version() != '3.12.13':
        errors.append('CPython 3.12.13 required for reproducible sandbox runs')
    if not errors:
        # No environment is instantiated here.
        import gymnasium  # noqa: F401
        import minigrid  # noqa: F401
    if require and errors:
        raise DependencyUnavailable('; '.join(errors) +
            '; run python3.12 -I scripts/setup_sandbox.py')
    return {'available': not errors, 'versions': versions, 'errors': errors,
            'python': platform.python_version(), 'episodes_executed': 0}


class UnsupportedMission(ValueError):
    pass


def _description(text):
    pattern = (r'(?:the|a) (?:(red|green|blue|purple|yellow|grey) )?'
               r'(ball|box|key|door|object)(?: (on your left|on your right|'
               r'in front of you|behind you))?')
    match = re.fullmatch(pattern, text)
    if not match:
        raise UnsupportedMission(f'Unsupported object description: {text!r}')
    color, kind, location = match.groups()
    return {'type': kind, 'color': color, 'location':
            {None: None, 'on your left': 'left', 'on your right': 'right',
             'in front of you': 'front', 'behind you': 'behind'}[location]}


def parse_mission(value):
    """Bounded grammar, not general language understanding or executable text.

    Dict input accepts {"text": supported_text} or {"order", "steps"}.
    Structured specifications render to the same bounded grammar and verifier.
    """
    if type(value) is dict:
        if set(value) == {'text'}:
            value = value['text']
        else:
            _keys(value, ('order', 'steps'), 'mission specification')
            if value['order'] not in ('single', 'sequence', 'all'):
                raise UnsupportedMission('Unsupported mission order')
            steps = value['steps']
            if type(steps) is not list or not 1 <= len(steps) <= 2:
                raise UnsupportedMission('One or two atomic steps required')
            if (len(steps) == 1) != (value['order'] == 'single'):
                raise UnsupportedMission('Mission order and step count disagree')

            def render(desc):
                _keys(desc, ('type', 'color', 'location'), 'object specification')
                if (desc['type'] not in ('ball', 'box', 'key', 'door', 'object') or
                        desc['color'] not in (*COLORS, None) or
                        desc['location'] not in (None, 'left', 'right', 'front', 'behind')):
                    raise UnsupportedMission('Unsupported object specification')
                location = {None: '', 'left': ' on your left', 'right': ' on your right',
                            'front': ' in front of you', 'behind': ' behind you'}[desc['location']]
                return 'the ' + ((desc['color'] + ' ') if desc['color'] else '') + desc['type'] + location

            parts = []
            for step in steps:
                if type(step) is not dict or step.get('verb') not in ('goto', 'pickup', 'open', 'putnext'):
                    raise UnsupportedMission('Unsupported structured verb')
                _keys(step, ('verb', 'target', 'reference') if step['verb'] == 'putnext'
                      else ('verb', 'target'), 'atomic mission specification')
                if step['verb'] == 'putnext':
                    parts.append('put ' + render(step['target']) + ' next to ' + render(step['reference']))
                else:
                    parts.append({'goto': 'go to ', 'pickup': 'pick up ', 'open': 'open '}[step['verb']]
                                 + render(step['target']))
            value = (' and ' if value['order'] == 'all' else ', then ').join(parts)
    if type(value) is not str or not 1 <= len(value) <= 512:
        raise UnsupportedMission('Mission must be 1..512 characters')
    text = ' '.join(value.lower().strip().rstrip('.').split())
    reach = ('get to the green goal square', 'get to the goal',
             'use the key to open the door and then get to the goal')
    if text in reach:
        return {'schema': 'echo5.sandbox.mission.v1', 'text': text, 'order': 'single',
                'steps': [{'verb': 'reach', 'target':
                          {'type': 'goal', 'color': 'green', 'location': None}}]}
    if ' after you ' in text:
        parts, order = list(reversed(text.split(' after you '))), 'sequence'
    elif ', then ' in text or ' then ' in text:
        parts, order = text.replace(', then ', ' then ').split(' then '), 'sequence'
    elif ' and ' in text:
        parts, order = text.split(' and '), 'all'
    else:
        parts, order = [text], 'single'
    if len(parts) > 2:
        raise UnsupportedMission('At most two atomic instructions are supported')
    steps = []
    for part in parts:
        if part.startswith('put ') and ' next to ' in part:
            move, fixed = part[4:].split(' next to ', 1)
            step = {'verb': 'putnext', 'target': _description(move),
                    'reference': _description(fixed)}
        else:
            match = re.fullmatch(r'(go to|pick up|open) (.+)', part)
            if not match:
                raise UnsupportedMission(f'Unsupported instruction: {part!r}')
            step = {'verb': {'go to': 'goto', 'pick up': 'pickup', 'open': 'open'}
                    [match[1]], 'target': _description(match[2])}
        if step['verb'] == 'open' and step['target']['type'] != 'door':
            raise UnsupportedMission('Only doors can be opened by this grammar')
        if step['verb'] in ('pickup', 'putnext') and step['target']['type'] == 'door':
            raise UnsupportedMission('Doors cannot be picked up')
        steps.append(step)
    return {'schema': 'echo5.sandbox.mission.v1', 'text': text,
            'order': order, 'steps': steps}


def validate_observation(value):
    """Reject extra fields, including seed, dimensions, position, info or labels."""
    _keys(value, ('schema', 'image', 'direction', 'mission'), 'sandbox observation')
    if value['schema'] != OBS_SCHEMA:
        raise ValueError('Unsupported observation schema')
    _integer(value['direction'], 0, 3, 'direction')
    image = value['image']
    if type(image) is not list or len(image) not in (3, 5, 7, 9):
        raise ValueError('image must be a 3/5/7/9 square x-major encoded view')
    for column in image:
        if type(column) is not list or len(column) != len(image):
            raise ValueError('Non-square observation')
        for cell in column:
            if type(cell) is not list or len(cell) != 3:
                raise ValueError('Each encoded cell has type/color/state')
            _integer(cell[0], 0, 10, 'object type')
            _integer(cell[1], 0, 5, 'object color')
            _integer(cell[2], 0, 2, 'object state')
    parse_mission(value['mission'])
    return deepcopy(value)


def sanitize_observation(raw):
    """Copy exactly the native observation; never consult env.unwrapped or info."""
    _keys(raw, ('image', 'direction', 'mission'), 'native MiniGrid observation')
    image = raw['image'].tolist() if hasattr(raw['image'], 'tolist') else raw['image']
    return validate_observation({'schema': OBS_SCHEMA, 'image': image,
                                 'direction': int(raw['direction']),
                                 'mission': raw['mission']})


def decode_cell(cell):
    kind, color, state = cell
    return {'type': TYPES[kind], 'color': None if kind in (0, 1) else COLORS[color],
            'state': ('open', 'closed', 'locked')[state] if kind == 4 else None}


def visible_objects(observation):
    image = observation['image']
    n = len(image)
    return [dict(decode_cell(cell), view_position=[x, y],
                 carrying=(x, y) == (n // 2, n - 1), source='native_partial_image')
            for x, column in enumerate(image) for y, cell in enumerate(column)
            if cell[0] not in (0, 1, 2, 3)]


def _passable(cell):
    return cell is not None and (cell[0] in (1, 3, 8) or
                                (cell[0] == 4 and cell[2] == 0))


def _plus(a, b):
    return a[0] + b[0], a[1] + b[1]


class ObservationActor:
    """Finite mission planner with a map acquired only from partial images.

    This is a symbolic policy, not a trained neural model. Relative coordinates
    start at zero; motor-model odometry remains a labelled hypothesis. Neither
    a simulator handle nor a generation seed is accepted or retained.
    """

    def __init__(self, *, mode='informative'):
        if mode not in MODES + EXPLORATION_OPTIONS:
            raise ValueError('Unknown sandbox mode')
        self.mode = mode
        self.observation = None
        self.mission = None
        self.tick = 0
        self.position = (0, 0)
        self.initial_direction = None
        self.cells = {}
        self.evidence = []
        self.visits = Counter()
        self.completed = set()
        self.carried_from = None
        self.conflicts = 0
        self.replans = 0
        self.motion = {'status': 'origin', 'alternatives': [[0, 0]]}
        self.transitions = Counter()
        self._rng = random.Random(0)  # constant policy seed, never the case seed
        self._frontier_target = None
        self._frontier_trace = None
        self._hybrid_stagnant = 0
        self._hybrid_information_until = 0
        self._hybrid_cooldown_until = 0
        self._hybrid_selections_left = 0
        self._hybrid_started_at = None
        self._last_plan = []
        self.last_learning = None

    @property
    def hand(self):
        image = self.observation['image']
        cell = image[len(image) // 2][-1]
        return cell if cell[0] in (5, 6, 7) else None

    def _project(self, obs, position):
        n = len(obs['image'])
        forward = DIRS[obs['direction']]
        right = (-forward[1], forward[0])
        for x, column in enumerate(obs['image']):
            for y, cell in enumerate(column):
                if not cell[0] or (x, y) == (n // 2, n - 1):
                    continue
                side, ahead = x - n // 2, n - 1 - y
                point = (position[0] + right[0] * side + forward[0] * ahead,
                         position[1] + right[1] * side + forward[1] * ahead)
                yield point, cell, [x, y]

    def _locate(self, before, action, after, budget):
        if action != 2:
            return self.position, {'status': 'action_model',
                                   'alternatives': [list(self.position)]}
        n = len(before['image'])
        front = before['image'][n // 2][n - 2]
        moved = _plus(self.position, DIRS[before['direction']])
        candidates = [self.position, moved]
        scores = []
        old = {p: c for p, c, _ in self._project(before, self.position)}
        for candidate in candidates:
            score, support = 0, 0
            for p, cell, _ in self._project(after, candidate):
                budget.consume('localization_cell')
                other = old.get(p)
                # Only static walls/doors localize; a moving ball is not a landmark.
                if other is not None and (cell[0] in (2, 4) or other[0] in (2, 4)):
                    support += 1
                    score += 1 if cell[:2] == other[:2] else -2
            scores.append((score, support))
        expected = 1 if _passable(front) else 0
        best = max(range(2), key=lambda i: (scores[i][0], i == expected))
        tied = scores[0][0] == scores[1][0]
        return candidates[best], {'status': 'conditional_motor_model' if tied else
            'visual_registration', 'scores': [list(s) for s in scores],
            'alternatives': [list(p) for p in candidates] if tied else
                            [list(candidates[best])],
            'prediction_error': best != expected}

    def observe(self, observation, *, budget, action=None):
        obs = validate_observation(observation)
        n = len(obs['image'])
        budget.consume('observation_validate', n * n)
        before = self.observation
        if before is None:
            if action is not None:
                raise ValueError('Initial observation cannot follow an action')
            self.mission = parse_mission(obs['mission'])
            self.initial_direction = obs['direction']
        else:
            _integer(action, 0, 6, 'previous action')
            if obs['mission'] != before['mission']:
                raise ValueError('Mission changed within an episode')
        position, motion = ((self.position, self.motion) if before is None else
                            self._locate(before, action, obs, budget))
        projected = list(self._project(obs, position))
        # Reserve update work atomically so an exhausted observer stays coherent.
        budget.consume('map_update', len(projected) + 1)
        if self.mode == 'frontier_hybrid':
            budget.consume('hybrid_progress')
            previous_progress = (len(self.cells), len(self.visits), len(self.completed),
                                 self.hand if before is not None else None)
        old_position = self.position
        if before is not None:
            self.tick += 1
        if self.mode == 'no_memory':
            self.cells.clear()
            self.visits.clear()
        self.position, self.motion = position, motion
        changes = []
        for p, cell, view in projected:
            previous = self.cells.get(p)
            if previous is not None and previous['cell'] != cell:
                changes.append({'position': list(p), 'before': previous['cell'],
                                'after': list(cell), 'tick': self.tick})
            self.cells[p] = {'cell': list(cell), 'seen_at': self.tick,
                             'view_position': view, 'source': 'partial_image',
                             'coordinate_status': 'relative_pose_estimate'}
        # The tile beneath the agent is not visible: do not assert an empty cell.
        self.observation = obs
        if before is not None and action == 3 and self.hand is not None:
            previous_hand = before['image'][n // 2][-1]
            if previous_hand[0] not in (5, 6, 7):
                self.carried_from = _plus(position, DIRS[obs['direction']])
        if self.hand is None:
            self.carried_from = None
        self.visits[(position, obs['direction'])] += 1
        if before is not None:
            self.transitions[(action, position != old_position)] += 1
            self._update_subgoals(before, action)
        self.conflicts += len(changes)
        if self.mode == 'frontier_hybrid':
            progress = (len(self.cells), len(self.visits), len(self.completed), self.hand)
            self._hybrid_stagnant = (0 if before is None or changes or progress != previous_progress
                                    else min(HYBRID_STAGNATION_STEPS, self._hybrid_stagnant + 1))
        self.last_learning = {'tick': self.tick, 'observed_cells': len(projected),
            'map_changes': changes, 'motion': deepcopy(motion),
            'subgoals_supported': sorted(self.completed)}
        self.evidence.append(deepcopy(self.last_learning))
        if self.mode == 'no_memory':
            self.evidence = self.evidence[-1:]
        return deepcopy(self.last_learning)

    def _matches(self, cell, desc, point=None):
        if cell is None or cell[0] in (0, 1, 2, 3, 9):
            return False
        if desc['type'] != 'object' and TYPES[cell[0]] != desc['type']:
            return False
        if desc['color'] is not None and COLORS[cell[1]] != desc['color']:
            return False
        if desc['location']:
            if point is None:
                return False  # carrying alone does not prove an initial location
            f = DIRS[self.initial_direction]
            side, ahead = -f[1] * point[0] + f[0] * point[1], f[0] * point[0] + f[1] * point[1]
            return {'left': side < 0, 'right': side > 0,
                    'front': ahead > 0, 'behind': ahead < 0}[desc['location']]
        return True

    def _update_subgoals(self, before, action):
        n = len(before['image'])
        previous_front = before['image'][n // 2][n - 2]
        current_front = self.observation['image'][n // 2][n - 2]
        front_pos = _plus(self.position, DIRS[self.observation['direction']])
        for i, step in enumerate(self.mission['steps']):
            if i in self.completed:
                continue
            if self.mission['order'] == 'sequence' and i and i - 1 not in self.completed:
                break
            verb, desc = step['verb'], step['target']
            supported = False
            if verb == 'pickup' and action == 3:
                supported = (self._matches(previous_front, desc, front_pos) and
                             self.hand == previous_front)
            elif verb == 'open' and action == 5:
                supported = self._matches(current_front, desc, front_pos) and current_front[2] == 0
            elif verb == 'goto':
                supported = self._matches(current_front, desc, front_pos)
            elif verb == 'putnext' and action == 4:
                supported = self._matches(current_front, desc, front_pos) and any(
                    self._matches(self.cells.get(_plus(front_pos, d), {}).get('cell'),
                                  step['reference'], _plus(front_pos, d)) for d in DIRS)
            # Reaching a goal is judged externally; underfoot is not an observation.
            if supported:
                self.completed.add(i)
            if self.mission['order'] == 'sequence':
                break

    def _cell(self, p):
        return self.cells.get(p, {}).get('cell')

    def _paths(self, budget):
        start = (*self.position, self.observation['direction'])
        paths, queue = {start: []}, [(0, start)]
        while queue and len(paths) <= 2048:
            cost, state = heapq.heappop(queue)
            if cost != len(paths[state]):
                continue
            budget.consume('planning_expand')
            x, y, direction = state
            successors = [((x, y, (direction - 1) % 4), [0]),
                          ((x, y, (direction + 1) % 4), [1])]
            p = _plus((x, y), DIRS[direction])
            cell = self._cell(p)
            if _passable(cell) or p == self.position:
                successors.append(((*p, direction), [2]))
            elif cell is not None and cell[0] == 4 and (cell[2] == 1 or
                    (self.hand and self.hand[:2] == [5, cell[1]])):
                successors.append(((*p, direction), [5, 2]))
            for successor, actions in successors:
                budget.consume('planning_edge')
                path = paths[state] + actions
                if successor not in paths or len(path) < len(paths[successor]):
                    paths[successor] = path
                    heapq.heappush(queue, (len(path), successor))
        return paths

    def _route(self, paths, point, verb):
        self._planning_budget.consume('route_match', len(paths))
        candidates = []
        for state, path in paths.items():
            p, direction = state[:2], state[2]
            if verb == 'reach' and p == point:
                candidates.append(path)
            elif verb != 'reach' and _plus(p, DIRS[direction]) == point:
                suffix = {'goto': [], 'pickup': [3], 'open': [5], 'drop': [4]}[verb]
                candidates.append(path + suffix)
        return min(candidates, key=lambda p: (len(p), p)) if candidates else None

    def _drop_route(self, paths, forbidden=()):
        doors = [p for p, v in self.cells.items() if v['cell'][0] == 4]
        candidates = []
        for p, value in self.cells.items():
            if value['cell'][0] != 1 or p in forbidden or p == self.position:
                continue
            if any(abs(p[0] - d[0]) + abs(p[1] - d[1]) <= 1 for d in doors):
                continue
            # Do not replace one blockage with another in a known narrow passage.
            free_neighbors = sum(_passable(self._cell(_plus(p, d))) or
                                 _plus(p, d) == self.position for d in DIRS)
            if free_neighbors < 3:
                continue
            route = self._route(paths, p, 'drop')
            if route:
                candidates.append(route)
        return min(candidates, key=lambda p: (len(p), p)) if candidates else None

    def _goal_plan(self, paths, budget):
        for index, step in enumerate(self.mission['steps']):
            if index in self.completed:
                continue
            matches = []
            for p, value in self.cells.items():
                budget.consume('goal_match')
                if self._matches(value['cell'], step['target'], p):
                    matches.append(p)
            verb = step['verb']
            if verb in ('pickup', 'putnext') and self.hand:
                if verb == 'putnext' and self._matches(self.hand, step['target'], self.carried_from):
                    routes = []
                    for p, value in self.cells.items():
                        budget.consume('relation_match')
                        if self._matches(value['cell'], step['reference'], p):
                            for d in DIRS:
                                drop = _plus(p, d)
                                if self._cell(drop) is not None and self._cell(drop)[0] == 1:
                                    route = self._route(paths, drop, 'drop')
                                    if route:
                                        routes.append(route)
                    if routes:
                        return min(routes, key=lambda r: (len(r), r)), 'satisfy_next_to_relation'
                    return None, None  # keep the target while locating its reference
                # Keep a key until the target has a reachable approach, or no
                # known locked door uses it. This avoids an unlock/drop loop.
                reachable = any(self._route(paths, p, 'goto') is not None for p in matches)
                needed = any(v['cell'][0] == 4 and v['cell'][2] == 2 and
                             self.hand[:2] == [5, v['cell'][1]] for v in self.cells.values())
                if reachable or not needed:
                    drop = self._drop_route(paths, matches)
                    if drop:
                        return drop, 'free_hand_for_goal'
            routes = []
            for p in matches:
                if verb in ('pickup', 'putnext') and self.hand:
                    continue
                if verb == 'open':
                    cell = self._cell(p)
                    if cell[2] == 2 and not (self.hand and self.hand[:2] == [5, cell[1]]):
                        continue
                route = self._route(paths, p, 'pickup' if verb == 'putnext' else verb)
                if route is not None:
                    routes.append(route or [6])  # native verifier still needs a step
            if routes:
                return min(routes, key=lambda r: (len(r), r)), 'mission_target'
            if self.mission['order'] == 'sequence':
                break
        # Relocate a visible blocker before collecting its door's key; otherwise
        # a full hand can cause a repeated key-drop/reacquisition loop.
        for door, value in sorted(self.cells.items()):
            if value['cell'][0] != 4 or value['cell'][2] == 0:
                continue
            if self._route(paths, door, 'goto') is not None:
                continue
            for d in DIRS:
                blocker = _plus(door, d)
                cell = self._cell(blocker)
                if cell is not None and cell[0] in (5, 6, 7):
                    route = self._route(paths, blocker, 'pickup')
                    if route:
                        if self.hand:
                            route = self._drop_route(paths, (blocker,))
                        if route:
                            return route, 'clear_observed_door_blocker'
        # Satisfy a locked-door prerequisite only from observed doors and keys.
        locked = [v['cell'][1] for v in self.cells.values()
                  if v['cell'][0] == 4 and v['cell'][2] == 2]
        routes = []
        if self.hand is None:
            for p, value in self.cells.items():
                if value['cell'][0] == 5 and value['cell'][1] in locked:
                    route = self._route(paths, p, 'pickup')
                    if route:
                        routes.append(route)
        if routes:
            return min(routes, key=lambda r: (len(r), r)), 'observed_key_door_prerequisite'
        # Accessible door toggles can expose a room even before a target is seen.
        for p, value in self.cells.items():
            cell = value['cell']
            if cell[0] == 4 and (cell[2] == 1 or
                    (cell[2] == 2 and self.hand and self.hand[:2] == [5, cell[1]])):
                route = self._route(paths, p, 'open')
                if route:
                    routes.append(route)
        if routes:
            return min(routes, key=lambda r: (len(r), r)), 'open_observed_door'
        return None, None

    def _explore(self, paths, budget):
        if self.mode == 'frontier_hybrid':
            return self._explore_hybrid(paths, budget)
        if self.mode in EXPLORATION_MODES:
            candidates = self._frontier_candidates(paths, budget)
            # Every selector retains its target until reached or invalidated.
            # A random frontier must not abandon its route at every action.
            budget.consume('frontier_commitment_lookup', len(candidates))
            selected = next((c for c in candidates if c[2] == self._frontier_target), None)
            continued = selected is not None
            if selected is None:
                selected = self._select_frontier(candidates, budget)
            self._frontier_target = selected[2] if selected else None
            self._frontier_trace = {'status': 'predicted_not_observed', 'selector': self.mode,
                'candidate_count': len(candidates), 'continued_target': continued,
                'relative_target_pose': list(selected[2]) if selected else None,
                'predicted_unknown_cells': selected[1] if selected else 0}
            return list(selected[0]) if selected else None
        choices = []
        n = len(self.observation['image'])
        for state, path in paths.items():
            if not path:
                continue
            budget.consume('information_candidate')
            x, y, direction = state
            forward = DIRS[direction]
            right = (-forward[1], forward[0])
            unknown = 0
            # A bounded visibility estimate, labelled prediction, not evidence.
            for lateral in (-1, 0, 1):
                for distance in range(1, n):
                    budget.consume('information_ray')
                    p = (x + forward[0] * distance + right[0] * lateral,
                         y + forward[1] * distance + right[1] * lateral)
                    cell = self._cell(p)
                    if cell is None:
                        unknown += 1
                    elif cell[0] == 2 or (cell[0] == 4 and cell[2] != 0):
                        break
            if unknown:
                visits = self.visits[((x, y), direction)]
                score = unknown * 24 // (len(path) + 2) - visits * 12
                if score > 0:
                    choices.append((-score, len(path), state, path))
        return min(choices)[3] if choices else None

    def _unscored_frontier_candidates(self, paths, budget):
        """Exact historical eligibility, stopping at the first unknown cell.

        These charged visibility probes test existence, not information gain.
        Worst case still inspects three view-length rays per unvisited pose;
        neither this enumeration nor the shared path planner is constant-time.
        """
        candidates = []
        n = len(self.observation['image'])
        for state, path in sorted(paths.items()):
            budget.consume('frontier_candidate')
            x, y, direction = state
            if not path or self.visits[((x, y), direction)]:
                continue
            forward, right = DIRS[direction], DIRS[(direction + 1) % 4]
            unknown = False
            for lateral in (-1, 0, 1):
                for distance in range(1, n):
                    budget.consume('frontier_visibility_probe')
                    point = (x + forward[0]*distance + right[0]*lateral,
                             y + forward[1]*distance + right[1]*lateral)
                    cell = self._cell(point)
                    if cell is None:
                        unknown = True
                        break
                    if cell[0] == 2 or (cell[0] == 4 and cell[2] != 0):
                        break
                if unknown:
                    break
            if unknown:
                candidates.append((tuple(path), None, state))
        return candidates

    def _hybrid_trigger(self, budget):
        """Called only after the shared goal/prerequisite planner found no plan.

        Missing targets alone and unrelated doors are not goal blockage. A known
        active requirement without a supported plan is a map-relative signal,
        not proof that the true world is unsolvable (planning is bounded).
        """
        budget.consume('hybrid_gate')
        for index, step in enumerate(self.mission['steps']):
            if index in self.completed:
                continue
            role = ('reference' if step['verb'] == 'putnext' and self.hand and
                    self._matches(self.hand, step['target'], self.carried_from) else 'target')
            positions = []
            for point, value in self.cells.items():
                budget.consume('hybrid_mission_match')
                if self._matches(value['cell'], step[role], point):
                    positions.append(list(point))
            if positions:
                return 'observed_mission_blockage', {
                    'subgoal': index, 'required_role': role, 'positions': sorted(positions),
                    'basis': 'no_plan_on_observed_map'}
            if self.mission['order'] == 'sequence':
                break
        if self._hybrid_stagnant >= HYBRID_STAGNATION_STEPS:
            return 'observation_stagnation', {
                'stagnant_observations': self._hybrid_stagnant,
                'basis': 'no_new_cells_poses_inventory_or_subgoal_support_and_no_cell_changes'}
        return None, None

    def _explore_hybrid(self, paths, budget):
        trigger, evidence = self._hybrid_trigger(budget)
        if trigger is None:
            self._hybrid_selections_left = 0
        elif self.tick >= self._hybrid_cooldown_until:
            self._hybrid_started_at = self.tick
            self._hybrid_information_until = self.tick + HYBRID_INFORMATION_STEPS
            self._hybrid_cooldown_until = self._hybrid_information_until + HYBRID_COOLDOWN_STEPS
            self._hybrid_selections_left = HYBRID_INFORMATION_SELECTIONS
        information = (trigger is not None and self.tick < self._hybrid_information_until and
                       self._hybrid_selections_left > 0)
        # Written before charged work, so an exhausted decision still exports
        # the actual gate via the existing sandbox_stop hypotheses event.
        self._frontier_trace = {'status': 'predicted_not_observed', 'selector': self.mode,
            'phase': 'information' if information else 'nearest', 'trigger': trigger,
            'trigger_evidence': evidence, 'observation_tick': self.tick,
            'information_phase_started_tick': self._hybrid_started_at,
            'information_until_tick': self._hybrid_information_until,
            'cooldown_until_tick': self._hybrid_cooldown_until,
            'information_selections_remaining': self._hybrid_selections_left,
            'information_scoring_attempted': False, 'information_scored': False}
        candidates = self._unscored_frontier_candidates(paths, budget)
        budget.consume('frontier_commitment_lookup', len(candidates))
        selected = next((c for c in candidates if c[2] == self._frontier_target), None)
        continued = selected is not None
        if selected is None and candidates:
            if information:
                self._frontier_trace['information_scoring_attempted'] = True
                candidates = self._frontier_candidates(paths, budget)
                self._frontier_trace['information_scored'] = True
                self._hybrid_selections_left -= 1
            selected = self._select_frontier(candidates, budget, selector=(
                'frontier_information' if information else 'frontier_nearest'))
        self._frontier_target = selected[2] if selected else None
        self._frontier_trace.update(candidate_count=len(candidates), continued_target=continued,
            relative_target_pose=list(selected[2]) if selected else None,
            predicted_unknown_cells=selected[1] if selected else None,
            information_selections_remaining=self._hybrid_selections_left)
        return list(selected[0]) if selected else None

    def _frontier_candidates(self, paths, budget):
        """Same observed-map candidates for all three matched selectors.

        Exclude visited poses rather than using the informative score as an
        eligibility gate. No environment, true position, reward or world seed.
        The visibility estimate and its work are common to every arm.
        """
        candidates = []
        n = len(self.observation['image'])
        for state, path in sorted(paths.items()):
            budget.consume('information_candidate')
            x, y, direction = state
            if not path or self.visits[((x, y), direction)]:
                continue
            forward, right = DIRS[direction], DIRS[(direction + 1) % 4]
            unknown = 0
            for lateral in (-1, 0, 1):
                for distance in range(1, n):
                    budget.consume('information_ray')
                    point = (x + forward[0]*distance + right[0]*lateral,
                             y + forward[1]*distance + right[1]*lateral)
                    cell = self._cell(point)
                    if cell is None:
                        unknown += 1
                    elif cell[0] == 2 or (cell[0] == 4 and cell[2] != 0):
                        break
            if unknown:
                candidates.append((tuple(path), unknown, state))
        return candidates

    def _select_frontier(self, candidates, budget, *, selector=None):
        if not candidates:
            return None
        selector = self.mode if selector is None else selector
        # Linear ranking charge includes every compared alternative. Random
        # selection pays its draw; enumeration has already been paid identically.
        if selector == 'frontier_random':
            budget.consume('frontier_random_draw')
            return candidates[self._rng.randrange(len(candidates))]
        budget.consume('frontier_rank', len(candidates))
        if selector == 'frontier_nearest':
            return min(candidates, key=lambda c: (len(c[0]), c[2]))
        return min(candidates, key=lambda c: (-(c[1]*24//(len(c[0])+2)), len(c[0]), c[2]))

    def _unblock(self, paths):
        if self.hand:
            return self._drop_route(paths)
        candidates = []
        doors = [p for p, v in self.cells.items() if v['cell'][0] == 4]
        for p, value in self.cells.items():
            if value['cell'][0] not in (5, 6, 7):
                continue
            route = self._route(paths, p, 'pickup')
            if route:
                near_door = any(abs(p[0] - d[0]) + abs(p[1] - d[1]) == 1 for d in doors)
                candidates.append((not near_door, len(route), route))
        return min(candidates)[2] if candidates else None

    def choose(self, *, budget):
        if self.observation is None:
            raise RuntimeError('Observe before choosing')
        budget.consume('decision')
        self._frontier_trace = None
        if self.mode == 'fixed':
            action = (2, 2, 0, 2, 1, 3, 5, 4)[self.tick % 8]
            return self._decision([action], 'fixed_sequence')
        if self.mode == 'passive':
            return self._decision([self._rng.randrange(3)], 'passive_seed0_walk')
        if self.mode == 'no_planning':
            # Same observed memory, but only a current-view greedy reaction.
            n = len(self.observation['image'])
            front = self.observation['image'][n // 2][n - 2]
            point = _plus(self.position, DIRS[self.observation['direction']])
            for i, step in enumerate(self.mission['steps']):
                if i not in self.completed and self._matches(front, step['target'], point):
                    action = {'pickup': 3, 'putnext': 3, 'open': 5, 'goto': 6, 'reach': 2}[step['verb']]
                    return self._decision([action], 'local_goal_reaction')
            if front[0] == 4 and front[2] != 0:
                return self._decision([5], 'local_door_reaction')
            if front[0] == 5 and self.hand is None:
                return self._decision([3], 'local_key_reaction')
            return self._decision([2 if _passable(front) and self.tick % 5 else 1], 'local_walk')
        self._planning_budget = budget
        paths = self._paths(budget)
        plan, reason = self._goal_plan(paths, budget)
        if self.mode == 'frontier_hybrid' and plan is not None:
            self._hybrid_selections_left = 0
            self._frontier_trace = {'selector': self.mode, 'phase': 'goal', 'trigger': None,
                'trigger_evidence': None, 'information_scoring_attempted': False,
                'information_scored': False, 'observation_tick': self.tick}
        if plan is None:
            plan, reason = self._explore(paths, budget), 'expected_information_gain'
            if self.mode in EXPLORATION_OPTIONS:
                reason = self.mode
        if plan is None:
            # Goal-only empty rooms with dynamic obstacles cannot pick them up.
            can_unblock = self.mission['steps'][0]['verb'] != 'reach' or any(
                v['cell'][0] == 4 for v in self.cells.values())
            plan = self._unblock(paths) if can_unblock else None
            reason = 'relocate_observed_blocker'
        if not plan:
            plan, reason = [1], 'scan_unobserved_direction'
        self.replans += 1
        return self._decision(plan, reason)

    def _decision(self, plan, reason):
        if self.mode == 'frontier_hybrid' and reason == 'manual_public_action':
            self._frontier_trace = {'selector': self.mode, 'phase': 'manual', 'trigger': None,
                'trigger_evidence': None, 'information_scoring_attempted': False,
                'information_scored': False, 'observation_tick': self.tick}
        self._last_plan = list(plan)
        action = plan[0]
        n = len(self.observation['image'])
        front = self.observation['image'][n // 2][n - 2]
        prediction = {'status': 'hypothesis', 'basis': 'native_action_model_and_observed_cells',
                      'front': decode_cell(front), 'expected':
                      ('advance' if _passable(front) else 'blocked_or_changed') if action == 2
                      else ACTIONS[action], 'not_evidence': True}
        result = {'action': action, 'action_name': ACTIONS[action], 'reason': reason,
                'plan': list(plan), 'prediction': prediction,
                'hypotheses': self.hypotheses()}
        if self.mode in EXPLORATION_OPTIONS:
            result['exploration'] = deepcopy(self._frontier_trace)
        return result

    def hypotheses(self):
        targets = []
        if self.mission:
            for i, step in enumerate(self.mission['steps']):
                positions = [list(p) for p, v in sorted(self.cells.items())
                             if self._matches(v['cell'], step['target'], p)]
                targets.append({'subgoal': i, 'candidate_positions': positions,
                    'status': 'unobserved' if not positions else 'multiple_observed_matches'
                              if len(positions) > 1 else 'observed_description_match',
                    'unseen_alternatives_possible': True})
        result = {'targets': targets, 'pose': deepcopy(self.motion),
                  'plan_status': 'conditional_on_observed_map_and_native_mechanics'}
        if self.mode in EXPLORATION_OPTIONS:
            result['exploration'] = deepcopy(self._frontier_trace)
        return result

    def memory_snapshot(self):
        return {'schema': 'echo5.sandbox.memory.v1', 'kind': 'observation_acquired_map',
            'coordinate_frame': 'episode_origin_relative_xy',
            'agent_position': list(self.position), 'position_status': 'estimate',
            'initial_direction': self.initial_direction,
            'carried_from': None if self.carried_from is None else list(self.carried_from),
            'cells': [dict(v, position=list(p), **decode_cell(v['cell']))
                      for p, v in sorted(self.cells.items())],
            'conflicts': self.conflicts, 'replans': self.replans,
            'supported_subgoals': sorted(self.completed), 'mode': self.mode,
            'transition_counts': [{'action': a, 'moved': moved, 'count': count}
                                  for (a, moved), count in sorted(self.transitions.items())]}


def catalogue():
    """Static UI catalogue; neither import nor this call creates an environment."""
    from .sandbox_eval import SCENARIOS
    return [dict(id=key, name=row['name'], environment=row['environment'],
                 defaults={'scenario': key, 'seed': 101, 'mode': 'informative',
                           'budget': {'actions': 192, 'work': 200000},
                           'environment_options': deepcopy(row.get('options', {}))})
            for key, row in SCENARIOS.items()]


class Session:
    """Synchronous dashboard API; only construction/reset/step advance simulation.

    ``snapshot`` is an idempotent detached JSON view and ``close`` is idempotent.
    A parent may serialize calls with its own lock for pause, SSE and reset.
    The constructor starts one episode. It never starts a background runner.
    """

    def __init__(self, spec, journal=None):
        from .sandbox_eval import normalize_spec
        self._spec = normalize_spec(spec)
        self._journal = journal
        self._environment = None
        self._closed = False
        self.reset()

    def _emit(self, kind, **facts):
        if self._journal is not None:
            self._journal.write(kind=kind, **deepcopy(facts))

    def reset(self):
        from .sandbox_eval import ExternalEnvironment, source_manifest
        if self._closed:
            raise RuntimeError('Session is closed; create a new Session')
        if self._environment is not None:
            self._environment.close()
        self._budget = Budget(self._spec['budget']['work'])
        self._actor = ObservationActor(mode=self._spec['mode'])
        self._transcript = []
        self._decision = None
        self._consequence = None
        self._status = 'running'
        self._policy_seconds = 0.0
        self._budget.consume('environment_reset')
        self._environment = ExternalEnvironment(self._spec)
        self._sources = source_manifest()
        self._observation = self._environment.observation()
        self._initial = deepcopy(self._observation)
        try:
            started = time.perf_counter()
            self._actor.observe(self._observation, budget=self._budget)
            self._policy_seconds += time.perf_counter() - started
        except BudgetExceeded:
            self._status = 'budget_exhausted'
        except Exception:
            self._environment.close()
            raise
        snapshot = self.snapshot()
        self._emit('sandbox_reset', snapshot=snapshot,
                   source='native_minigrid_partial_observation')
        return snapshot

    @property
    def done(self):
        return self._status != 'running' or self._closed

    def step(self, action=None):
        if self._closed:
            raise RuntimeError('Session is closed')
        if self.done:
            raise RuntimeError('Episode is finished; reset before stepping')
        manual = action is not None
        if isinstance(action, str):
            if action not in ACTIONS:
                raise ValueError('Unknown action name')
            action = ACTIONS.index(action)
        if manual:
            _integer(action, 0, 6, 'action')
            if action not in self._environment.actions:
                raise ValueError('Action is unavailable in this native environment')
        before = deepcopy(self._observation)
        self._decision = None
        self._consequence = None
        record = None
        try:
            started = time.perf_counter()
            try:
                if not manual:
                    self._decision = self._actor.choose(budget=self._budget)
                    action = self._decision['action']
                else:
                    self._budget.consume('manual_decision')
                    self._decision = self._actor._decision([action], 'manual_public_action')
            finally:
                self._policy_seconds += time.perf_counter() - started
            # Fixed policy uses the common seven-action alphabet; native dynamic
            # obstacles expose three actions. Match their documented invalid-action
            # fallback explicitly, and preserve the proposed action in the receipt.
            if action not in self._environment.actions:
                proposed = action
                action = 0
                self._decision = self._actor._decision([0], 'native_action_space_fallback')
                self._decision['proposed_action'] = proposed
            self._budget.consume('environment_step')
            after = self._environment.step(action)
            self._observation = after
            record = {'before': before, 'action': action, 'manual': manual,
                      'decision': deepcopy(self._decision), 'after': deepcopy(after),
                      'native_outcome': self._environment.outcome()}
            # Retain the real action even if the ensuing observation update exhausts.
            self._transcript.append(record)
            self._consequence = {'action_executed': ACTIONS[action],
                'observation_changed': before['image'] != after['image'],
                'direction_before': before['direction'], 'direction_after': after['direction'],
                'learning': None, 'source': 'native_step_observation'}
            started = time.perf_counter()
            try:
                learning = self._actor.observe(after, action=action, budget=self._budget)
                record['learning'] = learning
                self._consequence['learning'] = learning
            finally:
                self._policy_seconds += time.perf_counter() - started
            if self._environment.finished:
                self._status = 'environment_finished'
            elif len(self._transcript) >= self._spec['budget']['actions']:
                self._status = 'action_limit'
        except BudgetExceeded:
            self._status = 'budget_exhausted'
            if record is not None:
                record['learning'] = {'status': 'budget_exhausted_after_native_step'}
        except Exception as exc:
            self._status = 'instrument_error'
            self._emit('sandbox_error', step=len(self._transcript),
                       error_type=type(exc).__name__, error=str(exc))
            self._environment.close()
            raise
        snapshot = self.snapshot()
        self._emit('sandbox_step' if record is not None else 'sandbox_stop',
                   step=len(self._transcript), observation=before,
                   objects=visible_objects(before),
                   hypotheses=(self._decision or {}).get('hypotheses', snapshot['hypotheses']),
                   evidence=snapshot['evidence'], prediction=snapshot['prediction'],
                   action=snapshot['action'], consequence=deepcopy(self._consequence),
                   next_observation=deepcopy(self._observation),
                   memory=snapshot['memory'], budget=snapshot['budget'],
                   done=snapshot['done'], status=self._status)
        return snapshot

    def snapshot(self):
        """Actor/public UI fields only. Never call a full-grid renderer here."""
        image = self._observation['image']
        n = len(image)
        decision = self._decision or {}
        return deepcopy({'schema': SNAPSHOT_SCHEMA, 'done': self.done,
            'closed': self._closed, 'status': self._status, 'step': len(self._transcript),
            'mode': self._spec['mode'], 'observation': self._observation,
            'visible_grid': image, 'visible_grid_order': 'x_y_type_color_state',
            'agent_position': {'view': [n // 2, n - 1],
                               'relative': list(self._actor.position),
                               'relative_status': 'estimate',
                               'direction': self._observation['direction']},
            'objects': visible_objects(self._observation),
            'mission': self._actor.mission,
            'hypotheses': self._actor.hypotheses(),
            'evidence': self._actor.last_learning,
            'prediction': decision.get('prediction'),
            'action': None if not decision else
                      {'id': decision['action'], 'name': decision['action_name'],
                       'reason': decision['reason']},
            'consequence': self._consequence,
            'memory': self._actor.memory_snapshot(),
            'budget': {'actions': {'limit': self._spec['budget']['actions'],
                                  'used': len(self._transcript),
                                  'remaining': self._spec['budget']['actions'] - len(self._transcript)},
                       'work': self._budget.snapshot()},
            'actor_receives': ['partial_image', 'direction', 'mission'],
            'adjudication': 'evaluator_only_use_result'})

    def result(self):
        """Evaluator receipt. Do not feed this result back to the actor."""
        from .sandbox_eval import source_manifest
        if source_manifest() != self._sources:
            raise RuntimeError('Sandbox sources changed during this episode')
        receipt = {'schema': 'echo5.sandbox.episode.v1', 'config': deepcopy(self._spec),
            'sources': deepcopy(self._sources), 'initial_observation': deepcopy(self._initial),
            'transcript': deepcopy(self._transcript),
            'final_observation': deepcopy(self._observation),
            'status': self._status, 'done': self.done,
            'work': self._budget.snapshot(), 'actions': len(self._transcript),
            'memory': self._actor.memory_snapshot(),
            'adjudication': self._environment.adjudicate(self._status),
            'external_calls': {'resets': 1, 'steps': len(self._transcript)}}
        return {'receipt': _seal(receipt),
                'timing': {'environment_seconds': self._environment.wall_seconds,
                           'policy_seconds': self._policy_seconds,
                           'unit': 'wall_seconds_not_replay_identity'}}

    def close(self):
        if not self._closed:
            if self._environment is not None:
                self._environment.close()
            if self._status == 'running':
                self._status = 'closed'
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


SandboxSession = Session


def run_benchmark(config, journal=None):
    """Convenience export; evaluator remains in sandbox_eval."""
    from .sandbox_eval import run_benchmark as evaluate
    return evaluate(config, journal=journal)
