"""Closed serializable Grid->Grid language with bounded named expansion."""
from dataclasses import dataclass
import re

from .budget import Budget
from . import grounding
from .legacy import module

_dsl = module('seed.dsl')
GEOMETRY = ('identity', 'rot90', 'rot180', 'rot270', 'fliplr', 'flipud',
            'transpose', 'crop', 'up2', 'down2', 'tile1x2', 'tile2x1')
SEARCH_GEOMETRY = GEOMETRY[:8]
_FUNCTIONS = {name: getattr(_dsl, name) for name in GEOMETRY if name != 'identity'}
MAX_STEPS = 16
MAX_DEPTH = 8
MAX_NODES = 128
_NAME = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')


@dataclass(frozen=True)
class Step:
    op: str
    role: str | None = None
    relation: str | None = None
    effect: str | None = None
    name: str | None = None
    axis: str | None = None

    def to_dict(self):
        return {key: value for key, value in vars(self).items() if value is not None}


@dataclass(frozen=True)
class Program:
    steps: tuple[Step, ...]

    def to_dict(self):
        return {'steps': [s.to_dict() for s in self.steps]}


def valid_name(name):
    return type(name) is str and _NAME.fullmatch(name) is not None


def parse_program(proposal, *, budget):
    """Reject unknown keys, including claimed verification/authority fields."""
    budget.consume('program_nodes')
    if isinstance(proposal, Program):
        proposal = proposal.to_dict()
    if type(proposal) is not dict or set(proposal) != {'steps'}:
        raise ValueError('program must contain only steps')
    steps = proposal['steps']
    if type(steps) is not list or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError('program needs one to 16 steps')
    parsed = []
    for node in steps:
        budget.consume('program_nodes')
        if type(node) is not dict or type(node.get('op')) is not str:
            raise ValueError('typed instruction required')
        op = node['op']
        if op in GEOMETRY:
            if set(node) != {'op'}:
                raise ValueError('geometry takes no parameters')
        elif op == 'relate':
            if set(node) != {'op', 'role', 'relation', 'effect'}:
                raise ValueError('relate requires exactly role, relation, effect')
            if (node['role'] not in grounding.ROLES or node['relation'] not in grounding.ALL_RELATIONS
                    or node['effect'] not in grounding.EFFECTS):
                raise ValueError('unknown grounded operation')
            if node['effect'] == 'extract' and node['relation'] != 'all':
                raise ValueError('extract requires relation all')
        elif op == 'object':
            if (set(node) != {'op', 'role', 'effect'} or node['role'] not in grounding.ROLES
                    or node['effect'] not in grounding.OBJECT_EFFECTS):
                raise ValueError('object requires exactly a known role and effect')
        elif op == 'pack':
            if set(node) != {'op', 'axis'} or node['axis'] not in grounding.PACK_AXES:
                raise ValueError('pack requires exactly a known axis')
        elif op == 'call':
            if set(node) != {'op', 'name'} or not valid_name(node['name']):
                raise ValueError('call requires a bounded concept name')
        else:
            raise ValueError('unknown operation')
        parsed.append(Step(**node))
    return Program(tuple(parsed))


def expand(proposal, *, library=None, budget):
    """Charge every visited node; reject cycles, missing names and expansion bombs."""
    output = []
    visited = 0
    def visit(program, stack):
        nonlocal visited
        if len(stack) > MAX_DEPTH:
            raise ValueError('concept nesting limit')
        parsed = parse_program(program, budget=budget)
        for step in parsed.steps:
            budget.consume('expansion_nodes')
            visited += 1
            if visited > MAX_NODES:
                raise ValueError('expansion node limit')
            if step.op == 'call':
                budget.consume('concept_lookups')
                if step.name in stack:
                    raise ValueError('cyclic concept expansion')
                if library is None:
                    raise ValueError('concept library required')
                visit(library.resolve(step.name, budget=budget), (*stack, step.name))
            else:
                output.append(step)
                if len(output) > MAX_STEPS:
                    raise ValueError('expanded step limit')
    visit(proposal, ())
    return tuple(output)


def apply_step(step, rows, *, budget, analysis=None):
    """Execute a validated primitive, optionally reusing per-solve analysis."""
    budget.consume('execution_steps')
    if analysis is not None:
        analysis._check_budget(budget)
    if not isinstance(step, Step):
        raise ValueError('typed Step required')
    if step.op == 'relate':
        return grounding.apply_relation(rows, role=step.role, relation=step.relation,
                                        effect=step.effect, budget=budget, analysis=analysis)
    if step.op == 'object':
        return grounding.transform_object(rows, role=step.role, effect=step.effect,
                                          budget=budget, analysis=analysis)
    if step.op == 'pack':
        return grounding.pack_objects(rows, axis=step.axis, budget=budget, analysis=analysis)
    if step.op not in GEOMETRY:
        raise ValueError('expanded primitive required')
    # Reserve output work before geometry, including an overlarge failed result.
    area = len(rows) * len(rows[0])
    factor = 4 if step.op == 'up2' else 2 if step.op in ('tile1x2', 'tile2x1') else 1
    budget.consume('geometry_cells', area * factor)
    return rows if step.op == 'identity' else _FUNCTIONS[step.op](rows)


def execute(proposal, rows, *, budget=None, library=None):
    """Public per-program API. Returns an immutable grid; errors are ValueError."""
    budget = Budget(500_000) if budget is None else budget
    steps = expand(proposal, library=library, budget=budget)
    result = grounding.grid(rows, budget)
    for step in steps:
        result = apply_step(step, result, budget=budget)
    return result


def candidate_atoms(*, relational=True):
    """Yield detached JSON programs; V3 control retains only V3 roles/relations."""
    for op in SEARCH_GEOMETRY:
        yield {'steps': [{'op': op}]}
    roles = grounding.ROLES if relational else grounding.BASE_ROLES
    relations = grounding.RELATIONS if relational else grounding.BASE_RELATIONS
    for role in roles:
        yield {'steps': [{'op': 'relate', 'role': role, 'relation': 'all', 'effect': 'extract'}]}
        for relation in relations:
            for effect in ('recolor', 'erase', 'stamp'):
                yield {'steps': [{'op': 'relate', 'role': role, 'relation': relation, 'effect': effect}]}


def synthesis_atoms(grammar=None, *, relational=True):
    """Explicit opt-in alphabet for deeper synthesis; never inferred from labels.

    Restrictions are part of the public search contract, not generator hints.
    Empty lists disable a category. The historical candidate_atoms API is intact.
    """
    domains = {'geometry': GEOMETRY, 'roles': grounding.ROLES,
               'relations': grounding.ALL_RELATIONS, 'effects': grounding.EFFECTS,
               'object_effects': grounding.OBJECT_EFFECTS, 'pack_axes': grounding.PACK_AXES}
    if grammar is not None and (type(grammar) is not dict or set(grammar) - set(domains)):
        raise ValueError('unknown synthesis grammar keys')
    chosen = {}
    for key, domain in domains.items():
        values = domain if grammar is None else grammar.get(key, ())
        if (type(values) not in (list, tuple) or len(values) > len(domain)
                or any(type(v) is not str or v not in domain for v in values)
                or len(values) != len(set(values))):
            raise ValueError('invalid synthesis grammar category: ' + key)
        chosen[key] = values
    for op in chosen['geometry']:
        yield {'steps': [{'op': op}]}
    for role in chosen['roles']:
        if not relational and role not in grounding.BASE_ROLES:
            continue
        for relation in chosen['relations']:
            if not relational and relation not in grounding.BASE_RELATIONS:
                continue
            for effect in chosen['effects']:
                if effect != 'extract' or relation == 'all':
                    yield {'steps': [{'op': 'relate', 'role': role, 'relation': relation, 'effect': effect}]}
        if relational:
            for effect in chosen['object_effects']:
                yield {'steps': [{'op': 'object', 'role': role, 'effect': effect}]}
    if relational:
        for axis in chosen['pack_axes']:
            yield {'steps': [{'op': 'pack', 'axis': axis}]}
