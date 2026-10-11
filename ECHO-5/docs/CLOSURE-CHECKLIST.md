# ECHO-5: checklist de cierre

Nota de publicación: la tabla conserva el corte histórico indicado abajo.
El [checkpoint del proyecto](../../docs/PROJECT-CHECKPOINT-20261011.md) es la
referencia vigente; ECHO-5 sigue abierto y la calibración no está limpia.

<!-- ACTIVE-CLOSURE-STATUS -->
Estado automático (2026-10-11T04:38:10+02:00): **Cadena detenida; ECHO-5 continúa pendiente de cierre.**
Detalle y rutas: [estado de ejecución](CLOSURE-RUN-STATUS.md).
<!-- END-ACTIVE-CLOSURE-STATUS -->

Actualización de estado, 11 de octubre de 2026, 04:08 (Madrid). La tabla cita los
recibos auditados de r1 y distingue la corrección r4 en ejecución; la implementación por sí
sola no cambia el estado científico. S6 queda fuera hasta después de 5.5.

| Entrega | Programación | Validación requerida | Estado medido |
|---|---|---|---|
| Objetos, relaciones y familias nuevas | Programado | Transferencia y controles ambiguos o fuera del lenguaje | Confirmación r1 auditada: 48/48 compatibles y abstención 24/24 (12 ambiguous_rotation y 12 unsupported_color); alcance sintético reservado |
| Conceptos adquiridos | Programado | Biblioteca vacía/fija/control del mismo tamaño, adquisición incluida | Confirmación r1 válida: 16,91 % menos trabajo que biblioteca vacía; 3,24 % más que fija, dentro del margen prerregistrado; no superioridad sobre biblioteca fija |
| Composición profunda y caché | Programado | Nuevas profundidades, acierto y coste real | Confirmación r1 auditada: 57,79 % menos trabajo en prefijos reutilizados, sin cambiar respuestas |
| MiniGrid/BabyAI e interacción | Programado | Observación parcial, controles, replay y evaluación externa | Confirmación r1 auditada: 54/56; fijo 0/56, pasivo 0/56, sin memoria 20/56, sin planificación 6/56 |
| Contraejemplos adaptativos | Programado | 32 ejecuciones emparejadas, información igualada, incertidumbre y coste | Confirmación r1 auditada: 256/256 frente a 201/256 aleatorio y 152/256 secuencial; puertas científicas cumplidas |
| MissionAgent completo | Programado, razonador nuevo conectado por defecto | Cadena software, regresiones y gates | Confirmación software r1 válida: 4/12 frente a 3/12 convencional; empate con horizonte 1; simulador físico pendiente |
| Gazebo/PX4 nuevo | Programado; corrección de estimación y recuperación en prueba | ULog, poses, ACK, supervisor y auditoría; no hardware | Confirmación r1 fallida: 17/18 recibos válidos, ECHO 2/3 nominales frente a 3/3 convencional. Nueva calibración de seis vuelos en ejecución; cierre pendiente |
| Panel local de decisiones | Programado | Navegador, controles, diario y límites de acceso | Validado en navegador de escritorio y móvil; misión nativa resuelta en 20 acciones |
| Diagnóstico LIF real | Programado | Frames iguales al módulo histórico; sin efecto en política | Tests y navegador válidos; diagnóstico de 256 neuronas, no controlador del episodio |
| Custodia y runner en segundo plano | Programado | Tests, integridad, auditoría en proceso nuevo | Checks r4 válidos: 335 tests de núcleo (12 opcionales omitidos) y 32 de sandbox. Calibración y continuación con fuentes congeladas |

La autopsia de los dos fallos y la intervención están en
[el diagnóstico de confirmación](SITL-CONFIRMATION-R1-DIAGNOSIS.md).
Los resultados cognitivos anteriores conservan su identidad de fuentes.
La nueva cadena repetirá esas suites como regresión; sólo la confirmación
física usa semillas nuevas (971809–971814). S6 continúa fuera de alcance.
Los párrafos históricos siguientes conservan la secuencia de incidencias;
el estado vigente se consulta en el checkpoint del proyecto enlazado arriba.

Los resultados nuevos vivirán en `artifacts/closure-*`. Cada ejecución conserva
las versiones previas y sus resultados. El panel lee `artifacts/closure-latest.json`.
Los costes son operaciones lógicas y tiempos medidos; no se declaran julios.
Una auditoría válida puede confirmar un resultado negativo.

Recibo de software actual: `artifacts/closure-checks-20261011-r3/result.json`.
Navegador actual: `artifacts/browser-20261011-preflight-r3/result.json`.
Los últimos recibos de navegador y desarrollo CPU, anteriores al adaptador de
parámetros IMU, son `artifacts/browser-20261010-r6/result.json` y
`artifacts/closure-development-20261010-r5/audit.json`. Las pruebas base nuevas
ejecutaron 314 casos con 12 omitidos por requerir el entorno opcional; las
32 pruebas del entorno MiniGrid/BabyAI pasaron, cubriendo también esos 12.
No se suman ambos recuentos como si fueran pruebas distintas.
Las capturas actuales están en `artifacts/browser-20261011-preflight-r3/`.
El panel está en <http://127.0.0.1:8765> y <http://echoai.localhost:8765>.

La revisión de captura física pasó 292 tests de núcleo (12 requieren el entorno
opcional) y 32 de sandbox en
`artifacts/closure-checks-20261010-preflight-r5/result.json`. La calibración r2
se auditó con `valid: true`, pero `scientific_success: false`: validez del
registro y éxito de misión son condiciones distintas. El cambio posterior de
observación activa y el refuerzo del finalizador tienen las pruebas r5 citadas
arriba. El piloto nuevo de `artifacts/mission-active-development-20261010-r1/`
se midió y auditó con éxito: 22 acciones del razonador ejecutadas y 30 recibos
de consecuencias entregados al actor. Ese piloto no necesitó inspecciones
adicionales; su éxito no demuestra por sí solo una ventaja de ese mecanismo.
La batería completa terminó en `artifacts/sitl-development-20261010-r3/`.
Su auditoría independiente reprodujo el resultado negativo sin discrepancias
(`findings: []`, `valid: false`). El coordinador r1 se detuvo antes de abrir
confirmación. Su historial está en
`artifacts/closure-pipeline-20261010-r1/status.json`.

El bloqueo de altura de r3 está documentado en
[su diagnóstico](SITL-DEVELOPMENT-R3-DIAGNOSIS.md). El caso fallido no produjo
decisiones del agente y no acredita superioridad de ECHO. La calibración GNSS
de `artifacts/sitl-height-calibration-20261010-r1/` pasó en un episodio;
la repetición completa r5 mostró que esa corrección era insuficiente.
Una calibración favorable no sustituye a una batería completa. La revisión científica
independiente de transferencia y currículo no encontró bloqueos en su alcance:
`artifacts/scientific-review-20261010-r1/REVIEW.md` conserva sus límites.

La calibración pasó a las 23:28. El desarrollo CPU r5 y navegador r6 también
pasaron. La batería SITL r4 sufrió después un agotamiento global de memoria
provocado por un proceso ajeno: [diagnóstico y recuperación](SITL-HOST-OOM-20261010.md).
Su auditoría conserva el fallo y los 16 episodios no ejecutados. El coordinador
`artifacts/closure-pipeline-20261010-r3/status.json` se detuvo después del fallo
de altura de r5; no hubo otro OOM. El [diagnóstico IMU](SITL-IMU-DIAGNOSIS-20261011.md)
explica la evidencia y el nuevo experimento separado. Su prerregistro está en
`artifacts/imu-calibration-20261011-r1/plan.json`; necesita tres ejecuciones y
auditoría antes de habilitar `artifacts/closure-pipeline-20261011-r1/`.
La confirmación permanece cerrada.

La revisión acotada del adaptador terminó sin bloqueos pendientes en
`artifacts/imu-parameter-review-20261011-r1/FINAL.md`, después de corregir
vinculación al binario, truncados y cierre del contenedor de extracción.
Las regresiones con el parser real están en
`artifacts/imu-extractor-regressions-20261011-r1/`. La ejecución CPU nueva terminó con auditoría válida;
sus cuatro procesos están registrados en
`artifacts/closure-pipeline-20261011-r1/cpu-prerequisite-status.json`.
La calibración de tres vuelos pasó con auditoría independiente hacia las 01:05; el coordinador
es `artifacts/imu-calibration-20261011-r1/coordinator-status.json`.
La batería SITL completa nueva ya está en ejecución. Su auditoría debe pasar
antes de abrir la confirmación reservada y el veredicto final. Los procesos mantienen las
fuentes congeladas y los fallos impiden abrir la siguiente fase.

Antes de abrir confirmación se registró una ampliación de desarrollo en
`artifacts/development-scale-20261010-r1/plan.json`: 72 tareas de transferencia
con semillas de desarrollo nuevas y 32 ejecuciones emparejadas de currículo.
Comprueba si se amortiza la adquisición y si la ventaja temprana se repite.
No cambia gramática, algoritmos, presupuestos por caso ni umbrales; no permite
promoción y conserva todos los resultados. La confirmación permanece reservada.
