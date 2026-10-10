# S6-B19: investigación del rechazo y requisitos para B20

6 de octubre de 2026. Investigación privada sobre el código y los artefactos
cerrados. **B19 está auditado y rechazado; B20 todavía no está implementado ni
ejecutándose.** Este análisis no modifica los contratos ni las fuentes congeladas.

Se recalcularon las 36 propuestas y sus efectos por caso, se contrastaron las
trayectorias y se comprobó la biblioteca real de guardas frente al validador.
Las 65 fuentes de B18 y las 68 de B19 conservan sus hashes. No se ejecutaron
partidas nuevas, llamadas al modelo ni pruebas protegidas. Reproducción:

```bash
python3 lab/seed/s6b19-analysis-20261006/analyze.py
```

[Datos recalculados](../lab/seed/s6b19-analysis-20261006/analysis.json) ·
[Script](../lab/seed/s6b19-analysis-20261006/analyze.py) ·
[Cierre B19](../lab/seed/s6b19-20261005/kaggle-results/closed.json) ·
[Auditoría](../lab/seed/s6b19-20261005/kaggle-results/micro-audit.json).

**Qué falló realmente.** Ninguna propuesta consiguió simultáneamente dos
niveles adicionales y conservar el nivel y el score de cada partida. Los
1.188 juegos físicos incluyen replays y auditoría de doce casos dirigidos;
no son 1.188 problemas independientes. Solo hubo una generación inicial del
LLM, compartida por control e híbrido. Los refinamientos fueron deterministas.

| Brazo, propuesta representativa | Niveles sobre base 52 | Casos con pérdida | Resultado |
|---|---:|---:|---|
| Buscador anterior, 3 | 60 | 2 | Ganancia insuficientemente conservadora |
| Híbrido, 2 | 56 | 1 | Conserva una regresión de score |
| Síntesis sin LLM, 3 | 53 | 0 | No alcanza +2 |

El híbrido también llega a 60, conservando al menos dos pérdidas. No se
abrieron los 160 casos de cualificación completa ni los 80 nuevos protegidos.
No hay evidencia nueva de conservación fuera del cribado. Los dos servicios
de seguimiento B19 están inactivos y terminaron con código cero.

**1. Una intervención temprana encarece el resto de la partida. Confirmado.**
En v3/28027, el candidato híbrido 2 cambia HOLD de 40 a 1 al consumir el
control en el índice de acción 35. La primera acción distinta aparece en
43. La observación contiene `level=0`, `world_events=7`, `pending_effect=0`.

| Medida de v3/28027 | Base | Híbrido 2 |
|---|---:|---:|
| Niveles | 5 | 5 |
| Score | 4,2785976331 | 4,0723022791 |
| Acciones registradas, incluidos reinicios del runner | 784 | 1.264 |
| Decisiones del agente, excluidos esos reinicios | 765 | 1.232 |
| Reinicios automáticos | 19 | 32 |
| Acciones por nivel | 52, 457, 184, 45, 27 | 150, 791, 219, 45, 27 |

HOLD regula cuándo se vuelve a probar una tecla de reinicio. En H4 esa tecla
también reemplaza una copia que reproduce movimientos y puede sostener un
interruptor. La reconstrucción previa de B18 verificó este mecanismo con
frames idénticos; B19 comparte el prefijo y la primera intervención del caso.
`pending_effect=0` significa que se vació `_tried_at`, no que una acción
persistente haya dejado de ser necesaria. Una guarda puede dejar de aplicarse
y aun así persistir el daño en la trayectoria y el aprendizaje del actor.

La diferencia global es causal respecto a cambiar la política completa en
este entorno determinista. Atribuir toda la pérdida a una lectura individual
requiere intervenciones emparejadas adicionales. La reconstrucción del estado
privado del simulador sirve al diagnóstico humano, nunca como entrada del actor.
[Mecanismo y reconstrucciones anteriores](ECHO45-S6-B18-COST-FORENSICS.md).

**2. El buscador se encierra en un objetivo. Confirmado.**
`cost_guard_search.target_for` ordena por alcanzar +2, después menos pérdidas,
menor pérdida de score, ganancia neta e identificador. Sustituye al selector
anterior sin conservar su límite de descendientes. El presupuesto global
sigue acotado, pero ya no obliga a abandonar una rama estancada.

El híbrido dirige los intentos 3–12 al candidato 2: diez refinamientos de la
misma referencia. Ese candidato gana en A18 y v3/28031. El intento 9 vuelve a
ganar cuatro niveles en A53, pero conserva más pérdidas y no pasa a ser objetivo.
La ganancia de A53 ya se conocía del intento 1; el ranking del objetivo 2 no
la incluye en sus positivos. El archivo de historia existe, pero la selección
de qué ganancias merece conservar empobrece esa memoria.

El sintetizador dirige los intentos 4–12 al candidato 3, de +1 sin pérdidas.
Su conjunto positivo solo contiene ese +1: la propia cobertura estimada no
puede alcanzar +2 desde esa referencia. Puede descubrir ganancias nuevas por
casualidad, pero el criterio de búsqueda no las favorece. Necesita varias
ramas activas, un presupuesto de estancamiento y retorno a hipótesis con
ganancias complementarias. No se deben sumar ganancias de parches distintos
sin ejecutar su composición.

**3. Hay un hueco entre el lenguaje validable y el generable. Confirmado;
beneficio de ampliarlo todavía no medido.**
`precise_patch.validate` acepta de una a tres condiciones observables.
`precise_patch_grammar.conditions()` ofrece 1.205 guardas: 154 simples, 602
dobles y 449 triples. Las dobles requieren uno de cuatro anclajes prefijados;
las triples parten de solo tres pares prefijados. No enumera todas las
conjunciones del validador.

Por ejemplo, las tres guardas siguientes son válidas pero ninguna aparece
en el generador actual:

```text
pending_effect == 0 AND world_events <= 16
level >= 1 AND pending_effect == 0 AND world_events <= 16
goal_evidence == 1 AND pending_effect == 0 AND world_events <= 16
```

La primera tiene una variante con `reset_known=1` que sí se genera. El problema
es que ese anclaje ocupa una de las tres posiciones e impide añadir otra
restricción útil. Las otras dos separan algunas observaciones iniciales de
ganancia y pérdida, pero podrían causar pérdidas posteriores. **No son
soluciones verificadas y no deben introducirse como respuestas del agente.**

B20 debe declarar la ampliación de biblioteca, hacerla idéntica para los
brazos comparables y reconstruir sus certificados de equivalencia. Reutilizar
las particiones de umbrales de B19 para guardas nuevas podría podar propuestas
incorrectamente. La gramática completa tampoco garantiza que las observaciones
disponibles distingan todos los estados que exigen acciones diferentes.

**4. La puntuación del ranking es una aproximación débil. Confirmado.**
Para una guarda g, B19 calcula aproximadamente:

```text
G(g) = suma de ganancias del objetivo en casos con alguna lectura basal
       donde g es verdadera
L(g) = suma de frecuencias de lecturas modificadas en casos con pérdida
orden = (G(g) < 2, L(g), número de condiciones, orden textual)
```

Una coincidencia con cualquier lectura basal recibe la ganancia de toda la
partida, aunque no sea la intervención que la produjo. El coste mezcla
lecturas de distintos valores HOLD e historias del mismo control; una
asociación negativa con HOLD=1 no demuestra que HOLD=4 falle ahí. Las
frecuencias son sensibles a bucles que el propio candidato provoca.

En los intentos híbridos 3, 8 y 10, la cobertura predice al menos +2 pero
la ganancia real queda por debajo. El intento 6 del sintetizador tiene carga
negativa estimada cero y pierde score en 28027. Cero carga significa ausencia
de evidencia coincidente en esa memoria, no seguridad. Además, el orden
textual decide empates sin medir información nueva ni diversidad de resultados.

La reparación debe mantener por separado observaciones, hipótesis causales
y certificados. Conservar la incertidumbre es necesario para evitar que una
heurística se convierta en un veto injustificado a una reparación viable.

**5. La diversidad de valores no garantiza experimentos informativos.
Confirmado.** Cada tercer intento modifica la duración, pero vuelve a escoger
la guarda por ranking; no hay un diseño general que mantenga fijo un factor.
En el híbrido se probaron HOLD=2, 4 y 8 con `world_events<=8`, permitiendo ese
contraste concreto, pero sin eliminar la pérdida. No se recorrió toda la
escala declarada en doce oportunidades.

En síntesis, los intentos 4, 5, 7 y 10 prueban `path_pending=1` con HOLD 1, 0,
2 y 4. Dan exactamente el mismo comportamiento: mejoran score en A59 y no
añaden niveles. No son inertes frente a la base; son redundantes entre sí.
El certificado actual exige el mismo valor para descartar equivalencias y
por tanto no los evita. Son nueve comportamientos distintos en doce intentos
de síntesis; control tiene once e híbrido doce. La diversidad relevante debe
medirse también por el efecto sobre el caso que se intenta reparar.

No basta con ampliar ese certificado por intuición: igualdad observada entre
dos valores no autoriza descartar todos los valores intermedios en casos nuevos.
B20 puede usarla como señal de estancamiento y exigir prueba semántica completa
para podar sin ejecutar.

**6. La ventana de evidencia también restringe la búsqueda. Confirmado en el
código; peso causal pendiente de ablación.** El esquema se construye con tres
casos seleccionados, aunque se evalúan doce. Una guarda que no modifica ningún
consumo de esos tres queda fuera antes del ranking. El análisis de todos los
casos y de los consumos creados por candidatos debe alimentar al sintetizador;
el prompt puede recibir un resumen acotado con procedencia. Ampliar esa ventana
aumenta costes y exige medir presupuesto, no simplemente volcar más contexto.

**7. B19 no permite atribuir el fallo a la calidad general del LLM.** Una sola
salida inicial condiciona toda la historia híbrida. No hubo un modelo leyendo
cada error y proponiendo reparaciones nuevas. Cambiar a un modelo mayor o
añadir GPU no corrige el ranking, la biblioteca ni la semántica del actor.
Tampoco está demostrada una ventaja del híbrido frente a la síntesis: en B18
ambos produjeron el mismo comportamiento; en B19 ninguno pasa. Harán falta
ablaciones con igual presupuesto y varias semillas de propuesta.

**8. El mecanismo del entorno exige memoria temporal más precisa. Hipótesis
con fundamento, todavía sin ablación concluyente.** Dos situaciones con las
mismas features pueden requerir decisiones opuestas: reiniciar para salir de
un bloqueo o conservar una copia que sostiene una puerta. Si esa colisión se
confirma en observaciones accesibles al agente, ampliar conjunciones no bastará.
Se necesitarían features derivadas de historia visible: antigüedad de la
intervención, progreso observado de objetos remotos y persistencia de relaciones.
Ni índices de tareas ni estados privados H4 pueden convertirse en entradas.

**Qué reviso de la decisión de ingeniería anterior.** B19 sí implementó lo
anunciado: coste antes de ganancias excedentes, lecturas realmente modificadas
y variación de duración. No se había demostrado que ese conjunto bastara para
conservar eficiencia. Los tests acreditaban propiedades locales e integridad;
no cubrían el estancamiento de diez refinamientos, la pérdida de una rama útil
ni la cobertura combinatoria real de la gramática. La demostración retrospectiva
favorable del ranking partía de la regla B18 ya buena, mientras el ensayo
autónomo partió de una propuesta amplia. Faltó una comprobación del bucle
completo desde ese arranque, con un presupuesto realista y sin darle la solución.

Una auditoría que reproduce el mismo algoritmo confirma el resultado, incluso
cuando el algoritmo busca mal. Por ello B20 necesita pruebas de cobertura y
de comportamiento de la búsqueda además de replays. No corresponde alterar
el juez para convertir estos resultados en éxito.

| Posible explicación | Estado actual | Cómo discriminarla |
|---|---|---|
| Corrupción de fuentes, caché o ejecución B19 | Sin evidencia; auditoría y hashes válidos | Mantener auditoría separada y comprobación de contenido |
| Fallo del monitor de red causó el rojo | Descartado por finalización y replays | Separar estado del transporte y estado científico |
| Basta aumentar HOLD con la guarda B18 fija | Refutado en las diez duraciones medidas | Cambiar ámbito o representación, no repetir ese barrido |
| Sesgo del selector y biblioteca estrecha | Confirmados; reparación aún sin resultado | Ablación de búsqueda y biblioteca por separado |
| Falta de señales temporales observables | Posible | Pares de historias, intervención emparejada y prueba de colisiones |
| Gramática actual o ampliada no contiene solución conservadora | Abierto | Censo acotado declarado; un negativo solo acota lo explorado |
| Doce propuestas insuficientes | Posible; no explica por sí sola la mala selección | Curvas de cobertura y rendimiento por coste, con topes |
| Sobreajuste a los doce casos conocidos | Riesgo alto por selección dirigida | Desarrollo amplio y luego reserva nueva sin realimentación |
| Mejora del buscador, sin beneficio propio del LLM | Compatible con B18/B19 | Comparación pareada con síntesis sin LLM |
| Pérdidas de score inevitables para esa familia de intervención | Abierto | Frontera ganancia/coste; evaluar otras intervenciones si persiste |
| Interacción con reglas aceptadas o con memoria posterior | Plausible y parcialmente observada | Evaluar política completa; restaurar estado exacto en diagnósticos |

S6 resulta difícil porque exige descubrir una mejora, conservar cada caso,
transferirla y superar controles de atribución. Ganar más niveles y perder
menos tiempo son objetivos distintos. Un cambio temprano puede alterar memoria
y trayectoria mucho después. El espacio explorado es estrecho y el investigador
ha tenido sesgos que desperdician oportunidades. Aun corrigiéndolos, la existencia
de una solución con el presupuesto y las observaciones actuales queda por medir.

**Quedan dos bloques superiores de ECHO-4.5:** S6 y el cierre final. REL-DSL-1,
memoria/política 3E, refinamiento/síntesis, multi-view, consistencia y guía 500k
están verdes en los contratos sintéticos autorizados; su integración técnica
también. No equivale a transferencia ARC confirmada. El cierre requiere esa
evaluación, retención global, auditoría y decisión de versión. ECHO-5, 5.1, 5.5
y RSI son líneas posteriores, no módulos adicionales pendientes de 4.5.
[Corte de módulos V3](ECHO45-RELATIONAL-V3-RESULTS.md).

Siguiente paso: [diseño B20](ECHO45-S6-B20-PLAN.md).
Conocer varios fallos permite corregirlos y hacer mejores experimentos; no
demuestra que ya conozcamos todos ni garantiza un resultado positivo futuro.
