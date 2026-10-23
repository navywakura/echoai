"""Fixed, independently authored mission meanings and native verifier witnesses.

No parsing, environment creation, optional imports, writes or agent runs at import.
This is an evaluator diagnostic, not a policy, language parser or closure gate.
"""

from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform

SCHEMA = 'echo5.mission_reference.v1'


def _desc(kind, color=None, location=None):
    return {'type': kind, 'color': color, 'location': location}


def _atom(verb, target, reference=None):
    value = {'verb': verb, 'target': target}
    if reference is not None:
        value['reference'] = reference
    return value


def _world(objects, *, direction=0):
    # All positions, identities and directions are fixture data, never sampled.
    return {'size': 7, 'agent_pos': [3, 3], 'agent_dir': direction,
            'objects': [{'id': name, 'type': kind, 'color': color, 'pos': [x, y]}
                        for name, kind, color, x, y in objects]}


def _trace(name, actions, success):
    return {'id': name, 'actions': actions.split(), 'expected_success': success}


def _case(name, mission, order, steps, world, binding, trajectories=(), *,
          native_operator=None, rejection=None):
    # Copy input and meaning separately: even an in-place parser mutation cannot
    # alter the reference through an alias to a structured mission input.
    return {'id': name, 'mission': deepcopy(mission),
            'expected': deepcopy({'order': order, 'steps': steps}),
            'world': deepcopy(world), 'expected_binding': deepcopy(binding),
            'trajectories': deepcopy(list(trajectories)),
            'native_operator': native_operator or order,
            'expected_rejection': rejection}


def reference_cases():
    """Return detached literal reference data; never consult production parsing.

    Helpers only assemble records. Meanings, bindings, actions and expected
    outcomes below are hand-authored. Locations refer to the initial pose.
    """
    doors = _world((('red_door', 'door', 'red', 4, 3),
                    ('blue_door', 'door', 'blue', 3, 2),
                    ('grey_door', 'door', 'grey', 3, 4)))
    objects = _world((('red_ball', 'ball', 'red', 4, 3),
                      ('blue_ball', 'ball', 'blue', 3, 2),
                      ('red_box', 'box', 'red', 3, 4),
                      ('red_key', 'key', 'red', 2, 3)))
    ring = _world((('north_ball', 'ball', 'red', 3, 2),
                   ('south_ball', 'ball', 'red', 3, 4),
                   ('east_ball', 'ball', 'red', 4, 3),
                   ('west_ball', 'ball', 'red', 2, 3)))
    palette = _world((('purple_key', 'key', 'purple', 4, 3),
                      ('grey_ball', 'ball', 'grey', 3, 2),
                      ('yellow_box', 'box', 'yellow', 3, 4),
                      ('green_door', 'door', 'green', 2, 3)))
    putting = _world((('red_ball', 'ball', 'red', 4, 3),
                      ('blue_box', 'box', 'blue', 2, 3),
                      ('red_key', 'key', 'red', 3, 2),
                      ('blue_key', 'key', 'blue', 4, 5)))
    red_open = _atom('open', _desc('door', 'red'))
    blue_open = _atom('open', _desc('door', 'blue'))
    ordered = [
        _trace('red_then_blue', 'toggle left toggle', True),
        _trace('blue_then_red', 'left toggle right toggle', False),
        _trace('only_red', 'toggle', False),
        # Before/After are non-strict. Reopen blue after red to recover.
        _trace('recover_order', 'left toggle right toggle left toggle toggle', True),
    ]
    both = [
        _trace('red_then_blue', 'toggle left toggle', True),
        _trace('blue_then_red', 'left toggle right toggle', True),
        _trace('only_red', 'toggle', False),
        _trace('wrong_door', 'right toggle', False),
    ]
    door_binding = {'target:0': ['red_door'], 'target:1': ['blue_door']}
    put = _atom('putnext', _desc('ball', 'red'), _desc('box', 'blue'))
    put_binding = {'target:0': ['red_ball'], 'reference:0': ['blue_box']}
    put_traces = [
        _trace('move_target', 'pickup right forward right drop', True),
        _trace('diagonal', 'pickup right drop', False),
        _trace('move_reference', 'left left pickup left forward left drop', False),
        _trace('wrong_type', 'left pickup left left forward right drop', False),
        _trace('wrong_reference', 'pickup right forward left drop', False),
        _trace('no_drop', 'pickup right forward right', False),
    ]
    cases = [
        _case('after_doors', 'open the blue door after you open the red door',
              'sequence', [red_open, blue_open], doors, door_binding, ordered,
              native_operator='after'),
        _case('then_doors', 'open the red door, then open the blue door',
              'sequence', [red_open, blue_open], doors, door_binding, ordered),
        _case('then_no_comma', 'open the red door then open the blue door',
              'sequence', [red_open, blue_open], doors, door_binding, ordered),
        _case('and_doors', 'open the red door and open the blue door',
              'all', [red_open, blue_open], doors, door_binding, both),
        _case('open', 'open the red door', 'single', [red_open], doors,
              {'target:0': ['red_door']}, [
                  _trace('open_target', 'toggle', True),
                  _trace('open_wrong', 'left toggle', False),
                  _trace('face_only', 'done', False)]),
        _case('goto', 'go to the red ball', 'single',
              [_atom('goto', _desc('ball', 'red'))], objects,
              {'target:0': ['red_ball']}, [
                  _trace('face_target', 'done', True),
                  _trace('wrong_color', 'left', False),
                  _trace('wrong_type', 'right', False)]),
        _case('pickup', 'pick up the red ball', 'single',
              [_atom('pickup', _desc('ball', 'red'))], objects,
              {'target:0': ['red_ball']}, [
                  _trace('pick_target', 'pickup', True),
                  _trace('face_only', 'done', False),
                  _trace('wrong_color', 'left pickup', False),
                  _trace('wrong_type', 'right pickup', False)]),
        _case('ambiguous_ball', 'pick up a ball', 'single',
              [_atom('pickup', _desc('ball'))], objects,
              {'target:0': ['blue_ball', 'red_ball']}, [
                  _trace('red_match', 'pickup', True),
                  _trace('blue_match', 'left pickup', True),
                  _trace('wrong_type', 'right pickup', False)]),
        _case('wildcard_type', 'pick up a red object', 'single',
              [_atom('pickup', _desc('object', 'red'))], objects,
              {'target:0': ['red_ball', 'red_box', 'red_key']}, [
                  _trace('ball_match', 'pickup', True),
                  _trace('box_match', 'right pickup', True),
                  _trace('key_match', 'left left pickup', True),
                  _trace('wrong_color', 'left pickup', False)]),
        _case('uncolored_key', 'pick up a key', 'single',
              [_atom('pickup', _desc('key'))], objects,
              {'target:0': ['red_key']}, [
                  _trace('key_match', 'left left pickup', True),
                  _trace('wrong_type', 'pickup', False)]),
        _case('purple', 'pick up the purple key', 'single',
              [_atom('pickup', _desc('key', 'purple'))], palette,
              {'target:0': ['purple_key']}, [
                  _trace('match', 'pickup', True), _trace('wrong', 'left pickup', False)]),
        _case('grey', 'pick up the grey ball', 'single',
              [_atom('pickup', _desc('ball', 'grey'))], palette,
              {'target:0': ['grey_ball']}, [
                  _trace('match', 'left pickup', True), _trace('wrong', 'pickup', False)]),
        _case('yellow', 'pick up the yellow box', 'single',
              [_atom('pickup', _desc('box', 'yellow'))], palette,
              {'target:0': ['yellow_box']}, [
                  _trace('match', 'right pickup', True), _trace('wrong', 'pickup', False)]),
        _case('green', 'open the green door', 'single',
              [_atom('open', _desc('door', 'green'))], palette,
              {'target:0': ['green_door']}, [
                  _trace('match', 'left left toggle', True), _trace('wrong', 'toggle', False)]),
        _case('putnext', 'put the red ball next to the blue box', 'single',
              [put], putting, put_binding, put_traces),
        _case('putnext_locations',
              'put the red ball in front of you next to the blue box behind you',
              'single', [_atom('putnext', _desc('ball', 'red', 'front'),
                               _desc('box', 'blue', 'behind'))],
              putting, put_binding, put_traces),
        _case('putnext_multiple_referents', 'put a red object next to a blue object',
              'single', [_atom('putnext', _desc('object', 'red'), _desc('object', 'blue'))],
              putting, {'target:0': ['red_ball', 'red_key'],
                        'reference:0': ['blue_box', 'blue_key']}, [
                  _trace('ball_to_box', 'pickup right forward right drop', True),
                  _trace('key_to_box', 'left pickup left left forward right drop', True),
                  _trace('ball_to_key', 'pickup right forward left drop', True),
                  _trace('diagonal', 'pickup right drop', False),
                  _trace('move_reference', 'left left pickup left forward left drop', False)]),
        _case('missing_referent', 'pick up the purple ball', 'single',
              [_atom('pickup', _desc('ball', 'purple'))], objects, {}, rejection='no_match'),
        _case('putnext_overlap', 'put the red ball next to a red object', 'single',
              [_atom('putnext', _desc('ball', 'red'), _desc('object', 'red'))],
              putting, {}, rejection='overlap'),
        _case('putnext_already_adjacent', 'put the red ball next to the blue box',
              'single', [put], _world((('red_ball', 'ball', 'red', 4, 3),
                                      ('blue_box', 'box', 'blue', 5, 3))), {},
              rejection='already_adjacent'),
    ]
    # These tuples are literal geometric witnesses, not computed from a parser
    # or the native location predicate. Include all four starting directions.
    for name, phrase, location, direction, identity, good, bad in (
        ('left', 'on your left', 'left', 0, 'north_ball', 'right right right pickup', 'right pickup'),
        ('right', 'on your right', 'right', 0, 'south_ball', 'right pickup', 'left pickup'),
        ('front', 'in front of you', 'front', 0, 'east_ball', 'left right pickup', 'left left pickup'),
        ('behind', 'behind you', 'behind', 0, 'west_ball', 'left left pickup', 'pickup'),
        ('left_facing_south', 'on your left', 'left', 1, 'east_ball', 'left pickup', 'right pickup'),
        ('left_facing_west', 'on your left', 'left', 2, 'south_ball', 'left pickup', 'right pickup'),
        ('left_facing_north', 'on your left', 'left', 3, 'west_ball', 'left pickup', 'right pickup'),
    ):
        world = deepcopy(ring)
        world['agent_dir'] = direction
        cases.append(_case(name, 'pick up the red ball ' + phrase, 'single',
                           [_atom('pickup', _desc('ball', 'red', location))], world,
                           {'target:0': [identity]}, [
                               _trace('initial_location', good, True),
                               _trace('other_location', bad, False)]))
    cases.extend([
        _case('normalized_text', '  PICK UP   the red ball.  ', 'single',
              [_atom('pickup', _desc('ball', 'red'))], objects,
              {'target:0': ['red_ball']}, [
                  _trace('match', 'pickup', True), _trace('wrong', 'left pickup', False)]),
        _case('text_mapping', {'text': 'open the red door and open the blue door'},
              'all', [red_open, blue_open], doors, door_binding, both),
        _case('structured_sequence', {'order': 'sequence', 'steps': [red_open, blue_open]},
              'sequence', [red_open, blue_open], doors, door_binding, ordered),
        _case('structured_all', {'order': 'all', 'steps': [red_open, blue_open]},
              'all', [red_open, blue_open], doors, door_binding, both),
        _case('structured_putnext', {'order': 'single', 'steps': [put]},
              'single', [put], putting, put_binding, put_traces),
    ])
    return cases


def rejection_cases():
    """Unsupported/ambiguous syntax; ambiguous object *sets* above are valid."""
    return [
        {'id': name, 'mission': value} for name, value in (
            ('pronoun', 'pick up it'),
            ('other_referent', 'go to the other ball'),
            ('missing_color_name', 'pick up the orange ball'),
            ('bad_location', 'go to the red ball near you'),
            ('open_non_door', 'open the red ball'),
            ('pickup_door', 'pick up the blue door'),
            ('put_door', 'put the red door next to the blue ball'),
            ('mixed_connectives', 'open the red door and open the blue door then pick up a key'),
            ('three_steps', 'open the red door then open the blue door then open the grey door'),
            ('unsupported_before', 'open the red door before you open the blue door'),
            ('dangling_then', 'open the red door then'),
            ('executable_text', '__import__("os").system("echo forbidden")'),
            ('empty', ''), ('too_long', 'x' * 513), ('non_string', None),
            ('extra_field', {'text': 'go to the red ball', 'success': True}),
            ('bad_order', {'order': 'sometimes', 'steps': []}),
            ('no_steps', {'order': 'single', 'steps': []}),
            ('order_count', {'order': 'all', 'steps': [
                _atom('goto', _desc('ball', 'red'))]}),
            ('missing_reference', {'order': 'single', 'steps': [
                _atom('putnext', _desc('ball', 'red'))]}),
        )
    ]


def _native_dependencies():
    # Independent fixture runtime pins, not a source of mission expectations.
    pins = {'minigrid': '3.0.0', 'gymnasium': '1.2.0', 'numpy': '2.2.6',
            'pygame': '2.6.1', 'cloudpickle': '3.1.1',
            'Farama-Notifications': '0.0.4', 'typing_extensions': '4.14.1'}
    versions, errors = {}, []
    for name, pin in pins.items():
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
        if versions[name] != pin:
            errors.append(f'{name}: expected {pin}, found {versions[name]}')
    if platform.python_version() != '3.12.13':
        errors.append('CPython 3.12.13 required for native reference fixtures')
    if not errors:
        try:
            from minigrid.envs.babyai.core import verifier
            if os.environ.get('BABYAI_DONE_ACTIONS') or verifier.use_done_actions:
                errors.append('BABYAI_DONE_ACTIONS changes the reference semantics')
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
    return {'available': not errors, 'versions': versions, 'errors': errors,
            'python': platform.python_version()}


def _reference_instruction(case):
    """Compile ONLY fixed reference data to native verifier objects.

    This function has no path to parse_mission or the production judge builder.
    AfterInstr also exercises the native reverse-order implementation directly.
    """
    from minigrid.envs.babyai.core import verifier as v

    def descriptor(data):
        return v.ObjDesc(None if data['type'] == 'object' else data['type'],
                         color=data['color'], loc=data['location'])

    atoms = []
    for step in case['expected']['steps']:
        target = descriptor(step['target'])
        if step['verb'] == 'goto':
            atom = v.GoToInstr(target)
        elif step['verb'] == 'pickup':
            atom = v.PickupInstr(target)
        elif step['verb'] == 'open':
            atom = v.OpenInstr(target)
        elif step['verb'] == 'putnext':
            atom = v.PutNextInstr(target, descriptor(step['reference']))
        else:
            raise ValueError('Unsupported fixed reference verb')
        atoms.append(atom)
    operator = case['native_operator']
    if operator == 'single':
        return atoms[0]
    if operator == 'after':
        return v.AfterInstr(atoms[1], atoms[0])
    if operator == 'sequence':
        return v.BeforeInstr(atoms[0], atoms[1])
    if operator == 'all':
        return v.AndInstr(atoms[0], atoms[1])
    raise ValueError('Unsupported fixed reference operator')


class _FixtureRejected(Exception):
    pass


def _environment(case, builder):
    """A finite hand-placed native RoomGridLevel, with no rejection-sampling loop."""
    from minigrid.core.roomgrid import RoomGrid
    from minigrid.core.world_object import Ball, Box, Door, Key
    from minigrid.envs.babyai.core.roomgrid_level import RejectSampling, RoomGridLevel

    class FixedLevel(RoomGridLevel):
        def _gen_grid(self, width, height):
            RoomGrid._gen_grid(self, width, height)
            world = case['world']
            self.agent_pos = tuple(world['agent_pos'])
            self.agent_dir = world['agent_dir']
            self.fixture_objects = {}
            for item in world['objects']:
                obj = {'ball': Ball, 'box': Box, 'door': Door, 'key': Key}[
                    item['type']](item['color'])
                self.put_obj(obj, *item['pos'])
                self.get_room(0, 0).objs.append(obj)
                self.fixture_objects[item['id']] = obj
            self.instrs = builder()
            try:
                self.mission = self.instrs.surface(self)
            except AssertionError as exc:
                if str(exc) != 'no object matching description':
                    raise
                raise _FixtureRejected('no_match') from exc
            try:
                self.validate_instrs(self.instrs)
            except RejectSampling as exc:
                reason = str(exc)
                if 'match both lhs and rhs' in reason or 'next to itself' in reason:
                    raise _FixtureRejected('overlap') from exc
                if reason == 'objs already next to each other':
                    raise _FixtureRejected('already_adjacent') from exc
                raise

    return FixedLevel(room_size=case['world']['size'], num_rows=1, num_cols=1,
                      max_steps=64, render_mode=None)


def _binding(env):
    """Record native referent sets using stable fixture IDs, never memory IDs."""
    from minigrid.envs.babyai.core import verifier as v
    instruction = env.instrs
    if isinstance(instruction, v.AfterInstr):
        atoms = (instruction.instr_b, instruction.instr_a)
    elif isinstance(instruction, v.SeqInstr):
        atoms = (instruction.instr_a, instruction.instr_b)
    else:
        atoms = (instruction,)
    result = {}
    for index, atom in enumerate(atoms):
        fields = (('target', 'desc_move'), ('reference', 'desc_fixed')) if isinstance(
            atom, v.PutNextInstr) else (('target', 'desc'),)
        for role, attr in fields:
            matched = getattr(atom, attr).obj_set
            # An unexpected wall/unregistered referent must be visible too.
            names = [name for name, obj in env.fixture_objects.items() if obj in matched]
            if len(names) != len(matched):
                names.append('<non-fixture-object>')
            result[f'{role}:{index}'] = sorted(names)
    return result


def _state(env):
    return {'agent_pos': [int(x) for x in env.agent_pos], 'agent_dir': int(env.agent_dir),
            'carrying': next((name for name, obj in env.fixture_objects.items()
                              if obj is env.carrying), None),
            'objects': {name: {'pos': [int(x) for x in obj.cur_pos],
                               'open': bool(obj.is_open) if obj.type == 'door' else None}
                        for name, obj in env.fixture_objects.items()}}


def _native_trial(case, builder, actions):
    env = _environment(case, builder)
    try:
        try:
            env.reset(seed=0)
        except _FixtureRejected as exc:
            return {'rejection': str(exc), 'binding': {}, 'success': False, 'trace': []}
        result = {'rejection': None, 'binding': _binding(env), 'initial': _state(env),
                  'success': False, 'trace': []}
        for action in actions:
            _obs, reward, terminated, truncated, _info = env.step(getattr(env.actions, action))
            success = bool(terminated and reward > 0)
            result['trace'].append({'action': action, 'reward': float(reward),
                                    'terminated': bool(terminated), 'truncated': bool(truncated),
                                    'success': success, 'state': _state(env)})
            result['success'] = success
            if terminated or truncated:
                break
        return result
    finally:
        env.close()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def _parse_case(case, *, reject=False):
    from . import sandbox
    try:
        parsed = sandbox.parse_mission(deepcopy(case['mission']))
    except ValueError as exc:
        # Includes UnsupportedMission and the structured field validator.
        return {'valid': True, 'passed': reject, 'rejected': True, 'status': 'rejected',
                'error_type': type(exc).__name__, 'error': str(exc)}, None
    except Exception as exc:
        return {'valid': False, 'passed': False, 'rejected': False, 'status': 'error',
                'error_type': type(exc).__name__, 'error': str(exc), 'stage': 'parser'}, None
    try:
        observed = {'order': parsed['order'], 'steps': parsed['steps']}
        json.dumps(observed, allow_nan=False)
    except Exception as exc:
        # A malformed/non-JSON return is a parser error, never a rejection pass.
        return {'valid': False, 'passed': False, 'rejected': False, 'status': 'error',
                'error_type': type(exc).__name__, 'error': str(exc), 'stage': 'parser_output'}, None
    return {'valid': True, 'passed': not reject and observed == case['expected'],
            'rejected': False, 'status': 'accepted', 'observed': observed}, parsed


def run_benchmark(*, native=True):
    """Return a JSON-serializable report; no files, policy runs or sealed tasks.

    ``instrument_valid`` means the complete native reference measurement was usable.
    ``semantic_pass`` additionally requires agreement by the parser and custom judge.
    ``valid`` / ``passed`` are aliases for these two fields. Parser exceptions are
    recorded candidate failures; they do not invalidate a correctly executed oracle.
    Parser-only/missing-dependency reports cannot claim a full valid/pass.
    No timing fields: reports replay exactly across fresh processes on these sources
    and pinned dependencies. The caller owns artifact storage and audit custody.
    """
    if type(native) is not bool:
        raise TypeError('native must be boolean')
    cases, rejections = reference_cases(), rejection_cases()
    counters = dict.fromkeys((
        'parser_cases', 'parser_mismatches', 'rejection_cases', 'rejection_failures',
        'parser_errors', 'native_trajectories', 'native_positive', 'native_negative',
        'native_disagreements', 'native_false_successes', 'native_false_negatives',
        'reference_failures', 'binding_mismatches', 'native_rejections',
        'native_rejection_mismatches', 'candidate_errors', 'instrument_errors',
        'reference_steps', 'candidate_steps'), 0)
    report = {'schema': SCHEMA, 'corpus_sha256': _digest([cases, rejections]),
              'instrument_valid': False, 'semantic_pass': False,
              'valid': False, 'passed': False, 'counters': counters,
              'parser': {'valid': True, 'passed': True},
              'native': {'status': 'not_requested', 'errors': []},
              'cases': [], 'rejections': [],
              'scope': 'fixed public development fixtures; no policy evaluation',
              'limitations': [
                  'Finite grammar examples, not general language understanding.',
                  'Native engine and verifier are shared; mission meanings are independent.',
                  'MiniGrid reach aliases and ExternalEnvironment override plumbing are not exercised.',
                  'Negative trajectories mean no success on that finite prefix, not permanent failure.',
                  'Single-room fixtures; no sealed tasks, random campaign seeds or agent decisions.',
              ]}
    parsed_cases = {}
    for case in cases:
        result, parsed = _parse_case(case)
        counters['parser_cases'] += 1
        counters['parser_mismatches'] += int(not result['passed'])
        counters['parser_errors'] += int(not result['valid'])
        row = {'id': case['id'], 'mission': deepcopy(case['mission']),
               'expected': deepcopy(case['expected']), 'parser': result,
               'expected_rejection': case['expected_rejection'],
               'passed': False, 'trajectories': []}
        report['cases'].append(row)
        parsed_cases[case['id']] = parsed
    for case in rejections:
        result, _ = _parse_case(case, reject=True)
        counters['rejection_cases'] += 1
        counters['rejection_failures'] += int(not result['passed'])
        counters['parser_errors'] += int(not result['valid'])
        report['rejections'].append(dict(case, **result))
    report['parser'] = {
        'valid': counters['parser_errors'] == 0,
        'passed': counters['parser_mismatches'] == counters['rejection_failures'] == 0,
    }
    # Coverage comes from the independent data, including unexecuted checks.
    report['coverage'] = {
        'semantic_cases': len(cases), 'syntax_rejections': len(rejections),
        'native_trajectories_expected': sum(len(c['trajectories']) for c in cases),
        'native_rejections_expected': sum(c['expected_rejection'] is not None for c in cases),
        'verbs': sorted({s['verb'] for c in cases for s in c['expected']['steps']}),
        'orders': sorted({c['expected']['order'] for c in cases}),
        'locations': sorted({d['location'] for c in cases for s in c['expected']['steps']
                             for d in (s['target'], s.get('reference', {})) if d.get('location')}),
        'starting_directions': sorted({c['world']['agent_dir'] for c in cases}),
    }
    if not native:
        return report
    dependencies = _native_dependencies()
    report['native'] = dict(dependencies, status='ready' if dependencies['available'] else 'unavailable')
    if not dependencies['available']:
        return report
    if not cases or not rejections:
        report['native']['status'] = 'invalid'
        report['native']['errors'].append('Empty reference or rejection corpus')
        return report
    ids = [c['id'] for c in cases + rejections]
    if len(ids) != len(set(ids)) or any(
            not c['expected_rejection'] and
            {t['expected_success'] for t in c['trajectories']} != {False, True} for c in cases):
        report['native']['status'] = 'invalid'
        report['native']['errors'].append('Duplicate case IDs or missing positive/negative witnesses')
        return report
    from . import sandbox_eval
    from minigrid.envs.babyai.core import verifier, roomgrid_level
    paths = {'reference': Path(__file__),
             'parser': Path(__file__).with_name('sandbox.py'),
             'custom_judge': Path(sandbox_eval.__file__),
             'native_verifier': Path(verifier.__file__),
             'native_level': Path(roomgrid_level.__file__)}
    report['source_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                               for name, path in paths.items()}
    for case, row in zip(cases, report['cases']):
        parsed = parsed_cases[case['id']]
        reference_builder = lambda case=case: _reference_instruction(case)
        candidate_builder = lambda parsed=parsed: sandbox_eval._native_instruction(deepcopy(parsed))
        row['world'] = deepcopy(case['world'])
        row['expected_binding'] = deepcopy(case['expected_binding'])
        try:
            # Rejections are evaluated once with zero actions. Every trajectory
            # below uses a fresh native environment and fresh verifier state.
            probes = case['trajectories'] or [{'id': 'rejection', 'actions': [],
                                             'expected_success': False}]
            reference_ok, candidate_ok = True, True
            for probe in probes:
                reference = _native_trial(case, reference_builder, probe['actions'])
                expected_rejection = case['expected_rejection']
                ref_ok = (reference['rejection'] == expected_rejection and
                          reference['success'] == probe['expected_success'] and
                          reference['binding'] == case['expected_binding'])
                counters['reference_failures'] += int(not ref_ok)
                reference_ok = reference_ok and ref_ok
                row['reference_binding'] = reference['binding']
                candidate = None
                if parsed is not None:
                    try:
                        candidate = _native_trial(case, candidate_builder, probe['actions'])
                    except (ValueError, KeyError, TypeError, AssertionError) as exc:
                        counters['candidate_errors'] += 1
                        row['candidate_error'] = f'{type(exc).__name__}: {exc}'
                candidate_match = bool(candidate is not None and
                                       candidate['rejection'] == expected_rejection and
                                       candidate['success'] == probe['expected_success'] and
                                       candidate['binding'] == case['expected_binding'])
                candidate_ok = candidate_ok and candidate_match
                if expected_rejection:
                    row['reference_rejection'] = reference['rejection']
                    row['candidate_rejection'] = candidate['rejection'] if candidate else None
                    counters['native_rejections'] += 1
                    counters['native_rejection_mismatches'] += int(not candidate_match)
                else:
                    counters['native_trajectories'] += 1
                    counters['native_positive' if probe['expected_success'] else 'native_negative'] += 1
                    counters['reference_steps'] += len(reference['trace'])
                    counters['candidate_steps'] += len(candidate['trace']) if candidate else 0
                    counters['binding_mismatches'] += int(candidate is not None and
                                                          candidate['binding'] != reference['binding'])
                    disagreement = candidate is None or candidate['success'] != reference['success']
                    counters['native_disagreements'] += int(disagreement)
                    counters['native_false_successes'] += int(candidate is not None and
                                                              candidate['success'] and not reference['success'])
                    counters['native_false_negatives'] += int(candidate is not None and
                                                              not candidate['success'] and reference['success'])
                    row['trajectories'].append(dict(probe, reference=reference, candidate=candidate,
                                                    valid=ref_ok, passed=ref_ok and candidate_match))
            row['passed'] = row['parser']['passed'] and reference_ok and candidate_ok
        except Exception as exc:
            counters['instrument_errors'] += 1
            row['error'] = f'{type(exc).__name__}: {exc}'
            report['native']['errors'].append(f'{case["id"]}: {row["error"]}')
    report['instrument_valid'] = (counters['reference_failures'] == 0 and
                                  counters['instrument_errors'] == 0 and
                                  counters['native_trajectories'] == report['coverage']['native_trajectories_expected'] and
                                  counters['native_rejections'] == report['coverage']['native_rejections_expected'])
    report['semantic_pass'] = report['instrument_valid'] and report['parser']['passed'] and all(
        row['passed'] for row in report['cases'])
    report['valid'], report['passed'] = report['instrument_valid'], report['semantic_pass']
    report['native']['status'] = 'complete' if report['valid'] else 'invalid'
    return report


def main(argv=None):
    """Print the evidence report to stdout; never choose an artifact directory."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parser-only', action='store_true', help='stdlib subset; no full valid/pass')
    args = parser.parse_args(argv)
    report = run_benchmark(native=not args.parser_only)
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 0 if report['passed'] else 1 if report['valid'] else 2


if __name__ == '__main__':
    # Direct execution under -I uses only this explicit ECHO-5 source directory.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'echo5'
    raise SystemExit(main())
