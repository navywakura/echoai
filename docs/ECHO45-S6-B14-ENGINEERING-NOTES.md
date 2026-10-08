# S6-B14 — correcciones implementadas y preparación

**Cierre posterior, 4 de octubre, 14:07:14 Madrid:** auditoría válida de las
5080 partidas independientes y 54 veredictos. B14 termina sin promoción:
ECHO 1134, FIJO 1134. Campaña y examen sin abrir. La investigación posterior
identifica fallos en la correspondencia foco/operador, el crédito del selector
y el resumen de oportunidades. [Informe reproducible](ECHO45-S6-B14-FORENSICS.md).
El registro de preparación y sus previsiones iniciales se conserva a continuación.

Actualización del 4 de octubre de 2026, 08:54 de Madrid. La auditoría B13-R1
terminó a las 08:32:03: válida, con 54 veredictos reconstruidos y 7720 partidas
en su caché independiente. Confirma ECHO 1113 frente a FIJO 1125 y cierra
`PILOT_NO_PROMOTION`, con el examen sin abrir. Las 159 fuentes B13 y las 166
fuentes B14 mantienen sus hashes. No se modificó el piloto negativo ni se
rebajaron V3/V4 o B1–B5.

B14 salió automáticamente de la espera después de ese cierre. La paridad
de SEMILLA quedó válida a las 08:38:20, con 365 niveles y observador sin efecto
en el comportamiento. El piloto está en marcha: el primer par completo
terminó con ECHO 378 y FIJO 378, ambos con una mejora aceptada de +13.
Es un resultado parcial de desarrollo, sin ventaja entre brazos ni auditoría
B14 todavía. La campaña y el examen siguen condicionados a superar las puertas.

`echo_arc/repair_memory.py` conserva recibos observados, selecciona casos con
señal, contabiliza todos los intentos, asigna los refinamientos a su mecanismo
de origen y prueba mecanismos disponibles antes de volver a explotar uno.
Los objetivos caducados no se regeneran como descendientes. La rotación queda
dentro de los casos pertinentes al foco. El modelo recibe siempre el último
resultado; durante refinamiento también recibe el objetivo y su último intento.
La política completa usa una codificación reversible que ahorra contexto.

La memoria de diversidad tiene dos mecanismos separados. El primero puede
excluir un fallo V3 cuando sus controles son idénticos en todas las decisiones
de las trayectorias completas A del candidato anterior. Nunca usa una mera firma
de las oportunidades de la base. El segundo introduce una pausa de una llamada
para un control/valor que acaba de producir un fallo repetido. Esta pausa es una
heurística de exploración: no demuestra que cualquier otra guarda vaya a fallar.
Se aplica también a FIJO y RANDOM, conservando presupuestos iguales.

La evaluación local del instrumento pasó **25 pruebas**. Incluye pérdida de
feedback y rechazo V4, codificación reversible, selección sin casos irrelevantes,
exploración garantizada, contabilidad de rechazos, caducidad, equivalencia sobre
traza completa, manipulación de certificados, pausa temporal y reconstrucción
de solicitudes/recibos en una fase de prueba. El paso piloto terminado →
subproceso de auditoría → cierre negativo también se ejercitó y dispone de
`subprocess.STDOUT`. Los dobles usados en estas pruebas no cuentan como juegos
de ECHO ni resultados del experimento.

Se reprodujeron los formatos de **36 historiales reales** y se forzaron los
**seis contextos de refinamiento** de B13 para comprobar el fallo anterior,
aunque el selector nuevo pudiera elegir otro foco. Todos conservan el recibo
obligatorio. Una política de **32 reglas** también cabe. El mayor tamaño
seleccionado fue **3026 tokens**, por debajo de 3072; se usó el tokenizador real
del GGUF sin generar respuestas. El recibo está en
`lab/seed/s6b14-20261004/validation.json`, con hashes de fuentes y log de tests.
La preparación no jugó ninguna partida ni hizo llamadas de generación.

Se conservaron los resultados negativos de la comprobación de duplicados:
ninguno de los cinco pares históricos comparados tiene controles idénticos
durante toda su trayectoria, por lo que el filtro conservador no los elimina.
Al reconstruir las historias, la pausa temporal sí habría impedido el ajuste
repetido en tres propuestas antiguas. Esto acredita la actuación del control;
no predice qué alternativa emitirá ahora el modelo ni qué puntuación obtendrá.

Durante las pruebas, un fixture del recibo V4 reutilizaba el mismo digest
ficticio que todos sus antecedentes y activó correctamente la nueva pausa.
Se cambió ese fixture a un resultado nuevo para comprobar el caso de refinamiento
no repetido; la pausa dispone de pruebas específicas. Se conservó el log del
fallo inicial en `lab/s6b14-tests-before-fixture-fix.log` y la calificación
anterior a la pausa en `qualification.before-diversity`. La calificación final
se volvió a ejecutar después de las correcciones.

El perfil B14 congela **166 fuentes/datos**, SHA-256
`556c69c032b262ee3012b7ff1eb2780314811968b323eb5baf395152ba385b7a`.
El servicio `echoai-s6b14` arrancó a las **05:48:41**. Permaneció en
`WAITING_B13_AUDIT`, con `games_started:false`, hasta las 08:32. La espera
no creó workers de juego ni llamadas al modelo. El recibo
`previous-audit-gate.json` enlaza los hashes de auditoría, cierre y perfil B13
que permitieron iniciar B14. Se comprobaron de nuevo en esta revisión.

La condición arrancó con SEMILLA vacía, el mismo modelo local y nuevos juegos
protegidos/reservados. El proceso encadenará
piloto, auditoría, campaña, auditoría y examen solo si cumple las puertas.
No se copian las soluciones encontradas por FIJO ni por sondeos dirigidos.
La ejecución sigue siendo privada y requiere el portátil despierto.

A las 05:50, la auditoría B13 llevaba **2197/7720 partidas (28,5 %)**. Terminó
dentro de la previsión de 08:00–09:00, tras 3 h 48 min. La condición anterior
conserva su resultado negativo.

La orientación inicial para B14 es terminar el piloto hacia las **13:00–15:00**
y su auditoría hacia las **17:00–20:00** del 4 de octubre. Son ventanas de
planificación basadas en las aproximadamente 4 h 16 min del piloto anterior
y 3 h 48 min de su auditoría, con margen por propuestas, caché y carga distintos.
No son una extrapolación fiable de las pocas llamadas B14 ya medidas ni una
fecha de cierre S6. Campaña y examen solo podrán ejecutarse después de una
promoción válida. La ejecución no requiere otra confirmación del propietario.

[Contrato congelado](ECHO45-S6-B14-DESIGN.md) ·
[Resultado automático](ECHO45-S6-B14-RESULTS.md) ·
[Estado](../lab/seed/s6b14-20261004/status.json).
