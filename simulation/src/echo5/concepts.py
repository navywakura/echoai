"""Demonstration-backed named programs; JSON receipts are evidence, not truth."""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from .budget import Budget
from .grounding import grid
from .programs import Program, execute, expand, parse_program, valid_name

MAX_CONCEPTS = 64
MAX_DEMONSTRATIONS = 10
MAX_STATE_BYTES = 8_000_000


def digest(value, budget=None):
    """Hash canonical bounded JSON, charging traversal, serialization and hashing."""
    def walk(item, depth=0):
        if budget is not None:
            budget.consume('json_nodes')
        if depth > 32:
            raise ValueError('JSON nesting limit')
        if type(item) in (dict, list, tuple):
            if len(item) > 10000:
                raise ValueError('JSON container limit')
            children = item.items() if type(item) is dict else enumerate(item)
            for key, child in children:
                if type(item) is dict:
                    if type(key) is not str:
                        raise ValueError('JSON keys must be strings')
                    walk(key, depth + 1)
                walk(child, depth + 1)
        elif type(item) is str:
            if len(item) > MAX_STATE_BYTES:
                raise ValueError('JSON string limit')
            if budget is not None:
                budget.consume('json_characters', len(item))
        elif item is not None and type(item) not in (int, bool):
            raise ValueError('portable integer JSON required')
    walk(value)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError('state size limit')
    if budget is not None:
        budget.consume('hash_bytes', len(raw))
    return hashlib.sha256(raw).hexdigest()


def _sealed(value, budget=None):
    result = deepcopy(value)
    result['checksum'] = digest(value, budget)
    return result


def _check_checksum(value, budget=None):
    if type(value) is not dict or type(value.get('checksum')) is not str:
        raise ValueError('checksum required')
    body = {k: v for k, v in value.items() if k != 'checksum'}
    if digest(body, budget) != value['checksum']:
        raise ValueError('checksum mismatch')


def _provenance(value):
    if type(value) is not dict or not value.get('source'):
        raise ValueError('provenance source required')
    if set(value) - {'source', 'task_id', 'note'} or any(type(v) is not str or len(v) > 512 for v in value.values()):
        raise ValueError('provenance permits source, task_id and note strings only')
    return dict(value)


def demonstrations(rows, budget, *, minimum=2):
    """Read only demonstration input/output; do not accept whole tasks."""
    budget.consume('demonstration_sets')
    if type(rows) not in (list, tuple) or not minimum <= len(rows) <= MAX_DEMONSTRATIONS:
        raise ValueError('need bounded independent demonstrations')
    found, receipts = {}, []
    for pair in rows:
        inp, out = grid(pair['input'], budget), grid(pair['output'], budget)
        if inp in found and found[inp] != out:
            raise ValueError('contradictory demonstration labels')
        found[inp] = out
        receipts.append(_sealed({'input': [list(r) for r in inp],
                                 'output': [list(r) for r in out]}, budget))
    if len(found) < minimum:
        raise ValueError('distinct demonstration inputs required')
    return receipts


def _matches(program, receipts, library, budget):
    for pair in receipts:
        predicted = execute(program, pair['input'], budget=budget, library=library)
        expected = tuple(tuple(r) for r in pair['output'])
        budget.consume('demonstration_compare_cells', sum(map(len, expected)))
        if predicted != expected:
            raise ValueError('program contradicts demonstration')


@dataclass(frozen=True)
class _VerifiedView:
    """Task-local compiled definitions, created only after replaying support.

    This is a detached execution view, not a persistent verification token.
    A later solve must build a new view and pay for evidence replay again.
    """
    definitions: object
    source_checksum: str

    def active_names(self):
        return tuple(self.definitions)

    def resolve(self, name, *, budget):
        budget.consume('concept_resolutions')
        if not valid_name(name) or name not in self.definitions:
            raise ValueError('unknown compiled concept')
        return self.definitions[name]


class Library:
    """Immutable definitions; only explicit measured challenges quarantine them."""
    def __init__(self):
        self._records = {}

    def active_names(self):
        return tuple(sorted(n for n, r in self._records.items() if r['status'] == 'active'))

    def resolve(self, name, *, budget):
        budget.consume('concept_resolutions')
        if not valid_name(name) or name not in self._records:
            raise ValueError('unknown concept')
        record = self._records[name]
        _check_checksum(record, budget)
        if record['status'] != 'active':
            raise ValueError('quarantined concept')
        for dependency, checksum in record['dependencies'].items():
            budget.consume('dependency_checks')
            other = self._records.get(dependency)
            if other is None or other['status'] != 'active' or other['checksum'] != checksum:
                raise ValueError('stale concept dependency')
        return deepcopy(record['program'])

    def acquire(self, name, program, demonstrations, *, budget, provenance):
        budget.consume('concept_acquisitions')
        if not valid_name(name):
            raise ValueError('invalid concept name')
        if name not in self._records and len(self._records) >= MAX_CONCEPTS:
            raise ValueError('concept capacity reached')
        provenance = _provenance(provenance)
        parsed = parse_program(program, budget=budget)
        # A definition cannot acquire itself through a previously installed name.
        if any(s.op == 'call' and s.name == name for s in parsed.steps):
            raise ValueError('self-referential concept')
        expanded = expand(parsed, library=self, budget=budget)
        receipts = globals()['demonstrations'](demonstrations, budget)
        _matches(parsed, receipts, self, budget)
        if name in self._records:
            if self.resolve(name, budget=budget) != parsed.to_dict():
                raise ValueError('concept names are immutable')
            return deepcopy(self._records[name])
        dependencies = {s.name: self._records[s.name]['checksum'] for s in parsed.steps if s.op == 'call'}
        record = _sealed({'name': name, 'program': parsed.to_dict(),
                          'expanded': Program(expanded).to_dict(), 'dependencies': dependencies,
                          'demonstrations': receipts, 'provenance': provenance,
                          'status': 'active', 'counterexamples': [], 'quarantine_reason': None}, budget)
        self._records[name] = record
        return deepcopy(record)

    def reverify_all(self, *, budget):
        """Replay original support each task. Applicability is checked by solve."""
        names = self.active_names()
        budget.consume('concept_enumeration', len(self._records))
        for name in names:
            record = self._records[name]
            program = self.resolve(name, budget=budget)
            actual = Program(expand(program, library=self, budget=budget)).to_dict()
            if actual != record['expanded']:
                raise ValueError('expanded definition changed')
            receipts = demonstrations(record['demonstrations'], budget)
            _matches(program, receipts, self, budget)
        return len(names)

    def verified_view(self, *, budget):
        """Replay once per task, then compile immutable primitive tuples once.

        Avoid hashing whole evidence records on every candidate call. The
        expanded form was checked against each dependency by reverify_all;
        checksums alone never admit a program into this view.
        """
        self.reverify_all(budget=budget)
        definitions = {}
        for name in self.active_names():
            budget.consume('compiled_concept_copies')
            definitions[name] = parse_program(self._records[name]['expanded'], budget=budget)
        state = self.state(budget=budget)
        return _VerifiedView(MappingProxyType(definitions), state['checksum'])

    def challenge(self, name, demonstrations, *, budget, provenance):
        """Explicit external claim about a concept's scope, never a query label."""
        program = self.resolve(name, budget=budget)
        provenance = _provenance(provenance)
        receipts = globals()['demonstrations'](demonstrations, budget, minimum=1)
        counterexamples = []
        for pair in receipts:
            budget.consume('counterexample_checks')
            try:
                prediction = execute(program, pair['input'], budget=budget, library=self)
                observed = [list(r) for r in prediction]
            except ValueError as exc:
                observed = None
                error = str(exc)
            else:
                error = None
            budget.consume('demonstration_compare_cells', sum(map(len, pair['output'])))
            if observed != pair['output']:
                counterexamples.append(_sealed({'demonstration': pair, 'prediction': observed,
                                                'error': error, 'provenance': provenance}, budget))
        if counterexamples:
            record = deepcopy(self._records[name])
            record.pop('checksum')
            record['counterexamples'].extend(counterexamples)
            record['status'] = 'quarantined'
            record['quarantine_reason'] = 'measured counterexample'
            # Stage the whole invalidation so budget exhaustion cannot half-apply it.
            updates = {name: _sealed(record, budget)}
            changed = True
            while changed:
                changed = False
                for other, entry in self._records.items():
                    budget.consume('dependency_checks')
                    if other not in updates and entry['status'] == 'active' and set(entry['dependencies']) & set(updates):
                        body = {k: deepcopy(v) for k, v in entry.items() if k != 'checksum'}
                        body.update(status='quarantined', quarantine_reason='quarantined dependency')
                        updates[other] = _sealed(body, budget)
                        changed = True
            self._records.update(updates)
        return deepcopy(self._records[name])

    def state(self, *, budget=None):
        if budget is not None:
            budget.consume('library_snapshot_records', len(self._records))
        return _sealed({'schema_version': 1, 'concepts': [deepcopy(self._records[n]) for n in sorted(self._records)]}, budget)

    @classmethod
    def restore(cls, state, *, budget=None):
        budget = Budget(10_000_000) if budget is None else budget
        _check_checksum(state, budget)
        if set(state) != {'schema_version', 'concepts', 'checksum'} or type(state['schema_version']) is not int or state['schema_version'] != 1:
            raise ValueError('unknown library schema')
        records = state['concepts']
        if type(records) is not list or len(records) > MAX_CONCEPTS:
            raise ValueError('invalid concept collection')
        lib = cls()
        keys = {'name', 'program', 'expanded', 'dependencies', 'demonstrations',
                'provenance', 'status', 'counterexamples', 'quarantine_reason', 'checksum'}
        for record in records:
            _check_checksum(record, budget)
            if set(record) != keys or not valid_name(record['name']) or record['name'] in lib._records:
                raise ValueError('invalid or duplicated concept')
            _provenance(record['provenance'])
            parse_program(record['program'], budget=budget)
            parse_program(record['expanded'], budget=budget)
            if record['status'] not in ('active', 'quarantined') or type(record['dependencies']) is not dict or type(record['counterexamples']) is not list:
                raise ValueError('invalid concept status/dependencies')
            receipts = demonstrations(record['demonstrations'], budget)
            if receipts != record['demonstrations']:
                raise ValueError('demonstration checksum mismatch')
            direct = {s.name for s in parse_program(record['program'], budget=budget).steps if s.op == 'call'}
            if direct != set(record['dependencies']):
                raise ValueError('dependency declaration mismatch')
            if record['status'] == 'active' and (record['counterexamples'] or record['quarantine_reason'] is not None):
                raise ValueError('counterexample cannot be marked active')
            lib._records[record['name']] = deepcopy(record)
        lib.reverify_all(budget=budget)
        return lib

    def save(self, path):
        Path(path).write_text(json.dumps(self.state(), sort_keys=True, indent=2) + '\n', encoding='utf-8')

    @classmethod
    def load(cls, path, *, budget=None):
        path = Path(path)
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError('state file size limit')
        return cls.restore(json.loads(path.read_text(encoding='utf-8')), budget=budget)


ConceptLibrary = Library
