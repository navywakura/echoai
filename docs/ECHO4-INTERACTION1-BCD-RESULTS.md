# E4-INTERACTION-1 — resultados B/C/D

2026-09-22. **B/C/D cerradas; E4-INTERACTION-1 verde en su perfil declarado.**
Auditoría completa en proceso nuevo: `valid=true`, cero hallazgos,
`interaction1_green=true` en el recibo. Todas las trazas se reconstruyen.
El resultado se limita a decisiones aprendidas de un paso frente a dos
contrapartes con objetivos privados diseñados. No acredita conciencia,
negociación general, integración térmica ni el agente ECHO-4 completo.

110 fuentes fijadas antes del examen; las 104 de A y su evidencia permanecen
intactas. Digest de reproducción:
`d1c5b073e7ac406ddd855184cc6f4bd1176d354eed57438eb51af1383f040735`.

[Contrato previo](ECHO4-INTERACTION1-BCD-DESIGN.md) ·
[Informe](../lab/echo4/interaction1-bcd-v1/report.json) ·
[Lock](../lab/echo4/interaction1-bcd-v1/lock.json) ·
[Recibo](../lab/echo4/interaction1-bcd-v1/audit-receipt.json).

## Qué se implementó

- **B:** OTHER alimenta una hipótesis WSP16 sin hecho/extract, que indexa la
  Q original. Esta aprende si colaborar con la contraparte encontrada resulta
  conveniente. No hay una regla que ordene colaborar cuando el otro lo haga.
  El calendario de encuentros lo fija el entorno, no lo elige el aprendiz.
- **C:** identidad nueva, visibilidad incompleta, recibos ausentes, identidad
  ausente, incumplimiento, no participación, veto, coste alto, agotamiento,
  presupuesto cero y parada. Fallo parcial conserva gastos y bloquea reintentos.
  Un conflicto observado fuerza incertidumbre; no borra ni reescribe historia.
- **D:** dos cohortes nuevas, cinco brazos emparejados, orden inverso,
  reconstrucción pública y auditoría nativa completa en proceso nuevo.

Se conservan Agent.turn, CAM/T/Q y gate originales. Dos acciones realmente
ejecutadas y vetadas preceden a cada liquidación física. El aprendiz recibe
solo su producción menos su coste. Cada contraparte conserva CAM/T/Q propias,
240 turnos privados de formación y actualizaciones Q durante los encuentros.
Su incentivo privado +16/-16 mantiene preferencias diferentes; queda separado
del neto físico. Es un experimento asimétrico, no cooperación que haya emergido
sin objetivos diseñados. La celda de liquidación tiene Q cero: horizonte de
un paso, no planificación social multietapa.

Código nuevo: [creencias y Q](../echo4/interaction_learning.py),
[sesión y contabilidad](../echo4/interaction_social.py),
[casos y controles](../echo4/interaction_cases.py),
[campaña/auditor](../echo4/interaction_final.py),
[pruebas](../tests/test_echo4_interaction1bcd.py).

## D: ventaja después de la formación

Cada cohorte contiene ocho vidas por brazo: 480 encuentros por vida, primeros
288 de formación y últimos 192 puntuados. Q sigue actualizándose durante
puntuación, sin exploración forzada. Tres presupuestos iniciales de 4096,
sin recargas. Semillas 262001..262008 y 262101..262108, distintas de B.
Las secuencias son nuevas dentro de la misma familia balanceada de tareas;
no son nuevas especies de contraparte ni evidencia de generalización abierta.

Los totales puntuados coinciden en ambas cohortes:

| Brazo | Neto aprendiz por cohorte | Neto físico conjunto | Coste conjunto | Producción conjunta |
|---|---:|---:|---:|---:|
| Identidad + historia → Q | 6912 | 9984 | 4096 | 14080 |
| Sin distinguir identidades | 6144 | 6656 | 3584 | 10240 |
| Sin historia del otro | 6144 | 6656 | 3584 | 10240 |
| Siempre solo | 6144 | 6656 | 3584 | 10240 |
| Siempre colaborar | −3072 | 0 | 7680 | 7680 |

Ventaja del aprendiz **+768 por cohorte (+12,5%)** frente a solo/ablaciones;
conjunto **+3328 (+50%)**. Ambos superan el margen preregistrado >=256 frente
a cada control en cada cohorte. Ninguna vida pierde frente a solo **en la
ventana puntuada**. La diferencia desaparece al quitar historia o identidad:
evidencia funcional de que usar OTHER beneficia la decisión en este dominio.
Los controles solo/siempre colaborar tienen propuesta fija, no se presentan
como políticas aprendidas. Mantienen gate, costes y las mismas contrapartes.

Por vida puntuada: aprendiz 864; contraparte de preferencia (0,1,2), 352;
contraparte (1,2,0), 32. En el control solo: 768, 32 y 32 respectivamente.
Las identidades se permutan; el aprendiz no recibe sus preferencias privadas.

## Límite importante: el aprendizaje todavía cuesta

La mejora posterior **no amortiza el coste inicial para el aprendiz dentro
de estas 480 rondas**. No se oculta esa pérdida cambiando el horizonte:

| Cohorte | Aprendiz: formación | Aprendiz: vida completa | Solo: vida completa | Diferencia aprendiz | Neto conjunto completo / solo |
|---|---:|---:|---:|---:|---:|
| 1 | 7147 | 14059 | 15360 | −1301 | 20789 / 16640 |
| 2 | 7224 | 14136 | 15360 | −1224 | 20896 / 16640 |

También pierde en neto individual de vida completa frente a las ablaciones:
14343 y 14402 sin historia/identidad, respectivamente. El conjunto gana,
pero eso no convierte automáticamente en positiva la utilidad del aprendiz.
Cada vida focal pierde entre 119 y 180 frente a solo al incluir formación.
La contraparte que colabora gana entre 670 y 710; la otra empata con solo.
Frente al control de colaborar siempre, la contraparte colaboradora obtiene
menos durante la formación. El informe conserva cada identidad/brazo, no solo
la suma. No se acredita Pareto-mejora de toda la vida ni ventaja universal.

B, desarrollo: tres semillas, neto focal puntuado 2592 frente a 2304 de
solo/ablaciones; conjunto 3744 frente a 2496. Tampoco se usa B como examen.

## Verificación, presupuesto y límites

37 pruebas nuevas aprobadas y 11/11 testigos adversos de C. Regresión completa:
**723/723 pruebas ECHO-4**, más 33 de Q/T/inverso/encoder/gate del núcleo;
**756 pruebas distintas aprobadas**, sin fallos ni omisiones. Entradas inválidas,
fallos antes/después de liquidación, capacidad CAM, límite 512, fuentes o
artefactos alterados y JSON ambiguo se rechazan. Las predicciones preceden a
ambas acciones. Invertir el orden conserva toda la traza. El replay público
reconstruye OTHER sin ejecutar física ni acceder a Q privada ajena.

El banco principal consume 43200 turnos nativos de desarrollo y 230400 de
examen, incluyendo preformación y ejecuciones de orden inverso; C añade 6420.
Total **280020 turnos nativos**, más pruebas unitarias de desarrollo. El auditor
repite esta evidencia; no es una tercera cohorte. 16 vidas × 5 brazos × 480
encuentros = 38400 rondas primarias de D, otras tantas en orden inverso.
No se descuentan recursos usando créditos privados ni se eliminan pérdidas.

Invariantes: WSP16, aritmética entera, sin borrar CAM, sin hechos derivados
de predicción ni llamadas al LLM. La selección consume observaciones y memoria
propia; la privacidad aquí es separación de datos/política, no aislamiento
de seguridad entre procesos hostiles. Los perfiles no estacionarios conflictivos
provocan abstención; **reaprender una identidad cambiante queda sin demostrar**.
Agotamiento comprueba contabilidad y ausencia de producción gratuita, no
autorregulación térmica aprendida. No mensajes, persuasión o promesas.

## Reproducir

Desde `RXos`, con Python del sistema:

```bash
python3 -m unittest echoai.tests.test_echo4_interaction1bcd
python3 -m echoai.echo4.interaction_final verify echoai/lab/echo4/interaction1-bcd-v1
```

Regresión general ejecutada en esta entrega:

```bash
python3 -m unittest discover -s echoai/tests -t . -p 'test_echo4_*.py'
python3 -m unittest echoai.tests.test_qtable \
  echoai.tests.test_nexus0.TestWorld echoai.tests.test_nexus0.TestTConf \
  echoai.tests.test_nexus0.TestInverse echoai.tests.test_nexus0.TestEncoder \
  echoai.tests.test_nexus0.TestCellEncoder echoai.tests.test_nexus0.TestGate
```

Para otra copia de campaña, utilizar un directorio nuevo con `campaign` y
después `verify --write-receipt` en otro proceso. No sobrescribir el examen
sellado. El informe mantiene `interaction1_green=false` por diseño: únicamente
el recibo reconstructivo concede el cierre si todos los criterios pasan.

Siguiente fase tras el cierre: **E4-RELATION-1**, historia compartida y ventaja
transferible; después ROLES, INTEGRATE y RELEASE. `rxlabs/echoai-4` sigue siendo
destino previsto, no publicado. Hardware después; METAVERSE-1 último.
Sin Discord, modificación web, commit, push o publicación en esta entrega.
