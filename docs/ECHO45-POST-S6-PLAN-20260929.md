# ECHO-4.5 después de S6 · orden de trabajo

Orden de Roger del 29 de septiembre: prioridad inmediata cerrar S6; después
continuar los módulos pendientes y medir transferencia en ARC-AGI-1/2/3.
Actualizado el 29 de septiembre: comparador y diagnóstico de capacidades
preparados mientras continúa S6. No se ha abierto su examen final ni iniciado
una nueva medición ARC. [Implementación y evidencia](ECHO45-ARC-PREPARATION-RESULTS.md).

1. **S6-B11 en curso:** usa contrastes de acciones/resultados y selección
   adaptativa, con desarrollo ampliado y validación nueva. En las dos primeras
   rondas completas, ECHO tiene una propuesta aceptada: A 365→373 y B 168→171,
   sin regresiones medidas; FIJO tiene cero aceptaciones. Es evidencia
   provisional: faltan las demás rondas, repetibilidad y auditoría independiente.
   B10 quedó cerrado y auditado sin promoción; sus propuestas perdían puntuación
   individual en B. Se conservan sus resultados y los anteriores.
   Campaña y examen de cuatro brazos solo tras las promociones. VERDE solo con
   B1–B5. [Contrato B11](ECHO45-S6-B11-DESIGN.md) ·
   [Diagnóstico histórico](ECHO45-S6-DIAGNOSIS-20260929.md).
   B8 y sus continuaciones numéricas conservan sus resultados y límites por
   separado; B8-CPUQ8 cerró auditado sin promoción (534–534, cero aceptaciones).
2. **Medir la transferencia del candidato congelado.** Comparación primaria
   con la configuración evaluada el 28 de septiembre: ARC-1 31/400, ARC-2
   0/120, ARC-3 11/112. SEMILLA histórica es otra referencia, no se confunde
   con la versión inmediatamente anterior. Mismo presupuesto, datos y métrica.
   Los conjuntos ya evaluados se etiquetan como seguimiento conocido; no
   vuelven a ser un examen ciego. La confirmación necesita reserva nueva u
   oficial privada, según disponibilidad y reglas de acceso.
   El comparador ya reconstruye esas referencias, comprueba datos y fuentes,
   calcula ganancias/pérdidas emparejadas y bloquea políticas del piloto.
   S6-B11 no cambia las rejillas: ARC-1/2 serán alias explícitos hasta registrar
   un solver distinto. [Contrato de comparación](ECHO45-ARC-COMPARISON-DESIGN.md).
3. **Desarrollo para los fallos restantes:** relaciones entre objetos,
   composición de programas y selección/refinamiento de hipótesis. Parte del
   código ya existe; su ventaja adicional no está demostrada. Cada ampliación
   tendrá contrato, tareas de entrenamiento/desarrollo, ablación, congelación
   y examen aparte. No se incorporan automáticamente todos los módulos ECHO-5
   al alcance de ECHO-4.5.
   Diagnóstico sintético de doce tareas preparado y ejecutado con ablaciones
   de relaciones y composición. Sus resultados se separan de ARC oficial.
4. **Integrar y publicar:** validar el borrador Kaggle/gateway, comparar costes
   y conservación de habilidades, documentar fallos y efectuar los envíos
   autorizados. Memoria 3E verde en aldea no demuestra transferencia a ARC.

## Qué entrenamiento y qué informe

Para S6 se aprende mediante propuestas y consecuencias de A; B actúa como
verificador protegido. No se entrena con salidas reservadas. Para el solver de
rejillas se adquieren operaciones/conceptos solo de tareas de entrenamiento;
el refinamiento prueba hipótesis contra las demostraciones permitidas. Buscar
programas no se denomina actualización de pesos ni test-time training.

El informe comparará aciertos exactos en ARC-1/2; niveles, score y acciones
en ARC-3. Publicará diferencia absoluta y porcentual con denominador explícito.
Con base cero, la mejora porcentual relativa no está definida: se informa
el incremento de tareas/puntos porcentuales. Por ejemplo, 0→n no es un
porcentaje relativo infinito ni 100% de capacidad.

Capacidades candidatas: objetos/relaciones, composición, orden, conteo,
planificación, memoria y petición/verificación de ayuda. Solo se atribuirá
mejora a un módulo si un examen específico o una ablación a presupuesto común
lo sostiene. Un aumento del total ARC no identifica por sí solo su causa.

Estado actual: comparador, bloqueo del candidato, métricas y diagnóstico de
capacidades implementados; candidato S6 final y medición de transferencia
pendientes. El [protocolo de memoria→ARC](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md)
documenta el adaptador y las ablaciones aún necesarios. No hay promesa de mejora
ni fecha de cierre científico antes de medir.
