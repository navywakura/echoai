# S6-PROBE2 · contrato de la búsqueda dirigida HOLD 0/1

**Fecha:** 01-10-2026. **Estado:** preparado, **sin ejecutar** y pendiente de la
revisión de Codex. No se ha jugado ninguna partida de PROBE2.
**Tipo:** control de capacidad **dirigido después de conocer PROBE1**. No es mejora
autónoma, no es evidencia de S6 y no cambia ningún veredicto de B12 ni de PROBE1.

Origen: [encargo](ECHO45-S6-PROBE2-HANDOFF.md) · [resultados PROBE1](ECHO45-S6-PROBE1-RESULTS.md).

## 1. Selección posterior declarada e hipótesis

PROBE1 encontró ganancia de +4 niveles en A53 solo con `HOLD 0` y `HOLD 1`
(candidatos 178 y 77), siempre con pérdidas de score en otras partidas.
**+4 en A53 sin ninguna pérdida bastaría para V3** (378 → 382 ≥ 380).
PROBE2 se diseñó **después** de ver esos resultados y lo declara así.

- **H1:** las observaciones disponibles cuando se consume HOLD permiten
  distinguir cuándo una espera corta ayuda (A53) de cuándo empeora el score
  (A51, A76, A68, A77).
- **H2:** las guardas de la gramática actual expresan esa distinción.

Que esta búsqueda acotada fracase no refuta H1 ni H2 por sí solo.

## 2. Análisis previo (datos existentes, sin partidas nuevas)

Fuente: la caché de PROBE1, en solo lectura. Su base reproduce la de B12
(`4458a4c2…`).

- **HOLD solo se lee en 10 de las 80 partidas A** de la base: 4, 18, 21, 42,
  51, 53, 59, 68, 76 y 77. Son 141 lecturas, todas con valor 40, y 60 de ellas
  en A53.
- **Hay muy poca información en las lecturas.** En las lecturas aplicadas por
  77 y 178, todas las features valen lo mismo (`goal_evidence=1`,
  `reset_useful=1`, `pending_effect=0`, `body_known=1`, el resto 0), salvo
  **`level` y `world_events`**. Son las únicas que varían y, por tanto, las
  únicas candidatas a separar los casos útiles de los dañinos.
- **Candidato 178** (`HOLD 0` si `world_events ≥ 80`): en A53 pasa de 1 a 5
  niveles, con primera divergencia en el paso 263, en el nivel 1. En A68
  diverge en el paso 655, ya en los niveles 2 y 3, aunque también se aplicó en
  el nivel 1 sin cambiar acciones. En A77 diverge en el paso 1408, en el nivel 4.
  En A51 y A76 se aplicó sin cambiar ninguna acción.
- **Candidato 77** (`HOLD 1` si `goal_evidence=1`): se aplica desde los primeros
  eventos en las diez partidas. En A53 diverge en el paso 98. Gana en A18 y A53
  y pierde score en A51 y A76.

Esto sirve para preparar la búsqueda, **no** para afirmar que una guarda concreta
funcionará: las trayectorias divergen después del primer cambio.

## 3. Universo y plan

- **Universo:** todas las propuestas legales `HOLD ∈ {0, 1}` de
  `contrastive_grammar.choices(build_schema(rows_A_378, []))`. Una regla, de 1 a 3
  guardas sobre features observables. **1.004** propuestas.
- **Selección:** se queda con las que coinciden con al menos una lectura de HOLD
  de la base **en A53**: **874**. El número 53 solo decide qué se mide; ninguna
  guarda lo consulta. Lo mismo vale para semillas, mapas o respuestas: no son
  entradas de la política.
- **Firma:** valor + conjunto de lecturas de la base que coinciden, partida a
  partida: **126** firmas. Una firma común solo garantiza la misma primera
  divergencia; **no** demuestra equivalencia. Por eso se miden **las 874**, no
  un representante por firma.
- **Orden:** etapa 1, el representante de cada firma (la propuesta canónica
  mínima), 126 en total; etapa 2, las 748 restantes. Dentro de cada etapa, menos
  partidas tocadas primero y después orden canónico. Ambas etapas se informan
  por separado.
- `PLAN_SHA = a725b39f…be66b`. El sondeo se detiene si su plan o su presupuesto
  difieren.

## 4. Cribado exacto por partidas tocadas

**Argumento.** HOLD se consume en un único punto trazado
(`self.hold = self.HOLD`, `agent.py`). Si ninguna lectura de la base de una
partida coincide con la guarda, el valor consumido no cambia en ningún paso y
la ejecución determinista de esa partida es **idéntica** a la base.

**Comprobación con datos ya medidos.** En los 105 candidatos HOLD de PROBE1,
medidos en las 80 partidas, ningún efecto apareció fuera de las partidas
tocadas según esta regla: **0 contradicciones** (test).

**Cribado.** Cada candidato se mide solo en las partidas que toca (4–10).
**Superviviente** = ninguna pérdida de niveles ni de score en esas partidas y
**≥ +2 niveles** en ellas. Como las partidas no tocadas quedan idénticas, este
criterio es V3 exacto si el argumento es correcto. Aun así, **no se declara V3
desde el cribado**: ver §5.

## 5. Verificación en las 80 partidas A

- **Supervivientes:** se miden las 80 partidas A, reutilizando la caché de las
  partidas cribadas, y además un **replay completo**. **Éxito** = V3 nativo
  (≥ 380 niveles, ninguna pérdida individual de niveles ni score, tolerancia
  1e-10) **y** replay idéntico. Como máximo se verifican **30**; si hay más
  supervivientes, el informe dice «medición incompleta».
- **Muestra fija de solidez:** las posiciones 0, 200, 400, 600 y 800 del plan
  se miden en las 80 partidas A, sobrevivan o no. Se exige que todas las
  partidas no tocadas tengan comportamiento idéntico a la base (acciones,
  frames, niveles, acciones por nivel, reinicios y score).
  En `run` cada comprobación se realiza al llegar a su posición, antes de
  continuar el cribado. En `estimate` no se ejecuta la muestra completa.
- **Controles de PROBE1:** los candidatos 77 y 178 están en el plan (posiciones
  93 y 3). Sus registros de cribado deben coincidir byte a byte con los de la
  caché de PROBE1.
- **Replays de negativos:** el cribado de cada posición múltiplo de 10 se
  repite: 88 replays.

**Una discrepancia de replay, un cambio en una partida no tocada o una diferencia
en un control detiene el sondeo** y conserva la evidencia en `failures/`. Ninguno
de esos casos se convierte en una conclusión negativa de capacidad.

## 6. Conclusiones permitidas

| Resultado | Se dice | No se dice |
|---|---|---|
| ≥ 1 verificado pasa V3 con replay idéntico | El lenguaje actual alcanza V3 desde 378 en A (control de capacidad, V4 sin evaluar) | Descubrimiento autónomo, cierre de S6, que ECHO lo encontraría |
| 0 pasan, medición completa | «Sin solución en esta búsqueda dirigida y con este presupuesto» | Lenguaje agotado; refutación de H1 o H2 |
| Medición detenida o incompleta | «Medición incompleta» y el motivo | Cualquier conclusión de capacidad |

El informe separa los descartes del cribado, los fallos en A completo y lo que
quedó sin medir. Los parches ganadores **no** se muestran a ningún modelo, no
se usan como ejemplos ni etiquetas y no se promueven a ECHO. Ampliar las
features, las guardas o los operadores, o pasar a dos parches, requiere otra
condición declarada.

## 7. Presupuesto (partidas de juego)

| Partida | Partidas |
|---|---:|
| Base + replay | 160 |
| Cribado (874 candidatos, partidas tocadas) | 8.386 |
| Replays de cribado (88) | 841 |
| Muestra de solidez (partidas no tocadas) | 357 |
| Reserva para supervivientes (30 × 160) | 4.800 |
| **Tope `MAX_GAMES`** | **14.544** |

Los trabajos interrumpidos también cuentan. **No hay estimación de tiempo:**
`estimate` mide la base y los 5 primeros candidatos (4, 4, 6, 6 y 6 partidas) y
escribe `estimate.json`. Como referencia sin valor de estimación, PROBE1 midió
unas 40 partidas por minuto con 4 procesos.
La calibración también repite el cribado de la posición 0 (4 partidas):
160 de base + 26 de cribado + 4 de replay = **190 partidas** previstas.

## 8. Custodia

- 0 llamadas al modelo. B y examen cerrados: `play_one` y los envoltorios de
  `measure` rechazan cualquier especificación que no sea A **antes** de jugar o
  de leer la caché.
- Directorio propio `lab/seed/s6probe2-20261001/`, con caché, presupuesto y
  diarios propios. Se reutiliza la maquinaria de PROBE1 (`play_one`, `_measure`,
  `reserve_games`), reasignada a este directorio; no hay una segunda
  implementación. Los diarios son efímeros en el cribado y se conservan en la
  base, en los replays y ante errores. El registro de cada partida se guarda
  antes de borrar su diario.
- 4 procesos y el Python 3.12 congelado de B12. Perfil congelado: fuentes,
  configuración, perfil de PROBE1, `result.json` de PROBE1
  (`16afe62e…a102ba64`) y recibo de su auditoría independiente.

## 9. Puerta: auditoría independiente de PROBE1

`prepare` exige `lab/seed/s6probe1-20260930-audit/audit.json` con
`valid: true`, `sample_single_indices` que incluya **77 y 178** y una
`cache_root` distinta de la de PROBE1. La realiza Codex, fuera de este código,
con la muestra fijada antes de reejecutar. Debe incluir también un +1 sin
pérdidas (p. ej. 31) y un control negativo. Si el formato final del recibo es
otro, hay que ajustar `probe1_closure` **antes** de congelar el perfil.

Revisión de Codex antes de congelar: el recibo se vincula al perfil y al
resultado exactos de PROBE1, y a los hashes de los cuatro candidatos
reejecutados (2, 31, 77, 178), con base reproducida, fuentes y planes
comprobados y origen A exclusivamente. La ruta de caché se resuelve de
forma canónica y se rechaza cualquier subdirectorio de PROBE1. Los controles
77/178 se recomprueban también al reanudar desde recibos ya guardados.

## 10. Ejecución

```bash
cd /home/roger/REALRXOS/RXos/echoai
PY=lab/arc3/ARC-AGI-3-Agents/.venv/bin/python
PYTHONPATH=. $PY -m unittest tests.test_s6probe2   # 11 tests, sin partidas
PYTHONPATH=. $PY -m seed.s6probe2 prepare          # exige la auditoría de PROBE1
PYTHONPATH=. $PY -m seed.s6probe2 estimate         # base + 5 candidatos → estimate.json
PYTHONPATH=. $PY -m seed.s6probe2 run              # reanudable; ECHO45-S6-PROBE2-RESULTS.md
```
