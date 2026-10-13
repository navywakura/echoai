"""Strict patches and crash-recoverable retention above PCWorld snapshots/receipts.

Staging is not acceptance. Only supervisor-issued PUBLIC property receipts may
retain a candidate; neither tool stdout nor a candidate's own success string
can authorize retention. This is transaction infrastructure, not task closure.
"""
from contextlib import contextmanager
from dataclasses import asdict
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from ..pcworld.accounting import Budget
from ..pcworld.receipts import ReceiptStore, canonical, _atomic_write
from ..pcworld.snapshots import _parts
from .environment import repo_store
from .types import PatchCandidate, RepoBase, PublicTask, EnvironmentRef

PROTECTED = {'.git','.echoai','.github','tests','test','testing','__pycache__',
             'conftest.py','pytest.ini','tox.ini','.repoworld-probes'}
PROPOSAL_LIMITS = (65536, 8, 800)
# Final export can contain eight proposals; a per-call limit is not a run limit.
EXPORT_LIMITS = (8*65536, 64, 6400)


def _allowed(path):
    parts=_parts(path)
    if any(p in PROTECTED or p.startswith('test_') or p.endswith('_test.py') for p in parts):
        raise ValueError('protected public checks/configuration path')
    if any(ord(c)<32 for c in path) or len(path.encode())>512:
        raise ValueError('unsupported patch path')
    return path


def production_path(repo,path):
    _allowed(path)
    from .checks import CATALOG
    if repo in CATALOG:
        roots=CATALOG[repo][1]
        if not any(path.startswith(p) if p.endswith('/') else path==p for p in roots):
            raise ValueError('only declared production source paths may be patched')
    return True


def protected_paths(entries):
    result=[]
    for path in sorted(entries,key=lambda s:(len(s.split('/')),s)):
        if path=='.' or any(path==p or path.startswith(p+'/') for p in result): continue
        try: _allowed(path)
        except ValueError: result.append(path)
    return result


def _parse_diff(store,current,diff,*,limits=PROPOSAL_LIMITS,probe=False):
    max_bytes,max_files,max_lines=limits
    if type(diff) is not str or not diff or len(diff.encode('utf-8'))>max_bytes or '\0' in diff:
        raise ValueError('invalid or oversized text diff')
    lines=diff.splitlines(keepends=True);i=0;edits=[];seen=set();changed=0
    while i<len(lines):
        # Git's two harmless informational headers; mode/rename/binary headers
        # are intentionally unsupported, rather than interpreted permissively.
        if lines[i].startswith('diff --git '): i+=1
        if i<len(lines) and re.fullmatch(r'index [0-9a-f]+\.\.[0-9a-f]+(?: 100(?:644|755))?\n',lines[i]): i+=1
        if i+1>=len(lines) or not lines[i].startswith('--- ') or not lines[i+1].startswith('+++ '):
            raise ValueError('strict unified diff headers required')
        old=lines[i][4:].rstrip('\n');new=lines[i+1][4:].rstrip('\n');i+=2
        if old!='/dev/null' and not old.startswith('a/'): raise ValueError('old path prefix')
        if new!='/dev/null' and not new.startswith('b/'): raise ValueError('new path prefix')
        path=(new if old=='/dev/null' else old)[2:]
        if probe:
            if old!='/dev/null' or not re.fullmatch(r'\.repoworld-probes/[A-Za-z0-9_-]{1,64}\.py',path):raise ValueError('probe must create an isolated Python test')
        else:path=_allowed(path)
        if old!='/dev/null' and new!='/dev/null' and old[2:]!=new[2:]: raise ValueError('renames unsupported')
        if path in seen or len(seen)>=max_files: raise ValueError('duplicate/excess patch files')
        seen.add(path);entry=current.manifest['entries'].get(path)
        if old=='/dev/null':
            if entry is not None: raise ValueError('creation exists')
            before=[];expected=None
        else:
            if entry is None or entry['type']!='file' or entry['size']>4*1024*1024: raise ValueError('missing/oversized text target')
            raw=store.read(current,path)
            if b'\0' in raw: raise ValueError('binary target')
            before=raw.decode('utf-8').splitlines(keepends=True);expected=entry['sha256']
        result=[];old_at=0;hunks=0
        while i<len(lines) and lines[i].startswith('@@ '):
            header=re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n',lines[i])
            if not header: raise ValueError('invalid hunk header')
            os_,oc,ns,nc=(int(v) if v is not None else 1 for v in header.groups())
            start=os_-1 if oc else os_
            if start<old_at or start>len(before): raise ValueError('invalid hunk position')
            result.extend(before[old_at:start]);old_at=start
            target_start=ns-1 if nc else ns
            if target_start!=len(result): raise ValueError('new hunk position mismatch')
            i+=1;used_old=used_new=0
            while used_old<oc or used_new<nc:
                if i>=len(lines) or lines[i][:1] not in (' ','+','-'): raise ValueError('truncated hunk')
                op=lines[i][0];text=lines[i][1:];i+=1
                if i<len(lines) and lines[i].startswith('\\ No newline at end of file'):
                    if not text.endswith('\n'): raise ValueError('invalid newline marker')
                    text=text[:-1];i+=1
                if op in (' ','-'):
                    if old_at>=len(before) or before[old_at]!=text: raise ValueError('hunk context mismatch (no fuzz)')
                    old_at+=1;used_old+=1
                if op in (' ','+'):
                    result.append(text);used_new+=1
                if op in ('+','-'): changed+=1
                if used_old>oc or used_new>nc or changed>max_lines: raise ValueError('hunk count/patch line limit')
            hunks+=1
        if not hunks: raise ValueError('no hunks')
        result.extend(before[old_at:]);content=''.join(result)
        if new=='/dev/null':
            if content: raise ValueError('deletion leaves content')
            content=None
        edits.append(dict(path=path,expected_sha256=expected,content=content))
    return edits


def stage_probe(session,diff):
    import ast
    edits=_parse_diff(session.store,session.current,diff,limits=(12000,1,150),probe=True)
    source=edits[0]['content']
    if source is None or len(source.encode())>8192:raise ValueError('probe source capacity')
    try:ast.parse(source)
    except SyntaxError as exc:raise ValueError('invalid proposed Python syntax') from exc
    identity=hashlib.sha256(source.encode()).hexdigest()
    if not any(r['body'].get('event')=='repoworld.probe-proposal' and r['body'].get('probe_id')==identity for r in session.receipts.records):
        session.receipts.append(dict(event='repoworld.probe-proposal',probe_id=identity,source=source,
            author='model',scope='proposed-test',property_status='unknown'))
    return identity


def stage_patch(base,current,diff,*,expected_snapshot_id,purpose):
    if purpose!='solution': raise ValueError('probe namespace requires the public-check adapter (task 4)')
    if expected_snapshot_id!=current.id: raise ValueError('STALE_BASE')
    store=repo_store(current.root.parent.parent);store.validate(current)
    edits=_parse_diff(store,current,diff)
    for edit in edits: production_path(base.task.repo,edit['path'])
    result=store.apply(current,current.id,edits,allowed_paths=tuple(e['path'] for e in edits),advance=False)
    digest=hashlib.sha256(diff.encode()).hexdigest()
    operation=hashlib.sha256(canonical(dict(base=base.snapshot.id,source=current.id,patch=digest,purpose=purpose))).hexdigest()
    return PatchCandidate(base.snapshot.id,result,digest,operation)


class Workspace:
    def __init__(self,directory,base=None):
        self.directory=Path(directory).absolute();self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.directory.is_symlink() or self.directory.stat().st_mode&0o077:
            raise ValueError('private supervisor workspace required')
        self.store=repo_store(self.directory/'objects')
        self.receipts=ReceiptStore(self.directory/'receipts',self.directory/'authority')
        self.budget=Budget({'fuel':200,'tools':80,'output_tokens':80000,'cpu_us':1200000000})
        self.checks={}  # supervisor-only check_id -> fixed argv/limits capability
        with self._lock():
            identity=self.directory/'base.json'
            if identity.exists():
                data=json.loads(identity.read_bytes())
                ref=EnvironmentRef(**{**data['environment'],'root':Path(data['environment']['root'])})
                self.base=RepoBase(PublicTask(**data['task']),self.store.get(data['snapshot']),ref)
                if base is not None and (base.task!=self.base.task or base.snapshot.id!=self.base.snapshot.id or base.environment!=ref):
                    raise ValueError('workspace/base identity mismatch')
            else:
                if base is None: raise ValueError('base required for new workspace')
                snap=self.store.capture(base.snapshot)
                self.base=RepoBase(base.task,snap,base.environment)
                env=asdict(base.environment);env['root']=str(env['root'])
                _atomic_write(identity,canonical(dict(task=asdict(base.task),snapshot=snap.id,environment=env)))
                _atomic_write(self.directory/'state.json',canonical(dict(head=snap.id,pending=None)))
                _atomic_write(self.directory/'cursor.key',secrets.token_bytes(32))
            self._recover()

    @contextmanager
    def _lock(self):
        fd=os.open(self.directory/'transaction.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX);yield
        finally: os.close(fd)

    def _state(self): return json.loads((self.directory/'state.json').read_bytes())
    def _save(self,value): _atomic_write(self.directory/'state.json',canonical(value))
    def _crash_hook(self,point): pass

    def _recover(self):
        state=self._state();pending=state['pending']
        records=self.receipts.records  # validates custody, including its own pending append
        if pending is None:
            retained=[r['body'] for r in records if r['body'].get('event')=='repoworld.retain']
            expected=retained[-1]['to'] if retained else self.base.snapshot.id
            if state['head']!=expected: raise ValueError('retained pointer lacks authenticated transaction')
            return
        if state['head'] not in (pending['from'],pending['to']): raise ValueError('transaction head mismatch')
        self.store.get(pending['to'])
        staged=[r['body'] for r in records if r['body'].get('event')=='repoworld.stage' and r['body'].get('operation_id')==pending['operation_id']]
        if len(staged)!=1 or staged[0]['source']!=pending['from'] or staged[0]['candidate']!=pending['to']:
            raise ValueError('pending transaction lacks a staged proposal')
        by_id={r['sha256']:r['body'] for r in records}
        if not pending['public_receipt_ids']: raise ValueError('pending transaction has no evidence')
        for key in pending['public_receipt_ids']:
            item=by_id.get(key,{})
            if item.get('event')!='repoworld.public-property' or item.get('candidate')!=pending['to'] or item.get('scope')!='public' or item.get('property_status')!='supported':
                raise ValueError('pending transaction evidence invalid')
        events=[r for r in records if r['body'].get('event')=='repoworld.retain' and r['body'].get('operation_id')==pending['operation_id']]
        body=dict(event='repoworld.retain',**pending)
        if len(events)>1 or (events and events[0]['body']!=body): raise ValueError('conflicting retention receipt')
        if not events: self.receipts.append(body)
        self._crash_hook('receipt')
        self._save(dict(head=pending['to'],pending=pending))
        self._crash_hook('head')
        self._save(dict(head=pending['to'],pending=None))

    @property
    def current(self):
        with self._lock():
            self._recover();return self.store.get(self._state()['head'])

    def snapshot(self,identifier):
        # Do not accept any other tree merely because it exists on the filesystem.
        allowed={self.base.snapshot.id,self._state()['head']}
        allowed.update(r['body']['candidate'] for r in self.receipts.records if r['body'].get('event')=='repoworld.stage')
        if identifier not in allowed: raise ValueError('snapshot not authorized in this session')
        return self.store.get(identifier)

    def stage(self,diff,expected_snapshot_id,purpose='solution'):
        with self._lock():
            self._recover()
            if self._state()['head']!=expected_snapshot_id: raise ValueError('STALE_BASE')
            current=self.store.get(expected_snapshot_id)
            candidate=stage_patch(self.base,current,diff,expected_snapshot_id=expected_snapshot_id,purpose=purpose)
            # Reject an unexportable aggregate BEFORE it can be retained.
            self._export_diff(candidate.snapshot)
            record=dict(event='repoworld.stage',candidate=candidate.snapshot.id,base=candidate.base_id,
                        source=current.id,patch_sha256=candidate.patch_sha256,operation_id=candidate.operation_id)
            if not any(r['body']==record for r in self.receipts.records): self.receipts.append(record)
            return candidate

    def retain(self,candidate,*,expected_head,public_receipt_ids):
        with self._lock():
            self._recover();records=self.receipts.records;state=self._state()
            staged=[r for r in records if r['body'].get('event')=='repoworld.stage' and r['body'].get('operation_id')==candidate.operation_id]
            if len(staged)!=1 or staged[0]['body']['candidate']!=candidate.snapshot.id or staged[0]['body']['source']!=expected_head or staged[0]['body']['patch_sha256']!=candidate.patch_sha256 or candidate.base_id!=self.base.snapshot.id:
                raise ValueError('unrecognized staged capability')
            self.snapshot(candidate.snapshot.id)
            if any(r['body'].get('event')=='repoworld.retain' and r['body'].get('operation_id')==candidate.operation_id for r in records):
                if state['head']!=candidate.snapshot.id: raise ValueError('stale completed operation')
                return candidate.snapshot.id
            if state['head']!=expected_head: raise ValueError('STALE_HEAD')
            by_id={r['sha256']:r['body'] for r in records}
            if not public_receipt_ids: raise ValueError('public property evidence required')
            for key in public_receipt_ids:
                r=by_id.get(key,{})
                if r.get('event')!='repoworld.public-property' or r.get('candidate')!=candidate.snapshot.id or r.get('property_status')!='supported' or r.get('scope')!='public':
                    raise ValueError('invalid public property receipt')
            pending=dict(operation_id=candidate.operation_id,**{'from':expected_head,'to':candidate.snapshot.id},
                         public_receipt_ids=list(public_receipt_ids))
            self._save(dict(head=expected_head,pending=pending));self._crash_hook('intent')
            self._recover();return candidate.snapshot.id

    def final_diff(self):
        return self._export_diff(self.current)

    def _export_diff(self,current):
        # Diff text has no authority: roundtrip through the same strict parser is mandatory.
        before=self.base.snapshot;chunks=[];size=0
        for path in sorted(set(before.manifest['entries'])|set(current.manifest['entries'])):
            a=before.manifest['entries'].get(path);b=current.manifest['entries'].get(path)
            if a==b: continue
            _allowed(path)
            if a is None and b and b['type']=='directory' and b['mode']==0o755: continue
            if (a and a['type']!='file') or (b and b['type']!='file'): raise ValueError('directory changes not exportable')
            av=self.store.read(before,path).decode() if a else ''
            bv=self.store.read(current,path).decode() if b else ''
            lines=list(difflib.unified_diff(av.splitlines(True),bv.splitlines(True),fromfile='a/'+path if a else '/dev/null',tofile='b/'+path if b else '/dev/null'))
            for line in lines:
                value=line if line.endswith('\n') else line+'\n\\ No newline at end of file\n'
                size+=len(value.encode('utf-8'))
                if size>EXPORT_LIMITS[0]: raise ValueError('cumulative export byte limit')
                chunks.append(value)
        result=''.join(chunks)
        if result:
            edits=_parse_diff(self.store,before,result,limits=EXPORT_LIMITS)
            rebuilt=self.store.apply(before,before.id,edits,allowed_paths=tuple(e['path'] for e in edits),advance=False)
            if rebuilt.id!=current.id: raise ValueError('final diff roundtrip mismatch')
        elif current.id!=before.id:
            raise ValueError('snapshot changes not representable by this text-diff profile')
        return result


def retain(candidate,*,expected_head,public_receipt_ids):
    return Workspace(candidate.snapshot.root.parent.parent.parent).retain(candidate,
                      expected_head=expected_head,public_receipt_ids=public_receipt_ids)
