# echoAI y ECHO-3: qué existe y cómo funciona

**Guía para usuarios · estado contrastado el 18-09-2026.** echoAI es el agente; ECHO-1, ECHO-2 y ECHO-3 son etapas de validación de sus capacidades. No son nombres de tres modelos de lenguaje.

## La respuesta a «¿ya tenéis un híbrido SNN/LLM?»

**Sí: echoAI ya dispone de componentes spiking y de una vía opcional hacia un LLM real, dentro de una arquitectura de dos relojes.** Además incluye memoria, modelos de predicción, política discreta, aprendizaje por consecuencias y un gate que puede vetar propuestas. Esas piezas importan tanto como la red neuronal y el modelo de lenguaje.

El reloj rápido funciona con el córtex apagado. El reloj lento interpreta información cuando ATTEND encuentra una razón para consultarlo. La propuesta del LLM debe cumplir un formato restringido y pasar por el gate. No escribe hechos verificados ni manda motores.

La demostración local con Qwen ya existe. **La integración completa de ese LLM con una misión robótica continua y con echOS todavía no está certificada.** Los hitos ECHO-3 citados aquí prueban componentes y vuelos simulados con el córtex apagado. Por tanto, proponer «añadir un LLM para crear el híbrido» ignora trabajo existente; proponer cómo integrar su salida lenta sin afectar al control sigue siendo una pregunta pertinente.

## Qué hace cada pieza, en lenguaje cotidiano

| Pieza | Pregunta que resuelve | Implementación y límite |
|---|---|---|
| **WSP** | ¿Cómo representamos lo observado o propuesto? | Paquete cognitivo fijo de 16 bytes. Una propuesta y un hecho pueden compartir formato sin compartir autoridad |
| **CAM** | ¿Qué ocurrió y qué evidencia quedó? | Memoria episódica de 4.096 ranuras; conservar un episodio no obliga a seguir confiando en él |
| **T** | ¿Qué suele suceder después de esta acción? | Modelo de transición aprendido; conserva evidencia y conflictos |
| **PATTERN** | ¿Importa lo que pasó antes? | Reconoce regularidades temporales que una observación aislada no distingue |
| **Q** | ¿Qué acción ha resultado útil? | Política con valores enteros, separada de la memoria episódica |
| **Búsqueda/composición** | ¿Qué combinación de pasos permite cumplir la meta? | Planificación acotada usando observaciones y efectos disponibles; no conocimiento del mapa secreto |
| **Gate** | ¿Se puede ejecutar esta propuesta en el estado actual? | Acepta, modifica o bloquea; el resultado se registra |
| **ATTEND** | ¿Hace falta consultar el reloj lento? | Usa condiciones como novedad, baja confianza, información ausente o contradicción |
| **Córtex / Qwen** | ¿Puede una interpretación de lenguaje aportar una propuesta? | Adaptador opcional en host; salida restringida y sin autoridad directa |
| **SLEEP** | ¿Qué regularidades se pueden compactar fuera del paso rápido? | Consolidación sin convertir una simulación o relato en episodio observado |

El circuito básico es `percibir → representar → recordar/predecir → proponer → filtrar → actuar → observar consecuencia → aprender`. Puede ejecutarse sin generar una frase de lenguaje natural.

## Dónde están las neuronas spiking

Hay código neuronal real, no sólo una ilustración. CAPACITY-1 evaluó **512 LIF + 128 Adaptive-LIF**. En el banco perceptivo, 512 LIF obtuvo **2.048/2.048** firmas reservadas frente a **829/2.048** con 256 LIF. En el temporal obtuvo **256/256** frente a **0/256** del control del mismo tamaño sin adaptación. [Informe CAPACITY-1](../../lab/echo2_capacity1_report.json) y [contrato](../CAPACITY1-DESIGN.md).

Esto acredita esos bancos concretos, no comprensión visual general. En NEURAL-VIZ-1, la rama LIF/Adaptive-LIF se presenta como **monitor perceptivo**: observa el WSP y muestra actividad. La política causal del agente representado sigue pasando por CAM/Q/gate. No es correcto afirmar que esas 640 neuronas gobiernan directamente los motores o que toda decisión de ECHO-3 procede de ese banco neuronal. [Guía de la demostración](../NEURAL-VIZ1-GUIDE.md).

La SNN de PRISMA es otra implementación orientada a señal EEG. Compartir LIF o STDP no hace que los tres proyectos sean una única red ni que compartan pesos.

## Qué se probó con el LLM real

El informe **Qwen-0** identifica Qwen3-4B-Instruct-2507, cuantización Q4_K_M, en host x86_64. La tarea era interpretar letreros y proponer acercarse o evitar, bajo contrato; no conversar libremente ni pilotar un dron.

| Resultado conservado | Interpretación |
|---|---|
| 8/8 letreros resueltos | Resultado de ese pequeño banco |
| 6/6 paráfrasis frente a 0/6 del comparador por reglas | El modelo aportó interpretación de lenguaje que aquel comparador no cubría |
| `CortexROI_canonical = 16` | Diferencia de recompensa en una prueba definida; no porcentaje de mejora general |
| 1,6178 s de media | Tiempo de esas consultas en ese host; no presupuesto para cada tick robótico |
| `false_facts = 0`, `qwen_rejected = 0` | Contadores de esa ejecución, no garantía universal |

Fuente: [JSON Qwen-0](../../lab/nexus0_qwen4b_report.json). El [adaptador real](../../nexus0/tools/qwen_cortex.py) y el [contrato del córtex](../../nexus0/cortex.py) están implementados. Los bancos principales no dependen del modelo ni de sus pesos.

**Nota sobre SIGN-C:** el historial documenta una ejecución positiva con Qwen, pero el JSON de trabajo consultado ahora contiene `model_configured=false` y `green=false`. No se usa ese archivo para acreditar el resultado histórico positivo. Una ejecución sin modelo configurado tampoco mide el rendimiento de Qwen. La evidencia numérica del LLM que se cita en esta guía es Qwen-0. [Estado del archivo consultado](../../lab/nexus0_qwen_signc_report.json).

**Dos relojes no significa que todo aislamiento temporal esté terminado.** `cortex.complete()` espera un subproceso en la ruta host inspeccionada. La GUI coloca el trabajo del agente en otro hilo para mantener el render, lo cual no prueba que un controlador de vuelo pueda seguir atendiendo sus plazos durante esa espera. Un servicio lento desacoplado, con descarte de respuestas caducadas y pruebas de carga, sigue siendo trabajo de integración; no un motivo para introducir el LLM en el lazo rápido.

## Qué añadieron ECHO-1 y ECHO-2

ECHO-1 cerró un ciclo situado con memoria, predicción, aprendizaje, objetos, acciones, patrones y transferencia en sus mundos de prueba. ECHO-2 añadió viabilidad, cambios de distribución, procesamiento en flujo, consolidación, herencia acotada y regulación de energía/temperatura **simuladas**. Las muertes, nacimientos y variables corporales de estos bancos son estados computacionales, no organismos vivos.

La demostración neuronal nativa permite observar decisiones, memoria, atención y propuestas del córtex. Su dron dibujado representa Body3D; ese render por sí solo no simula aerodinámica. El paso a dinámica de vuelo realista corresponde a los bancos posteriores de Gazebo/PX4 en ECHO-3. [Cierre ECHO-2](../ECHO2-START.md), [estado vigente](../ECHO3-STATUS-20260917.md).

## ECHO-3: capacidades robóticas que ya se han ensayado

**13 de 15 hitos tienen certificado verde en su alcance software.** Es una cuenta de hitos, no un porcentaje de seguridad, rendimiento ni trabajo restante.

| Hito | Qué demuestra su versión vigente | Dónde termina la demostración |
|---|---|---|
| SIM-3 | Infraestructura de simulación y aislamiento del agente | Host, no robot físico |
| FLIGHT-1S v6 | Ejecución de vuelo con PX4 | Simulación |
| SENSOR-1S v3 | Sensores con tiempos, fuente y procedencia | Señales simuladas |
| GROUND-1 v2 | Traducción de observaciones físicas a WSP | Ontología y tareas del banco |
| PATTERN-1R v4 | Identidad entre observaciones en dos familias LiDAR | Examen por replay; no reconocimiento universal |
| FUSION-1 | Caducidad, evidencia y tratamiento de conflictos | Banco funcional y replay delimitado |
| DYNAMIC-1 v2 | Movimiento de una cara observada desde hover | No seguimiento general de cualquier objeto |
| COMPOSE-1 v4 | Composición de pasos y ejecución bajo PX4 | Salas extruidas, altura fija y recursos simulados |
| CAUSE-1 | Atribución propia/externa en movimiento frente a una pared | No causalidad general ni fuerzas externas arbitrarias |
| PX4-1 | Objetivos acotados, confirmación y failsafe | Transacciones supervisadas de una tarea concreta |
| POWER-1 | Decisiones considerando coste previsto y reserva | Energía simulada, no batería física medida |
| SAFE-1 v2 | Contención de fallos y aterrizaje nativo PX4 | Fallos y condiciones preregistrados |
| HOST-1 | Autoridad de fuente/signo/contexto actualizada por consecuencias | Calibración y cinta de máquina; no confianza psicológica humana |
| **TRANSFER-3** | Escuela y mecanismos implementados, ensayos negativos conservados | **Rojo: mejora útil transferida no confirmada; sin candidato** |
| **DRONE-3** | Contrato de misión integrada definido | **Pendiente: integración completa y después hardware/HIL/jaula** |

Fuentes: [estado por fase](../ECHO3-STATUS-20260917.md), [contrato ECHO-3](../ECHO-3-ACCEPTANCE.md) y [último resultado TRANSFER-3 B3](../TRANSFER3-PLAN-B3-RESULTS.md). La situación posterior del diario prima sobre entradas antiguas.

### Ejemplos concretos de lo conseguido

COMPOSE-1 v4 registra **6.144 misiones funcionales y 32 vuelos nuevos Gazebo/PX4**. El agente completo alcanzó las seis metas accesibles de aceptación. En el banco funcional mostró ahorro de movimientos frente a horizonte uno; **el comparador convencional quedó prácticamente empatado**. No se declara superioridad que el ensayo no encontró. [Resultados](../COMPOSE1-V4-RESULTS.md), [JSON](../../lab/echo3_compose1_v4_report.json).

SAFE-1 v2 registra **diez fallos contenidos mediante aterrizaje nativo PX4**, con veto máximo observado de **288 ms**. Esto es una medida del camino de integración simulado y de sus fallos ensayados, no del coste aislado de una función ni un plazo garantizado. [Resultados](../SAFE1-V2-RESULTS.md).

HOST-1 registra **1.536/1.536 decisiones útiles frente a 768/1.536 del control por etapa**. Aprende a valorar una fuente según consecuencias; no mide cuán convencido está un usuario de una intención y no valida aún una BCI humana. [Resultados](../HOST1-RESULTS.md).

## Qué implica para las sugerencias de otra IA

| Sugerencia | Respuesta con el estado actual |
|---|---|
| «Añadid SNN y un pequeño LLM» | La arquitectura híbrida ya existe. Identificar primero qué capacidad falta y dónde encaja con ATTEND, política y gate |
| «Que el modelo estime la confianza del usuario» | Distinguir calidad de señal, probabilidad calibrada del decoder, autoridad de una fuente y seguridad de una acción. Ninguna equivale sin validación a confianza subjetiva |
| «Dad más autoridad a medida que el sistema confíe» | HOST-1 es antecedente de autoridad por consecuencias. Un entrenamiento humano progresivo sería nuevo; sus límites no deben relajarse por un score aislado |
| «Añadid feedback corporal» | Sigue siendo una pieza relevante de NEURO-DRON, pendiente de implementación y ensayo |

## Preguntas actuales para una revisión útil

1. ¿Qué contrato permite consumir una propuesta lenta sin esperar al modelo, y cómo se descarta si el mundo ya cambió?
2. ¿Qué evidencia añadirá una propuesta de PRISMA sin confundir confianza del decoder con seguridad física?
3. ¿Cómo se enlazan causa, secuencia y tiempo entre WSP y el Intent ABI de echOS?
4. ¿Qué capacidad aprendida mejora de verdad el examen de TRANSFER-3 frente a un control competente?
5. ¿Qué pruebas integrales faltan en DRONE-3 antes de interpretar los trece certificados como un sistema único?

Lectura accesible adicional: [echoAI](https://www.rxlabs.org/docs/echoai/que-es), [arquitectura](https://www.rxlabs.org/docs/echoai/piezas), [ruta ECHO-3](https://www.rxlabs.org/docs/echoai/ruta). Estas guías se basan en lectura de artefactos existentes; no anuncian nuevas ejecuciones ni cierres.
