"""Attack saved physical evidence in throwaway copies; preserve originals."""
import json
import shutil
import tempfile
from pathlib import Path
from .evaluate import audit_session, read_lines


def mutations(source):
    original = audit_session(source)
    if not original['evidence_valid'] or not original['execution_green']:
        raise ValueError('mutations require a valid physical source')
    out = {}
    for name in ('ack', 'late_prediction', 'consequence', 'residual', 'omit_command',
                 'wrong_seed', 'body_pose_write'):
        with tempfile.TemporaryDirectory(prefix='cause1-mutation-') as tmp:
            root = Path(tmp)/'flight'
            shutil.copytree(source, root, symlinks=True)
            rows = read_lines(root/'journal.jsonl')
            mission = read_lines(root/'out/mission.jsonl')
            if name == 'ack':
                next(r for r in mission if r['kind'] == 'ack')['accepted'] = False
            elif name == 'late_prediction':
                next(r for r in mission if r['kind'] == 'command')['sent_ns'] = 0
            elif name == 'consequence':
                next(r for r in rows if r['side'] == 'backend' and r['event'].get('kind') == 'after')['event']['raw']['estimate']['position_mm'][1] += 1000
            elif name == 'residual':
                [r for r in rows if r['side'] == 'agent'][-1]['response']['external_delta_mm'] += 1000
            elif name == 'omit_command':
                mission = [r for r in mission if r['kind'] != 'command']
            elif name == 'wrong_seed':
                cfg = json.loads((root/'configuration.json').read_text())
                cfg['seed'] += 1
                (root/'configuration.json').write_text(json.dumps(cfg))
            elif name == 'body_pose_write':
                value = json.loads((root/'out/result.json').read_text())
                value['body_pose_writes'] = 1
                (root/'out/result.json').write_text(json.dumps(value))
            (root/'journal.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            (root/'out/mission.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in mission))
            try:
                changed = audit_session(root)
                out[name] = not changed['evidence_valid'] or not changed['execution_green']
            except (ValueError, KeyError, IndexError):
                out[name] = True
    return dict(rejected=out, green=all(out.values()))
