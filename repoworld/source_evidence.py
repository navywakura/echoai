"""Receipt-derived source knowledge, not another authority or truth lattice.

Views are reusable only for identical file bytes. Public check results remain
scoped to their candidate/check/environment; they are not source observations.
"""
import hashlib
import json
import subprocess
import sys

MAX_SOURCE_BYTES=1024*1024
PARSER = r'''
import ast,json,resource,sys
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
source=sys.stdin.buffer.read(1024*1024+1)
if len(source)>1024*1024: raise ValueError('source size limit')
tree=ast.parse(source.decode('utf-8'))
rows=[]
def visit(node,prefix=''):
 for child in ast.iter_child_nodes(node):
  if isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
   symbol=prefix+child.name
   rows.append(dict(symbol=symbol,kind='class' if isinstance(child,ast.ClassDef) else 'function',start=min([child.lineno]+[d.lineno for d in child.decorator_list]),end=child.end_lineno))
   visit(child,symbol+'.')
  else:visit(child,prefix)
visit(tree)
print(json.dumps(rows,separators=(',',':')))
'''

def parse_symbols(raw):
    if len(raw)>MAX_SOURCE_BYTES:raise ValueError('source size limit')
    try:
        result=subprocess.run([sys.executable,'-I','-c',PARSER],input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=3)
    except subprocess.TimeoutExpired as exc:raise ValueError('AST time limit') from exc
    if result.returncode:raise ValueError('AST_SYNTAX_OR_RESOURCE_ERROR')
    return json.loads(result.stdout)

def file_bytes(session,snapshot,path):
    from .tools import _path
    snap=session.snapshot(snapshot);_path(snap,path)
    if snap.manifest['entries'][path]['type']!='file':raise ValueError('regular source file required')
    if (snap.root/path).stat().st_size>MAX_SOURCE_BYTES:raise ValueError('source size limit')
    raw=session.store.read(snap,path)
    if len(raw)>MAX_SOURCE_BYTES:raise ValueError('source size limit')
    raw.decode('utf-8')
    return raw

def record_view(session,request,reply):
    raw=file_bytes(session,request['snapshot_id'],request['path'])
    existing=observed_lines(session,request['path'],raw)
    is_redundant=bool(existing and reply.get('lines') and all(x['number'] in existing for x in reply['lines']))
    reply['redundant']=is_redundant
    return session.receipts.append(dict(event='repoworld.source-observation',path=request['path'],
        snapshot=request['snapshot_id'],file_sha256=hashlib.sha256(raw).hexdigest(),lines=reply['lines'],redundant=is_redundant))

def observed_lines(session,path,raw):
    digest=hashlib.sha256(raw).hexdigest();lines={}
    # ReceiptStore authenticates complete bodies on load; the model cannot append.
    for row in session.receipts.records:
        b=row['body']
        if b.get('event')!='repoworld.source-observation' or b['path']!=path or b['file_sha256']!=digest:continue
        for line in b['lines']:
            n=line['number'];text=line['text']
            if n in lines and lines[n]!=text:raise ValueError('conflicting source evidence')
            lines[n]=text
    return lines

def projection(session,max_bytes=6000):
    """Whole-line bounded pin of most recently observed current-content file."""
    for row in reversed(session.receipts.records):
        b=row['body']
        if b.get('event')!='repoworld.source-observation':continue
        path=b['path']
        if session.current.manifest['entries'].get(path,{}).get('type')!='file':continue
        raw=file_bytes(session,session.current.id,path)
        if hashlib.sha256(raw).hexdigest()!=b['file_sha256']:continue
        lines=observed_lines(session,path,raw);selected=[];size=0
        # Most recent window first, without duplicate overlap or partial lines.
        order=[x['number'] for x in b['lines']]+[n for n in sorted(lines) if n not in {x['number'] for x in b['lines']}]
        for n in order:
            cost=len(json.dumps(dict(number=n,text=lines[n]),ensure_ascii=False).encode())
            if size+cost>max_bytes:break
            selected.append(dict(number=n,text=lines[n]));size+=cost
        return dict(path=path,file_sha256=b['file_sha256'],lines=sorted(selected,key=lambda x:x['number']),coverage_count=len(lines),receipt_id=row['sha256'])
    return None
