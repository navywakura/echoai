"""Bounded four-tool dispatcher. No tool accepts executable shell or host paths.

Default output accounting is a conservative UTF-8-byte token upper bound;
production may inject the fixed model tokenizer. Neither is a claim of measured
LLM inference. All tools share PCWorld Budget and ReceiptStore.
"""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import selectors
import resource
import subprocess
import time
from ..pcworld.receipts import canonical
from ..pcworld.snapshots import _parts
from .environment import execute_repo

SCHEMA=Path(__file__).resolve().parents[1]/'ECHO-5.1/docs/swebench/SWE-TOOLS.schema.json'


def _query(request):
    return hashlib.sha256(canonical({k:v for k,v in request.items() if k!='cursor'})).hexdigest()


def _cursor(session,request,position):
    raw=canonical(dict(q=_query(request),p=position))
    payload=base64.urlsafe_b64encode(raw).decode().rstrip('=')
    mac=hmac.new((session.directory/'cursor.key').read_bytes(),payload.encode(),'sha256').hexdigest()
    token=payload+'.'+mac
    if len(token)>256: raise ValueError('cursor capacity exceeded')
    return token


def _position(session,request,default):
    token=request.get('cursor')
    if token is None: return default
    try:
        payload,mac=token.split('.')
        expected=hmac.new((session.directory/'cursor.key').read_bytes(),payload.encode(),'sha256').hexdigest()
        if not hmac.compare_digest(mac,expected): raise ValueError('cursor authentication failed')
        data=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
        if data['q']!=_query(request):
            session.receipts.append(dict(event='repoworld.cursor-reset',
                tool=request['tool'],request_sha256=_query(request),
                reason='authenticated cursor belongs to another query/snapshot'))
            return default
        return data['p']
    except (TypeError,KeyError,UnicodeError) as exc: raise ValueError('invalid cursor') from exc


def _path(snapshot,path):
    if path!='.': _parts(path)
    if path not in snapshot.manifest['entries']: raise ValueError('path not in snapshot')
    return snapshot.root if path=='.' else snapshot.root/path


FILE_VIEW_SOURCE_BYTES=2500
FILE_VIEW_OUTPUT_UNITS=6000


def _fits_reply(session,reply,*,output_limit=1000):
    # Count JSON escaping, receipt and cursor overhead before committing a page.
    rendered=json.dumps(dict(reply,receipt_id='0'*64,output_tokens=output_limit),ensure_ascii=False)
    counter=getattr(session,'token_counter',lambda s:len(s.encode('utf-8')))
    count=counter(rendered)
    if type(count) is not int or count<0: raise ValueError('invalid tokenizer count')
    # Leave room for tokenizer differences between the placeholder digest/count
    # and the real hexadecimal receipt. Byte accounting is already exact.
    return len(rendered.encode())<=8192 and count<=output_limit-100


def _view(session,request):
    snap=session.snapshot(request['snapshot_id']);path=_path(snap,request['path'])
    if snap.manifest['entries'][request['path']]['type']!='file': raise ValueError('file required')
    end=request['start_line']+request['line_count']-1
    # Cursors only point at complete-line boundaries. Never return a fragment
    # as though it were an entire source line.
    position=_position(session,request,None);rows=[];used=0
    with path.open('rb') as f:
        if position is None:
            number=1
            while number<request['start_line']:
                chunk=f.readline(65536)
                if not chunk: break
                if chunk.endswith(b'\n'): number+=1
        else:
            offset,number=position;f.seek(offset)
            if offset:
                f.seek(offset-1)
                if f.read(1)!=b'\n': raise ValueError('cursor is not a complete-line boundary')
                f.seek(offset)
        while number<=end:
            beginning=f.tell();raw=f.readline(FILE_VIEW_SOURCE_BYTES+1)
            if not raw: break
            if b'\0' in raw: raise ValueError('binary file')
            if len(raw)>FILE_VIEW_SOURCE_BYTES:
                f.seek(beginning)
                if rows: break
                raise ValueError(f'complete line {number} exceeds page budget; request a later start_line explicitly')
            try: text=raw.decode('utf-8')
            except UnicodeDecodeError as error: raise ValueError('invalid UTF-8 file') from error
            following=number+1;offset=f.tell()
            candidate=dict(lines=rows+[dict(number=number,text=text)],
                cursor=_cursor(session,request,[offset,following]) if following<=end and offset<path.stat().st_size else None)
            if used+len(raw)>FILE_VIEW_SOURCE_BYTES or not _fits_reply(session,candidate,output_limit=FILE_VIEW_OUTPUT_UNITS):
                f.seek(beginning)
                if not rows: raise ValueError(f'complete line {number} exceeds encoded page budget; request a later start_line explicitly')
                break
            rows.append(dict(number=number,text=text));used+=len(raw);number=following
        offset=f.tell();more=number<=end and offset<path.stat().st_size
    return dict(lines=rows,cursor=_cursor(session,request,[offset,number]) if more else None)


def _outline(session,request):
    from .source_evidence import file_bytes,parse_symbols
    raw=file_bytes(session,request['snapshot_id'],request['path'])
    symbols=parse_symbols(raw);name=request.get('class_name')
    if name:symbols=[x for x in symbols if x['symbol']==name or x['symbol'].startswith(name+'.')]
    offset=_position(session,request,0)
    if type(offset) is not int or not 0<=offset<=len(symbols):raise ValueError('invalid outline offset')
    rows=[];reply=dict(path=request['path'],file_sha256=hashlib.sha256(raw).hexdigest(),symbols=[],cursor=None)
    for row in symbols[offset:]:
        next_offset=offset+len(rows)+1
        candidate={**reply,'symbols':rows+[row],'cursor':_cursor(session,request,next_offset) if next_offset<len(symbols) else None}
        if not _fits_reply(session,candidate,output_limit=FILE_VIEW_OUTPUT_UNITS):break
        rows.append(row);reply=candidate
    if offset<len(symbols) and not rows:raise ValueError('outline symbol exceeds page budget')
    session.receipts.append(dict(event='repoworld.outline-observation',snapshot=request['snapshot_id'],**reply))
    return reply


def _search_request(session,request,snap):
    """Normalize directory spelling only; never resolve traversal or symlinks."""
    original=request['path'];path=original.strip()
    hint=('SEARCH_PATH_INVALID: use a relative repository path, e.g. '
          'repo_search(path="sympy/matrices/expressions", pattern="BlockMatrix"), '
          'or path="." for the repository root. Absolute paths, .., internal empty/dot '
          'segments, NUL, backslashes and symlink targets are not accepted.')
    # Check BEFORE rstrip: '/' must never become the repository root.
    if path.startswith('/') or '\0' in path or '\\' in path:raise ValueError(hint)
    path=path.rstrip('/') or '.'
    try:
        if path!='.':_parts(path)
    except ValueError as error:raise ValueError(hint) from error
    entry=snap.manifest['entries'].get(path)
    if entry is None:
        raise ValueError('SEARCH_PATH_NOT_FOUND: relative path absent from snapshot; '
                         'use repo_search(path=".", pattern=...) to locate it.')
    if entry['type'] not in ('file','directory') or (original.strip().endswith('/') and entry['type']!='directory'):
        raise ValueError(hint)
    normalized={**request,'path':path}
    session.receipts.append(dict(event='repoworld.search-path',snapshot=snap.id,
        original_path=original,canonical_path=path,
        request_sha256=_query(request),canonical_request_sha256=_query(normalized)))
    return normalized


def _search(session,request):
    snap=session.snapshot(request['snapshot_id'])
    request=_search_request(session,request,snap)
    _path(snap,request['path'])
    skip=_position(session,request,0)
    if type(skip) is not int or not 0<=skip<=100000: raise ValueError('invalid search offset')
    if any(c in request['pattern'] for c in ('\n','\r','\0')): raise ValueError('single-line literal required')
    argv=['/usr/bin/rg','--no-config','--color','never','--fixed-strings','--line-number',
          '--with-filename','--only-matching','--no-heading','--no-ignore','--hidden',
          '--sort','path','--null','--',request['pattern'],request['path']]
    rows=[];count=0;more=False;size=0;deadline=time.monotonic()+2;buffer=b''
    proc=subprocess.Popen(argv,cwd=snap.root,env={'PATH':'/usr/bin:/bin','LC_ALL':'C.UTF-8'},
                          stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
    try:
        while True:
            if time.monotonic()>deadline: raise ValueError('search time budget exhausted')
            ready=selector.select(.03)
            if not ready:
                if proc.poll() is not None: break
                continue
            chunk=os.read(proc.stdout.fileno(),8192)
            if not chunk: break
            buffer+=chunk
            if len(buffer)>32768: raise ValueError('search record exceeds limit')
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1)
                count+=1
                if count<=skip: continue
                name,rest=line.decode('utf-8').split('\0',1);num,match=rest.split(':',1)
                if name.startswith('./'): name=name[2:]
                row=dict(path=name,line=int(num),match=match)
                cost=len(json.dumps(row,ensure_ascii=False).encode())
                if len(rows)>=30 or size+cost>380:
                    more=True;break
                if name not in snap.manifest['entries']: raise ValueError('unexpected search path')
                rows.append(row);size+=cost
            if more: break
        if proc.poll() not in (None,0,1): raise ValueError('search failed')
    finally:
        selector.close()
        if proc.poll() is None: proc.kill()
        proc.wait(timeout=2);proc.stdout.close()
    if more and not rows: raise ValueError('search record exceeds output budget; narrow the query')
    return dict(matches=rows,cursor=_cursor(session,request,skip+len(rows)) if more else None)


def dispatch_tool(request: dict,*,session):
    # Reservations happen before validation, including failed/forged requests.
    remaining=session.budget.report()['remaining'].get('cpu_us',0)
    output_limit=FILE_VIEW_OUTPUT_UNITS if request.get('tool') in ('file_view','file_outline') else 1000
    ticket=session.budget.reserve({'tools':1,'output_tokens':output_limit,'cpu_us':remaining})
    reply=None;candidate_cpu=0;started=time.process_time_ns()
    child_start=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        import jsonschema
        try: jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(request)
        except jsonschema.ValidationError as exc: raise ValueError('invalid tool request') from exc
        tool=request['tool']
        if tool=='file_view':
            reply=_view(session,request)
            from .source_evidence import record_view
            record_view(session,request,reply)
        elif tool=='file_outline':reply=_outline(session,request)
        elif tool=='repo_search': reply=_search(session,request)
        elif tool=='patch_apply':
            if request['purpose']=='probe':
                if request['expected_snapshot_id']!=session.current.id:raise ValueError('STALE_BASE')
                from .workspace import stage_probe
                reply=dict(probe_id=stage_probe(session,request['diff']),retained=False,claim_status='unknown')
            else:
                if 'search' in request:
                    from .workspace import search_replace_diff
                    diff=search_replace_diff(session,request['path'],request['search'],request['replace'],request['expected_snapshot_id'])
                else:diff=request['diff']
                candidate=session.stage(diff,request['expected_snapshot_id'],request['purpose'])
                reply=dict(candidate_id=candidate.snapshot.id,operation_id=candidate.operation_id,
                           retained=False,claim_status='unknown')
        elif tool=='test_run':
            check=session.checks.get(request['check_id'])
            probe=None
            if request['probe_id'] is not None:
                probe=next((r['body'] for r in session.receipts.records if r['body'].get('event')=='repoworld.probe-proposal' and r['body']['probe_id']==request['probe_id']),None)
            if check is None or (request['probe_id'] is not None and probe is None):
                raise ValueError('check/probe capability not registered')
            snap=session.snapshot(request['candidate_id'])
            argv=('/usr/bin/python3','/runner/probe.py') if probe else tuple(check['argv'])
            execution=execute_repo(session.base,snap,argv,limits=check.get('limits',{}),env=check.get('env'),
                                   check_artifacts=(),probe_source=probe['source'] if probe else None)
            candidate_cpu=execution['resources']['cpu_us']
            # Full bounded logs remain in supervisor receipts; model gets a small
            # observation reference. Task 4 must interpret/check, never this tool.
            observed=session.receipts.append(dict(event='repoworld.execution',candidate=snap.id,
                        check_id=request['check_id'],observation=execution))
            reply=dict(execution_receipt=observed['sha256'],status=execution['status'],
                       exit_code=execution['exit_code'],claim_status='unknown',task_success=False)
            from .checks import sanitize_output
            reply['summary']=sanitize_output(execution['stdout']+'\n'+execution['stderr'])
            # Preserve the trace/exception under both byte and tool-envelope caps.
            while not _fits_reply(session,reply) and reply['summary']:
                reply['summary']=reply['summary'][len(reply['summary'])//4+1:]
        receipt=session.receipts.append(dict(event='repoworld.tool',request_sha256=hashlib.sha256(canonical(request)).hexdigest(),
                        tool=tool,response_sha256=hashlib.sha256(canonical(reply)).hexdigest()))
        reply['receipt_id']=receipt['sha256'];reply['output_tokens']=0
        counter=getattr(session,'token_counter',lambda s:len(s.encode('utf-8')))
        for _ in range(4):
            rendered=json.dumps(reply,ensure_ascii=False)
            count=counter(rendered)
            if type(count) is not int or count<0: raise ValueError('invalid tokenizer count')
            if count==reply['output_tokens']: break
            reply['output_tokens']=count
        if len(rendered.encode())>8192 or count>output_limit: raise ValueError('tool output budget exceeded')
        return reply
    except Exception as error:
        try: request_hash=hashlib.sha256(canonical(request)).hexdigest()
        except (ValueError,TypeError): request_hash=None
        session.receipts.append(dict(event='repoworld.tool-error',request_sha256=request_hash,
                                     error_type=type(error).__name__,claim_status='unknown'))
        raise
    finally:
        children=resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu=int(((children.ru_utime+children.ru_stime)-(child_start.ru_utime+child_start.ru_stime))*1000000)
        cpu_us=(time.process_time_ns()-started)//1000+max(0,child_cpu)+candidate_cpu
        session.budget.settle(ticket,{'tools':1,'output_tokens':reply.get('output_tokens',0) if reply else 0,'cpu_us':cpu_us})
