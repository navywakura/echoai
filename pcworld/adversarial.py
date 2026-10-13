"""Bounded adversarial probe categories and evidence-aware E routing.

This is an explicit symbolic policy, not a learned critic or a claim that CAM
discovers bug classes by itself. CAM supplies the seen-probe history; E uses
that history and visible source cues to choose an untested category.
"""
import json


ATTACKS={
    'intervals':('touching-endpoints','nested-transitive','empty-singleton'),
    'records':('duplicate-keys','empty-singleton','first-occurrence-order'),
    'path':('dotdot-cancellation','root-boundary','repeated-separators'),
    'csv':('quoted-delimiter','escaped-quote','whitespace-newline'),
    'pagination':('negative-bounds','empty-out-of-range','zero-limit'),
    'dependencies':('self-and-multinode-cycles','duplicate-edges','disconnected-lex-order'),
}

FIXED_ORDER={
    'intervals':('empty-singleton','nested-transitive','touching-endpoints'),
    'records':('empty-singleton','first-occurrence-order','duplicate-keys'),
    'path':('repeated-separators','root-boundary','dotdot-cancellation'),
    'csv':('whitespace-newline','escaped-quote','quoted-delimiter'),
    'pagination':('empty-out-of-range','zero-limit','negative-bounds'),
    'dependencies':('disconnected-lex-order','duplicate-edges','self-and-multinode-cycles'),
}

GUIDANCE={
    'touching-endpoints':'Try intervals that meet at exactly one endpoint and a nested interval.',
    'nested-transitive':'Try nested and transitively overlapping intervals in a different order.',
    'empty-singleton':'The input MUST be a JSON list with exactly zero or one elements: [] or [one valid element]. NEVER include multiple elements in this category.',
    'duplicate-keys':'Use the same key twice with different values; check which occurrence must survive.',
    'first-occurrence-order':'Use repeated keys interleaved with another key; check stable order.',
    'dotdot-cancellation':'Use a path containing /../ and verify lexical cancellation.',
    'root-boundary':'Use /../../x and verify that normalization never climbs above root.',
    'repeated-separators':'Use repeated slashes and dot components in an absolute path.',
    'quoted-delimiter':'Use a delimiter inside a quoted CSV field.',
    'escaped-quote':'Use doubled quotes inside a quoted CSV field.',
    'whitespace-newline':'Check significant spaces and a quoted newline.',
    'negative-bounds':'Use negative offset or limit and verify each is clamped separately.',
    'empty-out-of-range':'Try empty input and offsets beyond the final item.',
    'zero-limit':'Try limit zero and one item.',
    'self-and-multinode-cycles':'Try a self-edge and a multi-node cycle.',
    'duplicate-edges':'Repeat an edge and verify it has no extra effect.',
    'disconnected-lex-order':'Use disconnected nodes and ties that require the lexicographically smallest order.',
}

def _family(task):
    prop=task.get('property','')
    if not isinstance(prop,str) or not prop.startswith('repair.'):
        raise ValueError('adversarial routing requires a repair task')
    family=prop.split('.',1)[1]
    if family not in ATTACKS: raise ValueError('unknown repair family')
    return family

def choose_category(arm,task,source,seen):
    """Choose a fixed category for F or rank unseen source risks for E."""
    family=_family(task);ordered=ATTACKS[family]
    if arm not in ('F','E'): raise ValueError('only critic arms route adversarial probes')
    seen=set(seen)
    if arm=='F': return next((category for category in FIXED_ORDER[family] if category not in seen),None)
    if arm=='E':
        # Transparent, preregisterable source cues for this bounded repair suite.
        # The cues prioritize a probe; they do not label code as correct or faulty.
        cues={
            'intervals':('touching-endpoints' if '<' in source and '<=' not in source else None),
            'records':('duplicate-keys' if 'DictComp' in source or "{p['id']:p" in source else None),
            'path':('dotdot-cancellation' if '.split' in source and '..' not in source else None),
            'csv':('quoted-delimiter' if '.split' in source and ',' in source else None),
            'pagination':('negative-bounds' if '[' in source and 'offset' in source else None),
            'dependencies':('self-and-multinode-cycles' if 'dfs' in source or 'visited' in source else None),
        }
        preferred=cues[family]
        if preferred and preferred not in seen: return preferred
    return next((category for category in ordered if category not in seen),None)

def matches_category(task,category,value):
    """Independently reject a critic input that does not exercise its label."""
    family=_family(task)
    if category not in ATTACKS[family]: return False
    from .repairs import repair_domain
    if not repair_domain(task['property'],value): return False
    if category=='empty-singleton': return len(value) in (0,1)
    if category=='touching-endpoints':
        return any(a[1]==b[0] or b[1]==a[0] for i,a in enumerate(value) for b in value[i+1:])
    if category=='nested-transitive':
        return any((a[0]<=b[0] and b[1]<=a[1]) or (b[0]<=a[0] and a[1]<=b[1])
                   for i,a in enumerate(value) for b in value[i+1:])
    if category in ('duplicate-keys','first-occurrence-order'):
        positions={};
        for i,row in enumerate(value): positions.setdefault(row['id'],[]).append(i)
        repeated=[idx for idx in positions.values() if len(idx)>1]
        if not repeated: return False
        if category=='duplicate-keys':
            return any(len({value[i]['value'] for i in idx})>1 for idx in repeated)
        return any(idx[-1]-idx[0]>1 for idx in repeated)
    if category=='dotdot-cancellation': return '..' in value.split('/')
    if category=='root-boundary': return value.split('/').count('..')>=2 and value.startswith('/../')
    if category=='repeated-separators': return '//' in value or '/./' in value or value.endswith('/.')
    if category=='quoted-delimiter':
        import re
        return bool(re.search(r'"(?:[^"]|"")*,(?:[^"]|"")*"',value))
    if category=='escaped-quote': return '""' in value
    if category=='whitespace-newline':
        return '\n' in value or bool(__import__('re').search(r'(?:^|,)\s|\s(?:,|$)',value))
    if category in ('negative-bounds','empty-out-of-range','zero-limit'):
        if category=='negative-bounds': return value['offset']<0 or value['limit']<0
        if category=='empty-out-of-range': return not value['items'] or value['offset']>=len(value['items'])
        return value['limit']==0
    if category in ('self-and-multinode-cycles','duplicate-edges','disconnected-lex-order'):
        nodes=value['nodes'];edges=[tuple(e) for e in value['edges']]
        if category=='duplicate-edges': return len(edges)!=len(set(edges))
        if category=='disconnected-lex-order':
            degree={n:0 for n in nodes}
            for a,b in edges: degree[a]+=1;degree[b]+=1
            return len(nodes)>1 and any(degree[n]==0 for n in nodes) and bool(edges)
        graph={n:[] for n in nodes}
        for a,b in edges: graph[a].append(b)
        active=set();done=set()
        def visit(node):
            if node in active: return True
            if node in done: return False
            active.add(node)
            cyclic=any(visit(next_node) for next_node in graph[node])
            active.remove(node);done.add(node)
            return cyclic
        return any(visit(node) for node in nodes)
    return False

def critic_instructions(task,category,*,seen_inputs=(),rejection=None):
    family=_family(task)
    if category not in ATTACKS[family]: raise ValueError('category does not match repair family')
    prior=json.dumps(list(seen_inputs),ensure_ascii=True,separators=(',',':'))
    if len(prior)>2048: raise ValueError('probe history exceeds prompt budget')
    example=(' For records, valid syntax examples are [] or [{\"id\": \"x\", \"value\": 1}].'
             if family=='records' and category=='empty-singleton' else '')
    message=(
        f'Generate exactly one new, valid test input in category /{category}. '
        f'{GUIDANCE[category]}{example} The input must follow the declared JSON input schema '
        'and preconditions. Do not repeat an earlier input or the public example. '
        'Do not copy the task description into input. Return NO_COUNTEREXAMPLE_FOUND '
        'only if this category has no valid test; never invent an oracle or a property.'
        f' Previously tested inputs: {prior}.'
    )
    if rejection:
        if not isinstance(rejection,str) or len(rejection)>240: raise ValueError('invalid schema feedback')
        message+=f' The validator rejected your previous input: {rejection}. Correct the input format and retry the same category.'
    return message
