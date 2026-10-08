# S6-B21-A — cobertura conjunta y reparación por contraejemplos

Contrato privado, 6 de octubre de 2026. Implementación de la primera etapa
recomendada en `B21-investigacion-20261006.pdf`, recibido del propietario.
La ejecución se autoriza después del cierre, replay independiente y revisión
aritmética válidos de B20. El hash de este documento se congela antes de jugar.

La pregunta es si distribuir explícitamente las oportunidades entre duración
y condiciones permite encontrar una mejora que B20 no descubrió en sus 18
intentos. Se cambia el investigador. El actor, las observaciones instantáneas,
la base aceptada B14 y el juez de conservación permanecen congelados.
Las observaciones nuevas son generadas por simulaciones completas. Los frames
antiguos sirven para orientar propuestas; no puntúan trayectorias alternativas.

**Comparación y presupuesto.** Siete recorridos: B20 determinista una vez,
muestreo aleatorio tres veces y agenda balanceada tres veces. Las semillas
emparejadas son 821101, 821117 y 821129. El orden de ejecución se sortea con
821000 y se guarda en `manifest.json`. Cada recorrido tiene como máximo 18
plazas y se detiene en su primer pase. Todas parten de la misma política.
Se cuentan también propuestas repetidas, inactivas o sin candidato legal.
Nunca se regala otra plaza para sustituirlas.

El control B20 ejecuta `s6b20_search.request('new', ...)` sin cambios, con
historia aceptada B14 más sus propios intentos. Esta condición A no llama al
neocórtex: cero tokens y cero coste de API. No puede acreditar por sí misma
la contribución del LLM ni descubrimiento desde SEMILLA.

El lenguaje común usa un parche HOLD, duración en
`0,1,2,4,8,12,16,20,24,32` y conjunciones de una a tres condiciones sobre
features distintas. Conserva exactamente los átomos de la gramática B20.
No incorpora IDs, coordenadas privadas, reglas ganadoras ni condiciones
privilegiadas tomadas de controles humanos.

El muestreador general elige uniformemente longitud 1/2/3, subconjunto de
features y átomo legal por feature. Toda guarda legal tiene soporte, aunque
sea inactiva en las observaciones actuales. No es muestreo uniforme entre
todas las sintaxis: se publican esos tres niveles de la distribución.

El muestreador de diversidad usa la biblioteca B20 ampliada (máximo 2.048
representantes) más 64 muestras generales. Reagrupa sus firmas de verdad
sobre lecturas HOLD de la base y de los candidatos del propio recorrido.
En la agenda balanceada prioriza firmas menos expuestas y miembros todavía
no usados. En el control aleatorio elige uniformemente firma y miembro sin
usar ganancias o pérdidas. Ambos reciben sus nuevas observaciones; el control
aleatorio es una ablación de agenda y reparación, no una búsqueda ciega sin
memoria. La rotación de representantes B20 depende de guardas antes medidas.
Dos firmas iguales no prueban equivalencia sobre estados futuros.

La agenda balanceada reserva las primeras diez plazas a una permutación
sembrada de las diez duraciones; cinco guardas generales y cinco diversas,
alternando con inicio sembrado. Si encuentra un pase antes, deja congelado
ese primer candidato y no completa artificialmente las diez plazas.
Las ocho restantes alternan cuatro reparaciones y cuatro exploraciones.
Las reparaciones son guarda/duración/guarda/duración, con objetivos
reparar-pérdida/aumentar-ganancia/aumentar-ganancia/reparar-pérdida.

El archivo investigador conserva hasta 32 entradas: propuesta, política,
ganancia, pérdidas por caso, linaje, consumo y trayectoria. En este micro
hay a lo sumo 18, de modo que ninguna hipótesis rechazada se pierde por cupo.
La selección alterna ramas de ganancia, distingue +1 conservador de ganancia
≥2 con pérdidas y limita cada padre a dos hijos. Si el objetivo preferido no
existe, usa otra rama con ganancia bruta positiva; si no hay padre o reparación
inédita legal, consume la plaza como exploración general declarada.

Cambiar duración mantiene la guarda y considera valores menores y mayores.
Cambiar guarda mantiene la duración y no exige conservar el anclaje del padre:
compara la biblioteca más 128 muestras generales. Las propuestas repetidas
del archivo no ocupan espacio en esa lista de reparación. Esto es filtrado
de candidatos antes de simular, no una medición gratuita.
El ranking prioriza cobertura estimada ≥2, menos contextos asociados a pérdidas,
más cobertura de ganancia y desempate sembrado. Las pérdidas se asocian solo a
la misma duración y linaje; la ganancia se estima con lecturas cambiadas del
padre. La atribución sigue siendo incierta. Solo la simulación decide V3.

**Puertas.** El cribado tiene las mismas doce partidas de B20: v2/18;
v3/2,11,13,19,28,36,37; v3/28026,28027,28031,28039. Dos mil acciones por caso.
Se usa el mismo cálculo de score y tolerancia 1e-10. El pase exige ganancia
total ≥2 y cero casos con pérdida de nivel o score. Cada resultado necesita
replay completo y después otra ejecución en proceso independiente y caché
separada. Discrepancias bloquean el instrumento, sin contarse como fracaso
del candidato. Se exige paridad con el digest basal B20 antes de proponer.

Tras el micro auditado, si hay un candidato balanceado elegible, se miden
todos los primeros ganadores (también controles) en las 160 partidas de
desarrollo amplio de B20. Se repiten el mismo umbral y la auditoría. Si sigue
existiendo un balanceado elegible, los supervivientes se congelan y miden en
80 partidas protegidas: versiones 2 y 3, semillas 64000–64039, réplica 0 y
2.000 acciones. Allí se exige cero pérdidas individuales; no se exige ganancia
nueva ≥2. La reserva no produce feedback, diarios de observación ni selección
de sustitutos. Un permiso enlaza por hash cada política y la cualificación.

El cribado y desarrollo amplio ya orientaron el diseño y se etiquetan como
diagnóstico retrospectivo. `partition-review.json` inventaría los perfiles
históricos revisados para detectar exposición de la nueva reserva. Una
ausencia de coincidencias en ese inventario no prueba ausencia universal de
exposición fuera del laboratorio registrado.

Cuatro procesos locales, Python 3.12.13, numpy 2.3.2, arcengine 0.9.3;
240 segundos máximos por partida. El techo es 16.000 partidas físicas,
incluidas las programadas que fallen. La cota conservadora del informe,
repitiendo bases por recorrido, es 14.868. Compartiendo una base por fase
amplia, la implementación necesita como máximo 10.548:
4.788 de cribado/auditoría, 3.840 de cualificación y 1.920 de conservación.
Si políticas exactas se repiten dentro de una caché, se reutiliza el registro
con checksum, conservando su plaza lógica. La auditoría nunca lee la caché
de la ejecución original. No se afirma igualdad de segundos de CPU entre
buscadores: se igualan oportunidades y límites de simulación, y se registran
por separado tiempos reales de búsqueda y partidas.

**Superficie de datos y trazabilidad.** El buscador recibe exclusivamente
JSON canónico: política, observaciones basales, historial aceptado B14,
historial propio, tipo de brazo, semilla e índice. Los bytes exactos se guardan
comprimidos sin pérdida en `investigator-inputs/<sha256>.json.gz`; la auditoría
los reconstruye y compara antes de volver a proponer. Cada plaza registra
solicitud, lista corta, respuesta determinista, propuesta, padre, hashes de
política/trayectoria, resultado y costes. Los hashes de consumo se derivan del
archivo de evidencias. Los resúmenes escalares iguales no se llaman reglas
iguales ni conductas iguales.

Se ejecuta desde una copia mínima con fuentes enumeradas por hash. Excluye
documentos, tests, PDF, PROBE y el módulo de controles humanos B20. Conserva
dependencias históricas necesarias para importar el actor y evaluador; esto
es aislamiento de datos de investigación, no un sandbox adversarial de Python.
El buscador determinista no tiene herramientas de archivos, red ni modelos;
las pruebas verifican que su llamada usa únicamente los bytes recibidos.
El supervisor sí puede leer recibos para autorizar fases; no se los entrega
como experiencia al investigador. Todos los ficheros congelados B18–B20
deben conservar sus bytes. Modificarlos bloquea la cola.

Las decisiones de desarrollo se envían al diario existente
`live/journal.jsonl`, compatible con `observe.py`. Son solicitudes, acciones,
hipótesis instrumentadas y resultados medidos; no una transcripción mental.
No se crea un segundo bus ni se instrumenta la reserva. La reanudación usa
registros completos y checksums. Una partida interrumpida con diario parcial
requiere recuperación explícita; no se oculta su coste.

Se informará, por recorrido, número de intentos, duraciones expuestas, padres,
propuestas/políticas/firmas/trayectorias distintas, ganancias, pérdidas,
coste y primer pase. Tres semillas permiten un diagnóstico pequeño: un éxito
aislado no establece superioridad estadística general frente al aleatorio.
Si todos fallan, se informa el espacio probado; no se declara agotado el DSL.

Una cualificación verde habilita diseñar la ablación del neocórtex. El
descubrimiento autónomo desde SEMILLA, piloto, campaña y examen B1–B5 siguen
siendo requisitos separados de S6. `s6_green` permanece falso.

La investigación restante queda separada para poder atribuir efectos: T,
historia temporal del investigador; C, crédito diferido; R, replay con
restauración comprobada; N, una llamada frente a tres sin y con feedback;
P, nuevas features del actor si la evidencia las justifica. En A se aplica
el archivo de hipótesis y el replay completo desde el inicio. No se afirma
haber implementado e-prop, restauración parcial de mundos o crítica del LLM.
El decaimiento entero y la semántica de RESET del PDF son requisitos de las
etapas temporales posteriores, no cambios encubiertos del actor B21-A.

Implementación: `echo_arc/s6b21_search.py`, `echo_arc/s6b21_archive.py`,
`seed/s6b21.py`, `seed/s6b21_review.py`, `seed/s6b21_build.py`.
Pruebas: `tests/test_s6b21.py`, más regresión B20/B18.
