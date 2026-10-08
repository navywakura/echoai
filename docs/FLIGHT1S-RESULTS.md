# FLIGHT-1S — resultados medidos

> **Nota añadida el 2026-09-10, después de v2.** Nada de este documento se ha
> alterado: sus afirmaciones, sus hashes y su veredicto rojo son los de la
> corrida original, y `lab/echo3_flight1s_report.json` sigue reconstruyendo con
> 375 comprobaciones y cero hallazgos. El defecto de medición descrito en §4 se
> reparó en un protocolo aparte, con hash, lock, informe y evidencia propios:
> [FLIGHT1S-V2-DESIGN.md](FLIGHT1S-V2-DESIGN.md) y
> [FLIGHT1S-V2-RESULTS.md](FLIGHT1S-V2-RESULTS.md). v2 también salió rojo, por
> dos causas nuevas y distintas.

**Estado: ROJO. El banco se ejecutó entero y no cierra.**
Fecha: 2026-09-10.
Diseño: [FLIGHT1S-DESIGN.md](FLIGHT1S-DESIGN.md). Relevo:
[GPT-OPUS5-FLIGHT1S-PROMPT.md](GPT-OPUS5-FLIGHT1S-PROMPT.md).
Informe: `lab/echo3_flight1s_report.json` ·
`report_sha256 = 57ccea7f19ebc3b3851abe6faf9c5f1a25365be1f6181291c8e748414944e809`.
Auditoría: `lab/echo3_flight1s_audit.json`.

Ocho de los nueve grupos preregistrados están en verde y los 48 episodios
volaron completos. **`flight1s_green=false`** porque el grupo `disturbance`
falla en 2 de 24 episodios perturbados. El rojo se conserva; §4 dice qué
variable concreta lo impide y qué haría falta, sin tocarla.

---

## 1. Qué se ejecutó

```bash
cd /home/roger/REALRXOS/RXos/echoai

PYTHONPATH=.. python3 -m echoai.nexus0.flight1s validate                                   # exit 0
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s preflight --output lab/flight1s/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --rehearsal --output lab/echo3_flight1s_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit lab/echo3_flight1s_report.json

PYTHONPATH=.. python3 tests/test_flight1s.py           # 24 tests, sin backend
PYTHONPATH=.. python3 tests/test_flight1s_backend.py   # 13 tests, con PX4 real
```

Salidas reales:

```text
preflight exit=0
bench     exit=1        # 3.807,2 s de reloj de pared, flight1s_green=false
audit     exit=1        # evidence_valid=true, pero el informe era rojo
tests/test_flight1s.py          Ran 24 tests in  39.4s  OK
tests/test_flight1s_backend.py  Ran 13 tests in 215.7s  OK
```

`bench` exige el lock congelado antes de medir y se niega con `lock_stale`
si el código cambió desde que se congeló. `audit` devuelve 0 sólo si la
evidencia reconstruye **y** el informe era verde; aquí reconstruye y el
informe es rojo, así que devuelve 1. Son dos hechos distintos y el código
los separa.

---

## 2. Runtime realmente usado

`lab/flight1s/runtime-lock.json`,
`lock_sha256 = d41c76a0d8d739cba690c21c3681a27ff223a9a4f516e0de16f2191607e2d818`,
`code_sha256 = c4dd8fdb6f4f7dbcfb4e473f6ae8464a86def6cf58ba7dce0b0cf08b7ee3102c`.

| Pieza | Fijación real |
|---|---|
| Autopiloto | PX4-Autopilot `v1.15.4`, commit `99c40407ffd7ac184e2d7b4b293f36f10fe561ef` |
| Modelos | `PX4/PX4-gazebo-models` `d754381a1cecdd7f17050acd72bf5bf1327bced6` |
| Binario PX4 | `px4_sitl_default`, SHA-256 `05bc7c4cb8d882e93cb8743c24e9f1ee6a94aab2acb6657a1e340ca63600b6b9` |
| Cuerpo | `x500` → `x500_base`, `base_link` 2,0 kg + 4 rotores de 16,077 g = 2,064 kg |
| Assets del cuerpo | `x500/model.sdf` `76d8668c…`, `x500_base/model.sdf` `f0f04e43…`, airframe `4001_gz_x500` `4ffa85e8…` |
| Simulador | gz-sim 8.15.0, libsdformat 14.9.0, DARTsim 7.8.0 (imagen SIM-3 sin tocar) |
| Imagen | `echoai-flight1s-px4:v1.15.4` `0911af28…`, **FROM** `echoai-sim3-gz:harmonic` `97893d2e…` |

Composición, no sobrescritura: el lock de SIM-3 y su informe siguen intactos y
reproducibles. `--pull=never`, `--network=none` y `GZ_FUEL_STATIC_ONLY=1` en
todos los episodios; el control de red lo comprueba desde dentro del propio
contenedor de episodio (§5).

---

## 3. Calibración en A, publicada entera

La magnitud de la perturbación y las bandas son lo único que se elige en vez
de declararse, así que se eligieron sólo en split A, con reglas fijadas
**antes** de correr:

- radio de recuperación = `ceil(máximo horizontal del hover nominal en A, 50 mm)`;
- una fuerza admisible debe empujar el cuerpo por encima de 2 × ese radio **en
  los cuatro mundos A** y no pasar de 25° de actitud;
- entre las admisibles, la más pequeña.

Ronda 1 (1–4 N) — `lab/flight1s/sweep-round1-1to4N.json`, **conservada en rojo**:

| F (mN) | admisible | excursión mín..máx (mm) | actitud máx (mdeg) | impulso (ppk) |
|---:|---|---|---:|---|
| 1000 | no | 118,4 .. 156,4 | 2 975 | 1116, 890, 1014, 867 |
| 2000 | no | 170,6 .. 300,3 | 5 050 | 978, 1054, 980, 962 |
| 3000 | no | 264,9 .. 387,7 | 7 847 | 930, 936, 877, 990 |
| 4000 | no | 303,1 .. 529,9 | 10 567 | 1001, 892, 1007, 933 |

Ninguna admisible: ni 4 N movía el mundo A más tranquilo más de 303 mm, por
debajo de 2 × 200 mm. **No se tocó la regla**; se amplió el rango de
candidatos y se conservó la ronda 1. Ronda 2 (5–8 N), en
`lab/flight1s/sweep.json`:

| F (mN) | admisible | excursión mín..máx (mm) | actitud máx (mdeg) | impulso (ppk) |
|---:|---|---|---:|---|
| 5000 | **sí** | 455,3 .. 596,5 | 12 816 | 1069, 903, 954, 941 |
| 6000 | sí | 613,7 .. 679,2 | 15 406 | 916, 987, 906, 916 |
| 8000 | sí | 816,1 .. 869,4 | 19 720 | 909, 930, 923, 1007 |

Elegida la más pequeña: **5 000 mN durante 600 ms**. 36 episodios de A en
total. Protocolo congelado en
[protocol.json](examples/flight1s/protocol.json),
`sha256 = ac1db6f9abf849f96ee3671e73ce63c116d62a43dc4d9c5184c4598e65c98229`,
con `order_seed = 20260910`. Ese hash es el freeze: el auditor rechaza un
informe cuyas bandas no coincidan con esos bytes.

---

## 4. El rojo

```text
grupo disturbance: FAIL  — 22 de 24 episodios perturbados cumplen
  perturbed-73e0dcb3241663a5-r1   excursión 389,4 mm   (mínimo 400)   impulso 963 ppk
  perturbed-ef7f22a49738b970-r2   excursión 291,7 mm   (mínimo 400)   impulso 957 ppk
```

En los dos episodios **la fuerza sí se aplicó**: una sola publicación de
wrench y un cociente de impulso de 963 y 957 por mil, indistinguible del
resto. Lo que no alcanzó el suelo preregistrado fue el desplazamiento, porque
PX4 rechazó el empujón mejor en esos dos vuelos.

La variable concreta que impide cerrar es
`bands.min_disturb_excursion_mm = 400`. Es un criterio de **suficiencia del
estímulo** — existe para que la prueba no sea vacía — pero está redactado
sobre un resultado de lazo cerrado: la fuerza es abierta y constante, y la
excursión es lo que queda después de que el controlador reaccione. Un
controlador mejor produce una excursión menor y por tanto acerca el estímulo a
su propio suelo.

El muestreo de A también lo subestimó: cuatro episodios por nivel dieron una
excursión mínima de 455 mm a 5 N; los 24 episodios del banco completo bajaron
a 291,7 mm. n=4 no acotaba la dispersión.

**No se ha cambiado el umbral, ni la fuerza, ni N, ni las bandas.** Cualquier
corrección exige un protocolo v2 con hash nuevo, una recalibración y el banco
completo otra vez; esta evidencia se conserva. Lo que un v2 tendría que
arreglar, dicho aquí y no aplicado: expresar la suficiencia del estímulo sobre
la magnitud **aplicada** (impulso medido, que fue 874–1008 ppk en las 24) en
vez de sobre el desplazamiento resultante, y calibrar con más de cuatro
episodios por nivel.

Separación medida entre condiciones, que sí es limpia:

```text
excursión nominal      n=24   92,0 .. 195,4 mm
excursión perturbada   n=24  291,7 .. 694,3 mm
hueco entre ambas                    96,3 mm, sin solape
```

---

## 5. Lo que sí quedó demostrado

Ocho grupos en verde, 48/48 episodios completos.

| Grupo | Medido |
|---|---|
| `envelope` | 12/12 mundos SIM-3 admiten la envolvente del X500; margen de pared peor caso 2 500 mm |
| `episodes` | 48/48 arman, despegan, mantienen la referencia, aterrizan y desarman |
| `recovery` | 24/24 perturbados vuelven a 200 mm de la referencia y aguantan 3 s; 894 .. 6 154 ms, mediana 1 412 ms |
| `repetition` | 24/24 parejas dentro de las tolerancias congeladas, con el mismo SDF efectivo |
| `hygiene` | 48/48 sin regresiones de reloj, sin contacto no autorizado, aterrizadas a ≤10 mm de su pose de reposo, firma PX4 presente, un solo lock |
| `controls` | 4/4 |
| `mutants` | 9/9 |
| `regression` | bancos NEXUS-0 y SIM-3 en verde |

Vuelo medido sobre los 48 episodios:

| Magnitud | min | p50 | max |
|---|---:|---:|---:|
| Hover, error horizontal RMS (mm) | 34,7 | 63,2 | 130,8 |
| Hover, error horizontal máx (mm) | 53,8 | 121,4 | 211,5 |
| Hover, error vertical máx (mm) | 42,7 | 104,3 | 276,2 |
| Desvío de altitud respecto a la referencia (mm) | −444,1 | −39,0 | +468,1 |
| Excursión perturbada (mm) | 291,7 | 497,9 | 694,3 |
| Cociente de impulso perturbado (ppk) | 874 | 957 | 1008 |
| Tiempo de recuperación (ms) | 894 | 1 412 | 6 154 |
| Actitud máxima perturbada (mdeg) | 12 158 | 12 634 | 13 182 |
| Frecuencia efectiva de muestreo (Hz) | 46,8 | 46,9 | 46,9 |
| P99 de hueco entre muestras (ms) | 22 | 22 | 23 |
| Reloj de pared por episodio (s) | 52,7 | 55,7 | 58,6 |
| RTF | 0,802 | 0,819 | 0,832 |

El desvío de altitud de ±450 mm respecto a la referencia de 1,5 m es real y se
publica tal cual: es la altitud que EKF2 sostiene con el barómetro y el navsat
simulados de este SITL. La estabilidad *alrededor* de donde se queda es otra
cosa y es buena (RMS horizontal de 63 mm mediano). Las dos se miden por
separado a propósito, para que un sesgo no se esconda dentro de una dispersión.

### Que la fuerza fue física, no declarada

Tres vías independientes, y la tercera es la que decide:

1. una sola publicación de wrench por episodio, sobre `x500_0::base_link`;
2. el cambio de momento del cuerpo medido en el flujo de poses del backend
   contra `F·Δt`: **874–1008 por mil** en los 24 episodios;
3. el mutante que declara la fuerza y nunca publica el wrench: **15 por mil**
   frente a 913 de su control positivo. Un factor de sesenta.

### Controles

```text
config_carries_no_room_identity   24 configuraciones; sólo varían spawn_pose y condition
no_network_during_bench           TCP "Network is unreachable", DNS "Temporary failure"
paired_nominal_vs_perturbed       101,9 mm frente a 524,9 mm en el mismo mundo y guion
world_hash_mismatch_refused       sdf_hash_mismatch antes de que vuele nada
```

### Mutantes

Cada uno desde un control positivo que voló:

```text
pose_teleported_or_replayed        sin ulog, sin armado, sin cambio de modo -> rechazado
fixture_controller_labelled_as_sitl  misma firma ausente -> rechazado
force_declared_without_wrench      impulso 15 ppk frente a 913 del control
fabricated_or_frozen_clock         el episodio no puede completarse: episode_timeout
branch_by_split                    el inspector de configuración lo ve
ground_truth_as_setpoint           idem, con station_mm
asset_download_during_bench        URLError: no hay ruta fuera del contenedor
positive_control_episode           vuela y se mide
report_level_mutants               los comprueba el auditor
```

---

## 6. Auditoría independiente

```text
evidence_valid   true
checks           375
findings         []
recomputed       48 episodios
```

El auditor no lee `flight1s_green`. Regenera los doce mundos desde las
semillas publicadas, re-hashea las 48 trazas y los 48 ulogs de PX4, recalcula
por su cuenta el RMS del hover, el desvío de altitud, la excursión, el
cociente de impulso y el estado de recuperación desde las muestras crudas,
reconstruye la permutación de condiciones desde `order_seed`, y comprueba que
el denominador sea 48 con 24 por condición y 4 por mundo.

`--self-test` muta copias del informe y exige que cada una sea rechazada,
partiendo de un control que aceptó:

```text
positive_control                aceptado
omitted_red_episode             rechazado   episode_count, episodes_per_condition
relaxed_band_in_report          rechazado   protocol_bands
two_locks_across_episodes       rechazado   single_runtime_lock
rewritten_trace_hash            rechazado   trace_sha/…
rewritten_ulog_hash             rechazado   ulog_sha/…
altered_measurement             rechazado   recompute/…/hover_horiz_rms_mm
green_without_groups            rechazado   flight1s_green_consistent
condition_order_rewritten       rechazado   condition_order_from_seed
wrong_code_hash                 rechazado   code_sha256
```

Un informe rojo con evidencia perfectamente reconstruible es exactamente el
aspecto de un fallo honesto.

---

## 7. Cómo está construido

```text
supervisor (host)   mundo efectivo, pose de spawn, guion congelado, orden por seed
      │  un contenedor por episodio, --network=none --pull=never
      ▼
  flightrunner.py   único proceso que habla con Gazebo y con PX4
      ├── gz sim -s -r --headless-rendering  (mundo SIM-3 + sistemas fijos)
      ├── PX4 SITL con PX4_GZ_STANDALONE=1: crea su propio cuerpo por el backend
      └── driver MAVLink: MIS_TAKEOFF_ALT, AUTO.TAKEOFF, armar, aterrizar, desarmar
```

Lo único que varía entre los 24 configs que cruzan al contenedor es
`spawn_pose` —la columna libre validada del propio mundo— y `condition`, la
variable manipulada. Ni split, ni seed, ni `package_id`, ni roles, ni estación.

PX4 estabiliza y mezcla actuadores; el driver sólo fija la referencia. Dos
hallazgos de implementación, registrados porque costaron episodios:

- sin `<magnetic_field>` en el mundo, PX4 simula su magnetómetro sobre un campo
  que no existe, EKF2 se queda sin referencia de rumbo y el cuerpo arma y se
  desarma solo diez segundos después con «Yaw estimate error». El valor es el
  de PX4 y es idéntico en los doce mundos;
- `MAV_CMD_NAV_TAKEOFF` a secas se acepta y no despega en esta build. Lo que
  manda el despegue es el cambio a `AUTO.TAKEOFF` seguido del armado;
- `/world/<w>/wrench/persistent` **suma** una wrench por mensaje. Publicarla en
  el bucle de muestreo acumulaba kilonewtons y lanzaba el cuerpo 54 m. Se
  publica exactamente una vez y se limpia al cerrar la ventana.

El mundo fuente es dato y la copia de ejecución lleva código: se hashean por
separado, y el perfil `sim3-boxes-v1` rechaza la copia efectiva. Los bytes de
los doce paquetes SIM-3 no se han tocado.

---

## 8. Lo que esto no demuestra

- Software in the loop y nada más: no hay aerodinámica realista, viento real,
  autonomía, seguridad universal ni sim-to-real.
- echoAI está desconectado: `agent_in_gazebo=false`, `cortex_calls=0`,
  `wsp_writes=0`. Ningún sensor simulado se publica como evidencia ni se
  traduce a WSP. Eso es SENSOR-1 y GROUND-1.
- PX4 conserva estabilización y mezcla; la interfaz de intención y los
  failsafes son PX4-1 y SAFE-1.
- La velocidad, y por tanto el impulso, es una diferencia finita del flujo de
  poses del backend, no un sensor de velocidad independiente.
- La perturbación es una wrench constante. No es viento y no afirma nada
  atmosférico.
- Los mundos son los paquetes rehearsal de SIM-3, revalidados para la
  envolvente. Son datos públicos de ensayo y no consumen ningún examen
  reservado; no existe C de campaña en este árbol.
- Tiempos y RTF describen un host. No son energía ni autonomía.
- `hardware_status="not_available"`: no hay aeronave y no hay Akida.

---

## 9. Estado

FLIGHT-1S **no cierra**. Ocho grupos en verde, 48 episodios volados, evidencia
auditada y reconstruible, y un criterio preregistrado incumplido en 2 de 24
episodios. Para cerrarlo hace falta un protocolo v2 con hash nuevo, una
recalibración con más episodios por nivel y el banco completo repetido — no
un umbral movido.
