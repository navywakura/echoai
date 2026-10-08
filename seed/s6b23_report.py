"""Read-only status summary; an old status file is never proof of a live process."""
import argparse
import json
from pathlib import Path


def report(root):
    def read(name,default):
        path=root/name
        return json.loads(path.read_text()) if path.exists() else default
    rows=[]
    for arm in ('R22','M22','M23','N7','N14'):
        events=[json.loads(p.read_text())['event'] for p in sorted((root/'steps'/arm).glob('*.json'))]
        rows.append(dict(arm=arm,attempts=len(events),max_attempts=18,
            micro_passes=sum(e['verdict']=='A_ONLY_PASS' for e in events),
            invalid=sum(e['verdict']=='INVALID_PROPOSAL' for e in events),
            duplicates=sum(e['verdict']=='DUPLICATE' for e in events),
            losses=sum(bool(e.get('A',{}).get('loss_indices')) for e in events),
            best_measured_gain=max((e['A']['gain'] for e in events if 'A' in e),default=None)))
    budget=read('budget.json',{'scheduled_games':0})
    finished=list((root/'executions/completed').glob('*.json'))
    jobs={j['job_id']:j for j in budget.get('jobs',[])}
    matched=[];orphan=[]
    for path in finished:
        receipt=json.loads(path.read_text());job=jobs.get(int(path.stem))
        if job and receipt['task_id']==job['task_id']:matched.append(path.name)
        else:orphan.append(path.name)
    return dict(status=read('status.json',{'stage':'NOT_PREPARED'}),
        readiness=read('readiness.json',None),arms=rows,
        reserved_games=budget['scheduled_games'],completed_games=len(matched),orphan_completion_receipts=orphan,
        model_calls=len(read('model-budget.json',{'calls':[]})['calls']),
        estimate=read('estimate.json',None),closed=read('closed.json',None),
        s6_green=False,process_liveness='not checked; status is the last persisted receipt')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('lab/seed/s6b23-20261007'))
    print(json.dumps(report(p.parse_args().root),ensure_ascii=False,indent=2))
