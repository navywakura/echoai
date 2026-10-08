# COMPOSE-1 — composición espacial acotada

Diseño previo al código y al examen, 2026-09-14. FUSION-1 ya cerró su contrato
funcional y replay SITL; Roger autorizó continuar directamente.

## Pregunta

¿Componer efectos observados permite acceder a una estación al otro lado de
una barrera, revisar un paso invalidado y abandonar con reserva, mejor que Q
reactiva con las mismas observaciones? Sin ampliar LIF ni activar un LLM.

## Dos puertas que no se confunden

1. **Módulo funcional:** cuerpo de radio 400 mm en voxeles de 1 m, espacio 3D,
   odometría entera exacta, rayos geométricos discretos, desplazamientos de una
   celda y coste en unidades de simulación. Física cinemática declarada, sin
   aerodinámica ni PX4. Mide composición y su interfaz WSP en un proceso aislado.
2. **Cierre ECHO-3:** ejecutar las mismas capacidades y comprobaciones con
   observaciones y consecuencias de Gazebo/PX4. La correspondencia entre
   coordenadas, capacidades y sensores debe verificarse; el verde funcional
   por sí solo **no** marca COMPOSE-1 cerrado en el roadmap.

El segundo punto conserva el contrato ECHO-3; no se sustituye por una maqueta
que se llame vuelo. PX4-1 seguirá certificando el enlace completo y su autoridad.

## Modelo y memoria

Se importan CAM, QTable y World existentes. T aprende efectos relativos de seis
movimientos y espera con ejercicios separados en A; no recibe rutas ni mapas.
Sus índices son ranuras CAM de WSP de condiciones y consecuencias. Q aprende
preferencias reactivas con recompensa observada por progreso/coste en A.

El registro espacial contiene sólo celdas alcanzadas por los rayos del sensor,
posición de odometría, evidencia por fuente y antigüedad. Cada celda tiene una
referencia local WSP; no se usan IDs ni nombres del mundo. La misión puede
indicar una coordenada como hipótesis: sólo el sensor local confirma la estación.
Mantener una coordenada objetivo no equivale a conocer su ruta ni su existencia.

FUSION-1 decide sobre cada celda observada. La geometría discreta garantiza
400 mm de radio en una celda vacía de 1 m; esto no convierte el rayo frontal
del banco físico FUSION en un certificador de volumen libre.

## Decisión

Búsqueda de profundidad máxima cuatro movimientos observables, presupuestos
de 8 y 32 expansiones. Cada candidato exige efecto conocido de T y evidencia
espacial admisible. Se puntúan progreso hacia la meta, coste, visitas previas
y Q. Se permite alejarse de la meta para rodear una barrera. Las fronteras
observadas orientan exploración cuando la meta aún no cabe en el horizonte.

Sólo se ejecuta el primer movimiento, tras volver a comprobar evidencia,
colisión y reserva. Cada ciclo publica la predicción antes del acto y contrasta
odometría/consecuencia después. Los rollouts no escriben T, Q ni CAM. En B/C
T y Q quedan congeladas; la memoria perceptiva sigue actualizándose. Aprendizaje
de efectos y evaluación congelada se informan por separado.

La opción elegida (hasta cuatro pasos) conserva su submeta mientras sigue
siendo admisible. Cambiar de horizonte a cada tick provocó oscilación en el
primer sondeo de desarrollo; ahora cada siguiente eslabón se vuelve a verificar
y una discrepancia o pérdida de evidencia invalida el resto de la opción.
El control convencional usa la misma búsqueda acotada y exploración de
fronteras, sin priorización por Q; no se degrada a un seguidor codicioso sin
memoria. El cálculo de reserva recorre como máximo las 256 celdas observadas;
ese recorrido auxiliar se distingue de las 8/32 expansiones de composición.
Se añade control `one_step`: la misma memoria, visitas y modelo, pero horizonte
uno. Se publica para separar la mejora de memoria/exploración de una ventaja
específica del horizonte. El coste de visitas incluye todos los eslabones de
una opción; juzgar sólo su hoja ocultaba pasos intermedios repetidos en A.

Reserva: coste de un camino observado de retorno + aterrizaje + margen.
Se publica el modelo de coste, no julios. Agotar búsqueda es acceso no encontrado.
No se infiere inexistencia de acceso. El banco termina en llegada confirmada,
retorno, abandono declarado o presupuesto agotado; no hay muerte para resetear.

## Mundos y partición funcional

Separación por semillas antes de medir. Misma geometría generadora con variantes
de posición, orientación, altura de abertura, barrera móvil y ausencia de acceso.
El generador y el plano permanecen fuera del proceso consumidor.

- A desarrollo y aprendizaje: 20261801–20261816.
- B validación: 202618101–202618132.
- C confirmación funcional: 202618201–202618232.
- N por etapa y brazo: 32 misiones, máximo 64 pasos.
- Casos alternos: abertura estática, cambio de abertura, acceso cerrado,
  energía insuficiente. Condición y seed no entran al agente.
- C funcional no consume ni sustituye C físico sellado de TRANSFER-3.

Controles: Q reactiva, búsqueda sin caducidad, planificador convencional,
oracle geométrico (sólo techo del evaluador), completo con 8 y 32 expansiones.
Mismos sensores, recursos y acciones para los brazos no oracle. El oracle no
justifica una fuga. No se exige vencer al planificador convencional.

## Criterios

Puerta funcional verde exige cero colisiones, hechos de estación sin observar,
escrituras imaginadas o fugas; éxito agregado superior a Q en metas bloqueadas
factibles; límites de profundidad/candidatos respetados; abstención o retorno
en acceso no hallado y reserva insuficiente; memoria de mapas vacía al entrar
en B/C. Publicar conteos por condición, diferencia emparejada e intervalo,
pasos, reservas, revisiones, latencia P99 y tamaño de memoria.

Mutantes: ignorar evidencia, escribir rollouts en T, tratar hipótesis de meta
como éxito, ignorar reserva y recibir plano/ID. El auditor rechaza omisiones,
falso verde, predicción/acción alterada, resultado falso y escrituras ocultas.

Archivos nuevos en `nexus0/compose1/`, pruebas, informes y trazas separados.
Se conserva la evidencia roja; no se ajusta B/C hasta obtener una corrida verde.
`functional_green` y `compose1_green` son campos distintos. El segundo requiere
también la puerta Gazebo/PX4, incluso si el primero resulta favorable.
