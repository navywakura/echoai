# S6-B18 — prototipo híbrido con inferencia GPU

Estado final del 5 de octubre de 2026: **CLOSED_NO_PROMOTION**. El micro y sus
auditorías terminaron correctamente. **El juez protegido rechaza la promoción
por dos pérdidas de puntuación. S6 sigue abierto y el examen no se ha abierto.**
La investigación y el notebook son privados.

B18 corrige el selector del híbrido: incorpora las lecturas reales de sus
propios candidatos, conserva los contraejemplos de los intentos anteriores,
descarta repeticiones de comportamiento cuando puede certificarlas y prueba
el primer candidato legal de su ordenación. El modelo propone el parche
inicial; el núcleo de ECHO elige las condiciones de los refinamientos. El
selector anterior deja esa última elección al LLM. Se incluye también la
búsqueda del núcleo sin LLM. El diseño conoce los antecedentes de B17 y PROBE;
es un ensayo de desarrollo dirigido, declarado antes de medir.

Se ejecutó en Kaggle con Qwen3-4B-Instruct-2507 Q4_K_M. Los registros de las
ocho generaciones confirman **37/37 capas en GPU Tesla T4**. La preparación
superó **39/39 pruebas de código** y cuatro partidas de paridad, agrupadas en
dos parejas de ejecución/replay. Estas cuatro partidas y la generación neutral
de calibración se contabilizan aparte del ensayo científico.

El ensayo evaluó **14 propuestas, correspondientes a 12 políticas distintas**,
sobre **80 partidas de desarrollo A y 40 partidas protegidas B nuevas**. Las
partidas pertenecen al banco de juegos procedurales S6. Las
repeticiones, las distintas políticas y las auditorías suman **3.480 ejecuciones
físicas de partidas**. Se hicieron ocho generaciones científicas del LLM; la
primera respuesta se compartió entre el selector anterior y el híbrido. El
híbrido utilizó esa única respuesta y dos refinamientos calculados por el núcleo.

| Brazo | Propuestas | Mejor total A | Pase A sin pérdidas | Conservación B |
| --- | ---: | ---: | --- | --- |
| Selector anterior con LLM | 8 | 383 | Ninguno; mantiene pérdidas | No elegible |
| Sintetizador sin LLM | 3 | 383 | Propuesta 3, auditada | Rechazado: dos pérdidas de score |
| Híbrido B18 | 3 | 383 | Propuesta 3, auditada | Rechazado: dos pérdidas de score |

La base A obtiene 378 niveles. Ambos métodos nuevos obtienen **383, una ganancia
de cinco niveles sin pérdidas individuales de nivel o puntuación**: +1 en A18 y
+4 en A53. La auditoría reconstruyó las 14 solicitudes y veredictos, volvió a
ejecutar las políticas en otra caché y reprodujo las trayectorias completas.
El selector anterior produjo cinco comportamientos distintos en sus ocho
propuestas; el híbrido y el sintetizador produjeron tres en tres intentos.

La guarda elegida por ambos métodos es:

```python
reset_known == 1 and pending_effect == 0 and world_events <= 16
```

El híbrido la aplica a `HOLD = 1`; el sintetizador, a `HOLD = 0`. En las 120
partidas medidas sus candidatos finales tienen **las mismas acciones, frames,
niveles y puntuaciones**, aunque sus políticas y parte de la telemetría difieren.
Este ensayo acredita una mejora del controlador de búsqueda. **No demuestra
una ventaja adicional del LLM frente a la búsqueda sin LLM.** Tampoco permite
atribuir la mejora de calidad a la GPU: todos los brazos con modelo usaron el
mismo backend CUDA en esta condición.

En B, la base obtiene **173 niveles** y ambos candidatos **176**. La partida de
versión 3 y semilla 28031 pasa de dos a cinco niveles completados. La puntuación
total sube de 1606,641734 a 1609,764089. **No se pierde ningún nivel en ninguna
partida**, pero aparecen dos pérdidas individuales de puntuación:

| Caso B | Versión / semilla | Niveles antes → después | Score antes → después | Decisiones antes → después | Reinicios automáticos antes → después |
| --- | --- | --- | --- | --- | --- |
| 27 | 3 / 28027 | 5 → 5 | 4,278598 → 4,047364 | 765 → 1308 | 19 → 35 |
| 39 | 3 / 28039 | 5 → 5 | 13,322537 → 13,206456 | 577 → 603 | 15 → 16 |

Las decisiones se cuentan excluyendo los reinicios automáticos de la lista de
acciones registrada. En B27 aumentan los costes de los tres primeros niveles;
en B39 mejora el coste del primero y empeora el del cuarto. Esos son efectos
medidos. El mecanismo causal concreto que produce cada desvío todavía no ha
sido aislado. La guarda encontrada conserva los resultados de A, pero su
alcance no basta para conservar el coste en estos casos nuevos.

El contrato exige cero pérdidas individuales de nivel **y** score, con la
tolerancia numérica declarada de 1e-10. Las dos pérdidas producen el rechazo.
Se reproducen en el replay completo y en la auditoría independiente de B.
Por tanto, el resultado es un rechazo científico válido; no hubo un fallo del
instrumento ni una discrepancia de replay. No se modifica la guarda a partir
de B ni se escoge otro candidato después de conocerlo.

| Fase | Ejecuciones físicas |
| --- | ---: |
| Desarrollo A: medición y replay | 2080 |
| Auditoría independiente de A | 1040 |
| Conservación B: medición y replay | 240 |
| Auditoría independiente de B | 120 |
| **Total** | **3480** |

El envío científico se realizó a las **04:51:54** y el runner cerró a las
**07:17:06**, hora de Madrid: aproximadamente 2 h 25 min. Los ocho comandos de
generación sumaron **35,93 segundos**, incluyendo el inicio de esos procesos;
esta cifra excluye la preparación y tokenización. Las partidas y los replays
se ejecutaron en CPU. Usar GPU resolvió la ejecución rápida del LLM; el tiempo
del ensayo siguió dominado por las simulaciones y su verificación.

La descarga se verificó contra el manifiesto congelado y el presupuesto. Una
segunda revisión local, sin importar el solver ni ejecutar partidas, recalculó
las ganancias, las pérdidas, las sumas de score, los pases y los recuentos desde
los registros. Comprobó también ejecución, replay y auditoría de cada política.
Las **65 fuentes congeladas** mantienen sus hashes.

El siguiente trabajo requiere una condición nueva de desarrollo que investigue
el coste de recuperación y las consecuencias de acortar las esperas en más
contextos. La fiabilidad de la señal `pending_effect = 0` como condición para
esa intervención es una hipótesis a contrastar, no una garantía demostrada.
Estos resultados B ya se han visto y no pueden reutilizarse como confirmación
ciega tras un ajuste. Hará falta otro bloque protegido, seguido del piloto
principal, la campaña y el examen de cuatro brazos B1–B5. **No queda ningún
piloto, campaña o examen B18 pendiente de lanzamiento automático.**

[Contrato congelado](ECHO45-S6-B18-DESIGN.md) ·
[Notebook privado de Kaggle](https://www.kaggle.com/code/navywakura/echo45-s6b18-micro-20261005) ·
[Cierre](../lab/seed/s6b18-20261005/kaggle-results/closed.json) ·
[Auditoría A](../lab/seed/s6b18-20261005/kaggle-results/micro-audit.json) ·
[Auditoría B](../lab/seed/s6b18-20261005/kaggle-results/retention-audit.json) ·
[Verificación de descarga](../lab/seed/s6b18-20261005/download-verification.json) ·
[Revisión aritmética reproducible](../lab/kaggle/s6b18-20261005/arithmetic-review.json) ·
[Calibración y recuperación del monitor](../lab/kaggle/s6b18-20261005/CALIBRATION.md).

Para repetir únicamente la revisión local de artefactos:

```bash
python3 lab/kaggle/s6b18-20261005/review.py
```
