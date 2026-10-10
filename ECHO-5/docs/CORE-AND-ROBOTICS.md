# Núcleo y robótica: inventario de familias

Revisión estática del 10 de octubre de 2026. 385 Python en `nexus0/`,
incluidos 58 módulos raíz. Estados tomados de informes, sin ejecutar bancos
ni abrir datos de exámenes. El [catálogo](inventory/CATALOG.md) enumera cada
archivo, incluidos runners, mutantes y auditores de subdirectorios.

| Familia | Archivos raíz de nexus0 | Función y alcance |
|---|---|---|
| Contratos | `__init__`, `constants`, `types` | Exportaciones, estado y métricas; tres acciones por defecto, ampliaciones explícitas. |
| Representación | `encoder`, `lex` | Banco canónico y léxico WSP; FNV como baseline. El léxico ya se portó; el spec inicial no refleja todas las revisiones. |
| Control | `loop`, `qtable`, `world`, `gate` | Agent, CAM, Q, T, conflictos, aprendizaje y veto; extensiones opt-in. |
| Deliberación | `plan`, `escalate`, `attend`, `oracle` | Lookahead, escalada y testimonios externos. Preguntar no equivale a moverse. |
| Mundos iniciales | `env`, `bench`, `corridor`, `graph` | Anillo, pasillo y grafo de 256 nodos; transferencia topológica acotada. |
| Córtex | `cortex`, `cortex_turn`, `sign`, `signc`, `qwen_sign`, `qwen_signc` | Contratos y experiencias de señal cortical; Qwen opcional, fuera del banco basal. |
| Cuerpo 2D | `body` | CUERPO/WALK/CREDIT; variantes de crédito y navegación con sus controles. |
| Cuerpo 3D | `body3d`, `self1`, `room1` | Cuerpo abstracto, atribución motor/suelo y habitaciones. No aerodinámica real. |
| Objetos | `obj1`, `open1` | Recoger, transportar, entregar y abrir; cuatro acciones opt-in en OPEN. |
| Contexto y transferencia | `pattern`, `pattern0`, `xfer1` | Contexto de orden dos y conservación de CAM/Q/T/patrón. XFER-1d incorporado en xfer1. |
| Registro e interfaces | `thought`, `view`, `demo`, `board`, `talk`, `talk1`, `neural_viz`, `neural_viz_gui` | Diario, subtítulos, HTML y visores live. Algunos modos ejecutan al agente. |
| Vida y adaptación | `vita1`, `food1`, `echo2`, `shifts` | H, alimento, muerte terminal, renacimiento y cambio del entorno. |
| Percepción y consolidación | `pattern1`, `stream1`, `sleep2` | Familias binarias, WSP externo y reglas consolidadas. SLEEP no gobierna por sí solo la política. |
| Herencia | `gen1`, `gen1b`, `gen1c`, `gen1d`, `gen1e`, `gen1f` | GEN-1f de referencia hereda sólo evidence_budget=8; memorias del hijo nuevas. Helpers antiguos aún se importan. |
| Homeostasis | `heat1`, `heat1b` | HEAT-1b de referencia; temperatura/recursos enteros simulados. |
| Capacidad LIF | `capacity1` | 256/512 LIF y Adaptive-LIF128 en banco CPU; no sustituye Q/CAM/gate. |
| Cierres históricos | `flight1s_v4_close`, `flight1s_v5_close` | Herramientas para conservar resultados de cadenas interrumpidas. |

Fuentes: [estado consolidado](../../docs/STATUS.md),
[antecedentes ECHO-2](../../docs/ECHO2-START.md),
[guía de visualización](../../docs/NEURAL-VIZ1-GUIDE.md).
ECHO-1/2 constan cerrados en sus dominios; eso no acredita una capacidad
general de robótica o de razonamiento fuera de los bancos declarados.

Los 31 subdirectorios directos incluyen `bank/`, `tools/` y las siguientes
29 carpetas de familias/revisiones de robótica. Los nombres entre llaves
en la tabla denotan varios directorios existentes, no un paquete nuevo.

| Familia / revisiones | Implementación y dependencias | Referencia documental y límite |
|---|---|---|
| `sim3` | Geometría, SDF, declaraciones, aislamiento, sesión, custodia, evaluación y mutantes | [SIM-3](../../docs/SIM3-RESULTS.md): infraestructura, física y separación de información; no agente autónomo volando. |
| `flight1s`, `flight1s_v4`, `flight1s_v5`, `flight1s_v6`; v2/v3 dentro de flight1s | Runtime, protocolos, runners y campañas; v6 reutiliza componentes de revisiones anteriores | [v6](../../docs/FLIGHT1S-V6-RESULTS.md) verde SITL; v1/v2/v4/v5 rojas, v3 sin certificado. |
| `sensor1s`, `sensor1s_v2`, `sensor1s_v3` | Modelos, contrato, canal aislado, evaluadores; FLIGHT v6 | [v3](../../docs/SENSOR1S-V3-RESULTS.md) verde en sensores simulados. Reutiliza v1/v2 rojas. |
| `ground1`, `ground1_v2` | Consumidor de sensores a WSP, evaluador, sesión; v2 corrige llegada/timestamp | [v2](../../docs/GROUND1-V2-RESULTS.md) verde; identidad CAM exacta, no simple proximidad Hamming. |
| `dynamic1`, `dynamic1_v2` | Seguimiento de caras y runners de pared móvil | [v2](../../docs/DYNAMIC1-V2-RESULTS.md) verde desde hover, movimiento normal de pared; no evasión general. |
| `pattern1r`, `pattern1r_v2`, `pattern1r_v3`, `pattern1r_v4` | Consumidores LiDAR, recorrido, memoria y evaluación; extienden pattern1 | [v4](../../docs/PATTERN1R-V4-RESULTS.md) verde en dos familias; v1–v3 rojas. Recorrido impuesto y examen por replay. |
| `fusion1` | `core`, `integration`, `judge`, `scenarios`, `replay`, `bench`; gate basal | [FUSION](../../docs/FUSION1-RESULTS.md) funcional y replay: caducidad, correlación, conflicto y procedencia. |
| `compose1`, `compose1_v2`, `compose1_v3`, `compose1_v4` | Effects, controlador, percepción, escuela y transportes; v4 usa runtime v3 y bases previas | [v4](../../docs/COMPOSE1-V4-RESULTS.md) verde; altura fija, salas extruidas, energía abstracta. Sin superioridad sobre convencional. |
| `cause1` | Percepción, consumidor, transporte, sesión y evaluación | [CAUSE](../../docs/CAUSE1-RESULTS.md) verde frente a pared plana; hipótesis, no escritura automática en CAM/T/Q. |
| `px41` | Gateway, sesión, evaluación, controles y runner | [PX4](../../docs/PX41-RESULTS.md) verde en objetivos acotados; ACK no equivale a llegada. |
| `power1` | Guard, mundo, telemetría, consumidor y controles | [POWER](../../docs/POWER1-RESULTS.md) verde funcional; reserva y retorno, sin consumo físico acreditado. |
| `safe1`, `safe1_v2` | Core, servicio, IPC, supervisor y fallos; v2 corrige banco/auditor | [v2](../../docs/SAFE1-V2-RESULTS.md) verde acotado; runtime v1 sigue en uso. |
| `host1` | Fuente/signo/contexto, consumidor, transportes, replay y probes | [HOST](../../docs/HOST1-RESULTS.md) verde funcional/replay; no confianza humana general. |
| `transfer3` | 52 módulos, escuelas y ramas A/B/C; reutiliza COMPOSE/FUSION/SIM | [Índice](../../docs/TRANSFER3-INDEX.md): C1 verde software con su enmienda; A/B negativos conservados. |
| `drone3` | MissionAgent, calibración, energía, gates, gateway, supervisor, transporte y sesión | [DRONE](../../docs/DRONE3-RESULTS.md): B/C 12/12; SITL verde. HIL y jaula pendientes. |

`transfer3/` requiere especial cuidado: la línea C1 vigente incluye
`calib_c1`, `camera_c1`, `planner_c1`, `consumer_c1`, `transport_c1`,
`school_c1`, `bench_c1`, `custodian_c1`, `campaign_c1`. Reutiliza piezas
de ramas anteriores como `planner_a2`. «Campaña C1 v2» es una revisión del
protocolo, no un directorio `transfer3_v2`. El catálogo conserva los 52 módulos.

`assets/` incluye Python ejecutable de consumidores, runners y mutantes;
no se debe excluir sólo por el nombre. Hay Containerfiles, modelos SDF/config
y recursos externos de PX4. `tools/gen_lex.py` lee el léxico de
`../legacy/kernel-navi/wsp_lex.c`; `bank/canonical.json` y las gramáticas son
recursos de la interfaz. Gazebo, PX4, Podman, Bubblewrap, pymavlink y pyulog
requieren un perfil de instalación separado; esta revisión no comprueba su
disponibilidad ni reconstruye imágenes.

Los principales límites arquitectónicos son concretos:

- `nexus0/loop.py` aloja el Agent basal. La robótica usa `compose1/model.py`
  con Cam, World/Q de siete acciones y después Composer/MissionAgent. Comparte
  primitivas; no demuestra que todo el Agent basal esté integrado en DRONE.
- LIF no elige actualmente la acción basal. `encode_event` proporciona
  representación/ticks y la política usa Q/T/gate. CAPACITY ejecuta Layer256;
  las visualizaciones LIF no acreditan que esa dinámica gobierne las acciones.
- El gate actual devuelve decisión, acción y flags, frente al par del spec
  inicial. Q/T usan enteros en listas Python; tamaños lógicos int8/uint16 no
  equivalen al consumo real de memoria Python. Fijar contratos actuales antes
  de crear adaptadores.
- DRONE combina COMPOSE, FUSION, calibración C1, POWER, SAFE y PX4. HOST,
  PATTERN-1R y DYNAMIC no deben declararse integrados sólo por vivir en nexus0.
- FLIGHT v6, SENSOR v3, GROUND v2, COMPOSE v4 y SAFE v2 necesitan archivos de
  versiones anteriores. El resultado rojo histórico no implica código muerto.
- Algunas custodias históricas incluyeron todo el árbol nexus0. Añadir o mover
  archivos puede invalidar su reconstrucción aunque no cambie el agente.
  ECHO-5 debe mantener referencias congeladas y declarar su propia integración.

La herencia robótica se recuperará desde estos contratos y dependencias;
esta revisión no vuelve a ejecutar vuelos ni promete validación física.
