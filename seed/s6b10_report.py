"""Use the same terminal proof checks for the B10 report, without exam reads."""
from collections import Counter
import json
import sys
from types import FunctionType
from seed import s6b9_report as previous

ROOT = previous.REPO / 'lab/seed/s6b10-20260929'
bindings = dict(previous.publish.__globals__, ROOT=ROOT, LABEL='S6-B10',
                RESULT_DOC='ECHO45-S6-B10-RESULTS.md', MARK_BEGIN='<!-- S6B10-RESULT-BEGIN -->',
                MARK_END='<!-- S6B10-RESULT-END -->')
publish_summary = FunctionType(previous.publish.__code__, bindings)


def report_text(root, result):
    lines = ['# S6-B10 · condiciones compatibles con observaciones', '',
             f"Estado: **{result['state']}**. S6 verde: **{'sí' if result['green'] else 'no'}**.", '',
             result['detail'], '',
             'Estas medidas son del banco sintético de desarrollo; no son puntuaciones ARC oficiales.',
             'Una ganancia agregada con regresión individual se rechaza. Solo B1–B5 permiten cerrar S6.', '']
    for phase in ('pilot', 'campaign'):
        path = root / (phase + '.json')
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        audit_path = root / (phase + '-audit.json')
        audited = audit_path.exists() and json.loads(audit_path.read_text()).get('valid') is True
        counts = Counter(v['verdict'] for v in data['verdicts'])
        lines += [f"## {'Piloto' if phase == 'pilot' else 'Campaña'}", '',
                  f"Suma A: ECHO **{data['paired_A']['echo']}**, FIJO **{data['paired_A']['fijo']}**. "
                  f"Aceptaciones ECHO: **{data['accepted_echo']}**. "
                  f"Auditoría independiente: **{'válida' if audited else 'pendiente'}**.", '',
                  'Veredictos: ' + ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + '.', '',
                  '| Brazo | Semilla | Propuesta (ID original) | Veredicto | A: antes→después | Pérdidas A/B |',
                  '|---|---:|---:|---|---:|---:|']
        for row in data['verdicts']:
            a, b = row.get('A'), row.get('B')
            levels = f"{a['before_levels']}→{a['after_levels']}" if isinstance(a, dict) else 'sin medida'
            losses = '/'.join(str(len(x['loss_indices'])) if isinstance(x, dict) else 'sin medida' for x in (a, b))
            lines.append(f"| {row['arm']} | {row['seed']} | {row['id']} | {row['verdict']} | {levels} | {losses} |")
        lines += ['', f'[Artefacto {phase}](../lab/seed/{root.name}/{phase}.json) · '
                  f'[Auditoría](../lab/seed/{root.name}/{phase}-audit.json).', '']
    if 'checks' in result:
        lines += ['## Examen reservado', '', '| Criterio | Resultado |', '|---|---|']
        lines += [f"| {key} | {'✅' if value else '❌'} |" for key, value in sorted(result['checks'].items())]
        lines += ['', '| Brazo | Niveles | Score |', '|---|---:|---:|']
        lines += [f"| {arm} | {value['levels']} | {value['score']} |" for arm, value in result['totals'].items()]
        lines += ['', f'[Auditoría del examen](../lab/seed/{root.name}/exam/audit.json).', '']
    lines += ['[Contrato](ECHO45-S6-B10-DESIGN.md) · [Recuperación](ECHO45-S6-B10-RECOVERY.md) ·',
              '[Estado](../lab/seed/s6b10-20260929/status.json) · [Plan posterior](ECHO45-POST-S6-PLAN-20260929.md).', '']
    return '\n'.join(lines)


def publish(result):
    (previous.REPO / 'docs/ECHO45-S6-B10-RESULTS.md').write_text(report_text(ROOT, result))
    publish_summary(result)


main = FunctionType(previous.main.__code__, dict(previous.main.__globals__, ROOT=ROOT,
                    LABEL='S6-B10', publish=publish))


if __name__ == '__main__':
    main(sys.argv[1:] == ['--watch'])
