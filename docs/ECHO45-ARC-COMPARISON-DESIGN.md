# ECHO-4.5 · preparación de comparación ARC y capacidades

29 de septiembre de 2026. Autorizado mientras S6-B11 sigue ejecutándose.
Preparación y diagnóstico de desarrollo; ningún examen nuevo abierto.
Las fuentes congeladas de S6, del examen anterior y de memoria se conservan.

## Dos preguntas diferentes

1. ¿Mejora el candidato final respecto a la versión inmediatamente anterior?
   La referencia auditada del **28 de septiembre** es ARC-1 **31/400**,
   ARC-2 **0/120** y ARC-3 **11/112**. SEMILLA histórica es otra comparación.
2. ¿Qué mecanismos explican una diferencia? Una puntuación ARC global no
   basta: hacen falta tareas etiquetadas previamente y ablaciones emparejadas.

Analogía: la clasificación de una carrera dice quién llegó antes; quitar
por separado el mapa o la memoria permite investigar por qué.

## Referencia y custodia

`python3 -m seed.arc_comparison prepare` reconstruye la referencia desde los
520 registros de rejillas y 16 registros de juegos ya auditados. Comprueba
identidades, cobertura, hashes completos, presupuesto, contadores de acciones
y puntuación. No lee los outputs de los datasets de evaluación ni ejecuta
otra vez el examen cerrado. Resuelve los alias reales: en juegos, `sin_s6`
apunta a los registros de `con_s6`; en rejillas ocurre al revés.

La preparación guarda su propio perfil, copia de fuentes, corpus sintético,
referencia y hashes de recibos bajo `lab/final/echo45-comparison-prep-20260929/v2`.
Verifica seis manifiestos protegidos, incluidos transporte B11 y EGO-MEMORIA-3E.
Un cambio de fuente protegida hace fallar la comprobación; nunca se actualiza
su hash para aceptar el cambio. Comprueba también commits/árboles de datasets,
archivos de evaluación y hashes del código de los juegos contra la referencia.
La primera preparación y su diagnóstico quedan preservados en el directorio
padre; v2 añade estas comprobaciones de corpus y la exigencia del intérprete
ARC gestionado. El diagnóstico v2 se repite con las mismas tareas y parámetros.

## Comparación primaria ARC

| Dominio | Presupuesto y criterio conservados |
|---|---|
| ARC-1 / ARC-2 | 400 expansiones, profundidad 4, un programa/primer intento, coincidencia exacta en todos los tests |
| ARC-3 | 2000 decisiones por juego, semilla de entorno 0, `seed_for(game, 0)`, 16 juegos/112 niveles, sin deadline de reloj |
| Coste | Cero llamadas al modelo durante la evaluación; gasto real registrado además del límite |

Se mantienen las 400/120 tareas y los 16 juegos del contrato anterior.
Son **conjuntos conocidos de seguimiento**, no una reserva ciega nueva ni
un envío oficial. No se reescriben los resultados históricos. La confirmación
ciega necesitará otro contrato y datos no empleados en el desarrollo.

El score ARC-3 conserva la fórmula congelada: `min(humano/agente,1)^2`, con
peso creciente por índice de nivel, denominador de todos los niveles, y
reinicios automáticos incluidos en las acciones de cada nivel. Se informa
como **score local del contrato**, no como resultado de un gateway actual.

**S6-B11 solo cambia el controlador de juegos.** No añade operaciones al
solver de rejillas: ARC-1/2 quedan como alias explícitos de S2v y su resultado
histórico, sin fabricar una nueva medición ni mejora. Para cambiar el solver
de rejillas habrá que registrar otro candidato y su comparación específica.
Una expansión del solver antiguo no equivale a un programa probado por el
refinador: no se equiparan sus contadores llamándolos a ambos «pasos».

## Bloqueo del candidato y ejecución posterior

`freeze-candidate` requiere el cierre S6-B11 VERDE, B1–B5 completos, promociones
y auditorías de piloto/campaña, cuatro políticas congeladas, replays y auditoría
del transporte de los doce lotes. Vincula por hash la política ECHO **final de
campaña**. Ninguna política provisional del piloto puede entrar al comparador.
Comprueba también el runtime ARC contra el utilizado el 28 de septiembre.

Después, `run-arc3` ejecutará el controlador B11 nativo con el contador anterior,
sin observador, en un directorio nuevo. La biblioteca, fuentes y política
permanecen fijas. Otro proceso repetirá todas las partidas y comparará todos
los campos en JSON canónico. Los checkpoints deben coincidir con el perfil;
un seguimiento cerrado no se reabre. No hay ejecución automática al preparar.

```sh
python3 -m seed.arc_comparison prepare
python3 -m seed.arc_comparison check
python3 -m seed.arc_comparison snapshot
# Solamente después del cierre verde de S6; el propio programa lo comprueba:
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.arc_comparison freeze-candidate
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.arc_comparison run-arc3
```

## Pruebas de capacidades preparadas

Doce tareas **sintéticas de desarrollo**: cuatro familias, tres semillas
45101/45103/45107, tres demostraciones y dos tests por tarea. Colores, tamaño,
posición y orientación varían; la regla permanece. Los outputs del generador
se construyen directamente, sin utilizar el DSL que se evalúa.

| Familia | Qué comprueba | Analogía |
|---|---|---|
| Objetos | Aislar el componente mayor entre distractores | Distinguir una pieza del resto de la mesa |
| Relación con marcador | Usar el color de un marcador para transformar otra pieza | Leer una etiqueta y aplicarla al objeto correspondiente |
| Relación de tamaño | Ordenar colores de objetos por su área | Clasificar cajas por capacidad, aunque cambien de sitio |
| Composición | Aislar el objeto mayor y después rotarlo | Elegir la pieza correcta y orientarla para encajar |

Tres brazos del mismo refinador, con la misma biblioteca S2v congelada:

- Completo: relaciones disponibles y composición hasta profundidad 4.
- Sin relaciones nuevas: retira únicamente los cuatro operadores relacionales
  añadidos por `RefinementLibrary`; S2v ya contiene operaciones sobre objetos.
- Sin composición: profundidad 1 y sin macros que oculten varios pasos.

Todos tienen **2000 programas como límite global**, cuatro rondas, beam 8,
32 hipótesis como máximo y multivista apagada. La diferencia de profundidad
es la ablación declarada, no un aumento oculto del presupuesto. Se publican
programas realmente probados, pasos primitivos contados como cota superior,
ambigüedad, tiempo y aciertos. Puede agotarse el espacio de un brazo antes de
consumir el límite. Se puntúa solo la primera solución elegida y deben acertar
los dos tests; no se escoge a posteriori entre respuestas usando el juez.

Estas tareas prueban generalización dentro de familias construidas. No son
una muestra representativa de ARC ni certifican abstracción general. Los tags
de las tareas ARC históricas permanecen `unclassified`: no se deducen capacidades
del programa ganador ni de la respuesta de test. Los resultados por familia
de este diagnóstico se publican separados de las puntuaciones ARC.

```sh
python3 -m seed.arc_capabilities run
```

Un proceso y prioridad baja para convivir con S6. Usa el `Journal` existente;
la mini terminal muestra programas ajustados a demostraciones, errores medidos,
rondas y ambigüedad. No inventa pensamientos ni afirma verificar un test sin
su juez. Auditoría posterior en otro proceso, sin volver a instrumentar nada
reservado. El visor es pasivo; su texto no vuelve al agente.

## Informe y condiciones de aceptación

El comparador publica aciertos/denominador, diferencia absoluta, puntos
porcentuales y cambio relativo. **Con base cero el cambio relativo es `null`**,
no infinito ni 100 %. Conserva la lista de casos ganados y perdidos aunque
se cancelen en el agregado. En juegos publica además acciones, resets,
puntuación y pérdidas individuales. No suma porcentajes de categorías solapadas.

Preparación técnica completada significa que las referencias y protecciones
pasan y el harness ha sido probado. Un diagnóstico positivo exige una ventaja
observada de la condición completa frente a su ablación, a presupuesto común,
y replay exacto; solo vale para esta cohorte. Ningún resultado de este trabajo
declara S6 o todo ECHO-4.5 VERDE. Se preservan los criterios originales R1–R4.

Memoria 3E ya pasa su examen de aldea; la transferencia a ARC sigue pendiente.
[Protocolo de transferencia de memoria](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md) ·
[Referencia anterior](ECHO45-FINAL-EXAM-RESULTS.md) ·
[S6-B11](ECHO45-S6-B11-DESIGN.md).
