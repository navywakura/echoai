# SENSOR-1S v3 — resultados

Estado: **VERDE bajo v3**. Validación A y banco completos, auditados, con
evidencia válida y todas las mutaciones del informe detectadas. Contrato:
[SENSOR1S-V3-DESIGN.md](SENSOR1S-V3-DESIGN.md) (criterios de v1 con sus dos
enmiendas; canal de v2; sesgo del LiDAR con filtro de sensibilidad angular).
Lock `1308c536…583f`; A `c3766267…`, banco `0b0340d6…`, final
`lab/echo3_sensor1s_v3_report.json` (`1428350d…`). V1 y v2 siguen rojas.

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría | Reinicios PX4 |
|---|---|---|---|---:|
| Validación A | 16 + 4 controles sin fuerza | 14/14 verdes | 169 comprobaciones, 0 hallazgos | 0 |
| Banco | 24 + 7 mutantes | 15/15 verdes | 257 comprobaciones, 0 hallazgos | 0 |

Auditoría de la cadena y auditoría independiente en proceso nuevo coinciden.
Mutaciones del informe 5/5 detectadas. Mutantes del banco 7/7: cada uno pone
rojo su caso concreto con el vuelo completo y su gemelo honesto del mismo mundo
pasa.

## Medidas

| | A | Banco |
|---|---|---|
| Espera máxima IMU / RGB / profundidad / LiDAR | 4 / 3 / 4 / 2 ms | 5 / 3 / 7 / 3 ms |
| P99 limpia captura→entrega (cotas 10/50/60/150) | 1 / 14–15 / 20–22 / 60–68 ms | 1 / 14–15 / 20–22 / 61–67 ms |
| Fallos: pérdidas / obsoletos / inválidos por fuente | 5 / 2 / 1 en cada vuelo con fallos; 0 en limpios | igual |
| Ruido agrupado LiDAR σ/declarado, sesgo | 0.996, 0.03 mm (n = 28 046) | 1.001, −0.29 mm (n = 26 108) |
| Ruido agrupado profundidad | 1.004, −0.02 mm (n = 84 414) | 1.002, −0.07 mm (n = 70 650) |
| LiDAR por episodio: σ/declarado, sesgo | 0.966–1.040, −0.93…+0.76 mm | 0.957–1.040, −1.99…+0.61 mm |
| Inicio del pulso en la IMU (ventana 0–12 ms) | 1–5 ms en 16 perturbados | 2–6 ms en 24 |
| Controles sin fuerza en silencio | 4/4 | — |
| Tramas, canarios | 299 268, 0 | 450 028, 0 |

Los dos mundos que tumbaron v2 pasan: `fc7b66ad…` sesgo −1.06 y −1.99 mm (408
y 425 haces juzgables); `3d98a13f…` −1.93 mm en el vuelo con fallos.

## Límites declarados

- El sesgo del LiDAR **no se juzgó** en 3 de 24 episodios del banco por tener
  menos de 200 haces juzgables: `cb83617b…` (48 y 90) y el limpio de
  `3d98a13f…` (135). En ellos se juzgó σ, y sus haces entran en el sesgo
  agrupado de la etapa.
- El filtro (0.5°, 10 mm) se eligió con los datos del banco rojo de v2. V3 voló
  todo de nuevo, con semillas nuevas, pero en los mismos 12 mundos de
  rehearsal: no es un examen reservado.
- El sesgo del LiDAR no queda certificado en geometría rasante o de borde
  estrecho, donde el LiDAR de GPU se desvía haz a haz hasta ~0.5°.

## Qué significa y qué no

Significa: en SITL, cuatro sensores simulados del X500 (IMU, RGB, profundidad y
LiDAR) llegan a un consumidor aislado con fuente, sello de captura, latencia,
pérdida, validez y ruido correctos frente a la verdad privada; los fallos
inyectados se informan exactos; ningún identificador del mundo se filtra; y
un adaptador que mienta de siete maneras distintas es detectado.

No significa: sensores físicos, calibración real, percepción, traducción a WSP
(eso es GROUND-1) ni autonomía echoAI (`agent_in_gazebo=false`,
`cortex_calls=0`, `wsp_writes=0`).

## Historia que acompaña al verde

- v1: rojo por una espera de arranque de 31 ms frente a 30.
- v2: el canal en su proceso eliminó la parada; rojo por el sesgo del LiDAR en
  2 mundos, que la investigación atribuyó a la sensibilidad angular del modelo
  de verdad, no al adaptador.
- v3: sólo cambia cómo se juzga ese sesgo. El límite de 30 ms nunca se tocó.

## Adenda factual (2026-09-11, al preparar GROUND-1)

El modelo de verdad de los evaluadores de SENSOR-1S (v1–v3) sitúa el sensor
0.24 m bajo su posición real: Gazebo publica la pose del marco del modelo y el
`x500_base` de PX4 coloca `base_link` a `<pose>0 0 .24</pose>` de ese marco;
el montaje (0.12, 0.03, 0.242) es relativo a `base_link`. Se detectó en vuelo
(el LiDAR pasa por encima de muros que la verdad baja todavía toca: 99.84 % de
acuerdo con la corrección frente a 95.56 % sin ella). Recalculado con la altura
correcta, ningún caso de ruido de los 44 vuelos honestos de v3 cambia de valor
ni de veredicto: en reposo los rayos son horizontales y las paredes verticales.
El veredicto bloqueado no se toca; GROUND-1 usa la pose corregida.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sensor1s_v3.campaign audit
```

Log: `lab/sensor1s-v3-run.log`. Evidencia: `lab/sensor1s-v3/`.
