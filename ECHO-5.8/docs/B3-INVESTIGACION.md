# B v3 · investigación: cómo actúa ECHO y por qué se atasca

20 de octubre de 2026. Investigación pedida por Roger tras cerrar B v2 en
desarrollo. **No es un contrato ni una medida de examen**: son trazas de
desarrollo (semillas 7 000 000+, 10 episodios por familia, régimen A2) con la
memoria de A leída con las correcciones que B encontró (`order`, `refine` de
las clases 8 y 12 por rango 0). Herramientas: `echo58/b3/trace.py` (detecta
el bucle y vuelca qué cree el agente de cada objeto en ese momento) y
`echo58/b3/probe_fixes.py` (enciende arreglos genéricos uno a uno). Los
nombres de objetos solo los usa la herramienta para explicarnos la traza; el
agente no los ve. Datos: `lab/echo58/b3/trace-*.json`.

## 1. Cómo decide ECHO hoy (resumen de `memx/agent.py`)

Cada paso: (1) ir a lo que cree META; (2) si no, probar la acción desconocida
más cercana (o, por prioridad, verificar que algo se puede coger, accionar lo
que abre, ir a buscar lo que podría abrir algo); (3) si no, soltar lo que
lleva; (4) si no, quedarse quieto. Antes de coger algo suelta lo que lleva.
Todo depende de creencias por (objeto, acción, mano); **no hay memoria de lo
que hizo hace un momento ni noción de «esto ya lo he intentado así»**.

## 2. Por qué se atasca (trazas)

| Familia | Éxito | Bucle detectado | Patrón dominante en los fallos |
|---|---|---|---|
| BlockedUnlockPickup | 0/10 | 10/10 | coger llave ↔ soltar llave, ~273 veces |
| ObstructedMaze-1Dlh | 0/10 | 10/10 | coger caja ↔ soltar caja, ~130 veces |
| ObstructedMaze-2Dl | 4/10 | 10/10 | coger llave ↔ soltar llave (6 fallos) |
| KeyCorridorS3R2 | 7/10 | 10/10 | intentar coger una puerta cerrada ~230 veces (3 fallos) |
| DynObs-Random-6x6 | 8/10 | 1/10 | quieto: cree que ya no hay nada que probar (2 fallos) |

Tres causas, ninguna de memoria:

1. **Oscilación coger/soltar.** Con la llave en la mano quiere *verificar* que
   otro objeto se puede coger (regla «probar primero lo reversible»), suelta
   la llave; entonces la regla «ve a buscar lo que podría abrir algo» la
   vuelve a coger. Dos reglas correctas por separado se anulan. Ninguna
   detecta que el estado se repite.
2. **Contabilidad con la mano llena (defecto).** Si no hay casilla libre para
   soltar, intenta coger con la mano llena; el resultado se apunta bajo
   (objeto, coger, *mano llena*) pero la regla consulta (objeto, coger,
   *mano vacía*): nunca aprende que falló y lo repite.
3. **Quietud.** Cuando todo está «sabido» y nada es META, se queda quieto.

Lo que **falta** del todo: «apartar lo que tapa el camino» (la pelota delante
de la puerta) y «abrir un contenedor para ver qué tiene» (la llave dentro de
la caja) como conductas, no como creencias.

## 3. Experimento: arreglos genéricos uno a uno

| Familia | sin arreglo | `loop` | `handkey` | ambos |
|---|---|---|---|---|
| KeyCorridorS3R2 | 7 | **0** | **10** | 0 |
| ObstructedMaze-1Dlh | 0 | **6** | 0 | 6 |
| ObstructedMaze-2Dl | 4 | **0** | 4 | 0 |
| BlockedUnlockPickup | 0 | 0 (cambia el fallo) | 0 | 0 |

- `loop` (prototipo tosco): un estado visto 3 veces → lo que perseguía en los
  últimos pasos «no hace nada» en este episodio.
- `handkey`: apuntar el intento de coger con la mano llena bajo la clave que
  la regla consulta.

Lectura:

1. **Hay cadena.** En BlockedUnlockPickup, romper la oscilación hace aparecer
   el **siguiente** obstáculo (la pelota que tapa la puerta): el fallo cambia
   de «coger/soltar llave» a «coger pelota / soltar». Es el «desbloqueo
   endógeno» que proponía Argon: cada arreglo destapa el siguiente atasco.
2. **Los arreglos interactúan y pueden dañar.** `loop` tosco rompe
   KeyCorridor (7 → 0) y ObstructedMaze-2Dl (4 → 0) porque prohíbe demasiado
   (hasta pisar suelo); combinado con `handkey`, manda `loop`: la columna
   «ambos» es igual a `loop` solo. (Una primera versión de esta tabla daba
   «ambos = sin arreglo»: era un error de mi comando, que pasaba los dos
   nombres como una sola palabra y no encendía ninguno. Corregido.)
   El orden y el ajuste importan: justo lo que una puerta de aceptación
   ronda a ronda tendría que decidir.
3. `handkey` es un defecto de la política base. Se puede tratar como una
   edición que ECHO descubre por una señal genérica («repito la misma acción,
   el resultado es NOOP y mi creencia no cambia»).

## 4. Propuesta para B v3 (PLAN, sin contrato)

**Idea:** ampliar el menú de automejora de «cómo leo mi memoria» a **«cómo
actúo»**, con piezas genéricas sin nombres que ECHO enciende, ordena y ajusta
desde sus fallos medidos. Las rondas y la medida serían las de B v2 (mezcla
estacionaria, episodios fallidos, `lote_final`, `vacia_online`, azar con el
mismo menú).

Menú de política candidato (a validar en desarrollo):

| Pieza | Señal que la dispara en el diagnóstico |
|---|---|
| `loop(k, alcance)`: estado repetido k veces → la última intención (o las últimas n) no sirve en este episodio | estado repetido |
| `book_hand`: el intento con la mano llena se apunta donde se consulta | misma acción repetida, NOOP, creencia sin cambiar |
| `commit`: no soltar lo que se lleva para verificar otra cosa mientras quede un objetivo que lo podría usar | oscilación coger/soltar |
| `clear(dist)`: si la única casilla de acceso a algo sin probar está ocupada por algo que se puede coger, cogerlo y dejarlo a ≥ dist | intención imposible de alcanzar |
| `open_first`: probar accionar antes que coger en objetos de una casilla | coger funciona pero no hay progreso |
| `wander`: si no queda nada, explorar la casilla accesible menos visitada en vez de quedarse quieto | quietud |

Riesgos que el contrato tendría que controlar:

- **El arquitecto soy yo.** Si las piezas están hechas a medida de las familias
  de examen, el mérito es mío y no de ECHO. Mitigación: piezas genéricas
  diseñadas solo con familias de desarrollo; sonda de examen con familias
  distintas; `azar` con el mismo menú y `lote_final` con el mismo presupuesto.
- **Es el terreno de RSI-1** (que salió rojo). La diferencia aquí: las piezas
  se activan por señales de fallo localizadas, y hay evidencia de cadena.
- Las piezas interactúan; una mala puede romper familias que iban bien. La
  puerta estricta sobre la mezcla completa debería frenarlo.

## 5. Corrección: lo que falla en el banco real (reconstrucción)

Las trazas de §2–3 usaban un agente distinto del banco: memoria inicial +
correcciones, sin las rondas acumuladas y **sin aprendizaje en línea entre
episodios**. `echo58/b3/replay.py` reconstruye el brazo `recursiva` de B v2
ronda a ronda y juega la sonda igual que el banco; reproduce los fallos de
desarrollo exactamente (3 macros × 6 rondas × 4 familias). Datos:
`lab/echo58/b3/replay-m*.json`. Revisión de Argon con estos datos:
`research/ARGON-B3-20261020-REVIEW.md`.

- En la sonda, la caja de ObstructedMaze-1Dlh **ya se resuelve** desde la
  ronda 1 (0–3/30). El suelo es **KeyCorridorS3R3** (46 de 51 fallos en r5).
- Con `handkey` solo en la sonda: 51 → 25 fallos en r5 (KeyCorridorS3R3
  46 → 20).
- Lo que queda es abrir/cerrar la misma puerta en bucle.
- En la **mezcla**, el atasco que queda es la pelota de BlockedUnlockPickup.

Cadena observada en la sonda: lava (memoria) → mano llena (política) →
oscilación de puertas (política). Es la forma que B v3 necesita, pero **de
momento la he encontrado yo mirando trazas, no ECHO**.

## 6. Prototipo de una sesión (protocolo de Argon, 20/10, desarrollo)

Código `echo58/b3/policy.py` (agente con el arreglo de la mano en la base y
piezas `commit`, `no_retoggle`, `clear`, `wander`, `no_repick`), `b3/bench.py`
(rondas de B v2 con menú memoria + piezas propuestas desde señales de los
episodios fallidos: `pickdrop`, `retoggle`, `blockdrop`, `idle`; la pareja
`commit`+`no_repick` se ofrece también junta porque sale de la misma señal).
Sonda de desarrollo: ObstructedMaze1Dlh → **ObstructedMaze1Dlhb** (la 1Dlh ya
se resolvía). Datos: `lab/echo58/b3/bench-dev-20261020T201837.json` y
`…T202226.json`.

Ajustes de las piezas durante la sesión, todos en familias de desarrollo:
`commit` solo cuenta objetivos alcanzables que no son pared, y solo bloquea
cambiar por algo **ya cogido en este episodio** (si no, abría la caja con la
llave y la caja desaparecía); `clear` anda como mucho 8 pasos; `no_repick`
añadida al ver que con `commit` quedaba un bucle coger/soltar la pelota.

Fallos en la sonda (suma de 3 macros, fallidos/daño):

| Brazo | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| **recursiva** | 267/173 | 118/14 | 84/0 | 63/0 | 38/0 | 39/0 |
| piezas_dadas (todas desde r0; ECHO solo edita memoria) | 215/173 | 71/22 | 44/0 | 41/0 | 37/0 | 43/0 |
| vacia_online | 116/25 | = | = | = | = | 116/25 |
| sin_acumular | 267/173 | 118/14 | 113/17 | 120/21 | 157/29 | 153/33 |
| lote_final | = fija hasta r4 | | | | | 157/33 |
| azar (mismo menú) | 267/173 | 270/175 | 266/154 | 207/65 | 201/67 | 199/63 |
| fija | 267/173 | 271/169 | 275/161 | 280/153 | 284/149 | 286/146 |

Por macro (recursiva): 86→41→30→16→15→14; 91→39→23→15→12→14;
90→38→31→32→11→11.

Lectura:

1. **Cuatro mejoras seguidas en la suma** (r0→r4), cinco en la macro 1. Es lo
   que B v1 y B v2 no lograron.
2. **Dependencia medida, no programada por mí:** en las 3 macros la pareja
   `commit`+`no_repick` se probó en la ronda 1 y la puerta la **rechazó**; se
   aceptó en r2–r4. Igual `no_retoggle` y `clear`: propuestas pronto,
   rechazadas, aceptadas después.
3. **Pero el mérito del menú es mío:** `piezas_dadas` acaba igual (43 frente
   a 39). Lo que ECHO hace solo es **elegir y ordenar** las piezas desde sus
   fallos; las piezas las diseñé yo mirando trazas. `wander` nunca se acepta.
4. Gana a todos los controles en r5 (vacía en línea 116, sin acumular 153,
   lote final 157, azar 199, fija 286).
5. Riesgo para el examen: ObstructedMaze2Dl (sonda de examen) la vi en las
   trazas de §2 (otras semillas, 7 000 000+). Conviene cambiarla en el
   contrato por una familia que no haya mirado.

Con la regla de corte de Argon (≥ 3 escalones encontrados por ECHO), el
prototipo **pasa en desarrollo**. Siguiente: contrato B v3 para que Roger lo
apruebe (afirmación: «ECHO elige y encadena ediciones de memoria y de política
desde sus propios fallos»; no «inventa» políticas).

## 7. Siguiente paso (antes del prototipo)

1. Implementar las piezas como interruptores limpios sobre el agente (sin
   tocar A ni B v1/v2), con la señal de diagnóstico de cada una.
2. Medir en desarrollo cada pieza sola y en orden, en las familias de esta
   investigación: confirmar que hay cadenas de ≥ 3 escalones *que ECHO
   encuentra solo*.
3. Si las hay: contrato de B v3 para que Roger lo apruebe. Si no: cerrar B y
   pasar a C (ENJAMBRE).
