# ECHO-4.5 · contrato del cierre R1–R4

2026-09-28. Implementación y contrato previos a la apertura del examen final.

La orden de implementar los pendientes abarca este cierre. Primero se termina
el piloto B4 y, si promociona, su campaña y auditoría. Después se fija un perfil
único de fuentes, estado aprendido, datasets y runtime. No se entrena ni se
selecciona configuración con los resultados finales. Los rojos se publican.

## R1 y R2

ARC-AGI-1: 400 tareas de evaluación. ARC-AGI-2: 120. Tres brazos:
SEMILLA S0 vacía; SIN S6, biblioteca `echo45-s2v`; CON S6, esa misma biblioteca
con las operaciones aceptadas de S6-A. S6-A aceptó cero: se comprueba contra su
auditoría congelada y los dos brazos entrenados son idénticos por construcción.
Se reutiliza su medida, identificándola explícitamente, sin fingir tres agentes
diferentes. La selección de la biblioteca usa solo desarrollo anterior.

Por tarea: 400 expansiones, profundidad 4, sin límite de tiempo, un programa
seleccionado con los ejemplos de entrenamiento. Antes de llamar al solver se
eliminan **todos** los outputs de test. El juez separado exige coincidencia
exacta en todos los tests; no elige programas mediante sus respuestas.
El evaluador no aprende ni modifica la biblioteca. R1/R2 pasan si el brazo
entrenado resuelve al menos una tarea y supera estrictamente a SEMILLA.

## R3

Los 16 juegos de `lab/arc3/split.json`, excluyendo LS20, 112 niveles. SEMILLA
es el actor v2; SIN S6 es v5.8. CON S6 usa los parches de ECHO B4 solamente
si B1–B5 de su examen pasan; en otro caso es v5.8 y se declara la identidad.
La regla se fija antes del resultado B4. Ninguna llamada a LLM en el examen.
Una pasada por juego, semilla histórica `seed_for(game, 0)`, 2000 decisiones,
sin plazo de reloj. Se conserva el registro completo, sin mini terminal en el
examen. El entorno tiene su semilla fijada a cero, como en desarrollo oficial.
R3 pasa con **≥23/112 niveles**; se publican niveles y ambas puntuaciones.
Los juegos ya tuvieron exámenes previos: no es una nueva cohorte ciega.

## R4

Proceso nuevo que reconstruye todas las soluciones y partidas de los brazos
distintos, compara el registro completo y verifica fuentes, estado, presupuestos,
cadena del diario, cada programa aprendido y procedencia de cada concepto.
Los conceptos deben figurar en el diario y tener al menos dos tareas de origen
de entrenamiento; sus programas se reproducen. La prior se contrasta con sus
programas de origen. No basta comprobar el hash de la biblioteca.

Se distinguen RESET inicial (fuera del presupuesto), reinicios elegidos por el
actor y automáticos tras GAME_OVER. Se registran desde las llamadas reales;
los automáticos también cuentan en la columna nueva por nivel. Se publica
la puntuación histórica y la fórmula congelada de competición
`min(humano/agente,1)^2`, ponderada por nivel, usando ese contador completo.
No se modifica el contador de los experimentos previos. No se afirma que el
scorecard local, que usa otra fórmula, sea la puntuación del gateway actual.
R4 verifica la contabilidad contra `Card.inc_reset_count` del SDK fijado y
una reconstrucción independiente. La validación contra el gateway remoto y
el envío final se mantienen como pasos de publicación con visto bueno del dueño.

## Custodia y cierre

Los tests del harness usan tareas de desarrollo o sintéticas. Preparar calcula
hashes sin inspeccionar ejemplos de evaluación ni código de juegos reservados.
Cada apertura deja recibo; se puede reanudar únicamente con el mismo perfil y
registros válidos. Un informe separado publica R1–R4 y el estado S6/memoria.
Cerrar la medición no convierte en verde una hipótesis que no pasó. No hay
envío ni publicación externa automáticos.
