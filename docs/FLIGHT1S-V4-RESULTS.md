# FLIGHT-1S v4 — resultados

Estado: **cerrada roja**. Validación A interrumpida en 44/64 vuelos y con un
fallo de recuperación. Banco no autorizado. FLIGHT-1S no queda verde bajo v4.
Contrato: [FLIGHT1S-V4-DESIGN.md](FLIGHT1S-V4-DESIGN.md).

## Veredicto

| Grupo | Estado | Nota |
|---|---|---|
| Ejecución | rojo | 44/64 vuelos A, 0/4 controles negativos; cadena interrumpida |
| Recuperación | rojo | `perturbed-eddc87870377f61b-r5`: `not_recovered` |
| Separación | rojo | no evaluable: faltan bloques de mundo completos |
| Controles negativos | rojo | no volados |
| Estímulo, desafío perturbado, envolvente física 1000 mm | verde | sobre los 44 vuelos existentes |
| Repetición, higiene, configuración, código/historia congelados | verde | lock `8ed03f5a…cb71c` intacto |

Uno solo de los grupos rojos basta para impedir el verde. La recuperación
fallida es independiente de la interrupción: completar los 20 vuelos no
cambiaría el veredicto de A.

## Interrupción

El proceso `campaign run` murió el 2026-09-11 a las 07:09:37 (CEST) junto
con la sesión del agente que lo había lanzado. No hay traceback ni OOM del
kernel. En ese momento volaban `perturbed-02083ef67737f6d9-r7` y
`nominal-02083ef67737f6d9-r7`; sus contenedores terminaron solos y su
salida quedó en `/tmp`, fuera de `lab/`. No hubo `validation/report.json`.

Faltan 02083…-r7/r8 (4 vuelos), el mundo `ef7f22a49738b970` completo
(16) y los 4 negativos. Por diseño no hay reintentos ni exclusión de fallos de
infraestructura, y el coordinador congelado rechaza reabrir una etapa. No se
volaron vuelos nuevos para completar el denominador. El log original se copió
a `lab/flight1s-v4/run.log` (sha256 `156a2d2e…2701`).

## Evidencia existente

Auditoría de los 44 vuelos contra el lock: **662 comprobaciones, 0 hallazgos**.
Traza, ULog, identidad, asignación, parámetros leídos en ULog, mundo, fuerza,
duraciones y aritmética independiente reconstruidos; ningún fichero ajeno.

| Brazo | N | Mínimo, mm | Máximo, mm | >250 mm |
|---|---:|---:|---:|---:|
| Nominal | 22 | 85.459 | 291.350 | 2 |
| Perturbado | 22 | 399.588 | 643.178 | 22 |

Nominales >250 mm (diagnóstico v2, no criterio v4): `nominal-eddc…-r8`
256.294 y `nominal-02083…-r1` 291.350. Impulso perturbado 636–763 ppk; una
publicación de wrench en cada perturbado; desplazamiento máximo 658 mm.

Fallo de recuperación, del veredicto congelado: tras el pulso, desafío
457.476 mm, impulso 638 ppk, sin 3 s continuos dentro de 200 mm antes de
10 s; offset final 124.563 mm. El final dentro del radio no demuestra
permanencia. El detalle de entrada/salida de banda está en
[flight1s-v5/DESIGN.md](flight1s-v5/DESIGN.md); no altera este resultado.

Contraste por mundo, sólo diagnóstico (la puerta exige 4 bloques completos):

| Mundo | Parejas | Media d, mm | Mínimo d, mm |
|---|---:|---:|---:|
| 73e0dcb3241663a5 | 8/8 | 381.891 | 220.708 |
| eddc87870377f61b | 8/8 | 240.536 | 191.904 |
| 02083ef67737f6d9 | 6/8 | 325.441 | 269.410 |
| ef7f22a49738b970 | 0/8 | — | — |

Con cuatro mundos A es sólo puerta de ingeniería; estas medias no son
inferencia. La estabilidad observada se atribuye a PX4; echoAI no participa
en estos vuelos (`agent_in_gazebo=false`, `cortex_calls=0`, `wsp_writes=0`).

## Comprobaciones previas

Auditores históricos ejecutados de nuevo antes del lock:

| Versión | Comprobaciones | Hallazgos | Episodios reconstruidos | Resultado |
|---|---:|---:|---:|---|
| v1 | 375 | 0 | 48 | Evidencia válida, rojo |
| v2 | 435 | 0 | 48 | Evidencia válida, rojo |

Desarrollo v3 de `noaid_7n` (no entra en el denominador v4): 68 nominales
88.049–280.493 mm (1 >250) y 67 perturbados 393.057–677.017 mm. Regresión
previa al lock: 7/7 módulos verdes (`lab/flight1s-v4/regression.json`).

## Reproducir

Desde `echoai`:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s_v4_close audit
```

Reconstruye el cierre desde las trazas y lo compara con
`lab/echo3_flight1s_v4_report.json` (sha256 `ad998091…46b8`,
`kind=interrupted_closure`). `close` es de una escritura y se niega si el
informe existe. `nexus0/flight1s_v4_close.py` está fuera de `nexus0/flight1s_v4/`
para no alterar el inventario congelado; usa el contrato v4 sin cambios.
La orden congelada `flight1s_v4.campaign audit` no evalúa etapas sin
`report.json` y devuelve `evidence_valid=false`; esperado en esta cadena.
Las pruebas de adulteración de etapa del coordinador no se ejecutaron: no
hay informe de etapa sobre el que mutar.

Un verde v4 no habría significado que v2 era verde ni precisión nominal
≤250 mm. Esta cadena no acredita autonomía echoAI, vuelo real ni sim-to-real.
