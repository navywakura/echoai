# SENSOR-1S v1 — resultados

Estado: **rojo en validación A**. 13 de 14 grupos verdes; cae `latency` por un
único registro de 293 466: una espera del adaptador de 31 ms frente al máximo
prerregistrado de 30 ms, durante el arranque de PX4. Banco no autorizado. Sin
reintentos. Contrato: [SENSOR1S-DESIGN.md](SENSOR1S-DESIGN.md), con sus dos
enmiendas previas al lock. Lock `1622b60f…a3e6`, informe de etapa
`lab/sensor1s/validation/report.json` (`18491b8c…`), final
`lab/echo3_sensor1s_report.json`.

## Veredicto de A

| Grupo | Estado | Nota |
|---|---|---|
| Ejecución | verde | 20/20 vuelos completos, 0 reinicios PX4; inyecciones = calendario planificado |
| Esquema | verde | campos fijados en cada registro; transcripción = registro del adaptador; recuento del consumidor = recálculo desde la transcripción |
| Aislamiento | verde | 0 canarios en 293 466 tramas; autocomprobación de la jaula correcta |
| Fuente, tiempo, validez, pérdida | verde | emparejamiento uno a uno contra el tap; cobertura completa |
| Ruido (episodio y agrupado) | verde | ver tabla |
| **Latencia** | **rojo** | `clean-ef7f22a49738b970-r2`, profundidad: espera 31 ms > 30 ms |
| Denominador, jaula, modelo, congelado | verde | |

Auditoría de la cadena y auditoría independiente en proceso nuevo: evidencia
válida, 169 comprobaciones, 0 hallazgos. Mutaciones del informe detectadas 5/5.

## El registro que decide

Profundidad, `seq` 2: capturado a 1.783 s (97 ms después del primer mensaje del
flujo), llegó al tap a 1.800 s y salió a 1.831 s. La misma parada retrasó los
IMU siguientes 27, 23, 19, 15, 11 y 7 ms: un único bloqueo de ~31 ms de tiempo
simulado del hilo emisor, mientras PX4 arrancaba. Es latencia real del
adaptador, no un error de medida. Desarrollo había mostrado paradas de
arranque de hasta 23 ms; el revisor lo señaló; la cota se fijó en 30 ms antes
del lock. En otro vuelo la IMU llegó a 28 ms.

## Medidas

| Fuente | P99 limpia captura→entrega (cota) | Espera p99 | Espera máx. |
|---|---|---|---|
| IMU | 1–2 ms (10) | 1–2 ms | 28 ms |
| RGB | 13–22 ms (50) | 1–2 ms | 3 ms |
| Profundidad | 18–29 ms (60) | 1–2 ms | **31 ms** |
| LiDAR | 59–67 ms (150) | 1 ms | 3 ms |

Fallos: los 8 vuelos con fallos informaron exactamente 5 pérdidas, 2
obsoletos y 1 inválido por fuente; los 12 limpios, 0. Ninguna pérdida natural.

| Ruido | Por episodio | Agrupado |
|---|---|---|
| LiDAR σ/declarado | 0.951–1.026, sesgo −0.79…+0.72 mm | 0.993, n = 31 882 |
| Profundidad σ/declarado | 0.984–1.021, sesgo −0.29…+0.13 mm | 1.002, n = 94 498 |
| IMU (6 ejes) | 0.882–1.098 | — |

Inicio del pulso en la IMU, 16 perturbados: 2–7 ms (ventana 0–12 ms). Los
controles sin fuerza, 4/4 sin inicio. Con la ventana original de 4 ms, 4 de
los 16 habrían caído rojos sin error de sello.

## Qué dice y qué no

Dice: en A, el canal entrega los cuatro sensores simulados con fuente, sello,
pérdida, validez y ruido correctos frente a la verdad privada, sin filtrar
identidad del mundo, y el evaluador endurecido por el revisor no encuentra
fallo en esos grupos. No dice que el adaptador cumpla la cota de espera: no la
cumplió en un registro de arranque. SENSOR-1S v1 no es verde; el banco no se
voló. Nada de esto acredita sensores físicos, percepción, WSP ni autonomía.

## Reproducir

Desde `echoai`:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sensor1s.campaign audit
```

Log de la cadena: `lab/sensor1s-run.log`. Desarrollo previo al lock, conservado:
`lab/sensor1s/dev/`.
