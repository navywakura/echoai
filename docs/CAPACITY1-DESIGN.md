# CAPACITY-1 — capacidad neuronal medible antes de ECHO-3

Fecha de preregistro: 2026-09-09. **Documento de diseño; no es una
implementación ni un resultado.** Luna implementará el banco, automatizará
las repeticiones y resumirá los barridos. Las condiciones de examen y el
criterio verde quedan fijados aquí antes de ejecutar sus semillas.

## 1. Pregunta y límite de la afirmación

CAPACITY-1 debe responder dos preguntas separadas:

1. ¿una representación con 512 LIF conserva o separa mejor señales
   sensoriales que el spoke actual de 256 LIF, con un coste medido?;
2. si existe un cuello de botella temporal demostrado, ¿un head de 128
   Adaptive-LIF mejora la discriminación temporal frente a un head del mismo
   tamaño con adaptación desactivada?

El número de neuronas no es una medida de inteligencia. Un cierre verde sólo
afirma una mejora causal de representación o temporalidad en los exámenes de
este documento. No afirma visión real, navegación 3-D, capacidad del AKD1500,
AGI ni equivalencia con neuronas biológicas.

La temperatura de HEAT-1b sigue siendo una variable sintética 0..127; no es
entrada de este banco y no se leerán sensores del PC.

## 2. Hecho arquitectónico que el banco debe respetar

`navi10_qn.Layer256` implementa un Q8 de 256 LIF enteras. En el agente actual,
`encode_event()` produce vértice, latencia y ticks, pero la política no usa el
argmax del spoke: decide con `Q[slot, action]`. Duplicar el objeto y contar sus
spikes no puede, por sí solo, mejorar ninguna acción.

CAPACITY-1 integrará el resultado neuronal únicamente como rasgo sensorial
entero que consume la memoria PATTERN-1. El trayecto será:

```
WSP de 16 bytes -> vértice/estímulo -> banco neuronal -> firma u16
                                             |
                                             v
                              PATTERN-1 -> consecuencia aprendida
```

La WSP original continúa intacta y es la única observación compartida. La
firma `u16` ocupa el mismo papel que la firma perceptiva de PATTERN-1; no es un
segundo thought-bus. Ningún spike escribe hechos, elige IRQ, toca disco ni
salta el gate. Q/T/CAM/VERIFY/gate permanecen iguales y en CPU.

## 3. Implementación permitida

Luna podrá crear:

- `nexus0/capacity1.py`: configuraciones, dataset, runner y auditor;
- `tests/test_capacity1.py`: contrato, mutantes y recomputación;
- `lab/echo2_capacity1_report.json`: certificado generado por el runner.

No copiará `Layer256` ni `navi_q6_step`. Para 256 y 512 LIF compondrá
instancias importadas de `navi10_qn.Layer256`. El adaptador debe ser fino y no
modificar `navi10_qn.py`, Q6 ni el unikernel.

El head temporal será una única implementación parametrizada de 128 celdas.
El control y el candidato ejecutarán el mismo código, proyección, recurrencia,
pesos, ticks y readout; sólo cambiará `adapt_gain=0` frente al valor Adaptive-
LIF preregistrado. Así no habrá dos implementaciones que diverjan en secreto.
Todo el paso neuronal será entero, con buffers de tamaño fijo y sin crecimiento
durante un episodio.

Antes de escribir el head, Luna documentará en el módulo sus ecuaciones,
límites, saturación, reset, conectividad y tamaño de estado. Esos valores se
fijarán usando sólo la partición de desarrollo. No se reajustarán después de
abrir el examen.

## 4. Configuraciones obligatorias

| id | red | función en la comparación |
|---|---:|---|
| `lif256` | 256 LIF | baseline importado y presupuesto mínimo |
| `lif512` | 2 × 256 LIF | ampliación inicial del roadmap |
| `lif512_lif128` | 512 LIF + head 128, adaptación 0 | control de 640 neuronas y misma recurrencia |
| `lif512_alif128` | 512 LIF + 128 Adaptive-LIF | candidato temporal |
| `feature_blind` | firma constante, sin aprendizaje neuronal | suelo y prueba de fuga de etiquetas |
| `feature_permuted` | firmas barajadas entre muestras de examen | ablación causal de la interfaz PATTERN-1 |

`lif256` y `lif512` recibirán los mismos 16 bytes y el mismo presupuesto de
16 ticks por muestra. La proyección queda cerrada aquí para evitar escogerla
después de ver el examen:

```
vertex = simhash16(wsp)
hi = vertex >> 8
lo = vertex & 255
lif256: stim = hi XOR lo; firma = winner || winner
lif512: stim0 = hi; stim1 = lo; firma = winner0 || winner1
target de auditoría = q8_nearest(stim)
```

Cada `winner` es el byte codeword devuelto por el `Layer256` importado y `||`
concatena dos bytes en un `u16`. Así 256 dispone de hasta 16 símbolos y 512 de
hasta 256, sin agrandar WSP ni esconder un clasificador. En Python los dos Q8
se ejecutan secuencialmente y se reportan como tal. No se permitirá dar al
candidato etiquetas, posiciones, ids de objeto, semillas o consecuencias que
no reciba el baseline.

El head de 128 celdas sólo se ejecutará en el examen final si el diagnóstico
temporal de la sección 7 demuestra el cuello de botella previsto. Si no lo
demuestra, se registrará `adaptive_status="not_justified"`; no se fabricará una
tarea nueva después de ver resultados.

## 5. Tres bancos, una causa por banco

### A. Integridad Q8 y coste

Comprueba que la composición mantiene el comportamiento importado. Incluye
los 256 estímulos Q8, todos los codewords, distancia Hamming 0/1/2 y secuencias
vacías. Verifica ganador, primer spike, total de spikes, determinismo tras
reset y saturación.

Este banco no puntúa inteligencia ni exige que 512 sea más preciso. Su misión
es detectar una ampliación rota y medir coste.

### B. Capacidad perceptiva congelada

Generará 32 familias WSP de 16 bytes, por debajo de la capacidad 64 de
PATTERN-1 para que esa tabla no sea el cuello de botella. Cada semilla elige 16
familias repartidas entre celdas del codebook Q8 de entrada: es estratificación
del estímulo, fijada antes de entrenar, no selección por la predicción de un
candidato. Los nombres de familia y consecuencias sólo existen en el harness.

Cada familia recibe cuatro exposiciones controladas de una WSP base para llegar
al umbral fijo de PATTERN-1. El examen usa una WSP distinta de 16 bytes que
conserva el mismo vértice `simhash16`; por tanto comprueba la interfaz WSP→QN
sin convertir cambios arbitrarios de hash en una etiqueta visual falsa.

La red recibe exclusivamente una WSP de 16 bytes y devuelve una firma `u16`.
Durante entrenamiento, una instancia nueva de `InvariantPatternMemory`
recibe `(firma, consecuencia)`. Durante examen, tanto la red como PATTERN-1
quedan congeladas y sólo reciben la WSP/firma; la consecuencia se usa después
para puntuar. Train y exam usan familias de ejemplares, máscaras y semillas
disjuntas.

Se publican aciertos, errores, abstenciones, balanced accuracy por familia,
colisiones entre consecuencias incompatibles y distancia intra/interfamilia.
El KPI principal es balanced accuracy contando una abstención como fallo.

### C. Temporalidad y anomalías

Usará secuencias que comparten exactamente el mismo evento actual y el mismo
histograma de eventos, pero difieren en orden y separación temporal. Habrá
motivos normales, motivos con transposición, evento omitido y evento insertado.
La etiqueta es `normal` o `anomalía`; nunca entra en la red durante examen.

Dos controles justifican el experimento:

- `current_only`: clasifica desde el último evento y debe quedar cerca del
  nivel ambiguo;
- `history_oracle`: recibe el motivo completo en el harness y demuestra que
  el dataset sí contiene señal temporal resoluble.

Existe cuello de botella si el oracle supera a `lif512` en al menos 20 puntos
porcentuales de balanced accuracy y `lif512` no supera 60 %. Sólo entonces se
comparan `lif512_alif128` y `lif512_lif128` en el examen reservado.

## 6. Particiones y semillas cerradas

Habrá dos ejecuciones distintas:

- **desarrollo:** 24 semillas, disponible para fijar proyección, constantes
  del head y duración;
- **examen:** 128 semillas nuevas, bloqueadas hasta que el código, tests y
  `config_sha256` estén cerrados.

Cada semilla se deriva de los primeros ocho bytes big-endian de:

```
SHA256("ECHO-AI/CAPACITY-1/2026-09-09/<bank>/<split>/<index>")
```

El informe guardará material ASCII, valor derivado y SHA-256 de las listas de
semillas. Cada configuración de un par comparte ejemplos, orden, ruido y
duración. Cambia únicamente la configuración neuronal. El runner rechazará
semillas duplicadas entre desarrollo y examen.

Luna puede paralelizar por `(bank, seed, config)`, pero debe ordenar el JSON
final por banco, semilla y configuración. La tabla funcional exhaustiva de los
256 estímulos se calcula con `Layer256` importado y se reutiliza sólo para las
repeticiones de la evaluación funcional, porque el spoke se resetea por cada
muestra. La medición de latencia ejecuta capas frescas, sin tabla. Dos
ejecuciones completas deben producir el mismo bloque científico byte por byte;
tiempos de pared irán en un bloque separado no incluido en ese hash.

## 7. Barrido que Luna ejecutará

Primero ejecutará un piloto de una semilla para detectar excepciones; sus
números no entran en ninguna comparación. Después:

1. corre A para `lif256` y `lif512`;
2. corre desarrollo B para 256/512 con los 16 ticks fijados;
3. congela dataset, proyección y constantes en `config_sha256`;
4. corre desarrollo C y evalúa el diagnóstico de cuello de botella;
5. si se justifica, elige `adapt_gain` de `{4, 8, 16}` y memoria adaptativa de
   `{8, 16, 32}` ticks con una regla lexicográfica: balanced accuracy, menos
   estado, menos actualizaciones;
6. congela el candidato y abre una sola vez las 128 semillas de examen;
7. ejecuta todos los controles aplicables y genera informe, tabla Markdown y
   auditoría.

No se seleccionará por latencia ni por el examen. Un fracaso produce informe
rojo; no autoriza añadir candidatos o cambiar umbrales en la misma revisión.

## 8. Estadística y criterio verde

Las métricas se calculan por semilla y de forma agregada. Para cada comparación
principal se publican victorias, derrotas y empates por semilla, diferencia de
balanced accuracy y prueba unilateral exacta de signos, excluyendo empates.
No se usarán floats para decidir: porcentajes y `p` se comparan como fracciones
enteras; el decimal sólo es presentación.

CAPACITY-1 queda verde si se cumplen todos estos puntos:

1. integridad A completa, resultados deterministas y cero divergencias del
   `Layer256` importado;
2. en B, `lif512` supera a `lif256` por al menos 5 puntos porcentuales
   agregados, tiene más victorias que derrotas y `p <= 0,01`;
3. en B, las colisiones de consecuencias incompatibles bajan al menos 25 % y
   `feature_permuted`, con un barajado determinista independiente por semilla,
   pierde al menos 80 % de la ganancia 512−256;
4. si C justifica Adaptive-LIF, `lif512_alif128` supera al control emparejado
   `lif512_lif128` por al menos 5 puntos, con más victorias que derrotas,
   `p <= 0,01`, y la permutación elimina al menos 80 % de la ganancia;
5. si C no lo justifica, el informe no ejecuta ni atribuye ventaja al head y
   el verde depende de la mejora causal 256→512 de B;
6. WSP mide siempre 16 bytes; `false_facts=0`, `destroyed=0`,
   `cortex_calls=0`; Q/T/CAM/VERIFY/gate no cambian;
7. examen congelado: hashes de red, PATTERN-1 y estado iguales antes/después;
8. pasan `test_capacity1`, los tests de PATTERN-1 y la regresión NEXUS-0 que
   el repositorio ya exige.

Si 512 sólo reduce latencia o produce más spikes, CAPACITY-1 queda rojo como
mejora cognitiva aunque esos datos se publiquen. Si ALIF gana a 512 pero no al
control de 640 neuronas, se atribuye la mejora al tamaño/head, no a adaptación.

## 9. Medidas de recursos

Por configuración se registran:

- neuronas LIF y Adaptive-LIF por separado;
- potenciales, umbrales adaptativos, pesos y bytes de estado declarados según
  su representación prevista en C;
- actualizaciones neuronales, spikes totales, spikes por muestra y ticks;
- tiempo `perf_counter_ns` sin caché: calentamiento 10 repeticiones y 30
  repeticiones medidas para 256 y 512 LIF, publicando mediana y p95 junto al
  host y versión de Python;
- pico Python mediante `tracemalloc`, etiquetado como coste del prototipo y no
  como RAM bare-metal;
- tamaño del informe y hashes de configuración/código.

La latencia de dos `Layer256` ejecutados secuencialmente en Python es latencia
CPU del prototipo; no se describirá como paralelismo neuromórfico. No se
publicarán julios ni potencia: no hay shunt, RAPL atribuible al componente ni
placa Akida en este experimento.

## 10. Informe auditable

`lab/echo2_capacity1_report.json` contendrá al menos:

```
schema, slice, date, green
code_sha256, config_sha256, scientific_result_sha256
seed_derivation, development_seed_hash, exam_seed_hash
configs, selected_config, adaptive_status
integrity, perception, temporal, ablations
paired_counts, exact_sign_fraction, effect_fractions
neurons_by_type, state_bytes, updates, spikes, latency_host
frozen_hashes_before_after
wsp_bytes, false_facts, destroyed, cortex_calls
tests, limitations
```

`green(report)` no confiará en el booleano guardado. Recomputará seeds,
agregados, fracciones, comparaciones pareadas, hashes y cierre desde filas
crudas. Los tests incluirán mutantes que cambien una semilla, etiqueta,
predicción, tiempo, recuento neuronal, hash, control, resultado congelado y el
propio campo `green`; todos deben ser rechazados.

## 11. Entrega esperada de Luna

Luna entregará el módulo, tests, JSON y una tabla corta:

| config | neuronas | BA percepción | BA temporal | colisiones | spikes | ns p50/p95 | estado bytes |
|---|---:|---:|---:|---:|---:|---:|---:|

Su resumen distinguirá `medido`, `inferido` y `no medido`. Un rojo válido es
un resultado científico aceptable y conservará la evidencia. Sólo un verde
según la sección 8 permite cerrar CAPACITY-1 antes de NEURAL-VIZ-1.

## 12. Trabajo aplazado hasta disponer del AKD1500 M.2

Este banco no simula el AKD1500. Cuando exista la tarjeta, su runtime y un
modelo compilado, se repetirá el dataset congelado comparando CPU y hardware
en el mismo host. Se medirán capacidad compilada real, precisión, latencia,
memoria, consumo con instrumentación válida y fallback al desconectar el
acelerador. No se convertirán GOPS en un número supuesto de neuronas.
