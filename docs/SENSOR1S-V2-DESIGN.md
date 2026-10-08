# SENSOR-1S v2 — el canal de sensores en su propio proceso

Estado: **prerregistro aprobado por Roger** (2026-09-11), anterior a cualquier
vuelo v2 de validación. V1 se conserva roja e intacta.

## Por qué v2

SENSOR-1S v1 cayó en validación A por un único registro de 293 466: una espera
del adaptador de 31 ms frente al máximo prerregistrado de 30 ms, durante el
arranque de PX4 ([SENSOR1S-RESULTS.md](SENSOR1S-RESULTS.md)). Los otros 13
grupos fueron verdes.

Diagnóstico (desarrollo, `lab/sensor1s-v2/dev/diag1`, `diag2`, con el runner v1
instrumentado en una copia): antes del primer heartbeat de PX4 el emisor se
bloqueó escribiendo en la FIFO cuadros RGB de 230 KB y de profundidad de 77 KB
(14.5–37 ms; la tubería era de 64 KiB), y en otro vuelo el hilo emisor no fue
planificado durante 13–18 ms. Ningún callback fue lento y el host nunca se
bloqueó al reenviar al consumidor. En v1 las esperas > 15 ms aparecen al
arrancar (5 eventos, máx. 31 ms) y durante el aterrizaje (6, máx. 29 ms):
momentos en que el proceso de vuelo trabaja con MAVLink, en el mismo
intérprete que el canal.

## Cambio, en la fuente

- El canal completo (tap, inyector, adaptador y escritor) corre en **un proceso
  propio**, con su intérprete y sus suscripciones al reloj y a la pose real de
  Gazebo. El proceso de vuelo vuelve a ser exactamente el runner v6 (más el
  `PX4_SIM_MODEL` de v1).
- La FIFO se amplía a **1 MiB** (`F_SETPIPE_SZ`; límite del kernel 1 MiB): un
  cuadro completo cabe sin esperar al lector.
- La lógica de tap, inyector y adaptador es la de v1, sin cambios. Las paradas
  del emisor > 4 ms quedan en el registro privado como evidencia, no se juzgan.

## Desarrollo v2 antes del lock (`lab/sensor1s-v2/dev/`, no cuenta)

- 15 vuelos honestos con el canal en su proceso: todos los grupos verdes; FIFO
  a 1 048 576 B en todos; espera máxima IMU 5 / RGB 3 / profundidad 4 /
  LiDAR 3 ms (v1: hasta 31 ms); 10 pausas del emisor > 4 ms en total, ninguna
  cerca de 30 ms. Límite: 13 de los 15 son el mismo mundo (A0) y limpios, por
  un error de comillas del lote; ver `NOTE-mislabelled-batch.md`.
- 7 mutantes volados con argumentos explícitos, cada uno con 16 fallos: los 7
  completan el vuelo y ponen rojo su caso concreto.
- `test_sensor1s_v2` 6/6 y `test_sensor1s` 24/24.

## Lo que no cambia

Contrato de v1 con sus dos enmiendas previas al lock: preguntas, sensores,
rig, fallos, evaluador, campos fijados, **espera máxima 30 ms**, p99 ≤ 2 ms,
cotas de latencia, ventana del pulso 0–12 ms, ruido y tamaños (A 16 + 4
controles, banco 24 + 7 mutantes). El evaluador y el consumidor se importan de
v1 sin copiar. Semillas nuevas: 20261011 (A) y 20261012 (banco).

## Límites declarados

V2 repite el mismo instrumento tras un rojo; v1 no se reescribe. El banco sigue
usando los 12 mundos rehearsal, incluidos los 4 de A. La sesión y el
coordinador son copias de v1 con las referencias de ruta, versión, semillas e
historia cambiadas; las pruebas comprueban que no hay otra diferencia.

Un verde v2 significaría lo mismo que habría significado v1: sensores simulados
con metadatos correctos en SITL; no sensores físicos, percepción, WSP ni
autonomía.
