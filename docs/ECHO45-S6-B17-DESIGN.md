# S6-B17 — consumos temporales y síntesis acotada de guardas

Condición privada nueva, 4 de octubre de 2026. Este contrato congela un
microensayo de desarrollo A y su auditoría independiente. No autoriza el inicio
automático del piloto, la campaña ni el examen bajo un protocolo todavía por
definir. S6 conserva su estado pendiente y sus criterios B1–B5.

B16 cerró con 24 propuestas y ninguna mejora válida desde la base de 378
niveles. Sus propuestas HOLD contenían ganancias locales de cinco niveles
con pérdidas de siete a nueve en otras partidas. El controlador seguía
refinando la raíz aunque un descendiente redujera pérdidas; una pausa por
familia podía cortar la reparación. Las condiciones propuestas eran amplias.
El punto de primera divergencia de acciones tampoco era necesariamente el
punto en que se había leído el control.

El análisis retrospectivo ordenó 485 guardas y situó una solución ya conocida
por PROBE2 en el puesto cinco. Ese análisis motivó el diseño y NO constituye
descubrimiento autónomo ni confirmación independiente: los desarrolladores
conocen resultados en A. El runtime no lee PROBE2, sus ganadores ni el ranking
retrospectivo. Empieza con la política B14 de 378 niveles y su recibo original.
Los intentos fallidos B16 usados para cualificar el formato nunca se cargan
como historial de los brazos del micro.

Se implementan tres cambios concretos:

1. El observador existente registra cada consumo real de control, su valor,
   features antes de decidir, índice de decisión y consecuencia inmediata.
   Los índices se alinean con las acciones, incluidos los resets del runner.
   La suma debe reproducir exactamente el contador de consumos anterior.
   Un comparador empareja la primera intervención distinta de cada partida
   dentro del prefijo común de acciones y comunica su demora hasta la primera
   divergencia y los resultados finales. Es una asociación temporal, no una
   atribución causal exclusiva. Se conservan todos los consumos en caché.
   El prompt resume como máximo dos enlaces: una pérdida y una ganancia.
2. El sintetizador enumera las guardas legales del lenguaje existente, con
   aplicabilidad a los casos seleccionados y exclusión de propuestas repetidas
   o certificadas equivalentes. No amplía primitivas, umbrales ni features.
   En reparación mantiene el operador y valor del mejor descendiente. Ordena
   por: mayor cobertura de partidas con ganancia de niveles; menor número de
   lecturas alcanzadas en partidas con pérdidas observadas en el linaje; menos
   condiciones; orden canónico. Conserva ocho candidatos. Las pérdidas del
   linaje no se olvidan al mejorar un descendiente. Una lectura de una partida
   perdedora no queda prohibida: ese indicador es una heurística de ordenación.
   Las simulaciones completas siguen decidiendo la utilidad.
3. El controlador admite descendientes como nuevos objetivos. Prioriza mayor
   ganancia local, menos niveles perdidos, menos partidas perdedoras, menos
   score perdido y, en empate, el intento anterior. Cada raíz tiene un máximo
   de siete descendientes, incluidos los fallos de sintaxis. Una oportunidad
   local puede continuar pese a su agregado negativo mientras tenga ese
   presupuesto. Un pase A cierra el linaje; nunca equivale a aceptación en B.

El micro mantiene fija la base durante sus ocho rondas. Cada intento válido
añade un parche a esa base y se mide por separado. Encontrar una mejora no
permite detener selectivamente los otros brazos ni sustituir los resultados
anteriores. Los tres brazos son:

| Brazo | Generación y selección | Máximo de propuestas | Llamadas LLM |
| --- | --- | ---: | ---: |
| `b16` | Controlador y prompt B16 congelados | 8 | 8 |
| `synth` | Nuevo controlador; elige la primera guarda del ranking sin LLM | 8 | 0 |
| `hybrid` | Primer mecanismo propuesto con la misma petición B16; después, nuevo controlador y elección LLM entre ocho guardas al refinar | 8 | 8 |

Cuando `synth` abre un mecanismo nuevo, toma el mínimo valor legal y la guarda
con mayor número de lecturas observadas, desempatando por simplicidad y orden
canónico. Cuando `hybrid` no tiene objetivo parcial, el modelo propone un
mecanismo en la gramática del operador seleccionado. Agotar las guardas para
un valor produce abstención; no cambia silenciosamente de valor. Las
abstenciones o errores V1 consumen su oportunidad y no se remuestrean.

Las semillas de llamada son 770101 + índice de ronda × 1000. `b16` e `hybrid`
tienen la misma semilla en cada ronda; la primera petición es idéntica. Solo
hay una secuencia por brazo, ocho rondas. Esto prueba funcionamiento y
capacidad en A, no significación estadística ni generalización.

Todos usan las mismas 80 A: versiones 2 y 3, semillas 0–39, repetición cero,
2000 acciones máximas por partida. Se rechaza cualquier partida fuera de A
antes de invocar el entorno. No se mide B ni el examen. No se pasan
identificadores de partidas, coordenadas ocultas ni datos protegidos al LLM.
El conjunto completo de 80 resultados decide V3, aunque el prompt resuma.

| Presupuesto | Tope |
| --- | ---: |
| Propuestas por brazo | 8 |
| Juegos lógicos por propuesta válida | 80 + 80 de replay |
| Juegos lógicos de candidatos por brazo | 1280 |
| Base compartida + replay | 160 |
| Ejecución primaria máxima | 4000 |
| Auditoría independiente: base + 24 candidatos | 2000 |
| Presupuesto físico total | 6000 |
| Llamadas totales al modelo | 16 |
| Workers de juegos / hilos de inferencia | 4 / 4 |

La caché primaria puede reutilizar políticas idénticas de distintos brazos,
pero cada propuesta medida consume 160 juegos lógicos de su techo. Se publican
costes físicos y lógicos por separado. El ahorro de caché por orden de brazo
no se presenta como ventaja de velocidad del agente. `synth` no convierte
sus llamadas no gastadas en más evaluaciones ni más oportunidades.

Se conserva Qwen3-4B-Instruct-2507 Q4_K_M local en CPU, pesos, binarios y
parámetros de B16: contexto 4096, entrada máxima 3072, salida máxima 160,
temperatura 0.6, top-k 40, top-p 0.95 y timeout por llamada ya congelado.
La tokenización es la nativa. No se trunca el objetivo para hacer caber un
prompt: un desbordamiento detiene el instrumento. No hay gasto de API/GPU.

El pase A exige al menos 380 niveles desde 378, ninguna pérdida individual
de niveles o score según el verificador existente y replay completo idéntico.
Se etiqueta `A_ONLY_PASS`. Las mejoras con pérdidas siguen rechazadas incluso
si el total supera 383. Las propuestas no se integran en la base del micro.

La auditoría arranca automáticamente al completar los 24 intentos, también
si el resultado es negativo. Usa otro proceso y caché separada; ejecuta la
base y cada candidato válido en las 80 A. Reconstruye los prompts, respuestas,
tokenización, linajes y veredictos, comparándolos íntegramente. No regenera
respuestas LLM. Una diferencia de replay, paridad, origen, presupuesto o
custodia detiene el instrumento y conserva los artefactos. No se contabiliza
como evidencia negativa sobre el agente.

Antes de la primera inferencia, la base y su replay deben conservar 378
niveles y todas las trayectorias anteriores, retirando únicamente el campo
nuevo de telemetría. Su digest antiguo debe seguir siendo
`4458a4c2e5f4d8ac6c46547fcbc62785e0aca93bd0bdecb6d23d7456d63c2d2c`.
Los diarios efímeros se borran solo después de guardar atómicamente el
resultado completo, incluida la nueva cronología, en la caché verificable.
Se mantiene la mini terminal de decisiones observables ya existente.

Un pase del híbrido y auditoría válida habilitan diseñar el siguiente piloto.
Un empate con el sintetizador demostraría utilidad de la búsqueda acotada,
pero no una aportación adicional del LLM. Se informarán primera oportunidad
exitosa, propuestas, llamadas, aciertos A sin pérdidas, acciones modificadas,
coste físico/lógico, pérdidas y fallos del instrumento. El piloto posterior
deberá congelar qué herramientas comparten FIJO y ECHO, recomenzar sin estos
intentos y demostrar conservación protegida. Examen y B1–B5 siguen pendientes.

Preparación reproducible, con el Python 3.12 congelado:

```sh
python -m unittest tests.test_s6b17_timeline tests.test_s6b17_synthesis tests.test_s6b17_runner -v
python -m seed.s6b17_qualification
python -m seed.s6b17 prepare
python -m seed.s6b17 follow
```

Las fuentes propias y heredadas se archivan y congelan antes de ejecutar.
La cualificación usa tests, registros de desarrollo existentes y fixtures
sintéticos declarados; genera cero partidas nuevas y cero respuestas LLM.
Las estimaciones de tiempo se documentan fuera del contrato.
