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
        if data['q']!=_query(request): raise ValueError('cursor belongs to another query/snapshot')
        return data['p']
    except (TypeError,KeyError,UnicodeError) as exc: raise ValueError('invalid cursor') from exc


def _path(snapshot,path):
    if path!='.': _parts(path)
    if path not in snapshot.manifest['entries']: raise ValueError('path not in snapshot')
    return snapshot.root if path=='.' else snapshot.root/path


def _fits_reply(session,reply):
    # Count JSON escaping, receipt and cursor overhead before committing a page.
    rendered=json.dumps(dict(reply,receipt_id='0'*64,output_tokens=1000),ensure_ascii=False)
    counter=getattr(session,'token_counter',lambda s:len(s.encode('utf-8')))
    count=counter(rendered)
    if type(count) is not int or count<0: raise ValueError('invalid tokenizer count')
    # Leave room for tokenizer differences between the placeholder digest/count
    # and the real hexadecimal receipt. Byte accounting is already exact.
    return len(rendered.encode())<=8192 and count<=900


def _view(session,request):
    snap=session.snapshot(request['snapshot_id']);path=_path(snap,request['path'])
    if snap.manifest['entries'][request['path']]['type']!='file': raise ValueError('file required')
    end=request['start_line']+request['line_count']-1
    # Cursor carries byte offset inside long UTF-8 lines, not just a line number.
    position=_position(session,request,None);rows=[];capacity=380
    with path.open('rb') as f:
        if position is None:
            number=1
            while number<request['start_line']:
                chunk=f.readline(65536)
                if not chunk: break
                if chunk.endswith(b'\n'): number+=1
        else:
            offset,number=position;f.seek(offset)
        while number<=end and capacity>8:
            beginning=f.tell()
            raw=f.readline(min(capacity,8192))
            if not raw: break
            if b'\0' in raw: raise ValueError('binary file')
            # Trim only an incomplete trailing UTF-8 code point; invalid interior
            # bytes are rejected. Position always points to a code point boundary.
            try: text=raw.decode('utf-8');used=len(raw)
            except UnicodeDecodeError as error:
                if error.reason!='unexpected end of data' or error.start==0: raise ValueError('invalid UTF-8 file') from error
                used=error.start;text=raw[:used].decode('utf-8');f.seek(used-len(raw),1)
            def preview(length):
                prefix=text[:length];offset=beginning+len(prefix.encode('utf-8'))
                following=number+int(prefix.endswith('\n'))
                cursor=(_cursor(session,request,[offset,following])
                        if following<=end and offset<path.stat().st_size else None)
                return dict(lines=rows+[dict(number=number,text=prefix)],cursor=cursor)
            if not _fits_reply(session,preview(len(text))):
                low,high=0,len(text)
                while low<high:
                    mid=(low+high+1)//2
                    if _fits_reply(session,preview(mid)): low=mid
                    else: high=mid-1
                if not low:
                    f.seek(beginning)
                    if not rows: raise ValueError('metadata exceeds page budget')
                    break
                text=text[:low];used=len(text.encode('utf-8'));f.seek(beginning+used)
                rows.append(dict(number=number,text=text))
                if text.endswith('\n'): number+=1
                break
            rows.append(dict(number=number,text=text))
            capacity-=used+32
            if text.endswith('\n'): number+=1
        offset=f.tell();more=number<=end and offset<path.stat().st_size
    return dict(lines=rows,cursor=_cursor(session,request,[offset,number]) if more else None)


def _search(session,request):
    snap=session.snapshot(request['snapshot_id']);_path(snap,request['path'])
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
    ticket=session.budget.reserve({'tools':1,'output_tokens':1000,'cpu_us':remaining})
    reply=None;candidate_cpu=0;started=time.process_time_ns()
    child_start=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        import jsonschema
        try: jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(request)
        except jsonschema.ValidationError as exc: raise ValueError('invalid tool request') from exc
        tool=request['tool']
        if tool=='file_view': reply=_view(session,request)
        elif tool=='repo_search': reply=_search(session,request)
        elif tool=='patch_apply':
            candidate=session.stage(request['diff'],request['expected_snapshot_id'],request['purpose'])
            reply=dict(candidate_id=candidate.snapshot.id,operation_id=candidate.operation_id,
                       retained=False,claim_status='unknown')
        elif tool=='test_run':
            check=session.checks.get(request['check_id'])
            if check is None or request['probe_id'] is not None:
                raise ValueError('check/probe capability not registered')
            snap=session.snapshot(request['candidate_id'])
            execution=execute_repo(session.base,snap,tuple(check['argv']),limits=check.get('limits',{}),check_artifacts=())
            candidate_cpu=execution['resources']['cpu_us']
            # Full bounded logs remain in supervisor receipts; model gets a small
            # observation reference. Task 4 must interpret/check, never this tool.
            observed=session.receipts.append(dict(event='repoworld.execution',candidate=snap.id,
                        check_id=request['check_id'],observation=execution))
            reply=dict(execution_receipt=observed['sha256'],status=execution['status'],
                       exit_code=execution['exit_code'],claim_status='unknown',task_success=False)
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
        if len(rendered.encode())>8192 or count>1000: raise ValueError('tool output budget exceeded')
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
