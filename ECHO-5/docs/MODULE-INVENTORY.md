# Inventario previo a la integración de ECHO-5

10 de octubre de 2026. Revisión estática del árbol existente, con contraste
documental de resultados. **No se ha integrado ni ejecutado ningún agente.**
Los certificados mencionados proceden de informes anteriores; esta revisión
no repite experimentos, abre reservas ni convierte tests encontrados en tests
aprobados. S6 sigue sin pase y B24 conserva su ejecución y su checkpoint.

El [catálogo archivo por archivo](inventory/CATALOG.md) incluye **981 módulos
Python**: 975 dentro de los árboles de código de echoAI y seis dependencias
host del repositorio padre (cinco importadas y otra declarada por el
empaquetador). Incluye 208 archivos de pruebas; un archivo no
equivale a una capacidad ni a una prueba. Los 981 archivos se analizaron por
AST sin errores de sintaxis bajo Python 3.12.13. El [JSON](inventory/modules.json)
contiene rutas, hashes, símbolos superiores, imports, consumidores, tests que
los importan y menciones documentales. El [grafo](inventory/dependencies.mmd)
cuenta imports potenciales entre familias; no representa llamadas de ejecución.

| Área | Python | Alcance |
|---|---:|---|
| `nexus0/` | 385 | Núcleo, etapas 1/2, robótica 3, campañas y recursos ejecutables |
| `echo4/` | 109 | Cuerpo, ego funcional, continuidad, interacción, tribu, dreaming y bancos |
| `seed/` | 167 | DSL, aprendizaje, memorias, V3, S6, RSI y evaluación |
| `echo_arc/` | 51 | Actor de juegos, memorias temporales, gramáticas e investigadores |
| `gui4/` | 8 | GUI anterior, evidencia, catálogo y visualización |
| `harness/` | 28 | Bridges, echo-nexus y arnés de desarrollo |
| `metaverse1/` | 9 | Mundo, declaración, custodia y recursos del simulador |
| `release1/` | 11 | Empaquetado, verificación, CLI y adaptador de córtex |
| `tests/` | 204 | Pruebas principales; otras cuatro viven bajo harness |
| Raíz | 3 | `__init__.py`, `observe.py`, `observe_b5.py` |
| Dependencias del padre | 6 | WSP, QN, CAM, DAG, spoke y STDP declarado por release |

También se enumeran 46 archivos auxiliares, con hash de cinco fuentes o
configuraciones no Python: dos gramáticas, dos scripts shell y el pyproject
de echo-nexus. El alcance excluye copias bajo `lab/`, datos, pesos, entornos,
herramientas de terceros, web histórica, recursos gráficos y `echo-discord`.
`viz_tasks/` se recorrió sin encontrar módulos Python. Los scripts operativos
y ZIP congelados de Kaggle son artefactos de ejecución separados: el inventario
del árbol actual no sustituye su manifiesto. En particular, B24-R1 contiene
overrides declarados que no se deben confundir con los archivos raíz de B24.

La revisión conserva los nombres y versiones reales. «Reutilizable» significa
candidato a una integración con contrato y pruebas; no significa que baste
copiar una carpeta o que toda la capacidad ya esté conectada al núcleo.

## Representación, control y antecedentes

El inventario detallado de núcleo y robótica se completa en
[CORE-AND-ROBOTICS.md](CORE-AND-ROBOTICS.md). Sus grupos principales son:

| Familia | Implementación existente | Función y disposición |
|---|---|---|
| WSP/QN/CAM | `../navi10_wsp.py`, `../navi10_qn.py`, `../navi10_cam.py`, `../navi10_dag.py`, `../navi10_spoke.py`; `navi10_stdp.py` incluido por release | Dependencias host; no eliminar por su nombre histórico. WSP16, direcciones, episodios y respuesta LIF son componentes distintos; inclusión de STDP no acredita uso en decisiones. |
| Núcleo NEXUS-0 | `nexus0/{loop,encoder,lex,qtable,world,gate,constants,types}.py` | Observación, estado, aprendizaje entero y veto. Preservar funcionamiento con córtex apagado. |
| Planificación y adaptación | `plan`, `attend`, `escalate`, `pattern*`, `oracle`, `corridor`, `stream1`, `xfer1` | Extensiones situadas y bancos específicos; hay que elegir interfaces y versiones, no activarlas todas por defecto. |
| Cuerpo y mantenimiento temprano | `body*`, `graph`, `open1`, `self1`, `room1`, `obj1`, `vita1`, `food1`, `heat1*`, `shifts`, `sleep2` | Antecedentes de cuerpo, recursos, causalidad y adaptación. Conservar linajes de evaluación. |
| Herencia y capacidad | `gen1*`, `capacity1` | Herencia acotada y experimentos LIF; no equivalen a entrenamiento de un LLM ni a la guía asociativa 500k. |
| Córtex y comunicación | `cortex*`, `sign*`, `qwen_sign*`, `talk*`, `thought` | Propuestas y reporte bajo contratos; distinguir stubs, llamadas opcionales y hechos verificados. |
| Robótica | `sim3`, `flight1s*`, `sensor1s*`, `ground1*`, `dynamic1*`, `pattern1r*`, `fusion1`, `compose1*`, `cause1`, `px41`, `power1`, `safe1*`, `host1`, `transfer3`, `drone3` | Cadena software validada en dominios acotados; DRONE-3 SITL verde, HIL y jaula pendientes. |

## ECHO-4, interfaces y distribución

La revisión de estas familias se detalla en
[AGENT-AND-INTERFACES.md](AGENT-AND-INTERFACES.md). Incluye WORLD/SENSATION,
BOUNDARY/SELF, CONTINUITY, DREAM, MAINTAIN, OTHER/INTERACTION, RELATION,
ROLES/TRIBE, INTEGRATE/SITUATE, CODE y bancos ARC. Las campañas y auditores
se conservan como instrumentos separados del runtime.

Ya hay interfaces que revisar antes de programar una nueva: `nexus0/board.py`
genera un replay HTML; `nexus0/neural_viz*` y `gui4/` presentan actividad;
`observe.py` y `echo_arc/observe.py` leen o exportan decisiones reales;
`harness/echo-nexus` implementa la TUI y sus conexiones. Una GUI web nueva
debe reutilizar la procedencia y las reglas de observación, sin asumir que
estas implementaciones son ya el producto local que queremos.

## ECHO-SEED, rejillas y memoria 4.5

| Familia | Archivos de `seed/` | Qué existe y qué no se atribuye |
|---|---|---|
| Semilla y corpus | `dsl`, `learn`, `sandbox`, `gym` | Primitivas, biblioteca de conceptos, clonación y adquisición con diarios. La gramática cambia por nivel S0/S1/S1b/S2v; un nivel posterior no acredita mejor transferencia automáticamente. |
| Datos sintéticos y guía neuronal | `dreams`, `intuition` | Generación de tareas por programas y CNN para ordenar primitivas. Entrenamiento PyTorch, inferencia NumPy. No es la misma estructura que LIF ni la guía 500k. Presencia de código no certifica un checkpoint útil. |
| Refinamiento | `refinement`, `refinement_bench`, `refinement_s2v_bench` | Búsqueda/composición, vistas y comprobación de demostraciones. Bench separado de biblioteca; la verdad de test debe seguir fuera del solver. |
| DSL relacional | `relational_dsl`, `relational_solver`, `relational_tasks` | `OBJECTS`, `RELATE`, `BIND`, `MAP_OBJECTS`, `RENDER`; roles y composición tipada, coste explícito y desacuerdo entre programas. Los generadores de tareas pertenecen al evaluador. |
| Adquisición e informes relacionales | `relational_campaign`, `relational_report` | Instrumentos del cierre V3; no son memoria ni control del agente en producción. |
| Memoria de aldea | `village`, `village2`, `village3`, `village3_factorized`, `village3_efficient`, `village3_settled`, `village3_receipts` y sus campañas | Variantes y herencia reales. 3E es `village3_receipts`; depende de versiones anteriores. Conservar resultados rojos de sus antecesores. |
| Memoria para rejillas | `arc_memory`, `grid_memory_update` | Recibos de demostraciones verificadas, recuperación y estado. Reutiliza mecanismos de aldea, no sus hechos privados ni valores aprendidos como si fueran habilidades ARC. |
| Política diferida | `arc_delayed_policy` | `ArcPolicy` hereda de `village3.Echo`: `choose/begin/charge/mature` para recuperar primero o buscar primero; el verificador permanece externo. |
| Integración V1/V2 | `integrated_grid`, `integrated_grid_v2`, `echo45_grid`, `echo45_grid_v2` | Candidatos históricos; desarrollo mejoró pero el seguimiento disjunto V1/V2 quedó 1/128. Conservar referencias, no presentar transferencia general. |
| Integración V3 | `echo45_v3` | CLI que carga memoria/política y llama al solver relacional, con guía opcional. Es una integración de rejillas, no toda la robótica ni todo ECHO-4. |
| Guía asociativa | `kenyon_capacity`, `verified_program_guide` | `SparsePrimitiveGuide` y `ProgramGuide`: contadores uint8 con capacidad configurable. 500.000 posiciones no son 500.000 neuronas LIF. |
| Estudios de capacidad | `kenyon_arc1`, `kenyon_bench`, `associative_stress*`, `capacity_*`, `program_guide_campaign` | Evaluación, diagnóstico y media del banco. Mantener separados del ranking usado en inferencia. |
| Campañas de integración | `integration_campaign`, `integration_followup`, `integration_report`, `integration_revision`, `integration_transfer`, `arc_capabilities`, `arc_comparison`, `echo45_completion` | Evaluación y preparación del cierre. No ejecutar durante la integración como si fueran pruebas unitarias. |
| Evaluación por lotes | `arc_v3_batch`, `arc_b24_closure` | Separación de etiquetas, presupuesto, procesos por tarea, custodia y gating de B24. La calibración conocida fue 0/16 por corpus; lote público completo pendiente. |
| Cierres anteriores | `final_arc`, `final_eval`, `final_campaign`, `final_audit_recovery` | Instrumentos históricos; reservar su alcance y procedencia, no repetir exámenes para comprobar una refactorización. |

Evidencia: [V3](../../docs/ECHO45-RELATIONAL-V3-RESULTS.md),
[memoria 3E](../../docs/ECHO45-EGO-MEMORIA3-RESULTS.md),
[S1](../../docs/ECHO45-S1-RESULTS.md),
[inventario de resultados](../../docs/ECHO45-CLOSURE-EVIDENCE-20261009.md).
REL/MEM/SYN/VIEW/CONS/GUIDE tienen verdes acotados; estos no certifican ventaja
ARC general ni integración automática con robótica.

## Juegos, investigación S6 y RSI

| Familia | Ubicación | Disposición |
|---|---|---|
| Actor ARC | `echo_arc/agent.py`, `runner.py`; antecedente `echo4/arc3_agent.py` | Actor especializado derivado de ECHO-4, con diario propio; su cabecera declara que no importa el núcleo ECHO-4. No confundirlo con el agente completo. |
| H1/H3 | `echo_arc/temporal_agent.py`, `temporal_memory.py`, `temporal_runner.py`, `temporal_bench.py`, `temporal_audit.py` | v5.8 amplía v5.7 con orden y conteo; separar actor, ejecutor, observación y juez. [Examen documentado](../../docs/ECHO45-H1-H3-EXAM2-RESULTS.md). |
| Mundos de desarrollo | `seed/arc3gym.py`, `echo_arc/runner.py` | Simulación y adaptación al SDK; el agente no debe recibir estado privado del simulador. |
| Estrategias y parches | `echo_arc/strategy*`, `temporal_policy*`, `local_patch*`, `precise_patch*`, `parameter_first_grammar`, `stale_transition`, `feasible_grammar`, `contrastive_grammar`, `repair_loop_grammar` | Lenguajes acotados con validadores; no un sistema de modificación arbitraria del núcleo. |
| Evidencia y observación | `echo_arc/*observe.py`, `repair_evidence`, `consumption_evidence`, `consumption_timeline`, `contrastive_evidence`, `transition_evidence`, `repair_diagnostics`, `repair_outcomes` | Observaciones y atribuciones acotadas; los textos del visor no alimentan al agente. |
| Selección y contexto | `consumer_requests`, `context_requests`, `context_tokenizer`, `contrastive_requests`, `feasible_requests`, `repair_loop_requests`, `repair_memory`, `repair_experiments` | Selección de evidencia y experimentos, límites de contexto y memoria del investigador. No acreditar utilidad por mera existencia. |
| Síntesis e investigadores | `guard_synthesis`, `guard_search`, `cost_guard_search`, `s6b20_search`, `s6b21_archive`, `s6b21_search`, `s6b22_search`, `s6b23_search`, `s6b23r4_search`, `s6b24_search` | Linajes de investigadores versionados; B24 estudia reparación y cooperación. Preservar cada contrato, no seleccionar versiones por número sin prueba. |
| S6 inicial | `seed/selfimprove.py`, `game_selfimprove*.py`, `s6_capacity`, `s6_precise_*`, `s6_prompt_pilot`, `s6_transition_capacity`, `s6_followup_report` | Ensayos, contratos y utilidades compartidas. S6 no superado. |
| B6–B24 y PROBE | `seed/s6b6*` a `seed/s6b24*`, `seed/s6probe*` | Orquestación, LLM, preflight, custodia, auditorías y cierres históricos. B24 congelado; no importar la campaña en el runtime ECHO-5. Cada archivo está en el catálogo. |
| RSI1 privado | `seed/rsi1`, `rsi1_queue`, `rsi1_recovery1` | Ensayo de biblioteca DSL, sin modificación general de pesos. [Resultado](../../docs/ECHO-RSI1-RESULTS.md): `RSI1_green=false`, sin mejora sucesiva acreditada. |

S6 y RSI son programas experimentales distintos. La existencia de una cola,
un modelo que propone o un parche que gana en desarrollo no acredita
automejora recursiva. La investigación nueva se difiere a después de 5.5.

## Dependencias y obstáculos antes de mover código

1. **Cinco dependencias host viven fuera de esta carpeta.** El namespace y
   el empaquetado de ECHO-5 deben incluirlas o definir adaptadores explícitos.
   Eliminar `navi10_*` por su nombre rompería imports activos.
2. **Hay identidades de importación múltiples.** Por ejemplo, V3 usa tanto
   `seed.arc_memory` como `echoai.seed.refinement`. Si una misma fuente se
   carga bajo dos nombres, puede duplicar estado global. Hay que fijar un
   namespace y comprobar equivalencia antes de migrar.
3. **Memoria depende de un archivo de campaña.** `arc_memory` y `village2`
   importan hashes/canonización desde `seed/game_selfimprove.py`, que a su vez
   importa actores y ejecutores ARC. Extraer una biblioteca de recibos será
   una intervención nueva, con comparación de bytes y comportamiento.
4. **Versión antigua no significa archivo prescindible.** 3E hereda de
   `village3_efficient` y `village3_factorized`; la política ARC hereda de
   `village3`. La robótica también compone versiones previas. Suprimir estos
   antecesores rompería la versión más reciente.
5. **El escáner identifica 16 componentes con ciclos potenciales de imports.**
   Incluyen núcleo, observador/runner, campañas y algunos imports de tests
   desde benches. Muchos imports son condicionales; esto no demuestra un
   error de ejecución. El detalle permite separar biblioteca y evaluador.
6. **Las dependencias pesadas pertenecen a adaptadores concretos.** NumPy/ARC,
   Gazebo/PX4/pymavlink/pyulog, PyTorch/transformers, GUI/VTK, Textual y Blender
   no deben instalarse juntas por defecto. El listado de imports externos
   también contiene nombres locales inyectados al empaquetar; no es un
   fichero de requisitos instalable.
7. **Hay varias superficies de interfaz y varios conceptos de memoria.**
   CAM, diario causal, archivo de hipótesis y Q no son intercambiables. La
   nueva interfaz debe señalar qué agente, memoria y registro está mostrando.
8. **Las rutas y artefactos son parte de los contratos.** Rutas absolutas,
   snapshots, modelos externos, mundos y hashes no están encapsulados en una
   única distribución. Hay que inventariar los recursos del candidato elegido
   además de su cierre transitivo de imports antes de prometer instalación.

Orden propuesto: fijar límites de paquete y procedencia; definir recibos y
estado sin mover las fuentes congeladas; adaptar el núcleo; recuperar la
cadena robótica SITL; conectar capacidades V3 mediante interfaces explícitas;
incorporar observabilidad y después GUI. Neocórtex, multiagente y dreaming se
integrarán con pruebas propias y controles de coste. La integración sigue
pendiente: este inventario es su punto de partida, no su validación.

Reproducción del inventario, sin imports del agente ni acceso a datos de examen:

```sh
cd ECHO-5
.venv/bin/python -I scripts/inventory.py
make check
```

`harness/localdev/inventory.py` ya contiene un analizador general para su
arnés. El script de esta revisión produce un corte específico, con alias,
dependencias host y enlaces documentales; no importa el arnés histórico ni
lo sustituye. No se ha añadido lógica cognitiva ni se han instalado paquetes.
