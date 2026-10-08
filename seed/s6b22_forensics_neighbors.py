"""Retrospective reconstruction of B22 repair rankings; never plays a game."""
import json
from pathlib import Path

from echo_arc import s6b22_search as search
from seed.s6b22_forensics import REPO, sha, require, delta


def main():
    root = REPO/'lab/seed/s6b22-20261006'
    read = lambda rel: json.loads((root/rel).read_text())
    policy = read('input/baseline.json')['policy']
    winning_guard = read('input/winner.json')['policy']['program']['patches'][-1]['when']
    findings = []
    for folder in sorted((root/'steps').glob('M22-*')):
        history = []
        for path in sorted(folder.glob('*.json')):
            e = json.loads(path.read_text())['event']
            if e['schedule']['phase'] == 'repair':
                parent = next(p for p in history if p['id'] == e['target_id'])
                ranking, _ = search.repair_candidates(parent,history,policy,
                    int(folder.name.split('-')[1]),e['schedule']['child'])
                require(ranking[0]['proposal'] == e['proposal'], 'reconstructed repair differs')
                # The known B21 winner is consulted ONLY by this postmortem,
                # never exported as input to a future researcher/model.
                winner_ranks = [i+1 for i,r in enumerate(ranking)
                                if r['proposal']['patches'][0]['when'] == winning_guard]
                first = ranking[0]
                findings.append(dict(arm=folder.name,id=e['id'],parent=e['target_id'],
                    child=e['schedule']['child'],options=len(ranking),chosen=first,
                    result=e['A'],parent_result=parent['A'],
                    known_winner_guard_ranks=winner_ranks))
            history.append(e)
    # A measured capacity control existed before B22, separately from discovery.
    capacity_root = REPO/'lab/seed/s6b20-capacity-20261006'
    capacity = json.loads((capacity_root/'capacity.json').read_text())
    audit = json.loads((capacity_root/'capacity-audit.json').read_text())
    plan_path = REPO/'lab/kaggle/s6b20-20261006/capacity-input/capacity-plan.json'
    plan = json.loads(plan_path.read_text())
    control = next(c for c in plan['candidates'] if c['name'] == capacity['qualified']['human-control'])
    search.validate_proposal(control['proposal'])
    # The plan's base_sha256 identifies a B19 measurement, not policy bytes.
    fixture = json.loads((plan_path.parent/'baseline.json').read_text())
    require(fixture['policy'] == policy, 'capacity control uses another policy')
    require(audit['valid'] and audit['capacity_sha256'] == sha(capacity), 'capacity linkage differs')
    broad_base = json.loads((capacity_root/'capacity/measurements/full-baseline.json').read_text())
    b22_base = read('v-broad/measurements/baseline.json')
    require(broad_base == b22_base, 'capacity broad baseline differs from B22')
    broad_after = json.loads((capacity_root/'capacity/measurements/full-human-control.json').read_text())
    measured_effect, _ = delta(broad_base,broad_after)
    require(measured_effect == capacity['broad']['human-control'], 'capacity effect differs')
    detail = dict(reconstructed_repairs=len(findings),repairs=findings,
        known_control=dict(legal_under_b22=True,base_identical=True,
            broad_effect=measured_effect,audit_valid=True,
            proposal_sha256=sha(control['proposal']),not_delivered_to_researcher=True),
        games_started=0,model_calls=0,
        interpretation='Retrospective explanation only; known-control matching is not autonomous discovery')
    out = REPO/'lab/seed/s6b22-forensics-20261007/repair-reconstruction.json'
    out.write_text(json.dumps(detail,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in detail.items() if k != 'repairs'},ensure_ascii=False))


if __name__ == '__main__':
    main()
