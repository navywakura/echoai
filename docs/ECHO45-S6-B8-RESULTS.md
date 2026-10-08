# S6-B8 · implementación y resultado parcial auditado

**PENDIENTE por infraestructura y cuota. S6 no está VERDE.**
No es un piloto cerrado negativo: faltan las seis propuestas de la tercera ronda.

## Qué se implementó y comprobó

Diagnósticos de aplicabilidad sobre estados realmente observados; selección
por oportunidades de intervenir; secuencias estado→acción→resultado; feedback
adaptativo; piloto de tres rondas; campaña condicional, SIN FILTRO acumulativo,
examen nuevo y auditor independiente. Diez pruebas B8 pasan, incluida paridad
de acciones con/sin observador; cuatro pruebas de recuperación también pasan.
La base vuelve a dar 178 niveles en A y conserva su conducta anterior.

## Dos rondas completas, doce propuestas

| Brazo | Propuestas verificadas | Aceptadas | Suma A de tres parejas tras ronda 1 |
|---|---:|---:|---:|
| FIJO | 6 | 0 | 534 |
| ECHO | 6 | 0 | 534 |

Cada pareja evalúa 40 partidas A, 200 niveles posibles. La suma de tres
parejas no representa tareas independientes adicionales ni puntuación ARC
oficial. B8 parte de SEMILLA; no borra la mejora aceptada de B7.

Las seis propuestas de la segunda ronda repiten exactamente las de la
primera, aunque recibieron prompts, feedback y semillas de muestreo nuevos.
Los doce veredictos son V3: cero ganancia de niveles. El diagnóstico distingue
valores nativos/inactivos de cambios de parámetro que tampoco mejoran conducta.
El paquete selector+feedback todavía no acredita ventaja sobre FIJO.

El análisis posterior encontró el caso preciso: `motor_ready=1 → HOLD=100`
coincide con cero de las 85 asignaciones reales de espera del actor nativo A.
Se preparó otro diagnóstico, con cuatro pruebas adicionales que pasan, para
distinguir consumo observado de configuración potencial. No altera B8 ni
su puntuación. [Diagnóstico y límites](ECHO45-S6-CONSUMPTION-DIAGNOSIS-20260929.md).

[Auditoría parcial](../lab/seed/s6b8-20260929/partial-audit.json): reconstruye
los doce veredictos, peticiones, respuestas, usos del modelo y políticas desde
caché independiente. Declara `complete_pilot=false`, seis propuestas pendientes
y `exam_opened=false`. La procedencia de ambas inferencias pasa; B8 mantiene
intactas sus 87 fuentes congeladas y V1–V4/B1–B5 originales.

## Fallos de infraestructura conservados

El trabajo p2, con máximo configurado de 300 segundos, terminó ERROR durante
la descarga de pesos, sin respuestas. Una recuperación explícita de hasta
600 segundos, con el mismo wrapper byte por byte, terminó
CANCEL_ACKNOWLEDGED; el último registro seguía en 0/4 archivos y sus seis listas
de respuestas estaban vacías. No se interpretan como respuestas incorrectas.

La recuperación tuvo además un error local de enlace antes del envío,
corregido con perfil previo archivado y prueba específica. No alteró prompts,
modelo, datos, criterios ni fuentes B8. Los fallos de red del sandbox también
se conservaron; no enviaron trabajos. [Adenda](ECHO45-S6-B8-INFERENCE-RECOVERY.md).

Cuota gratuita tras estos trabajos: **13,394 segundos**; renovación indicada
por Kaggle: **3 de octubre de 2026**. Pago desactivado. El runtime local
consultado no tiene Qwen fijado en caché ni CUDA disponible; no se sustituyó
silenciosamente por otro modelo o una cuantización.

## Qué queda y cómo se evita repetir el gasto

La caché privada de pesos terminó en **CPU, sin inferencia ni GPU**,
con la revisión exacta, descarga HTTP con Xet desactivado y verificación SHA256
de los cuatro shards: 15242805878 bytes. Manifiesto completo y hashes válidos.
[Preparación](../lab/kaggle/s6-model-cache-20260929/README.md).

Se ha registrado **S6-B8-CPU**, una continuación separada que hereda las doce
propuestas y ejecuta las seis restantes en CPU float16 con esos mismos pesos,
prompts y semillas. Pasa seis comprobaciones locales y fue enviada a Kaggle
a las 00:46 UTC del 29 de septiembre, sin acelerador ni pago. El cambio de
backend no garantiza las mismas muestras que CUDA y queda explícito en el
contrato; B8 original conserva su estado parcial. Ambos intentos fallidos se
conservan. Solo una promoción completa y auditada permite campaña y examen
de cuatro brazos. [Contrato CPU](ECHO45-S6-B8-CPU-DESIGN.md) ·
[Resultado CPU](ECHO45-S6-B8-CPU-RESULTS.md).

La reserva 24500–24559 permanece sin abrir. EGO-MEMORIA-3E sigue VERDE en
su dominio. Las puntuaciones ARC publicadas no cambian.

## Actualización: continuación Q8 completa, sin promoción

La condición separada **S6-B8-CPUQ8** terminó a las 01:52 UTC. Completó las
seis propuestas pendientes con cuantización dinámica int8 y reconstruyó los
18 veredictos del piloto en una auditoría independiente. Total A: ECHO 534,
FIJO 534, cero aceptaciones. Todas las propuestas nuevas cambiaron cero
acciones y ganaron cero niveles. Piloto **sin promoción**, reserva cerrada.
No se atribuyen estos resultados a una ejecución íntegramente GPU/float16.
[Resultado Q8](ECHO45-S6-B8-CPUQ8-RESULTS.md).

CPU float16 terminó `CANCEL_ACKNOWLEDGED` tras el límite de su trabajo, con
dos respuestas de seis y ninguna evaluación del piloto completo. Se conservan
como parciales; no se sustituyen por respuestas Q8 ni se mezclan sus resultados.
La línea activa siguiente es [S6-B9](ECHO45-S6-B9-DESIGN.md), desde SEMILLA,
con un operador nuevo respaldado por control humano independiente.

[Contrato B8](ECHO45-S6-B8-DESIGN.md) ·
[Continuación de ECHO-4.5 tras S6](ECHO45-POST-S6-PLAN-20260929.md) ·
[Estado](../lab/seed/s6b8-20260929/status.json).
