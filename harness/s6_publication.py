"""Private publication of terminal B11 receipts, never exam instrumentation."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

CORE = Path(__file__).resolve().parents[1]
RUN = CORE / 'lab/seed/s6b11-20260929'
STATE = CORE / 'lab/echo-nexus/s6-publication'
WEB = Path('/tmp/rxlabs-s6b11-publication')
ORIGIN = 'https://github.com/navywakura/ROGEX-LABORATORIES.git'
PATHS = ['src/data/echo-research.json', 'public/data/echo-research.json',
         'public/evidence/echo45/s6-b11-final.json',
         'public/evidence/echo45/ECHO45-S6-B11-RESULTS.md']


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def final_summary(closed, pilot, campaign=None, audit=None):
    """A status label alone cannot turn the public record green."""
    audit, campaign = audit or {}, campaign or {}
    if closed.get('exam_opened') and not audit:
        raise ValueError('Opened exam has no final audit')
    checks = audit.get('checks', {})
    green = bool(closed.get('s6_green') and audit.get('green') and
                 set(checks) == {'B1','B2','B3','B4','B5'} and all(v is True for v in checks.values()) and
                 pilot.get('promote') and campaign.get('promote') and closed.get('exam_opened'))
    if closed.get('s6_green') and not green:
        raise ValueError('Inconsistent green receipt; publication refused')
    return {'condition':'S6-B11','stage':'CLOSED','green':green,'closed':closed['at'],
            'result':closed['result'],'checks':checks,'totals':audit.get('totals',{}),
            'accepted_echo':campaign.get('accepted_echo',pilot['accepted_echo']),
            'pilot':{k:pilot[k] for k in ('promote','paired_A','accepted_echo')},
            'campaign':{k:campaign[k] for k in ('promote','paired_A','accepted_echo') if k in campaign},
            'exam_opened':closed['exam_opened'],'cost_usd':audit.get('cost_usd',0),
            'arc_official_scores_changed':False}


def verified_summary():
    closed = read(RUN/'closed.json')
    profile = read(RUN/'profile.json')
    for name, expected in profile['sources'].items():
        if hashlib.sha256((CORE/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen source mismatch: '+name)
    pilot = read(RUN/'pilot.json')
    campaign = read(RUN/'campaign.json') if (RUN/'campaign.json').exists() else None
    audit = read(RUN/'exam/audit.json') if (RUN/'exam/audit.json').exists() else None
    if audit:
        policies = read(RUN/'strategies.json')
        completed = read(RUN/'completed.json')
        if digest(policies) != audit['strategies_sha256'] or completed['strategies_sha256'] != digest(policies):
            raise ValueError('Strategy digest mismatch')
        if audit['sources'] != profile['sources'] or completed['sources'] != profile['sources']:
            raise ValueError('Audited sources mismatch')
        for phase in ('pilot','campaign'):
            receipt = read(RUN/(phase+'-audit.json'))
            if receipt.get('valid') is not True or receipt['profile_sha256'] != digest(profile):
                raise ValueError('Missing independent phase audit')
    summary = final_summary(closed,pilot,campaign,audit)
    summary['profile_sha256'] = digest(profile)
    summary['receipt_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [RUN/'closed.json', RUN/'pilot.json', RUN/'campaign.json', RUN/'exam/audit.json'] if p.exists()}
    return summary


def command(*args, cwd=WEB):
    return subprocess.run(args,cwd=cwd,check=True,text=True,capture_output=True,timeout=180).stdout.strip()


def publish(summary):
    if not WEB.exists():
        command('git','clone',ORIGIN,str(WEB),cwd=CORE)
    if command('git','remote','get-url','origin') != ORIGIN:
        raise ValueError('Wrong publication repository')
    if command('git','status','--porcelain'):
        raise ValueError('Publication checkout is dirty; review before resuming')
    command('git','fetch','origin')
    command('git','merge','--ff-only','origin/main')
    data = read(WEB/'src/data/echo-research.json')
    data['s6_latest'].update(summary)
    data['s6_latest']['pilot_audit_valid']=(RUN/'pilot-audit.json').exists()
    data['s6_latest']['status']={'stage':'CLOSED','at':summary['closed']}
    data['snapshot_at']=datetime.now(timezone.utc).isoformat()
    data['latest_experiment_at']=summary['closed']
    for name in PATHS[:2]:(WEB/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (WEB/PATHS[2]).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    # The engine report is public prose/aggregate metrics, never source code or exam inputs.
    report=(CORE/'docs/ECHO45-S6-B11-RESULTS.md').read_text()
    (WEB/PATHS[3]).write_text(report+'\n\n[Recibo final publicado](/evidence/echo45/s6-b11-final.json).\n')
    changed=set(command('git','diff','--name-only').splitlines())
    untracked=set(command('git','ls-files','--others','--exclude-standard').splitlines())
    if not changed.union(untracked) <= set(PATHS):
        raise ValueError('Unexpected publication paths')
    command('git','add','--',*PATHS)
    command('git','diff','--cached','--check')
    command('git','-c','user.name=RxLabs','-c','user.email=rxlabs@users.noreply.github.com',
            'commit','-m','Publish audited S6-B11 closure: '+('green' if summary['green'] else 'criteria pending'))
    commit=command('git','rev-parse','HEAD')
    # Record before push. If push is uncertain, do not create a duplicate commit.
    receipt={'commit':commit,'summary':summary,'state':'PUSH_PENDING'}
    (STATE/'publication.json').write_text(json.dumps(receipt,indent=2)+'\n')
    command('git','push','origin','HEAD:main')
    receipt['state']='PUSHED'
    (STATE/'publication.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'published':commit,'s6_green':summary['green']}),flush=True)


def follow():
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'watch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (STATE/'publication.json').exists():
            raise ValueError('Existing publication receipt; inspect before retrying')
        while not (RUN/'closed.json').exists() or read(RUN/'status.json').get('stage') != 'CLOSED':
            status=read(RUN/'status.json')
            (STATE/'status.json').write_text(json.dumps({'waiting':True,'s6':status})+'\n')
            time.sleep(30)
        publish(verified_summary())


if __name__=='__main__':
    if sys.argv[1:]==['follow']:follow()
    elif sys.argv[1:]==['check']:
        print(json.dumps({'terminal':(RUN/'closed.json').exists(),'s6':read(RUN/'status.json')}))
    else:raise SystemExit('use follow or check')
