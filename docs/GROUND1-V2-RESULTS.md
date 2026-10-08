# GROUND-1 v2 — resultados

Estado: **VERDE bajo v2**. Validación A y banco completos, auditados, con
evidencia válida, todas las mutaciones del informe detectadas y 6/6 mutantes.
Contrato: [GROUND1-V2-DESIGN.md](GROUND1-V2-DESIGN.md), que es
[GROUND1-DESIGN.md](GROUND1-DESIGN.md) con sus enmiendas 1–3 y un único cambio
en el canal. Lock `602292b9…1efd`; A `46d14c9e…`, banco `21292394…`, final
`lab/echo3_ground1_v2_report.json` (`05ccbfd0…`). GROUND-1 v1 sigue rojo
([GROUND1-RESULTS.md](GROUND1-RESULTS.md)).

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría | Reinicios PX4 |
|---|---|---|---|---:|
| Validación A | 16 + 4 controles sin fuerza | 22/22 verdes | 169 comprobaciones, 0 hallazgos | 0 |
| Banco | 24 + 6 mutantes | 23/23 verdes | 249 comprobaciones, 0 hallazgos | 0 |

La auditoría de la cadena y la auditoría independiente, en un proceso nuevo,
coinciden. Mutaciones del informe 7/7 detectadas. Mutantes del banco 6/6: cada uno pone
rojo su caso concreto en un vuelo sano y su gemelo honesto del mismo mundo
pasa.

## El arreglo de v1

v1 cayó porque 2 de 435 875 registros salieron sellados 1 ms antes de su
llegada. La causa era que el emisor del canal leía el reloj fuera del cerrojo
de la cola. v2 lo lee dentro, con la comprobación igual de estricta.

- Un test determinista fuerza la carrera en el host: el canal viejo da −1 ms;
  el nuevo da 0 y el mensaje queda bloqueado en el cerrojo.
- En vuelo: 0 de 294 644 envíos en A, 0 de 445 271 en el banco y 0 de 149 928 en
  desarrollo.
- Límite: esos ceros no prueban la corrección. A la tasa del banco de v1 se
  esperarían ~3.4 casos en A + banco; a la tasa de toda la evidencia anterior,
  ~0.5. La prueba es el test.

## Medidas

| | A | Banco |
|---|---|---|
| Distancia: barridos juzgados acertados | 9 314 / 9 314 | 11 919 / 11 919 |
| Distancia: cobertura mínima por episodio (juzgados / barridos) | 0.760 | 0.823 |
| Barridos no utilizables, todos dichos `DESCONOCIDO` | 24 | 36 |
| Primer `CAMBIAR` tras el empuje (ventana 400 ms) | 30–97 ms en 16 perturbados | 9–99 ms en 24 |
| `CAMBIAR` en la ventana de toque, por vuelo | 1–5 | 0–4 |
| `CAMBIAR` fuera de las ventanas; certeza `C` equivocada | 0; 0 | 0; 0 |
| Cable: una línea canónica, 0 bytes de vuelta, salida 0 | todos | todos los honestos |
| CAM: paquetes distintos por vuelo; distancia mínima de vértice | ≤ 8; 1 bit | ≤ 8; 2 bits |
| Espera máxima IMU / RGB / profundidad / LiDAR (límite 30 ms) | 6 / 4 / 3 / 2 ms | 4 / 3 / 2 / 3 ms |
| Espera p99 máxima por fuente (límite 2 ms) | 1 / 2 / 2 / 1 ms | 1 / 2 / 2 / 1 ms |
| Tramas, canarios | 294 644, 0 | 445 271, 0 |

## Límites declarados

- **CAM** es una comprobación estructural (enmienda 1): la ranura es la clave
  exacta de 16 B. Los vértices del conjunto cerrado colisionan (1–2 bits), así
  que un módulo que agrupe por `nearest()` no separaría esos perceptos.
- **Ambigüedad vertical** (±5 cm) y ventana de toque −100 ms (enmienda 3):
  elegidas con datos vistos, de SENSOR-1S v3 y desarrollo.
- **Certeza** se juzga contra los marcadores de los registros entregados. Un
  retraso no es marcador; una fuente que calla del todo no baja `C`; un LiDAR
  muerto da silencio, no `DESCONOCIDO`.
- **Canal de tiempo**: el ritmo de lectura del consumidor queda acotado por los
  límites de espera, no cerrado; está fuera de alcance, como en SIM-3.
- **Espera p99 en el límite**: RGB y profundidad llegan a 2 ms, el límite, en
  algunos vuelos. Heredado de SENSOR-1S; no cayó.
- **Rehearsal**: los 12 mundos de rehearsal, sin examen reservado. Sólo dos
  bandas de distancia, y la distancia sólo cambia al despegar y aterrizar.

## Qué significa y qué no

Significa que, en SITL, la traducción física → WSP de 16 B dentro de la jaula
cumple lo que dice en 44 vuelos honestos del examen:

- depende sólo de lo que entregan los sensores, sin futuro;
- sale por un único cable;
- dice la banda de distancia verdadera en todos los barridos juzgados;
- marca el empuje y el toque, y nada más;
- baja la certeza exactamente donde hubo marcadores de fallo.

Los grupos de SENSOR-1S siguen verdes en los mismos vuelos, y seis
consumidores mentirosos distintos son detectados.

No significa percepción de objetos (PATTERN-1R), fusión de evidencias
(FUSION-1), decisiones ni vuelo del agente (`agent_in_gazebo=false`,
`cortex_calls=0`), ni sensores reales.

## Historia

- **v1, rojo**: todos los grupos de traducción verdes; cayó `latency`,
  heredado, por la carrera del sello. Antes del lock, un revisor independiente
  encontró 16 problemas (enmienda 3).
- **v2, verde**: el reloj se lee dentro del cerrojo. El resto es v1, importado.
  Un segundo revisor independiente no encontró ningún verde falso ni hueco en el
  lock.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.ground1_v2.campaign audit
```

Log: `lab/ground1-v2-run.log`. Evidencia: `lab/ground1-v2/`.
