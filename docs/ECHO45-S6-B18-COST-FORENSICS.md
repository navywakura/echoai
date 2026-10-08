# B18: por qué ganó niveles y perdió conservación

5 de octubre de 2026. B18 cerró con auditorías válidas y dos regresiones de
score. El rechazo permanece registrado. Su base de 173 niveles en B pasó a
176, pero v3/28027 y v3/28039 requirieron más decisiones. No basta con sumar
niveles: el contrato exige conservar cada puntuación individual.

La palabra «espera» estaba ocultando una distinción del código. En
`echo_arc/agent.py`, `Arc3EchoV57.choose` consume HOLD cuando decide probar una
tecla reconocida como reinicio. Durante la inhibición ECHO puede moverse;
el contador limita volver a ejecutar esa intervención. Se decrementa antes
de comprobarse. HOLD 0 y 1 eliminan prácticamente la protección del siguiente
turno; su igualdad de comportamiento en B18 es una medida sobre 120 casos,
no un teorema sobre todas las composiciones posibles de parches.

En el entorno H4, `Level._hstep` de `seed/arc3gym.py` hace dos cosas cuando
recibe esa tecla: devuelve el cuerpo al inicio y reemplaza la copia que
reproduce su trayectoria. Si la copia estaba activando un interruptor, puede
perderse la apertura de la puerta. Si aún se movía, se interrumpe el trabajo
pendiente. `_tried_at`, del que deriva `pending_effect`, se borra en cuanto
sube el contador de eventos remotos. Un evento observado no acredita que
el proceso haya acabado ni que deje de ser útil.

Se reconstruyeron las acciones ya registradas de cuatro casos B18, base y
candidato. Los ocho recorridos reproducen todos los hashes de frames. No se
volvió a ejecutar el solver para elegir acciones, no se reabrió la auditoría
B18 y el estado privado leído por el analista no se entrega al actor.

| Caso consumido | Primera divergencia, índice de acción | Qué hace el candidato | Reinicios con copia sin terminar, base → candidato |
| --- | ---: | --- | ---: |
| v3/28027 | 43 | Reinicia cuando la copia ya está en el interruptor; luego repite reinicios que interrumpen nuevas copias | 26 → 48 |
| v3/28039 | 162 | Reinicia con 14 movimientos pendientes de la copia, que había avanzado 1 de 15 | 18 → 20 |
| v3/28026 | 136 | El cambio acaba reduciendo el coste en esta partida | 2 → 0 |
| v3/28031 | 80 | El cambio permite terminar tres niveles adicionales | 80 → 77 |

Los contadores describen trayectorias distintas completas; no atribuyen cada
pérdida posterior a un solo reinicio. En 28039 se mejora el primer nivel y
se empeora el cuarto. La modificación inicial afecta la experiencia y la
memoria posteriores. Desactivar el parche más tarde no restaura el estado
interno que habría tenido la base. Esto explica por qué una guarda aplicada
a unos pocos consumos puede alterar costes de niveles posteriores.

El diagnóstico posterior B19 conservó la guarda B18 y modificó solo HOLD en
los doce casos declarados en su contrato. Sus 132 ejecuciones dan:

| HOLD | Ganancia de niveles en el cribado | Casos con pérdida de nivel o score |
| ---: | ---: | ---: |
| 1 | +8 | 2 |
| 2 | +8 | 2 |
| 4 | +4 | 1 |
| 8 | +1 | 2 |
| 12 | +1 | 2 |
| 16 | +1 | 2 |
| 20 | 0 | 1 |
| 24 | 0 | 0 |
| 32 | 0 | 1 |
| 40 | 0 | 0 |

Ninguna duración supera simultáneamente +2 y conservación estricta. Es una
refutación del arreglo «cambiar solo la duración» dentro de este conjunto,
no una prueba de imposibilidad para toda la gramática. Las cuatro partidas
B18 reetiquetadas como desarrollo conservan todas las columnas originales
del registro basal al añadir observación, salvo la etiqueta de partición;
las nuevas columnas diagnósticas no cambian el comportamiento.

El buscador B18 tiene además tres límites verificables en el código:

- Su ordenación maximiza la cobertura de ganancias antes de reducir el coste
  asociado a pérdidas, aunque una mejora menor ya superaría el umbral +2.
- Mantiene el valor HOLD del objetivo durante todos sus refinamientos.
- Cuenta todas las lecturas HOLD de una partida perdida como posibles
  intervenciones, incluidas aquellas donde el parche no cambió el valor basal.

El último punto confundía una consecuencia posterior del recorrido con otra
intervención del parche. B19 mantiene las lecturas modificadas tempranas y
tardías, pero excluye del coste atribuido las que consumieron el mismo valor
que la base en ese contexto. Sigue siendo evidencia asociativa: la selección
solo obtiene autorización después de ejecutar y verificar la política.

La primera revisión retrospectiva del ranking sobre los doce casos priorizaba
`world_events <= 8`, con una lectura asociada a pérdida. Al distinguir las
intervenciones reales, el ranking coloca primero `goal_evidence == 1` y luego
`level >= 1`, sin lecturas de intervención asociadas a pérdidas en esa memoria.
Esto no demuestra que esas guardas funcionen: pueden crear nuevos consumos
y consecuencias. No se inserta ninguna de ellas como respuesta conocida en
el código ni se publica un pase sin medir.

B19 incorpora las tres correcciones en `echo_arc/cost_guard_search.py` y
amplía el proceso de cualificación: cribado dirigido → auditoría → 160 casos
de desarrollo → auditoría → 80 casos protegidos nuevos → auditoría. Tiene un
control con el buscador B18 y otro sin LLM, una sola generación inicial
compartida, doce oportunidades por brazo y 6000 partidas físicas como tope.
Las 68 fuentes se congelaron después de superar 52 pruebas de código.
El primer comando de tests señaló un nombre de módulo inexistente; la batería
correcta y su repetición final pasaron. No fue un fallo de las partidas.

S6 todavía necesita conservación nueva, piloto emparejado, campaña y examen
B1–B5. El empate del híbrido y el sintetizador en B18 tampoco prueba ventaja
adicional del LLM. La GPU reduce el coste de inferencia; no resuelve estas
limitaciones del controlador ni acelera automáticamente las partidas CPU.

[Contrato de diagnóstico](ECHO45-S6-B19-DEVELOPMENT.md) ·
[Contrato B19](ECHO45-S6-B19-DESIGN.md) ·
[132 resultados](../lab/seed/s6b19-diagnostic-20261005/result.json) ·
[Reconstrucción de los ocho recorridos](../lab/seed/s6b19-forensics-20261005/reconstruction.json) ·
[Código de reconstrucción](../lab/seed/s6b19-forensics-20261005/reconstruct.py) ·
[Ranking retrospectivo revisado](../lab/seed/s6b19-diagnostic-20261005/ranking-interventions-only-review.json).
