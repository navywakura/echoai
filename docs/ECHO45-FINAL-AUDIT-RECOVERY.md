# R4 · recuperación del comparador de registros JSON

2026-09-28, después de una auditoría interrumpida. No es una campaña nueva
ni un cambio retroactivo de criterios, agente, presupuesto o resultados.

El examen comenzó a las 02:04 Madrid. La medición terminó a las 03:07;
la auditoría original terminó con error a las 04:07, antes del cierre R4.
R1: 31/400 frente a 20/400; R2: 0/120 en ambos actores; R3: 11/112 frente
a 13/112 de SEMILLA. Resultados medidos; todavía sin certificación final R4.

La comparación `record == json.loads(receipt)` falla en el campo `model`
de v5.8, que contiene tuplas anidadas en las hipótesis. JSON las conserva
como arrays/listas. En AR25 se reprodujeron exactamente todas las acciones,
fotogramas y niveles; el hash JSON canónico del registro completo también
coincidió. El diagnóstico se conserva en `audit-recovery/diagnostic.json`.

El código original, sus 46 fuentes, datasets, perfiles, registros y salida
de error se mantienen intactos. Un auditor separado, con su propio perfil
y archivo de fuentes, compara **todos los campos** en representación JSON
canónica. No omite `model`, redondea números ni excluye acciones, fotogramas,
puntajes o hipótesis. Distingue booleanos y enteros; cualquier cambio de
contenido fracasa. Es una reparación del comparador del formato de archivo.

Antes de repetir la auditoría se fijan los hashes de los 1040 registros de
rejillas, 32 partidas y resúmenes medidos. Desde procesos nuevos se repiten
los dos actores distintos en las 520 tareas y 16 juegos, se reconstruyen
programas, conceptos y cadenas, y se comprueban contadores contra el SDK.
Los alias CON/SIN S6 se conservan. Rejillas y ARC3 pueden auditarse en
paralelo porque son estados y procesos independientes; los presupuestos
deterministas no dependen del reloj. Se mantienen todos los criterios.

La salida de error original queda como registro histórico; el estado de
esta recuperación está en `lab/final/echo45-20260928/audit-recovery/`.
Solamente al completar ambas auditorías se escribe `audit.json` y el
informe final, indicando explícitamente esta extensión y su huella.
