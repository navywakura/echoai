"""Scoped public evidence, never an official SWE verdict.

JUnit is structured observation from an untrusted Python process, not a proof.
Protected input files, collection/exit consistency and two baseline runs catch
ordinary tampering and broken environments; arbitrary in-process monkeypatching
of the test framework remains outside this evidence's assurance claim.
"""
import base64
from dataclasses import dataclass, field
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from ..pcworld.receipts import canonical, _atomic_write
from .environment import execute_repo

CATALOG = {
    'astropy/astropy': ('pytest', ['astropy/'], ['astropy/utils/tests/test_misc.py']),
    'django/django': ('django', ['django/'], ['utils_tests.test_datastructures']),
    'matplotlib/matplotlib': ('pytest', ['lib/matplotlib/', 'src/'], ['lib/matplotlib/tests/test_cbook.py']),
    'mwaskom/seaborn': ('pytest', ['seaborn/'], ['tests/test_utils.py']),
    'pallets/flask': ('pytest', ['src/flask/', 'flask/'], ['tests/test_basic.py']),
    'psf/requests': ('pytest', ['requests/', 'src/requests/'], ['test_requests.py']),
    'pydata/xarray': ('pytest', ['xarray/'], ['xarray/tests/test_utils.py']),
    'pylint-dev/pylint': ('pytest', ['pylint/'], ['tests/lint/test_utils.py']),
    'pytest-dev/pytest': ('pytest', ['src/_pytest/', 'src/pytest.py', '_pytest/'], ['testing/test_assertion.py']),
    'scikit-learn/scikit-learn': ('pytest', ['sklearn/'], ['sklearn/utils/tests/test_validation.py']),
    'sphinx-doc/sphinx': ('pytest', ['sphinx/'], ['tests/test_util.py']),
    'sympy/sympy': ('sympy', ['sympy/'], ['sympy/core/tests/test_basic.py']),
}


def catalog_for(repo):
    runner, roots, targets = CATALOG[repo]
    argv = {'pytest': ['/usr/bin/python3', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', '--tb=short', '--junitxml=/work/.out/public.xml'],
            'django': ['/usr/bin/python3', 'tests/runtests.py', '--verbosity', '2', '--settings=test_sqlite', '--parallel', '1'],
            'sympy': ['/usr/bin/python3', 'bin/test', '-C', '--verbose']}[runner]
    return dict(schema='repoworld.public-plan.v1', repo=repo, parser=runner,
                argv=argv, public_targets=list(targets), production_roots=list(roots),
                env={'PYTHONPATH':('/work/lib:' if repo=='matplotlib/matplotlib' else '')+'/work/src:/work:/deps', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'},
                limits={'wall_ms':180000,'cpu_ms':240000,'memory_bytes':4*1024**3,
                        'disk_bytes':1024**3,'pids':128,'output_bytes':1024*1024})


def sanitize_output(value):
    """Tail prioritises the last frame/assertion; bounded UTF-8, no ANSI controls."""
    value=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(value))
    value=''.join(c for c in value if c in '\n\t' or ord(c)>=32)
    lines=value.splitlines()
    # Preserve failure context even when followed by a long summary.
    relevant=[i for i,s in enumerate(lines) if re.search(r'AssertionError|ImportError|ModuleNotFoundError|^E\s|File ".*", line|FAILED|ERROR',s)]
    if relevant:
        end=relevant[-1]+1
        lines=lines[max(0,end-36):end]+lines[-min(4,len(lines)-end):] if end<len(lines) else lines[-40:]
    else: lines=lines[-40:]
    raw='\n'.join(lines[-40:]).encode('utf-8')[-1500:]
    return raw.decode('utf-8','ignore')


def parse_junit(text, *, exit_code, include_skip_reasons=False):
    if isinstance(text, bytes): text=text.decode('utf-8')
    if len(text.encode())>512*1024 or '<!' in text: raise ValueError('unsafe or oversized test report')
    try: root=ET.fromstring(text)
    except ET.ParseError as exc: raise ValueError('malformed test report') from exc
    if root.tag not in ('testsuite','testsuites'): raise ValueError('test report root')
    states={};skip_reasons={}
    for node in root.iter('testcase'):
        name=node.get('classname','')+'::'+node.get('name','')
        if name=='::' or name in states: raise ValueError('missing/duplicate test identity')
        kinds=[s.tag for s in node if s.tag in ('error','failure','skipped')]
        if len(kinds)>1: raise ValueError('contradictory test outcomes')
        states[name]={'error':'ERROR','failure':'FAILED','skipped':'SKIPPED'}.get(kinds[0] if kinds else '', 'PASSED')
        if states[name]=='SKIPPED':
            skip_reasons[name]=node.find('skipped').get('message','')
    if not states: raise ValueError('zero collected tests')
    suites=list(root.iter('testsuite'))
    if not suites or sum(int(s.get('tests','-1')) for s in suites)!=len(states):
        raise ValueError('collection count mismatch')
    failed=any(s in ('FAILED','ERROR') for s in states.values())
    if exit_code != int(failed): raise ValueError('exit contradicts test observations')
    return (states,skip_reasons) if include_skip_reasons else states


def parse_native(text, *, runner, exit_code):
    states={}
    if runner=='django':
        for line in text.splitlines():
            m=re.fullmatch(r'(test\S+) \(([^)]+)\)(?:.*) \.\.\. (ok|FAIL|ERROR|skipped .*)',line.strip())
            if m:
                key=m[2]+'::'+m[1]
                if key in states: raise ValueError('duplicate native identity')
                states[key]='PASSED' if m[3]=='ok' else ('SKIPPED' if m[3].startswith('skipped') else m[3]+'ED' if m[3]=='FAIL' else 'ERROR')
        count=re.findall(r'^Ran (\d+) tests? in ',text,re.M)
        if len(count)!=1 or int(count[0])!=len(states): raise ValueError('native collection mismatch')
    elif runner=='sympy':
        # Verbose bin/test uses a file heading then individual test names.
        filename=None
        for line in text.splitlines():
            heading=re.match(r'^(sympy/\S+\.py)\[',line)
            if heading: filename=heading[1]
            m=re.match(r'^(test\S+) (ok|F|E|s|XFAIL)\b',line.strip())
            if m and filename:
                key=filename+'::'+m[1]
                if key in states: raise ValueError('duplicate native identity')
                states[key]={'ok':'PASSED','F':'FAILED','E':'ERROR','s':'SKIPPED','XFAIL':'XFAIL'}[m[2]]
        counts=re.findall(r'(\d+) passed',text)
        if not counts or int(counts[-1])!=sum(v=='PASSED' for v in states.values()): raise ValueError('native collection mismatch')
    else: raise ValueError('unknown parser')
    if not states or exit_code!=int(any(s in ('ERROR','FAILED') for s in states.values())):
        raise ValueError('invalid native observation/exit')
    return states


def compare_states(before, after):
    return tuple(sorted(k for k,v in before.items() if v in ('PASSED','XFAIL') and after.get(k) not in ('PASSED','XFAIL')))


@dataclass(frozen=True)
class PublicCheckReport:
    candidate_id: str
    check_plan_sha256: str
    states: dict
    evidence_blob_sha256: str
    receipt_id: str
    valid: bool
    summary: str = ''
    cpu_us: int = 0
    skip_reasons: dict = field(default_factory=dict)


def validate_plan(plan):
    allowed={'schema','repo','parser','argv','public_targets','production_roots','env','limits'}
    if plan.get('schema')=='repoworld.public-plan.v2':
        allowed.add('expected_skips')
        skips=plan.get('expected_skips')
        if (type(skips) is not dict or not 1<=len(skips)<=64 or any(
            type(key) is not str or not key.strip() or len(key)>500 or '\0' in key
            or type(reason) is not str or not reason.strip() or len(reason)>500
            for key,reason in skips.items())):
            raise ValueError('public expected skips require exact identities and reasons')
    elif plan.get('schema')!='repoworld.public-plan.v1': raise ValueError('public check plan schema')
    if set(plan)!=allowed: raise ValueError('public check plan fields')
    expected=catalog_for(plan['repo'])
    if plan['argv']!=expected['argv'] or plan['parser']!=expected['parser'] or plan['production_roots']!=expected['production_roots']:
        raise ValueError('runner/catalog mismatch')
    targets=plan['public_targets']
    if (not targets or len(targets)>128
            or any(type(t) is not str or not re.fullmatch(r'[A-Za-z0-9_./:\[\]-]+',t) or t.startswith(('-', '/')) or '..' in t for t in targets)
            or sum(len(t.encode('utf-8')) for t in targets)>16384):
        raise ValueError('invalid supervisor test target')
    if set(plan['env'])-{'PYTHONPATH','PYTHONWARNINGS','PYTEST_DISABLE_PLUGIN_AUTOLOAD','SKLEARN_SITE_JOBLIB'}: raise ValueError('invalid test environment')
    if 'SKLEARN_SITE_JOBLIB' in plan['env'] and (plan['repo']!='scikit-learn/scikit-learn' or plan['env']['SKLEARN_SITE_JOBLIB']!='1'):
        raise ValueError('site joblib requires the explicit sklearn profile')
    return hashlib.sha256(canonical(plan)).hexdigest()


def public_skips_match(states, skip_reasons, check_plan):
    """Match observed skip identities and exact JUnit messages to operator policy."""
    return (type(states) is dict and type(skip_reasons) is dict
            and {name for name,state in states.items() if state=='SKIPPED'}==set(skip_reasons)
            and skip_reasons==check_plan.get('expected_skips',{}))


def baseline_pair_valid(first, second, check_plan):
    """One policy for fresh preflight, protocol startup and checkpoint restore."""
    return (first.valid is True and second.valid is True
            and first.candidate_id==second.candidate_id
            and first.check_plan_sha256==second.check_plan_sha256
            and first.states==second.states and first.skip_reasons==second.skip_reasons
            and public_skips_match(first.states,first.skip_reasons,check_plan)
            and any(state=='PASSED' for state in first.states.values())
            and all(state in ('PASSED','XFAIL','SKIPPED') for state in first.states.values()))


def run_public_checks(base, candidate, check_plan, *, receipts, execute_fn=execute_repo):
    plan_sha=validate_plan(check_plan)
    snapshot=candidate.snapshot if hasattr(candidate,'snapshot') else candidate
    observed=execute_fn(base,snapshot,tuple(check_plan['argv']+check_plan['public_targets']),
                        limits=check_plan['limits'],env=check_plan['env'],
                        check_artifacts=('public.xml',) if check_plan['parser']=='pytest' else ())
    logs=observed.get('stdout','').split('\nREPOWORLD_ARTIFACTS_V1 ',1)[0]+'\n'+observed.get('stderr','')
    states={};skip_reasons={};valid=False;reason='execution not complete'
    if observed.get('status') in ('EXITED','FAILED') and observed.get('isolation',{}).get('job_empty'):
        try:
            if check_plan['parser']=='pytest':
                artifact=observed['artifacts']['public.xml']
                raw=base64.b64decode(artifact['data_b64'],validate=True)
                if hashlib.sha256(raw).hexdigest()!=artifact['sha256']: raise ValueError('artifact hash')
                states,skip_reasons=parse_junit(raw,exit_code=observed['exit_code'],include_skip_reasons=True)
            else: states=parse_native(logs,runner=check_plan['parser'],exit_code=observed['exit_code'])
            # Exact message evidence is required before any arm can retain a
            # candidate. Native parsers cannot authorize skips without reasons.
            if not public_skips_match(states,skip_reasons,check_plan):
                raise ValueError('public skips differ from declared identities/reasons')
            valid=True;reason='scoped public observation'
        except (KeyError,ValueError,ET.ParseError) as exc: reason=str(exc)
    evidence=hashlib.sha256(canonical(observed)).hexdigest()
    receipt=receipts.append(dict(event='repoworld.public-check',candidate=snapshot.id,check_plan_sha256=plan_sha,
        evidence_blob_sha256=evidence,observation=observed,states=states,skip_reasons=skip_reasons,
        valid=valid,reason=reason,scope='public',task_success=False))
    return PublicCheckReport(snapshot.id,plan_sha,states,evidence,receipt['sha256'],valid,
                             sanitize_output(reason+'\n'+logs),observed['resources']['cpu_us'],skip_reasons)


def collect_public_baseline(base, check_plan, *, receipts, execute_fn=execute_repo):
    first=run_public_checks(base,base.snapshot,check_plan,receipts=receipts,execute_fn=execute_fn)
    second=run_public_checks(base,base.snapshot,check_plan,receipts=receipts,execute_fn=execute_fn)
    expected=check_plan.get('expected_skips',{})
    valid=baseline_pair_valid(first,second,check_plan)
    r=receipts.append(dict(event='repoworld.public-baseline',candidate=base.snapshot.id,
        check_plan_sha256=first.check_plan_sha256,runs=[first.receipt_id,second.receipt_id],valid=valid,
        states=second.states,skip_reasons=second.skip_reasons,expected_public_skips=expected,scope='public',
        reason=('two identical public runs; declared skips remain uncovered' if expected else 'two identical passing runs') if valid else 'invalid/failing/flaky baseline'))
    return PublicCheckReport(base.snapshot.id,first.check_plan_sha256,second.states,
        second.evidence_blob_sha256,r['sha256'],valid,second.summary,first.cpu_us+second.cpu_us,second.skip_reasons)


def public_regressions(before, after):
    if not before.valid or before.check_plan_sha256!=after.check_plan_sha256: raise ValueError('baseline/check plan mismatch')
    return compare_states(before.states,after.states)


def decide_candidate(workspace,candidate,baseline,after,*,guard=True):
    """Stage does not advance head: rollback is refusal to commit the transaction."""
    regressions=public_regressions(baseline,after)
    status='PUBLIC_REGRESSION' if regressions else ('PUBLIC_CHECKS_PASSED' if after.valid else 'PUBLIC_CHECKS_UNKNOWN')
    decision=workspace.receipts.append(dict(event='repoworld.public-decision',candidate=candidate.snapshot.id,
        status=status,regressions=list(regressions),guard=guard,check_receipt=after.receipt_id,baseline_receipt=baseline.receipt_id,
        retain=after.valid and (not regressions or not guard),task_success=False))
    # Evidence permitting retention is explicit supervisor policy; no claim of
    # issue correctness. Guard-off retains observed regressions as the ablation.
    if after.valid and (not regressions or not guard):
        prop=workspace.receipts.append(dict(event='repoworld.public-property',candidate=candidate.snapshot.id,
            scope='public',property_status='supported',property='eligible-under-declared-public-guard',
            decision_receipt=decision['sha256']))
        workspace.retain(candidate,expected_head=workspace.current.id,public_receipt_ids=[prop['sha256']])
    return dict(status=status,regressions=list(regressions),retained=workspace.current.id==candidate.snapshot.id,
                receipt_id=decision['sha256'],summary=after.summary)
