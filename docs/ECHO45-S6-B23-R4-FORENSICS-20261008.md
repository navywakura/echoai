# B23-R4: autopsia de búsqueda y correcciones para B24

8 de octubre de 2026. Investigación sobre evidencia ya recogida. Cero partidas
nuevas, cero inferencias, cero acceso a reserva o examen. S6 sigue abierto.
La corrección se incorpora al [plan existente B24](ECHO45-S6-B24-CONDITIONAL-PLAN.md);
su efecto científico todavía no está medido.

**El lenguaje permite una mejora conservadora en este micro, pero ninguno de
los dos investigadores la encontró.** Ambos modelos encontraron exactamente
la misma política de 61 a 65 niveles. Conservó los niveles de cada partida,
pero perdió score en cinco. El resultado aceptado fue cero mejoras; hubo
mejoras parciales de capacidad que no superaron la conservación exigida.

La evidencia completa de Kaggle ocupa 43.484.499 bytes; SHA-256
`6f0cbf1d3f5001adb676481963321ea87d8593c8a213712afc7e030fce8a4861`.
La revisión local recalculó los 924 registros de partidas, las 66 mediciones
y 22 ternas medición/replay/auditoría. Comprobó 88 fuentes congeladas, las
36 entradas del investigador, los bytes de los 36 prompts y 264 archivos
con hash de las 44 llamadas, incluidas ocho de formato. Todo coincide.
Esta comprobación documental no vuelve a ejecutar el simulador.

Recibos: [análisis recalculado](../lab/seed/s6b23r4-forensics-20261008/analysis.json),
[36 propuestas completas](../lab/seed/s6b23r4-forensics-20261008/proposals.csv),
[script reproducible](../lab/seed/s6b23r4-forensics-20261008/analyze.py).

## Qué ocurrió realmente

| Medida | Qwen 14B | Qwen 7B |
|---|---:|---:|
| Llamadas científicas | 18 | 18 |
| Duplicados exactos, sin nueva partida | 12 | 4 |
| Propuestas distintas medidas | 6 | 14 |
| Medidas con guarda inactiva en toda la base | 3 | 9 |
| Medidas activas | 3 | 5 |
| Medidas activas con pérdidas individuales | 3 | 5 |
| Guardas distintas propuestas | 2 | 8 |
| Duraciones distintas | 3 | 6 |
| Mejor ganancia neta de niveles | +4 | +4 |
| Propuestas aceptadas | 0 | 0 |

La partición de los 36 intentos es **16 duplicados + 12 inactivos medidos +
8 activos con pérdidas**. Las doce propuestas inactivas reprodujeron las
acciones de la base. No hay que sumar otra vez los duplicados inactivos.
Entre ambos brazos hubo 18 propuestas distintas y siete firmas de conducta
medida. Las firmas no prueban equivalencia de políticas fuera de estas
trayectorias.

El 14B probó únicamente HOLD 4, 8 y 12 y dos guardas: `body_known`,
`reset_known` y `reset_useful`, todos a cero o todos a uno. La segunda guarda
copia las condiciones de la regla REVALIDATE_NOOP ya presente en la política
base, aunque esa regla interviene en otro mecanismo. Esa coincidencia es
observable; no permite afirmar por qué el modelo la eligió.

El 7B usó HOLD 2, 4, 8, 12, 16 y 32. También propuso combinaciones como
`body_known=0, click_only=1, count_known=1`, que no coinciden con ninguna
lectura HOLD registrada. En las 181 lecturas de la base, `body_known=1`,
`reset_known=1`, `click_only=0`, `count_known=0` y `order_known=0` son
constantes. Ninguno de los 36 intentos usó condiciones numéricas, pese a
tener disponibles `level`, `world_events` y sus átomos legales. Todos usaron
tres condiciones booleanas. No probaron HOLD 0, 1, 20 ni 24.

## Qué hizo la regla de +4 y por qué fue rechazada

N14 la propuso en la plaza 12; N7, en la 5:

```json
{"patches":[{"set":{"HOLD":8},"when":{"body_known":["eq",1],"reset_known":["eq",1],"reset_useful":["eq",1]}}]}
```

HOLD se lee al probar deliberadamente una tecla de reinicio conocida; inicia
un intervalo que restringe nuevas pulsaciones de esa tecla. El actor puede
seguir ejecutando otras acciones durante ese intervalo. No significa que
todas las acciones de la partida sean esperas ni que reducir HOLD siempre
acelere la solución. El valor predeterminado es 40.
Véanse `Arc3EchoV57.choose` en [agent.py](../echo_arc/agent.py) y
[el observador del consumo real](../echo_arc/consumer_observe.py).

La regla gana +1 en mundo v2/semilla 18 y +3 en v3/28031. Ninguna partida
pierde niveles. La suma de score gana 11,269316, pero cinco casos empeoran:

| Caso local | Mundo/semilla | Score base → candidato | Consecuencia observable |
|---|---|---|---|
| 2 | v3/11 | 8,636326 → 3,329727 | Acciones del segundo nivel: 24 → 490 |
| 4 | v3/19 | 5,318963 → 4,327734 | Acciones por nivel: [24,100,185,120,33] → [24,105,238,136,38] |
| 5 | v3/28 | 9,195898 → 8,420545 | Tercer/cuarto nivel: 285/63 → 428/244 |
| 6 | v3/36 | 22,046985 → 18,933309 | Segundo nivel: 20 → 81, aunque el quinto mejora |
| 9 | v3/28027 | 4,278598 → 4,208769 | Primer/segundo nivel: 52/457 → 150/738 |

El score se recalculó desde las acciones de cada nivel:

\[
S=100\frac{\sum_{i=1}^{L}i\,\min(b_i/a_i,1)^2}{\sum_{i=1}^{L}i},
\]

donde un nivel no resuelto aporta cero, `b_i` es su referencia y `a_i` sus
acciones. Por eso una suma menor de acciones o una ganancia agregada de
score no sustituye la conservación por partida. Las pérdidas son muy
superiores a `1e-10`; no son ruido de redondeo. No se halló una discrepancia
aritmética del juez. La exigencia científica puede ser difícil, pero bajarla
tras ver los resultados cambiaría la pregunta del experimento.

La comparación determinista identifica el efecto del **parche completo**.
No identifica por sí sola qué consumo concreto causó cada pérdida. El daño
puede depender de interacciones posteriores. Un contrafactual de una sola
intervención exigiría reproducir el prefijo y simular la alternativa,
contabilizando ambas ejecuciones.

## Fallos de diseño del investigador identificados

**1. El brazo LLM no usa el reparador M23.** En
[s6b23_search.py](../echo_arc/s6b23_search.py), `from_bytes` separa el
selector M23 de `model_request`. En las 36 peticiones N7/N14,
`target_id=None`, fase `model`, sin un compromiso de conservar HOLD y reparar
las condiciones de un padre. Las funciones `parents`, `repairs` e
`inactive` no controlan esas propuestas. Dar feedback al modelo no equivale
a ejecutar ese algoritmo. B23-R4 siguió su contrato: es una limitación de
la condición experimental, no una caída del servicio.

**2. La gramática exige forma válida, pero admite reiteración e inactividad.**
La gramática R4 permite todo el lenguaje declarado. El runner detecta el
duplicado después de gastar la llamada y la plaza. No tiene un filtro de
aplicabilidad para N7/N14. Esto preservó una medición honesta de ese diseño,
pero desperdició 28 de las 36 oportunidades entre repetición e inactividad.
En B24 los descartes, compilación de restricciones y selección deben tener
coste explícito; excluir un duplicado antes de inferir no autoriza llamadas
gratis ni garantiza que lo restante mejore.

**3. La memoria guarda los resultados, pero recupera mal la evidencia.**
Las 36 reconstrucciones confirman que se enviaron todos los efectos por
partida de la historia propia, incluidos indicadores exactos de pérdidas.
No faltó el historial completo de resultados. Los detalles de consumos, en
cambio, proceden exclusivamente del último intento medido. En N7, después
de descubrir +4, las peticiones 8, 10, 11, 16 y 17 ya no contenían ningún
detalle de consumos, porque un intento posterior inactivo había reemplazado
el foco. El resultado anterior permanece como fila, sin su dossier de
contextos. Hace falta recuperar la evidencia del padre elegido.

**4. La selección de extremos puede ocultar el rango numérico pertinente.**
`read_summary(..., 2)` recorre las features variables alfabéticamente y
trunca la lista después de recoger extremos. En la petición N14/13, tras
la regla de +4, `goal_evidence` ocupa las dos primeras posiciones. Se
resumen dos pérdidas y una ganancia, seis contextos de 43 disponibles:

| Caso | `world_events` completo → mostrado | `level` completo → mostrado |
|---|---|---|
| 2, pérdida | 18–196 → 18–20 | 0–4 → 0–1 |
| 6, pérdida | 1–131 → 14–32 | 0–4 → 0–1 |
| 10, ganancia | 5–91 → 5–11 | 0–4 → 0–1 |

Los niveles aquí son valores de la feature interna, no el total completado.
Las omisiones se declaraban mediante conteos; esa transparencia no repone la
información que el modelo necesita para seleccionar umbrales. Los otros tres
casos con pérdidas solo aparecen en la tabla de efectos. B24 conservará
rangos completos y evidencia de todos los casos afectados del padre, con
una selección de ejemplos por cobertura. Un rango tampoco describe todas
las correlaciones entre features: se mantendrán vectores reales enlazados.

**5. El prompt omitió la semántica del control y del score.** Los bytes
enviados contienen átomos, resultados, política y columnas, pero no una
explicación de dónde se consume HOLD, su valor predeterminado, su diferencia
con una espera ya iniciada ni la fórmula del score. La instrucción de sistema
solo pide JSON. El prompt B13 sí tenía una descripción verbal de HOLD; el
constructor nuevo no la incorporó. Corregirlo es una intervención medible;
no podemos cuantificar aún cuánto explica del fracaso.

## Capacidad disponible y límites de la conclusión

La proyección retrospectiva del control humano `human-00` de B20 sobre las
14 identidades de B23 reproduce **61 → 67**, sin pérdidas de niveles ni
score. Acciones, frames, acciones por nivel, score y niveles de su base
histórica coinciden exactamente con B23. Su propuesta es legal en la gramática
actual. En las 160 partidas amplias ya había conseguido 740 → 746 sin
pérdidas. Es evidencia histórica de capacidad expresiva, no descubrimiento
autónomo ni transferencia nueva. El script registra hashes y resultados;
la solución del control queda excluida de las entradas del investigador B24.

La base completa de este micro suma 61 de 70 niveles posibles. B23-R3 ya
había encontrado +9 con pérdidas; B23-R4 encontró +4 con pérdidas. El reto
local inmediato consiste en conservar eficiencia mientras se ganan niveles.
No hay evidencia de que 32B, más unidades asociativas o más instancias resuelvan
por sí solos ese problema. Si la búsqueda corregida se agota, habrá que medir
la cobertura real del lenguaje y la información observada antes de ampliarlos.

No hubo desbordamiento de contexto: entradas de 3.223–5.026 tokens para N14
y 3.223–5.975 para N7, bajo el límite de 8.192. Las salidas ocuparon 64–78
tokens frente a un máximo de 768. No aparecieron errores de transporte,
parseo, memoria GPU, replay ni puntuación en las evidencias verificadas.
Estos datos refutan atribuir este cierre a un corte técnico observado; no
demuestran que la cuantización o el muestreo carezcan de efectos.

El 14B tardó 350,7 segundos acumulados en sus 18 procesos de inferencia;
el 7B, 186,6. Estos tiempos incluyen la ejecución del CLI y no todo el coste
de tokenización, preparación, simulación y auditoría del notebook. Las dos
T4 no aceleran automáticamente las partidas Python. Una semilla, dos modelos
cuantizados y una interfaz común insuficiente no permiten concluir que 7B
sea generalmente superior ni que 14B sea incapaz de razonar.

## Corrección integrada en B24 y expectativa

El plan conserva un investigador, tres independientes y tres cooperativos.
Todos los brazos B24 reciben el mismo control de búsqueda: semántica explícita,
menús de propuestas activas y nuevas, selección de un padre, reparación de
guarda a duración fija, archivo de ramas y evidencia recuperada por objetivo.
Se añaden una referencia R4 y un control del sintetizador sin LLM. Así se
pueden medir corrección, aporte del neocórtex y cooperación por separado.

La hipótesis es que aumentará el número de hipótesis útiles medidas dentro
del presupuesto y que una reparación podrá conservar la ganancia y reducir
las pérdidas. Encontrar un pase todavía es una predicción, no un resultado.
Más investigadores solo ayudarán si exploran ramas complementarias y usan
recibos compartidos; también podrían copiarse y multiplicar el mismo sesgo.

El marco de [síntesis guiada por contraejemplos de Solar-Lezama](https://people.csail.mit.edu/asolar/SynthesisCourse2020/Lecture10.htm)
motiva incorporar fallos a la búsqueda. Aquí el verificador es una simulación
finita: no produce una prueba universal, y solaparse con contextos de pérdida
no basta para descartar toda una familia. [Reflexion](https://arxiv.org/abs/2303.11366)
apoya estudiar recuperación de feedback entre intentos sin modificar pesos;
no certifica la eficacia de este diseño en ECHO.

Para acreditar un nivel superior hará falta que la mejora sobreviva a
desarrollo amplio, a casos reservados no utilizados para orientar reparaciones
y a la confirmación desde SEMILLA, piloto, campaña y examen B1–B5. Para ampliar
capacidades más allá de ajustar esperas, las hipótesis de representación de
objetos, composición y planificación requieren sus propios bancos y controles.

Reproducción de esta autopsia desde la raíz local de ECHO:

```bash
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python lab/seed/s6b23r4-forensics-20261008/analyze.py
```

Solo escribe el análisis y CSV en su directorio. Los archivos originales de
B23 y su contrato permanecen congelados.
