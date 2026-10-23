"""Bounded per-solve memoization and necessary, never sufficient, signatures.

Only validated immutable grids enter this internal cache. Every key construction,
lookup and write is charged. Equal grids share IDs after full tuple equality, not
after hash equality alone. No task identifier, witness or query label is accepted.
"""
from .programs import apply_step
from . import grounding


def palette_preserving(steps):
    """A closed proof whitelist; new operators/effects disable this pruning."""
    geometry = ('identity', 'rot90', 'rot180', 'rot270', 'fliplr', 'flipud',
                'transpose', 'crop', 'up2', 'down2', 'tile1x2', 'tile2x1')
    return all(s.op in geometry or
               s.op == 'relate' and s.effect in ('recolor', 'erase', 'stamp', 'extract') or
               s.op == 'object' and s.effect in ('outline', 'fill_box') or
               s.op == 'pack' and s.axis in ('row', 'column') for s in steps)


class SearchCache:
    def __init__(self, budget, *, max_entries=20000, max_cells=2000000):
        if any(type(v) is not int or v < 0 for v in (max_entries, max_cells)):
            raise ValueError('nonnegative integer cache limits required')
        self.budget = budget
        analysis_cells = min(250000, max_cells//4)
        self.analysis = grounding.AnalysisCache(budget, max_entries=min(4096, max_entries//4),
                                                max_cells=analysis_cells)
        self.max_entries, self.max_cells = max_entries, max_cells-analysis_cells
        self.cells = 0
        self.by_identity, self.grids, self.transitions, self.losses, self.palettes = {}, {}, {}, {}, {}
        self.canonical = []
        self.stats = {'transition_hits': 0, 'loss_hits': 0, 'intern_hits': 0}

    @property
    def total_retained_cells(self):
        return self.cells + self.analysis.retained_cells

    def identifier(self, rows):
        self.budget.consume('memo_identity_lookups')
        key = id(rows)
        known = self.by_identity.get(key)
        if known is not None:
            return known[1]
        area = len(rows)*len(rows[0])
        self.budget.consume('memo_grid_hash_cells', area)
        fingerprint = hash(rows)
        self.budget.consume('memo_grid_lookups')
        ident = None
        for candidate in self.grids.get(fingerprint, ()):
            self.budget.consume('memo_grid_compare_cells', area)
            if self.canonical[candidate] == rows:
                ident = candidate
                break
        if ident is not None:
            self.stats['intern_hits'] += 1
        elif len(self.canonical) < self.max_entries and self.cells+area <= self.max_cells:
            self.budget.consume('memo_grid_writes')
            self.budget.consume('memo_canonical_writes')
            ident = len(self.canonical)
            self.grids.setdefault(fingerprint, []).append(ident)
            self.canonical.append(rows)
            self.cells += area
        if ident is not None and len(self.by_identity) < self.max_entries and self.cells+area <= self.max_cells:
            # Retain each alias too: id reuse must not produce a false cache hit.
            self.budget.consume('memo_identity_writes')
            self.by_identity[key] = (rows, ident)
            self.cells += area
        return ident

    def step(self, step, rows):
        ident = self.identifier(rows)
        if ident is not None:
            self.budget.consume('memo_canonical_reads')
            rows = self.canonical[ident]
        self.budget.consume('transition_key_fields', 7)
        self.budget.consume('transition_lookups')
        key = (ident, step)
        if ident is not None and key in self.transitions:
            self.stats['transition_hits'] += 1
            result = self.transitions[key]
            if isinstance(result, str):
                raise ValueError(result)
            return result
        try:
            result = apply_step(step, rows, budget=self.budget, analysis=self.analysis)
        except ValueError as exc:
            if ident is not None and len(self.transitions) < self.max_entries:
                self.budget.consume('transition_writes')
                self.transitions[key] = str(exc)
            raise
        area = len(result)*len(result[0])
        if ident is not None and len(self.transitions) < self.max_entries and self.cells+area <= self.max_cells:
            # Retain a reference, just as the baseline prefix cache does. No
            # grid copy is performed here; memory retention is capped separately.
            self.budget.consume('transition_writes')
            self.transitions[key] = result
            self.cells += area
        return result

    def loss(self, actual, expected, compute):
        a, b = self.identifier(actual), self.identifier(expected)
        self.budget.consume('loss_cache_lookups')
        key = (a, b)
        if a is not None and b is not None and key in self.losses:
            self.stats['loss_hits'] += 1
            return self.losses[key]
        result = 0 if a is not None and a == b else compute(actual, expected, self.budget)
        if a is not None and b is not None and len(self.losses) < self.max_entries:
            self.budget.consume('loss_cache_writes')
            self.losses[key] = result
        return result

    def signature(self, grids):
        ids = tuple(None if grid is None else self.identifier(grid) for grid in grids)
        self.budget.consume('state_key_nodes', len(ids))
        if any(i is None and grid is not None for i, grid in zip(ids, grids)):
            # A disjoint tag prevents collision with a tuple of interned IDs.
            self.budget.consume('state_hash_cells', sum(len(g)*len(g[0]) for g in grids if g is not None))
            return ('grids', tuple(grids))
        return ('ids', ids)

    def palette(self, grid):
        ident = self.identifier(grid)
        self.budget.consume('palette_lookups')
        if ident is not None and ident in self.palettes:
            return self.palettes[ident]
        self.budget.consume('signature_palette_cells', len(grid)*len(grid[0]))
        result = frozenset(c for row in grid for c in row)
        if ident is not None:
            self.budget.consume('palette_writes', len(result))
            self.palettes[ident] = result
        return result

    def can_reach_palette(self, current, target):
        # Every expanded primitive in this DSL only uses input colors.
        a, b = self.palette(current), self.palette(target)
        self.budget.consume('signature_palette_checks', len(b))
        return b.issubset(a)


def output_shape(shape, extension, budget):
    """Exact dimensions when derivable cheaply; None means unknown, not failure."""
    h, w = shape
    for step in extension:
        budget.consume('signature_shape_steps')
        op = step.op
        if op in ('rot90', 'rot270', 'transpose'):
            h, w = w, h
        elif op == 'up2':
            h, w = 2*h, 2*w
        elif op == 'tile1x2':
            w *= 2
        elif op == 'tile2x1':
            h *= 2
        elif op == 'down2':
            if h % 2 or w % 2:
                return None  # Undefined is checked by the normal executor.
            h, w = h//2, w//2
        elif op in ('crop', 'pack') or op == 'relate' and step.effect == 'extract':
            return None
        elif op not in ('identity', 'rot180', 'fliplr', 'flipud', 'object', 'relate'):
            return None
    return h, w


def ordered_extensions(compiled, parent_outputs, demos, budget):
    """Train-only ordering, retaining every atom, including shape-changing ones."""
    priorities = []
    for index, pair in enumerate(compiled):
        _, extension = pair
        score = 0
        for grid, (_, target) in zip(parent_outputs, demos):
            shape = output_shape((len(grid), len(grid[0])), extension, budget)
            desired = (len(target), len(target[0]))
            # Known match, then unknown, then mismatch. Never prune on priority.
            score += 0 if shape == desired else 1 if shape is None else 2
        priorities.append((score, index, pair))
    budget.consume('signature_order_work', len(priorities)*max(1, len(priorities).bit_length()))
    priorities.sort(key=lambda item: item[:2])
    return [pair for _, _, pair in priorities]


class _BindingDomain:
    """Resolve role aliases once on one public prefix output, without rendering."""
    def __init__(self, rows, cache):
        self.rows, self.cache = rows, cache
        self.scene, self.roles, self.relations = None, {}, {}
        self.grounded = False

    def signature(self, step):
        budget = self.cache.budget
        budget.consume('binding_signature_reads')
        if self.rows is None:
            return None
        if step.op not in ('object', 'relate'):
            return ('literal', step)
        if not self.grounded:
            try:
                self.scene = grounding.ground(self.rows, budget, analysis=self.cache.analysis)
            except ValueError:
                self.scene = None
            self.grounded = True
        if self.scene is None:
            return None
        scene = self.scene
        if step.role not in self.roles:
            try:
                source = grounding.select(scene, step.role, budget, analysis=self.cache.analysis)
                budget.consume('binding_source_index', len(scene.objects))
                self.roles[step.role] = scene.objects.index(source)
            except ValueError:
                self.roles[step.role] = None
        source_index = self.roles[step.role]
        if source_index is None:
            return None
        if step.op == 'object':
            return ('object', source_index, step.effect)
        if step.effect == 'extract':
            return ('extract', source_index)
        key = (source_index, step.relation)
        if key not in self.relations:
            selected = grounding.targets(scene, scene.objects[source_index], step.relation,
                                         budget, analysis=self.cache.analysis)
            budget.consume('binding_target_indices', len(selected)*len(scene.objects))
            self.relations[key] = tuple(scene.objects.index(obj) for obj in selected)
        targets = self.relations[key]
        if not targets:
            return None
        return ('relate', source_index, step.effect, targets)


def prune_binding_aliases(compiled, parent_outputs, query_outputs, cache):
    """Prune only undefined train bindings or equal bindings on ALL public grids.

    Checks are paid and counted even when no executable candidate is created.
    The original alphabet remains available at every prefix. A different query
    binding keeps a distinct representative. Multi-step chunks stay opaque.
    """
    budget = cache.budget
    domains = [_BindingDomain(rows, cache) for rows in (*parent_outputs, *query_outputs)]
    retained, seen, discarded = [], {}, []
    for atom, extension in compiled:
        budget.consume('signature_operator_checks')
        budget.consume('signature_program_checks', len(extension))
        if len(extension) != 1 or len(atom['steps']) != 1:
            # Preserve symbolic step-limit behavior as well as execution.
            retained.append((atom, extension))
            continue
        else:
            components = []
            for index, domain in enumerate(domains):
                key = domain.signature(extension[0])
                if key is None and index < len(parent_outputs):
                    discarded.append((extension, 'proven_inapplicable', None))
                    break
                components.append(key)
            else:
                # Bounded object-index tuples; charge their key construction.
                budget.consume('binding_signature_key_units',
                               sum(1 if key is None else len(key) + (len(key[-1])
                                   if key[0] == 'relate' else 0) for key in components))
                signature = ('bindings', tuple(components))
                if signature in seen:
                    discarded.append((extension, 'binding_alias', seen[signature]))
                else:
                    budget.consume('binding_signature_writes')
                    seen[signature] = extension
                    retained.append((atom, extension))
                continue
            continue
    return retained, discarded
