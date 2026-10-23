# S6-PROBE1 · contrato del sondeo de capacidad

**Fecha:** 30-09-2026. **Estado:** revisado antes de congelar, **sin partidas**.
Requiere cierre negativo y ambas auditorías válidas de B12-R1: `closed.json`,
`campaign-audit.json` y `runtime-recovery1/campaign-audit.json`, enlazados por
hash a campaña y perfiles íntegros; examen sin abrir también en el filesystem.
**Tipo:** control de capacidad. **No** es mejora autónoma, **no** es evidencia de S6
y no cambia ningún veredicto de B12.

Origen: [respuesta de Opus](ECHO45-S6-CAPACITY-ANALYSIS-20260930.md), con las
correcciones de Nav del 30-09-2026 (redacción de conclusiones, pares
complementarios con ganancia cero, sin estimación de tiempo no medida).

## 1. Pregunta

Partiendo del programa final de B12 (idéntico en ECHO y FIJO, 378 niveles A),
¿contiene el lenguaje B12 sin cambios **una propuesta individual**, o **un par**
de propuestas, que pase V3 en desarrollo A?

## 2. Qué no hace

- 0 llamadas a modelos. No se genera ni se envía ningún prompt.
- No mide B (V4) ni abre el examen. `play_one` rechaza cualquier especificación
  que no sea A antes de jugar, y el test lo comprueba.
- No modifica fuentes congeladas, datos ni artefactos de B12. Solo **lee**
  `lab/seed/s6b12-20260930/{campaign.json, campaign/round-*.json, profile.json,
  closed.json, campaign-audit.json}` y los perfiles, fuentes y recibos R1 necesarios
  para comprobar la procedencia. Las mediciones y datos B no se usan en el sondeo.
- Ninguna solución que se encuentre se mostrará a un modelo ni se atribuirá a ECHO.

## 3. Base y paridad

- Base: `campaign.json.finals[*].strategy`. El sondeo exige que ECHO y FIJO coincidan.
- Antes de nada, el sondeo mide la base en A con replay y exige lo siguiente:
  378 niveles, `trace_sha256 = 4458a4c2…2c2d2c` (la medición B12 anterior a
  cada propuesta tras la aceptación), replay idéntico y
  `behavior_sha256 = 4cf4148e…93f1`. Si algo no coincide, se detiene.

## 4. E0 · censo por firmas (sin partidas)

**Universo.** `contrastive_grammar.choices(build_schema(rows_A_378, []))`: la
gramática B12 construida con las 80 partidas A y sin exclusiones de historial.
Contiene **70.208** propuestas.

**Firma.** Cada propuesta se añade al final del programa, así que gana donde su
guarda coincide (`settings`: última asignación). La firma es el conjunto de
decisiones A registradas en las que **cambia el valor consumido**:

| Control | Cuándo cuenta una decisión |
|---|---|
| `REVALIDATE_NOOP` | la guarda coincide, el valor difiere del efectivo de la base y el paso es sin cambio (`next_state == state`) |
| `HOLD` | la guarda coincide, valor ≠ 40 y las features coinciden con una lectura trazada de `self.hold = self.HOLD` (único punto de lectura) |
| `COOLDOWN_CAP` | la guarda coincide y `hold_remaining > v`, o bien `hold_remaining == 100` (valor recortado, conservador) |

**Inercia demostrable.** Si la firma está vacía, la ejecución determinista es
idéntica a la de la base. Para `REVALIDATE_NOOP`, la base solo usa valores 0/1,
y eso mantiene vacía la evidencia entre pasos. El código lo comprueba.
Una firma no vacía **no** implica un cambio de comportamiento: es una
sobreaproximación. Dos propuestas con la misma firma pueden divergir más tarde:
la clase sirve para muestrear, **no** demuestra equivalencia.

**Comprobaciones hechas sobre la caché B12, sin partidas nuevas:**

- Las features registradas reproducen exactamente `patch_hits` en las 80 partidas.
- 39.269 decisiones; **154 propuestas inertes** (todas `REVALIDATE_NOOP`).
- **15.454 clases**: REVALIDATE_NOOP 1.374 · HOLD 9.000 · COOLDOWN_CAP 5.080.
- Contraste con las 58 propuestas B12 medidas sobre la base 378: 8 se predecían
  inertes y ninguna cambió acciones (**0 violaciones**). 14 no inertes tampoco
  cambiaron acciones (sobreaproximación, como se esperaba) y 36 sí cambiaron.
- `E0_SHA = 3b67ba86…d7940`.

## 5. E1 · 200 propuestas individuales

- **Estrato fijo:** las 5 propuestas B12 distintas que se rechazaron con ganancia
  A positiva (todas `COOLDOWN_CAP`). Sus clases se excluyen del sorteo.
- **195 por sorteo**, una clase por candidato. El representante de cada clase es
  su propuesta canónica lexicográficamente mínima. Reparto proporcional al número
  de clases, con un mínimo de 30 por operador y resto mayor
  (empates por nombre): **RN 30 · HOLD 105 · COOLDOWN_CAP 60**. `random.Random(20260930)`.
  El orden de medición se baraja con el mismo generador.
- `PLAN_SHA = a0eb472c…34fcf`. El sondeo se detiene si su plan no coincide.
- **Veredicto.** Se aplica la condición V3 nativa (`game_selfimprove_b5.verify`):
  niveles A ≥ 378 + 2 y ninguna pérdida individual de niveles ni de score (1e-10).
  **Se cuenta como éxito** solo un V3 con **replay idéntico**.
- **Replay** (desviación declarada respecto a `verify`, que lo hace siempre): se
  repite cada candidato que pasa V3, y además los de índice múltiplo de 10 como
  auditoría de determinismo. Para los éxitos se exige también V2. Un negativo
  sin replay queda marcado `determinism=not_checked`: es cribado de capacidad,
  no una certificación de determinismo de todos los candidatos. Cualquier
  discrepancia de replay detiene el sondeo y conserva la evidencia del fallo.

## 6. E1b · hasta 50 pares

La regla está fijada antes de medir y usa solo los efectos A individuales de E1.
Entran en el grupo los candidatos que cambiaron acciones en alguna partida y no
fallaron el replay.

- **Nivel 1 (≤ 25):** partidas cambiadas disjuntas y predicción aditiva de
  niveles ≥ 1. Se ordena por predicción, luego por número de partidas con pérdida
  y luego por índice. **Un miembro puede tener ganancia individual 0.**
- **Nivel 2 (hasta completar 50):** operadores distintos que tocan alguna partida
  común, donde puede haber interacción. Se admiten los dos miembros con ganancia 0.
  Sorteo uniforme con `random.Random(20261001)`.
- **Programa:** base + los dos parches en orden canónico. Tiene 3 reglas, por
  debajo del límite de 32. Mismo veredicto y replay que en E1.

## 7. Conclusiones permitidas (redacción fija)

| Resultado | Se puede decir | No se puede decir |
|---|---|---|
| ≥ 1 individual pasa | «Existe al menos una solución individual desde 378» | Que ECHO o el modelo la habrían encontrado |
| ≥ 1 par pasa | «Justifica investigar composición» | Que ningún parche individual pueda funcionar |
| 0 y 0 | «No encontramos solución con este presupuesto» | «Lenguaje agotado» |

Los dos primeros resultados pueden darse a la vez. Se informan muestras y
éxitos por estrato. No se calcula una cota binomial global con la regla del 3:
hay cinco candidatos dirigidos y muestreo estratificado de clases con distinta
fracción de selección, además de selección adaptativa de pares.

## 8. Presupuesto

| Partida | Partidas de juego |
|---|---:|
| Base + replay | 160 |
| 200 individuales | 16.000 |
| Replays de auditoría (20) | 1.600 |
| 50 pares | 4.000 |
| Replays de auditoría de pares (5) | 400 |
| **Subtotal fijo** | **22.160** |
| Replays de éxitos | 80 por éxito |

Tope: **26.000** partidas (`reserve_games`). Si se alcanza, el sondeo se detiene
sin informe automático y se documenta como incompleto.
**No hay estimación de tiempo.** `estimate` mide la base y los 5 primeros
candidatos y escribe `estimate.json`; a partir de ahí se decide si continuar.
**Cuatro procesos** en la versión revisada. Se comprueba el arranque con `spawn`
sin jugar partidas; `estimate` verificará la paridad real y registrará el pico
RSS observado de los workers. El determinismo no garantiza que diez procesos
quepan en memoria o respeten los tiempos límite. No aumentar el paralelismo
después de congelar sin una condición de recursos declarada.

**Disco:** los diarios de B12 ocupan 33 GB para 13.487 partidas (~2,5 MB cada una).
Los diarios de decisiones de las primeras mediciones son **efímeros** y se borran
solo **después de guardar de forma duradera el resultado en la caché**. Se
conservan los de la base, todos los replays y las ejecuciones que fallen.
El borrado se limita a la ruta canónica de esa partida dentro del directorio
efímero del sondeo; se rechazan rutas externas. El registro resumido incluye
trayectoria, acciones y resultados necesarios para replay y comparación.

## 9. Ejecución

```bash
cd /home/user/REALRXOS/RXos/echoai
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m unittest tests.test_s6probe1
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6probe1 prepare
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6probe1 estimate
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6probe1 run
```

Se usa el **Python 3.12 y dependencias congeladas de B12**; el Python del
sistema no sirve para ejecutar mediciones de esta condición. Los tests no
juegan partidas. `estimate` mide únicamente base + replay y cinco candidatos,
registra tiempos, memoria y disco y termina con `ESTIMATE_READY`.

`wait-estimate` permite dejar esa calibración en una cola local: espera al
cierre auditado, se detiene si B12 termina sin cierre o si cambian las fuentes
del sondeo mientras espera, y ejecuta solo `estimate`. **Nunca lanza `run`.**
El comando se puede alojar en un servicio de usuario para sobrevivir al chat.
Un bloqueo exclusivo evita ejecutar dos comandos del sondeo simultáneamente.
Antes de reanudar se recomprueban E0, `PLAN_SHA`, el plan de pares y su asociación
con los resultados existentes. Cualquier error queda como `BLOCKED` con causa.

Artefactos: `lab/seed/s6probe1-20260930/` (`profile.json`, `parity.json`,
`e0.json`, `singles-plan.json`, `singles/NNN.json`, `pairs-plan.json`,
`pairs/NNN.json`, `result.json`, `budget.json`, `cache/`).

## 10. Auditoría independiente (Codex, por encargo de Nav)

- Paridad de la base con B12 (`parity.json`).
- Recalcular E0 y el plan desde la caché y comparar `E0_SHA` y `PLAN_SHA`.
- Volver a ejecutar una muestra de candidatos (incluidos todos los éxitos) y
  comparar `trace_sha256` en otro proceso y caché independiente. Pendiente
  después del sondeo: los replays de cribado no sustituyen esta revisión.
- Confirmar que no hay mediciones de B ni del examen: la caché solo contiene
  especificaciones A, y `budget.json` cuadra con lo que la caché contiene.

## 11. Pendiente para un contrato posterior de dos parches (no es de este sondeo)

- **Límite de 32 reglas.** `precise_patch.validate` rechaza más de 32. Treinta
  propuestas dobles pueden producir 60 reglas en SIN FILTRO, que acumula sin
  filtrar. Hay que elevarlo o redefinirlo **antes** de ese contrato, igual para
  los cuatro brazos.
- V3 se conserva y los dos parches se evalúan juntos. ECHO y FIJO tienen las
  mismas posibilidades, SEMILLA no cambia y SIN FILTRO recibe exactamente las
  propuestas ECHO.
