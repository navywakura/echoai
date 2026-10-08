# E4-SELF-1 / SELF-C — conducta y protección selectiva v1

2026-09-21. Contrato prospectivo, antes del banco. Autorización: implementar
SELF-C. No modifica fuentes selladas de SELF-A/B, WORLD, SENSATION, BOUNDARY
ni el núcleo histórico. No cierra E4-SELF-1: faltará el examen nuevo B/C.

## Pregunta y alcance

¿La evidencia de SELF-B permite adaptar acciones y evitar que un efecto
corporal se aprenda como una transición nominal del entorno, sin congelar
todo el aprendizaje? Reutilizar `Agent.self_model.observe_step`, T/Q/CAM,
SENSATION y gate. No segunda T, bus ni LLM.

Se hereda el prior explícito de SELF-B, no se descubren leyes físicas.
Tras calibración y diagnóstico supervisados hay **una restauración declarada**
al estado inicial oculto del experimento. Después: veinticuatro decisiones en una
sola vida, sin resets, reparación o recarga por fuera de las tres acciones.
El pulso externo ocurre una vez, en el primer paso de esta vida; acoplamientos
y pulso permanecen iguales a los del diagnóstico. Se contabiliza el coste
de preparación aparte; no se presenta como recuperación continua desde una
avería espontánea. No leer H/temperatura reales, parámetros ni etiqueta del
juez desde el controlador; solo WSP, acciones y recibos del loop original.

Algunos fallos hacen imposible sostenerse indefinidamente. La recuperación
medida aquí es completar veinticuatro pasos vivo bajo la alteración, no reparar el
actuador ni lograr mantenimiento indefinido. El juez privado enumera si hay
alguna secuencia viable de veinticuatro pasos y publica también los casos imposibles.

## Decisión y actualización

El conjunto de hipótesis de SELF-B se continúa temporalmente, sin restaurarlo
en cada turno. Antes de actuar se predice un paso por las tres acciones.
Se prefiere el mayor margen mínimo `min(H, theta, 127-theta)` sobre todas
las hipótesis. Desempate: Q existente, propuesta original y luego wait.
Es una heurística de seguridad explícita, no una necesidad aprendida ni
planificación óptima. El gate original conserva la decisión final. Si ninguna
acción es segura en el modelo, se pide parada del ensayo (no cuarta acción,
no cuenta como completar la vida). Incertidumbre inicial o contradicción:
parada y desconocido; no convertirla en certeza externa.

Con la observación posterior se filtran los pronósticos previos. Para escribir
T se exige que **todas** las hipótesis compatibles den ese mismo código al
reponer hipotéticamente los acoplamientos nominales, manteniendo el pulso
externo. Si no, se retiene la actualización completa de esa transición;
no fabricar un WSP contrafactual para enseñárselo a T. Las observaciones
externas compatibles y transiciones sin efecto corporal observable sí pasan.
Se usa `World.observe` original, incluido KCC e inverso; Q aprende recompensa
real sin cambios. SENSATION/PATTERN recibe exactamente la misma autorización;
su ventana temporal avanza aun cuando la transición no se aprende.
Veto, contexto inválido o contradicción no autorizan escritura nominal.

Una transición externa transitoria admitida no es prueba de haber aprendido
una ley externa permanente. La protección es por transición observable,
no por propiedad metafísica de un byte ni inmunidad frente a todo aliasing.

## Controles y banco de desarrollo

H inicial {29,34,39}, temperatura {44,52,60,68}, cuatro acoplamientos y cinco
pulsos {-16,-4,0,4,16}: **240 condiciones**, veinticuatro pasos como máximo.
Smoke: H=34, temperatura=60, veinte condiciones. Banco público, no B/C.
Todos parten de iguales observaciones nominales, T y Q. La T inicial se
aprende de las transiciones realmente observadas durante calibración, no
se carga desde la tabla privada del simulador.

Cinco brazos, sin eliminar fracasos:

- `selective`: hipótesis completas, decisión adaptada y protección selectiva.
- `no_protection`: misma decisión/hipótesis, pero enseña todo a T/PATTERN.
- `no_attribution`: posición estimada compartida, decisión suponiendo cuerpo
  nominal y pulso cero; enseña todo. Aísla el uso del diagnóstico dinámico.
- `all_external`: decisión suponiendo cuerpo nominal, conserva estimación
  del pulso; enseña todo.
- `all_self`: decisión suponiendo ambos canales desacoplados y sin pulso;
  congela T/PATTERN por completo. No se confunde esa congelación con aprender.

El juez verifica por transición si el efecto corporal cambió el WSP respecto
al contrafactual nominal con el mismo pulso. Mide escrituras contaminantes,
filas retenidas byte-idénticas, escrituras legítimas, actualizaciones externas,
acciones, pasos vivos, paradas, terminalidades y condiciones completadas.
También compara decisiones del selectivo con sus ablaciones sobre trayectorias
reales. Mismo controlador sin protección debe tener exactamente las mismas
acciones: la heurística no usa T para decidir, y ese límite se publica.

## Criterios previos del entregable

- Selectivo completa ≥90% de las condiciones físicamente viables y más que
  `no_attribution`; publicar todos los denominadores, no ocultar inviables.
- Cero escrituras contaminantes del selectivo; `no_protection` presenta
  alguna. Toda actualización retenida deja T/PATTERN intactos en ese paso.
- Alguna actualización legítima y alguna externa pasan en el selectivo;
  el control `all_self` no aprende. No exigir ventaja ficticia sobre todos
  los controles en todas las métricas.
- Cero terminalidades del selectivo dentro del prior, gate respetado, sin
  pasos tras muerte/parada, sin resets dentro de la vida ni hechos causales CAM.
- Modelo local ≤64 candidatos H y ≤160 térmicos, deduplicación por paso,
  un pronóstico pendiente, sin historia creciente. Enteros; sin cambios WSP16.
- Pruebas de integración real, veto, desconocido, contradicción, capacidad,
  saturación, sellos anteriores y manipulación de artefactos. Replay completo
  independiente y manifiesto de fuentes. No retocar criterios si sale rojo.

Aunque pase: `self1_green=false`. B/C nuevos deberán evaluar cierre conjunto,
generalización fuera de desarrollo, negativos y utilidad; no reciclar este
banco como reservado. Hardware después del software, METAVERSE-1 último.
