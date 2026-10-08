# S6-B20 — contrato de capacidad y micro factorial

6 de octubre de 2026. Condición privada posterior al rojo auditado B19.
Se congela antes de la primera partida B20. Fuentes anteriores intactas,
modelo y juez conservados. [Motivación](ECHO45-S6-B19-FORENSICS.md) y
[plan general](ECHO45-S6-B20-PLAN.md).

Este contrato implementa la cualificación de la reparación HOLD desde el
programa B14 aceptado de 378 niveles. Su alcance está limitado explícitamente
a ese mecanismo. No evalúa todavía selección libre de operadores desde
SEMILLA. Piloto, campaña y examen requieren después un contrato de cuatro
brazos que demuestre ese descubrimiento completo. Ninguna rama de este runner
puede declarar S6 verde ni abrir el examen.

La biblioteca ampliada enumera las 420.986 conjunciones de una a tres features
distintas sobre los mismos átomos y umbrales que B19, sin anclajes obligatorios.
Para acotar el coste, agrupa por coincidencias en las observaciones propias
completas y conserva un representante por firma; rota representantes ya usados.
Si hubiera más de 2.048 firmas, las ordena por longitud y hash y conserva las
primeras 2.048. El recibo expone sintaxis enumerada, firmas, reducción y eventual
truncamiento. Esta agrupación orienta exploración; no demuestra equivalencia
en trayectorias nuevas ni exhaustividad de la medición. Los controles basales
se construyen con los doce casos, no con tres elegidos.

La escala HOLD es 0,1,2,4,8,12,16,20,24,32. El validador conserva sus límites
originales y el máximo de 32 reglas aceptadas. Cada propuesta lleva un parche.
Las firmas incluyen consumos basales y de candidatos propios, incluidos los
tardíos. La poda formal se limita al certificado existente de igual valor y
misma verdad en todos los consumos reales de un candidato sobre la misma base;
no se reutilizan los certificados de particiones de guardas antiguas. Cambiar
de valor no habilita esa poda. No hay resultados B ni identificadores de caso
dentro de las condiciones ejecutables.

El selector nuevo conserva familias de ganancias observadas por partida,
alternando las menos exploradas. Limita a tres descendientes directos por
objetivo y seis por familia de ganancias. Se informa agotamiento en vez de
reabrir indefinidamente la misma familia. Los dos primeros refinamientos
mantienen el valor y buscan ámbito; el tercero mantiene la guarda y ensaya
el siguiente valor mayor declarado. El ranking separa intervenciones realmente
modificadas y agrupa evidencia negativa por valor y linaje. Usa contextos
distintos, evitando multiplicar castigo por repetir un bucle. La asociación
con ganancias/pérdidas sigue siendo incierta; solo las partidas autorizan
aceptación. No se modifica el actor ni se incorporan features privadas H4.

**Control dirigido de capacidad, CPU local.** Usa solo los doce casos de
desarrollo consumidos por B19, con idéntica base. A partir de la historia
híbrida consumida de B19, genera un plan fijo de doce candidatos de biblioteca
antigua y doce de ampliada con el mismo algoritmo de ranking y presupuesto.
La selección considera las referencias 1, 2 y 9 de forma intercalada; se
completa por hash si faltan propuestas. Se guarda el plan antes de medir.
Es una búsqueda dirigida por investigación humana, sin atribución autónoma.

Añade tres controles humanos de cobertura, separados de la comparación de
bibliotecas: HOLD1 con `pending_effect=0 AND world_events<=16`, y sus variantes
con `level>=1` o `goal_evidence=1`. Ninguno entra en la memoria, prompt o ranking
del posterior micro autónomo. No se entrega al micro el archivo de propuestas
ni las trayectorias de este control. Solo recibe un recibo de habilitación con
hashes. Ese bit de existencia se declara como prerrequisito de ingeniería.

Se miden los 27 candidatos y la base en doce partidas cada uno, con replay.
Se toma el primer ganador +2 sin pérdidas de cada categoría (antigua,
ampliada, control humano) para comprobarlo una sola vez en 160 partidas de
desarrollo, también con replay. Una auditoría en otro proceso y caché repite
todo y exige igualdad completa. Tope: 2.928 partidas físicas; ninguna B.
Si ninguna categoría confirma +2 sin pérdidas en el desarrollo amplio, el
micro no se lanza y se registra un resultado negativo de capacidad acotada.

**Micro factorial privado en Kaggle.** Cuatro condiciones:

| Condición | Inicialización | Refinamiento |
|---|---|---|
| C0 | Determinista | Ranking/selector B19 |
| C1 | La misma inicialización determinista | B20 |
| H0 | LLM | Ranking/selector B19 |
| H1 | La misma propuesta LLM que H0 | B20 |

Todas acceden al mismo generador ampliado, la misma evidencia inicial, valores
y presupuesto de 18 propuestas. Se compara el controlador, no una réplica
exacta de todo B19. El generador y el esquema se reconstruyen sobre la historia
propia de cada brazo; no hay feedback cruzado. C0/C1 se ejecutan una vez cada
uno: repetirlos no produciría nuevas muestras independientes. H0/H1 se comparan
en tres pares con semillas LLM 820101, 820117 y 820129. Total máximo: ocho
recorridos, 144 propuestas y tres llamadas físicas LLM iniciales. Los pares
comparten la respuesta inicial y cuentan su coste en ambos brazos lógicos.
La auditoría reutiliza respuestas registradas, no remuestrea al modelo.

Modelo Qwen3-4B-Instruct-2507 Q4_K_M, hash y CUDA cualificados B18/B19;
máximo 3072 tokens de entrada y 160 de salida por llamada, contexto 4096,
temperatura 0,6. Un prompt excesivo detiene el instrumento; no se trunca
silenciosamente. Hay una sola generación por par; no se atribuye refinamiento
continuo al LLM. CPU: cuatro procesos; Python 3.12.13, numpy 2.3.2,
arcengine 0.9.3; timeout existente de 240 s por partida. No servicios de pago.

Cada recorrido se detiene en su primer candidato con +2 niveles y cero
pérdidas individuales de nivel o score, tolerancia 1e-10. Cribado de doce
casos con replay completo; auditoría reconstruye solicitudes, respuestas,
políticas, filas y veredictos usando caché separada por brazo y fase. Los
candidatos de capacidad y sus historias rechazadas no están disponibles.

Si hay algún H1 ganador y el micro está auditado, el primer ganador de cada
recorrido elegible se congela y mide en 160 casos completos: A histórica
(v2/v3, semillas 0–39), cuarenta B18 consumidas (28020–28039) y cuarenta nuevas
de desarrollo (62000–62019), repetición 0, presupuesto 2000. Exige +2 y cero
pérdidas, replay y auditoría completa. Ningún ganador se sustituye después
de ver esta ampliación. Se informa la tasa de éxito sobre los tres pares,
incluidos los recorridos fallidos; no se presenta un ganador aislado como
ventaja media del modelo.

Solo si sigue habiendo H1 elegible se abre conservación: ochenta partidas
nuevas v2/v3, semillas 63000–63039, repetición 0, presupuesto 2000. Cero pérdidas
individuales, replay y ejecución independiente. No se instrumenta esa reserva,
no se envían sus resultados al buscador y no se vuelve a seleccionar candidato.
Una política que conserve permite preparar piloto; no demuestra por sí sola
superioridad del híbrido ni robustez de todas las semillas. Se conservan todos
los resultados de controles y semillas, incluidos los negativos.

El micro y su cualificación disponen de 16.000 partidas físicas en total,
incluyendo las reservas de ejecución interrumpida, replays y auditorías.
No se cambia ningún límite por resultados parciales. La calibración inicial
de enumeración tardó aproximadamente 1,4 segundos sobre datos B19 ya guardados;
no ejecutó partidas ni seleccionó por resultados nuevos. El control de capacidad
medirá tiempos de juegos para estimar la duración del micro antes de enviarlo.

Una fuente cambiada, caché dañada, replay diferente, timeout o recibo LLM ambiguo
produce BLOCKED_INSTRUMENT. Nunca se cuenta como evidencia de incapacidad.
Los resultados científicos negativos cierran la fase sin abrir su sucesora.
Se guarda cada resultado antes de borrar su diario efímero, manteniendo las
trayectorias diagnósticas completas en caché. El observador existente muestra
veredictos reales de desarrollo. No se instrumentan exámenes históricos.

Los resultados son del banco procedural S6. No son puntuaciones ARC oficiales,
no permiten bajar B1–B5 y no convierten el proyecto completo en verde.
