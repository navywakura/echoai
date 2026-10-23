"""Ephemeral inference-only relay. No shell, files, or candidate execution.

One outstanding request; distinct client/worker capabilities. Responses are
untrusted model data. Local PCWorld keeps all execution and oracle authority.
"""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import re
from pathlib import Path
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES=2*1024*1024
ROUTES=('/apply-template','/tokenize','/completion')

def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()

def parsed(raw):
    def pairs(rows):
        d={}
        for k,v in rows:
            if k in d: raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    def invalid(value): raise ValueError('nonfinite JSON')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
    if not isinstance(value,dict):raise ValueError('JSON object required')
    return value


class DurableJobs:
    """Bounded authenticated replay cache. Delivered-but-lost work stays pending.

    It is never redelivered automatically after a broker/worker crash. That
    ambiguity needs a late worker result or explicit episode termination; this
    provides at-most-once dispatch, not distributed exactly-once computation.
    """
    def __init__(self,directory,key):
        self.root=Path(directory);self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.root.is_symlink() or self.root.stat().st_mode&0o077: raise ValueError('private replay directory required')
        self.key=key.encode()
    def path(self,identifier):
        if not isinstance(identifier,str) or not re.fullmatch('[A-Za-z0-9_-]{1,180}',identifier): raise ValueError('invalid request ID')
        return self.root/(hashlib.sha256(identifier.encode()).hexdigest()+'.json')
    def load(self,identifier):
        p=self.path(identifier)
        if not p.exists(): return None
        if p.is_symlink() or p.stat().st_size>3*MAX_BYTES: raise ValueError('invalid replay record')
        envelope=parsed(p.read_bytes());raw=encoded(envelope['value'])
        if not hmac.compare_digest(envelope['hmac'],hmac.new(self.key,raw,'sha256').hexdigest()): raise ValueError('replay authentication failed')
        if envelope['value']['job']['id']!=identifier: raise ValueError('replay identity mismatch')
        return envelope['value']
    def save(self,item):
        p=self.path(item['job']['id']);raw=encoded(item)
        files=list(self.root.glob('*.json'))
        if (len(files)>=10000 and not p.exists()) or sum(f.stat().st_size for f in files)+len(raw)>512*1024**2:
            raise ValueError('replay cache capacity exhausted')
        envelope=encoded({'value':item,'hmac':hmac.new(self.key,raw,'sha256').hexdigest()})
        temp=self.root/(p.name+'.'+secrets.token_hex(8)+'.tmp')
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(envelope);f.flush();os.fsync(f.fileno())
        os.replace(temp,p);fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def pending(self):
        found=[]
        for p in self.root.glob('*.json'):
            item=parsed(p.read_bytes())['value'];item=self.load(item['job']['id'])
            if item['result'] is None: found.append(item)
        if len(found)>1: raise ValueError('multiple unresolved relay jobs')
        return found[0] if found else None

class RelayServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,*,client_token,worker_token,request_timeout=300,poll_timeout=15,audit_log=None,journal_dir=None):
        if address[0]!='127.0.0.1':raise ValueError('loopback bind required')
        for token in (client_token,worker_token):
            if not isinstance(token,str) or not 32<=len(token)<=256 or not token.isascii():raise ValueError('invalid credential')
        if client_token==worker_token:raise ValueError('distinct capabilities required')
        for value,upper in ((request_timeout,300),(poll_timeout,20)):
            if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=upper:raise ValueError('invalid timeout')
        self.client_token=client_token;self.worker_token=worker_token
        self.request_timeout=request_timeout;self.poll_timeout=poll_timeout
        self.audit_log=Path(audit_log) if audit_log else None
        self.condition=threading.Condition();self.pending=None;self.stopped=False;self.ready=None
        self.jobs=DurableJobs(journal_dir,client_token) if journal_dir else None
        if self.jobs:self.pending=self.jobs.pending()
        super().__init__(address,Handler)
    def stop_work(self):
        with self.condition:
            self.stopped=True
            if self.pending is not None and not self.pending.get('durable'):self.pending=None
            self.condition.notify_all()

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,*args):pass
    def reply(self,status,data):
        raw=encoded(data);self.close_connection=True
        try:
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('Connection','close');self.end_headers();self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError):pass
    def auth(self,role):
        supplied=self.headers.get('Authorization','')
        client=hmac.compare_digest(supplied,'Bearer '+self.server.client_token)
        worker=hmac.compare_digest(supplied,'Bearer '+self.server.worker_token)
        if not(client or worker):self.reply(401,{'error':'unauthorized'});return False
        if (role=='client' and not client) or (role=='worker' and not worker):
            self.reply(403,{'error':'capability denied'});return False
        return True
    def body(self):
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
            self.reply(400,{'error':'fixed content length required'});return None
        try:n=int(self.headers['Content-Length'])
        except ValueError:self.reply(400,{'error':'invalid length'});return None
        if not 0<n<=MAX_BYTES:self.reply(413,{'error':'body size limit'});return None
        try:
            raw=self.rfile.read(n)
            if len(raw)!=n:raise ValueError('truncated request')
            return parsed(raw)
        except (ValueError,RecursionError,TimeoutError):self.reply(400,{'error':'invalid JSON body'});return None
    def do_GET(self):self.dispatch('GET')
    def do_POST(self):self.dispatch('POST')
    def do_PUT(self):self.reply(405,{'error':'method not allowed'})
    def dispatch(self,method):
        s=self.server;path=self.path
        known=path in ROUTES or path in ('/health','/stop','/worker/next','/worker/result','/worker/ready')
        if not self.auth('worker' if path.startswith('/worker/') else 'client'):return
        if not known:self.reply(404,{'error':'unknown route'});return
        expected='GET' if path in ('/health','/worker/next') else 'POST'
        if method!=expected:self.reply(405,{'error':'method not allowed'});return
        data=self.body() if method=='POST' else None
        if method=='POST' and data is None:return
        if path=='/health':
            with s.condition:self.reply(200,{'worker_ready':s.ready is not None,'metadata':s.ready,'stopped':s.stopped,'durable_request_ids':s.jobs is not None})
        elif path=='/stop':s.stop_work();self.reply(200,{'status':'stop'})
        elif path=='/worker/ready':
            with s.condition:
                if s.stopped or s.ready is not None:self.reply(409,{'error':'already ready or stopped'});return
                s.ready=data
            self.reply(200,{'status':'ready'})
        elif path=='/worker/next':
            with s.condition:
                until=time.monotonic()+s.poll_timeout
                while not s.stopped and (s.pending is None or s.pending['delivered']):
                    remaining=until-time.monotonic()
                    if remaining<=0:break
                    s.condition.wait(remaining)
                if s.stopped:self.reply(200,{'status':'stop'});return
                if s.pending is None or s.pending['delivered']:
                    self.reply(200,{'status':'idle'});return
                s.pending['delivered']=True
                if s.jobs and s.pending.get('durable'):s.jobs.save(s.pending)
                self.reply(200,s.pending['job'])
        elif path=='/worker/result':
            if set(data)!={'id','status','data'} or not isinstance(data['data'],dict) or type(data['status']) is not int or not (200<=data['status']<=299 or 400<=data['status']<=599):
                self.reply(400,{'error':'invalid result'});return
            with s.condition:
                item=s.pending
                if s.jobs:
                    cached=s.jobs.load(data['id'])
                    if cached and cached['result'] is not None:
                        self.reply(200 if cached['result']==[data['status'],data['data']] else 409,{'status':'replayed-result'});return
                if (s.stopped and not(item and item.get('durable'))) or item is None or item['job']['id']!=data['id'] or not item['delivered'] or item['result'] is not None:
                    self.reply(409,{'error':'expired or duplicate result'});return
                item['result']=[data['status'],data['data']]
                if s.jobs and item.get('durable'):s.jobs.save(item)
                if item.get('durable') and s.pending is item:s.pending=None
                s.condition.notify_all()
            self.reply(200,{'status':'received'})
        else:
            identifier=data.pop('request_id',None)
            if identifier is not None and not s.jobs:self.reply(412,{'error':'durable replay required'});return
            if data.get('stream',False) is not False:self.reply(400,{'error':'streaming disabled'});return
            started=time.monotonic();sha=hashlib.sha256(encoded({'path':path,'data':data})).hexdigest()
            item={'job':{'id':identifier or secrets.token_hex(24),'path':path,'data':data,'request_sha256':sha},'delivered':False,'result':None}
            if identifier is not None:item['durable']=True
            with s.condition:
                if s.stopped:self.reply(503,{'error':'stopped'});return
                if identifier is not None:
                    try:cached=s.jobs.load(identifier)
                    except ValueError:self.reply(409,{'error':'invalid replay record/identity'});return
                    if cached:
                        if cached['job']['request_sha256']!=sha:self.reply(409,{'error':'request ID payload conflict'});return
                        if cached['result'] is not None:self.reply(*cached['result']);return
                        if s.pending is None:s.pending=cached
                if s.pending is not None:
                    if identifier is None or s.pending['job']['id']!=identifier:self.reply(429,{'error':'one request at a time'});return
                    item=s.pending
                else:
                    if identifier is not None:s.jobs.save(item)
                    s.pending=item
                s.condition.notify_all()
                until=started+s.request_timeout
                while item['result'] is None and not s.stopped:
                    remaining=until-time.monotonic()
                    if remaining<=0:break
                    s.condition.wait(remaining)
                status,result=item['result'] or (503 if s.stopped else 504,{'error':'stopped' if s.stopped else 'relay timeout'})
                if s.pending is item and (not item.get('durable') or item['result'] is not None):s.pending=None
                s.condition.notify_all()
                if s.audit_log:
                    row={'request_sha256':sha,'response_sha256':hashlib.sha256(encoded(result)).hexdigest(),
                         'status':status,'elapsed_ms':round((time.monotonic()-started)*1000)}
                    s.audit_log.parent.mkdir(parents=True,exist_ok=True)
                    with s.audit_log.open('ab') as f:f.write(encoded(row)+b'\n')
            self.reply(status,result)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def fetch(url,*,token=None,data=None,timeout=30):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(url,data=encoded(data) if data is not None else None,headers=headers)
    opener=urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req,timeout=timeout) as r:
            raw=r.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('oversize response')
            return r.status,parsed(raw)
    except urllib.error.HTTPError as exc:
        raw=exc.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise ValueError('oversize error')
        try:body=parsed(raw)
        except ValueError:body={'error':'upstream HTTP error'}
        return exc.code,body

def deliver_worker_message(url,*,token,data,until):
    """Retry an idempotent acknowledgement, never rerun local inference."""
    for attempt in range(4):
        try:
            status,value=fetch(url,token=token,data=data,timeout=min(30,max(.1,until-time.monotonic())))
            if status not in (429,502,503,504):return status,value
        except (OSError,TimeoutError):pass
        if attempt==3 or time.monotonic()>=until:raise RuntimeError('relay delivery deadline; generated result not recomputed')
        time.sleep(min(2**attempt,max(0,until-time.monotonic())))


def run_worker(broker_url,worker_token,*,max_seconds=2700,ready_metadata=None):
    url=urllib.parse.urlsplit(broker_url)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/'):
        raise ValueError('HTTPS broker origin required')
    if type(max_seconds) is not int or not 1<=max_seconds<=8400:raise ValueError('invalid worker duration')
    base=broker_url.rstrip('/');until=time.monotonic()+max_seconds;count=0
    status,_=deliver_worker_message(base+'/worker/ready',token=worker_token,data=ready_metadata or {'ready':True},until=until)
    if status!=200:raise RuntimeError('relay readiness refused')
    while time.monotonic()<until:
        status,job=fetch(base+'/worker/next',token=worker_token,timeout=25)
        if status!=200:raise RuntimeError('relay poll failed')
        if job.get('status')=='stop':return {'requests':count,'stopped':True}
        if job.get('status')=='idle':continue
        if set(job)!={'id','path','data','request_sha256'} or job['path'] not in ROUTES or not isinstance(job['data'],dict):
            raise ValueError('invalid inference request')
        if hashlib.sha256(encoded({'path':job['path'],'data':job['data']})).hexdigest()!=job['request_sha256']:
            raise ValueError('request hash mismatch')
        try:
            code,result=fetch('http://127.0.0.1:8785'+job['path'],data=job['data'],timeout=min(280,max(1,until-time.monotonic())))
            if not(200<=code<=299 or 400<=code<=599):code,result=502,{'error':'unsupported upstream status'}
        except (ValueError,OSError,TimeoutError):code,result=502,{'error':'local inference failure'}
        status,_=deliver_worker_message(base+'/worker/result',token=worker_token,data={'id':job['id'],'status':code,'data':result},until=until)
        if status not in (200,409):raise RuntimeError('relay result delivery failed')
        count+=1
    return {'requests':count,'stopped':False,'deadline':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('secrets',type=Path);p.add_argument('--log',type=Path);p.add_argument('--port',type=int,default=8786);p.add_argument('--journal',type=Path)
    a=p.parse_args();credentials=json.loads(a.secrets.read_text())
    server=RelayServer(('127.0.0.1',a.port),client_token=credentials['client_token'],worker_token=credentials['worker_token'],audit_log=a.log,journal_dir=a.journal)
    try:server.serve_forever()
    finally:server.stop_work();server.server_close()
