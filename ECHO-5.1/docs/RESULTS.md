# PCWORLD-1 · primera entrega de desarrollo · 2026-10-12

Se implementó y ejecutó el primer circuito de integración del plan recibido:
proponer, aplicar un parche, ejecutar en aislamiento, comprobar una propiedad
con una referencia externa al candidato, guardar evidencia y reparar a partir
de un contraejemplo. Se mantiene separado de la versión publicada de ECHO-5.

**Estado: prototipo de infraestructura probado; investigación ECHO-5.1 abierta.**
No hay resultado de superioridad multiagente, entrenamiento de Q, modelo nuevo,
confirmación reservada ni promoción. Las obligaciones parciales están en
[ACCEPTANCE.md](ACCEPTANCE.md).

## Evidencia ejecutada

| Comprobación | Resultado |
|---|---|
| Suite PCWorld completa de esta entrega | 138 tests; OK, 17,818 s |
| Regresiones seleccionadas de localdev, CodeMemory, CODE-1 y núcleo | 59 tests; OK, 7,195 s |
| Desarrollo congelado `development-20261012-r2` | 16/16 episodios aceptados; fuentes sin cambios; ningún error de episodio |
| Modelos externos durante el desarrollo | 0 llamadas, 0 tokens |
| Auditoría posterior | `valid: true`; valida custodia, bytes, snapshots, propiedades y replay WSP |

Las pruebas se ejecutaron con Python 3.14.6, Bubblewrap y systemd/cgroup v2 del
host. El comando reproducible y sus requisitos están en [RUNBOOK.md](RUNBOOK.md).
No se reabrieron S6 ni los exámenes sellados de ECHO-5.

Se conserva una salvedad del proyecto base: `TestGenLex.test_check_mode_reports_in_sync`
falla también en el checkout público **intacto** `f6062de` por la ausencia de
`legacy/kernel-navi/wsp_lex.c`, una dependencia del árbol RXos no distribuida
ahí. En el worktree con otro nombre también falla la ruta histórica hacia el
léxico Python. No se
cambió el núcleo para ocultar ese defecto. Los 59 tests indicados son una
selección explícita; no afirmamos que la suite histórica completa esté verde.

## Resultado por brazo y coste observado

Son cuatro propiedades públicas con soluciones **programadas**, no generadas
por un LLM: suma de positivos, enteros únicos ordenados, media racional y número
de distintos. Cada una se ejecutó en los cuatro brazos. Las entradas adicionales
son desarrollo conocido, no casos de confirmación nuevos.

| Brazo | Desarrollo aceptado | Herramientas | CPU de hijos (s) | CPU del supervisor (s) | Pared acumulada (s) |
|---|---:|---:|---:|---:|---:|
| S | 4/4 | 58 | 0,925370 | 0,938730 | 5,374 |
| I2 | 4/4 | 66 | 0,945642 | 1,061213 | 5,867 |
| F | 4/4 | 58 | 0,941414 | 0,943701 | 5,880 |
| E | 4/4 | 58 | 0,923462 | 0,950159 | 5,834 |

Totales por cuatro episodios, no por tarea. Hay variación de arranque, carga y
planificación del SO: las pequeñas diferencias de tiempo no prueban eficiencia
cognitiva. El éxito de las respuestas programadas sólo acredita el recorrido y
los comprobadores. En esta tanda F y E no muestran una diferencia útil de
selección; la divergencia de sus políticas se comprueba con estados de fallo en
tests, no con una mejora de calidad atribuible al basal.

El [resumen JSON](DEVELOPMENT-SUMMARY.json) conserva cada episodio, presupuesto,
error, identidad de candidato y hashes de evidencia. El
[manifiesto de fuentes](SOURCE-MANIFEST.json) fija los archivos ejecutados.
Los diarios completos y la autoridad privada están en
`ECHO-5.1/artifacts/development-20261012-r2/`, excluidos de Git.

## Qué se corrigió durante la verificación

La revisión del protocolo encontró y corrigió casos que podían sesgar o
falsear una conclusión:

- Restaurar el estado inicial de I2 ahora consume herramienta y fuel y genera
  recibo; no es una operación gratis.
- «Desconocido» se conserva distinto de «contradicho». El crítico debe indicar
  propiedad, dominio/precondiciones y referencia de oráculo compatibles.
- Se validan configuración del proveedor y snapshots archivados durante la
  auditoría, además del resumen autenticado y las fuentes.
- Se guardan los bytes originales de salida y su hash, incluso si no son UTF-8.
  Superar la cuota conserva el recibo y se carga todo el consumo observado.
- Un agente único tiene autorrevisión y puede producir una prueba adicional.
  El crítico no se consulta dos veces sobre la misma identidad de candidato.
- La aceptación final exige los casos públicos y los contraejemplos retenidos,
  además de los casos adicionales de desarrollo.
- El conector opcional cuenta el prompt antes de admitir la generación y
  limita la salida al saldo. El deadline restante abarca preflight y generación.
  Estos últimos casos se verificaron con un proveedor simulado, sin llamadas
  reales ni afirmaciones sobre un modelo desplegado.

La primera tanda `r1` se detuvo por cambios de fuentes durante una integración.
Se conserva como intento incompleto. Los resultados de la tabla proceden sólo
de `r2`, una ejecución posterior íntegra y auditada. Una revisión delegada de
seguridad no llegó a completarse; no se presenta como auditoría independiente.
Una revisión posterior de semántica experimental sí produjo los cinco hallazgos
sobre aceptación, tokens, autorrevisión, versiones y deadlines, cubiertos por
regresiones que primero reprodujeron los fallos.

## Respuestas a las preguntas del encargo

- **¿Funciona la frontera?** Pasaron los casos de aislamiento y recursos de esta
  suite; MCP y localdev utilizan el backend común. No constituye una prueba
  formal de seguridad ante cualquier programa o fallo del kernel.
- **¿Qué afirma un recibo?** El supervisor observó esos bytes, ejecución y
  recursos. Una propiedad necesita la referencia independiente. El resultado
  final sólo se aplica al contrato finito de desarrollo.
- **¿Hay ganancia E–S o E–F?** No estimada: las respuestas de esta tanda son
  fixtures. No se convierte su 16/16 en evidencia sobre capacidad de un LLM.
- **¿Contribuyen memoria y crítico?** Está probado el recorrido de conservar un
  contraejemplo y comprobarlo otra vez tras reparar. Falta medir su beneficio en
  tareas independientes y con ablaciones.
- **¿Cuánto cuesta?** La tabla y el JSON detallan consumo real de desarrollo.
  El dry-run de 60 tareas × 4 brazos × 2 repeticiones calcula un techo de 480
  episodios, 12 millones de tokens, 24.000 herramientas y 40 horas de CPU de
  hijos. Es un techo, no una previsión de gasto ni una campaña ejecutada.

## Pendiente antes del piloto científico

Runtime hermético o alcance de reproducibilidad explícitamente reducido;
modelo y tokenizer realmente identificados; ciclo con modelo real; corpus de
reparación/datos/archivos independientes; ablaciones y cálculo de muestra. La
caché persistente de ejecuciones está deshabilitada. El registro de conceptos
es un mecanismo unitario, sin aprendizaje o transferencia demostrados.

La implementación está en la rama local `research/echo-5.1-pcworld1` de un
worktree basado en `f6062de`. No se publica, fusiona ni promociona automáticamente,
conforme al apartado 13 del documento recibido.
