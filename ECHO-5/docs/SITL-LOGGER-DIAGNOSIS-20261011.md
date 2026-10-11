# Cierre del ULog y repetición de la validación

11 de octubre de 2026. ECHO-5 sigue pendiente de cierre. S6 queda aplazado
hasta después de ECHO-5.5.

La calibración `artifacts/velocity-calibration-20261011-r1/` terminó seis
episodios y su auditoría independiente reprodujo el resultado negativo. Cinco
episodios cumplen su criterio; el control convencional del caso de contradicción
no conserva evidencia válida. No debe reinterpretarse como una misión insegura:
el defecto impide verificarla con el contrato completo.

El ULog `0001-conventional/out/wd/log/2026-10-11/02_11_38.ulg` mide 30.720.000
bytes. El último registro comienza en el byte 30.719.970, declara 132 bytes de
cuerpo y sólo conserva 27. El extractor estricto informa `truncated ULog message
body`, por lo que no genera `ulog-parameters.json`. El proceso terminó con código
cero: ese código no acredita la integridad del registro. Los archivos originales
y el resultado negativo permanecen intactos.

El ejecutor terminaba PX4 después de observar el desarmado, sin solicitar antes
el cierre del logger. La corrección llama al cliente local `px4-logger stop`
después de la misión y antes de terminar PX4/Gazebo. El código de la imagen fijada
confirma que el cierre del logger detiene la escritura, vacía el buffer y espera
al hilo del escritor. Se limita la llamada al menor valor entre ocho segundos y
el tiempo restante del ejecutor, conservando el margen anterior para exportación.
Se rechazan errores,
timeouts y cierres forzados, incluso si el cliente devuelve cero. El resultado
original de la misión se conserva. El juez exige que el recibo de cierre limpio
sea posterior al desarmado y coincida con el resultado final del ejecutor, y
continúa comprobando el ULog completo mediante el extractor independiente.

El adaptador modifica en memoria el finalizador del ejecutor histórico,
verificando previamente su SHA-256. No se edita `nexus0/drone3/assets/runner.py`.
Los parámetros IMU, políticas, semillas de confirmación, límites de seguridad,
presupuestos y contrato de misión permanecen iguales. La documentación primaria
de PX4 describe el [registro ULog](https://docs.px4.io/main/en/dev_log/logging);
la comprobación concreta del vaciado se hizo sobre los fuentes de la imagen
local fijada por el contrato, no sobre una versión distinta de PX4.

Los tres casos de batería baja de la calibración anterior sí pasan. Disponen
inicialmente de 150 unidades, frente a una estimación de 226 para la misión y
74 para aterrizar. POWER decide aterrizar en casa antes de invocar al razonador.
Los recibos confirman desarmado, seguridad y reserva final de 127–129. No llegar
a la meta en este caso adverso es el comportamiento esperado; no demuestra una
ventaja cognitiva ni un trayecto de regreso desde una posición lejana. Forzar
la intervención del razonador o premiar la meta cambiaría el experimento.

Las pruebas requeridas de la corrección están en
`artifacts/closure-checks-20261011-r6/`: 340 casos de núcleo, con 12 opcionales
omitidos en ese entorno, y 32 casos de sandbox. Los recuentos se solapan y no se
suman como pruebas independientes. También pasan la comprobación del entorno
y la sintaxis JavaScript. Las pruebas nuevas ejercitan el finalizador real,
el orden de parada, fallos del cliente, timeout y preservación del error original.

El prerregistro nuevo está en `artifacts/logger-calibration-20261011-r1/plan.json`.
Repite los seis casos conocidos, empezando por el convencional que falló. Es
una comprobación de ingeniería emparejada, no una muestra de transferencia
nueva. Cada episodio conserva su resultado, incluidos los negativos. Una
auditoría en otro proceso debe reproducirlos y confirmar seis criterios
cumplidos antes de abrir `artifacts/closure-pipeline-20261011-r3/`.

La continuación incluye navegador, regresiones cognitivas, desarrollo físico
completo de 18 episodios, sus auditorías, confirmación cognitiva y confirmación
física de 18 episodios en el intervalo reservado 971809–971814. La confirmación
física anterior permanece fallida. Un fallo detiene las fases dependientes.
La cadena completa conserva el mínimo previo de 6 GiB disponibles. La calibración
secuencial añade una comprobación de 5 GiB disponibles para su único contenedor
limitado a 4 GiB. Se vigila el contador de OOM; una espera de recursos tiene un
máximo registrado de 30 minutos. El coordinador registra los fallos y detiene
las fases dependientes.

A las 19:09 (Madrid), el primer episodio repetido, convencional/contradicción,
terminó con `valid_receipt=true`, `safety_success=true`, `success=true` y
`findings=[]`. El logger cerró en 0,0236 s; el ULog nuevo conserva 31.213.375
bytes y la extracción estricta de parámetros pasó. Es una primera comprobación
de la reparación en Gazebo/PX4. Los cinco casos restantes y la auditoría
independiente siguen pendientes; este recibo no cierra ECHO-5.

El panel necesita reinicio porque protege su identidad de fuentes y devuelve
HTTP 409 si éstas cambian. Se conserva esa protección. El estado actual de los
procesos y recibos está en [CLOSURE-RUN-STATUS.md](CLOSURE-RUN-STATUS.md).
