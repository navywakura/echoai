# E4-OTHER-1 — resultados y límites

2026-09-22. **E4-OTHER-1 verde y cerrada en su perfil observacional discreto.**
Dos cohortes nuevas superan los umbrales preregistrados; reconstrucción íntegra
en proceso nuevo válida, sin hallazgos, `other1_green=true` en el recibo.
99 fuentes fijadas, incluidas las 93 de MAINTAIN, sin modificar antecedentes.

Digest de reproducción:
`1263f11ab291a1ff350313a93a70d9f4b3b9259099482bb8425e9f414c2aa024`.
Artefactos: [campaña](../lab/echo4/other1-v1/report.json) y
[recibo de auditoría](../lab/echo4/other1-v1/audit-receipt.json).

## Qué se ha implementado

`other_model.py` aprende regularidades observables de una contraparte en la
CAM/T originales del propio agente. `other_world.py` permite el encuentro de
dos `Agent` nativos con mundos, memorias y Q independientes; cada Q aprende
desde cero durante 240 pasos privados. No se asigna directamente la acción
correcta ni se sustituye el gate. El modelo del otro recibe exclusivamente
paquetes públicos de contexto y ejecución, no sus preferencias, recompensas,
Q, memoria o secuencia futura del mundo.

`other_replay.py` reconstruye el observador desde esos paquetes; no ejecuta
la contraparte ni el entorno. `other_bench.py` fija fuentes antes del examen,
compara cuatro brazos emparejados y reconstruye después los resultados.
No nuevo bus ni tabla predictiva paralela: WSP16, CAM/T/Q/gate originales,
camino rápido entero y sin LLM. Las predicciones no se convierten en hechos.

En este dominio, representar al otro significa aprender **qué acción suele
ejecutar en un contexto visible**, separándola de la conducta propia. El
identificador local y la codificación del sensor son proporcionados por el
experimento; no se ha descubierto visualmente una identidad ni inferido un
estado mental privado.

## Examen y coste real

Cada cohorte tiene ocho escenarios de pareja heterogénea y ocho de preferencia
igual; cada escenario se ejecuta con cuatro brazos. Son **32 escenarios,
128 ejecuciones de pareja y 256 vidas individuales** entre las dos cohortes,
no 128 parejas independientes. Se aprende durante el encuentro; se puntúan
las predicciones comprometidas de los últimos 96 de sus 192 pasos públicos.

| Brazo | Heterogénea D1 | Heterogénea D2 | Iguales D1 | Iguales D2 |
|---|---:|---:|---:|---:|
| Identidad separada | 1536/1536 | 1536/1536 | 1536/1536 | 1536/1536 |
| Identidad mezclada | 1008/1536 | 1008/1536 | 1536/1536 | 1536/1536 |
| Copiar conducta propia | 0/1536 | 0/1536 | 1536/1536 | 1536/1536 |
| Sin historia pública | 0/1536 | 0/1536 | 0/1536 | 0/1536 |

Numerador = aciertos; denominador incluye abstenciones. En heterogéneas,
`pooled` se abstiene 528 veces por cohorte y no falla las predicciones que
emite en esa mitad; `self_copy` emite 1536 predicciones incorrectas y
`no_history` se abstiene siempre. Separar sujetos aporta **34,375 puntos**
frente a mezclarlos, y 100 frente a los otros dos controles en cada cohorte.
Supera 85% de aciertos, 95% de precisión y márgenes +20/+20/+50 exigidos.
Cuando las preferencias coinciden no hay ventaja: se conserva ese empate.

No acierta todo desde el nacimiento. En la **primera mitad**, identity logra
1104/1536 por cohorte, con 432 abstenciones y cero errores. Agregando ambas
cohortes heterogéneas: pooled acierta 1462/3072, se equivoca 34 veces y se
abstiene 1576; self_copy falla sus 2791 predicciones y se abstiene 281 veces.
En iguales, self_copy acierta 2791/3072 en esa primera mitad, mejor que
identity (2208/3072): requiere menos historia. No se oculta este coste.

D ejecuta **61.440 acciones privadas de preparación + 49.152 acciones
nativas durante encuentros = 110.592 acciones** en los cuatro brazos.
Las 49.152 acciones del encuentro resuelven su tarea privada correctamente;
sus trazas son idénticas entre brazos. La preparación está fuera del KPI de
predicción pública, no fuera del coste. Desarrollo añade 24 ejecuciones de
pareja, 11.520 acciones privadas y 9.216 de encuentro; C se registra aparte.
La reconstrucción vuelve a ejecutar estos bancos; no es evidencia nueva.

Identity usa hasta 15 filas CAM por agente, 12 públicas; pooled hasta 24,
21 públicas. No hay borrado ni desbordamiento en D. Es coste en este banco,
no una garantía de memoria, energía o latencia para un producto integrado.

## Integridad y pruebas

40 pruebas nuevas pasan. Cubren forma WSP completa, tipos estrictos,
predicción anterior al resultado, ausencia de hechos inventados, CAM llena,
identidad desconocida, visibilidad/ejecución ausentes, contradicción, recibos
inválidos, duplicados, presupuesto, parada, gate y separación de memoria.
Comprueban que Q parte de cero, aprende y elige las acciones reales; ningún
brazo recibe una política de acciones escrita a medida.

Regresión de esta entrega: **620 pruebas distintas** (40 OTHER, 85 MAINTAIN
y 495 de núcleo/Q), **619 aprobadas y un fallo esperado histórico**. Los ocho
errores iniciales eran denegaciones de sockets del sandbox en pruebas GUI;
las 29 pruebas de sus tres clases pasan al repetirlas con permiso de localhost.
No se modificó código para esa repetición ni se cuentan como pruebas nuevas.
No se afirma haber vuelto a ejecutar toda la suite histórica ECHO-4 en este corte.

```bash
PYTHONPATH=.. python3 -m unittest tests.test_echo4_other1 tests.test_echo4_maintain1 tests.test_echo4_maintain1a tests.test_nexus0 tests.test_qtable -q
```

C conserva 12 comprobaciones positivas y dos reconstrucciones en procesos
nuevos: 25 registros por observador, incluyendo un veto nativo. Igualan las
predicciones originales y el hash público CAM/T. Cambiar una predicción
original hace fallar la comparación. El replay local coincide también en
ambos observadores de las 152 ejecuciones de pareja de desarrollo y D.
La auditoría posterior reproduce toda la campaña byte a byte y verifica las
99 fuentes y la custodia parental. No demuestra aislamiento frente a código
host malicioso ni autentica personas fuera del sensor simulado.

## Controles y límites de interpretación

- `identity`: historia separada por sujeto.
- `pooled`: historia sin distinguir quién actuó; las claves derivadas no son hechos.
- `self_copy`: extrapola al otro la conducta propia observada en ese contexto.
- `no_history`: no aprende las transiciones públicas, sin borrar memoria nativa.

Todos usan las mismas experiencias privadas. La observación todavía no dirige
acciones: deben coincidir acciones, vetos y recompensas entre los cuatro brazos.
Las parejas de igual preferencia controlan que copiarse a sí mismo sí funcione
cuando la conducta coincide. La ventaja no se presupone universal.

Ausencia de contexto/identidad implica desconocido; ausencia de ejecución no
se transforma en WAIT. Una identidad nueva necesita evidencia nueva. Una fila
contradicha deja de emitir predicciones, **sin borrar sus observaciones**: este
perfil no demuestra reaprendizaje posterior de una conducta cambiante.

La tarea discreta tiene tres contextos y tres acciones; no es el cuerpo térmico
de MAINTAIN ni acredita supervivencia conjunta. Las preferencias pertenecen a
un conjunto finito conocido por el banco, no por el predictor. Los exámenes
cambian parejas, experiencias y secuencias, no las leyes del mundo. El replay
reconstruye solo el subgrafo observacional, no la continuidad del agente completo.

El resultado no acredita conciencia subjetiva, empatía, control del otro,
teoría de la mente general ni cooperación útil. **INTERACTION-1** deberá medir
cuándo usar esa representación mejora resultados, con costes y controles.
INTEGRATE deberá unir los perfiles y contrastar sus contribuciones conjuntas.
Hardware después; METAVERSE-1 último. Discord no pertenece a este programa.

## Reproducción

Desde `echoai/`, sin activar Qwen:

```bash
PYTHONPATH=.. python3 -m unittest tests.test_echo4_other1 -q
PYTHONPATH=.. python3 -m echoai.echo4.other_bench verify lab/echo4/other1-v1
```

Una campaña reproducida usa `campaign` y un directorio inexistente. No
sobrescribir artefactos; repetir las mismas semillas no crea otro holdout.
El informe conserva `other1_green=false`: solo el recibo de reconstrucción
puede conceder el cierre. La auditoría reconstruye OTHER completo y coteja la
custodia de MAINTAIN; **no vuelve a ejecutar su física ni Qwen**.

[Contrato y umbrales](ECHO4-OTHER1-DESIGN.md) · [Roadmap](ROADMAP.md).
