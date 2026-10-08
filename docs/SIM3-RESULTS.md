# SIM-3 — resultados medidos

**Estado: implementado y verde en un host.** Fecha: 2026-09-10.
Diseño: [SIM3-DESIGN.md](SIM3-DESIGN.md). Contrato superior:
[ECHO-3-ACCEPTANCE.md](ECHO-3-ACCEPTANCE.md).
Informe: `lab/echo3_sim3_report.json` ·
`report_sha256 = 2d4fc12df82a91d3d772e5e991950d0be8e989e9e43deb88764c8cb8f9a5f007`.
Auditoría: `lab/echo3_sim3_audit.json`.

Hashes de cierre de la corrida vigente:

| Artefacto | SHA-256 |
|---|---|
| Contenido lógico del informe, excluido su campo `report_sha256` | `2d4fc12df82a91d3d772e5e991950d0be8e989e9e43deb88764c8cb8f9a5f007` |
| Bytes de `lab/echo3_sim3_report.json` | `924ba5a86a0a45e4b9b787df56dbc17873ae55ec2244b71e5f0cc402459582b6` |
| Bytes de `lab/echo3_sim3_audit.json` | `73384363e2f0e0fee73021619ff21396c2defa38e74cd520fa21e9ed97c1c1a3` |
| Lock lógico de runtime | `80ef5a38853b6b92d4b21093857f7cda6d0a7966f259764475e3668604fdbf2a` |
| Bytes de `lab/sim3/runtime-lock.json` | `0491847fb2cc62a2ab0255d7f90c4f3cefa0b1cbb0662ab0eb59d04f950a19f6` |
| Inventario de código, 29 archivos | `00c4061af6cefabc511380706734f756cbef39deb90d3ef7b3a81b6895752346` |

Este documento dice lo que se midió. Lo que SIM-3 **no** mide está en §7 y en
el campo `limitations` del informe; no se resume aquí en positivo.

---

## 1. Qué se ejecutó

```bash
cd /home/roger/REALRXOS/RXos/echoai

PYTHONPATH=.. python3 -m echoai.nexus0.sim3 validate \
    --package docs/examples/sim3 --protocol docs/examples/sim3/protocol.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 preflight \
    --output lab/sim3/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 bench --rehearsal \
    --output lab/echo3_sim3_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 audit lab/echo3_sim3_report.json

PYTHONPATH=.. python3 tests/test_sim3.py            # 44 tests, sin backend
PYTHONPATH=.. python3 tests/test_sim3_backend.py    # 9 tests, con backend
```

`bench` exige el lock congelado antes de medir y se niega a correr si el código
ha cambiado desde que se congeló (`lock_stale`). Devuelve 0 sólo si
`sim3_green` es cierto; `audit` devuelve 0 sólo si la evidencia reconstruye
**y** el informe era verde.

Salidas reales:

```text
preflight exit=0
bench exit=0        # 624,8 s de reloj de pared
audit exit=0
tests/test_sim3.py          Ran 44 tests in 71.583s  OK
tests/test_sim3_backend.py  Ran  9 tests in 85.579s  OK
```

`validate` sobre el ejemplo público:

```json
{
  "valid": true,
  "protocol_sha256": "b3be07e1d4933a716fce9207bfdda33dcc799ec413e5f749c56b859ab86f6c45",
  "package": {
    "sdf_sha256": "341c928d85251615b01878a9172d8bd4e7bf971986f7e40b438929471836ddab",
    "manifest_sha256": "facfe60ff0db8306f9801a0b67d336986b381b42d394b09e77c895ae2281edb2",
    "package_sha256": "b698df43a65257a2d6307663aca8cf8e09a2ec5ecab643e613d04daf118e3822",
    "fingerprint_sha256": "18c2efb91a497d2f12725ce563bd0a7e60e13a4913278fa89f90cdbb5b62a1f4",
    "n_models": 3, "n_barriers": 1
  },
  "roles": {"m0": "floor", "m1": "barrier", "m2": "charging_station"},
  "spawn_mm": [-3000, 0, 1000],
  "rig_start_mm": [-3000, 0, 1000],
  "approach_mm": [3000, 0, 550],
  "connectivity_attach_nodes": [125, 50],
  "libsdformat": {"tool": "gz sdf -k (libsdformat)", "returncode": 0,
                  "valid": true, "output": "Valid."}
}
```

---

## 2. Runtime realmente usado

`lab/sim3/runtime-lock.json`,
`lock_sha256 = 80ef5a38853b6b92d4b21093857f7cda6d0a7966f259764475e3668604fdbf2a`,
`code_sha256 = 00c4061af6cefabc511380706734f756cbef39deb90d3ef7b3a81b6895752346`
(29 archivos: los módulos de `nexus0/sim3/`, los tres assets, el
`Containerfile` y los cinco esquemas).

Esta es la segunda corrida. La primera cerró igual de verde bajo el lock
`2da89991…` / código `9880e579…`; la capa de manifiestos y runners de
[SIM3-RUNNERS.md](SIM3-RUNNERS.md) cambió el inventario de código, así que el
banco se repitió entero bajo lock nuevo en vez de reetiquetar aquel verde. Las
medidas de física coinciden dígito a dígito entre las dos corridas.

| Pieza | Versión |
|---|---|
| Host | Fedora Linux 43, kernel 7.1.4-100.fc43.x86_64, x86_64, Python 3.14.6 |
| Contenedor | `localhost/echoai-sim3-gz:harmonic`, imagen `97893d2e96e6…`, base `ubuntu:24.04@sha256:a61567bd…` |
| Simulador | gz-sim 8.15.0 (`libgz-sim8 8.15.0-1~noble`, `gz-sim8-cli` ídem) |
| SDF | `libsdformat14 14.9.0-1~noble` |
| Física | `libgz-physics7-dartsim 7.8.0-1~noble` |
| Transporte | `libgz-transport13 13.6.0-1~noble`, `libgz-msgs10 10.4.0-1~noble` |
| Bindings | `python3-gz-sim8`, `python3-gz-transport13`, `python3-gz-msgs10`, Python 3.12.3 |
| Sandbox | bubblewrap 0.11.0 |

`--pull=never` en todas las invocaciones y `GZ_FUEL_STATIC_ONLY=1` en la
imagen: el banco no descarga nada. `latest` no aparece en ningún sitio. Una
plataforma distinta exige lock nuevo y repetición del banco; el auditor
rechaza un informe cuyas ejecuciones no citen todas el mismo lock.

---

## 3. Los diez grupos

Todos en `pass`; `sim3_green=true`.

| Grupo | Medido |
|---|---|
| `packages` | 12/12 validan con el validador propio y con `gz sdf -k` real |
| `distinction` | 3 bases no equivalentes bajo traslación, reflexión y giros de 90°; 12 huellas distintas; 12/12 reproducibles regenerando en orden inverso |
| `physics` | 24/24 avanzan 1.000 pasos con reloj leído del backend |
| `repetition` | 12/12 parejas: mismo hash del SDF efectivo y 0,000 mm de diferencia en pose final (criterio ≤2 mm) |
| `isolation` | 24/24: 22 accesos prohibidos denegados, 1.001 ticks entregados, 0 canarios visibles |
| `rename` | 12/12: huella idéntica, transcript de ticks idéntico, 0 µm de diferencia en pose final, bytes del SDF distintos |
| `moved_wall` | 12/12: huella y bytes cambian, la entidad se mueve 500,000 mm en el backend, la esfera reposa sobre el muro y no sobre el suelo, transcript idéntico |
| `sealing` | 10/10 comprobaciones de compromiso, derivación, apertura única, reapertura, crash, exclusión mutua e inventario |
| `mutants` | 26 casos: 3 controles positivos, 22 mutantes que fallan cada uno por su causa, 1 puntero al auditor |
| `regression` | `echoai.tests.test_nexus0` en verde, `returncode=0` |

### 3.1 Física

En las 24 ejecuciones principales, con el rig soltado en la columna libre
verificada por el evaluador:

```text
caída a 200 ms      197,181 mm      criterio 150–250 mm
error en reposo       1,206 mm      criterio ≤10 mm
primer contacto     441 ms          par sim3_rig::body::solid / m<floor>::body::solid
mensajes de contacto    560         sensor de contacto del rig
gravedad del backend  0 0 -9,81 m/s²  leída del ECM, no del archivo
frames                1000 + 1 tick inicial = 1001
```

Los 24 valores de caída y de error en reposo son idénticos porque la columna
del rig está libre en los doce mundos: esta prueba certifica que el backend
corrió y que la esfera cayó y tocó, **no** que los mundos difieran. La
diferencia geométrica la certifican `distinction` y `moved_wall`.

`repetition` da 0,000 mm: en este host y bajo este lock la física repite
exactamente. Es más fuerte que el criterio de 2 mm y no se extiende a otras
plataformas; SIM-3 no afirma identidad bit a bit entre hosts.

### 3.2 Pared movida

Ejemplo del primer par (los doce se comportan igual):

```text
desplazamiento           +500 mm en x
pose de entidad          delta 500000 µm en x, 0 en y, 0 en z   (leída del ECM)
reposo sobre el muro   2 649 638 µm   esperado 2 650 000 µm
reposo en el original     48 941 µm   esperado    50 000 µm
transcript de ticks     idéntico al del mundo original
```

La sonda de colisión suelta el rig sobre la columna de la barrera desplazada
en los dos mundos. En el mundo movido la esfera se detiene sobre el muro; en
el original cae al suelo. Es colisión del backend, no lectura del SDF.

### 3.3 Aislamiento

El consumidor corre bajo bubblewrap con espacios de nombres propios de
usuario, IPC, PID, red, UTS y cgroup; `/usr` de sólo lectura, `/work` en
tmpfs, el resto remontado de sólo lectura, y `--as-pid-1` para que PID 1 sea
el propio consumidor. `argv` y `env` son los mismos en A, B y C:

```text
argv          ["/probe/probe.py"]                      (exec: /usr/bin/python3 /probe/probe.py)
env           HOME=/work LANG=C.UTF-8 PATH=/usr/bin PWD=/work
hostname      sim3
cwd           /work
raíz visible  bin dev lib lib64 probe proc sbin usr work
procesos      1
```

En cada ejecución el probe intenta y se le deniega: `/home`, `/home/roger`,
`/root`, `/var`, `/var/tmp`, `/run`, `/run/user`, `/etc`, `/etc/passwd`,
`/etc/shadow`, `/sys/class/net`; escrituras en `/`, `/probe`, `/usr` y
`/proc` (EROFS); TCP a 127.0.0.1:11345, :11317 y :8080; multicast UDP de
descubrimiento de gz; y sockets UNIX de D-Bus y X11. 22 denegaciones por
ejecución, 24 de 24.

Lo que sí puede leer es su propio espacio de nombres, y el evaluador
comprueba que esté vacío: `/proc/1/cmdline` es su propio comando,
`/proc/1/environ` sólo tiene las cuatro variables de la lista, `/proc/net/tcp`
y `/proc/net/unix` sólo la cabecera, `/dev/shm` vacío.

Tres canarios privados distintos por ejecución —uno en el entorno del
contenedor de Gazebo, uno en su argv y uno en un archivo privado— no aparecen
en nada de lo que el consumidor ve. El probe no sabe cuáles son: informa lo
que ve y decide el evaluador.

Hallazgo real durante la implementación, corregido y por eso registrado: sin
`--as-pid-1`, PID 1 dentro de la jaula era el propio `bwrap` y su
`/proc/1/cmdline` entregaba al consumidor la ruta absoluta del repositorio y
el entorno del operador. Sin `--remount-ro /`, el consumidor podía escribir
en `/` y `/probe`. Ambas fugas las detectó el probe adversarial, no una
inspección de clases.

### 3.4 Mutantes

De paquete, cada uno desde un control positivo que validó:
`sdf_hash_changed → sdf_hash_mismatch`, `role_nonexistent →
roles_model_absent`, `role_missing → roles_model_unassigned`, `role_duplicate
→ roles_duplicate_model`, `json_duplicate_key → json_duplicate_key`,
`seed_split_leaked → manifest_schema`, `remote_include →
sdf_unsupported_element`, `plugin_injected → sdf_unsupported_element`,
`xml_dtd → sdf_doctype`, `symlink_out_of_package → package_symlink_entry`,
`spawn_inside_solid → spawn_inside_solid`, `world_over_1mib → sdf_too_large`,
`goal_unreachable → goal_unreachable`, y una copia renombrada que conserva la
huella y cambia los bytes.

De ejecución, desde una sesión de control que sí cerró:
`backend_disconnected → backend_no_ready` con 0 ticks emitidos;
`stats_without_advance → clock_not_monotonic` (un backend real cuyo reloj se
congela); `sandbox_failure → sandbox_unavailable`; consumidor abusivo con
campo extra, mensaje sobredimensionado y secuencia equivocada →
`ack_mismatch`, consumidor mudo → `ack_timeout`, y en los cuatro casos ninguna
entidad nueva aparece en el mundo; y un tick al que el supervisor añade
`split` y `seed` → el consumidor lo rechaza con `unexpected_fields` y la
sesión muere.

### 3.5 Sellado

Con el secreto público de ensayo de 32 bytes `0x01`:

```text
compromiso del protocolo  aea59bf8d1fa915a01ffb9f8fdd209a765d3607b4d648e27b68d0534c67e3b66
                          = SHA256(b"SIM3/v1/commit\0" + digest + secreto)
derivación de semillas    HMAC-SHA256, 12 semillas distintas en A/B/C
inventario                compromiso con salt de 32 bytes 0x02, 12 entradas
sealed → opened → consumed, reapertura rechazada  (seal_already_consumed)
crash tras abrir → queda consumed                 (seal_crash_consumed)
dos procesos abriendo a la vez → rechazado        (seal_busy)
inventario alterado → detectado                   (inventory_mismatch)
```

El secreto es público a propósito: prueba la maquinaria y no prueba nada sobre
custodia. **No existe ninguna partición C de campaña en este árbol y no se ha
abierto ninguna.** Un hash no es custodia: el registro de accesos y el
custodio viven fuera de este repositorio.

---

## 4. Auditoría independiente

```text
evidence_valid   true
checks           416
findings         []
recomputed_runs  24
```

El auditor no lee `sim3_green`. Regenera los doce paquetes desde las semillas
públicas, comprueba que los `package_sha256` y las huellas del informe son los
suyos, re-hashea las 72 trazas, y recalcula por su cuenta caída, error en
reposo, número de frames, ticks y contactos de las 24 ejecuciones principales
antes de compararlos con lo declarado. Después verifica el compromiso del
protocolo, el inventario de código y que el lock del disco sea el que el
informe cita.

`--self-test` muta copias del informe y exige que cada una sea rechazada,
partiendo de un control positivo que aceptó:

```text
positive_control              aceptado          (sin este, lo de abajo no prueba nada)
flipped_case_result           rechazado         recompute/…/verdict, group_consistency/physics
bumped_contact_counter        rechazado         recompute/…/n_contact_msgs
rewritten_trace_hash          rechazado         trace_sha/…
different_runtime_lock        rechazado         lock_matches_report
one_world_on_another_runtime  rechazado         single_runtime_lock
green_without_groups          rechazado         sim3_green_consistent
altered_measurement           rechazado         recompute/…/fall_mm
wrong_protocol_hash           rechazado         protocol_sha256
wrong_code_hash               rechazado         code_sha256
```

Cada mutante re-sella el `report_sha256`, como haría quien manipulase el
informe de verdad: reescribir informe y hash a la vez no equivale a evidencia.

---

## 5. Métricas descriptivas

Sobre las 24 ejecuciones principales, en este host:

| Magnitud | min | p50 | max |
|---|---:|---:|---:|
| Lanzamiento (s) | 0,402 | 0,417 | 0,439 |
| RTF (s sim / s reloj) | 0,300 | 0,305 | 0,308 |
| Latencia ACK p50 (ms) | 0,197 | 0,204 | 0,212 |
| Latencia ACK p99 (ms) | 0,282 | 0,317 | 0,355 |
| RSS máx. Gazebo (KiB) | 115 864 | 119 276 | 122 516 |
| RSS máx. supervisor (KiB) | 34 228 | 34 228 | 34 228 |
| RSS máx. consumidor (KiB) | 11 496 | 11 752 | 11 752 |

1.001 muestras de latencia por ejecución. Son descriptivas: 24 ejecuciones en
una máquina no prometen una cola P99 estable, no miden ventaja edge y no
permiten hablar de julios. El RTF de 0,3 es el coste del lockstep de un paso
por tick a través de dos tuberías y un socket, no un límite del simulador.

Episodios totales: 72 (24 principales + 12 renombrados + 12 con pared movida +
24 sondas de colisión). Los pares metamórficos y las sondas no entran en el
conteo de las 24 principales ni en la tabla de arriba.

---

## 6. Cómo está construido

```text
Custodio (Roger)   protocolo, partición, secretos     — fuera de este árbol
        │
Supervisor (host)  paquete privado, SDF efectivo, canarios
        │
        ├── podman --network=none --read-only --pull=never
        │     └── gzrunner.py  ← único proceso que habla con Gazebo
        │           lockstep: un paso por petición; devuelve sim_time y pose
        │
        └── bwrap --unshare-{user,ipc,pid,net,uts,cgroup} --remount-ro / --as-pid-1
              └── probe.py     ← consumidor: stdin/stdout = socket, stderr = informe
                    recibe {"v":1,"seq":n,"sim_time_ns":t} y responde {"v":1,"ack":n}
```

El supervisor no tiene ninguna rama que dependa de la sala, la semilla o la
partición: `session.py`, `sandbox.py` y `rig.py` no mencionan `split`, `seed`
ni `package_id` en ninguna decisión. El tick cabe en 256 bytes y lleva tres
campos; si Gazebo no arranca o deja de avanzar no hay tick que enviar, porque
no existe camino de código que fabrique uno.

El SDF fuente es datos y el SDF efectivo lleva código: se validan con puertas
distintas y se hashean por separado. El perfil `sim3-boxes-v1` rechaza el SDF
efectivo, y hay un test que lo comprueba.

---

## 7. Lo que esto no demuestra

Del campo `limitations` del informe, sin suavizar:

- Sólo infraestructura: no hay vuelo, sensores, WSP desde física, aprendizaje
  ni córtex. `agent_in_gazebo=false`, `cortex_calls=0`.
- El consumidor es un probe instrumental, no un agente cognitivo.
- El aislamiento cubre fugas accidentales y accesos directos del probe. No es
  una afirmación sobre escapes de kernel ni sobre canales laterales
  temporales.
- Contacto y caída prueban gravedad y colisión. No prueban aerodinámica ni
  nada sobre un X500.
- El tick inicial lleva el tiempo del backend en su primer `pre_update` menos
  un paso, verificado como exactamente `step_ns`; los otros 1.000 llevan un
  tiempo leído del backend.
- La conectividad es un flood fill discreto de 100 mm sobre AABB inflados, no
  una garantía de navegación continua segura.
- 24 ejecuciones en un host describen latencia y RTF; no prometen P99 ni
  energía.
- `rehearsal-C` es un ensayo con secreto publicado: no es evidencia reservada
  y no consume ningún examen de campaña.
- No se afirma identidad bit a bit de la física entre hosts.
- `hardware_status="not_available"`. No hay AKD1000 ni AKD1500 en el
  laboratorio.

---

## 8. Dependencias del núcleo que SIM-3 no ha tocado

Siguen abiertas, tal como las dejó el diseño:

- `nexus0/loop.py:Agent` consume `env.cell()` y `Cell.kind`. Entregarle un
  wrapper del mundo expondría verdad global; `SDF → Cell(kind=GOAL)` no se
  admite como percepción. Queda para GROUND-1.
- `greedy=True` evita exploración pero `Agent.turn()` sigue actualizando T/Q y
  puede crear memoria/PATTERN: no equivale a congelar aprendizaje. Queda para
  TRANSFER-3.
- La configuración vital actual impide combinar planificación y supervivencia.
  Queda para COMPOSE-1.

Ninguna de las tres se ha corregido aquí, ni a escondidas ni de frente.

---

## 9. Relevo

Manifiestos y runners cerrados: [SIM3-RUNNERS.md](SIM3-RUNNERS.md).
Siguiente tajo software: FLIGHT-1S. Relevo para Claude Opus 5:
[GPT-OPUS5-FLIGHT1S-PROMPT.md](GPT-OPUS5-FLIGHT1S-PROMPT.md).
