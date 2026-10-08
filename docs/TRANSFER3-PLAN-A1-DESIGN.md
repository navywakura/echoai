# TRANSFER-3 Plan A1 — calibración de costes de movimiento: contrato

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Contrato fijado antes
de implementar y antes de mirar ningún examen. Autorizado por
[la propuesta](TRANSFER3-PROPUESTA-TRANSFERENCIA-UTIL.md); sigue la plantilla
de `ECHO-3-ACCEPTANCE.md` §9. No genera ni abre B/C. Software y simulación: un
verde funcional aquí no acredita hardware, HIL, vuelo real ni DRONE-3.

Autoría y escritor único: este contrato y los módulos con sufijo `a1` son de
Claude Opus 5. `codex` está activo en el mismo árbol y es autor de v4, v5,
`custody_v2`, el borrador de protocolo y la propuesta. No se modifica ningún
fichero ajeno; el espacio de nombres `a1` está libre.

## Corrección de un error propio, antes de nada

El registro [de implementación](TRANSFER3-CLAUDE-OPUS5-IMPLEMENTATION.md)
afirmó que la feature 504 era «el único obstáculo entre el mejor brazo y el
cribado». **Es falso.** Con 12 salas, aun con `new_failures = 0`, el brazo
seguía incumpliendo tres condiciones más:

| Condición del cribado | Valor con 12 salas | ¿Cumple? |
|---|---:|---|
| `new_failures == 0` | 2 | no |
| `joint_success_saved_moves > 0` | −12 | no |
| signo de una cola α ≤ 1/60 | 17/16 | no |
| coste escuela + examen < scratch | 1214 vs 1065 | no |

Eran cuatro incumplimientos, no uno. La afirmación se corrige aquí y el
registro histórico se conserva sin reescribir.

## Pregunta única

¿Una calibración de costes de movimiento aprendida en A, transferida sin mapa
ni geometría, permite completar misiones en salas nuevas con **menos energía
simulada** que el mismo agente con un prior nominal competente?

## Invariantes heredados

WSP 16 B y único bus cognitivo; estado cognitivo entero; córtex apagado; cero
LLM, Akida, kernel o segundo bus; la verdad del simulador fuera del estado
accesible al agente; `false_facts == 0`, `imagined_cam_writes == 0`,
`oracle_leaks == 0`, `gate_bypasses == 0`; parámetros congelados durante el
examen, percepción y seguimiento vivos.

## Entrada realmente disponible al agente

Las mismas tramas que hoy: `now_ns`, `odometry`, `energy`, `station_observed`,
`cells` con `depth`/`lidar`. La calibración se estima **exclusivamente** de la
variación de `energy` entre tramas consecutivas y de la acción que el propio
agente ejecutó. No se lee la tabla de costes del evaluador, ni seed, ni mapa,
ni solución. El agente nunca importa el simulador.

## Variable manipulada

La familia de costes del cuerpo, declarada y acotada:

```text
coste(acción a, acción anterior l) = base[a] + giro · [l is not None y l != a]
base[a] entero en [2, 6]   ·   giro entero en [0, 8]   ·   wait = 1
```

**Por qué un término de giro y no un término direccional.** Medido sobre las 64
salas públicas antes de implementar nada (ver más abajo): un coste direccional
por acción es **conservativo** y no distingue rutas. El coste total es
`fijo(Δx, Δy) + (base₀+base₁)·k_x + (base₂+base₃)·k_y`, donde `k` cuenta pares
de ida y vuelta desperdiciados; toda ruta de longitud mínima tiene `k = 0` y
por tanto **idéntico coste**. El giro no es conservativo: depende del orden de
las acciones, no de sus conteos. Es además físicamente interpretable para un
cuerpo aéreo: cambiar de dirección horizontal exige frenar y reacelerar.

## Prueba de identificabilidad y margen, ejecutada antes de implementar

Sonda externa sobre las 64 salas de examen de v4, sin agente ni campaña
(`lab/transfer3/plan-a1-margin.json`):

| Condición | Dispersión entre rutas de longitud mínima | Salas con elección real |
|---|---:|---:|
| uniforme, sin giro | 0 | 0/64 |
| direccional (3,5,4,4), sin giro | 0 | 0/64 |
| direccional fuerte (2,6,3,5), sin giro | 0 | 0/64 |
| uniforme + giro 4 | 1108 de 4324 (25,6 %) | 64/64 |
| uniforme + giro 8 | 2216 de 5944 (37,3 %) | 64/64 |

**Identificabilidad**: un paso recto revela `base[a]`; un paso que cambia de
dirección revela `base[a] + giro`. Ambos se separan con dos observaciones de
tipo distinto sobre la energía observada. Queda demostrado que se puede
aprender desde la interfaz.

**Margen, acotado con honestidad.** El agente nominal actual gasta 5260
unidades con giro 4; el óptimo con mapa completo gasta 3100. Esa diferencia del
41 % **no es reclamable**: 1208 unidades provienen de 302 pasos de más en 34
salas, causados por desconocer el mapa, y ninguna calibración de costes los
recupera. La parte atribuible a elegir ruta con conocimiento de giro, **a igual
longitud de camino**, es la dispersión: **25,6 % del coste de una ruta mínima**.
Ése es el techo declarado, y la cota oracle se publica sólo como techo, nunca
como competidor ni como filtro de salas.

## Brazos y control causal

Mismo ejecutable, mismos sensores, mismo planificador, mismos gates, misma
información pública inicial. Sólo cambian los parámetros de calibración:

| Brazo | Calibración |
|---|---|
| `nominal` | prior competente fijado antes de conocer la condición: `base = 4` en las cuatro acciones, `giro = 0` |
| `learned` | estimada en A a partir de energía observada |
| `permuted` | la misma calibración aprendida, con las bases permutadas y el giro conservado: control de que la ventaja viene del contenido y no de tener «algún» número |
| `crossed` | calibración aprendida bajo **otra** condición de la familia |
| `oracle` | valores verdaderos del evaluador, **cota externa no competitiva**, publicada aparte |

`nominal` no es un agente que no sepa moverse: recibe la misma cinemática
programada y el mismo prior de coste uniforme que es correcto en el mundo
histórico. Es un control competente, no un hombre de paja.

## Gate de reserva, idéntico en todos los brazos

La regla de reserva usa una constante **declarada y común** en todos los brazos.
Ningún brazo obtiene margen de seguridad por aprender. El éxito de misión y las
restricciones duras tienen prioridad sobre el coste.

### Enmienda 1 — la constante de reserva es 4

Fijada originalmente en el peor caso de la familia. Medido con el control y la
cota **antes de ejecutar ningún brazo aprendido**, ese valor es inviable: con
reserva 14 el agente evalúa `(12+12)·14+10 = 346 > 240` en el primer turno y
abandona antes de planificar, de modo que sólo 33 de 64 salas se completan. La
sonda sobre las 64 salas, usando únicamente `nominal` y la cota oracle:

| Reserva | Metas nominal | Metas cota | Fallos nuevos | Ahorro energía en éxito conjunto |
|---:|---:|---:|---:|---:|
| 4 | 59/64 | 62/64 | 0 | 152 (3,5 %) |
| 6 | 57/64 | 61/64 | 1 | 36 (0,9 %) |
| 8 | 54/64 | 59/64 | 3 | −96 (−3,0 %) |

Se adopta **reserva 4**, la misma constante de todo el trabajo histórico,
idéntica en todos los brazos. Consecuencia declarada: subestima el coste real
cuando se cobran giros, así que **las violaciones de reserva se adjudican
externamente con costes verdaderos** y se publican como KPI. Es un parámetro
del gate, no una métrica, y se fijó sin mirar ningún brazo aprendido.

### Horizonte

Se conservan `max_depth = 4` y presupuesto 32, los históricos. Medido: pasar a
profundidad 8 con presupuesto 128 **no cambia ningún resultado**, porque el
horizonte útil lo acota la visibilidad —el agente no puede expandir la búsqueda
a celdas que no ha observado—, no el parámetro. No se toca.

## Presupuesto de escuela, fijado por identificabilidad

**16 movimientos ejecutados.** La calibración necesita, como mínimo, una
observación recta y una de giro por cada una de las cuatro acciones: ocho
observaciones. Se declara el doble por margen. No se elige por su efecto sobre
la amortización, y la cobertura realmente alcanzada se publica. Si con 16
movimientos la cobertura es incompleta, eso es un resultado, no un motivo para
ampliarlo.

## Métricas, denominadores e intervalos

- Metas alcanzadas y **fallos nuevos** frente a `nominal`, por sala.
- **Coste primario: energía simulada total**, comparada entre éxitos conjuntos
  y también en todos los casos.
- Coste de escuela + **el mismo bloque de examen**, sin horizonte elegido
  después. Una proyección de equilibrio es secundaria y no convierte en verde
  un bloque que no ahorra.
- Error de calibración por parámetro, cobertura de observaciones, y efecto de
  retirar o permutar el aprendizaje.
- Movimientos, giros, tiempo, CPU y memoria, reportados aparte y también cuando
  empeoran.
- Prueba de signo de una cola sobre salas emparejadas, con N, multiplicidad y
  supuestos declarados antes de mirar el examen.

Recompensa, coste primario y criterio de éxito son cosas distintas.

## Criterios rojo y verde de esta rama

`plan_a1_development_pass` exige **todas**:

1. cero colisiones, violaciones de reserva, hechos falsos, escrituras
   imaginadas y modelos alterados durante el examen;
2. `new_failures == 0` frente a `nominal`;
3. energía entre éxitos conjuntos estrictamente menor que `nominal`;
4. energía de escuela + examen menor que la de `nominal` en el mismo bloque;
5. `learned` mejor que `permuted` y que `crossed` en energía de éxitos
   conjuntos, es decir, la ventaja viene del contenido de la calibración;
6. signo de una cola α ≤ 1/60 sobre salas emparejadas.

Rojo si falla cualquiera. **Aprobar esto es un efecto público observado**: no
es candidato confirmado ni cierre de custodia, y no autoriza `transfer3_green`.

## Seeds

Desarrollo: salas públicas ya usadas de v4 (`20264601`+). Validación
prospectiva y confirmación: geometrías nuevas de un generador versionado con
capacidad suficiente, disjunción comprobada, fijadas **después** de congelar el
candidato y **antes** de mirarlas. Quedan 34 formas de la familia histórica;
por eso la confirmación exige el generador ampliado, no esas 34.

## Mutantes que el auditor debe rechazar

Calibración injertada desde la verdad privada; lectura de seed, mapa o solución
durante aprendizaje o ejecución; aprendizaje durante el examen; payload o
dependencia alterados; caso omitido del informe; costes mal sumados; éxito
falso; reserva con semántica distinta entre brazos.

## Regla de parada de la rama

Si `learned` no supera a `nominal` en energía de éxitos conjuntos, o no supera
a `permuted`/`crossed`, la calibración de costes no transfiere en este dominio
y se pasa a Plan B —calibración del modelo de ejecución— sin encadenar una
tercera revisión del mismo mecanismo. Máximo dos revisiones de A con evidencia
nueva que cambie el diagnóstico.
