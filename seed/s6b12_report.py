"""Read-only progress publisher. No solver, model, protected traces or submissions."""
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'lab/seed/s6b12-20260930'
BASE = REPO / 'lab/kaggle/s6b12-20260930'
DOC = REPO / 'docs/ECHO45-S6-B12-LIVE.md'


def optional(path):
    return json.loads(path.read_text()) if path.exists() else {}


@lru_cache(maxsize=8)
def completed_round(path, modified_ns, size):
    result = optional(path)
    return {'verdicts': [{k: event[k] for k in ('arm', 'verdict', 'A') if k in event}
                         for event in result['verdicts']],
            'requests': {arm: [{'context': row['context']} for row in batch]
                         for arm, batch in result['requests'].items()}}


def update():
    current = optional(ROOT / 'status.json')
    supervisor = optional(ROOT / 'supervisor.json')
    if (supervisor.get('state') == 'RUNNING' and supervisor.get('condition') == 'S6-B12-R1' and
            current.get('stage') == 'PENDING_ERROR' and current.get('at', '') < supervisor.get('at', '')):
        current = {'at': supervisor['at'], 'stage': 'RECOVERY_RECONSTRUCTING',
                   'condition': 'S6-B12-R1', 'previous_error': current,
                   'source': 'supervisor resumed after the recorded interruption'}
    closed = optional(ROOT / 'closed.json')
    exam = optional(ROOT / 'exam/audit.json')
    pilot = optional(ROOT / 'pilot-audit.json')
    preflight = optional(ROOT / 'preflight.json')
    audit = optional(ROOT / 'campaign-audit.json')
    recovery = optional(ROOT / 'runtime-recovery1/profile.json')
    recovery_audit = optional(ROOT / 'runtime-recovery1/campaign-audit.json')
    counts = {arm: {'evaluated': 0, 'accepted': 0, 'rejections': {}} for arm in ('echo', 'fijo')}
    levels = {arm: preflight.get('A_levels') for arm in counts}
    rounds, context_tokens, tiers = [], [], {}
    for path in sorted((ROOT / 'campaign').glob('round-*.json')):
        info = path.stat()
        result = completed_round(path, info.st_mtime_ns, info.st_size)
        rounds.append(path.stem)
        for event in result['verdicts']:
            row = counts[event['arm']]
            row['evaluated'] += 1
            if event['verdict'] == 'accepted':
                row['accepted'] += 1
                levels[event['arm']] = event.get('A', {}).get('after_levels', levels[event['arm']])
            else:
                row['rejections'][event['verdict']] = row['rejections'].get(event['verdict'], 0) + 1
        for batch in result['requests'].values():
            for request in batch:
                context = request['context']
                context_tokens.append(context['tokens'])
                tier = str(context['tier'])
                tiers[tier] = tiers.get(tier, 0) + 1
    jobs = []
    folders = sorted(BASE.glob('c[0-5]')) + sorted((BASE / 'runtime-recovery1').glob('c[2-5]'))
    for folder in folders:
        sent = optional(folder / 'submitted.json')
        if not sent:
            continue
        terminal = optional(folder / 'terminal.json')
        jobs.append({'stage': folder.name + (' R1' if folder.parent.name == 'runtime-recovery1' else ''),
                     'ref': sent['ref'],
                     'state': terminal.get('status', current.get('status', 'SUBMITTED')
                         if current.get('ref') == sent['ref'] or
                         (not current.get('ref') and current.get('job') == folder.name) else 'SUBMITTED')})
    green = bool(closed.get('s6_green') and exam.get('green') and
                 set(exam.get('checks', {})) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(exam['checks'].values()) and
                 (not recovery or (recovery_audit.get('valid') and closed.get('recovery_profile_sha256') ==
                                   recovery_audit.get('profile_sha256'))))
    condition = 'S6-B12-R1' if recovery else 'S6-B12'
    result = {'updated_at': datetime.now(timezone.utc).isoformat(), 'condition': condition,
              'running': supervisor.get('state') == 'RUNNING', 'stage': current,
              'rounds_completed': len(rounds), 'rounds_total': 6, 'arms': counts,
              'pilot_inheritance_valid': bool(pilot.get('valid')),
              'preflight_valid': bool(preflight.get('pass')), 'campaign_audit_valid': bool(audit.get('valid')),
              'jobs': jobs, 'max_prompt_tokens': max(context_tokens, default=None), 'context_tiers': tiers,
              'development_levels': {'semilla': preflight.get('A_levels'), **levels},
              'recovery_audit_valid': bool(recovery_audit.get('valid')),
              's6_green': green, 'echo45_green': False, 'checks': exam.get('checks', {}),
              'closed': closed, 'budget': optional(ROOT / 'budget.json')}
    lines = ['# ' + condition + ' · seguimiento', '', 'Actualizado: ' + result['updated_at'], '',
             'Estado: **' + current.get('stage', 'PENDIENTE') + '**. Servicio: **' + supervisor.get('state', 'DESCONOCIDO') + '**.', '',
             '- Piloto B11 heredado: ' + ('36 peticiones verificadas; auditoría original válida.' if pilot.get('valid') else 'verificación pendiente.'),
             '- Paridad de la base y observador: ' + ('aprobada.' if preflight.get('pass') else 'pendiente.'),
             f'- Campaña: **{len(rounds)}/6 rondas completas**.',
             '- Auditoría independiente de campaña: ' + ('aprobada.' if audit.get('valid') else 'pendiente.'),
             '- Examen de cuatro brazos: ' + ('cerrado y auditado.' if exam else 'abierto, en curso.' if (ROOT / 'exam/opened.json').exists() else 'sin abrir.'), '',
             '| Brazo | Propuestas de rondas completas | Aceptadas | Rechazos |', '|---|---:|---:|---|']
    for arm, row in counts.items():
        lines += [f"| {arm.upper()} | {row['evaluated']}/30 | {row['accepted']} | {json.dumps(row['rejections'])} |"]
    lines += ['', f"Niveles en desarrollo A (80 partidas): SEMILLA **{preflight.get('A_levels', '?')}**, "
              f"ECHO **{levels['echo']}**, FIJO **{levels['fijo']}**. No es una puntuación oficial ARC."]
    if recovery:
        lines += ['', 'R1 amplía el límite remoto a 7200 s por trabajo; conserva la cancelación original '
                  'y exige reproducir las siete respuestas previas. El cómputo repetido cuenta. '
                  '[Condición y diagnóstico](ECHO45-S6-B12-RECOVERY1.md).']
    if current.get('label'):
        lines += ['', 'Medición activa: `' + current['label'] + f"`, {current.get('completed', '?')}/{current.get('total', '?')} partidas."]
    if current.get('message'):
        lines += ['', 'Incidencia: ' + current['message']]
    if context_tokens:
        lines += ['', f'Máximo de contexto en rondas completas: **{max(context_tokens)}/6000 tokens**.']
    if jobs:
        lines += ['', 'Trabajos privados Kaggle:']
        lines += ['- [' + j['stage'] + '](https://www.kaggle.com/code/' + j['ref'] + '): ' + j['state'] for j in jobs]
    if exam:
        lines += ['', 'Criterios: `' + json.dumps(exam['checks'], sort_keys=True) + '`.']
    lines += ['', 'S6: **' + ('VERDE' if green else 'NO VERDE / PENDIENTE') + '**.', '',
              'ECHO-4.5 global sigue pendiente de sus otras puertas: transferencia y comparación final ARC-2/3, envío y publicación. '
              'Un cierre S6 positivo no cambia por sí solo esos resultados.', '',
              '[Resultados](ECHO45-S6-B12-RESULTS.md) · [Contrato](ECHO45-S6-B12-DESIGN.md) · [Roadmap](ECHO45-ECHO5-ROADMAP.md).', '']
    doc_temporary = DOC.with_name(DOC.name + '.tmp-' + str(os.getpid()))
    doc_temporary.write_text('\n'.join(lines))
    doc_temporary.replace(DOC)
    temporary = ROOT / ('progress.json.tmp-' + str(os.getpid()))
    temporary.write_text(json.dumps(result, sort_keys=True) + '\n')
    temporary.replace(ROOT / 'progress.json')
    return result


def watch():
    while True:
        result = update()
        if not result['running']:
            break
        time.sleep(30)


if __name__ == '__main__':
    if sys.argv[1:] == ['--once']:
        row = update()
        print(json.dumps({k: row[k] for k in ('stage', 'rounds_completed', 's6_green')}))
    elif sys.argv[1:] == ['--watch']:
        watch()
    else:
        raise SystemExit('use --once or --watch')
