"""All candidates and A results are retained; V2 B is not selection data."""
import json
from pathlib import Path
from unittest.mock import patch
from echoai.nexus0.compose1.bench import save, MODES, CONDITIONS
from echoai.nexus0.fusion1.bench import seal
from echoai.nexus0.compose1_v2.bench import metrics
from echoai.nexus0.compose1_v2.functional import mission
from .candidates import Composer, PrefixWait
from echoai.nexus0.compose1_v2.development import train

ROOT = Path(__file__).resolve().parents[2]/'lab/compose1-v3'


def main():
    root = ROOT/'development/algorithms-1'
    root.mkdir(parents=True, exist_ok=False)
    (root/'controller.py').write_bytes(Path(__file__).with_name('controller.py').read_bytes())
    model = json.loads((ROOT.parent/'compose1-v2/physical-school.json').read_text())['model']
    save(root/'declared.json', seal(dict(seeds=list(range(20261901, 20261933)),
        candidates=['cost_aware', 'equal_horizon'], modes=list(MODES), conditions=list(CONDITIONS))))
    for name, cls in (('cost_aware', Composer), ('equal_horizon', PrefixWait)):
        rows = []
        with patch('echoai.nexus0.compose1_v2.functional.Composer', cls):
            for i, seed in enumerate(range(20261901, 20261933)):
                for mode in MODES:
                    result = mission(model, seed, CONDITIONS[i % 4], mode)
                    save(root/f'{name}-{seed}-{mode}.json', seal(result))
                    rows.append(result)
        report = seal(metrics(rows))
        save(root/f'{name}-report.json', report)
        print(name, json.dumps(report['horizon_contrast'], sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
