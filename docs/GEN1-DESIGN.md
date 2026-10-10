# GEN-1 — diseño de herencia mínima para implementación por Sol

Fecha: 2026-09-09. **Estado posterior: implementado y medido rojo.**
Este documento fijó el protocolo antes de medir; el resultado se conserva al
final y no declara GEN-1 verde.

## 1. Pregunta y alcance

¿Un hijo que nace con CAM, Q y T nuevas aprende a obtener alimento en menos
episodios gracias a un único entero heredado de un progenitor seleccionado?

Antecedente del diseño de ECHO-2, punto 7 y tabla de fases:
`b` opt-in, default 0, anillo default `[-12,+5,0]`, KPI
`EpisodesToCriterion` menor que el naïf, sin copiar Q.

Decisión de este diseño: **b controla la frecuencia de exploración**.
Es una predisposición de aprendizaje, constante durante la vida del hijo.
No codifica acciones correctas, posición de recursos, identidad de objetos,
filas de Q ni episodios. La tarea seguirá siendo caminar, adquirir y consumir
el objeto de FOOD-1/SURV-1 desde el START canónico.

Utilidad futura: estudiar cómo una configuración de exploración seleccionada
en simulación facilita el aprendizaje de misiones en robótica edge. GEN-1
no autoriza explorar con un dron físico ni demuestra seguridad de vuelo.

## 2. Arquitectura y único punto causal

Reutilizar `Agent`, `QTable`, `World`, `VitalEnv(FoodEnv(...))` y el gate.
No crear otro agente cognitivo, bus, política, predictor ni memoria CAM.

Añadir el argumento nombrado `inherited_b=0` a `Agent` y `QTable`.
Validar `type(b) is int` y `b in (-1, 0, 1)`; rechazar bool, float y otros
valores sin coerción ni módulo. `QTable.inherited_b` será la fuente operativa;
Agent lo pasa al constructor, sin mantener dos copias mutables independientes.

| b | Período efectivo de exploración sobre Q no plana |
|---|---:|
| -1 | 4 turnos |
| 0 | 8 turnos, comportamiento actual |
| +1 | 16 turnos |

Derivar el período desde `EPS_PERIOD` con desplazamientos enteros. Si el
período base es cero, conservar el significado existente de exploración
periódica desactivada. No modificar `EPS_PERIOD` global.

Cambios causales permitidos, exclusivamente en selección:

1. `is_explore`: greedy devuelve falso; una fila plana conserva su conducta
   actual; sobre una fila no plana se usa el período efectivo.
2. `select`: conservar la lógica de filas planas y `explore_flat` actual.
3. `_settled_phase`: usar **el mismo período efectivo** tanto en `gcd` como
   en la división. Mantener el recorrido de todos los verbos con cuatro
   acciones; no introducir el sesgo de explorar siempre `approach`.

No desplazar el reloj global con b: afectaría física, registros y otros
consumidores del turno. No sumar b a Q, recompensas, H, U, delta o acción.
`best`, `max_q`, `update`, α, γ, remainder, encoder y gate quedan bajo sus
contratos actuales. `greedy=True` tendrá idéntica selección para cualquier b
si la fila Q es la misma.

Para `b=0`, exigir equivalencia de selecciones y actualizaciones con el
comportamiento previo, además del candado del anillo. No modificar el esquema
del diario para esta fase: b y su efecto se documentan en el informe GEN-1.

## 3. Nacimiento frente a respawn

Son operaciones distintas:

- **Respawn del mismo individuo:** conserva sus Q/T/CAM y b; restaura cuerpo
  y H con el mecanismo existente. Los episodios siguientes pueden aprender.
- **Nacimiento del hijo:** construye Agent y entorno nuevos. Sólo recibe b
  del progenitor. Q y remainder parten de cero; T e inversa vacías; CAM sin
  episodios aprendidos; métricas, contexto temporal y vida reiniciados.

Interfaz prevista del harness: `new_agent(b, nutrition=24, initial_h=16)` y
`spawn_child(parent)`; esta última lee únicamente el entero y llama a la
factoría nueva. La factoría reutiliza los flags de SURV-1:
`ask=False, remainder=True, explore_flat=True`, córtex y planificación OFF.

No heredar reglas SLEEP-2, familias PATTERN-1, pesos aprendidos, PRNG, objetos
env ni referencias a tablas. Los valores físicos y flags comunes proceden
del protocolo, no del progenitor. Comparar el nacimiento contra una instancia
fresca equivalente y comprobar independencia de objetos mutables. Escribir
en el hijo no debe cambiar al padre y viceversa.

## 4. Selección del progenitor, sin mirar el examen

Se ensayan tres candidatos b de forma secuencial; no hay población simultánea,
mutaciones abiertas ni búsqueda sin límite. Todos nacen nuevos por semilla.

Protocolo fijado antes de ejecutar:

- Candidatos: `(-1, 0, 1)`.
- Semillas de selección: `(17, 101, 20260903)`, ya usadas por SURV-1.
- Máximo: 50 vidas por candidato y semilla.
- Física: `initial_h=16`, nutrición `24`, drenaje existente, mismo START.
- Seleccionar el b con menor suma de `capped_episodes_to_criterion`.
- Desempate: preferir 0; entre -1 y +1 preferir -1.

La selección usa sólo medidas observadas de estos episodios. Guardar toda la
tabla de candidatos y el criterio; no elegir manualmente el ganador. El
progenitor concreto será el individuo de la primera semilla de selección
con el b ganador. Sus recuerdos quedan excluidos del nacimiento.

Bloquear b ganador antes de crear hijos de examen. Si gana 0, se informa
ausencia de ventaja heredable en este protocolo: no cambiar desempate,
semillas, horizonte o semántica de b para forzar un verde.

## 5. Examen del hijo y controles emparejados

Semillas nuevas y fijas: `(211, 307, 401, 503, 601)`. Ninguna participa en
selección. Por semilla ejecutar:

| Brazo | Nacimiento | Aprendizaje entre vidas |
|---|---|---|
| inherited | hijo del progenitor, sólo b seleccionado | conserva memoria propia |
| naive | agente nuevo con b=0 | conserva memoria propia |
| erase_b | hijo nuevo al que se asigna 0 antes de actuar | conserva memoria propia |
| static_b | agente nuevo configurado directamente con b seleccionado | conserva memoria propia |

Exigir `erase_b == naive` y `static_b == inherited` en trazas conductuales,
memorias finales y métricas, excluyendo las etiquetas del brazo. Esto prueba
que la causa transmitida es el entero; no atribuir propiedades especiales a
la genealogía frente a configurar directamente el mismo parámetro.

Para cada semilla, generar **una vez** 50 fases externas con
`random.Random(seed).randrange(30000)` y compartir la lista inmutable entre
los brazos. Turno de selección: `life*30000 + phase[life] + life_turns`.
Ese reloj pertenece al harness, no se hereda. Mismo calendario por índice
de vida, aunque las duraciones diverjan. No saltar fases por resultados.

Ejecutar siempre las 50 vidas, incluso si se alcanza pronto el criterio.
Una vida acaba al morir; 40 turnos es el máximo con un recurso finito y sin
clamp de H en este banco. Registrar muerte y consumo real, no sustituir
simulación por la fórmula de duración. Ningún hijo empieza junto al alimento.

## 6. KPI definido antes de medir

Éxito de una vida: consumo exactamente una vez y duración 40, con muerte
terminal H=0. La duración 16 significa que no se obtuvo alimento.

`EpisodesToCriterion` es el primer índice **1-based** e>=5 para el que al
menos cuatro de las últimas cinco vidas tienen éxito. Se calcula de las
vidas de entrenamiento reales, que sí aprenden; **no llamarlo examen greedy
congelado**. Mide adquisición sostenida bajo la política de exploración.

Si no llega en 50 vidas: `episodes_to_criterion=null`, `censored=true`,
`capped_episodes_to_criterion=51`. No convertir censura en éxito en vida 51.
El resto recibe `censored=false` y su índice real. Publicar los tres campos.

Registrar además turnos reales hasta criterio, éxitos totales y éxitos en
las diez últimas vidas. La comparación de episodios se acompaña de turnos,
pues una vida larga contiene más interacciones. No afirmar eficiencia
energética ni menor tiempo de CPU a partir del número de episodios.

Cierre causal principal en las cinco semillas de examen:

- El hijo alcanza criterio en al menos 4/5 semillas.
- Su mediana de episodios capados es estrictamente menor que la del naïf.
- Hay ventaja estricta por pareja en al menos 3/5 semillas.
- La suma de éxitos en las últimas diez vidas no es menor que la del naïf.
- Publicar todas las parejas, incluidos empates, pérdidas y censuras.

Estos umbrales son requisitos propuestos, no resultados prometidos. Si fallan,
GEN-1 queda rojo medido; entregar informe y diagnóstico sin retocar el banco.

## 7. Controles adicionales obligatorios

**Sin nutrición:** repetir inherited y naive con nutrición 0 en las cinco
semillas nuevas y mismas fases. Todas las vidas deben durar 16; ninguna
alcanza el criterio. El acto de consumir puede ocurrir, pero no añade vida.

**Sin aprendizaje de Q:** repetir ambos brazos con `QTable.update` suprimida
en el harness de control, incluido remainder; CAM/T siguen su camino normal.
Con Q plana y `explore_flat=True`, b no tiene efecto por diseño: las trazas
de ambos brazos deben ser idénticas. Para atribuir la ventaja a aprendizaje,
el hijo normal debe superar a su propio control sin Q en la mediana de
episodios capados. Si el control resuelve igual de rápido, no cerrar GEN-1.

No añadir un interruptor global de aprendizaje al producto para este control;
usar sustitución acotada al banco y restaurada después. No copiar tablas
entrenadas para simular un nacimiento. No borrar CAM en ningún brazo.

## 8. Evidencia, informe y auditor

Artefacto previsto: `lab/echo2_gen1_report.json`, con versión de esquema,
`slice=GEN-1`, protocolo completo y `green` calculado.

Incluir candidatos y vidas de selección, ganador derivado, b transmitido,
semillas, fases, los cuatro brazos, controles y para cada vida: índice,
turnos, H final, terminal, consumos, recompensa total, conteos de acciones
propuestas/ejecutadas, exploraciones y decisiones del gate. Incluir hashes
deterministas del nacimiento y final de CAM/Q/T, métricas y configuración.

Las trazas causales por turno pueden guardarse como artefacto separado con
hash y ruta relativa: observación WSP, turno, propuesta, acción ejecutada,
reward, H antes/después y terminal. Reutilizar la instrumentación existente
donde encaje; no añadir otro thought-bus. Acotar tamaño por 50*40 turnos por
brazo. Los hashes respaldan comparación; por sí solos no prueban ausencia
de copia: hacen falta también pruebas de construcción e independencia.

`green(report)` debe reconstruir ganador, éxitos, ventanas, censura,
medianas y comparación por parejas desde filas, verificar exactamente
semillas, fases y denominadores del protocolo, y rechazar campos ausentes
o tipos inválidos. Nunca confiar en `green=true` recibido ni en resúmenes
precalculados. Medianas impares y comparaciones enteras; nada de float en
control. Los controles adicionales tienen el mismo escrutinio que el brazo
principal. Conteos de acción suman los turnos; vidas y fases no se duplican.

Invariantes de todos los brazos: WSP 16 B, CAM 4096, `destroyed=0`,
`false_facts=0`, `cortex_calls=0`, muerte terminal válida y gate efectivo.
La genealogía no aumenta H, nutrición o recompensas por estar vivo.

## 9. Plan de implementación y validación para Sol

Archivos previstos:

- `nexus0/qtable.py`: parámetro validado y período efectivo consistente.
- `nexus0/loop.py`: paso del argumento al constructor de QTable.
- `nexus0/gen1.py`: nacimiento, selección, bancos, informe y auditor.
- `tests/test_gen1.py`: pruebas de contrato y mutantes del informe.
- `lab/echo2_gen1_report.json`: sólo tras ejecución real.
- `docs/ECHO2-START.md` y `docs/NOW.md`: resultado medido, con sus límites.

Orden: primero semántica de b y default; después nacimiento; luego banco y
controles; finalmente auditor, artefacto y documentación. No tocar GUI,
neuronas, SLEEP-2, drivers, kernel ni despliegues.

Pruebas mínimas que aportan evidencia:

1. b inválido se rechaza; b=0 reproduce calendario previo en filas planas y
   no planas, greedy y exploración, con tres y cuatro acciones.
2. Períodos 4/8/16 medidos; cobertura de verbos; greedy idéntico entre b.
3. Nacimiento realmente vacío e independiente; respawn conserva b y memoria.
4. b no cambia Q.update, rewards, H ni observación para la misma transición.
5. Gate puede bloquear una propuesta exploratoria con cualquier b.
6. Selección sólo depende del conjunto de selección; cambiar resultados de
   examen en una copia de datos no altera al progenitor elegido.
7. Criterio correcto en límites, ventanas intermedias y casos censurados.
8. Ablación del entero, configuración directa, sin nutrición y sin Q cumplen
   las igualdades y comparaciones exigidas.
9. Mutantes: resumen inflado, semilla repetida, fase cambiada, vida faltante,
   censura inventada, memoria copiada, Q inicial no nula, control alterado,
   gate omitido y contadores no cero deben fallar pruebas o auditor según
   corresponda; no exigir a un JSON detectar por sí solo referencias Python.

Ejecutar pruebas GEN-1, QTable y las fases ECHO-2 existentes. Al modificar
selección compartida, ejecutar también la suite histórica NEXUS-0, incluyendo
los casos de cuatro acciones, y comprobar el candado `[-12,+5,0]`. Separar
fallos ambientales de regresiones y conservar el expectedFailure histórico
de WALK-1. Documentar comandos y resultados reales.

## 10. Límites del cierre

Esto es selección discreta de un hiperparámetro y transmisión de un entero
entre individuos simulados. No demuestra evolución abierta, herencia de
conocimientos, aumento de neuronas ni inteligencia general. La transferencia
se examina sobre nuevas secuencias de exploración en la misma tarea; no
afirmar generalización a nuevos mapas o misiones.

SLEEP-2 sigue consolidando experiencia del mismo individuo por separado.
Su memoria no cruza generaciones en GEN-1. HEAT-1, CAPACITY-1,
NEURAL-VIZ-1 y la integración AKD1500 permanecen fuera de esta entrega.

## 11. Resultado de la primera implementación

La implementación está en `nexus0/gen1.py` y su evidencia en
`lab/echo2_gen1_report.json`. El protocolo seleccionó `b=+1` con puntuaciones
capadas 101/80/76 para b=-1/0/+1. En las cinco semillas nuevas, el hijo obtuvo
mediana 34 episodios frente a 27 del naïf y cero victorias estrictas por
pareja; una semilla quedó censurada. Por tanto `green=false`.

El control sin actualización de Q también alcanzó el criterio en algunas
semillas. Esto muestra que la tarea y la ventana de éxito admiten resolución
por el calendario de exploración sin demostrar aprendizaje suficiente. No se
cambiaron semillas, umbrales ni ganador después de ver el resultado. Una
segunda hipótesis de GEN-1 deberá diseñar un KPI que el control sin Q no pueda
resolver y validarse como un protocolo nuevo, sin reetiquetar este resultado.

## 12. Cierre posterior: GEN-1f

La primera implementación anterior permanece roja. La cadena GEN-1b..e fue
el historial de desarrollo y preregistros fallidos. El cierre confirmatorio es
GEN-1f (`docs/GEN1F-DESIGN.md`, `lab/echo2_gen1f_report.json`): hereda
`evidence_budget=8`, usa T.n local hasta reunir la evidencia y después entrega
la decisión a Q greedy. El control sin Q no puede acertar porque `wait` nunca
es la respuesta válida y el examen no aprende.

En 128 condiciones nuevas: 360 errores tardíos frente a 602 del naïf, 470 del
histórico, 126/128 criterios, 52 victorias frente a 24 derrotas y prueba de
signos unilateral `p≈0,000881`. `green=true`. Este resultado cierra GEN-1 para
calibración sensorimotora ruidosa; no amplía sus conclusiones a navegación,
supervivencia completa o transmisión de memorias.
