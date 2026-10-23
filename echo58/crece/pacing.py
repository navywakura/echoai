"""Provider pacing shared between workers; scheduling state contains no credentials."""
import fcntl
from email.utils import parsedate_to_datetime
import json
import os
import re
from pathlib import Path
import tempfile
import time
from .api import complete
from .artifacts import durable_directory, sync_directory
from .equiv import LAB, log


class QuotaDeferred(RuntimeError):
    def __init__(self,until):
        self.until=until
        super().__init__(f'provider quota deferred until Unix time {until}; no new HTTP attempt')


def seconds(text):
    if not isinstance(text,str):return 0
    parts=re.findall(r'(\d+(?:\.\d+)?)(ms|s|m|h|d)',text)
    return sum(float(n)*{'ms':.001,'s':1,'m':60,'h':3600,'d':86400}[unit] for n,unit in parts)


def replace_state(path,value):
    fd,temp=tempfile.mkstemp(prefix='.pacing-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def paced_complete(model,prompt,cache,*,provider='groq',max_tokens=2048,reasoning_effort='low',
                   state_dir=None,call=complete,clock=time.time,sleep=time.sleep,before_call=None):
    root=Path(state_dir) if state_dir is not None else LAB/'provider-pacing'/provider
    durable_directory(root)
    with (root/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=root/'schedule.json'
        state=json.loads(path.read_text()) if path.exists() else {'next_allowed':0}
        wait=max(0,state['next_allowed']-clock())
        if wait:
            log('provider_wait',provider=provider,model=model,seconds=int(wait)+1)
        if wait>300:
            raise QuotaDeferred(state['next_allowed'])
        while clock()<state['next_allowed']:
            sleep(min(5,state['next_allowed']-clock()))
        state={'next_allowed':clock()+60,'provider':provider}
        replace_state(path,state)
        receipt=call(model,prompt,cache,provider=provider,max_tokens=max_tokens,reasoning_effort=reasoning_effort,
                     before_call=before_call)
        if receipt['status']==429:
            headers=receipt.get('rate_headers',{})
            retry=headers.get('retry-after',60)
            try:delay=max(60,float(retry))
            except (ValueError,TypeError):
                try:delay=max(60,parsedate_to_datetime(retry).timestamp()-clock())
                except (ValueError,TypeError,OverflowError):delay=60
            if str(headers.get('x-ratelimit-remaining-requests'))=='0':
                delay=max(delay,seconds(headers.get('x-ratelimit-reset-requests')))
            for error in receipt.get('provider_errors',[]):
                try:delay=max(delay,float((error.get('retry_delay') or '0s').removesuffix('s')))
                except (ValueError,TypeError):pass
            state['next_allowed']=max(state['next_allowed'],clock()+delay)
            replace_state(path,state)
            if delay>300:
                receipt={**receipt,'deferred_until':state['next_allowed']}
        return receipt
