# Siguiente paso tras la medición final y el piloto B4

2026-09-28. **Propuesta de trabajo**, no contrato congelado ni resultado verde.

## 1. Terminar R4, ya en ejecución

La recuperación del comparador JSON repite 1040 soluciones y 32 partidas
desde procesos nuevos. Se conservan agente, fuentes, métricas y criterios.
Aunque R4 pase, R2/R3 no pasan: ARC-2 0/120; ARC-3 11/112 frente a 13/112.
Se publicará el cierre tal como salga. R1 sí mejora: 31 frente a 20/400.

## 2. Diagnóstico de capacidad para S6, antes de otra campaña LLM

Se reconstruyó solo A y el diario del piloto, sin ejemplos de examen:

- FIJO local devuelve seis veces el mismo parche: `body_known==1`,
  `MIN_EVIDENCE=10`. Las seis verificaciones conservan 178 niveles A.
- ECHO local devuelve seis veces el mismo parche: `level>=3`, `HOLD=50`.
  Las seis verificaciones conservan 178 niveles A.
- ECHO global llega tres veces a 183 frente a 178 niveles A, pero el filtro
  detecta regresiones individuales; FIJO global llega a 179, por debajo de
  la ganancia mínima. Ninguna propuesta fue aceptada.

Esto demuestra repetición y ausencia de utilidad en las propuestas locales
observadas. No demuestra que todo el espacio sea incapaz de mejorar ni que
el modelo no pueda generar otras propuestas. La hipótesis a comprobar es si
los controles disponibles y las condiciones permiten expresar una reparación
útil, y si el modelo identifica el momento de aplicarla.

**Primer ensayo: control positivo manual, solo desarrollo y sin LLM.**
Congelar antes un conjunto pequeño de reparaciones legales, con presupuesto
de búsqueda declarado. Medir activación real, cambio de acciones, resultado,
replay y filtros V1–V4. Buscar al menos una reparación de +2 niveles A,
sin pérdidas individuales de niveles/puntuación A/B. Un control positivo
sirve para validar el instrumento; no cuenta como automejora de ECHO.

Si ningún control aporta una reparación útil, analizar si falta una operación
expresable y ensayar una ampliación del DSL sobre problemas sintéticos nuevos.
No concluir imposibilidad global con una búsqueda acotada. Toda operación
programada por humanos estará disponible por igual para los cuatro brazos.
Si el control sí funciona, contrastar repetición del modelo, evidencia del
prompt y elección de reparación, con igual presupuesto y varias semillas.

Solo después de un piloto con una mejora realmente propuesta y aceptada por
ECHO: contrato nuevo, campaña de cuatro brazos y cohorte reservada nueva.
Se mantienen B1–B5; no se convierte el control manual en resultado LLM ni
se elige una propuesta usando el examen. Cuota gratuita; no activar pago.

## 3. Transferencia de capacidad, en desarrollo

En rejillas, S2 ya observó que subir 400 a 1500 expansiones no aumentaba el
conjunto resuelto de desarrollo. Hay evidencia de un límite del vocabulario
bajo ese ensayo; no demuestra que más cómputo nunca sirva. La siguiente
hipótesis es componer operaciones sobre objetos y relaciones, aprendidas y
verificadas con los ejemplos, en vez de depender solo de transformaciones
globales de rejillas. Se prueba primero en entrenamiento y tareas sintéticas
reservadas nuevas, con presupuesto comparable y ablación del aprendizaje.

En juegos, comparar exploración general v2 y mecanismos v5.8 en mundos de
desarrollo con reglas variadas, comprobando qué habilidad se transfiere.
El menor número de niveles del examen final es un aviso de transferencia;
no se inspeccionan sus juegos para escribir reglas específicas que lo eleven.

## 4. Memoria y evaluación posterior

EGO-MEMORIA-2 demuestra varias capacidades bajo su condición, pero falla M5
en una semilla. Cualquier revisión usa otro contrato y cohorte; se conserva
el rojo y no se rebaja su umbral. No es el primer bloqueo del cierre ARC.

Un examen oficial ya medido se conserva como referencia y se declara cuando
se repite; no se presenta una repetición como una nueva cohorte ciega. Las
extensiones necesitan sus propios datos reservados y criterios previos.

Tiempo orientativo: R4, 60–90 min desde su recuperación; diagnóstico y
control positivo de S6, inicialmente media jornada de implementación/medición.
Una nueva campaña y examen pueden llevar varias horas y esperar cuota.
No hay fecha honesta de VERDE hasta que los criterios pasen.

[Evidencia A](../lab/seed/s6b4-20260928/training-followup.json) ·
[Contrato B4](ECHO45-S6-B4-DESIGN.md) ·
[Límite observado S2](ECHO45-S2-DESIGN.md) ·
[Auditoría actual](ECHO45-FINAL-AUDIT-RECOVERY.md).
