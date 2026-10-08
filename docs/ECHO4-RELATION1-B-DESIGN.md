# E4-RELATION-1 — contrato B v1 (PLAN, pendiente de aprobación)

2026-09-23. Contrato anterior al desarrollo. RELATION-A permanece sellada
(`ce24ccaa61f9d8b9b781274857b6ce15a9e75817bbf8d0b5fd2649a403369539`); sus 115
fuentes y evidencias no se modifican. INTERACTION D no se reutiliza como examen.

Motivo del relato (La fuga, 17:13): «necesito su ayuda pero no puedo moverme».
Es la tarea B. El motivo da nombre al dominio; no es evidencia ni requisito.

## Pregunta

¿La historia de encuentros de la tarea A, conservada en la CAM propia, mejora
decisiones aprendidas en una **tarea distinta** B, más allá de conocer la
identidad y predecir las acciones A de la contraparte?

«Transferencia» aquí = la historia registrada en A indexa decisiones de B.
No es generalización a cualquier tarea, ni afecto, confianza sentida o vínculo.

## Tarea B: petición de ayuda (HELP)

Encuentro = un paso B y después el paso A heredado, con la misma contraparte.
El paso B ocurre antes que el A del mismo encuentro: solo la historia de
encuentros **anteriores** está disponible.

Aprendiz, acciones B: 0 pedir ayuda, 1 trabajar solo, 2 esperar.
Contraparte, acciones B: 0 ayudar, 1 no ayudar. Solo se decide si se pidió.

| Resultado | Aprendiz coste/producción | Contraparte coste |
|---|---|---|
| pedir + ayuda | 1 / 8 | 3 |
| pedir + no ayuda | 3 / 0 | 0 |
| solo | 1 / 2 | 0 |
| esperar | 0 / 0 | 0 |

Valores enteros, fijados antes del desarrollo. No se retocan tras ver B.
Recursos: mismos libros de 4096 de INTERACTION, sin recarga; B y A los comparten.
Si falta presupuesto, la acción se ejecuta como incapaz (sin coste ni producción),
igual que A.

**Perfil de reciprocidad diseñado (incentivo privado).** La contraparte recibe
+16 por ayudar si en sus **tres últimos episodios propios con el aprendiz**
hubo al menos un éxito conjunto confirmado, y −16 si ayuda sin él; al revés
si no ayuda. Lo calcula desde **su** RelationMemory, no desde la del aprendiz.
Se publica aparte y **nunca cuenta como ganancia de interacción**, igual que
el incentivo de INTERACTION. Es un perfil asimétrico diseñado, no reciprocidad
emergente. Las contrapartes preentrenan B en privado con sus tres contextos
(sin historia / sin éxito reciente / con éxito reciente) antes de la vida.

Consecuencia esperada del dominio A heredado (a comprobar en desarrollo, no
supuesta): la contraparte que prefiere unir en contexto 0 genera éxitos
confirmados intermitentes; la que prefiere unir en contexto 2 (producción 0)
no genera ninguno. La fiabilidad reciente cambia con el tiempo dentro de la
misma identidad; por eso identidad sola no basta y el orden importa.

Sondeo previo al contrato, sin B implementado (solo la sesión A de RELATION,
semillas de desarrollo 151/163/179, 480 encuentros): una contraparte da 71/67/69
éxitos confirmados en 240 episodios y la otra 0/0/0. Tras la formación, «≥1 éxito
en los 3 episodios previos» se da en el 84/85/88 % de los encuentros con la
fiable. Es desarrollo, no evidencia. Esperanza bruta frente a identidad sola:
≈4 unidades por cada encuentro fiable sin éxito reciente (≈14 encuentros,
≈56 unidades por vida), un margen pequeño; D fijará umbrales tras ver B, no antes.

## Qué ve el aprendiz en B

Contexto público del encuentro y presupuesto propio (0..4, 5+), como INTERACTION.
Según el brazo, además una síntesis derivada de su propia RelationMemory:
éxitos confirmados en los tres últimos episodios con esa contraparte,
en cubos `sin historia (<3 episodios) / 0 / ≥1`.

La síntesis indexa una **fila WSP16 derivada, sin extract ni has_fact**, en la
CAM original (dominio 9, generador 8, un `style` nuevo reservado para B).
La Q original aprende en esas filas con la recompensa física real de B.
Sin tabla Q adicional, sin bus, sin LLM, sin regla escrita «si hubo éxito, pedir».
La síntesis es una consulta, no un hecho nuevo, ni una predicción convertida en hecho.
Los episodios B **no** se escriben en RelationMemory: A sigue siendo la única
física validada del diario. B termina en una observación factual de liquidación,
como la celda de INTERACTION.

## Brazos emparejados

Misma semilla, mismo calendario, misma preformación. La fase A de cada brazo
es idéntica (A es pasiva; comprobado en RELATION-A). Solo cambia la fila B.

| Brazo | Fila B contiene | Qué controla |
|---|---|---|
| `history` | cubo de historia reciente con esa contraparte | tratamiento |
| `other_only` | identidad + síntesis OTHER de INTERACTION | predecir al otro sin historia |
| `shuffled` | cubo calculado sobre la historia de la díada barajada con semilla fija | orden eliminado |
| `pooled` | cubo sobre los tres últimos episodios de cualquier contraparte | identidades agrupadas |
| `no_history` | solo contexto y presupuesto | sin historia relacional |
| `solo` | propuesta fija: trabajar solo | control fijo, no aprendido |
| `always_ask` | propuesta fija: pedir | control fijo, no aprendido |

Todos los brazos mantienen gate, ejecución, aprendizaje Q, costes y presupuestos.

## Banco de desarrollo

- Semillas de desarrollo 151, 163, 179. Nunca son examen.
- 480 encuentros: los 288 primeros solo A (formación, idéntica a INTERACTION);
  los 192 siguientes B+A. Calendario balanceado en bloques de seis como INTERACTION.
- Q continúa aprendiendo en B; sin exploración forzada; greedy en A tras 288.
- Publicar por brazo: neto B del aprendiz, neto B conjunto físico, ayudas,
  rechazos, incentivo privado excluido, neto A y neto de vida completa.

Criterio de desarrollo (no es examen): en las tres vidas, `history` supera en
neto B del aprendiz a **cada** brazo aprendido (`other_only`, `shuffled`,
`pooled`, `no_history`) y a `solo`. Si no lo hace, se publica el rojo y se
decide con Roger si hay v2; no se retocan pagos ni la regla de reciprocidad
después de ver resultados. Los márgenes numéricos de D se fijan en el contrato
C/D, antes de abrir cohortes nuevas.

## Pruebas B

- Paridad A: acciones, costes y digests A idénticos entre brazos.
- La síntesis usa solo episodios anteriores al encuentro; ningún dato del paso A
  actual ni del futuro entra en la fila B.
- El incentivo de la contraparte usa su memoria propia; el aprendiz nunca lo lee.
- Filas B sin hecho ni extract; cero hechos falsos, borrados y llamadas LLM.
- Gate INHIBIT del aprendiz impide pedir; contraparte vetada no ayuda.
- Recibo ausente o identidad ausente → cubo `sin historia`, nunca `≥1`.
- `shuffled` usa exactamente los mismos episodios que `history`, solo otro orden.
- Presupuesto agotado, parada del operador y fallo tras ejecución: costes conservados, sesión parada.
- Replay de B desde recibos públicos; orden inverso de ejecución reproduce trazas.

## Custodia

Fijar fuentes B antes del banco de desarrollo; las 115 de RELATION-A intactas.
Informe con `relation1_green=false`: B no cierra la fase. Solo el recibo de
auditoría de D podrá acreditarlo.

## Qué no afirma

No conciencia, confianza sentida, amistad ni reciprocidad emergente: la regla
de la contraparte está diseñada y publicada. No transferencia a tareas no
probadas. No integración con MAINTAIN/CONTINUITY (eso es INTEGRATE).

Siguiente tras B: RELATION-C (ruptura, reencuentro, «VOLVÍ AL CUERPO DE K»:
misma identidad con otra conducta; historia incompleta o contradictoria) y D.
Después ROLES, INTEGRATE, RELEASE. Sin Discord, web, hardware, commit, push ni HF.
