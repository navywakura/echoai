# RepoWorld · plan de implementación para Codex

> Para implementación por tareas: aplicar `superpowers:executing-plans` o
> `superpowers:subagent-driven-development`, conservando las mismas interfaces
> y revisando cada entrega. Este documento es un plan, no afirma que exista
> el runtime descrito.

**Objetivo:** evaluar reparación de repositorios reales con S/I2/F/E, aislar
el efecto del guardarraíl y medir memoria con adquisición completa.

**Arquitectura:** supervisor local con capacidades de snapshots y ejecución
Bubblewrap; inferencia exclusivamente remota por el relay existente; evaluación
oficial en autoridad distinta después de congelar todas las entregas.

**Stack:** Python, unittest, Bubblewrap, systemd/cgroup v2, Git, Docker para el
harness fijado; Qwen2.5-Coder-32B Q4/llama.cpp b11577; matplotlib/jsonschema
solo para análisis. Sin dependencias nuevas en NEXUS-0.

**Spec:** [diseño completo](SWE-BENCH-LITE-DESIGN-20261013.md),
[contrato](SWE-CONTRACT.json), [muestra](swebench/SWE-SAMPLE.json).

## Restricciones globales

- Dataset revisión `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`;
  harness v4.1.0 commit `726c5461e2ef52d83cf1ea2107870a8bb3328d57`.
- 24 issues principales, cuatro brazos, 96 episodios; 16 de calibración,
  24 de ablación y 14 de memoria: 150 previstos. No reemplazar casos por éxito.
- Cada issue/brazo: 25.000 tokens entrada+salida, 24 llamadas LLM, 80 herramientas,
  6 críticas, 8 parches, 10 tests, 1.200 s CPU candidato y 1.800 s pared.
- Contexto 4.096; prompt con plantilla ≤3.200, salida ≤768, margen mínimo 128.
- I2: 11k+11k+3k tokens; 10+10+4 llamadas; demás recursos compartidos, no duplicados.
- Tests individuales ≤180 s pared /240 s CPU; 4 GiB RAM /1 GiB tmpfs agregado;
  proveedor ≤240 s. Calibrar antes de sellar, cambiar igual para todos si hace falta.
- `patch`, `test_patch`, F2P/P2P, hints, logs finales y claves no son datos online.
- S/F/E usan el mismo modelo, herramientas, suite pública y límites; F no recibe
  un orden deliberadamente adverso. El evaluador final es idéntico para todos.
- SharedCAM publica por evidencia pública, nunca por el score oficial de un donante.
- No tocar núcleo NEXUS-0, no crear otro thought-bus, no reabrir S6.
- Rama local de investigación. No push/publicación de esta campaña.

## Foco de revisión

1. Repo con symlinks, archivo enorme, carrera de escritura o diff traversal:
   rechazo sin modificación parcial ni fuga. Tareas 2/3.
2. Test que importa código malicioso, falsifica PASSED o elimina colección:
   ejecución aislada; evidencia inválida no equivale a éxito. Tareas 2/4/7.
3. Gold/test patch o score filtrado por rootfs, cache, prompts o SharedCAM:
   separación por capacidades y barrera global, incluidos booleanos. Tareas 1/6/7.
4. Timeout con worker todavía generando y reinicio entre recibo y CAS:
   recuperar una sola transacción, cobrar lo consumido y no duplicar la llamada.
   Tareas 3/5/8.
5. Cadena de memoria vacía/irrelevante y adquisición cara:
   no sustituir donantes, controles emparejados, coste completo. Tareas 6/9.

## Entregas ya realizadas

- [x] Diseño, contrato de propuesta, schemas de herramientas/lock/export.
- [x] `scripts/select_swebench_subset.py`, proyección pública de 300 filas y
  muestra determinista de 24, con grupos disjuntos de calibración/memoria.
- [x] `scripts/plot_swebench_results.py`, cuatro PDF/PNG, denominadores
  completos, costes de fallos, coste de adquisición, marca de agua sintética.
- [x] `tests/test_swebench_design_tools.py`: validación/análisis/selección/export.

Las tareas 1–3 tienen una implementación local y calibración de infraestructura;
los entornos con dependencias y las tareas 4–9 siguen pendientes. Véase
[la entrega local](REPOWORLD-LOCAL-CALIBRATION-20261013.md). No ejecutar comandos `run`
hasta completar preflight, lock y revisión. Las pruebas de CPU van en segundo
plano con logs; se monitorizan fallos y no se relanzan selectivamente.

## Estructura propuesta

| Archivo | Responsabilidad |
|---|---|
| `repoworld/types.py` | Dataclasses para capacidades y referencias públicas/selladas distintas. |
| `repoworld/dataset.py` | Ingesta fijada, vista pública y catálogo privado. |
| `repoworld/environment.py` | Preparación de rootfs online e identidad de imágenes oficiales. |
| `repoworld/workspace.py` | Adaptar SnapshotStore, stage/retain/CAS y diff final. |
| `repoworld/tools.py` | Única entrada de las cuatro herramientas MCP. |
| `repoworld/checks.py` | Colección pública, baseline estable, sondeos y reportes. |
| `repoworld/provider.py` | Prompts/esquemas de repositorios y contexto limitado. |
| `repoworld/protocol.py` | Perfiles S/I2/F/E/E_no_guard y decisiones registradas. |
| `repoworld/memory.py` | Lecciones públicas entre episodios con procedencia. |
| `repoworld/evaluator.py` | Autoridad final aislada y export oficial de parches. |
| `repoworld/audit.py` | Custodia, presupuestos, cobertura y export de análisis. |
| `repoworld/study.py` | Calendario fijado, pausas y reanudación, cuota GPU. |
| `ECHO-5.1/scripts/run_repoworld.py` | CLI único de preparación, ejecución y auditoría. |
| `tests/test_repoworld_*.py` | Fixtures pequeñas independientes de las tareas SWE reservadas. |

Reutilizar `pcworld` mediante imports. Extraer transporte/contexto o ampliar
perfiles en módulos existentes con compatibilidad, sin copiar el runner ni
crear un segundo sistema de recibos. Cambios del código experimental producen
un manifiesto nuevo: las auditorías PCWorld históricas se reproducen desde su
commit congelado, no recalificando con RepoWorld.

## Tarea 1 · Contratos y frontera de datos

**Archivos:** crear `repoworld/types.py`, `dataset.py`, `__init__.py`,
`tests/test_repoworld_dataset.py`; consumir JSONs ya entregados.

**Interfaces:**

```python
@dataclass(frozen=True)
class PublicTask:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str

@dataclass(frozen=True)
class EnvironmentRef:
    rootfs_sha256: str
    policy_sha256: str
    root: Path                 # capability creada por supervisor, nunca por LLM

@dataclass(frozen=True)
class RepoBase:
    task: PublicTask
    snapshot: Snapshot         # pcworld.snapshots.Snapshot
    environment: EnvironmentRef

def public_task(row: dict) -> PublicTask: ...
def read_fixed_dataset(path: Path, expected_sha256: str) -> list[dict]: ...
```

- [x] Crear fixture con issue y sentinelas distintos en cada campo sellado.
  Afirmar `asdict(public_task(row))` exactamente igual a los cuatro campos
  permitidos; no filtrar por lista de claves prohibidas incompleta.
- [x] Añadir rechazo de IDs duplicados, commit inválido, schema incompatible,
  hash de dataset alterado y roster incompleto. No hacer inferencia en tests.
- [x] Ejecutar `python3 -m unittest discover -s tests -p test_repoworld_dataset.py`
  y confirmar el fallo por interfaz ausente; implementar lectura/proyección.
- [ ] Cargar solo metadatos al selector. Guardar catálogo sellado en directorio
  privado con autoridad independiente. Nunca serializarlo en `PublicTask`.
- [x] Añadir rechazo de cualquier arranque con contrato `design`, lock ausente
  o hashes/IDs divergentes. Pasar tests y revisión de frontera antes de commit local.

## Tarea 2 · Entorno hermético para repositorios

**Archivos:** `repoworld/environment.py`, perfil explícito en `pcworld/runner.py`
y `runtime.py`, `tests/test_repoworld_environment.py`.

**Interfaces:**

```python
def prepare_repo(task: PublicTask, source: Path, environment: EnvironmentRef,
                 expected_commit: str) -> RepoBase: ...
def execute_repo(base: RepoBase, candidate: Snapshot, check_argv: tuple[str,...],
                 *, limits: dict, check_artifacts: tuple[str,...]) -> dict: ...
```

- [x] Tests con programa que intenta leer sentinelas host, red, claves y otros
  episodios; ninguno debe aparecer en stdout. Test de escritura en scratch
  seguida de comprobación de que BASE/candidato conservan sus hashes.
- [x] Tests de memoria/PIDs/CPU/tmpfs y terminación de hijos. No aceptar fallback
  sin Bubblewrap/cgroup. Los límites totales de tmpfs no se multiplican por mount.
- [ ] Ensamblar rootfs específico desde dependencias fijadas; conservar kernel,
  CPU/arquitectura, toolchain e inventario como datos de entorno. Prohibir host
  `/usr`. No ejecutar instalación/colección dentro del supervisor.
- [x] Conservar rutas/semántica del runner PCWorld bajo el perfil anterior;
  el nuevo acepta cwd/entorno y extracción acotada de artefactos por capacidades.
- [ ] Inspeccionar contenido completo del rootfs online para gold, eval scripts,
  caches/historial Git y sentinelas sellados. Un directorio no listado no es seguro.
- [x] Medir una preparación pequeña sin GPU: bytes de imagen/rootfs, scratch,
  RAM pico y tiempo. Registrar límite de almacenamiento y limpieza solo de
  objetos creados por esta campaña; no `docker system prune -a` indiscriminado.
- [x] Pasar tests específicos más suite PCWorld en segundo plano; evidencia
  en la entrega local (35 RepoWorld, 255 PCWorld, 13 diseño/análisis).

## Tarea 3 · Navegación y parches transaccionales

**Archivos:** `repoworld/workspace.py`, `tools.py`, adaptación perfil de
`pcworld/snapshots.py`, `tests/test_repoworld_workspace.py`.

**Interfaces:**

```python
@dataclass(frozen=True)
class PatchCandidate:
    base_id: str
    snapshot: Snapshot
    patch_sha256: str
    operation_id: str

def stage_patch(base: RepoBase, current: Snapshot, diff: str, *,
                expected_snapshot_id: str, purpose: str) -> PatchCandidate: ...
def retain(candidate: PatchCandidate, *, expected_head: str,
           public_receipt_ids: tuple[str,...]) -> str: ...
def dispatch_tool(request: dict, *, session) -> dict: ...
```

- [x] Fixtures: dos archivos donde el segundo hunk falla; árbol/puntero idénticos
  antes/después. Rechazar stale CAS, absolute/`..`, symlink/hardlink, extensión
  de permisos, configuración Git maliciosa y diff >65.536 bytes.
- [x] Verificar que stage crea candidato, pero no cambia `retained_candidate`;
  recuperar crash antes/después de recibo y CAS con el mismo `operation_id`.
- [x] Adaptar captura/lectura por streaming con límites explícitos transmitidos
  por toda la cadena; evitar que el runner recapture con defaults de 64 MiB.
- [ ] Implementar four-tool dispatcher con schemas entregados, cursores
  autenticados al snapshot, argv fijo y límites de bytes/tokens. No shell libre.
- [x] Prueba `file_view`: Unicode, línea >8 KiB, rango fuera de archivo,
  líneas originales tras paginar y presupuesto insuficiente. AST solo indexa.
- [x] Generar diff final desde BASE y snapshot retenido; roundtrip exige el mismo
  hash. Se usa difflib + parser exacto en vez de Git: elimina hooks/configuración
  del proceso de edición. Git solo exporta blobs fijados durante la preparación.

**Estado de las capacidades locales:** `repo_search`, `file_view` y
`patch_apply` implementados; `test_run` despacha únicamente checks registrados
por el supervisor y conserva resultado desconocido. Falta el namespace de
sondeos y la semántica de aceptación de pruebas de la tarea 4. La imagen de
calibración contiene stdlib y no acredita dependencias SWE. El catálogo sellado
no se serializa en esta entrega: permanece fuera de la vista online.

## Tarea 4 · Evidencia pública y rollback

**Archivos:** `repoworld/checks.py`, `tests/test_repoworld_checks.py`.

**Interfaces:**

```python
@dataclass(frozen=True)
class PublicCheckReport:
    candidate_id: str
    check_plan_sha256: str
    states: dict[str,str]
    evidence_blob_sha256: str
    receipt_id: str
    valid: bool

def collect_public_baseline(base: RepoBase, check_plan: dict) -> PublicCheckReport: ...
def run_public_checks(base: RepoBase, candidate: PatchCandidate,
                      check_plan: dict) -> PublicCheckReport: ...
def public_regressions(before: PublicCheckReport,
                       after: PublicCheckReport) -> tuple[str,...]: ...
```

- [x] Fixtures independientes: un patch arregla bug pero rompe un test previo;
  otro repara ambos. En guard activo, comprobar conservación/reemplazo correcto.
- [x] Repetir BASE dos veces; test flaky o ya fallido queda identificado, no se
  convierte en una regresión nueva. Pass→skip, colección cero y test ausente
  producen invalidez o regresión según contrato; no se aceptan silenciosamente.
- [ ] Intentos de forjar líneas PASSED, cambiar plugins, editar tests/checker y
  exit contradictorio deben producir evidencia rechazada; documentar límite
  de amenaza del ejecutor Python, sin proclamar prueba formal universal.
- [x] Registrar test del crítico primero como propuesta. Testigos no justificados
  por contrato público no adquieren `PUBLIC_COUNTEREXAMPLE`. Fixture de un
  crítico que exige una salida errónea: no debe convertirse en FACT.
- [ ] Implementar recibos con blobs acotados, identidad del check y candidato,
  costes reales y feedback CEGIS. Pasar tests, revisión y commit.

## Tarea 5 · Proveedor, roles y presupuesto común

**Archivos:** `repoworld/provider.py`, `protocol.py`, extracción acotada de
`pcworld/provider.py`; pruebas `test_repoworld_protocol.py`.

**Interfaces:**

```python
def generate_repo(messages: list[dict], response_schema: dict, *,
                  budget: Budget, provider, deadline: float) -> dict: ...
def run_episode(base: RepoBase, arm: str, seed: int, *,
                budget: Budget, provider, library, output: Path) -> dict: ...
```

- [ ] Proveedor determinista de fixture: respuestas finitas que fuerzan localizar,
  editar, fallar test y reparar. Las pruebas de control no requieren un LLM.
- [ ] Afirmar que mensajes formateados+respuesta reservada nunca exceden 4096;
  páginas y ledger reordenados no pierden hash/procedencia. No resumen inventado.
- [x] S puede hacer la misma reparación que F/E. I2 comparte una sola cuenta;
  dos ramas nunca reciben 25k cada una. Selector no puede consultar final score.
- [x] F/E tienen mismo catálogo y guard; E_no_guard solo cambia retención
  automática. Probar que se ejecutan/cobran los mismos checks comunes.
- [x] Refutación activa suspende críticas y permite dos reparaciones. Cuota de
  críticas agotada congela el candidato; no inventa RESOLVED ni impide examen.
- [ ] Deadline de proveedor/relay coherente. Si hay generación remota pendiente,
  registrar estado y cancelar/esperar con límite; no iniciar una duplicada
  gratis. Probar respuesta tardía/repetida, EOF y restart del broker.
- [ ] Conservar 255 pruebas PCWorld y añadir tests específicos; commit local.

## Tarea 6 · Memoria con procedencia pública

**Archivos:** `repoworld/memory.py`, `tests/test_repoworld_memory.py`.

**Interfaces:**

```python
def publish_public_lesson(candidate: PatchCandidate, checks: PublicCheckReport,
                          *, author: str, public_task: PublicTask,
                          library) -> str | None: ...
def retrieve_lessons(base: RepoBase, *, library, max_tokens: int,
                     budget: Budget) -> tuple[dict,...]: ...
```

- [ ] Donante con control público verde y final rojo: publicación pública
  independiente del final. Donante con final verde pero sin testigo público:
  no inventar una receta verificada. El proceso de publicación ni recibe ese campo.
- [ ] Fixture cambia dependencias/precondición manteniendo AST parecido: debe
  revalidar y nunca bloquear semánticamente por similitud. Evitar asumir O(1).
- [ ] Persistir y restaurar biblioteca limitada con hashes/procedencia; probar
  corrupción, intento de publicar gold, receta irrelevante, biblioteca llena y
  donante sin lección. No reemplazar al donante fallido por uno exitoso.
- [ ] Cobrar publicación, retrieval y todos los donantes; comprobar que
  condiciones empty/shared arrancan mismo BASE y presupuesto, sin diff heredado.
- [ ] Medir primera propuesta, reparaciones, fallos repetidos y transferencia
  negativa, distinguiendo hints de propiedades comprobadas. Pasar tests/commit.

## Tarea 7 · Evaluación final y auditoría

**Archivos:** `repoworld/evaluator.py`, `audit.py`,
`tests/test_repoworld_evaluator.py`, `test_repoworld_audit.py`.

**Interfaces:**

```python
@dataclass(frozen=True)
class SubmissionRef:
    instance_id: str
    candidate_id: str
    diff_sha256: str
    journal_head: str

def freeze_submission(task: PublicTask, candidate: PatchCandidate | None,
                       journal_head: str) -> SubmissionRef: ...
def evaluate_sealed(submissions: tuple[SubmissionRef,...], *,
                     curator_capability, run_lock: dict) -> dict: ...
def audit_study(run_dir: Path, lock: dict, *, export: Path | None) -> dict: ...
```

- [ ] Construir fixtures de reporte upstream y logs: raw true pero test ausente,
  skip, todos XFAIL, P2P vacío, F2P vacío, timeout, identidad incorrecta, diff vacío.
  Mantener raw score; strict verified solo con toda la evidencia requerida.
- [ ] Export oficial `{instance_id, model_name_or_path, model_patch}` con una
  entrega por issue/brazo/semilla. `run_id` incluye lock y patch-set; caché no
  puede mezclar dos diffs. Verificar imagen/eval-script por digest.
- [ ] Curador valida negativo/gold, pero ningún byte de esos controles vuelve al
  actor. Probar sentinelas en stdout, filesystem, prompts y memoria.
- [x] Barrera global: intentar consultar un final mientras quede una entrega
  principal/guard/memoria sin congelar debe fallar. Auditor no crea claves ausentes.
- [ ] Comprobar cadena, artefactos, presupuesto, todos los roles, schedule, hashes
  de fuente, modelo, base/runtime y tests. JSON Schema valida estructura; las
  comprobaciones de significado se implementan aparte.
- [ ] Export `repoworld.analysis.v1` solo tras auditoría íntegra. Añadir tablas
  de raw vs verified y errores; no ocultar episodios que no tengan informe.
- [ ] Ejecutar un roundtrip independiente de fixture y comparación negativa/gold
  solo en calibración. Pasar tests y revisión de seguridad/metodología; commit.

## Tarea 8 · Orquestación y calibración

**Archivos:** `repoworld/study.py`, `ECHO-5.1/scripts/run_repoworld.py`,
`tests/test_repoworld_study.py`.

- [ ] CLI `prepare`, `preflight`, `calibrate`, `seal`, `run`, `audit`, `status`.
  `run` exige lock sellado; un contrato draft debe rechazarse antes de asignar GPU.
- [x] Registrar calendario completo por ID/brazo/seed. Reanudación solo de celdas
  no comenzadas o transacciones recuperables con misma identidad; no re-muestreo.
- [ ] Pruebas de caída entre token reserve/settle, snapshot/receipt, submit/eval;
  recuperar sin cobrar dos veces ni olvidar trabajo realmente consumido.
- [ ] Preflight local: capacidad real, rootfs/checks, 24 imágenes elegibles,
  runtime online sin secretos, controles negativos/gold. Si falla, no lanzar panel.
- [ ] Consultar cuota, encender GPU solo después de entornos preparados. Calibrar
  los 16 episodios con logs/mini terminal; medir throughput y espera local.
- [ ] Estimar P50/P90 del calendario; revisar límites iguales para todos antes
  de sellar. Si contexto 4k resulta insuficiente, medirlo y registrar protocolo
  nuevo; no subirlo solo en E. Congelar prompts y decisiones sin mirar panel.
- [ ] Escribir lock real, pasar esquema+semántica, cotejar manifiesto. Al acabar
  cada fase parar worker/broker y comprobar estado de Kaggle para evitar gasto ocioso.

## Tarea 9 · Piloto, cuatro figuras y checklist científico

**Archivos:** campaña bajo `ECHO-5.1/artifacts/` ignorada; informe nuevo en docs,
actualización `CLOSURE-CHECKLIST.md`; reutilizar plotter entregado.

- [ ] Ejecutar principal 96, ablación 24 y memoria 14 bajo los topes fijados.
  Publicar errores y no terminados aunque E pierda. Mantener oracle cerrado hasta
  todas las entregas; congelar parches antes de calificar.
- [ ] Ejecutar auditoría dos veces desde proceso nuevo con misma autoridad;
  verificar igualdad de resultados/hashes y fuentes. Export sanitized sin claves.
- [ ] Generar cuatro figuras PDF/PNG y resumen. Añadir resultados por familia/
  issue, contraste E_no_guard, pares E−S/E−F y transferencia negativa. El plotter
  básico ya existe; no presentarlo como auditoría ni significación estadística.
- [ ] Coste full de memoria = todos los donantes + publicación + lookup +
  receptores; coste marginal por separado. Cero resueltos produce N/D, no infinito
  oculto ni descarte de la serie. Suites preexistentes fallidas no son regresiones.
- [ ] Separar verde de infraestructura, piloto exploratorio e hipótesis general.
  Si efecto es incierto, dimensionar nueva confirmación y reservar tareas nuevas;
  no editar este contrato tras ver las puntuaciones para obtener verde.
- [ ] Completar checklist H1/H2/H3/H4/T20, reproducibilidad en otra máquina,
  límites del harness y contaminación potencial. S6 sigue fuera del alcance.

## Prueba rápida de los artefactos de diseño existentes

```bash
python3 -m unittest discover -s tests -p test_swebench_design_tools.py
python3 scripts/select_swebench_subset.py \
  --metadata ECHO-5.1/docs/swebench/SWE-LITE-PUBLIC-METADATA.json \
  --output /tmp/SWE-SAMPLE.reproduced.json
cmp /tmp/SWE-SAMPLE.reproduced.json ECHO-5.1/docs/swebench/SWE-SAMPLE.json
```

Esos comandos no descargan modelos, no lanzan Docker/Kaggle y no constituyen
ejecución de SWE-bench. La calibración local y los tests del nuevo runtime se
harán después de implementar las tareas correspondientes.

## Continuación: tareas 4–8, compuertas locales

Checks, protocolo, contabilidad duradera, curador, CLI y auditor se implementaron
en la continuación de `e0a1a6d`. La evidencia y los límites están en
[REPOWORLD-EXECUTION-20261013.md](REPOWORLD-EXECUTION-20261013.md).
Las casillas sin marcar mantienen obligaciones completas pendientes, aunque
haya implementación parcial. El preflight de entornos y los controles oficiales
no han pasado; Kaggle no se ha iniciado y el contrato permanece en diseño.
