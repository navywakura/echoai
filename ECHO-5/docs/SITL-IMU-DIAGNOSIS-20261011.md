# Deriva durante la espera de batería: desarrollo r5

La repetición con referencia GNSS se interrumpió al cerrar el octavo episodio,
sin procesos de vuelo activos. La auditoría conserva 18 episodios programados,
8 ejecutados, 7 válidos y seguros, uno inválido y diez sin ejecutar. El episodio
inválido es `0002-echo32`; falló antes de recibir una decisión de ECHO.
El contador de OOM del host no aumentó durante esta repetición. Los registros
están en `artifacts/sitl-development-20261010-r5/` y la interrupción en
`artifacts/height-stability-investigation-20261011-r1/interruption.json`.

En la entrega de control, a los 348 segundos simulados, la altura de misión
estimada era aproximadamente 2,832 m y la velocidad 0,410 m/s. El ejecutor
exige 2,5 m ±0,3 m y velocidad inferior a 0,2 m/s para la observación inicial.
Al agotar veinte segundos seguían fuera de tolerancia. La altura física de
Gazebo también crecía: aproximadamente 4,28 m a los 348 s y 4,60 m a los 365 s.
GPS y barómetro registraban el ascenso. Esta vez el origen vertical era sólo
0,029 m: corregir el datum inicial no explica por sí solo este fallo.

ULog registra fusión de GPS, altura GPS y barómetro, sin fusión de visión
externa ni rechazo de las mediciones verticales. A los 350 s, la mediana de
aceleración z era −9,581 m/s² y el sesgo z estimado +0,117 m/s², aún marcado
inestable. La estimación vertical se separaba de la velocidad GPS y de la
derivada de posición. Estos indicios respaldan investigar el seguimiento del
sesgo inercial. No prueban que éste sea la única causa.

El modelo IMU heredado usa `dynamic_bias_stddev=0.006` y correlación de 300 s.
Gazebo implementa un proceso de primer orden con varianza de innovación
`sigma²*tau/2*(1-exp(-2*dt/tau))`, aproximadamente `sigma²*dt` para pasos
pequeños. PX4 1.15.4 incrementa la covarianza del sesgo mediante
`(dt*EKF2_ACC_B_NOISE)²`; su valor por defecto es 0,003. La diferencia de
discretización impide trasladar el mismo número directamente entre ambos
parámetros. Este cálculo motiva una hipótesis sobre calibración; no sustituye
al resultado de vuelo. Fuentes primarias:
[ruido de Gazebo](https://raw.githubusercontent.com/gazebosim/gz-sensors/gz-sensors8/src/GaussianNoiseModel.cc),
[covarianza de PX4 1.15.4](https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.15.4/src/modules/ekf2/EKF/covariance.cpp)
y [rango documentado de PX4 1.15](https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_ACC_B_NOISE).

Se prerregistró una intervención en
`artifacts/imu-calibration-20261011-r1/plan.json`: `EKF2_ACC_B_NOISE=0.01`,
máximo del rango documentado. Se conservan ruido sensorial, generación de
mundos, tiempos, resto de parámetros, lógica de los actores y tolerancias.
Se repite el caso de poca energía en los tres modos, con tres procesos nuevos
y auditoría independiente. Son tres ejecuciones del mismo caso de desarrollo,
no tres semillas independientes. Deben pasar las tres; no se selecciona la
mejor. Un pase habilita una batería de desarrollo completa nueva.

El adaptador `sitl_parameters.py` amplía explícitamente el permiso de arranque
del controlador copiado al contenedor. No modifica las fuentes históricas.
Los valores se leen de vuelta por MAVLink antes de operar y se contrastan
independientemente con parámetros iniciales y cambios del ULog. El archivo
del adaptador, la configuración y los registros forman parte de los hashes.
Se rechaza una modificación durante el vuelo que no coincida con el contrato.

La revisión previa detectó dos huecos del primer adaptador: el resumen JSON
no estaba contrastado con los bytes del ULog, y un registro incompleto podía
parecer una historia sin cambios. Ambos se corrigieron antes de medir. Cada
evaluación vuelve a extraer los parámetros del binario en un proceso aislado
de sólo lectura. Se comprueban hash, identidad del episodio, extractor,
tramas completas hasta EOF, ausencia de pérdidas o corrupción y cobertura
desde preparación hasta desarmado, con la tolerancia temporal ya existente
de 60 ms. Múltiples segmentos o datos anexados no se aceptan en este perfil.
Las pruebas de regresión incluyen sustitución del resumen, truncado, pérdidas,
historia incompleta y omisión de archivos del manifiesto. Esto valida la
historia registrada bajo el supuesto del logger; no certifica cualquier
modificación no observable en un sistema adversario.

Esta calibración es trabajo de ingeniería humana asistida. No se atribuye a
ECHO como aprendizaje o automejora. Los intentos anteriores conservan su
resultado negativo. Confirmación, cierre de ECHO-5 y S6 siguen pendientes;
S6 no pertenece a este ensayo. No se ha usado una aeronave física.

El primer episodio nuevo (`0002-echo32`) terminó a las 00:48 del 11 de octubre:
recibo válido, retorno al origen, desarmado y reserva final 131, sin hallazgos.
La entrega ocurrió a los 347,900 s simulados y el desarmado a los 356,564 s.
El auditor de cada episodio volvió a extraer los parámetros del ULog. Todavía
faltan los otros dos modos y la auditoría conjunta en proceso independiente.
Este resultado permite continuar el plan registrado; no basta para declarar
corregida la estabilidad ni para abrir confirmación.

A las 00:56 terminó `0002-one_step`: recibo válido, retorno al origen,
desarmado y reserva final 129, sin hallazgos. El control convencional está
en ejecución; la auditoría conjunta sigue pendiente.

La medición y auditoría conjunta terminaron favorables hacia las 01:05. Los
tres modos conservaron recibos válidos, retorno al origen y desarmado; el
convencional terminó con reserva 132. La auditoría reprodujo exactamente las
tres filas. Se inició después una batería de desarrollo nueva de 18 vuelos en
`artifacts/sitl-development-20261011-r1/`. La calibración acredita estos tres
episodios del mismo caso, y no demuestra estabilidad universal ni una mejora
cognitiva. La repetición completa y la confirmación siguen pendientes.
