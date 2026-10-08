# ECHO-4 / WORLD-1 — primer slice de software

Fecha: 2026-09-21. Implementación autorizada tras la investigación ECHO-4.

> Actualización del orden, sin cambiar este contrato: SENSATION-1 y
> BOUNDARY-1 preceden a SELF-1. Véase el [programa vigente](ECHO4-EGO-PROGRAMA.md).

Foco de ECHO-4 actualizado por el usuario: [ego funcional](ECHO4-EGO-PROGRAMA.md).
WORLD-1 mantiene este contrato como base corporal; no cambia sus criterios
ni convierte la factibilidad en evidencia de ego.

## Alcance

Mundo renovable, análisis exhaustivo de viabilidad y conexión de desarrollo
con `nexus0.loop.Agent` sin modificarlo. **Sin hardware, PX4, Gazebo,
METAVERSE-1, renderer ni LLM.** El hardware queda para una fase posterior;
no bloquea este programa de software. No se reabren contratos de ECHO-3.

WORLD-1 implementa la puerta de factibilidad de
[la investigación](ECHO4-INVESTIGACION-Y-PROGRAMA-20260921.md), no toda
E4-MAINTAIN-1. Todavía no hay navegación, daño, reparación, trabajo útil,
reproducción, conciencia acreditada ni examen de aprendizaje superado.

## Física congelada para este slice

Un cuerpo, un dock y tres acciones existentes. Estado entero `(H, theta)`.
Vivo si `1 <= H <= 127` y `1 <= theta <= 126`; inicio `(32, 64)`.

| Acción | H | theta |
|---|---|---|
| approach / conectar al cargador | +5, saturando en 127 | +16, saturando en 127 |
| avoid / apartarse y enfriar activamente | -3, saturando en 0 | -16, saturando en 0 |
| wait / permanecer sin refrigeración activa | -1, saturando en 0 | +4, saturando en 127 |

Recompensa 0 mientras vive y -16 al morir. No premio por cargar ni
recompensa por turno vivo. Es un banco de posibilidad física, no una tarea
final con productividad. No se modifica HEAT-1b.

La fuente es externa e idealmente disponible: no se afirma independencia
energética del ordenador. Unidades abstractas, nunca julios ni Celsius.
Cada transición conserva el balance declarado:

`H_antes + entrada = H_después + consumo_efectivo + derrame`.

El consumo efectivo se limita a lo que quedaba; agotar la reserva termina
la vida, no genera recursos negativos. El derrame registra la entrada que
no cabe. La temperatura tiene su propia regla sintética: no se presenta
este modelo como simulación termodinámica de una batería real.

Entradas inválidas, booleanos, floats y acciones fuera de 0..2 se rechazan.
No se aplica módulo a comandos corruptos. Un cuerpo terminal no actúa.
El mundo es la autoridad física; el espejo fisiológico del agente se
comprueba antes de cada transición. Los reinicios son explícitos y contados.

## Viabilidad: oráculo externo al agente

Se enumeran 16.002 estados vivos y 48.006 transiciones. Se eliminan
iterativamente los estados sin sucesor vivo dentro del conjunto restante.
Aristas inversas permiten hacerlo en tiempo lineal en el grafo.

El punto fijo es el núcleo de viabilidad del modelo determinista y de
observación completa. Para estados fuera de él se calcula la duración
máxima, incluyendo la acción terminal. Para un inicio dentro, se devuelve
una trayectoria testigo con prefijo y ciclo repetible, verificada por la
misma función de transición pura.

La prueba positiva manual `(124,64) -> (127,80) -> (124,64)` usa cargar y
enfriar. El analizador debe descubrir y validar un testigo desde el inicio,
sin recibir ese ciclo como respuesta programada.

Controles negativos: sin entrada de recursos no puede haber ciclo vivo;
con los incrementos históricos de HEAT-1b el núcleo debe estar vacío y el
máximo desde `(32,64)` debe ser 71, incluida la acción terminal. Se comparan
exhaustivamente esas transiciones con el código histórico, no sus recompensas.

Este oráculo **no** entra en Q, CAM, T, el gate ni la selección de acción.
Su testigo demuestra factibilidad del mundo, no que ECHO haya aprendido.

## Observación y prueba del agente

Se importa el encoder existente: WSP host de 16 bytes, un objeto en la
celda 0, cuatro bandas de H y ocho térmicas. No se cambia ningún byte de
formato, no se introducen sensores privados ni una codificación del daño.
El formato host es el de `navi10_wsp`; no se presupone equivalencia con
otras revisiones actuales del transporte WSP del kernel.

La auditoría de observación agrupa estados con el mismo WSP y declara
aliasing de transiciones, terminalidad y acciones viables. Tener un núcleo
no vacío bajo observación completa no demuestra control suficiente con
las bandas actuales. El presupuesto de observaciones se mide separado del
grafo de 16.002 estados: el grafo pertenece al evaluador, no a la CAM.

La demostración usa el `Agent` existente con cortex/planificación/ask
apagados. Ejecuta **una sola vida**, deteniéndose al morir o llegar al
límite solicitado. Aprende en línea; `greedy` solo elimina exploración y
no se llama «congelado». No hay entrenamiento con un oráculo, ni una
política oculta, ni teletransporte, ni respawn automático. La traza registra
propuesta, acción ejecutada, WSP, cuerpo, recursos y terminalidad.

El demostrador tiene un máximo de 10.000 turnos y no escribe archivos:
JSON a stdout, sin usar rutas heredadas de variables de entorno. El
adaptador no concede acceso a hardware, red, comandos ni archivos.

## Criterios de aceptación del slice

- Física pura, determinista, entera, límites y balance verificados.
- Rechazo sin mutación de entradas inválidas y pasos tras terminalidad.
- Núcleo no vacío e inicio viable, con testigo reproducible y válido.
- Controles negativos rechazan supervivencia indefinida.
- Observabilidad auditada con limitaciones explícitas, no verde supuesto.
- Agente original conectado, sin cortex ni pérdida de CAM; un solo cuerpo
  por ejecución, límites y contabilidad consistentes.
- Regresión de NEXUS-0/HEAT y hashes de fuentes históricas preservados.

No existe un campo `echo4_green` en este slice. El siguiente contrato será
E4-SELF-1: observabilidad y atribución cuerpo/entorno. Mantenimiento con
trabajo útil y reparación queda después, en E4-MAINTAIN-1, según el programa
del ego funcional. Las campañas y el modo de evaluación congelada se diseñan
aparte, sin cambiar retrospectivamente estos resultados.
