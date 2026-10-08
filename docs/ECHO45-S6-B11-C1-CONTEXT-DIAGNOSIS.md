# S6-B11 · interrupción de contexto en c1

Revisión del 30 de septiembre de 2026. Estado: **DETENIDO / NO VERDE**.

El piloto terminó con ECHO 1129 frente a FIJO 1108, tres mejoras ECHO
aceptadas y promoción positiva. Su auditoría independiente reconstruyó los
36 veredictos y resultó válida. La campaña comenzó desde programas vacíos,
como exige el contrato: c0 terminó con una aceptación en cada brazo.

El trabajo CPU privado c1 terminó con ERROR a las 02:42 UTC (04:42 CEST).
Su log contiene `AssertionError: refusing prompt truncation` en la función
de generación, antes de la primera respuesta ECHO. El programa exacto,
descomprimido del wrapper de transporte sin ejecutarlo, comprueba que la
entrada tokenizada tenga como máximo 6000 tokens. La petición ECHO de c1
tiene 19972 caracteres; la FIJO, 6358. Los caracteres no son tokens: el log
no conserva la longitud tokenizada exacta, pero la aserción identifica el
límite excedido. No hay evidencia aquí de que haya fallado el solver ni el
examen reservado.

Las cinco respuestas FIJO de c1 quedaron guardadas; ECHO tiene cero. El
artefacto declara `complete: false`, por lo que no permite construir un
veredicto de ronda ni comparar ambos brazos. El supervisor preservó el
trabajo y salió con código 1 a las 02:42:32 UTC; no reenvió la inferencia.
Los servicios de campaña y seguimiento ya no están activos. El informe
conjunto mostraba «EN EJECUCIÓN» por ausencia de cierre; ahora distingue un
supervisor detenido de una evaluación en marcha.

Falta completar cinco rondas de campaña, aprobar su promoción y auditoría,
congelar los cuatro brazos y ejecutar el examen reservado, conservación y
auditoría B1–B5. No existe una estimación de finalización mientras esté detenido.

La corrección que debe evaluarse es limitar de forma determinista el tamaño
del feedback de desarrollo al construir las peticiones, conservando la
misma información permitida y el mismo presupuesto para ambos brazos.
Hay que comprobar el tamaño con el tokenizer antes de enviar el trabajo.
Cambiar las peticiones altera una condición congelada: requiere una nueva
condición y contrato previo, sin reutilizar respuestas parciales para elegir
la reparación ni abrir el examen de B11. Otra política de contexto también
necesitaría declararse y comprobar sus recursos antes de la inferencia.
Esta revisión solo documenta el fallo; no cambia B11 ni lanza otro experimento.

Evidencia local: [auditoría del piloto](../lab/seed/s6b11-20260929/pilot-audit.json),
[ronda c0](../lab/seed/s6b11-20260929/campaign/round-0.json),
[estado](../lab/seed/s6b11-20260929/status.json),
[respuestas parciales c1](../lab/kaggle/s6b11-20260929/c1/answers.json),
[log remoto c1](../lab/kaggle/s6b11-20260929/c1/output/echo45-s6b11-c1-20260929.log),
[contrato original](ECHO45-S6-B11-DESIGN.md).
