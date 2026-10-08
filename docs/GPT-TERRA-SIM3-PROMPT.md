# Prompt de relevo para GPT Terra — manifiestos y runners sobre SIM-3

**Estado del tajo anterior:** SIM-3 implementado y verde en un host.
**Fecha:** 2026-09-10.
**Origen:** implementación de Claude Opus 5 conforme a
[SIM3-DESIGN.md](SIM3-DESIGN.md) y [CLAUDE-SIM3-PROMPT.md](CLAUDE-SIM3-PROMPT.md).
**Resultados medidos:** [SIM3-RESULTS.md](SIM3-RESULTS.md),
`lab/echo3_sim3_report.json`, `lab/echo3_sim3_audit.json`.

Lee este archivo entero antes de escribir nada. Después lee, en este orden:
`CLAUDE.md`, `docs/ECHO-3-ACCEPTANCE.md`, `docs/SIM3-DESIGN.md`,
`docs/SIM3-RESULTS.md`, `echoai/nexus0/sim3/` y `echoai/tests/test_sim3*.py`.

---

## 1. Qué existe ya (no lo reimplementes)

`echoai/nexus0/sim3/` es infraestructura, no cognición. No importa WSP, CAM,
Q, T, PATTERN ni el gate, y no puede hacerlo.

| Módulo | Qué resuelve |
|---|---|
| `canon.py` | hash de bytes, JSON estricto, formas canónicas, rutas seguras |
| `geom.py` | milímetros exactos por decimal, AABB, rejilla libre, simetrías |
| `sdfprof.py` | gramática cerrada `sim3-boxes-v1`; rechaza lo que no nombra |
| `pkg.py` | paquete = 2 archivos; hash antes del parser; roles, columnas, conectividad |
| `generate.py` | SplitMix64 + tres arquetipos; 12 paquetes reproducibles |
| `rig.py` | lista fija de sistemas y esfera de prueba; SDF fuente ≠ SDF efectivo |
| `runtime.py` | preflight y `runtime-lock.json`; `gz sdf -k` real |
| `sandbox.py` | jaula bubblewrap del consumidor y su autotest |
| `session.py` | supervisor: Gazebo en lockstep y un socket con tres campos |
| `evaluate.py` | veredictos privados; nunca escribe al canal |
| `metamorph.py` | pares renombrado y pared movida |
| `seal.py` | compromiso, derivación HMAC, `sealed → opened → consumed` |
| `mutants.py` | 26 mutantes, cada uno desde un control positivo |
| `bench.py` | los diez grupos preregistrados y el informe |
| `audit.py` | auditor que reconstruye la evidencia y no lee `sim3_green` |

CLI real, con salida en `SIM3-RESULTS.md`:

```bash
cd /home/roger/REALRXOS/RXos/echoai
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 validate  --package docs/examples/sim3 --protocol docs/examples/sim3/protocol.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 preflight --output lab/sim3/runtime-lock.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 bench --rehearsal --output lab/echo3_sim3_report.json
PYTHONPATH=.. python3 -m echoai.nexus0.sim3 audit  lab/echo3_sim3_report.json
```

Lo que SIM-3 **no** demuestra, y por tanto tú tampoco puedes afirmar: vuelo,
aerodinámica, sensores, WSP desde física, planificación, transferencia,
hardware, Akida y julios. `hardware_status="not_available"` y
`agent_in_gazebo=false` siguen siendo obligatorios en cualquier informe que
produzcas.

---

## 2. Tu tajo: manifiestos y runners

No rediseñas SIM-3, no tocas el núcleo rápido y no adelantas FLIGHT-1. Haces
que lo medido sea **repetible por otro** y **declarable para una campaña**.

### 2.1 Manifiestos

1. **Manifiesto de campaña** (`docs/schemas/sim3-campaign.schema.json` +
   ejemplo). Congela, antes de generar nada: `protocol_sha256`,
   `lock_sha256`, `code_sha256`, generador y versión de PRNG, N por
   partición, KPI, umbrales, controles, custodio, fecha, y dónde vive el
   registro de accesos **fuera de este repositorio**. El compromiso del
   protocolo y el del inventario ya tienen fórmula fijada en SIM3-DESIGN.md
   §5; el manifiesto los referencia, no los reinventa.
2. **Manifiesto de familia de mundos**. Hoy hay tres arquetipos
   (`generate.ARCHETYPES`) escritos en Python. Extrae sus rangos a un
   manifiesto declarativo verificable por esquema — grosores, longitudes,
   alturas, rangos de estación y de spawn, retícula de 100 mm — de modo que
   una familia nueva sea un archivo, no un parche. La huella de geometría
   debe seguir siendo no equivalente entre familias bajo traslación,
   reflexión y giros de 90°: publica esa comprobación, no la supongas.
3. **Manifiesto de slice** para las fases de `ECHO-3-ACCEPTANCE.md` §9.
   La plantilla obligatoria (pregunta única, invariantes, entrada real,
   variable manipulada, control, métricas, semillas, verde/rojo, mutantes,
   artefacto) hoy es prosa. Conviértela en un esquema JSON y valida con él
   el manifiesto de SIM-3 como primer caso, para que FLIGHT-1 nazca ya
   declarado.

Reglas para los tres: `additionalProperties: false`, sin `latest`, sin
flotantes donde un entero en milímetros dice lo mismo, y un test que rechace
cada campo desconocido.

### 2.2 Runners

1. **Runner reproducible por host.** `preflight → bench → audit` con una sola
   orden, que construya la imagen si falta, verifique el digest si está, y
   **falle en alto** si no hay `podman` o `bwrap`. Nada de fallback: un host
   sin backend produce `not_run`, causa y siguiente comando. Recuerda que un
   host nuevo exige lock nuevo y repetición del banco: el runner debe
   negarse a mezclar dos locks en un informe.
2. **Runner de imagen.** El `Containerfile` fija la base por digest pero
   `gz-harmonic` viene del repositorio de OSRF y puede moverse. Haz que el
   runner registre las versiones instaladas, compare con el lock anterior y
   avise cuando cambien, en vez de reconstruir en silencio.
3. **Runner de CI.** Rápido y honesto: banco unitario siempre, banco de
   backend cuando haya backend, informe rojo publicado tal cual. El verde no
   se arregla bajando N ni tolerancias; si el criterio ha de cambiar, es una
   versión nueva del protocolo y el resultado anterior se conserva.

Documenta cada comando con su **salida real**. Si no lo ejecutaste, dilo.

---

## 3. Candados

- No toques `nexus0/` fuera de `nexus0/sim3/`, ni `tests/` fuera de
  `tests/test_sim3*.py`, ni `kernel/`, ISO, drivers o `userland/`.
- No cambies el perfil `sim3-boxes-v1`, los bytes de `docs/examples/sim3/`,
  N, tolerancias ni umbrales. Sus hashes están publicados y comprometidos.
- No generes la partición C de una campaña real en un árbol que un agente
  pueda leer. SIM-3 sólo corre ensayo, con el secreto público de 32 bytes
  `0x01`. Si escribes una C real, la has consumido.
- No conviertas `Cell.kind` ni ninguna verdad del simulador en sensor. El
  consumidor recibe `{"v","seq","sim_time_ns"}` y nada más; ampliar ese
  transporte con `goal`, `free_path` u `object_type` es fuga, no demo.
- No fabriques números. Sin dependencia: `not_run`, causa, siguiente comando.
- No relabeles: un mutante que falla por otra causa es un mutante roto, no
  una detección.

---

## 4. Entrega

Archivos cambiados, comandos ejecutados con salida real, esquemas nuevos con
sus tests de rechazo, estado por grupo y limitaciones. Actualiza `NOW.md` y
`ROADMAP.md` sólo con lo medido. Conserva los rojos.

Antes de cerrar, contesta por escrito: ¿algún runner ramifica por sala,
semilla o partición? ¿algún manifiesto exporta la solución? ¿un informe puede
mezclar dos locks? ¿algún test espera el valor que su propio mock acaba de
inventar? ¿has consumido un examen reservado?

La revisión posterior es independiente. No se promete verde: se exige que el
verde signifique el contrato medido.
