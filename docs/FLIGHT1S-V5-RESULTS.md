# FLIGHT-1S v5 — resultados

Estado: **cerrada roja**. Validación A: 64/64 vuelos ejecutados, uno fallido
por infraestructura; el coordinador se detuvo antes de `report.json` y de los
controles negativos. Banco no autorizado. FLIGHT-1S no queda verde bajo v5.
Contrato: [flight1s-v5/DESIGN.md](flight1s-v5/DESIGN.md) (criterios v4).

## Veredicto

| Grupo | Estado | Caso rojo |
|---|---|---|
| Ejecución (episodios, higiene, configuración) | rojo | `nominal-02083ef67737f6d9-r1`: `mavlink_no_heartbeat` |
| Envolvente física | rojo | mismo vuelo: sin muestras |
| Separación | rojo | pareja incompleta en 02083…-r1 |
| Repetición | rojo | agregador heredado v2 lanzó `KeyError` con ese vuelo |
| Controles negativos | rojo | 0/4 volados |
| Informe de etapa | rojo | no existe `validation/report.json` |
| Estímulo, recuperación, desafío perturbado, denominador, envolvente v2 | verde | — |
| Código/historia/regresión congelados | verde | lock `3c599b36…aea3b` |

Todos los grupos rojos proceden de un único vuelo que no llegó a volar, de
los negativos no volados o del informe inexistente. Ningún grupo físico
evaluado sobre vuelos medidos está rojo. Por diseño no hay exclusión de fallos
de infraestructura ni reintentos: ese vuelo basta para el rojo.

## Fallo de infraestructura

`nominal-02083ef67737f6d9-r1` (slot 16): Gazebo listo y PX4 arrancado, pero
sin heartbeat MAVLink. 0 eventos del driver, 0 muestras de pose, contenedor
con código 1 tras 124.31 s de pared, sin ULog. El perturbado de la misma
pareja voló normal (509.373 mm, recuperado en 1410 ms). El fallo no se atribuye
al parche GNSS: el parche no interviene antes del heartbeat, pero no hay
evidencia directa de la causa; dos contenedores concurrentes en el mismo host
es una hipótesis, no un hallazgo.

## Parada del coordinador

Tras el vuelo 64, `contract.verdict` → `Bench._group_repetition` (v2, heredado
sin cambios) leyó `hover_horiz_rms_mm` de ese episodio y lanzó `KeyError`. El
proceso terminó sin escribir informe ni volar los 4 negativos. Es un defecto del
agregador heredado ante un episodio sin medida: habría afectado igual a v4.
No cambia el veredicto; impidió producirlo dentro de la cadena.

## Evidencia existente

Auditoría de los 64 vuelos contra el lock: **962 comprobaciones, 1 hallazgo**:
`stage_durations/nominal-02083…-r1`, el plan de etapas de un vuelo que no
existió. Todos los hallazgos recaen sobre episodios fallidos
(`findings_on_failed_episodes_only=true`). `evidence_valid=false` se conserva
tal como lo da la lógica congelada.

Imagen `v1.15.4-gpsaccuracy` (ID `5364c865…1d27`), binario PX4 `50c2793c…4c42`
(stock `05bc7c4c…b6b9`); diff de dos líneas `eph 0.9→0.2`,
`s_variance_m_s 0.4→0.158`; ruido inyectado intacto, comprobado dentro de la
imagen antes del lock. Regresión previa al lock: 8/8 módulos verdes.

Vuelos medidos (63; excluye el fallido, sólo descriptivo):

| Brazo | N | Mínimo, mm | Máximo, mm | >250 mm |
|---|---:|---:|---:|---:|
| Nominal | 31 | 90.417 | 224.261 | 0 |
| Perturbado | 32 | 415.654 | 645.331 | 32 |

32/32 perturbados recuperados (200 mm, 3 s, ventana 10 s; máximo 4892 ms).
Impulso 615–780 ppk; desplazamiento máximo 697 mm desde el inicio.

Contraste por mundo, diagnóstico sin el vuelo fallido (no es la puerta):

| Mundo | Parejas | Media d, mm | Mínimo d, mm |
|---|---:|---:|---:|
| 73e0dcb3241663a5 | 8/8 | 381.631 | 248.151 |
| eddc87870377f61b | 8/8 | 361.338 | 296.787 |
| 02083ef67737f6d9 | 7/8 | 418.083 | 308.341 |
| ef7f22a49738b970 | 8/8 | 386.709 | 323.519 |

Comparado con v4 (desarrollo, otro candidato): nominal máximo 291.350 → 224.261
mm y 1 perturbado no recuperado → 0. Son dos cadenas distintas con N pequeño;
no se presenta como efecto demostrado del parche. A es puerta de ingeniería
sin inferencia con cuatro mundos.

## Reproducir

Desde `echoai`:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s_v5_close audit
```

Reconstruye el cierre y lo compara con `lab/echo3_flight1s_v5_report.json`
(sha256 `a57bd4c5…7b26`, `kind=stopped_before_report_closure`). `close` es de
una escritura. El módulo está fuera de todo inventario congelado; reutiliza
las piezas congeladas de `verdict` y captura sólo el agregador que falló, cuyo
error queda registrado en `frozen_verdict`. Log de la cadena:
`lab/flight1s-v5-run.log` (`c694aac9…07d6`). `flight1s_v5.campaign audit`
devuelve `stages={}`, `evidence_valid=false`: esperado sin informe de etapa.

La estabilidad observada se atribuye a PX4; echoAI no participa
(`agent_in_gazebo=false`, `cortex_calls=0`, `wsp_writes=0`). No acredita
autonomía echoAI, vuelo real ni sim-to-real.
