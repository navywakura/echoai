"""Pure B24 researcher. Inputs and returned receipts completely determine a slot.

The custodian scopes its full archive with ``visible_history`` BEFORE persisting
the six-field investigator input. No files, evaluator, model, or clocks are used.
Round/slot/author are zero based; proposal IDs remain global, one based.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction
from itertools import product
import json
import math
import random

from echo_arc import s6b22_search as old, s6b23_search as m23
from echo_arc import s6b23r4_search as r4
from echo_arc.contrastive_evidence import require_development
from echo_arc.feasible_grammar import canonical, matches, public_features
from seed.game_selfimprove import sha
from seed.s6b13_prompt import effective

KINDS = ('R4-REF', 'B24-G', 'B24-S', 'B24-I', 'B24-C')
SEED = 824101
ROUNDS = 18                         # compatibility: total logical slots
MAX_REPAIRS = 8
MAX_CHILDREN = 2
MAX_LINEAGE_REPAIRS = 4
MAX_INSPECTED = 2048
MENU_LIMIT = 64
VALUES = old.VALUES
validate_proposal = old.validate_proposal
HOLD_SITE = 'Arc3EchoV57.choose: self.hold = self.HOLD after queued known reset'


def _rng(seed, *parts):
    return random.Random(int(sha(['B24', seed, *parts]), 16))


def repair_quotas(seed=SEED):
    quotas = [3, 3, 2]
    _rng(seed, 'repair-quotas').shuffle(quotas)
    return quotas


def schedule(kind, index, seed=SEED):
    if kind not in KINDS or type(index) is not int or not 0 <= index < ROUNDS:
        raise ValueError('unknown arm or slot')
    if type(seed) is not int:
        raise ValueError('integer research seed required')
    authors = [0, 0, 1, 1, 2, 2]
    _rng(seed, 'researcher-order', index//6).shuffle(authors)
    return dict(author=authors[index % 6] if kind in ('B24-I', 'B24-C') else 0,
                round=index//6, slot=index)


def config():
    return dict(kinds=KINDS, seed=SEED, rounds=ROUNDS, research_rounds=3,
                slots_per_round=6, slots_per_author_per_round=2,
                researcher_schedule=[schedule('B24-I', i) for i in range(ROUNDS)],
                repair_quotas=repair_quotas(), max_repairs=MAX_REPAIRS,
                max_children=MAX_CHILDREN, max_lineage_repairs=MAX_LINEAGE_REPAIRS,
                max_inspected=MAX_INSPECTED, menu_limit=MENU_LIMIT, values=VALUES,
                language_sha256=old.language.language_sha(),
                parent_order='lineage services, losses, -net gain, newest id',
                explore='seeded HOLD x length x feature strata; alternating unrestricted / observed atoms',
                menu_order='explore: balanced duration/length/features; repair: 3 overlap-ranked / 1 diversity',
                repair='one literal edit, fixed parent HOLD; positive measured net gain only',
                shared_lineage_budget='one seeded eligible author per shared root per round; no private counts',
                duplicate_filter='normalized exact proposals in visible archive only',
                inactivity_filter='unchanged values at every complete baseline HOLD consumption',
                summary='greedy joint-vector extrema coverage; complete feature ranges and all parent cases',
                candidate_ids='C + one-based slot (2 digits) + menu offset (2 digits); full catalog hash binds receipt',
                limits=dict(input_tokens=8192, output_tokens=768, context_tokens=9216),
                timing='external custodian; deterministic work counters only')


def visible_history(kind, index, seed, history):
    """Scope a full OR already scoped prefix, without inspecting private results.

    All expected visible global IDs must be present, in order. Extra records
    may only be earlier, scheduled peers. Reapplying this function is lossless.
    """
    current = schedule(kind, index, seed)
    plans = [schedule(kind, i, seed) for i in range(index)]
    allowed = {i+1 for i, p in enumerate(plans)
               if kind not in ('B24-I', 'B24-C') or p['author'] == current['author']
               or (kind == 'B24-C' and p['round'] < current['round'])}
    if type(history) is not list:
        raise ValueError('history must be an ordered array')
    result = []
    last = 0
    for event in history:
        ident = event.get('id') if isinstance(event, dict) else None
        if type(ident) is not int or not last < ident <= index:
            raise ValueError('duplicate, reordered or future history ID')
        last = ident
        expected = plans[ident-1]
        recorded = event.get('schedule', {})
        for key, value in expected.items():
            if event.get(key, recorded.get(key)) != value:
                raise ValueError('history author/round/slot does not match seeded schedule')
            if key in recorded and recorded[key] != value:
                raise ValueError('inconsistent history schedule metadata')
        if ident in allowed:
            result.append(event)
    if {e['id'] for e in result} != allowed:
        raise ValueError('incomplete visible history')
    return deepcopy(result)


def _read(read):
    if not isinstance(read, dict) or not isinstance(read.get('features'), dict):
        raise ValueError('missing consumer features')
    if set(read['features']) != set(old.language.precise_patch.FEATURES):
        raise ValueError('incomplete or foreign consumer features')
    public_features(read['features'])
    if type(read.get('count')) is not int or read['count'] < 1:
        raise ValueError('invalid consumer count')
    if type(read.get('value')) is not int or not 0 <= read['value'] <= 100:
        raise ValueError('invalid consumed HOLD')
    if read.get('parameter', 'HOLD') != 'HOLD':
        raise ValueError('foreign consumer parameter')


def _baseline(policy, base):
    rows = base['rows']
    if not isinstance(rows, list) or not rows:
        raise ValueError('complete nonempty baseline cases required')
    require_development(rows)
    cases = []
    for row in rows:
        diagnostics = row['diagnostics']
        if diagnostics.get('truncated') or diagnostics.get('omitted', 0) or diagnostics.get('complete') is False:
            raise ValueError('incomplete baseline consumptions')
        reads = diagnostics['consumers']
        if not isinstance(reads, list):
            raise ValueError('complete baseline consumers required')
        case = []
        for read in reads:
            if read['parameter'] != 'HOLD':
                continue
            _read(read)
            before = effective('HOLD', read['features'], policy)
            if read['value'] != before:
                raise ValueError('baseline consumed value disagrees with base policy')
            case.append(dict(features=dict(read['features']), count=read['count'], value=before))
        cases.append(case)
    return dict(base_sha256=sha(policy), baseline_sha256=sha(base),
                rows_sha256=sha(rows), consumption_site=HOLD_SITE,
                case_indices=list(range(len(rows))), complete_cases=True, cases=cases)


def _inactive(proposal, basis):
    item = proposal['patches'][0]
    value = item['set']['HOLD']
    comparisons = []
    for case in basis['cases']:
        compared = []
        for i, read in enumerate(case):
            match = matches(item['when'], read['features'])
            after = value if match else read['value']
            if after != read['value']:
                return None
            compared.append(dict(read_index=i, count=read['count'], guard_match=match,
                                 before=read['value'], after=after))
        comparisons.append(compared)
    return dict(base_sha256=basis['base_sha256'], baseline_sha256=basis['baseline_sha256'],
                consumption_site=HOLD_SITE, case_indices=basis['case_indices'],
                complete_cases=True, changed_consumptions=0, comparisons=comparisons,
                scope='same deterministic base and complete recorded cases; sole HOLD intervention')


def inactivity_receipt(proposal, policy, base):
    """None means unproved inactivity, never a prediction of improvement."""
    basis = _baseline(policy, base)
    result = _inactive(validate_proposal(proposal), basis)
    return dict(result, basis=basis) if result is not None else None


def _validate_history(policy, rows, history, kind, seed):
    base_hash = sha(policy)
    for event in history:
        if event.get('base_sha256') != base_hash:
            raise ValueError('foreign base')
        if event.get('kind', kind) != kind:
            raise ValueError('foreign arm')
        p = event.get('proposal')
        if p is not None:
            validate_proposal(p)
        parent = event.get('target_id')
        phase = event['schedule'].get('phase')
        if kind != 'R4-REF' and (phase not in ('global', 'repair') or (parent is not None) != (phase == 'repair')):
            raise ValueError('inconsistent repair lineage')
        m23.root_id(event, history)  # missing or noncausal parents cannot be imported
        if parent is not None and p is not None:
            target = next(e for e in history if e['id'] == parent)
            if target.get('proposal') is None or p['patches'][0]['set'] != target['proposal']['patches'][0]['set']:
                raise ValueError('repair changed parent HOLD')
            if p['patches'][0]['when'] not in old.neighbors(target['proposal']['patches'][0]['when']):
                raise ValueError('repair is not one guard edit')
        d = event.get('development')
        if d is None:
            continue
        if p is None or d.get('origin') != 'DEVELOPMENT_A' or d.get('consumer_parameter') != 'HOLD':
            raise ValueError('protected or foreign evidence')
        cases, reads = d['case_effects'], d['candidate_consumers']
        if len(cases) != len(rows) or len(reads) != len(rows) or [c['case_index'] for c in cases] != list(range(len(rows))):
            raise ValueError('incomplete or reordered case evidence')
        for case in cases:
            if type(case['level_delta']) is not int or type(case['score_delta']) not in (int, float) or not math.isfinite(case['score_delta']):
                raise ValueError('invalid case effect')
        for case in reads:
            for read in case:
                _read(read)
    if kind == 'R4-REF':
        return
    children = Counter(e.get('target_id') for e in history if e.get('target_id') is not None)
    lineage = Counter(m23.root_id(e, history) for e in history if e.get('target_id') is not None)
    services = Counter(e['author'] for e in history if e.get('target_id') is not None)
    quotas = repair_quotas(seed) if kind in ('B24-I', 'B24-C') else [MAX_REPAIRS]
    if any(n > MAX_CHILDREN for n in children.values()) or any(n > MAX_LINEAGE_REPAIRS for n in lineage.values()):
        raise ValueError('repair lineage budget exceeded')
    if any(n > quotas[a] for a, n in services.items()):
        raise ValueError('researcher repair quota exceeded')


def _shared_owner(root, history, current, seed):
    """Reserve shared lineage service before the round, without peer feedback.

    Only one author can service a shared root this round. With two slots per
    author this enforces node/lineage caps even when other outcomes are hidden.
    Ownership is a budget reservation; provenance and per-author quotas persist.
    """
    closed = [e for e in history if e['round'] < current['round']]
    used = Counter(e['author'] for e in closed if e.get('target_id') is not None)
    available = [a for a, cap in enumerate(repair_quotas(seed)) if used[a] < cap]
    return min(available, key=lambda a: sha([seed, 'shared-root-owner', current['round'], root, a]), default=None)


def _parent(kind, current, seed, history):
    own_repairs = sum(e['author'] == current['author'] and e.get('target_id') is not None for e in history)
    quota = repair_quotas(seed)[current['author']] if kind in ('B24-I', 'B24-C') else MAX_REPAIRS
    if own_repairs >= quota:
        return None, own_repairs, quota
    by_id = {e['id']: e for e in history}
    for parent in m23.parents(history):
        root = m23.root_id(parent, history)
        if kind == 'B24-C' and by_id[root]['round'] < current['round']:
            if _shared_owner(root, history, current, seed) != current['author']:
                continue
        return parent, own_repairs, quota
    return None, own_repairs, quota


def read_summary(readings, limit=4):
    """Complete ranges, plus actual joint vectors chosen by extrema coverage."""
    if type(limit) is not int or limit < 1:
        raise ValueError('positive summary limit required')
    unique = {canonical(r): deepcopy(r) for r in readings}
    values = [unique[k] for k in sorted(unique)]
    keys = sorted({k for r in values for k in r['features']})
    if any(set(r['features']) != set(keys) for r in values):
        raise ValueError('incomplete feature vector')
    ranges = {k: [min(r['features'][k] for r in values), max(r['features'][k] for r in values)] for k in keys}
    varying = [k for k in keys if ranges[k][0] != ranges[k][1]]
    uncovered = {(k, v) for k in varying for v in ranges[k]}
    selected = []
    remaining = list(values)
    while remaining and len(selected) < limit:
        best = min(remaining, key=lambda r: (-sum((k, r['features'][k]) in uncovered for k in varying), canonical(r)))
        selected.append(best)
        uncovered.difference_update((k, best['features'][k]) for k in varying)
        remaining.remove(best)
    return dict(reads=selected, ranges=ranges, varying=varying, total=len(readings),
                occurrences=sum(r['count'] for r in readings), unique=len(values),
                omitted=len(remaining), uncovered_extrema=len(uncovered), all_sha256=sha(readings))


def _explore(seed, current, basis, history):
    atoms = defaultdict(list)
    for k, op, v in old.language.atoms():
        atoms[k].append([op, v])
    points = {canonical(r['features']): r['features'] for case in basis['cases'] for r in case}
    for event in history:
        for case in (event.get('development') or {}).get('candidate_consumers', []):
            for read in case:
                points[canonical(read['features'])] = read['features']
    points = [points[k] for k in sorted(points)]
    keys = sorted(atoms)
    strata = list(product(VALUES, (1, 2, 3), keys))
    rnd = _rng(seed, 'explore', current['slot'], current['author'])
    for draw in range(MAX_INSPECTED):
        if draw % len(strata) == 0:
            rnd.shuffle(strata)
        value, size, anchor = strata[draw % len(strata)]
        features = sorted([anchor] + rnd.sample([k for k in keys if k != anchor], size-1))
        point = rnd.choice(points) if points and draw % 2 else None
        guard = {}
        for key in features:
            choices = [a for a in atoms[key] if matches({key: a}, point)] if point is not None else atoms[key]
            guard[key] = list(rnd.choice(choices or atoms[key]))
        yield {'patches': [dict(when=guard, set={'HOLD': value})]}


def _catalog(parent, history, policy, basis, seed, current):
    if parent is None:
        stream = _explore(seed, current, basis, history)
        syntax_total = None
    else:
        patch = parent['proposal']['patches'][0]
        guards = old.neighbors(patch['when'])
        _rng(seed, 'neighbors', current['slot'], parent['id']).shuffle(guards)
        syntax_total = len(guards)
        stream = ({'patches': [dict(when=g, set=dict(patch['set']))]} for g in guards)
    used = {canonical(validate_proposal(e['proposal'])): e['id'] for e in history if e.get('proposal')}
    rejected, options, seen = [], [], set()
    inspected = 0
    for raw in stream:
        if inspected == MAX_INSPECTED:
            break
        inspected += 1
        p = validate_proposal(raw)
        key = canonical(p)
        reject = dict(proposal=p, proposal_sha256=sha(p))
        if key in used:
            rejected.append(dict(reject, reason='duplicate', visible_id=used[key]))
            continue
        certificate = _inactive(p, basis)
        if certificate is not None:
            rejected.append(dict(reject, reason='inactive', certificate=certificate))
            continue
        if key in seen:
            rejected.append(dict(reject, reason='catalog_duplicate'))
            continue
        seen.add(key)
        option = dict(proposal=p, predicted_gain=None, measured_effect=None, loss_risk='unknown')
        loss, gain = None, None
        if parent is not None:
            loss, gain, cases = old.overlap(p['patches'][0]['when'], parent, policy)
            option.update(loss_context_overlap=float(loss) if loss is not None else None,
                          gain_context_overlap=float(gain) if gain is not None else None, per_case=cases)
        options.append(((loss if loss is not None else Fraction(1),
                         -(gain if gain is not None else Fraction(0)),
                         sha([seed, current, p])), option))
    options.sort(key=lambda x: x[0])
    eligible = len(options)
    duration_counts, length_counts, feature_counts = Counter(), Counter(), Counter()
    selected = []
    def diversity(item):
        p = item[1]['proposal']['patches'][0]
        return (duration_counts[p['set']['HOLD']], length_counts[len(p['when'])],
                sum(feature_counts[k] for k in p['when']), item[0][-1])
    while options and len(selected) < MENU_LIMIT:
        entry = min(options, key=diversity) if parent is None or len(selected) % 4 == 3 else options[0]
        options.remove(entry)
        selected.append(entry[1])
        p = entry[1]['proposal']['patches'][0]
        duration_counts[p['set']['HOLD']] += 1
        length_counts[len(p['when'])] += 1
        feature_counts.update(p['when'].keys())
    menu = [dict(id=f'C{current["slot"]+1:02d}{i:02d}', **e)
            for i, e in enumerate(selected)]
    return menu, dict(inspected=inspected, eligible=eligible, retained=len(menu),
                      rejected=rejected, menu_truncated=eligible > MENU_LIMIT,
                      inspection_truncated=syntax_total is None or syntax_total > MAX_INSPECTED,
                      syntax_total=syntax_total,
                      coverage=dict(durations={str(k): v for k, v in sorted(duration_counts.items())},
                                    guard_lengths={str(k): v for k, v in sorted(length_counts.items())},
                                    features=dict(sorted(feature_counts.items()))))


def _prompt(policy, base, history, parent, menu, current):
    columns = sorted(old.language.precise_patch.FEATURES)
    effect_columns = ['case_index', 'level_delta', 'score_delta']
    contexts, context_ids = [], {}
    atom_table, proposal_table, effect_table = [], [], []
    def intern(table, value):
        if value not in table:
            table.append(value)
        return table.index(value)
    def compact_proposal(p):
        if p is None:
            return None
        item = p['patches'][0]
        atoms = [intern(atom_table, [columns.index(k), *test]) for k, test in sorted(item['when'].items())]
        return intern(proposal_table, [item['set']['HOLD'], atoms])
    def packed(reads, guard=None):
        summary = read_summary(reads)
        shown = []
        for read in summary.pop('reads'):
            vector = [read['features'][k] for k in columns]
            key = tuple(vector)
            if key not in context_ids:
                context_ids[key] = len(contexts)
                contexts.append(vector)
            shown.append([context_ids[key], read['value'], read['count'],
                          matches(guard, read['features']) if guard else None,
                          read['value'] != effective('HOLD', read['features'], policy)])
        # Hashes remain in the input/receipt, not repeated in model context.
        # Constants are in every actual vector; all varying ranges survive.
        ranges = [[columns.index(k), *summary['ranges'][k]] for k in summary['varying']]
        tails = Counter(canonical(r[1:]) for r in shown)
        defaults = json.loads(min(tails, key=lambda k: (-tails[k], k))) if tails else []
        compact_reads = []
        for read in shown:
            changes = [[i, x] for i, x in enumerate(read[1:]) if x != defaults[i]]
            compact_reads.append([read[0], changes] if changes else [read[0]])
        return [summary[k] for k in ('total', 'occurrences', 'unique', 'omitted', 'uncovered_extrema')] + [ranges, defaults, compact_reads]
    archive = []
    for event in history:
        development = event.get('development')
        sparse_effects = None if development is None else [
            [c[k] for k in effect_columns] for c in development['case_effects']
            if c['level_delta'] != 0 or c['score_delta'] != 0]
        archive.append([event['id'], event['author'], event['round'], event.get('target_id'),
                        compact_proposal(event.get('proposal')), event.get('verdict'), event.get('error'),
                        intern(effect_table, sparse_effects) if sparse_effects is not None else None])
    dossier = None
    if parent is not None:
        d = parent['development']
        links = {c['case_index']: c for c in d.get('control_links', [])}
        contrasts = {c['case_index']: c for c in d.get('contrasts', [])}
        cases = []
        for effect in d['case_effects']:
            i = effect['case_index']
            link, contrast = links.get(i, {}), contrasts.get(i, {})
            cases.append([i, packed(d['candidate_consumers'][i], parent['proposal']['patches'][0]['when']),
                          parent.get('actions_per_level', [None]*len(base['rows']))[i],
                          link.get('first_action_divergence', contrast.get('first_different_action')),
                          [link.get(k) for k in ('read_action_index', 'consumed_values', 'steps_until_action_divergence')] if link else None])
        dossier = dict(id=parent['id'], author=parent['author'], root_id=m23.root_id(parent, history),
                       proposal_id=compact_proposal(parent['proposal']), attribution='uncertain',
                       effects_id=next(e[-1] for e in archive if e[0] == parent['id']),
                       loss_cases=old.effects(parent)[1], cases=cases)
    base_cases = [[i, row['levels_completed'], row['score'], row['actions_per_level'],
                   packed([r for r in row['diagnostics']['consumers'] if r['parameter'] == 'HOLD'])]
                  for i, row in enumerate(base['rows'])]
    # A real medoid, not synthetic marginal extrema. Every original joint vector
    # is recoverable by replacing the listed coordinates of this observed row.
    reference = min(contexts, key=lambda v: (sum(a != b for other in contexts for a, b in zip(v, other)), v)) if contexts else []
    sparse_contexts = [[[i, x] for i, x in enumerate(vector) if x != reference[i]] for vector in contexts]
    compact_menu = [[e['id'], compact_proposal(e['proposal'])] for e in menu]
    return canonical(dict(
        task='Select exactly one complete candidate by ID. Goal: >=2 extra levels, no individual level loss or score loss (tolerance 1e-10).',
        response=dict(candidate_id='one exact ID from menu'),
        semantics=dict(HOLD_default=40, consumption=HOLD_SITE,
                       hold='Sets a future interval suppressing repeated known reset keys; the body can still move. Does not clamp an existing interval (COOLDOWN_CAP does).',
                       guards='1-3 distinct observable features, AND; patches appended to base, last matching assignment wins.',
                       score='100 * sum(i * min(baseline_actions[i]/actions_per_level[i],1)**2 for completed levels i=1..N) / sum(i for i=1..N); uncompleted or zero-action levels contribute 0; empty denominator gives 0.',
                       evidence='Case indices identify evidence only, never legal features. Guard match, changed consumption, first action divergence and final effect are distinct. Final effects are associations; attribution uncertain. No child inherits parent results.'),
        mode='REPAIR' if parent else 'EXPLORE', parent_id=parent['id'] if parent else None,
        policy=policy, author=current['author'], round=current['round'], cohort_size=len(base['rows']),
        context_columns=columns, context_reference=reference, contexts=sparse_contexts,
        context_encoding='Each context copies the real context_reference then replaces [column_index,value] pairs. No other coordinates change.',
        read_columns=['context_id', 'consumed_HOLD', 'count', 'parent_guard_matches', 'differs_from_base_at_context'],
        summary_columns=['total', 'occurrences', 'unique', 'omitted', 'uncovered_extrema', 'varying_ranges_[column,min,max]', 'read_defaults', 'reads'],
        read_encoding='Read=[context_id,optional changes]. Copy summary.read_defaults=[HOLD,count,parent_guard_matches,differs_from_base_at_context], then replace each [zero_based_tail_column,value] in changes; absent changes means exact defaults.',
        base_columns=['case', 'levels', 'score', 'actions_per_level', 'consumptions'], base=base_cases,
        history_columns=['id', 'author', 'round', 'parent_id', 'proposal_id', 'verdict', 'error', 'effects_id'],
        proposals=proposal_table, proposal_columns=['HOLD', 'guard_atom_ids'],
        effects=effect_table, atoms=atom_table,
        effect_columns=effect_columns, atom_columns=['context_column_index', 'operator', 'integer'],
        effect_encoding='null means unmeasured. Otherwise sparse complete-cohort deltas: any absent case in 0..cohort_size-1 has EXACT level_delta=0 and score_delta=0, not unknown. Tiny nonzero scores are retained.',
        parent_case_columns=['case_index', 'consumptions', 'actions_per_level', 'first_different_action', 'changed_consumption'],
        parent_link_columns=['read_action_index', 'consumed_values', 'steps_until_action_divergence'],
        history=archive, parent=dossier,
        menu=compact_menu, menu_columns=['id', 'proposal_id'],
        compaction='All archive effects and parent cases/losses retained exactly; complete varying-feature ranges, greedy actual joint-vector coverage, omissions counted. Custodian must check actual tokens; never silently cut this dossier or menu.'))


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def from_bytes(data):
    obj = _json(data)
    if type(obj) is not dict or set(obj) != {'policy', 'base', 'own_history', 'kind', 'index', 'seed'}:
        raise ValueError('unexpected investigator input surface')
    kind, index, seed = obj['kind'], obj['index'], obj['seed']
    current = schedule(kind, index, seed)
    history = visible_history(kind, index, seed, obj['own_history'])
    policy, base = obj['policy'], obj['base']
    if kind == 'R4-REF':
        # Delegate the frozen prompt and all original scientific decisions exactly.
        req = r4.model_request('N7', index, seed, policy, base, history)
        return dict(req, schedule=dict(req['schedule'], **current), proposal=None,
                    menu=[], menu_sha256=sha([]), selection_protocol='r4-json')
    basis = _baseline(policy, base)
    _validate_history(policy, base['rows'], history, kind, seed)
    parent, repairs_used, quota = _parent(kind, current, seed, history)
    menu, work = _catalog(parent, history, policy, basis, seed, current)
    plan = dict(current, phase='repair' if parent else 'global', mode='REPAIR' if parent else 'EXPLORE',
                parent_id=parent['id'] if parent else None,
                parent_receipt_sha256=sha(parent) if parent else None, base_sha256=sha(policy),
                root_id=m23.root_id(parent, history) if parent else None,
                repairs_used=repairs_used, repair_quota=quota, visible_ids=[e['id'] for e in history],
                visible_history_sha256=sha(history), inactivity_basis=basis, **work)
    prompt = _prompt(policy, base, history, parent, menu, current)
    req = dict(id=index+1, type='REFINE' if parent else 'WAIT', target_id=parent['id'] if parent else None,
               selection_mode=kind, requested_operator='HOLD', operator_binding=True,
               model_call_required=bool(menu) and kind != 'B24-G', schedule=plan, prompt=prompt,
               proposal=deepcopy(menu[0]['proposal']) if menu and kind == 'B24-G' else None,
               menu=menu, menu_sha256=sha(menu), selection_protocol='candidate-id' if menu and kind != 'B24-G' else 'none',
               predicted_gain=None, measured_effect=None, prompt_bytes=len(prompt.encode()))
    if not menu:
        req['abstention'] = 'NO_ELIGIBLE_CANDIDATE'
    return req


def reconstruct(req, selection):
    """Strict wire decoding: never repair, supplement or reinterpret a choice."""
    if isinstance(selection, (str, bytes, bytearray)):
        selection = _json(selection)
    protocol = req['selection_protocol']
    if protocol == 'r4-json':
        return validate_proposal(selection)
    menu = req['menu']
    if sha(menu) != req['menu_sha256']:
        raise ValueError('menu hash mismatch')
    if protocol == 'none':
        if selection is not None:
            raise ValueError('no selection allowed without a model call')
        if not menu and req.get('abstention') == 'NO_ELIGIBLE_CANDIDATE' and req['proposal'] is None:
            return None
        if menu and req['proposal'] == menu[0]['proposal']:
            return validate_proposal(req['proposal'])
        raise ValueError('invalid deterministic selection')
    if protocol != 'candidate-id' or type(selection) is not dict or set(selection) != {'candidate_id'} or type(selection['candidate_id']) is not str:
        raise ValueError('expected exactly one typed candidate_id')
    matches_id = [e for e in menu if e['id'] == selection['candidate_id']]
    if len(matches_id) != 1:
        raise ValueError('unknown or ambiguous candidate ID')
    return validate_proposal(matches_id[0]['proposal'])
