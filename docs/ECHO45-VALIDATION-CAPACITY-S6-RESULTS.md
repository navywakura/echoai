# Validación, capacidad ARC-1 y S6-B11

Actualizado: 2026-09-30T03:20:25.300230+00:00

- NEXUS-0: validación aprobada, 488 pruebas y un fallo esperado histórico.
- CAPACITY-500K: **VERDE**. Tres brazos en 250 tareas ARC-1 de training, con replay completo.
- S6-B11: **DETENIDO / PENDIENTE**. Sus cinco criterios conservan su contrato.

Estado conjunto: **PENDIENTE / NO VERDE**.

Aciertos de desarrollo: base 3/250, guide500k 6/250, guide640 5/250.

Incidencia del supervisor: Campaña c1 detenida: prompt ECHO excede 6000 tokens; respuestas parciales conservadas. Diagnóstico: docs/ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS.md

[Validación](ECHO45-NEXUS0-VALIDATION-20260930.md) · [Comparación](ECHO45-CAPACITY500K-ARC1-RESULTS.md) · [S6](ECHO45-S6-B11-RESULTS.md).

El supervisor usa un servicio de usuario y un aviso local de escritorio. Sigue mientras el equipo permanezca encendido; no envía mensajes a terceros.
