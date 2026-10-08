# DREAM-A — historial ejecutado y replay con revelación parcial

2026-09-22. Contrato de primer incremento, previo al código y al banco.
DREAM-1 sigue abierto. No Qwen, entrenamiento, promoción de estrategias,
autorreparación ni nuevo certificado de conciencia.

## Pregunta y diferencia respecto al paper

¿Podemos conservar intentos realmente ejecutados y revelar únicamente sus
resultados ya observados, sin volver a ejecutar el entorno ni mostrar futuros?
[Dream-RSI, §3](https://arxiv.org/html/2609.14858v1#S3) motiva el árbol de
intentos y el replay parcial. Aquí usamos un catálogo finito de experimentos
WORLD-1 y presupuesto entero de consultas, no su interfaz ni su puntuación.
No es una réplica de sus benchmarks ni evidencia de auto-mejora de Qwen.

## Primer dominio

- `SelfAgent` nominal, `ContinuityRun` original, entre turnos completos.
- Experimentos públicos fijos: `native` (turno normal) y `greedy` (turno con
  el flag existente). No se escribe Q ni se suministra una acción al agente;
  su código, parámetros y evaluador no cambian durante la recolección.
- Cada hijo restaura el checkpoint de su padre y ejecuta un turno real. Se
  permite volver al mismo padre para otro intento; no hay reparación ni
  resurrección, ni se representa esta restauración de laboratorio como una
  acción autónoma. Ramas terminales no se expanden.
- Dos árboles nuevos de desarrollo: (H, θ, historia, corte) = (60,46,2,3)
  y (64,55,4,4), profundidad máxima 3, hasta 14 intentos por árbol. Otro
  contexto (32,64,2,128) proporciona un checkpoint terminal sin hijos.
  No son holdouts de mejora: es un banco de integridad de infraestructura.
- Puntuación inicial = recompensa nativa (0 o penalización terminal), sin
  bonificación inventada. La tarea de descubrimiento útil y su evaluador
  para DREAM-B/C/D tendrán contrato propio; empates no son auto-mejora.

## Archivo y fronteras

Archivo privado, JSON cerrado y acotado: versión/perfil, fuentes, certificado
CONT-D, nodos con padre, experimento, observación pública, recompensa/coste
entero y digest de checkpoint. Cada nodo referencia un estado concreto;
igual WSP no fusiona nodos. Coste de cada intento: una ejecución nativa,
cero llamadas LLM. Raíz: cero coste nuevo; preparación informada aparte.

La carga valida digest del custodio, esquema, orden acíclico, continuidad de
turnos, terminalidad, tipos y límites. Sin pickle/eval, instrucciones remotas
ni imports contenidos en el archivo. Un hash prueba integridad respecto al
custodio, no veracidad física: esta la comprueba el banco reconstruyendo las
ejecuciones originales y cotejando cada checkpoint.

La vista permitida incluye solo WSP, acción/recompensa/gate, turno, estado
terminal, historial revelado y contadores de presupuesto. Sin H/θ exactos,
CAM/Q/T, rutas, checkpoints, semillas, fuentes privadas, puntuaciones futuras,
cantidad de hijos futuros ni IDs que delaten el orden global de recolección.
Handles de nodos se asignan al revelarlos. El archivo del laboratorio no es
el payload que se entregará al modelo. La separación es de API; no es un
sandbox para código hostil en el mismo proceso (eso no se ejecuta).

## Replay

`view()` comienza solo con la raíz. `expand(handle, experiment)` revela el
primer intento aún no visto de ese padre/experimento; repetir no inventa
otra muestra. Rama ausente: `unknown`; terminal visible: `terminal`.
Cada solicitud válida consume una consulta, incluida una desconocida; solo
revelar un intento ejecutado suma su coste representado. Ejecuciones físicas
y LLM durante replay: cero, no «cómputo total gratis».

Lotes limitados: todos los handles deben existir antes del lote, sin duplicar
peticiones; validar el lote/presupuesto entero antes de consumir nada. Un
fallo de validación no cambia el estado. El estado de una sesión replay no
contamina otras. El cargador copia y valida datos; el consumidor no puede
mutar el archivo a través de una vista devuelta.

## Criterios del incremento

1. Árboles recogidos con el agente nativo; igualdad completa de checkpoints
   al reconstruir, sin cambiar su padre y con fuentes CONT-D intactas.
2. Revelar todos los intentos devuelve los mismos registros públicos que
   online, también en un proceso nuevo. Cero ejecuciones/LLM en replay.
3. Vista parcial invariante al cambiar/añadir un futuro no revelado; IDs
   opacos por sesión. Sin acceso a estado físico exacto ni fusiones por WSP.
4. Desconocidos, terminales, muestras repetidas, presupuesto, lote y aislamiento
   entre sesiones comprobados. Rechazar corrupción, ciclos, tipos inválidos,
   campos privados introducidos en observación y costes manipulados.
5. Reconstrucción del informe entero, no confiar en su campo de aprobación;
   comprobar también archivos de checkpoint. Informe no concede `dream1_green`.
6. Tests nuevos y regresiones pertinentes, lint, hashes sellados preservados.

El incremento deja pendiente extender recolección a tareas de descubrimiento
con utilidad discriminante, fijar su contrato de evaluación y adaptar Qwen
en DREAM-B. No se ejecuta código generado ni se publica nada en Hugging Face.
