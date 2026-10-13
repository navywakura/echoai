"""Task/arm scoped host adapter over the existing 4096-slot CAM and WSP16.

Similar experiences are retrieval hints. They never veto, certify or shortcut
execution. Receipt identity lives in host metadata, not in ext.slot's byte.
"""
import hashlib
import json
from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack

RELATIONS={'observation':14,'failure':28,'property':27,'proposal':29,'decision':13}

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()

class EpisodeMemory:
    def __init__(self,task,arm):
        self.task,self.arm=task,arm
        self.cam=Cam();self.events=[];self.exact={};self.lookup_work=0;self.cortex_calls=0
    def record(self,receipt,*,kind):
        n=len(self.events)
        if n>=4096: raise RuntimeError('MEMORY_FULL: 4096 event identifiers; no recycling')
        if kind not in RELATIONS: raise ValueError('unknown semantic event')
        # domain=9 and generator=8 follow existing host research adapters.
        # styles 224..239 reserve this version's bounded episode identifiers.
        wsp=pack(src=2,rel=RELATIONS[kind],dst=3,domain=9,generator=8,
                 style=224+(n>>8),seq=n&255,slot=0)
        vertex,latency,_=encode_event(wsp)
        observed=kind in ('observation','failure','property')
        extract=_canonical({'receipt':receipt['sha256'],'scope':kind}).decode()
        slot,_=allocate(self.cam,wsp,vertex,latency,(0,0,0,0,0,0),has_fact=int(observed),
                        extract=extract if observed else '',source='pcworld-host-observation',key=wsp)
        if slot<0: raise RuntimeError('MEMORY_FULL')
        event={'n':n,'task':self.task,'arm':self.arm,'wsp':wsp.hex(),'cam_slot':slot,
               'kind':kind,'receipt_sha256':receipt['sha256'],'body':receipt['body']}
        self.events.append(event);return event
    def recall(self,kind):
        self.lookup_work+=len(self.events)
        kinds=(kind,) if isinstance(kind,str) else tuple(kind)
        return [e for e in self.events if e['kind'] in kinds]
    def cache(self,key,preconditions,value,*,cacheable=False):
        if not cacheable: return
        if len(self.exact)>=4096 and key not in self.exact: raise RuntimeError('CACHE_FULL')
        # Copies ensure a caller cannot mutate the preconditions after recording.
        self.exact[key]=json.loads(_canonical([preconditions,value]))
    def reuse(self,key,preconditions,*,cacheable=False):
        self.lookup_work+=1
        pair=self.exact.get(key)
        if cacheable and pair is not None and _canonical(pair[0])==_canonical(preconditions):
            return json.loads(_canonical(pair[1]))
        return None

class ConceptShelf:
    """Experimental scoped recipes; even matching recipes require execution.

    The principal pilot freezes this shelf empty. No learned-program promotion
    or evidence of cross-task transfer is claimed by this registry.
    """
    def __init__(self): self.entries={}
    def add(self,key,scope,recipe,*,supports):
        if key in self.entries or len(set(supports))<2: raise ValueError('distinct support required')
        self.entries[key]={'scope':scope,'recipe':recipe,'supports':sorted(set(supports)),'corrections':[]}
    def get(self,key,scope):
        value=self.entries.get(key)
        if value is None or value['scope']!=scope: return {'status':'inapplicable'}
        return {'status':'quarantined' if value['corrections'] else 'candidate',
                'recipe':value['recipe'],'requires_recheck':True}
    def correct(self,key,evidence):
        e=self.entries[key]
        if evidence.get('status')!='contradicted' or evidence.get('scope')!=e['scope'] or not evidence.get('receipt'):
            raise ValueError('scoped verified correction required')
        e['corrections'].append(dict(evidence))
