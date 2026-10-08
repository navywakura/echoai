"""Serial SITL development and frozen evaluation. All attempts are retained."""
import argparse
import json
from pathlib import Path

from echoai.nexus0.compose1.bench import save
from echoai.nexus0.fusion1.bench import seal
from .development import ROOT
from .session import run
from .evaluate import audit_session


def development(label):
    root = ROOT/'sitl-development'/label
    root.mkdir(parents=True, exist_ok=False)
    model = json.loads((ROOT/'physical-school.json').read_text())['model']
    cases = [(20261901, 'static', mode) for mode in ('echo32', 'one_step', 'q', 'conventional')]
    cases += [(20261902, 'dynamic', mode) for mode in ('echo32', 'one_step', 'q', 'conventional')]
    cases += [(20261903, 'closed', 'echo32'), (20261904, 'low_energy', 'echo32')]
    save(root/'declared.json', seal(dict(cases=cases)))
    records = []
    for seed, condition, mode in cases:
        case = root/f'{seed}-{mode}'
        run(case, seed, mode, condition=condition, snapshot=model)
        try:
            audit = audit_session(case)
        except Exception as exc:
            audit = dict(evidence_valid=False, findings=[repr(exc)])
        save(case/'audit.json', seal(audit))
        records.append(dict(seed=seed, condition=condition, mode=mode, audit=audit))
        print(json.dumps(dict(case=case.name, audit=audit), sort_keys=True), flush=True)
        if not audit['evidence_valid'] or not audit['execution_green']:
            break
    green = len(records) == len(cases) and all(r['audit']['evidence_valid'] and r['audit']['execution_green'] for r in records)
    green &= all(r['audit'].get('reached', False) for r in records
                 if r['mode'] == 'echo32' and r['condition'] in ('static', 'dynamic'))
    save(root/'summary.json', seal(dict(development_green=bool(green), records=records)))
    return green


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('develop',))
    parser.add_argument('label')
    args = parser.parse_args()
    raise SystemExit(0 if development(args.label) else 1)


if __name__ == '__main__':
    main()
