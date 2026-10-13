"""Bounded adversarial probe categories and evidence-aware E routing.

This is an explicit symbolic policy, not a learned critic or a claim that CAM
discovers bug classes by itself. CAM supplies the seen-probe history; E uses
that history and visible source cues to choose an untested category.
"""
import ast
import hashlib
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

EXTRA_CATEGORIES={
    'intervals':('disjoint-intervals','extreme-endpoints'),
    'records':('unique-keys','extreme-values'),
    'path':('plain-components','root-only'),
    'csv':('single-field','empty-fields'),
    'pagination':('in-range','extreme-items'),
    'dependencies':('linear-chain','edgeless'),
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
    'disjoint-intervals':'Use at least two intervals separated by strict gaps; no touching or overlapping endpoints.',
    'extreme-endpoints':'Use at least one interval endpoint exactly -10000 or 10000, inside the declared domain.',
    'unique-keys':'Use at least two records with distinct ids; no repeated id.',
    'extreme-values':'Use at least one record value exactly -10000 or 10000; valid ids and value fields only.',
    'plain-components':'Use an absolute path of nonempty lowercase-letter components only; no dots, repeated slashes or trailing slash.',
    'root-only':'Use exactly the absolute root path string "/".',
    'single-field':'Use a valid CSV record decoding to exactly one field.',
    'empty-fields':'Use a valid CSV record containing at least one empty field.',
    'in-range':'Use a nonempty item list and positive limit, with offset >= 0 and offset + limit <= item count.',
    'extreme-items':'Use at least one item exactly -10000 or 10000 and valid offset and limit.',
    'linear-chain':'Use at least two nodes connected as a single directed chain covering every node, without cycles or repeated edges.',
    'edgeless':'Use at least two distinct nodes and an empty edges list.',
    'reverse-alphabetical-edges':'Use an acyclic graph with at least one edge [before, after] where before is lexicographically greater than after. The input object has nodes and edges fields, never deps. Choose node labels whose dependency order contradicts alphabetic sorting.',
}

def _family(task):
    prop=task.get('property','')
    if not isinstance(prop,str) or not prop.startswith('repair.'):
        raise ValueError('adversarial routing requires a repair task')
    family=prop.split('.',1)[1]
    if family not in ATTACKS: raise ValueError('unknown repair family')
    return family

def categories_for(task):
    family=_family(task);catalog=task.get('probe_catalog','legacy-v1')
    if catalog not in ('legacy-v1','expanded-v1','expanded-v2'): raise ValueError('unknown probe catalog')
    extra=EXTRA_CATEGORIES[family] if catalog!='legacy-v1' else ()
    reverse=('reverse-alphabetical-edges',) if catalog=='expanded-v2' and family=='dependencies' else ()
    return ATTACKS[family]+extra+reverse

def fixed_order(task):
    """Precommitted permutation, independent of candidate, oracle and bug labels."""
    categories=categories_for(task)
    if task.get('probe_catalog','legacy-v1')=='legacy-v1':return FIXED_ORDER[_family(task)]
    seed=task.get('probe_order_seed')
    if type(seed) is not int or not 0<=seed<=2**31-1:raise ValueError('invalid probe order seed')
    identity=task.get('id')
    if not isinstance(identity,str) or not identity:raise ValueError('task identity required')
    return tuple(sorted(categories,key=lambda category:hashlib.sha256(
        json.dumps([seed,identity,category],separators=(',',':')).encode()).digest()))

def source_risks(task,source):
    """Auditable AST cues, not bug proofs or learned category probabilities."""
    family=_family(task)
    try:nodes=list(ast.walk(ast.parse(source)))
    except (SyntaxError,ValueError,RecursionError):return ()
    constants={n.value for n in nodes if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    split=any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='split'
              for n in nodes)
    cues={
        'intervals':('touching-endpoints' if any(isinstance(n,ast.Lt) for n in nodes) else None),
        'records':('duplicate-keys' if any(isinstance(n,ast.DictComp) for n in nodes) else None),
        'path':('dotdot-cancellation' if split and '..' not in constants else None),
        'csv':('quoted-delimiter' if split and ',' in constants else None),
        'pagination':('negative-bounds' if 'offset' in constants and any(isinstance(n,ast.Slice) for n in nodes) else None),
        'dependencies':('self-and-multinode-cycles' if 'nodes' in constants and
                        any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sorted'
                            for n in nodes) else None),
    }
    if family=='dependencies' and task.get('probe_catalog')=='expanded-v2':
        sort_call=any(isinstance(n,ast.Call) and
                      ((isinstance(n.func,ast.Name) and n.func.id=='sorted') or
                       (isinstance(n.func,ast.Attribute) and n.func.attr=='sort')) for n in nodes)
        if sort_call:return ('reverse-alphabetical-edges',)
    return (cues[family],) if cues[family] else ()

def choose_category(arm,task,source,seen):
    """Choose a fixed category for F or rank unseen source risks for E."""
    family=_family(task);ordered=ATTACKS[family]
    if arm not in ('F','E'): raise ValueError('only critic arms route adversarial probes')
    seen=set(seen)
    if task.get('probe_catalog','legacy-v1')!='legacy-v1':
        ordered=fixed_order(task)
        priorities=source_risks(task,source) if arm=='E' else ()
        return next((c for c in (*priorities,*ordered) if c not in seen),None)
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
    if category not in categories_for(task): return False
    from .repairs import repair_domain
    if not repair_domain(task['property'],value): return False
    if category=='disjoint-intervals':
        ordered=sorted(value)
        return len(ordered)>=2 and all(a[1]<b[0] for a,b in zip(ordered,ordered[1:]))
    if category=='extreme-endpoints':return any(abs(v)==10000 for pair in value for v in pair)
    if category=='unique-keys':return len(value)>=2 and len({r['id'] for r in value})==len(value)
    if category=='extreme-values':return any(abs(r['value'])==10000 for r in value)
    if category=='plain-components':return bool(__import__('re').fullmatch(r'/[a-z]+(?:/[a-z]+)*',value))
    if category=='root-only':return value=='/'
    if category in ('single-field','empty-fields'):
        import csv,io
        fields=next(csv.reader(io.StringIO(value,newline=''),strict=True))
        return len(fields)==1 if category=='single-field' else '' in fields
    if category=='in-range':return value['offset']>=0 and value['limit']>0 and value['offset']+value['limit']<=len(value['items'])
    if category=='extreme-items':return any(abs(v)==10000 for v in value['items'])
    if category=='reverse-alphabetical-edges':
        if not any(x>y for x,y in value['edges']):return False
        # A reverse edge in a cycle tests cycle detection, not topological order.
        graph={n:set() for n in value['nodes']}
        incoming={n:0 for n in graph}
        for x,y in value['edges']:
            if y not in graph[x]:graph[x].add(y);incoming[y]+=1
        ready=[n for n in graph if incoming[n]==0];visited=0
        while ready:
            n=ready.pop();visited+=1
            for child in graph[n]:
                incoming[child]-=1
                if incoming[child]==0:ready.append(child)
        return visited==len(graph)
    if category=='edgeless':return len(value['nodes'])>=2 and not value['edges']
    if category=='linear-chain':
        nodes=value['nodes'];edges=value['edges']
        if len(nodes)<2 or len(edges)!=len(nodes)-1 or len(set(map(tuple,edges)))!=len(edges):return False
        incoming={n:0 for n in nodes};outgoing={n:[] for n in nodes}
        for x,y in edges:incoming[y]+=1;outgoing[x].append(y)
        starts=[n for n in nodes if incoming[n]==0]
        if len(starts)!=1 or any(v>1 for v in incoming.values()) or any(len(v)>1 for v in outgoing.values()):return False
        seen=set();current=starts[0]
        while current not in seen:
            seen.add(current)
            if not outgoing[current]:break
            current=outgoing[current][0]
        return len(seen)==len(nodes)
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
    if category not in categories_for(task): raise ValueError('category does not match repair family')
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


def audit_probe_records(task,arm,records,source_for):
    """Replay category metadata using authenticated records; never run candidates.

    Property semantics and snapshot custody are independently replayed by the
    caller. This adds eligibility, selection order and per-category call limits.
    """
    if task.get('probe_catalog') not in ('expanded-v1','expanded-v2'):return []
    errors=[];seen={};attempts={};properties=[];sources={};proposals={};prior={};results=[]
    for record in records:
        b=record['body'];snapshot=b.get('snapshot');category=b.get('category')
        if b.get('kind')=='property' and 'property' in b:
            properties.append(b['property'])
        if b.get('role')=='critic' and 'probe' in b:
            probe=b['probe'];category=probe.get('category');attempt=probe.get('attempt')
            key=(snapshot,category);n=attempts.get(key,0)
            if type(attempt) is not int or attempt!=n or n>=3:
                errors.append('critic category retry limit or sequence differs')
            if category not in categories_for(task):errors.append('unknown critic category')
            if n==0:
                if snapshot not in sources:sources[snapshot]=source_for(snapshot)
                expected=choose_category(arm,task,sources[snapshot],seen.get(snapshot,set()))
                if category!=expected:errors.append('critic selection differs from fixed or AST policy')
            attempts[key]=n+1
            proposals[key]=b
        if b.get('operation') in ('probe_result','critic_probe'):
            seen.setdefault(snapshot,set()).add(category)
        if b.get('operation')=='probe_result':
            if not matches_category(task,category,b.get('input')):
                errors.append('probe category does not match observed input')
            if not any(p.get('snapshot')==snapshot and p.get('input')==b.get('input')
                       and p.get('status')==b.get('status') for p in properties):
                errors.append('probe result lacks prior property evidence')
            if 'replay_of' in b:
                original=prior.get(b['replay_of'],{})
                if (original.get('operation')!='probe_result' or original.get('category')!=category
                        or original.get('input')!=b.get('input')):
                    errors.append('probe replay does not identify its original challenge')
            else:
                from .verifier import validate_challenge
                proposal=proposals.pop((snapshot,category),{})
                payload=proposal.get('payload',{})
                if (not isinstance(payload,dict) or payload.get('input')!=b.get('input')
                        or validate_challenge(task['property'],payload).get('status')!='eligible'):
                    errors.append('probe result lacks originating eligible critic proposal')
                used=list(task.get('public_inputs',[]))+[r.get('input') for r in results
                    if r.get('snapshot')==snapshot or r.get('status')=='contradicted']
                if b.get('input') in used:errors.append('probe reuses an already known input')
            results.append(b)
        if record.get('sha256'):prior[record['sha256']]=b
    return errors
