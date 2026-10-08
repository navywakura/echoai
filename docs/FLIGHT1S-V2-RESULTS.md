# FLIGHT-1S v2 — resultados medidos

**Estado: ROJO. El defecto de v1 quedó reparado; el banco no cierra por dos
causas nuevas y distintas.** Fecha: 2026-09-10.
Diseño: [FLIGHT1S-V2-DESIGN.md](FLIGHT1S-V2-DESIGN.md).
Repara, sin tocarlo: [FLIGHT1S-RESULTS.md](FLIGHT1S-RESULTS.md).
Informe: `lab/echo3_flight1s_v2_report.json` ·
`report_sha256 = 6e3de4a8da35f3ec4820601aa99266c925e5d864ece9799e0fe475f371cb4764`.
Auditoría: `lab/echo3_flight1s_v2_audit.json`.

Ocho de los once grupos en verde, 48/48 episodios completos.
**`flight1s_green=false`**: fallan `challenge` (1 de 48, un episodio nominal),
`recovery` (1 de 24) y `repetition` (1 de 24, consecuencia del anterior).
El rojo se conserva. §4 dice exactamente qué falló.

---

## 1. Comandos y salidas reales

```bash
cd /home/roger/REALRXOS/RXos/echoai

PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 validate                                     # exit 0
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 preflight \
    --protocol docs/examples/flight1s-v2/protocol.json \
    --output lab/flight1s-v2/runtime-lock.json                                                 # exit 0
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 bench --rehearsal \
    --protocol docs/examples/flight1s-v2/protocol.json \
    --output lab/echo3_flight1s_v2_report.json                                                 # exit 1
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 audit lab/echo3_flight1s_v2_report.json     # exit 1

PYTHONPATH=.. python3 tests/test_flight1s_v2.py       # 25 tests OK
PYTHONPATH=.. python3 tests/test_flight1s.py          # 24 tests OK  (banco v1, intacto)
PYTHONPATH=.. python3 tests/test_sim3.py              # 44 tests OK
PYTHONPATH=.. python3 tests/test_flight1s_backend.py  # 13 tests OK  (PX4 real)
```

```text
preflight exit=0
bench     exit=1     3.946,0 s de reloj de pared, flight1s_green=false
audit     exit=1     evidence_valid=true, 435 comprobaciones, 0 hallazgos
```

`audit` devuelve 1 porque el informe es rojo, no porque la evidencia falle.
Son dos hechos distintos y el código los separa.

**Nota sobre la CLI.** El relevo pedía `--protocol` en los comandos v1.
Añadirlo habría cambiado `nexus0/flight1s/__main__.py`, que está dentro del
inventario de código del lock de v1, y el informe v1 habría dejado de
reconstruir — justo el fallo que §2 del relevo prohíbe. Por eso v2 tiene su
propia entrada, `python3 -m echoai.nexus0.flight1s.v2`, con `--protocol` en
todos sus comandos y el instante v2 por defecto. Los comandos v1 conservan su
significado byte por byte.

---

## 2. v1 sigue intacto

Se hashearon los artefactos v1 antes de empezar
(`lab/flight1s-v2/v1-preservation.json`) y se volvieron a hashear al terminar:

```text
10 archivos protegidos      sin cambios
15 archivos de código v1    sin cambios   code_sha256 c4dd8fdb…
48 trazas v1                digest idéntico
48 ULog v1                  digest idéntico
auditor v1                  evidence_valid=true, 375 comprobaciones,
                            0 hallazgos, 48 episodios recalculados, exit 1
```

Cómo se consigue: `nexus0/flight1s/v2/` es un **subpaquete** y el lock de v1
hashea `nexus0/flight1s/*.py` con un glob no recursivo; el esquema v2 vive en
`docs/schemas/flight1s-v2/` porque un archivo `docs/schemas/flight1s-*.json`
sí habría entrado en ese inventario — comprobado, no supuesto. Ningún archivo
de v1 se editó. El preflight v2 registra el `code_sha256` de v1 y se niega a
correr si cambia; el grupo `v1_preserved` lo vuelve a comprobar en cada banco;
el auditor v2 rechaza un informe que declare v1 tocado o v1 verde.

---

## 3. Calibración A-v2

68 episodios en los cuatro mundos A, orden permutado por la seed 20260911:
32 nominales frescos, 32 perturbados frescos y 4 controles negativos
(`force_declared_without_wrench`, uno por mundo). Todo en
`lab/flight1s-v2/calibration.json`.

```text
separación en impulso
  controles negativos   n=4    -7 .. 39 ppk    mediana 27
  perturbados reales    n=32  895 .. 1067 ppk  mediana 963
  hueco                                        856 ppk

nominal      hover horiz máx  67,7 .. 191,3 mm   excursión  95,2 .. 235,0 mm
perturbado   excursión       401,3 .. 636,2 mm   recuperación 1.147 .. 6.827 ms
             actitud       12.255 .. 13.036 mdeg
```

Las ocho puertas de la calibración pasaron. Los números salieron de las reglas
escritas antes de volar:

```text
radio de recuperación   max(200, ceil(191,3 → 50)) = 200 mm
margen de salida        ceil(1500 mm/s × 25 ms) + 10 mm = 38 + 10 → 50 mm
umbral de desafío       200 + 50 = 250 mm
suelo de impulso        max(500, 16,25 + 6×17,88 → 130) = 500 ppk
techo de impulso        1500 ppk, fijo
```

Protocolo congelado:
`docs/examples/flight1s-v2/protocol.json`,
`sha256 = 8afa05238c27a7869d385bf38f17739b4e34e1e69c610bd88012b6329d7dee99`,
`order_seed = 20260912`. Fuerza 5.000 mN durante 600 ms, sin cambios respecto
a v1. Impulso mandado 3.000 mN·s, delta-v libre 1.453 mm/s.

---

## 4. El rojo

### 4.1 `recovery` — 1 de 24

`perturbed-e6da9ac91abd450b-r2`. El cuerpo volvió a la banda de 200 mm en
**1,23 s**, más rápido que su propia pareja (1,41 s), y luego **volvió a
salir**:

```text
t+0,01 s   409,5 mm   fuera
t+1,42 s   102,2 mm   dentro
t+2,83 s   270,3 mm   fuera      ← sobreoscilación de vuelta
t+3,53 s   283,0 mm   fuera
t+7,05 s   218,3 mm   fuera
t+7,75 s   194,5 mm   dentro
t+9,87 s   151,5 mm   dentro
```

La segunda entrada definitiva ocurre alrededor de t+7,4 s y sólo deja **2,6 s**
dentro antes de que la ventana de 10 s se cierre: falta permanencia, no
retorno. El criterio pide volver **y quedarse** 3 s, y eso es lo que no hizo.
Es comportamiento real de PX4, no un artefacto de medida.

### 4.2 `challenge` — 1 de 48, y es un nominal

`nominal-fbfb2f3b01be4f00-r2`, con `wrench_published=0` y fuerza `[0,0,0]`,
derivó **270,6 mm** en la ventana posterior al hover, por encima del umbral de
250 mm. Su máximo *dentro* de la ventana de hover fue de sólo 98,0 mm: la
deriva ocurre después, en la fase de mantenimiento de posición.

**Los 24 perturbados salieron de la banda.** Lo que falla es la mitad de
control de la puerta, la que exige que el vehículo sin perturbar se quede
dentro. Esa puerta se declaró en el diseño **antes** de correr el banco, junto
con el riesgo que aceptaba: en A-v2 el máximo nominal fue 235,0 mm sobre 32
episodios, a 15 mm del umbral. El banco encontró 270,6 sobre 24. La cola de la
distribución nominal es más larga de lo que 32 episodios de A mostraban — la
misma lección de v1, un nivel más arriba.

### 4.3 `repetition` — 1 de 24, derivada

La pareja perturbada del mundo `e6da9ac9` no puede comparar tiempos de
recuperación porque uno de los dos no recuperó. Su diferencia de RMS de hover
es 9,7 mm sobre una tolerancia de 230. No es un fallo independiente.

### 4.4 Qué no se ha tocado

No se ha movido ningún umbral, ni la fuerza, ni N, ni las bandas, ni un PID.
No se han repetido sólo los episodios fallidos. FLIGHT-1S **no** se declara
cerrado. Lo que un v3 tendría que resolver, dicho aquí y no aplicado:

- la permanencia de 3 s dentro de una ventana de 10 s deja poco margen cuando
  PX4 sobreoscila al volver; o la ventana crece, o la permanencia se mide sobre
  la primera entrada estable con un criterio explícito de reentrada;
- el umbral de desafío se compara contra una excursión nominal medida en una
  ventana de 10,6 s de *loiter*, cuya cola no está acotada por 32 episodios;
  medir la deriva nominal con muchas más muestras, o separar la ventana de
  control de la ventana de desafío.

Ambas exigirían protocolo v3 con hash nuevo, recalibración y banco completo.

---

## 5. Lo que v2 sí demostró

**El defecto de v1 está reparado y medido.** Las tres preguntas se separaron y
la que v1 confundía sale limpia:

```text
stimulus    24/24   wrench publicada exactamente una vez, retirada registrada,
                    impulso dentro de 500–1500 ppk
challenge   24/24   perturbados fuera de 250 mm      (fallo: 1 nominal, §4.2)
recovery    23/24   vuelta y permanencia             (fallo: 1, §4.1)
```

Ninguna pregunta paga por otra: el nominal que derivó no compensó nada, y el
episodio que no permaneció no fue salvado por tener un impulso perfecto.

Bajo el criterio v2, los dos episodios que v1 suspendió (389,4 y 291,7 mm)
superan el umbral de 250 mm, y el máximo nominal de v1 (195,4 mm) no lo
alcanza. Es una **consecuencia documentada** del umbral, no su motivo: el
umbral es radio más un margen derivado de resolución de muestreo, y hay un test
que fija esa consecuencia por escrito para que no se confunda con la razón.

| Grupo | Estado | Medido |
|---|---|---|
| `v1_preserved` | pass | código, protocolo, informe, trazas y ULog de v1 idénticos |
| `envelope` | pass | 12/12 mundos admiten la envolvente del X500 |
| `episodes` | pass | 48/48 armaron, despegaron, mantuvieron, aterrizaron y desarmaron |
| `stimulus` | pass | 24/24 |
| `challenge` | **fail** | 24/24 perturbados; 23/24 nominales |
| `recovery` | **fail** | 23/24 |
| `repetition` | **fail** | 23/24 parejas |
| `hygiene` | pass | 48/48 sin regresión de reloj ni contacto no autorizado; un lock y un protocolo |
| `controls` | pass | 4/4 |
| `mutants` | pass | 13/13 |
| `regression` | pass | NEXUS-0, SIM-3 y el banco unitario v1 |

Vuelo medido sobre los 48 episodios:

| Magnitud | n | min | p50 | max |
|---|---:|---:|---:|---:|
| Cociente de impulso, perturbado (ppk) | 24 | 876 | 956 | 1084 |
| Excursión perturbada (mm) | 24 | 397,4 | 525,1 | 697,9 |
| Excursión nominal (mm) | 24 | 74,7 | 143,2 | 270,6 |
| Tiempo de recuperación (ms) | 23 | 1.108 | 1.511 | 5.491 |
| Hover, error horizontal RMS (mm) | 48 | 35,1 | 65,8 | 99,9 |
| Actitud máxima perturbada (mdeg) | 24 | 12.120 | 12.659 | 13.045 |
| Velocidad lateral máxima (mm/s) | 24 | 1.272 | 1.407 | 1.528 |

La velocidad lateral máxima medida (1.528 mm/s) queda por debajo del techo de
1.500 mm/s declarado para derivar el margen en sólo dos episodios; el margen se
redondeó de 48 a 50 mm, así que el punto ciego real sigue cubierto. Se registra
como límite del cálculo, no como corrección.

### Controles

```text
config_carries_no_room_identity   24 configuraciones; sólo varían spawn_pose y condition
no_network_during_bench           TCP inalcanzable, DNS sin resolución
paired_nominal_vs_perturbed       el nominal se queda dentro, el perturbado sale y vuelve
world_hash_mismatch_refused       sdf_hash_mismatch antes de volar
```

### Mutantes

13 casos, cada uno desde un control positivo que cerró las tres preguntas:

```text
force_declared_without_wrench                stimulus suspende; el episodio vuela igual
wrench_accumulated                           publicaciones ≠ 1 / impulso fuera de banda
disturb_window_shifted                       impulso fuera de banda o wrench fuera de ventana
force_units_wrong                            impulso por encima del techo
never_left_the_band_but_claims_recovery      challenge suspende con recovery perfecta
recovery_scored_before_the_wrench_stopped    el esquema fija measured_from
pose_teleported_or_replayed                  sin firma PX4 y sin stimulus
fabricated_or_frozen_clock                   el episodio no completa
branch_by_split / ground_truth_as_setpoint   el inspector de configuración lo ve
asset_download_during_bench                  sin ruta fuera del contenedor
```

---

## 6. Auditoría independiente

```text
evidence_valid   true
checks           435
findings         []
recomputed       48 episodios
```

El auditor no lee `flight1s_green`. Regenera los doce mundos desde las semillas
publicadas, re-hashea las 48 trazas y los 48 ULog, y recalcula por su cuenta el
RMS de hover, la excursión, el cociente de impulso, la salida de banda y la
permanencia desde las muestras crudas; comprueba que la wrench se publicó una
vez y se retiró, reconstruye la permutación de condiciones desde la seed,
verifica el denominador de 48 con 24 por condición, y exige un solo lock y un
solo protocolo v2. Además comprueba que v1 sigue rojo, con sus bytes y su
hash, y que el margen y el suelo de impulso son los que las reglas producen.

`--self-test` muta copias del informe y exige que cada una sea rechazada,
partiendo de un control que aceptó:

```text
positive_control                 aceptado
impulse_altered_in_report        rechazado   recompute/…/impulse
exit_margin_relaxed_in_report    rechazado   protocol_challenge
impulse_floor_relaxed_in_report  rechazado   protocol_stimulus
omitted_red_episode              rechazado   episode_count
two_locks_across_episodes        rechazado   single_runtime_lock
v1_and_v2_protocols_mixed        rechazado   single_protocol
v1_code_reported_as_touched      rechazado   v1_code_unchanged
v1_red_reported_as_green         rechazado   supersedes_v1
rewritten_trace_hash             rechazado   trace_sha/…
rewritten_ulog_hash              rechazado   ulog_sha/…
green_without_groups             rechazado   flight1s_green_consistent
wrong_code_hash                  rechazado   code_sha256
```

---

## 7. Runtime

`lab/flight1s-v2/runtime-lock.json`,
`lock_sha256 = a8f6f0a8a5007a387f6bc7c5fe4712d85cc2c69554a56e13c2580af60c204ac5`,
`code_sha256 = 0c9615df6c0eb95272dae4fc8d6c27752bb544c27a3d4cbc6b86120d0f7f6be6`.
Imagen, PX4, modelos y contenedor son exactamente los de v1: PX4 `v1.15.4`
commit `99c40407…`, modelos `d754381a…`, gz-sim 8.15.0, imagen
`echoai-flight1s-px4:v1.15.4` `0911af28…`. Ningún PID tocado.
`--pull=never`, `--network=none`, sin descargas durante el banco.

---

## 8. Lo que esto no demuestra

- Software in the loop y nada más: ni aerodinámica realista, ni viento real, ni
  autonomía, ni seguridad universal, ni sim-to-real.
- Es una **reparación de un banco rehearsal** sobre doce mundos ya volados en
  v1, no un examen ciego de generalización.
- echoAI sigue desconectado: `agent_in_gazebo=false`, `cortex_calls=0`,
  `wsp_writes=0`. Ningún sensor simulado se publica como evidencia ni llega a
  WSP. Eso es SENSOR-1 y GROUND-1.
- PX4 conserva estabilización y mezcla; la interfaz de intención y los
  failsafes son PX4-1 y SAFE-1.
- El cociente de impulso es una diferencia finita del flujo de poses del
  backend, no un sensor de velocidad independiente, y el momento neto también
  refleja la reacción de PX4.
- La perturbación es una wrench constante. No es viento.
- Tiempos y RTF describen un host.
- `hardware_status="not_available"`.

---

## 9. Estado

FLIGHT-1S **sigue sin cerrar**. El defecto de medición de v1 está reparado y
demostrado: las tres preguntas se separan y los 24 perturbados pasan estímulo y
desafío. Lo que ahora bloquea son dos cosas nuevas y medidas — una permanencia
de 3 s que PX4 no sostuvo en 1 de 24 tras sobreoscilar, y una deriva nominal de
270,6 mm que cruza un umbral de 250 mm en 1 de 24. Ambas exigen un protocolo
v3, no un umbral movido. Los dos rojos, el de v1 y el de v2, se conservan.
