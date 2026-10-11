# Confirmación robótica del 11 de octubre: diagnóstico y corrección

La cadena iniciada a las 01:04 terminó a las 03:20 de Madrid. La confirmación
CPU y su auditoría pasaron. La confirmación Gazebo/PX4 produjo 17 de 18
recibos válidos y bloqueó el cierre. Los archivos originales permanecen en
`artifacts/sitl-confirmation-20261011-r1/`; no se convierten en pases.

En `0001-echo32`, la orden 14 recibió ACK y acercó el vehículo a su destino,
pero no consiguió tres muestras de llegada dentro de los 15 segundos.
El supervisor cortó la sesión por `execution_fault` a los 105,306 segundos
simulados. La estimación final era `[11982, 3076, 2755]` mm para un destino
`[12000, 3000, 2500]`, con velocidad de 278 mm/s. La velocidad permitida
es 150 mm/s. PX4 aterrizó y se desarmó; la misión quedó sin resolver.

En `0002-one_step`, la entrega de control con poca batería ocurrió a los
347,9 segundos simulados. Durante los veinte segundos siguientes no se
obtuvo una observación estable. El último diagnóstico registró 230 mm/s,
frente al requisito de menos de 200 mm/s. El actor no recibió observaciones
ni produjo decisiones. La auditoría no puede tratarlo como derrota cognitiva.

Las medianas de velocidad vertical estimada por PX4 en las ventanas de
fallo son aproximadamente +0,215 m/s y −0,283 m/s en NED. La causa inmediata
de ambos rechazos está en la estabilización estimada. La atribución al
sesgo inercial y a su fusión con GNSS se contrasta con ULog y poses privadas;
estas poses sirven al diagnóstico y al juez, nunca a la política.

La corrección de ingeniería bajo prueba aumenta `EKF2_ACC_NOISE` de 0,35
a 0,7 m/s² para declarar mayor incertidumbre de predicción inercial. Es una
hipótesis, todavía no una corrección física demostrada. Se mantiene
`EKF2_ACC_B_NOISE=0.01`, el ruido de los sensores, los mundos, los límites
de velocidad/llegada, los presupuestos y la lógica de ECHO. El parámetro
pertenece al rango [0,01, 1] documentado por
[PX4 1.15](https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_ACC_NOISE).
La lectura MAVLink y la extracción independiente del ULog comprueban que
el valor aplicado coincide con el contrato y no cambia durante el vuelo.

Hay un defecto adicional del ejecutor: la rama de excepción corta los
latidos y termina enseguida PX4/Gazebo, antes de observar su recuperación.
El adaptador nuevo conserva el error y el resultado fallido, mantiene
cortados los comandos y latidos, y concede una espera acotada para registrar
el desarmado del autopiloto. Un aterrizaje posterior no transforma la misión
fallida en éxito ni sustituye la corrección de la estimación.

El plan `artifacts/velocity-calibration-20261011-r1/plan.json` fija seis
episodios nuevos: cambio del entorno y batería baja, cada uno en los tres
modos. Requiere recibos válidos, seguridad y desarmado en todos; retorno en
batería baja y misión completada por ECHO en el caso normal. Una auditoría
en otro proceso reconstruye cada fila. Un fallo detiene la continuación.

La confirmación 861703–861708 ya está expuesta. La siguiente confirmación
registra 971809–971814 antes de medir; ambos intervalos quedan excluidos
del desarrollo. Los resultados CPU existentes conservan su alcance y su
versión; la nueva calibración no constituye aprendizaje autónomo de ECHO.

Kaggle se comprobó con un notebook privado. Dispone de CPU y memoria, pero
carece de Gazebo/PX4/Podman y deniega la creación de los espacios de nombres
necesarios para el contenedor fijado. Las pruebas portables de regresión se
ejecutan allí por separado; no se presentan como vuelos ni como auditoría
física. La GPU no acelera estas pruebas de Python. Los recibos de capacidad
se conservan en `artifacts/kaggle-sitl-20261011-r1/`.

Actualización 04:10 Madrid: las regresiones privadas de Kaggle pasaron
18/18 pruebas de recuperación y 10/10 pruebas portables de parámetros con
Python 3.12.13. La prueba de limpieza del extractor de ULog, que importa el
lanzador completo, se ejecutó localmente dentro de la suite; no se subió ese
lanzador a Kaggle. Los 28 recibos cloud corresponden a los mismos hashes de
las fuentes activas, comprobados en `active-source-reconciliation.json`.
Los checks locales r4 pasaron: 335 casos recogidos (12 opcionales omitidos)
y 32 casos del entorno MiniGrid/BabyAI; estos recuentos se solapan.

La calibración arrancó a las 04:05 Madrid como proceso separado. El primer
caso de cambio de mundo del modo ECHO completó misión, regreso y desarmado,
con recibo válido y sin hallazgos. Es un resultado de desarrollo, pendiente
de los otros cinco casos y de reconstrucción independiente. La cadena
`artifacts/closure-pipeline-20261011-r2/` sólo se abre si pasan ambos.
La GPU de Kaggle no se solicitó ni consumió en estas regresiones.
