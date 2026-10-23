# S6-B · resultados y cierre · 2026-09-27

Estado final: **B0 cerrado ROJO**, B1 detenido en calibración;
**B2 cerrado y auditado ROJO**. No quedan pruebas de esta campaña corriendo.
S5-E de v5.7 está [cerrado VERDE](ECHO45-S5-E-RESULTS.md).
El [rojo de S6-A](ECHO45-S6-RESULTS.md) permanece sin cambios.

## B0: resultado del examen y auditoría

Base v5.7; 30 propuestas por brazo, seis rondas. Las 60 respuestas fueron V1:
se cortaron cerca del límite de 400 tokens y también contienen nombres
incorrectos, operadores sin comillas y condiciones no permitidas. Cero
estrategias aceptadas; SIN FILTRO tampoco puede incorporar JSON inválido.
Las cuatro estrategias finales son idénticas a la base.

Examen nuevo: 120 juegos (versiones 2 y 3, semillas 8000–8059), cinco niveles,
tres reps, 2000 decisiones por partida y reinicios automáticos registrados.

| Brazo | Niveles /1800 | Puntuación media /100 |
|---|---:|---:|
| SEMILLA | 1378 | 12,6593 |
| FIJO | 1378 | 12,6593 |
| ECHO | 1378 | 12,6593 |
| SIN FILTRO | 1378 | 12,6593 |

B1 (mejorar un 5 %), B2 (superar FIJO) y B3 (superar SIN FILTRO) fallan.
B4 (desarrollo sin regresión) y B5 (integridad/reconstrucción/replay) pasan.
Las estrategias idénticas comparten la primera medición; el replay de rep 0
se hizo en un proceso y cache independientes y fue exacto.
El solucionador resuelve los 600 niveles de ambas versiones y la generación
es determinista. Los prompts se reconstruyeron desde datos de A solamente.

**B0 ROJO por protocolo de salida.** No es evidencia de que una estrategia
válida del modelo no pueda mejorar a ECHO: ninguna llegó a la prueba de utilidad.

Datos: `lab/seed/s6b0-final-20260927/`, especialmente `exam/audit.json`.
Fuentes y wrapper congelados en `lab/kaggle/s6b0-20260927/preflight.json`.
Archivo privado: `57b331c5cb3296c926599b5b066ec34e77f5546cb0fd885dc9fa10eec202ee33`.

## B1: calibración fallida, sin brazos

Se redujo la petición y se dieron ejemplos válidos, con máximo 600 tokens.
Las dos llamadas genéricas de calibración devolvieron:

- una estrategia válida: MIN_EVIDENCE=4 y HOLD=60 cuando reconoce un reinicio;
- otra con la condición inexistente `max_units`, rechazada por el validador.

El arranque se detuvo por la condición fijada de que ambas debían ser válidas.
**Cero llamadas de brazos y examen sin abrir.** No se llama verde ni se reparan
respuestas a posteriori. No fue un problema de conexión o de GPU.
Recibo y respuestas en
`lab/kaggle/s6b1-20260927/error-output/s6b1/format-calibration.json`.
Se guardó el modelo real: revisión `c03e6d358207e414f1eca0bb1891e29f1db0e242`,
Torch 2.10.0+cu128 y Transformers 5.0.0, distribuido en las dos GPU.

## B2: cierre ROJO después del examen y la auditoría

[Contrato previo](ECHO45-S6-B2-DESIGN.md). Se preservan los requisitos de mejora
y la base. La gramática evita errores de sintaxis; el modelo elige los valores
de cuatro parámetros y una regla observable. Es control de mecanismos
existentes, no creación de algoritmos nuevos.

Calibración 2/2 válida; el control repetido en Kaggle es idéntico al local.
Los brazos terminaron sus 30 propuestas cada uno. Ninguna falla V1 o V2.

| Brazo | Aceptadas | Rechazadas V3 | Niveles A inicial → final | Niveles B inicial → final |
|---|---:|---:|---:|---:|
| FIJO | 2 | 28 | 56 → 62 | 28 → 30 |
| ECHO | 1 | 29 | 56 → 62 | 28 → 30 |

FIJO acepta las propuestas 10 y 22 (índices de diario 9 y 21), con ganancias
A de +3 y +3. ECHO acepta la 22, de tipo P2 (agrupar fallos), con +6.
La puntuación de B pasa de 201,4311 a 231,0282 en ambos brazos; FIJO tuvo
un paso intermedio de 209,7233. Son medidas de **entrenamiento y control**,
no resultados del examen.

V4 protege **totales de B**, no cada juego. Frente a SEMILLA, la estrategia
final pierde un nivel en un juego de B y gana tres en otro; también baja la
puntuación en tres juegos. En A gana seis niveles netos, pero empeora niveles
en tres juegos y baja la puntuación total de 320,0371 a 300,2594. V3 exigía
niveles, no puntuación de A; el examen B1 sí exige que su puntuación no baje.
Las diferencias individuales constan en `accepted-counterfactuals.json`.
Por tanto, «sin regresión en B» se refiere al total fijado en el contrato,
no a una garantía de conservar todas las partidas.

FIJO usó la petición genérica 30 veces. ECHO: P1 9, P2 11, P3 2, P4 8.
P3 solo se habilitó después de su primera aceptación. Hubo 26 propuestas
distintas en FIJO y 22 en ECHO. Aceptaciones primera/segunda mitad: FIJO 1/1,
ECHO 0/1; ese cambio no demuestra aprendizaje general del selector.

La estrategia final **es exactamente la misma en ECHO y FIJO**:

```json
{"defaults":{"BABBLE":4,"HOLD":60,"MIN_EVIDENCE":6,"WALL_MIN":5},"rules":[{"set":{"HOLD":80},"when":{"reset_known":["eq",1]}}]}
```

Ajusta la exploración, la evidencia necesaria para reconocer cuerpo/paredes
y el intervalo antes de volver a pulsar una tecla de reinicio o modo.
La regla aumenta ese intervalo cuando ya hay una tecla de reinicio conocida.
No agrega un mecanismo de orden o de conteo.

SIN FILTRO conserva la última propuesta válida del brazo ECHO, tal como
fijaba el contrato; no se elige retrospectivamente la que mejor rindió:

```json
{"defaults":{"BABBLE":2,"HOLD":40,"MIN_EVIDENCE":8,"WALL_MIN":3},"rules":[{"set":{"HOLD":60},"when":{"reset_known":["eq",1]}}]}
```

Por esa igualdad de estrategias, **el requisito B2 de superar FIJO falla**.
Se completaron igualmente las otras comparaciones, desarrollo y auditoría.
Las estrategias se congelaron antes del examen 10000–10059 y no se cambiaron
a partir de sus resultados.

Modelo real `Qwen/Qwen2.5-Coder-7B-Instruct`, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, Torch 2.10.0+cu128,
Transformers 5.0.0, distribuido entre ambas T4.
Uso aproximado por retokenización: FIJO 21 885 tokens de prompt y 1441 de
respuesta; ECHO 22 244 y 1442. Calibración adicional: 746 y 97.
62 muestras propuestas, generadas en lotes; **USD 0 de API**, GPU gratuita.
No son cifras de una factura de API.

### Examen reservado B2

120 juegos nuevos (versiones 2 y 3, semillas 10000–10059), cinco niveles,
tres reps, 2000 decisiones por partida: 360 partidas y 1800 niveles posibles
por brazo sumando las reps.

El límite cuenta decisiones del agente. Los reinicios automáticos tras
GAME_OVER también se guardan en acciones y frames, pero no consumen el
presupuesto ni incrementan `actions_per_level`. La puntuación usa la fórmula
oficial sobre ese contador del runner congelado; no es un scorecard de
competición. Los cuatro brazos usan la misma convención.

| Brazo | Niveles por rep | Total /1800 | Puntuación media /100 |
|---|---|---:|---:|
| SEMILLA | 459 · 463 · 465 | **1387** | **12,3810** |
| FIJO | 458 · 437 · 455 | 1350 | 10,8449 |
| ECHO | 458 · 437 · 455 | 1350 | 10,8449 |
| SIN FILTRO | 459 · 463 · 465 | **1387** | **12,3810** |

ECHO pierde **37 niveles (−2,67 %)** y un **12,41 % de puntuación** frente a
SEMILLA. B1 falla: no transfiere la ganancia del entrenamiento. B2 falla:
empata con FIJO. B3 falla: queda por debajo de SIN FILTRO.
El presupuesto mayor del examen estaba fijado antes de generar propuestas.

Las estrategias SEMILLA y SIN FILTRO tienen JSON distinto, pero produjeron
trazas idénticas en las tres reps. **Se midieron por separado**: las claves de
cache incluyen la estrategia. Solo ECHO/FIJO, con JSON idéntico, comparten
medición, como permitía el contrato.

### Desarrollo y veredicto completo

Ocho juegos oficiales de desarrollo, tres reps, 2000 decisiones por partida.
Los niveles y la puntuación siguientes suman las 24 partidas de cada brazo:

| Brazo | Niveles | Puntuación total |
|---|---:|---:|
| SEMILLA | 24 | 23,9990 |
| ECHO | 24 | 18,3599 |

Los niveles se conservan, pero la puntuación cae un 23,50 %; B4 falla.
La caída se concentra en g50t: ambos completan dos niveles sumando tres reps,
pero su puntuación total pasa de 7,1429 a 1,5037. Los otros siete juegos
conservan niveles y puntuación. Esto es desarrollo, no el examen R3 de
16 juegos y 112 niveles.

| Criterio | Resultado | Evidencia |
|---|---|---|
| B1: ≥5 % más niveles sin perder puntuación | ROJO | 1350 < 1457 requeridos; 10,8449 < 12,3810 |
| B2: superar FIJO | ROJO | 1350 = 1350; estrategia idéntica |
| B3: superar SIN FILTRO | ROJO | 1350 < 1387 |
| B4: desarrollo sin regresión | ROJO | 24 = 24 niveles; 18,3599 < 23,9990 puntos |
| B5: integridad, reconstrucción y replay | VERDE | fuentes intactas, diarios y prompts reconstruidos, contrafactuales aceptados comprobados de nuevo, cuatro replays exactos |

El solucionador resuelve 600/600 niveles y la generación repetida pasa sus
comprobaciones de determinismo. El replay de rep 0 usa procesos y cache
independientes. La auditoría de entrenamiento usa otra cache nueva: reconstruye
cada petición desde A, la política vigente y el diario; vuelve a comprobar
las tres aceptaciones y sus comparaciones A/B. No hay datos del examen en
los prompts. La evaluación local terminó con código de salida 0.

**B1 ∧ B2 ∧ B3 ∧ B4 ∧ B5: ROJO.** No se promueve la estrategia aceptada
sobre v5.7. La gramática resolvió el problema de formato; este experimento
no demuestra mejora que transfiera ni ventaja de la forma de preguntar.

### Diagnóstico posterior: cobertura y familias

El informe descriptivo posterior verifica las identidades de los registros;
no selecciona otra estrategia ni modifica el veredicto.

| Familia | Posibles | SEMILLA | ECHO | Diferencia |
|---|---:|---:|---:|---:|
| C1 | 75 | 75 | 75 | 0 |
| C2 | 135 | 135 | 135 | 0 |
| K1 | 120 | 120 | 120 | 0 |
| K2 | 180 | 179 | 163 | −16 |
| K3 | 150 | 135 | 140 | +5 |
| K4 | 120 | 111 | 79 | −32 |
| M1 | 120 | 82 | 82 | 0 |
| H1 (orden) | 225 | 62 | 68 | +6 |
| H2 (temporizador) | 255 | 252 | 255 | +3 |
| H3 (conteo) | 195 | 108 | 97 | −11 |
| H4 (copia) | 225 | 128 | 136 | +8 |

La caída de K4 no pudo verse en entrenamiento/control: **ni A ni B contienen
K4 o M1**. B tampoco contiene C1, K2, H1 ni H4. Esta cobertura insuficiente
es una limitación del piloto, no una explicación causal completa de cada fallo.
Las etiquetas se reconstruyeron para el informe; no se enviaron al modelo.
V4 protegía totales de solo ocho juegos, no cada juego ni cada familia.

Una nueva iteración necesita un contrato previo con A/B que cubran todas las
familias, evidencia de fallo más útil y un espacio de propuestas capaz de
añadir comportamiento temporal, en lugar de limitarse a cuatro controles.
Debe conservar las comparaciones y usar otro examen; 10000–10059 ya no son
un examen nuevo. No se cambian los criterios para convertir este rojo en verde.
**S6 sigue sin verde y no hay una fecha de mejora demostrable.**

### Artefactos y reproducción

Paquete: `dac54765521a7ce1123a0d2f0410fd7da46108020b74b629b53a9e043d854bb7`.
Código, perfiles, respuestas y resultados en las carpetas `s6b2-20260927`
y `s6b2-final-20260927`. El recibo fija las estrategias con SHA-256
`7fc03cce8e1fe43e8c3ab3e340ec2cb10ef4dfdd1476957eef058c69829bfa1c`.
Kaggle privado: `navywakura/echo45-s6b2-game-strategies`, estado COMPLETE.
Examen local iniciado 12:41 UTC, terminado y auditado a las 13:40 UTC.
Entorno: Python 3.12.13, NumPy 2.3.2, arcengine 0.9.3, arc-agi 0.9.1,
cuatro trabajadores; sin modelo durante las partidas.

- [Auditoría completa](../lab/seed/s6b2-final-20260927/exam/audit.json).
- [Recibo final y hashes de artefactos](../lab/seed/s6b2-final-20260927/closure.json).
- [Auditoría independiente de entrenamiento](../lab/seed/s6b2-final-20260927/independent-training-audit/audit.json).
- [Desglose y cobertura](../lab/seed/s6b2-final-20260927/exam/family-breakdown.json).
- [Diario resumido](../lab/seed/s6b2-final-20260927/campaign-summary.json) y [diferencias por partida](../lab/seed/s6b2-final-20260927/accepted-counterfactuals.json).
- [Congelación local](../lab/kaggle/s6b2-20260927/evaluation-freeze.json), [entorno real](../lab/seed/s6b2-final-20260927/local-execution-profile.json) y [reproducción](../lab/kaggle/s6b2-20260927/README.md).

Pruebas: 22 stdlib pasan (S6-A, limpieza del probe, frontera JSON,
crédito contrafactual, rechazo de regresión, reanudación y gramática).
El adaptador vacío reproduce exactamente v5.7 en las partidas comprobadas.
No se han editado el núcleo NEXUS, los modelos de Discord ni los exámenes
oficiales reservados; no se ha hecho un envío de competición.
