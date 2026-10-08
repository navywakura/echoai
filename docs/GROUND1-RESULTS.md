# GROUND-1 — resultados

Estado: **ROJO bajo v1**. Validación A verde. Banco rojo en un solo grupo,
`latency`, heredado de SENSOR-1S: 2 registros de 435 875 salen sellados 1 ms
antes de su llegada. Todos los grupos de GROUND-1 (traducción física → WSP)
quedan verdes en las dos etapas. Evidencia válida; la auditoría independiente,
en un proceso nuevo, coincide. Contrato: [GROUND1-DESIGN.md](GROUND1-DESIGN.md),
con las enmiendas 1–3. Lock `c7d14645…1286`; informe final
`lab/echo3_ground1_report.json` (`38c71dad…`).

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría | Reinicios PX4 |
|---|---|---|---|---:|
| Validación A | 16 + 4 controles sin fuerza | 22/22 verdes | 169 comprobaciones, 0 hallazgos | 0 |
| Banco | 24 + 6 mutantes | 22/23: `latency` rojo | 249 comprobaciones, 0 hallazgos | 0 |

Mutaciones del informe 7/7 detectadas (incluidas `forge_wsp` y `forge_cable`).
Mutantes del banco 6/6. Cada uno pone rojo su caso concreto en un vuelo sano,
y su gemelo honesto del mismo mundo pasa.

## El rojo

| Vuelo | Fuente | Mensaje | `delivered_ns` | `arrive` privado |
|---|---|---|---|---|
| `clean-e6da9ac91abd450b-r1` (honesto) | LiDAR | n 357 | 37.348 s | 37.349 s |
| `mutant-seq_counter-a15b6f99a2cee25a` | RGB | n 712 | 48.784 s | 48.785 s |

Ninguno de los dos mensajes tenía fallo inyectado ni estaba congelado. Las
esperas quedaron dentro de sus cotas (máximo 6 ms, límite 30 ms).

Recuento exacto, cruzando cada cabecera enviada con la llegada privada del
mismo mensaje: 0 de 1 105 383 envíos en SENSOR-1S v2, 0 de 749 296 en v3, 0 de
292 945 en la validación A de GROUND-1, 0 de 436 668 en desarrollo y 2 de
435 875 en el banco. En total, 2 de 3 020 167.

**Causa, leída en el código y todavía no reproducida.** Está en el canal de
SENSOR-1S v2 (`sensor1s_v2/assets/sensor_runner.py`), que GROUND-1 hereda:

- el hilo emisor lee `now` (línea 240) **antes** de tomar el cerrojo con el que
  saca mensajes de la cola (línea 242);
- un callback de Gazebo que entra en ese hueco lee un tic posterior como
  `arrive` (línea 155) y encola su mensaje (línea 185);
- el emisor lo saca en la misma tanda y lo sella con el `now` anterior.

Es una carrera de un tic dentro de un solo proceso, no dos relojes. Por qué
aparece sólo en este banco no está medido. Hipótesis: el consumidor de
GROUND-1 carga más la CPU del host.

## Medidas

| | A | Banco |
|---|---|---|
| Distancia: barridos juzgados acertados | 9 574 / 9 574 | 11 724 / 11 724 |
| Distancia: cobertura mínima por episodio (juzgados / barridos) | 0.802 | 0.759 |
| Barridos no utilizables, todos dichos `DESCONOCIDO` | 24 | 36 |
| Primer `CAMBIAR` tras el empuje (ventana 400 ms) | 3–98 ms en 16 perturbados | 11–82 ms en 24 |
| `CAMBIAR` en la ventana de toque, por vuelo | 1–4 | 0–5 |
| `CAMBIAR` fuera de las ventanas; certeza `C` equivocada | 0; 0 | 0; 0 |
| Cable: una línea canónica, 0 bytes de vuelta, salida 0 | todos | todos los honestos |
| CAM: paquetes distintos por vuelo; distancia mínima de vértice | ≤ 8; 2 bits | ≤ 8; 1 bit |
| Espera máxima IMU / RGB / profundidad / LiDAR | 6 / 7 / 3 / 3 ms | 6 / 4 / 3 / 4 ms |
| Tramas, canarios | 292 945, 0 | 435 875, 0 |

## Qué significa y qué no

Significa que, en SITL, la traducción dentro de la jaula (una regla entera
cerrada, 10 paquetes posibles) se comportó así en los 44 vuelos honestos:

- dijo la banda de distancia verdadera en todos los barridos juzgados;
- marcó `CAMBIAR` tras cada empuje y sólo alrededor del toque;
- bajó la certeza exactamente en las ventanas con marcadores de fallo;
- salió por un único cable;
- dependió sólo de lo recibido y nunca del futuro.

Seis consumidores mentirosos, cada uno de una manera, fueron detectados.

No significa verde. El protocolo exige los grupos de SENSOR-1S en el mismo
vuelo, y uno cayó. Tampoco significa percepción de objetos, decisiones del
agente, vuelo de echoAI (`agent_in_gazebo=false`, `cortex_calls=0`) ni sensores
reales. La CAM es una comprobación estructural (enmienda 1): los vértices del
conjunto cerrado colisionan.

## Historia

- Contrato aprobado, con dos enmiendas previas al evaluador:
  1. la CAM separa por clave exacta, no por vértice;
  2. el toque de aterrizaje es un cambio real.
- Un revisor independiente, en tres pasadas, encontró 16 problemas antes del
  lock (5 dejaban pasar a un consumidor mentiroso). Se arreglaron (enmienda 3)
  y se volaron tres tandas de desarrollo; sólo la última corre el código final.
- La cadena voló una vez, sin reintentos. El lock no se toca.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.ground1.campaign audit
```

Log: `lab/ground1-run.log`. Evidencia: `lab/ground1/`.
