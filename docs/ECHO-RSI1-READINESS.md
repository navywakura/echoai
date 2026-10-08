# ECHO RSI 1 preparación y lanzamiento

**Cierre del 2 de octubre, 08:16:37 Madrid:** RSI1-R1 terminó DONE/ROJO.
75 generaciones, 57 llamadas, cero gasto externo; recursivo 99/144 frente a
101/144 aleatorio, sin ventaja sobre el brazo sin acumulación. Los 15 replays
del examen coinciden. [Informe](ECHO-RSI1-RESULTS.md). Los cortes de arranque
que siguen se conservan como historial; el proceso ya no está ejecutándose.

**Actualización, 2 de octubre de 2026.** PROBE2 terminó válido a las 04:16
Madrid. La cola arrancó RSI1, pero la primera llamada a llama.cpp abortó
en ROCm; la condición original conserva BLOCKED y una llamada fallida.
La [recuperación declarada RSI1-R1](ECHO-RSI1-RECOVERY1.md) pasó los 17
tests del instrumento y una llamada real de calibración en CPU sin cómputo
GPU. Está ejecutándose desde las 04:35:47 como servicio de usuario
`echoai-rsi1-recovery1`, sin reinicio automático y con límite de ocho horas.
[Estado actual](../lab/research/echo-rsi1-recovery1-20261002/status.json),
[lanzamiento](../lab/research/echo-rsi1-recovery1-20261002/launch.json).
El texto siguiente conserva el corte histórico de preparación del día 1.

1 de octubre de 2026, 18:35 Madrid. [Contrato congelado](ECHO-RSI1-DESIGN.md)
y [plan ECHO-5.5](ECHO55-INFRASTRUCTURE-PLAN.md) preparados. No se publica
el experimento privado ni se inicia gasto externo.

## Qué se ha comprobado

12/12 tests pasan con el Python 3.12 fijado. Cubren propuestas inseguras,
outputs privados, separación de particiones, veto de regresiones, replay
distinto, presupuesto, ausencia de reintentos invisibles y la dependencia
de PROBE2. Una prueba recorre las cinco generaciones y el examen con el
solver real y transporte simulado, y conserva el resultado rojo.

El renderizador matplotlib exportó SVG y PNG válidos en un fixture artificial,
fuera de las cohortes. No son gráficas de resultados de RSI: se generarán al
terminar la medición real. La inferencia del GGUF **aún no se ha probado en
esta condición** y su duración real sigue pendiente. Máximo: 57 llamadas
locales, ocho horas de pared por ejecución y 0 € de servicio externo.

La preparación archivó las fuentes, runtime y hashes del modelo y ejecutable.
La integridad de PROBE2 sigue pasando. Recibos en
`lab/research/echo-rsi1-20261001/verification.json` y `profile.json`.

## Cola real y persistencia

Se intentó registrar `echoai-rsi1-after-probe2` con `systemd-run --user`;
el entorno respondió: `Failed to connect to user scope bus via local transport:
Operation not permitted`. No hay servicio RSI registrado por ese intento.

La cola está iniciada en una sesión de ejecución gestionada (85243), con
prioridad `nice 10`, comprobación cada 30 segundos y estado `WAITING_PROBE2`.
Arrancará el ensayo local después de un recibo válido DONE de PROBE2,
si este proceso sigue activo. **No se garantiza que sobreviva al cierre de
la sesión gestionada o al apagado del equipo.** No se confunde con el
servicio PROBE2 que Claude registró en el host.

`queue.lock` impide dos colas simultáneas. Para trasladarla a un servicio
persistente desde el host hay que detener únicamente la cola gestionada,
comprobar que libera su lock y usar el comando siguiente. No detener PROBE2:

```sh
systemd-run --user --unit=echoai-rsi1-after-probe2 \
  --property=Nice=10 \
  --property=WorkingDirectory=/home/roger/REALRXOS/RXos/echoai \
  --property=StandardOutput=append:/home/roger/REALRXOS/RXos/echoai/lab/research/echo-rsi1-20261001/queue-process.log \
  --property=StandardError=append:/home/roger/REALRXOS/RXos/echoai/lab/research/echo-rsi1-20261001/queue-process.log \
  /home/roger/REALRXOS/RXos/echoai/lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -u -m seed.rsi1_queue
```

Estado y lanzamiento se guardan en `queue-status.json`, `queue-process.log`
y `launch.json`. Una terminación roja científicamente válida de PROBE2 no
bloquea RSI; un error de integridad, replay o solidez sí.

## Lectura que se permitirá del resultado

Separar ventaja de resolución, acumulación de bibliotecas y productividad
de nuevas promociones. Dos llamadas de investigación por condición son un
ensayo muy pequeño; el estado retenido puede tener menos margen de mejora
por resolver ya más tareas. Informar ese límite al interpretar tasas y no
atribuir una curva creciente a aceleración general de investigación.

Un resultado privado RSI verde solo acredita el contrato sintético fijado.
No convierte S6, ECHO-4.5, ARC ni ECHO-5.5 en verde. La siguiente condición
con un modelo de API debe fijar proveedor, identificador, presupuesto y
permisos para datos antes de consumir créditos.
