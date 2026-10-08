"""Publish terminal artifacts only; never attach to or instrument an examination."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'lab/seed/s6b9-20260929'
LABEL='S6-B9'
RESULT_DOC='ECHO45-S6-B9-RESULTS.md'
MARK_BEGIN='<!-- S6B9-RESULT-BEGIN -->'
MARK_END='<!-- S6B9-RESULT-END -->'


def read(root,name):return json.loads((root/name).read_text())


def conclusion(root):
    if not (root/'closed.json').exists():
        state=read(root,'status.json')
        if state['stage']=='PENDING_ERROR':
            return {'state':'PENDIENTE POR ERROR','green':False,'detail':state.get('message','')}
        return None
    closed=read(root,'closed.json')
    if closed['result']=='PILOT_NO_PROMOTION':
        p,a=read(root,'pilot.json'),read(root,'pilot-audit.json')
        assert a['valid'] is True and p['promote'] is False and closed['s6_green'] is False
        assert not (p['accepted_echo']>0 and p['paired_A']['echo']>p['paired_A']['fijo'])
        assert not (root/'exam/opened.json').exists()
        return {'state':'PILOTO SIN PROMOCIÓN','green':False,
                'detail':f"ECHO {p['paired_A']['echo']}, FIJO {p['paired_A']['fijo']}; aceptaciones ECHO {p['accepted_echo']}. Piloto auditado, reserva sin abrir."}
    assert closed['result']=='EXAM_CLOSED'
    audit,completed=read(root,'exam/audit.json'),read(root,'completed.json')
    assert set(audit['checks'])=={'B1','B2','B3','B4','B5'}
    green=all(audit['checks'][k] is True for k in audit['checks'])
    assert audit['green'] is green and closed['s6_green'] is green
    assert audit['sources']==completed['sources'] and audit['strategies_sha256']==completed['strategies_sha256']
    if green:
        assert audit['training_audit'] is True and audit['model_payload_audit'] is True
        assert set(audit['replays'])=={'echo','fijo','semilla','sinfiltro'} and all(x is True for x in audit['replays'].values())
    return {'state':'EXAMEN VERDE' if green else 'EXAMEN ROJO','green':green,
            'detail':'Criterios: '+', '.join(f'{k}={v}' for k,v in audit['checks'].items())+'.',
            'checks':audit['checks'],'totals':audit['totals']}


def publish(result):
    stamp=datetime.now(timezone.utc).isoformat()
    text=(MARK_BEGIN+'\n'+f"**{LABEL} — {result['state']}. S6 {'VERDE' if result['green'] else 'todavía no verde'}.** "
          +result['detail']+f' [Resultado]({RESULT_DOC}) · [Estado](../lab/seed/{ROOT.name}/status.json).\n'+MARK_END)
    for name in ('NOW.md','STATUS.md','ECHO45-ECHO5-ROADMAP.md'):
        path=REPO/'docs'/name;value=path.read_text()
        if MARK_BEGIN in value:
            start=value.index(MARK_BEGIN);end=value.index(MARK_END,start)+len(MARK_END)
            value=value[:start]+text+value[end:]
        else:
            first,rest=value.split('\n',1);value=first+'\n\n'+text+'\n\n'+rest.lstrip('\n')
        path.write_text(value)
    path=REPO/'docs/ECHO4-ECHO5-TIMELINE.md';lines=path.read_text().splitlines()
    for i,line in enumerate(lines):
        if f'**{LABEL}:' in line:
            mark='✅' if result['green'] else '❌'
            lines[i]=f"| {mark} | **{LABEL}: propuesta y verificación del modelo** | {result['state']}. {result['detail']} [Resultado]({RESULT_DOC}) |"
    path.write_text('\n'.join(lines)+'\n')
    from seed.game_selfimprove import atomic
    atomic(ROOT/'documented.json',{'at':stamp,**result})


def main(watch):
    while True:
        result=conclusion(ROOT)
        if result is not None:
            publish(result);print(json.dumps(result),flush=True);return
        if not watch:
            print(LABEL+' sigue activo; no hay resultado terminal para publicar.');return
        time.sleep(30)


if __name__=='__main__':main(sys.argv[1:]==['--watch'])
