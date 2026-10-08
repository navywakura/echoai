"""Private progress report; reads receipts and never sends feedback to search."""
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'lab/seed/s6b22-20261006'


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def update():
    current=read(ROOT/'status.json');manifest=read(ROOT/'input/manifest.json');budget=read(ROOT/'budget.json')
    finished=list((ROOT/'executions/completed').glob('*.json'))
    started=list((ROOT/'executions/started').glob('*.json'))
    stamp=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%d-%m-%Y %H:%M Madrid')
    lines=['# S6-B22 — implementación y resultados','',f"Actualización: {stamp}. Estado: **{current.get('stage','NOT_RUN')}**.",'',
           'Primera etapa: B22-V y piloto B22-S de ocho pares. Límite de 15.336 partidas;',
           'cuatro procesos CPU locales, cero llamadas LLM. Cada medición tiene replay y',
           'auditoría en proceso y caché independientes. Los intentos fallidos conservan su coste.','',
           f"Reservadas: {budget.get('scheduled_games',0)}; iniciadas: {len(started)}; completadas: {len(finished)}.",'']
    for phase in ('v-micro','v-broad','v-new'):
        result=read(ROOT/(phase+'.json'))
        if result:
            lines.append(f"- {phase}: {'PASS' if result['passed'] else 'FAIL'}; {result['base_levels']} → {result['levels']} niveles; pérdidas {result['diff']['loss_indices']}; auditado.")
    lines+=['','| Recorrido S | Intentos auditados | Reparaciones | Primer pase |','|---|---:|---:|---|']
    for name,kind,seed in manifest.get('configuration',{}).get('cells',[]):
        events=[read(p)['event'] for p in sorted((ROOT/'steps'/name).glob('*.json'))]
        first=next((str(e['id']) for e in events if e['verdict']=='A_ONLY_PASS'),'ninguno' if len(events)==18 else 'pendiente')
        lines.append(f"| {name} | {len(events)} | {sum(e['schedule']['phase']=='repair' for e in events)} | {first} |")
    selector=read(ROOT/'selector.json');closed=read(ROOT/'closed.json')
    if selector:
        lines+=['','Resultado del piloto emparejado: `'+json.dumps(selector['pilot'],ensure_ascii=False)+'`.']
        lines+=['','Transferencia de finalistas: `'+json.dumps(selector['transfer'],ensure_ascii=False)+'`.']
    if current.get('stage')=='INVALID':lines+=['','Instrumento detenido: '+current.get('reason','')+'.']
    if closed:lines+=['',f"B22-V: **{closed['V']}**. B22-S: **{closed['S']}** (confirmación nueva pendiente)."]
    lines+=['','B22-N y B22-E: **NOT_RUN**, fuera del presupuesto inicial. Requieren sus',
            'contratos de modelo, confirmación, piloto/campaña y examen desde SEMILLA.',
            '**S6 sigue abierto.** Un resultado V/S no acredita B1–B5 ni una puntuación ARC.','',
            '[Contrato](ECHO45-S6-B22-DESIGN.md) · [Implementación](ECHO45-S6-B22-IMPLEMENTATION.md) ·',
            '[Estado](../lab/seed/s6b22-20261006/status.json) · [Pruebas](../lab/seed/s6b22-20261006/tests-final.log).','']
    dest=REPO/'docs/ECHO45-S6-B22-RESULTS.md';temp=dest.with_suffix('.tmp')
    temp.write_text('\n'.join(lines));temp.replace(dest)
    return current.get('stage')


if __name__=='__main__':
    while True:
        stage=update()
        if '--watch' not in sys.argv or stage in ('CLOSED','INVALID'):break
        time.sleep(45)
