# ECHO-4.5 · H1 y H3 implementados en v5.8

2026-09-27. **Implementación comprobada en desarrollo.** H1 conserva evidencia
de orden; H3 cuenta entradas y aprende umbrales. Ambos tienen pruebas de
integración, observabilidad y comparaciones reproducibles. El criterio del
[contrato de desarrollo](ECHO45-H1-H3-DESIGN.md) se cumple. Falta un examen
reservado propio: estos resultados no convierten S6 en VERDE.

## Qué se construyó

- `echo_arc/temporal_memory.py`: `OrderMemory` y `CountMemory`, con memoria
  acotada, apoyo, contradicciones y separación entre reglas e intento actual.
- `echo_arc/temporal_agent.py`: v5.8 hereda v5.7; adquiere entradas, detecta
  efectos remotos, prueba pares y reentradas y reutiliza reglas aprendidas.
- `echo_arc/temporal_runner.py`: fábrica privada; conserva el runner y el
  registro de agentes anteriores. Incluye ablaciones sin orden, sin conteo
  y sin ambos módulos.
- `echo_arc/temporal_bench.py` y `temporal_audit.py`: medición de desarrollo,
  trazas encadenadas, contabilidad y replay. La mini terminal existente muestra
  decisiones, entradas, pares, umbrales y evidencia.

No se modifican las fuentes congeladas de v5.7/S5-E/S6. No se incorpora un LLM
al actor ni se entrena una red neuronal. [Funciones y comandos](ECHO45-H1-H3-MODULES.md).

## Entrenamiento completo

Mundos **gym-train 0–39**, versiones v2 y v3, tres repeticiones, presupuesto
2000 decisiones por partida y mismo `seed_for(game_id, rep)` para ambos
agentes. Total: **480 partidas**. Los máximos de la tabla suman niveles de
mundos y repeticiones; no son tareas oficiales ARC ni un examen nuevo.

| Cohorte / familia | v5.7 | v5.8 | Cambio |
|---|---:|---:|---:|
| v3 · H1, orden | 45/135 | **134/135** | +89 |
| v3 · H3, conteo | 77/165 | **152/165** | +75 |
| v3 · H2, modo | 190/195 | 190/195 | 0 |
| v3 · H4, copia | 57/105 | 57/105 | 0 |
| v3 · total | 369/600 | **533/600** | +164 |
| v2 · total anterior | 573/600 | **574/600** | +1 |

La mejora de v2 está en K2, 104 → 105 niveles. Las otras seis familias
mantienen sus niveles y puntuaciones. H2 mantiene los niveles, pero reduce
coste; H4 mantiene también la puntuación.

| Cohorte y agente | Puntuación media del gimnasio | Decisiones | Reinicios automáticos |
|---|---:|---:|---:|
| v2 · v5.7 | 24,7708 | 79 622 | 2155 |
| v2 · v5.8 | 38,0192 | 64 325 | 1845 |
| v3 · v5.7 | 3,5229 | 172 629 | 4120 |
| v3 · v5.8 | 64,0285 | 60 012 | 1451 |

La puntuación es la fórmula histórica del runner aplicada a la línea base del
gimnasio. No equivale al porcentaje de niveles resueltos ni a una puntuación
de competición. `actions_per_level` excluye reinicios automáticos; el registro
de acciones y la auditoría los conservan y cuentan por separado.

Evidencia: [resumen y registros](../lab/observability/h1h3-training-final-20260927/summary.json),
[fuentes y configuración](../lab/observability/h1h3-training-final-20260927/profile.json),
[auditoría: 480 registros, 1 141 735 eventos y 12 replays exactos](../lab/observability/h1h3-training-final-20260927/audit.json).

## Ablaciones

Seis mundos de entrenamiento, semillas 0/4/5/7/10/15, una repetición y
presupuesto 2000: tres H1 y tres H3, 15 niveles posibles por familia.

| Agente | H1 | H3 | Total | Decisiones | Puntuación media |
|---|---:|---:|---:|---:|---:|
| v5.7 | 4/15 | 12/15 | 16/30 | 11 722 | 2,9103 |
| v5.8 | 15/15 | 15/15 | 30/30 | 1089 | 80,1787 |
| Sin orden | 15/15 | 15/15 | 30/30 | 1174 | 64,8710 |
| Sin conteo | 15/15 | 9/15 | 24/30 | 5911 | 41,7316 |

Sin orden aún completa H1: el módulo aporta eficiencia en esta muestra,
no prueba que sea indispensable. Su puntuación H1 pasa de 81,3727 a 50,7370.
Sin conteo pierde seis niveles H3. Estas ablaciones retiran también las pruebas
de exploración correspondientes. v5.8 contiene además planificación exacta y
prioridad de exploración tras un efecto; no se atribuye toda la mejora frente
a v5.7 exclusivamente a retener reglas.

La ablación sin ambos módulos conserva exactamente acciones, fotogramas y
modelo base de v5.7 en los tres casos de integración comprobados.

Evidencia: [ablaciones finales](../lab/observability/h1h3-ablations-final-20260927/summary.json)
y [auditoría: 24 registros, 60 175 eventos y ocho replays exactos](../lab/observability/h1h3-ablations-final-20260927/audit.json).

## Ocho juegos oficiales de desarrollo

Se usan únicamente las ocho copias de desarrollo ya congeladas en S6-B2,
repeticiones 0/1/2, presupuesto 2000; nunca los 16 juegos reservados.

| Agente | Niveles sumados | Suma de puntuaciones | Media |
|---|---:|---:|---:|
| v5.7 | 24 | 23,99903744 | 0,9999598933 |
| v5.8 | 24 | 23,99903744 | 0,9999598933 |

Se mantiene el resultado de desarrollo oficial. En estas 24 partidas de
v5.8 no se ejecutó ninguna acción del controlador temporal: los módulos
todavía no amplían la cobertura de percepción necesaria para estos juegos.

Evidencia: [comparación de 48 partidas](../lab/observability/h1h3-official-development-20260927/summary.json)
y [auditoría: 289 290 eventos y dos replays exactos](../lab/observability/h1h3-official-development-20260927/audit.json).

## Pruebas y procedencia

- 32 comprobaciones stdlib: siete de memoria temporal, cinco del observador y
  veinte de `ThoughtLog`/`TALK`. Pasan usando Python del sistema.
- Seis pruebas ARC pasan: umbrales ocultos 2/4/5, papeles H1 intercambiados
  y otras paletas, reinicio/nivel, exclusión del movimiento/reloj, paridad de
  observación/ablación y exclusión de teclas virtuales de clic.
- Ocho pares de partidas del observador anterior mantienen acciones y
  fotogramas. [Recibo de la primera verificación](../lab/temporal/h1h3-20260927/unit-verification.json).
- Las 29 fuentes protegidas del inicio conservan sus hashes. El contrato de
  desarrollo también conserva su hash original.

Después de medir y auditar se añadió una condición de compatibilidad:
el controlador temporal solo puede emitir teclas presentes en las acciones
disponibles. Las teclas virtuales que v5.7 aprende para navegar mediante clics
pertenecen al controlador de clic anterior. El test de regresión falló antes
de la condición y pasa después.

Las fuentes exactas de la medición anterior se conservan en
[v58-measured-sources](../lab/temporal/h1h3-20260927/v58-measured-sources/manifest.json).
Su replay archivado H1 también pasa. Para repetir una medición histórica sin
reemplazar las fuentes activas:

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python lab/temporal/h1h3-20260927/replay_measured.py lab/observability/h1h3-training-final-20260927/v5.8-r0/gym3-0004-H1/record.json
```

La compatibilidad se verifica con fuentes actuales en 18 partidas C2, cuatro
partidas de teclado H1/H2/H3/H4 y las 24 partidas oficiales de desarrollo.
Se comparan acciones, fotogramas, contadores, puntuaciones y modelo base contra
los registros anteriores; en teclado también el informe temporal completo.
En clic puede cambiar la declaración de cobertura, sin cambiar el comportamiento.
[Verificación de compatibilidad](../lab/temporal/h1h3-20260927/compatibility-verification.json)
y [recibo final](../lab/temporal/h1h3-20260927/completion.json).

## Lo que falta

H3 falla en el mundo de entrenamiento 35: 0/2/0 niveles según repetición;
el controlador temporal no se activa y no aprende un umbral. La identificación
del cuerpo sigue limitando la cobertura. H1 pierde un nivel en el mundo 38,
repetición 0. No hay resolución universal de estas familias.

La primera integración requiere cuerpo rectangular, marcadores compatibles
y teclas físicas con reglas observadas. Conserva tipos por color dentro del
juego, sin demostrar transferencia a otra semántica visual. La memoria temporal
no convierte toda la tabla histórica T en un modelo de estados ocultos.

Quedan un contrato y examen reservado nuevos, transferencia a otros mundos
y la siguiente iteración de S6. H1/H3 se marcan **✅ implementados y comprobados
en desarrollo**; la validación reservada y S6 VERDE siguen **❌ pendientes**.
[Roadmap actualizado](ECHO45-ECHO5-ROADMAP.md).
