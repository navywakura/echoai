# Respuesta de Opus 5.5 al informe S6 (30-09-2026)

**Responde a:** [ECHO45-S6-RESEARCH-BRIEF-20260930.md](ECHO45-S6-RESEARCH-BRIEF-20260930.md).
**Estado:** propuesta. No se ha implementado ni medido nada. No se han lanzado
partidas, inferencias ni campañas. La auditoría B12-R1 seguía en marcha
(`MEASURING`) y no se ha tocado.
**S6: NO VERDE.**

Todas las cifras de §1 salen de `lab/seed/s6b12-20260930/campaign/round-{0..5}.json`
(campos `verdicts[*].A`, `development`, `proposal`), leídos sin modificar.

---

## 1. Hallazgo que el informe no recoge: techo de +1 frente a un umbral de +2

El informe atribuye el empate a problemas del bucle (P1 memoria, P2 retraso,
P3 diversidad). Son reales. Pero los datos muestran otra restricción que actúa
**antes** que cualquiera de ellos:

| Hecho medido | Fuente |
|---|---|
| V3 exige **≥ +2 niveles A** por propuesta, sin pérdidas individuales | `reason: 'under +2 A levels or individual A regression'` |
| La gramática exige **exactamente un parche** por propuesta | `contrastive_grammar.validate_answer`: `len(program['patches']) != 1` → error |
| Todas las propuestas rechazadas con ganancia positiva (ECHO 1, 2; FIJO 9, 21, 28) son `COOLDOWN_CAP` 8 o 10 | rondas 0, 1, 4, 5 |
| Las cinco dan **+1 nivel neto**. Todas ganan score en el caso 4; todas pierden score en el caso 68; las de guarda amplia pierden además en 51 y 76 | `A.loss_indices`, `development.contrasts` |
| La mejor (ECHO id 2, `COOLDOWN_CAP=10 si level≥2`) gana el nivel en el caso 18 (4→5) y pierde **solo score** en el caso 68 (9,20 → 8,42; nivel 3 pasa de 285 a 428 acciones) | `round-0.json`, ECHO id 2 |

Consecuencia: aunque el refinamiento de id 2 funcionara a la perfección y
eliminara la pérdida del caso 68, la propuesta seguiría en **+1** y V3 la
seguiría rechazando. Además, dos mejoras de +1 en partidas distintas nunca se
pueden sumar: cada una por separado no pasa V3 y no se admiten dos parches
en una misma propuesta.

**Esto es una hipótesis, no una demostración.** Solo hemos visto una familia de
operador (COOLDOWN_CAP) con ganancia positiva. Pueden existir parches de +2
que nadie propuso. Precisamente por eso la primera intervención debe medir el
espacio de búsqueda, no mejorar el proponente.

### Segundo hecho nuevo: REFINE nunca tocó su objetivo

- El objetivo de REFINE era un parche `COOLDOWN_CAP` (id 2).
- De las **25 propuestas REFINE, 25 fueron `REVALIDATE_NOOP`** y **0 fueron
  `COOLDOWN_CAP`**. En su mayoría eran variantes de la regla ya aceptada (id 0).
- Esto incluye la ronda 2 (ids 5–9), en la que el objetivo **sí** aparecía en
  el feedback, aunque sin contrastes. n = 5 con el mismo prompt: es poca
  evidencia, pero indica que restaurar la memoria (P1) quizá no baste. El
  modelo se ancla en el programa aceptado, que sí aparece en el prompt.

### Tercer hecho: la gramática no filtra valores inertes respecto al programa actual

`build_schema` descarta valores inertes para HOLD/COOLDOWN_CAP, pero para
`REVALIDATE_NOOP` acepta cualquier valor (`parameter == 'REVALIDATE_NOOP' or …`).
Lo compara con el valor por defecto, no con el valor efectivo del programa aceptado.
Resultado: 16/30 propuestas ECHO sin ningún cambio de acción en A. Cuántas eran
predeciblemente inertes antes de ejecutarlas **está por medir**.

---

## 2. Diagnóstico: hipótesis, alternativas y qué las refutaría

| # | Hipótesis | Confianza | La refuta |
|---|---|---|---|
| H1 | **Techo de granularidad:** desde el programa 378, ningún parche individual del lenguaje actual da +2 sin pérdidas | media | El censo (§3, E1) encuentra ≥ 1 parche individual que pasa V3 |
| H2 | **Anclaje del proponente:** el modelo refina lo que ve (el programa aceptado), no el objetivo del selector | media-alta (25/25) | Con el objetivo y sus contrastes en el prompt, las propuestas REFINE siguen sin usar el operador del objetivo |
| H3 | **Retraso del lote** (P2) reduce la adaptación | baja-media | El brazo con lotes de 1 no produce más comportamientos nuevos por llamada que el de lotes de 5 |
| H4 | **Selector monopolizado** (P1) | alta como hecho, **baja como causa del empate** si H1 es cierta | — |
| H5 | El modelo de 7B no sabe explorar HOLD/COOLDOWN | baja | Un muestreador de la gramática sin modelo iguala al LLM en aceptaciones con el mismo número de verificaciones |

Explicación alternativa que hay que tener presente: **A está cerca de saturarse**
(378/400; quedan 22 niveles). Puede que los niveles restantes no sean alcanzables
con estos tres controles. H1 y esta alternativa se comprueban con el mismo censo.

---

## 3. Intervención inicial elegida: censo de capacidad (sin LLM)

Antes de P1–P7 hay que responder una pregunta que decide cuáles de ellas
pueden funcionar: **¿existe, desde el programa aceptado 378, alguna propuesta
del lenguaje actual que pase V3?**

Es un **control de capacidad**. No es una mejora autónoma, no se enseña al
modelo, no toca B ni el examen y no modifica fuentes congeladas.

### E0 — Firmas de activación (minutos, sin partidas)

Para cada elección permitida por `choices(build_schema(rows_378, history))`,
calcular sobre las trayectorias A registradas del programa 378 en qué pasos
cambiaría el valor efectivo de un control. Agrupar por firma.

Salida: número de clases distintas; cuántas son inertes (firma vacía); cuántas
de las 60 propuestas reales caían en clases inertes. Límite: la firma solo
predice la **primera** divergencia. No prueba equivalencia; solo sirve para ordenar
y deduplicar. Punto técnico: `REVALIDATE_NOOP` depende de contadores internos
de contradicción. Hay que reconstruirlos a partir de la traza o, si no es posible,
excluir ese operador de E0 y declararlo.

### E1 — Censo medido en A (horas de CPU, 0 $)

- **Población:** una propuesta representativa por clase de E0, con muestreo
  uniforme y semilla fija si hay más de N clases. **N = 200**, prerregistrado.
  Estratificado por operador: REVALIDATE_NOOP / HOLD / COOLDOWN_CAP en
  proporción a sus clases, con un mínimo de 30 por operador.
- **Medición:** V1–V3 exactamente como en B12, solo sobre A. **V4 no se ejecuta**:
  el censo no debe ver B.
- **Coste:** sin estimar; se mide con los 5 primeros candidatos (`estimate`). Se lanza **después** del cierre auditado de B12-R1.
- **E1b, composición:** hasta 50 pares, medidos como `378 + p1 + p2`. Incluye
  pares complementarios en los que algún miembro tiene ganancia individual 0.
  Regla exacta en el [contrato](ECHO45-S6-PROBE1-DESIGN.md) §6.

### Regla de decisión (fijada antes de medir)

| Resultado de E1/E1b | Conclusión permitida | Siguiente paso |
|---|---|---|
| ≥ 1 parche individual pasa V3 | Existe al menos una solución individual desde 378. No dice que ECHO la habría encontrado | Intervención I1 (§4) + muestreador como brazo de control |
| ≥ 1 par pasa V3 | Justifica investigar composición. **No** demuestra que ningún parche individual pueda funcionar | Contrato nuevo de dos parches (aceptado por Roger si la evidencia lo justifica), sin bajar V3 y corrigiendo antes el límite de 32 reglas |
| 0 individuales y 0 pares | **No encontramos solución con este presupuesto.** No dice que el lenguaje esté agotado | Decidir con Roger: más presupuesto, otra estrategia de búsqueda o P7 |

*Corregido el 30-09-2026 según la revisión de Roger. Contrato:
[ECHO45-S6-PROBE1-DESIGN.md](ECHO45-S6-PROBE1-DESIGN.md). La estimación
anterior de «3–4 h» no estaba medida y se retira.*

Qué **no** permite concluir el censo: con 0 éxitos en 200 clases solo se acota
la tasa por clase (< 1,5 % con 95 %, regla del 3).

### Por qué el censo y no P1 primero

P1 cuesta poco y corrige un bug real. Pero si H1 es cierta, P1 + P2 no pueden
producir ninguna aceptación, y el piloto (≥ 36 propuestas, ~1 día de Kaggle)
volvería a empatar sin informar de nada. El censo cuesta 0 $, no gasta
llamadas al modelo y sirve para decidir entre las tres ramas anteriores.
Además, E1 **es** el muestreador de gramática de P6: fija la tasa base que el
LLM tiene que superar.

---

## 4. Si el lenguaje basta: intervención I1 (mínima)

Solo si E1 encuentra ≥ 1 parche individual que pasa V3.

**Infraestructura compartida por los cuatro brazos.** No puede explicar B2.

1. **Lotes de 1** (P2): petición → V1–V4 → actualizar → siguiente petición.
   Cada prompt declara el `sha` del programa sobre el que se verificará.
2. **Filtro de inertes respecto al programa actual** en `build_schema`
   (hecho 3 de §1).

**Tratamiento solo de ECHO.** Candidato a explicar B2.

3. **Registro de objetivo** (P1): `{id, proposal, base_program_sha, gain,
   loss_indices, contrasts}`. Tiene reserva de tokens propia y se incluye antes
   del historial secundario.
4. **Retirada del objetivo**: tras **K = 3** intentos sin aceptación o sin
   comportamiento nuevo, o si `base_program_sha` ≠ programa actual, el objetivo
   se retira y el planificador vuelve a CONTRADICTION/WAIT/GENERALIZE.
5. **Anclaje explícito** (H2): la petición REFINE fija el operador del objetivo.
   La gramática de esa petición solo admite ese `parameter`.

Pseudocódigo del selector (módulo nuevo, sin editar `contrastive_requests.py` congelado):

```python
def select_v13(rows, arm, history, index, target_log):
    if arm == 'fijo':
        return fixed_rule(rows)                               # sin cambios
    t = target_log.active(current_sha)                        # None si retirado/rebasado
    if t and t.attempts < K and not t.stalled():
        return t.cases, 'REFINE', {'operator': t.operator, 'target': t.record}
    return planner(rows, history, index), focus, None         # CONTRADICTION/WAIT/GENERALIZE
```

**Por qué debería favorecer a ECHO frente a FIJO:** FIJO elige siempre los tres
casos con menos niveles. Solo gana ECHO si el censo muestra que las mejoras
alcanzables están en partidas que la regla fija **no** selecciona. **Comprobación
previa en A:** cruzar las partidas que ganan en E1 con los casos que elegiría FIJO.
Si coinciden, I1 mejorará los dos brazos por igual y B2 seguirá en empate: hay
que decirlo antes de gastar el piloto.

**SIN FILTRO (B3):** incorpora todo lo seguro y ejecutable, incluidas las
propuestas con pérdidas (FIJO id 13: −5). B3 depende de que ECHO rechace esas
propuestas y de que las +1 que SIN FILTRO acumula no sumen más que lo que ECHO
acepta. No hay que perjudicarlo artificialmente.

### Ablaciones y presupuesto del piloto I1

| Brazo | Qué recibe | Propuestas |
|---|---|---|
| FIJO | infraestructura 1–2 | 3 semillas × 6 = 18 |
| ECHO-B12 | infraestructura 1–2 + selector B12 | 18 |
| ECHO-I1 | infraestructura 1–2 + tratamiento 3–5 | 18 |
| MUESTREADOR | gramática uniforme, sin modelo, mismas verificaciones | 18 (0 llamadas al modelo) |

54 llamadas al modelo + 2 calibraciones. Semillas nuevas, fijadas antes. Nueva B
protegida y reserva independiente declaradas **antes** de ver resultados.

**Continuar** si ECHO-I1 > ECHO-B12 y ECHO-I1 > FIJO en suma A, sin perder en
ninguna semilla, y ECHO-I1 ≥ MUESTREADOR. **Abandonar I1** si ECHO-I1 ≤
MUESTREADOR: el modelo no aporta nada sobre la gramática, y el neocórtex no
puede reclamar una ventaja no demostrada.

---

## 5. Condiciones bajo las que **no** se puede declarar verde

- Cualquier solución hallada por el censo (E1) y entregada al modelo, o usada
  para diseñar prompts, operadores o guardas específicas.
- Cambiar V3, la tolerancia de score o B4 después de ver resultados.
- Reutilizar la B de B11/B12 como si fuera nueva, o abrir la reserva más de una vez.
- Elegir semillas, políticas o métricas a posteriori.
- Atribuir a ECHO una mejora que también consiga el MUESTREADOR con el mismo presupuesto.
- Cambios de infraestructura aplicados a un solo brazo sin declararlos como tratamiento.
- Cualquier fallo de B1–B5 en el examen congelado.

## 6. Plan de auditoría

- Censo: guardar cada candidato, su firma, su medición A y el hash del programa
  base. Un revisor independiente vuelve a ejecutar una muestra de 20 y compara
  `trace_digest`.
- Piloto I1: igual que B12 (reconstrucción exacta de las peticiones, identidad
  modelo/revisión, replays). Además, comprobar que ninguna propuesta se verifica
  sobre un programa distinto del declarado en su prompt.

## 7. Referencias adicionales

**No verificadas en esta sesión** (citadas de memoria, sin búsqueda web).
Comprobar antes de usarlas en un documento público.

| Trabajo | Mecanismo aplicable | Límite |
|---|---|---|
| Olausson et al., *Is Self-Repair a Silver Bullet for Code Generation?*, ICLR 2024 (arXiv 2306.09896) | Con el mismo presupuesto de muestras, reparar aporta poco frente a volver a muestrear. Sustenta el brazo MUESTREADOR | Código general, no gramáticas acotadas |
| Yang et al., *Large Language Models as Optimizers (OPRO)*, 2023 (arXiv 2309.03409) | Mantener en el prompt las mejores soluciones con su puntuación. Sustenta el registro de objetivo (P1) | Presupuestos mucho mayores |
| Lehman et al., *Evolution through Large Models*, 2022 (arXiv 2206.08896) | LLM como operador de mutación en búsqueda por calidad-diversidad (P3) | — |
| Mouret & Clune, *Illuminating search spaces by mapping elites* (MAP-Elites), 2015 (arXiv 1504.04909) | Archivo por descriptor de comportamiento, que aquí sería la firma de E0 (P3) | Requiere muchas evaluaciones |
| Chen et al., *Teaching Large Language Models to Self-Debug*, 2023 (arXiv 2304.05128) | Feedback de ejecución en el prompt (P5) | Las explicaciones textuales no son causas verificadas |

## 8. Resumen en una línea

Antes de mejorar el proponente hay que medir si existe algo que proponer. Todas
las propuestas positivas vistas se quedan en +1, y V3 pide +2 por parche.
