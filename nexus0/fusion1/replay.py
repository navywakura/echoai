"""Sensor boundary: reduced physical samples from immutable SITL evidence.

Only sensor values/times/status cross into the reducer. Private poses and
world metadata remain here, outside the consumer. No synthetic depth image
is claimed: the old logger preserved its central row, not the full image.
"""
import hashlib
import json
import math
from pathlib import Path
from .core import packet, UNKNOWN
from .scenarios import query

ECHOAI = Path(__file__).resolve().parents[2]
PARENT = ECHOAI/'lab/pattern1r-v4/bench/report.json'


def file_hash(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def quantize(distance):
    if not math.isfinite(distance) or not .3 <= distance <= 20:
        return UNKNOWN, None
    mm=round(distance*1000)
    return (1 if mm<1900 else 0 if mm>2100 else UNKNOWN), mm


def build():
    parent=json.loads(PARENT.read_text())
    if not parent['passed']:
        raise ValueError('parent not green')
    cases=[]
    pins={str(PARENT.relative_to(ECHOAI)):file_hash(PARENT)}
    for rec in parent['records']:
        if rec['arm'] not in ('clean','faulted'):continue
        paths={k:ECHOAI/rec[k] for k in ('private','transcript')}
        for k,p in paths.items():
            sha=file_hash(p)
            if sha!=rec[k+'_sha256']:raise ValueError('parent sample hash '+str(p))
            pins[str(p.relative_to(ECHOAI))]=sha
        # Sample 20 temporal windows deterministically, without inspecting values
        # or truth. Both channels remain as delivered, including invalid records.
        delivered=[]
        with open(paths['transcript']) as f:
            for line in f:
                row=json.loads(line);h=json.loads(row['h'])
                if h['source'] in ('depth','lidar'):
                    delivered.append((h,row['wire']))
        n=len(delivered)
        selected={idx for j in range(20) for idx in range(j*n//20,min(n,j*n//20+8))}
        wanted={(h['source'],h['capture_ns']) for idx,(h,_) in enumerate(delivered) if idx in selected}
        samples={}
        with open(paths['private']) as f:
            for line in f:
                r=json.loads(line)
                if r['k']=='raw' and (r['src'],r['stamp']) in wanted:
                    samples[(r['src'],r['stamp'])]=r
        for j in range(20):
            commands=[];origin=j*n//20
            # A window has a fresh local frame. This is local agreement, not SLAM.
            for h,wire in delivered[origin:min(n,origin+8)]:
                r=samples.get((h['source'],h['capture_ns']))
                if r is None:raise ValueError('capture has no raw sample')
                distance=r['sample']['values'][80] if h['source']=='depth' else r['sample']['ranges'][180]
                value,mm=quantize(distance)
                extract=json.dumps(dict(source=h['source'],capture_ns=h['capture_ns'],
                                        millimetres=mm,sample_index=80 if h['source']=='depth' else 180),sort_keys=True)
                commands.append(dict(op='observe',wsp=packet(value,40).hex(),source=h['source'],
                    capture_ns=h['capture_ns'],delivered_ns=h['delivered_ns'],
                    valid=h['status']=='ok' and wire==h['payload_sha256']==r['sha'],
                    extract=extract,extract_sha256=hashlib.sha256(extract.encode()).hexdigest()))
                commands.append(query(h['delivered_ns']))
            # Freeze source time but advance the query clock: a real stream ending
            # cannot leave a permanently authoritative observation behind.
            commands.append(query(commands[-1]['now_ns']+250_000_001))
            cases.append(dict(condition='sitl_replay',repetition=j,origin=rec['label'],commands=commands))
    if len(cases)!=240:raise ValueError('physical replay denominator')
    return cases,pins
