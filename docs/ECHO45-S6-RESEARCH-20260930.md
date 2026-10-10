# Investigación para cerrar S6: diagnóstico y propuestas

**Fecha: 30 de septiembre de 2026.**
Estado operativo comprobado a las **21:04 CEST (19:04 UTC)** de esa fecha.
Informe de investigación preparado a petición del responsable de echoAI.
Las propuestas de este documento **no están implementadas ni medidas**.
El objetivo es elegir la siguiente condición experimental a partir de evidencia,
sin modificar B12-R1 ni rebajar los requisitos para declarar S6 verde.

## 1. Conclusión y pregunta de investigación

**S6 todavía no está verde.** La campaña B12-R1 terminó con **ECHO 378,
FIJO 378 y SEMILLA 365 niveles en desarrollo A**. Cada brazo con modelo
aceptó una mejora, exactamente la misma. La auditoría independiente sigue
pendiente en el corte de este informe; el examen reservado permanece cerrado.
Una auditoría correcta de este empate confirma un resultado negativo para
la promoción: no aporta una nueva mejora.

La señal más útil no es simplemente «el modelo es pequeño». Hay tres
problemas observables en el bucle que merece la pena investigar primero:

1. **Refinamiento sin conservar su objetivo.** ECHO dedicó 25 de 30 propuestas
   a `REFINE`. Desde la tercera ronda, el prompt ya no contenía en su historial
   la propuesta que el selector pretendía refinar. Sus contrastes no aparecían
   en el feedback de ninguna de esas cinco rondas.
2. **Feedback con retraso.** La campaña genera cinco propuestas antes de
   verificar ninguna. Las cinco parten del mismo programa e historial, aunque
   luego se verifican secuencialmente contra un programa que puede haber cambiado.
3. **Poca diversidad de comportamiento.** Las 60 propuestas produjeron solo
   ocho comportamientos distintos medidos en A. Cambiar el JSON a menudo no
   cambió lo que hacía el agente.

Son hechos reproducibles del código y los artefactos; **todavía no demuestran
cuál causó el empate ni que corregirlos baste para superar B1–B5**.

**Pregunta para Opus:** ¿cuál es la intervención mínima que puede transformar
la selección adaptativa de evidencia de ECHO en una ventaja reproducible sobre
FIJO, manteniendo conservación, presupuesto comparable y examen independiente?

## 2. Qué se está evaluando realmente

Este ensayo es **S6-B sobre juegos interactivos del generador gym v2/v3**.
No es el protocolo inicial de 201 tareas ARC de rejillas, ni una medición
oficial de ARC-AGI-1, 2 o 3. Sus puntuaciones cuentan niveles de juegos;
no deben convertirse en porcentajes esperados de aquellos benchmarks.

ECHO usa el agente `Arc3EchoV58`. Un modelo externo propone un pequeño parche;
ECHO lo ejecuta y decide si incorporarlo. El modelo actual es
Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, CPU con cuantización dinámica
int8, cuatro hilos, temperatura 0,7 y top_p 0,95. Cada petición permite
6000 tokens de entrada y 900 de salida.

La autonomía que se busca demostrar es acotada: **observar → elegir qué pedir
→ obtener una propuesta → verificar → aceptar/rechazar → usar el resultado
en la siguiente petición**, sin seleccionar reparaciones manualmente durante
el ensayo. No se entrenan los pesos del modelo ni se demuestra autonomía general.

| Elemento | Condición B12-R1 |
|---|---|
| Desarrollo A | 80 partidas, cinco niveles por partida: máximo 400; 2000 decisiones por partida |
| Validación protegida B | 40 partidas; el modelo recibe veredictos, nunca sus casos ni trayectorias; reutilizada desde B11 y declarada como tal |
| Campaña | Seis rondas × cinco propuestas × dos brazos: 60 propuestas, más dos calibraciones |
| Examen reservado | 360 partidas, 1800 niveles por brazo; tres repeticiones por caso; no abierto |
| FIJO | Petición genérica, tres casos incompletos seleccionados con regla fija y feedback propio |
| ECHO | Selección adaptativa de casos y tipo de petición, con el mismo modelo, lenguaje y verificador |
| SEMILLA | Agente inicial sin parches del modelo |
| SIN FILTRO | Mismas propuestas ECHO y mismo orden, incorporando las seguras y ejecutables sin V3/V4 |

El lenguaje permite añadir **un control y entre una y tres condiciones
conjuntas** por propuesta, hasta 32 parches. Los controles disponibles son:

- `REVALIDATE_NOOP`: revisar una predicción de movimiento tras observar
  contradicciones repetidas en las que no cambia el estado.
- `HOLD`: ajustar una espera futura al probar una tecla de reinicio conocida.
- `COOLDOWN_CAP`: limitar una espera que ya está en marcha.

La gramática exige que la condición coincida con alguna oportunidad conjunta
observada en desarrollo. Esto acredita aplicabilidad, no utilidad.

### Condiciones de aceptación y de verde

| Puerta | Qué debe cumplirse |
|---|---|
| V1 | Formato y operaciones seguros y permitidos |
| V2 | Ejecución y reproducción determinista |
| V3 | Al menos dos niveles adicionales en A, sin perder niveles ni score en ninguna partida individual A |
| V4 | Ninguna pérdida individual de niveles ni score en B; tolerancia numérica de score 1e-10 |
| Promoción de campaña | Alguna aceptación ECHO y niveles A de ECHO estrictamente mayores que FIJO |
| B1, examen final | Niveles ECHO ≥105% de SEMILLA, con score medio no menor |
| B2, examen final | ECHO resuelve más niveles que FIJO |
| B3, examen final | ECHO resuelve más niveles que SIN FILTRO |
| B4, retención | Conserva niveles y score **agregados** en ocho juegos oficiales de desarrollo, con tres repeticiones |
| B5, auditoría | Procedencia, fuentes, modelo, peticiones, veredictos, solver y replays válidos |

**Solo B1–B5 juntos, después de promoción, auditoría y congelación de los
cuatro brazos, permiten declarar S6 verde.** B4 es agregado según el código
actual; no equivale a conservación de cada juego oficial individual.
El verde global de ECHO-4.5 exige además las otras puertas de su roadmap.

Fuentes normativas: [contrato B12](ECHO45-S6-B12-DESIGN.md),
[contrato B11](ECHO45-S6-B11-DESIGN.md) y función `checks` en
[s6_precise_exam.py](../seed/s6_precise_exam.py).

## 3. Qué ha fallado y qué sí ha avanzado

| Etapa | Evidencia | Interpretación y límite |
|---|---|---|
| Control humano de transición | 178 → 186 en el A anterior, sin las regresiones prohibidas para ese control | Existía una reparación útil; no demuestra descubrimiento autónomo ni basta para el A ampliado |
| B9 | ECHO 534, FIJO 534; cero aceptaciones; las condiciones no coincidían con las oportunidades observadas | El lenguaje podía producir reparaciones inaplicables |
| B10 | 18 propuestas con ganancia A de ocho niveles, rechazadas por pérdidas individuales de eficiencia en B | Aplicabilidad y ganancia agregada no garantizan conservación |
| Piloto B11 | ECHO 1129, FIJO 1108; tres aceptaciones ECHO; dos parejas ganadoras y ninguna perdedora; 36 veredictos auditados | Señal favorable real, pero los totales suman tres actores: no se comparan directamente con 378 |
| Campaña B11 | Interrupción al exceder 6000 tokens: una petición tenía 6372 | Fallo operativo, no una conclusión de capacidad |
| B12 / R1 | Contexto acotado y recuperación de una interrupción remota; campaña completa, 378 frente a 378 | La ejecución avanzó; la ventaja adaptativa del piloto no reapareció |

B12 heredó la calificación del piloto B11 tras verificar la identidad de
sus 36 peticiones; **no lo replicó de nuevo ni heredó sus políticas**.
La campaña empezó desde programas vacíos.

La recuperación R1 amplió el límite remoto de c2–c5 de 3600 a 7200 segundos.
Exigió reproducir exactamente siete respuestas parciales ya obtenidas y
contabilizar su coste adicional. No son siete nuevas muestras independientes.
Los tiempos de la interrupción son compatibles con el límite de ejecución;
la API no proporcionó un motivo más preciso.

Las 60 peticiones reales de esta campaña usaron **tier 0**, sin reducción
del contexto, y entre 1428 y 4665 tokens. Por tanto, el olvido descrito abajo
procede de la selección previa del historial, **no del compactador B12**.

Fuentes: [control de transición](ECHO45-S6-TRANSITION-RESULTS.md),
[B9](ECHO45-S6-B9-RESULTS.md), [B10](ECHO45-S6-B10-RESULTS.md),
[diagnóstico anterior](ECHO45-S6-DIAGNOSIS-20260929.md),
[B11](ECHO45-S6-B11-RESULTS.md),
[interrupción por contexto](ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS.md),
[B12](ECHO45-S6-B12-RESULTS.md) y [adenda R1](ECHO45-S6-B12-RECOVERY1.md).

## 4. Hallazgos nuevos y reproducibles

### 4.1 El selector queda concentrado en un refinamiento antiguo

En `contrastive_requests.select`, cualquier propuesta rechazada con ganancia
A positiva activa `REFINE`. Se busca en **todo** el historial y no hay caducidad,
límite de intentos ni condición de abandono de ese objetivo. Mientras exista,
se omite el planificador de `CONTRADICTION`, `WAIT` y `GENERALIZE`.

En esta campaña se eligió reiteradamente el intento ECHO **id 2**, que había
ganado un nivel, pero fue rechazado por V3. Los tipos fueron cinco
`CONTRADICTION` y 25 `REFINE`; no hubo peticiones `WAIT` ni `GENERALIZE`.

Sin embargo, `contrastive_evidence.feedback` conserva solo los últimos seis
intentos y añade contrastes detallados solo a los dos últimos:

| Ronda, numerada 1–6 | Objetivo del selector | Propuesta objetivo dentro del feedback | Contrastes del objetivo dentro del feedback |
|---|---|---|---|
| 1 | Sin objetivo REFINE | No aplica | No aplica |
| 2 | id 2 | Sí | No |
| 3–6 | id 2 | No | No |

El selector sí emplea índices de los antiguos contrastes para escoger casos.
Eso no transmite al modelo el programa antiguo ni la comparación que necesita
para repararlo. Es como pedirle a un mecánico «corrige el arreglo anterior»
mostrándole el coche, pero retirando la ficha de aquel arreglo.

### 4.2 Hay seis ciclos de feedback, no treinta

`seed.s6b11.run_phase`, reutilizado por B12, construye un lote completo antes
de generar y evaluar sus respuestas. El programa aceptado puede cambiar tras
la primera verificación, mientras las otras cuatro propuestas fueron generadas
para el programa anterior. La exclusión de propuestas históricas tampoco puede
ver las propuestas hermanas que aún no se han producido.

En las rondas 2–6 de ECHO, las cinco peticiones de cada lote tenían exactamente
el mismo prompt. Las respuestas pueden diferir por muestreo, pero ninguna
conoce el resultado de la anterior. El piloto B11 empleaba lotes de una
propuesta: esta diferencia es una hipótesis importante, aunque semillas y
número total de propuestas también cambiaron y confunden la comparación.

### 4.3 Predomina la repetición de comportamientos

| Medida de campaña | ECHO | FIJO |
|---|---:|---:|
| Propuestas | 30 | 30 |
| Aceptadas | 1 | 1 |
| Rechazadas en V3 | 29 | 29 |
| JSON de propuesta distintos | 14 | 20 |
| Comportamientos distintos medidos en A | 6 | 5 |
| Propuestas equivalentes a un comportamiento propio anterior | 24 | 25 |
| Propuestas sin cambios de acciones respecto al programa aceptado | 16 | 6 |
| Propuestas con alguna pérdida individual A | 9 | 4 |
| Operaciones REVALIDATE_NOOP / HOLD / COOLDOWN_CAP | 28 / 0 / 2 | 23 / 3 / 4 |

La unión contiene ocho comportamientos. Los recuentos de pérdidas y de
repeticiones no son categorías excluyentes. La equivalencia se mide mediante
acciones, frames, niveles, reinicios y score en A; **no prueba equivalencia
universal de programas**. `HOLD` estaba permitido en los seis lotes ECHO:
su ausencia no se explica por una prohibición de la gramática.

Ambos brazos aceptaron primero el mismo parche: `REVALIDATE_NOOP=1` cuando
`body_known`, `reset_known` y `reset_useful` valen 1. Dio +13 niveles A.
Después, ninguna propuesta pasó V3. Las 58 restantes **no llegaron a V4**:
el atasco actual ya aparece en desarrollo, antes del filtro protegido.

La mejora 365 → 378 es **+3,56% relativo en niveles**, o pasar de 91,25% a
94,50% de los 400 niveles disponibles: +3,25 puntos porcentuales. Como mera
referencia aritmética, un +5% sobre 365 exigiría 384, seis más que 378.
**Ese cálculo sobre A no acredita B1**, que se evalúa en otra distribución
reservada, ni B2/B3, que exigen superar los otros brazos.

### 4.4 El lenguaje añade parches, pero no edita los anteriores

`local_patch.append` agrega una regla. `settings` aplica la última asignación
coincidente. No existe una operación de reemplazar o eliminar una regla.
Añadir una condición más estrecha no borra la regla amplia que sigue activa
fuera de esa condición. Además, aunque el ejecutor reconoce
`REVALIDATE_NOOP=0`, la gramática de propuestas permite únicamente 1–8.

Esto limita cómo se puede reparar una excepción después de aceptar una regla.
No demuestra que falte una solución en el lenguaje actual: hace falta un
control de capacidad antes de atribuirle el estancamiento.

### 4.5 Los contrastes pueden quedar lejos de la decisión causante

El feedback muestra hasta tres casos y las acciones en la primera divergencia
y el paso anterior. Una modificación de una espera o predicción puede haber
ocurrido antes. La información es real, pero no siempre identifica dónde
actuó el control. Es una limitación de observabilidad que debe medirse,
sin inventar causas internas a partir de una diferencia de acciones.

Estos hallazgos se apoyan en [evidence.json](../lab/research/s6-brief-20260930/evidence.json),
que contiene recuentos, comprobaciones por petición y hashes de sus entradas.
Se reproduce sin inferencia ni partidas nuevas mediante:

```bash
python3 lab/research/s6-brief-20260930/analyze.py
```

El analizador exporta datos de desarrollo A y metadatos del protocolo, no
casos protegidos B ni resultados de examen.

## 5. Propuestas de investigación, por prioridad

### P1 — Conservar el objetivo de refinamiento y evitar que monopolice el selector

**Hipótesis:** el modelo recibe instrucciones de refinar sin la evidencia
necesaria; además, el selector insiste sobre un intento antiguo sin aprender
del fracaso de sus refinamientos.

**Cambio a estudiar:** un registro explícito de objetivo con programa,
programa base, ganancia, pérdidas A y contrastes positivos/negativos existentes.
Debe caber en el presupuesto antes de rellenar historial secundario. Registrar
intentos y ganancia aceptada por objetivo; tras un límite prefijado sin avance,
pasar a otro objetivo o mecanismo. No conservar indefinidamente un objetivo
solo porque alguna vez tuvo ganancia positiva.

**Prueba:** separar dos factores, memoria del objetivo y política de abandono.
Primero reproducir con fixtures la secuencia observada: el objetivo debe seguir
visible cuando sale de los últimos seis intentos, y el selector debe recuperar
exploración. Después comparar las variantes con semillas y presupuestos
emparejados. El acceso a memoria y sus límites debe quedar definido para ambos
brazos; cualquier asimetría adicional debe declararse como parte del tratamiento.

**Éxito local:** objetivo y contrastes disponibles en el 100% de las peticiones
REFINE pertinentes; ningún bloqueo indefinido; posteriormente, más mejoras
aceptadas y ventaja ECHO sobre FIJO. Arreglar el fixture no demuestra S6.

**Coste y riesgo:** bajo en código y fixtures; puede aumentar tokens o hacer
abandonar objetivos útiles demasiado pronto. Fuentes:
[selector](../echo_arc/contrastive_requests.py),
[feedback](../echo_arc/contrastive_evidence.py),
[contexto](../echo_arc/context_requests.py). **Prioridad máxima.**

### P2 — Verificar antes de construir la siguiente petición

**Hipótesis:** el retraso de cinco propuestas rompe buena parte de la adaptación
que el piloto con lotes de una propuesta podía aprovechar.

**Cambio a estudiar:** petición → respuesta → V1–V4 → actualizar programa e
historial → siguiente petición. Mantener el modelo cargado si el transporte
lo permite, sin convertir menor latencia en más intentos ocultos.

**Prueba:** comparar lotes de una y cinco propuestas con el mismo total por
brazo, semillas, modelo, datos y límites de tokens. Aplicar el cambio de
orquestación a FIJO y ECHO. Verificar que cada prompt declara el hash del
programa que realmente se evalúa. El piloto y campaña históricos no bastan
como comparación causal por sus otras diferencias.

**Éxito local:** cero propuestas verificadas sobre un programa distinto del
declarado al generarlas; mayor ganancia útil por llamada y menos repeticiones.
**Coste y riesgo:** más sincronización remota y tiempo de pared; una conexión
persistente puede mitigarlo. Fuente: [run_phase](../seed/s6b11.py).
**Prioridad máxima junto con P1.**

### P3 — Buscar diversidad de efectos, no solo de texto

**Hipótesis:** se consume casi todo el presupuesto recorriendo variantes que
actúan igual en los estados observados.

**Cambio a estudiar:** conservar una memoria compacta de comportamientos ya
medidos, sus pérdidas y las oportunidades de control utilizadas; orientar la
siguiente petición hacia mecanismos aún no explorados. Normalizar reglas para
detectar repeticiones exactas dentro del lote si se conserva procesamiento por
lotes. Una pequeña población diversa de candidatos puede ser una alternativa
al único candidato «mejor».

**Prueba:** comparar el selector actual, el selector con diversidad y un
muestreador determinista de la misma gramática. Medir comportamientos nuevos
por llamada, ganancia aceptada y regresiones, con presupuesto total idéntico.

**Éxito local:** superar las seis conductas distintas ECHO actuales bajo una
comparación emparejada y, además, conseguir utilidad. La novedad por sí sola
no es una mejora. Las coincidencias sobre observaciones disponibles son una
heurística: un candidato puede visitar estados nuevos. No autorizan omitir
V1–V4 ni declarar equivalencia global. Toda propuesta, descarte, rama y
remuestreo cuenta en el coste.

**Coste y riesgo:** memoria y verificaciones adicionales; fomentar diversidad
sin utilidad puede empeorar el resultado. Fuentes:
[gramática](../echo_arc/contrastive_grammar.py) y
[comparación](../echo_arc/contrastive_evidence.py). **Prioridad alta.**

### P4 — Medir si hace falta editar o componer reglas

**Hipótesis:** una mejora adicional requiere restringir una regla ya aceptada,
desactivarla en una excepción o coordinar dos controles. El lenguaje de adición
individual podría no representar esa reparación de forma eficiente.

**Prueba previa:** buscar con un presupuesto pequeño y explícito, solo en A,
una reparación con el lenguaje actual y otra con edición acotada. Comparar
añadir, reemplazar una regla por índice, desactivar de forma local y combinar
dos operaciones atómicas. Evaluar el programa completo, no solo el fragmento.

Un control escrito por una persona o encontrado por enumeración se etiqueta
**control de capacidad**, nunca mejora autónoma. No se entrega su solución
al modelo para después atribuirle el descubrimiento. Si la búsqueda acotada
no encuentra nada, no prueba imposibilidad del lenguaje.

**Éxito local:** demostrar una reparación adicional sin regresiones A que
justifique el cambio de representación; después, comprobar que ECHO puede
descubrirla por su propio bucle y pasar V4. Si el lenguaje original ya permite
mejoras accesibles, priorizar P1–P3 antes de ampliar la arquitectura.

**Coste y riesgo:** espacio de búsqueda mayor y semántica más difícil de auditar.
FIJO y ECHO deben compartir exactamente el nuevo lenguaje. SIN FILTRO necesita
una semántica de edición total y determinista: las referencias a reglas pueden
divergir entre brazos. Definirla antes del ensayo, sin reinterpretar rechazos
retroactivamente. Fuentes: [parches](../echo_arc/local_patch.py),
[extensión precisa](../echo_arc/precise_patch.py),
[transiciones](../echo_arc/stale_transition.py). **Prioridad alta, condicionada
al control de capacidad.**

### P5 — Mostrar el punto de intervención y su consecuencia

**Hipótesis:** la primera acción diferente no contiene la evidencia necesaria
para entender una espera útil o una revisión de predicción perjudicial.

**Cambio a estudiar:** asociar el evento real de aplicación del control con
su observación anterior, resultado y posterior divergencia. Comparar este
resumen con el contraste actual, a igual presupuesto de tokens. Usar solo
registros reales de desarrollo y añadir instrumentación únicamente en una
condición nueva; comprobar paridad con y sin observador.

**Prueba:** un conjunto de fallos A prefijado, incluyendo mejoras parciales
con pérdidas. Medir cuántas propuestas eliminan la pérdida sin destruir la
ganancia, frente al feedback actual. No pedir al LLM que invente la causa;
registrar sus propuestas como hipótesis y comprobarlas ejecutándolas.

**Coste y riesgo:** más trazas y tiempo; el evento de intervención tampoco
prueba por sí solo toda la cadena causal. Fuente:
[evidencia contrastiva](../echo_arc/contrastive_evidence.py).
**Prioridad media; subirla si P1 conserva contexto pero no mejora reparaciones.**

### P6 — Separar capacidad del modelo, sesgo del formato y valor del selector

**Hipótesis:** el modelo puede preferir REVALIDATE_NOOP por su probabilidad de
generación o formato, sin aprovechar controles alternativos válidos. También
es posible que una búsqueda acotada alcance lo mismo sin modelo.

**Prueba:** sobre problemas de desarrollo congelados, comparar el modelo actual,
un muestreador de gramática y, solo si el diagnóstico lo justifica, otro modelo
o backend. Mantener prompts y gramática en las comparaciones de modelo; para
estudiar formato, modificar únicamente el orden/presentación de opciones.
Fijar revisiones, semillas y reglas de equivalencia de coste antes de generar.

**Métricas:** controles usados, comportamientos nuevos, soluciones aceptadas,
tokens, segundos de inferencia y número de verificaciones. Registrar tanto
presupuesto de llamadas como coste: un modelo mayor no resulta comparable
solo por recibir treinta peticiones.

**Criterio:** si la enumeración o el muestreo igualan sistemáticamente al LLM,
no atribuir al neocórtex una ventaja no demostrada. Si un modelo mejor solo
mejora por igual FIJO y ECHO, todavía falta explicar B2. **Coste medio/alto;
no cambiar de modelo antes de corregir pérdidas demostradas de información.**

### P7 — Abstracciones temporales y composición reutilizable, si lo anterior no basta

**Hipótesis:** los tres controles actuales no permiten adquirir la capacidad
que falta. Harían falta programas de varios pasos, relaciones entre objetos,
memoria temporal o subrutinas reutilizables.

**Prueba:** una extensión pequeña motivada por errores A, con tareas sintéticas
que separen representación, adquisición y transferencia a casos nuevos.
Después medir adquisición autónoma y conservación con presupuesto explícito.
Las ramas hipotéticas o «universos» deben ser programas o simulaciones de
desarrollo contabilizados; no acceso oculto al futuro correcto del examen.

**Coste y riesgo:** alto; puede requerir otra etapa del roadmap. La ampliación
500K obtuvo 6/250 frente a 3/250 sin guía en otra comparación ARC-1 de
desarrollo, pero no fue integrada en S6 ni acredita que más memoria amplíe
las reglas expresables. Son capacidades distintas.
Fuente: [comparación 500K](ECHO45-CAPACITY500K-ARC1-RESULTS.md).
**Prioridad posterior a P1–P6, salvo evidencia clara del control de capacidad.**

## 6. Secuencia propuesta y reglas para interpretar el resultado

1. **Terminar la auditoría B12-R1 y archivar su resultado real.** No tocar
   fuentes congeladas, instrumentos, datos ni umbrales. Si se reproduce el
   empate, cerrar esta condición sin promoción; no abrir su examen para
   buscar una sorpresa favorable.
2. **Diagnóstico sin nuevas llamadas al modelo.** Reproducir este informe,
   construir fixtures para P1/P2 y probar semántica de parches. Son controles
   de software, no evidencia de mejora autónoma.
3. **Elegir una intervención mínima y prerregistrarla.** Definir
   población, cohortes, semillas, presupuesto, métricas, ablaciones y criterios
   de abandono. No aplicar siete ideas simultáneamente y atribuir el efecto
   a la preferida.
4. **Piloto nuevo desde cero.** Un diseño del tamaño de B11 cuesta 36 propuestas
   —tres semillas × seis propuestas × dos brazos— más calibraciones. Cada
   variante adicional consume su propio presupuesto; las respuestas viejas
   no sirven como respuestas de prompts modificados.
5. **Confirmación del mecanismo y campaña.** Una comparación limpia de lotes
   1 frente a 5 con treinta propuestas por brazo, tres semillas y dos
   condiciones supondría **360 propuestas**, más calibraciones. Es una opción
   de investigación, no trabajo autorizado por este informe ni un coste ya
   incurrido. Elegir el diseño mínimo suficiente antes de lanzarlo. Después,
   una campaña nueva con el presupuesto prefijado, seguida de auditoría.
6. **Congelar cuatro políticas, abrir una reserva independiente una sola vez
   y exigir B1–B5.** Si falla, documentar cuál y concluir negativo. No escoger
   retrospectivamente políticas, semillas o métricas para cambiar el resultado.

No hay una duración responsable para «S6 verde» mientras no aparezca una
mejora reproducible. Puede estimarse la duración de una ejecución con sus
tiempos medidos; no el número de hipótesis que necesitará la investigación.

La validación B devuelve poca información, pero sus veredictos también pueden
guiar indirectamente intentos repetidos. La condición siguiente debe declarar
qué cohortes reutiliza y, preferentemente, fijar una nueva B protegida y una
reserva independiente **antes** de conocer sus resultados. No mover casos
difíciles de la reserva al desarrollo ni escoger semillas por su puntuación.

B2 compara actualmente **selección de casos más política de petición**; no
aísla solo la redacción. B3 prueba el efecto de verificar sobre la secuencia
de propuestas de ese ensayo; si SIN FILTRO empata, falta esa demostración,
aunque el sistema haya mejorado respecto a SEMILLA. No se debe perjudicar
artificialmente a SIN FILTRO para asegurar una victoria.

Además de las puertas binarias, informar resultados por semilla/familia,
dispersiones, niveles ganados/perdidos y coste total. Una victoria pequeña en
una sola campaña no justifica una afirmación universal sobre autonomía.

## 7. Literatura primaria que merece contrastar

Estas referencias aportan mecanismos, **no predicciones de puntuación ECHO**
ni una garantía de cerrar S6. Se seleccionaron por relación con el diagnóstico,
no como una revisión exhaustiva del estado del arte.

| Trabajo | Qué investigar para ECHO | Límite de la analogía |
|---|---|---|
| [Self-Refine — Madaan et al., 2023](https://arxiv.org/abs/2303.17651) | Iterar propuesta, feedback y revisión conservando el objeto que se revisa; P1/P2 | Su feedback del modelo no sustituye los resultados del verificador ECHO |
| [Reflexion — Shinn et al., 2023](https://arxiv.org/abs/2303.11366) | Memoria de episodios y feedback sin actualizar pesos; P1 | Una reflexión textual plausible no demuestra aprendizaje ni es una traza interna literal |
| [Combinatorial Sketching for Finite Programs — Solar-Lezama et al., 2006](https://people.csail.mit.edu/asolar/papers/asplos06-final.pdf) | Síntesis acotada y refinamiento mediante contraejemplos; P3/P4/P5. Véase también la [explicación de CEGIS del autor](https://people.csail.mit.edu/asolar/SynthesisCourse2020/Lecture10.htm) | Pasar ejemplos empíricos no es una prueba formal para todos los juegos |
| [FunSearch — Romera-Paredes et al., publicado en línea en 2023](https://www.nature.com/articles/s41586-023-06924-6) | Programas ejecutables, evaluación externa y población diversa; P3/P6 | Sus presupuestos y problemas difieren; no extrapolar éxito a treinta propuestas |
| [DreamCoder — Ellis et al.](https://arxiv.org/abs/2006.08381) | Adquirir abstracciones reutilizables y guiar síntesis de programas; P4/P7 | Una biblioteca útil requiere adquisición y transferencia medidas, no solo más memoria |
| [Tree of Thoughts — Yao et al., 2023](https://arxiv.org/abs/2305.10601) | Explorar alternativas y retroceder, aplicado aquí a candidatos ejecutables; P3/P7 | La evaluación textual de ramas no reemplaza V1–V4; cada rama consume presupuesto |

ECHO ya tiene generación de programas, verificación externa, historial y
selección adaptativa. La investigación debe precisar **qué falta en su
implementación concreta**, en vez de recomendar esos nombres como si fueran
componentes ausentes.

## 8. Evidencia y reproducibilidad

- [Resumen calculado y hashes](../lab/research/s6-brief-20260930/evidence.json).
- [Analizador de solo lectura de campaña](../lab/research/s6-brief-20260930/analyze.py).
- [Campaña original](../lab/seed/s6b12-20260930/campaign.json) y sus seis
  `campaign/round-N.json`: fuentes locales completas; no hace falta entregarlas
  íntegras a otro modelo, pues pueden contener datos protegidos ajenos al resumen.
- [Estado de B12](ECHO45-S6-B12-RESULTS.md) y
  [seguimiento vivo](ECHO45-S6-B12-LIVE.md): consultar para conocer el desenlace
  de la auditoría posterior a este corte.
- [Roadmap ECHO-4.5 / ECHO-5](ECHO45-ECHO5-ROADMAP.md): cerrar S6 no equivale a
  cerrar automáticamente los otros módulos ni a acreditar puntuación ARC oficial.

Este informe no lanza inferencias, partidas, campañas ni exámenes. Añade
análisis de resultados ya obtenidos y una propuesta de investigación para
decidir el siguiente experimento.
