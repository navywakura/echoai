"""Read-only experiment reporting; writes only the private results document."""
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'lab/seed/s6b21-20261006'


def read(path):return json.loads(path.read_text()) if path.exists() else {}


def update():
    current=read(ROOT/'status.json');stage=current.get('stage','PREPARED')
    stamp=datetime.now(ZoneInfo('Europe/Madrid')).strftime('%d-%m-%Y %H:%M Madrid')
    manifest=read(REPO/'lab/kaggle/s6b21-20261006/input/manifest.json')
    intent=read(REPO/'lab/kaggle/s6b21-20261006/intent.json')
    config=manifest.get('configuration',intent.get('configuration',{}))
    budget=read(ROOT/'budget.json')
    lines=['# S6-B21-A — ejecución y resultados','',f'Actualización: {stamp}. Estado: **{stage}**.','',
           'B21-A implementa cobertura conjunta de duración/guarda, archivo de hipótesis',
           'y reparación por fallos medidos. Actor y juez conservan el contrato B20.',
           'Comparación: B20 una vez, aleatorio y balanceado con tres semillas cada uno.',
           'Máximo 18 propuestas por recorrido; cero llamadas al modelo.','',
           f"Partidas físicas reservadas: **{budget.get('scheduled_games',0)}/16000**. Cuatro procesos CPU locales.",
           'Secuencia: micro → replay/auditoría independiente → desarrollo amplio/auditoría',
           '→ conservación nueva/auditoría. Las fases amplias requieren un balanceado elegible.','']
    if stage in ('PREPARED_WAITING_B20_AUDIT','WAITING_B20_AUDIT'):
        lines+=['Todavía no se han jugado partidas B21. El supervisor espera recibos válidos',
                'de cierre y revisión aritmética de B20; después arranca automáticamente.','']
    if config:
        lines+=['| Recorrido | Intentos | Duraciones distintas | Mejor ganancia sin pérdidas | Primer pase |',
                '|---|---:|---:|---:|---|']
        for name,_,_ in config['cells']:
            steps=[read(p) for p in sorted((ROOT/'steps'/name).glob('*.json'))]
            events=[s['event'] for s in steps]
            values={e['proposal']['patches'][0]['set']['HOLD'] for e in events if e.get('proposal')}
            clean=[e['A']['gain'] for e in events if e.get('A') and not e['A']['loss_indices']]
            first=next((str(e['id']) for e in events if e['verdict']=='A_ONLY_PASS'),'pendiente')
            if len(events)==18 and first=='pendiente':first='ninguno'
            lines.append(f"| {name} | {len(events)} | {len(values)} | {max(clean) if clean else '—'} | {first} |")
        lines+=['']
    audit=read(ROOT/'micro-audit.json');closed=read(ROOT/'closed.json');arithmetic=read(ROOT/'arithmetic-review.json')
    lines+=['Auditoría del micro: '+('válida' if audit.get('valid') else 'pendiente')+'.',
            'Revisión aritmética y bytes exactos: '+('válida' if arithmetic.get('valid') else 'pendiente')+'.','']
    for phase in ('qualification','retention'):
        result=read(ROOT/(phase+'.json'))
        if result:
            audited=read(ROOT/(phase+'-audit.json')).get('valid',False)
            lines.append(phase+': ganadores '+(', '.join(result['winners']) or 'ninguno')+f'; auditoría válida: {audited}.')
    if stage=='BLOCKED_INSTRUMENT':lines+=['','Instrumento detenido: '+str(current.get('reason'))+'.']
    if closed:lines+=['','Cualificación completa: '+str(closed['qualification_passed'])+'.']
    lines+=['','**S6 sigue abierto.** Un pase de B21-A sería evidencia de búsqueda y conservación.',
            'Faltan atribución al neocórtex, descubrimiento desde SEMILLA, piloto, campaña y examen B1–B5.',
            'T/C/R/N/P del informe siguen como intervenciones posteriores separadas.','',
            '[Contrato congelado](ECHO45-S6-B21-A-DESIGN.md) · [Implementación](ECHO45-S6-B21-IMPLEMENTATION.md) ·',
            '[Estado](../lab/seed/s6b21-20261006/status.json) · [Pruebas](../lab/kaggle/s6b21-20261006/tests-final.log).','']
    dest=REPO/'docs/ECHO45-S6-B21-A-RESULTS.md';temp=dest.with_suffix('.tmp')
    temp.write_text('\n'.join(lines));temp.replace(dest)
    return stage


if __name__=='__main__':
    while True:
        stage=update()
        if '--watch' not in sys.argv or stage in ('QUALIFIED','CLOSED_NO_PROMOTION','BLOCKED_INSTRUMENT'):break
        time.sleep(45)
