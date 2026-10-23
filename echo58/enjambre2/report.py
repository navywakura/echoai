"""Descriptive development report; never interprets three macros as an exam."""
import argparse
from pathlib import Path
import json

from . import bench as b
from .transport import ATTACKS,require
from ..crece.artifacts import publish,save_new

FIELDS=('score','solved','failed','harm','episodes','altered_postcards','exposure_queries',
        'affected_memory_responses','global_asks','abstentions')


def summarize(rows):
    grouped={}
    for attack in ATTACKS:
        grouped[attack]={}
        for arm in b.ARMS:
            values=[rows[b.name((arm,'none' if arm=='honesto' else attack,m))]
                for m in b.MACROS if b.name((arm,'none' if arm=='honesto' else attack,m)) in rows]
            if values:
                grouped[attack][arm]={field:sum(v[field] for v in values) for field in FIELDS}
                grouped[attack][arm]['by_kind']={kind:{field:sum(v['by_kind_details'][kind][field] for v in values)
                    for field in ('harm','episodes','failed','score','solved')} for kind in b.KINDS}
                grouped[attack][arm]['trust_by_author']={str(a):{field:sum(v['trust_by_author'][str(a)][field] for v in values)
                    for field in ('good','bad')} for a in range(4)}
    exposed={attack:any(v['exposure_queries']>0 for arm,v in grouped[attack].items() if arm not in ('honesto','sin_global','oraculo')) for attack in ATTACKS}
    comparisons={}
    for attack,group in grouped.items():
        if all(arm in group for arm in ('prudente','ingenuo','por_autor','sin_global')):
            p=group['prudente']
            comparisons[attack]={'harm_leq_ingenuo':p['harm']<=group['ingenuo']['harm'],
                'harm_leq_sin_global':p['harm']<=group['sin_global']['harm'],
                'score_lt_sin_global':p['score']<group['sin_global']['score'],
                'score_lt_por_autor':p['score']<group['por_autor']['score']}
    return {'phase':'development','exam_run':False,'scientific_exam_verdict':None,
        'macros':3,'groups':grouped,'attack_exposure':exposed,'descriptive_comparisons':comparisons,
        'honest_reference_reused':True,'statistical_tests_performed':False}


def render(root):
    root=Path(root);audit=json.loads((root/'audit.json').read_text())
    require(audit['audit_green'] is True and audit['completed_sha256']==b.sha(root/'completed.json'),'matching green audit required')
    summary=summarize(audit['rows']);save_new(root/'results.json',summary)
    lines=['# C v2 · ENJAMBRE con mentiroso: desarrollo','',
        '**48 trabajos de desarrollo; examen cerrado.** Auditoría técnica VERDE.',
        'Tres macros, cuatro agentes, ocho mundos por macro,30rondas y300pasos por episodio.',
        'No hay veredicto científico de examen ni pruebas estadísticas sobre estas tres macros.','',
        '| Ataque | Brazo | Puntuación ↓ | Daño ↓ | Resueltos /24 | Fallidos | Consultas expuestas | Respuestas afectadas |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for attack,group in summary['groups'].items():
        for arm,row in group.items():
            lines.append(f"| {attack} | {arm} | {row['score']} | {row['harm']} | {row['solved']} | {row['failed']} | "
                f"{row['exposure_queries']} | {row['affected_memory_responses']} |")
    lines+=['','Menor puntuación: resolver antes; un mundo no resuelto cuenta31. La referencia',
        '`honesto` se ejecutó una sola vez por macro: se muestra en cada ataque como la misma',
        'referencia, nunca como tres muestras independientes.','',
        'Exposición significa que una postal alterada de otro agente alcanzó una consulta global,',
        'después de la precedencia local/privada/notas. Respuesta afectada significa que retirar',
        'esas postales de esa misma consulta cambia su respuesta de memoria. No prueba por sí',
        'sola un cambio de acción ni identifica la causa de cada daño.','',
        '## Lectura descriptiva','']
    for attack in ATTACKS:
        lines.append(f"- `{attack}`: exposición {'presente' if summary['attack_exposure'][attack] else 'ausente: inconcluso'}.")
        if attack in summary['descriptive_comparisons']:
            values=summary['descriptive_comparisons'][attack]
            lines.append('  Comparaciones descriptivas: '+', '.join(f'{k}={v}' for k,v in values.items())+'.')
    lines+=['','## Desglose por tipo de mundo','',
        '| Ataque | Brazo | Tipo | Puntuación ↓ | Daño ↓ | Resueltos /6 | Fallidos |',
        '|---|---|---|---:|---:|---:|---:|']
    for attack,group in summary['groups'].items():
        for arm,row in group.items():
            for kind,k in row['by_kind'].items():
                lines.append(f"| {attack} | {arm} | {kind} | {k['score']} | {k['harm']} | {k['solved']} | {k['failed']} |")
    lines+=['','## Confianza por autor','',
        'Cada celda es aciertos en disputa / errores, sumados sobre observadores y macros.',
        'La suma es descriptiva: cada agente conserva su propio registro; no decide con esta suma.',
        'El autor malicioso cambia con macro%4; los registros individuales están en cada recibo.',
        '| Ataque | Brazo | Autor0 | Autor1 | Autor2 | Autor3 |','|---|---|---:|---:|---:|---:|']
    for attack,group in summary['groups'].items():
        for arm,row in group.items():
            cells=[f"{row['trust_by_author'][str(a)]['good']}/{row['trust_by_author'][str(a)]['bad']}" for a in range(4)]
            lines.append('| '+attack+' | '+arm+' | '+' | '.join(cells)+' |')
    lines+=['','Un empate con `por_autor` no demuestra una ventaja de la jerarquía de riesgo.',
        'Sin exposición real, un ataque no puede presentarse como una defensa exitosa.',
        'Estos resultados son de desarrollo; ninguna comparación activa un examen automáticamente.','',
        '## Límites del mecanismo','',
        '- Una adaptación de riesgo a lectura de memoria, no el selector completo de LINK-3.',
        '- Un emisor autenticado altera solo el tablón global. No hay suplantación, colusión,',
        '  sabotaje físico ni falsificación de notas o peticiones de ayuda.',
        '- La confianza se contrasta con experiencia propia, una vez por clave y autor.',
        '  Una excepción local puede desacreditar una generalización honesta.',
        '- RM no entrena confianza; utiliza la obtenida en L1/L2. Exigir confirmación también',
        '  puede suprimir información útil, especialmente con autores nuevos.',
        '- El mundo, la política física y la cooperación son los mismos mecanismos humanos',
        '  programados de C v1. No se demuestra invención de cooperación ni defensa ante todo atacante.','',
        '## Custodia y siguiente decisión','',
        'Fuentes/dependencias/contrato/agenda congelados antes de ejecutar; recibos exclusivos de',
        'cada trabajo, rondas, observaciones reales, publicaciones original/enviada y consultas.',
        'Auditoría offline: recuento de métricas, reconstrucción de postales propias y notas,',
        'ataques, confianza y resoluciones. No vuelve a jugar mundos ni toca exámenes antiguos.',
        f"Preflight SHA256: `{audit['preflight_sha256']}`.",
        f"Completed SHA256: `{audit['completed_sha256']}`.",
        'Sin LLM, API, GPU, Hugging Face o publicación web. Conservar este desarrollo; Nav',
        'decide el siguiente paso con sus resultados. No se cambian ataques ni reglas para buscar verde.','']
    publish(root/'report.md','\n'.join(lines).encode())
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    print(b.canonical(render(parser.parse_args().root)))
