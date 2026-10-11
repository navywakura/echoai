# MissionAgent: integración de razonamiento, revisión 2

Código preparado en `artifacts/mission-integration-draft/staged/`; todavía sin
aplicar a fuentes activas ni ejecutar tests o campañas. El contrato es
`MISSION-CONTRACT.json` versión 2. No atribuirle los resultados de la revisión
1: aquélla ejecutaba COMPOSE heredado incluso en el modo principal.

## Ruta normal y API

```python
from echo5.budget import Budget
from echo5.mission import MissionBridge, goal_request, run_benchmark, audit_report

actor = MissionBridge(goal_request([1, 0, 0]), budget=Budget(1_000_000))
response = actor.decide(raw, sequence=0, now_ns=receiver_sim_clock_ns)
# Después de una ejecución: evidencia pública de ACK + muestras + llegada.
actor.observe_consequence(outcome)

report = run_benchmark(dict(phase="development", seed=51601,
                           cases=12, budget=1_000_000, max_decisions=64))
audit = audit_report(report)
```

`echo32` y `one_step` llaman automáticamente al razonador ECHO-5. No requieren
que el banco entregue `plan=`. `conventional` conserva la búsqueda COMPOSE con
Q neutralizada. El plan externo opcional sigue siendo una hipótesis validada;
no puede satisfacer el nuevo gate de integración de razonamiento de un banco.

Una subclase local importa y conserva `MissionAgent`. Sobrescribe solamente
`_compose(frame)` para introducir la búsqueda por instancia; no modifica las
clases ni las funciones globales heredadas. El agente original proyecta los
sensores, registra la calibración, actualiza FUSION y decide POWER antes de
ese punto. Regreso, inspección del marcador y parada siguen siendo heredados.
La ruta normal proyecta una vez; el hint externo conserva validación previa.

El nuevo `MissionReasoner` usa `grounding.Object/Scene`, relaciones fila/columna
y `interaction.HypothesisAgent.plan` con un prior nominal explícito. El prior
no escribe hipótesis aprendidas, soporte, CAM, T ni recuerdos de adquisición.
El adaptador construye el grafo con celdas admitidas por las familias actuales;
excluir una celda desconocida no la convierte en una pared observada. La meta
solicitada no se convierte en una observación del marcador.

Límites: dominio 9×9, 32 objetos como máximo, ocho destinos candidatos, cuatro
pasos de horizonte (uno en `one_step`), 324 aristas por llamada al planificador
y 30.000 unidades de trabajo por decisión, debitadas del techo del episodio.
La memoria de visitas sólo registra posiciones públicas observadas o llegadas
confirmadas. Una consecuencia confirmada cambia el coste de revisita de los
planes siguientes. No se afirma adquisición de nuevas dinámicas de vuelo.

## Consecuencias y autoridad

El worker SITL recibe exactamente `raw`, `sequence`, `now_ns`, `outcome`.
La primera observación tiene `outcome=None`; las siguientes incluyen el recibo
de la propuesta anterior. El relay lee incrementalmente sólo los eventos
públicos de `trace.jsonl`, sin leer `private.jsonl` ni la geometría privada.
El runner heredado y sus snapshots permanecen intactos.

`outcome` enlaza secuencia, hash del raw, WSP y predicción. `arrived` exige
admisión, envío, ACK correcto, estado completo, al menos tres muestras y
telemetría compatible: error horizontal <=350 mm, vertical <=300 mm y velocidad
<=150 mm/s. `not_executed` registra descartes `age`/`world_changed` y no contiene
ACK ni telemetría de llegada. Ni un ACK ni un plan se cuentan como movimiento.
El auditor reconstruye estos enlaces desde las trazas originales por separado.

POWER, SAFE, gateway y PX4 conservan su autoridad. WSP sigue siendo el único
bus; Recorder conserva observaciones y resultados reales. No se introduce
LLM, control de hardware, red externa, puerto de host ni desarmado forzado.

## Auditoría y gates

`audit_report(report)` conserva la adjudicación independiente desde el mundo
externo, POWER/SAFE/gateway y denominadores, seguida de replay lógico nuevo.
Además comprueba proyección, admisión actual, rutas y consecuencias nominales,
objetivo, elección entre candidatos, historia de visitas y correspondencia
entre plan y primer WSP. No llama al planificador para decidir si una ruta es
admisible. La comparación con el productor sigue siendo prueba adicional.

Cada fila incluye `reasoner_calls`, `reasoner_actions`, `reasoner_executed` y
`consequence_receipts`. Las filas nominales principales requieren llamadas y
acciones nuevas efectivamente ejecutadas. Un rótulo `plan_source` no acredita
la integración. Un resultado negativo reconstruible puede ser auditable sin
aprobar corrección, ventaja, SITL o hardware.

Desarrollo rechaza cualquier intersección entre `[seed, seed+cases-1]` y los
intervalos reservados 61703–61714 (software) u 861703–861708 (SITL). Se conservan
los máximos de casos 96/12 y todos los parámetros de confirmación.

## Ejecución posterior, a cargo del padre

Desde ECHO-5, sólo después de aplicar el borrador y finalizar toda programación:

```sh
.venv/bin/python -I -B scripts/dev.py test
.venv/bin/python -I -B scripts/run_sitl.py software --seed 51601 --cases 12 --out artifacts/mission-development-reasoning-v2
.venv/bin/python -I -B scripts/run_sitl.py run --phase development --cases 1 --episode-timeout-s 900 --campaign-timeout-s 2700 --out artifacts/sitl-development-reasoning-v2
.venv/bin/python -I -B scripts/run_sitl.py audit artifacts/sitl-development-reasoning-v2
```

El padre mantiene `.venv-sandbox` separada para sus checks externos. Estos
comandos se suministran, no se han ejecutado. El caso SITL único sirve para
arranque/calibración; no satisface cobertura de condiciones. El contrato
completo exige seis casos × tres modos y auditor externo. Timeout por episodio
900 s; campaña completa 18.000 s; teardown <=20 s. La referencia de tres modos
tardó unos 15 minutos; no es una promesa para el razonador nuevo.

La latencia incluye obtención del recibo público y petición/respuesta del
worker. Sigue pendiente medir cuánto cuesta el grafo frente al ahorro de una
proyección. El runner descarta sensores de más de 200 ms y conserva su veto de
worker. No se amplía esa ventana para que el nuevo razonador pase.

Se conserva la imagen local por ID
`5364c865ebf08b1dd19ee7a6a46ca3c3911056269974e7d9db2ced4a74201d27`:
Podman sin red, sin dispositivos, sin publicaciones, raíz de sólo lectura,
4 CPU, 4096 MB, renderizado software y procesos/identidades propios. ULog,
trazas, fuentes, contrato, telemetría privada del juez y teardown son recibos
obligatorios. La física usa tolerancias; no se promete replay float exacto.
