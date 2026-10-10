# ECHO-4, interfaces y distribución

Revisión estática del 10 de octubre de 2026. Resultados citados desde informes
existentes, sin reejecutar sus pruebas ni abrir partidas reservadas. Los
109 Python de `echo4/` están enumerados en el [catálogo](inventory/CATALOG.md).

| Familia | Archivos de echo4 | Evidencia y límite |
|---|---|---|
| WORLD/SENSATION/BOUNDARY | `world`, `viability`, `adapter`, `sensation*`, `boundary*` | Cuerpo térmico, predictor e intervenciones. [SENSATION](../../docs/ECHO4-SENSATION1-CLOSURE.md) y [BOUNDARY](../../docs/ECHO4-BOUNDARY1-RESULTS.md) cierran bancos propios; WORLD inicial es factibilidad. |
| SELF | `self_model`, `self_attribution`, `self_*agent`, `self_final` y auditores | [SELF](../../docs/ECHO4-SELF1-FINAL-RESULTS.md): diagnóstico propio/externo y reutilización de T bajo física nominal; no causalidad general. |
| CONTINUITY | `continuity`, `continuity_graph`, `continuity_active`, `continuity_lineage`, bancos y auditores | [CONT-D](../../docs/ECHO4-CONTINUITY1-D-RESULTS.md): 69/69 checkpoints, 300/300 eventos posteriores idénticos y 30/30 mutantes rechazados; perfil síncrono declarado. |
| DREAM | `dream_history`, `dream_probe`, `dream_policy`, `dream_qwen`, `dream_v2`, `dream_v3*` | [v3](../../docs/ECHO4-DREAM1-D-V3-RESULTS.md): 900/960 frente a fijo 640 y aleatorio 721; sin Qwen también 900. Catálogo de diagnóstico y ramas disponibles; no RSI ilimitado. |
| MAINTAIN | `maintain_world`, `maintain_model`, `maintain_agent`, `maintain_control`, `maintain_continuity` | [Cierre](../../docs/ECHO4-MAINTAIN1-FINAL-RESULTS.md): mantenimiento, reparación y parada en mecánica declarada; no autorreparación general de código. |
| OTHER/INTERACTION | `other_model`, `other_world`, `other_replay`, `interaction_*` | [INTERACTION](../../docs/ECHO4-INTERACTION1-BCD-RESULTS.md): modelado de contrapartes y Q contextual; costes de formación limitan la ventaja. |
| RELATION | `relation_memory`, `relation_session`, `relation_help`, `relation_c`, `relation_d` | [RELATION-D](../../docs/ECHO4-RELATION1-D-RESULTS.md): historia por contraparte y ayuda; reciprocidad diseñada, impostores aún pueden engañar. |
| ROLES/TRIBU | `roles*`, `tribe`, `tribe_v4`, `tribe_exam`, `tribe_liar*` | [Consolidado](../../docs/ECHO4-ROLES1-COMPLETO.md): deducción, rango y testimonio con tres agentes; orden fijo produce más neto, sin superioridad general del enjambre. |
| SITUATE | `situate`, `situate2` y bancos | [SITUATE2](../../docs/ECHO4-SITUATE2-RESULTS.md): identidad desde señales del proceso y clasificación de afirmaciones; no prueba de conciencia. |
| INTEGRATE | `integrate`, `integrate_bench`, `integrate_exam` | [Cierre](../../docs/ECHO4-INTEGRATE1-RESULTS.md): cuerpo y tribu comparten CAM/T/Q, 48/48 reanudaciones exactas. Tribu alimenta cuerpo, coste corporal no condiciona decisiones sociales. |
| CODE/MCP | `code_memory`, `code_gate`, `code_mcp`, `code_exam` | [CODE-A](../../docs/ECHO4-CODE1-A-RESULTS.md): evidencia, ocho herramientas y gate; examen no ciego, checks del operador confiables; no prueba de programar mejor. |
| Bancos externos | `bench1`, `arc2_bench`, `arc3_agent`, `arc3_llm`, `arc3_llm2`, `arc3_view` | SimpleQA/GSM8K/ARC y representación de frames. Ver resultados por condición; no atribuir puntuaciones oficiales a un replay local. |

[ARC2](../../docs/ECHO4-BENCH-ARC2-RESULTS.md) quedó rojo;
[ARC3](../../docs/ECHO4-BENCH-ARC3-RESULTS.md) conserva una corrección de score;
[ARC3+LLM](../../docs/ECHO4-BENCH-ARC3-LLM-RESULTS.md) no acreditó ventaja sobre
el agente solo. La presencia de un adaptador cortical no demuestra que ayude.

Las pruebas asociadas viven principalmente en `tests/test_echo4_*.py`.
El JSON del inventario enumera imports estáticos de cada prueba; no mide
cobertura ni afirma que pasen hoy. Los README antiguos conservan estados
anteriores a cierres posteriores: priorizar contrato, revisión e informe.

| Interfaz/herramienta | Implementación | Qué reutilizar y qué revisar |
|---|---|---|
| GUI4 | `gui4/{app,catalog,neural,benchmark,evidence,capture}.py` | Tkinter/Pillow, siete pestañas, PNG/vídeo y catálogo LIVE/BENCH/EVIDENCE. [Resultados](../../docs/GUI4-RESULTS.md): 32 pruebas documentadas. Acoplada a RuntimeEngine/TaskSpec anteriores y recursos locales; no una GUI web ECHO-5. |
| Observabilidad | `observe.py`, `observe_b5.py`, `echo_arc/*observe.py` | Lectura incremental, hashes y resultados. [Contrato](../../docs/ECHO45-OBSERVABILITY.md). Los modos launch pueden ejecutar desarrollo; leer una cola no certifica la cadena histórica entera. |
| METAVERSE | `metaverse1/{world,declare,sdf,bench}.py`, `assets/` | Retícula, SDF/GLB y custodia. [META-WORLD-2](../../docs/METAWORLD2-RESULTS.md) y [custodia](../../docs/METAVERSE1-CUSTODY-RESULTS.md). Geometría verificada; programa completo abierto. Blender en generación de assets. |
| echo-nexus | `harness/echo-nexus/src/echo_nexus/` | TUI Textual 1.5.1, perfiles, streaming, conexiones, asesor y MCP. [Resultados 1.5](../../docs/ECHO45-HARNESS15-RESULTS.md). Arnés público MIT separado; recibe JSON/procesos, no importa el agente. |
| Puentes privados | `harness/local_bridge.py`, `dev_bridge.py` | Catálogo y ejecutores del laboratorio, perfiles y telemetría. local_bridge declara que no debe exportarse al repositorio público del arnés. |
| Desarrollo local | `harness/localdev/{inventory,common,runner,worker,cpu_contracts,engine}.py` | AST, copias aisladas, Bubblewrap, límites y comprobaciones. [Resultados](../../docs/ECHO-LOCALDEV-RESULTS.md): ingeniería del arnés, no RSI. |
| Publicación | `harness/s6_publication.py` | Operaciones Git/web y recibos B11; mantener fuera de visores y procesos sin autorización de publicación. |
| Distribución | `release1/{build,cleanroom,review}.py`, `echoai_release/` | Nuitka, CLI, identidad, reproducción y córtex opcional. [RELEASE](../../docs/ECHO4-RELEASE1-RESULTS.md) y [ficha posterior](../../docs/RELEASE_2026-09-24.md). |

La distribución merece una frontera propia. `release1/build.py` empaqueta
`echo4`, `nexus0`, `tests` y seis módulos del padre, incluyendo
`navi10_stdp` como entrada declarada aunque el inventario no encuentre un
import directo desde las familias científicas. No empaqueta automáticamente
GUI4, METAVERSE, harness ni pesos. La wheel documentada usa CPython 3.14/Linux
x86_64: no debe instalarse como si fuera compatible con el setup 3.12 de ECHO-5.

El release instala un `.pth` que carga `echoai_release/_hook.py`, modifica
la importación y activa reemplazos de huellas en `identity.py`. No es una
biblioteca pasiva de inspección; requiere manifiesto y binarios propios.
La EULA aparece como borrador y la reproducción de tercero REL-D pendiente
en la ficha revisada. No se comprobó publicación remota en esta revisión.

Hallazgos de integración:

- `integrate.py` importa una sesión de `tribe_exam.py`: runtime y banco no
  están completamente separados.
- CONTINUITY serializa estado; `INTEGRATE.resume` reconstruye desde el inicio
  y verifica huella. Son mecanismos con costes y requisitos distintos.
- DREAM propone programas, SITUATE filtra afirmaciones y echo-nexus conversa
  como asesor. No existe evidencia aquí de un neocórtex único que coordine
  automáticamente todas esas funciones.
- Una ventana neuronal puede ser un monitor sin influencia causal en las
  acciones. La GUI debe mostrar esa diferencia junto a ejecución/replay/evidencia.
- Los stubs corticales, dobles HTTP y el mutador de `clamp` del arnés sirven
  para probar contratos de ingeniería. No acreditan autonomía ni aprendizaje.

Antes de integrar, definir qué objetos de estado se comparten y cuáles son
privados de cada adaptador; después medir la composición. El inventario no
autoriza a fusionar bancos, importar hooks del release ni reabrir exámenes.
