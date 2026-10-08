# E4-OTHER-1 — representación observable de una contraparte, v1

2026-09-22. Contrato previo al examen; sin modificar las 93 fuentes MAINTAIN.

## Pregunta y alcance

¿Un agente aprende regularidades de **otro** individuo, separadas de las
propias, usando únicamente observaciones públicas de su contexto y sus
acciones ejecutadas? ¿Se abstiene cuando faltan contexto, identidad o ejecución?

Dos `Agent` nativos, cada uno con CAM/T/Q privadas, aprenden por recompensa
en una tarea discreta de tres contextos y tres acciones. El entorno individual
tiene una preferencia privada por contexto; no se entrega al predictor.
La preferencia es una regla del mundo, no una personalidad ni conciencia.
Las acciones las elige la Q aprendida y pasan por el gate original, no un guion.

OTHER evalúa **predicción observacional**, no control causal del otro,
lectura de intenciones, teoría de la mente completa ni conciencia subjetiva.
No hay aún cooperación ni beneficio instrumental por comunicar: eso pertenece
a INTERACTION. Este banco usa la tarea discreta del núcleo, no el cuerpo
térmico de MAINTAIN. No hereda certificados de supervivencia; integrar ambos
perfiles queda para INTEGRATE. El corte nuevo no altera MAINTAIN ni DREAM.

## A — representación y separación

Cada individuo recibe solamente su celda y recompensa privadas. Antes del
encuentro aprende durante 240 acciones nativas (Q inicial cero); las memorias
no se comparten ni se copian. Después se encuentran y siguen eligiendo con
Q nativa greedy, que continúa actualizándose. El sensor público muestra
la identidad local estable y, cuando hay visibilidad, el contexto del otro.
Tras la ejecución muestra su acción aplicada, nunca su propuesta, Q, T,
recompensa privada ni regla de preferencia.

Todo se representa con `navi10_wsp.pack`, **16 B**: YO/OTRO como sujeto;
OBSERVAR para contexto y UNIR/TEMER/OBSERVAR para acción; AQUI para contexto,
OTRO para acción; AHORA; E=0 (no es un sentimiento atribuido); dominio 9 y
generador 8 ya usados por HOST, style 0/1 para contexto/acción, slot como
identificador local de seguimiento (0 propio, 1/2 ajeno), seq como contexto
0..2 o 255 desconocido. Se valida forma canónica completa. No nuevo layout,
bus, transporte de prosa ni campo emocional usado como bolsa de datos.

Los identificadores son proporcionados por el sensor de este simulador;
no se ha aprendido reconocimiento visual ni autenticación adversaria.
Un identificador nuevo empieza desconocido, aunque la conducta coincida.

## B — memoria y predicción

El módulo recibe exclusivamente la CAM y T del **propio** agente; no un
objeto contraparte, entorno, log ni Q ajena. Registra observaciones mediante
el asignador CAM original y aprende en la **misma T**, sin tabla predictiva
paralela: `(contexto público del sujeto, acción propia aplicada) → acción
pública del sujeto`. Son regularidades condicionales, no atribución causal.
Los contextos tienen WSP distintos de las celdas nativas; no reemplazan las
filas corporales ni modifican la Q de control.

Antes de que actúe cualquiera se consultan las tres posibles acciones propias.
Tras ambos pasos se evalúa la predicción ya comprometida correspondiente a
la acción propia aplicada, y **solo después** se aprende el resultado.
No hay beneficio por ejecutar primero: los dos entornos son independientes,
no comparten recursos, y la entrega pública ocurre después de ambos.
Se prueba invariancia al orden de ejecución.

Se exige al menos 3 observaciones consistentes y ninguna alternativa en T.
Conflicto implica abstención conservadora, no borrar memoria. Este perfil
no promete reaprender una fila contradicha: la adaptación social posterior
requiere otro examen. Una predicción nunca se escribe como hecho CAM.
Se registran como hechos solo paquetes presentes con extracto del sensor.
CAM llena se cuenta y no se usa el slot 0 como sustituto.

Controles emparejados (misma experiencia privada y mismas acciones):

1. `identity`: filas distintas para cada sujeto.
2. `pooled`: mezcla identidad en claves derivadas, marcadas **sin hecho**;
   conserva contexto y acción propia. Ablación de quién actuó. Sus índices
   privados usan style 2/3 y slot 255; no se aceptan como paquetes del sensor.
3. `self_copy`: predice al otro usando las filas observadas del propio yo;
   reúne las columnas conocidas de ese contexto y exige consenso. No queda
   artificialmente ciego por no haber ejecutado cierta acción propia allí.
4. `no_history`: sin aprendizaje de las filas públicas; no borra Q/CAM/T
   del núcleo ni impide el aprendizaje privado de las acciones.

Las predicciones no intervienen en el selector: debe haber paridad exacta
de acciones y recompensas privadas entre brazos. No se venderá este KPI
como mayor trabajo, supervivencia, confianza interpersonal o coordinación.

## C — ausencia, contradicción y límites

Contexto/identidad ocultos → desconocido. Acción no observada → no aprender;
no confundir silencio con WAIT. Recibos deben casar con contexto e identidad
de la observación previa, y ticks estrictamente crecientes; duplicados,
futuros y datos malformados se rechazan antes de escribir.
Presupuesto de 512 encuentros por vida; una parada impide nuevas observaciones.
La contraparte puede tener veto: solo cuenta la acción efectivamente aplicada.

Se prueban separación de objetos y filas, no interferencia de memorias
privadas, identidad nueva, ocultación, contradicción, saturación CAM,
parada, y predicciones idénticas usando solo paquetes capturados en un
proceso nuevo. Ese replay reconstruye un **observador**, no reanuda el
agente completo ni crea evidencia de nuevas acciones. CONT no se reabre.
El proceso nuevo debe igualar tanto las predicciones comprometidas por el
agente original como el hash del subgrafo público de su CAM/T. No basta con
comparar dos replays entre sí. Las pruebas unitarias incluyen un pronóstico
original manipulado que debe provocar discrepancia.

## Desarrollo y D — cierre preregistrado

Desarrollo con semillas 11, 29 y 47. Seis permutaciones posibles de preferencias
de tres acciones; en el brazo heterogéneo las preferencias del otro se
eligen entre las dos permutaciones que difieren en los tres contextos.
El control de igual preferencia usa la misma permutación en ambos agentes.
No se codifica esta relación en el predictor.

Cada pareja: 240 pasos privados por agente; 192 encuentros con contextos
independientes, visibilidad completa y ambos sentidos de observación.
Primeros 96 encuentros para formar historial público; últimos 96 para
puntuar predicciones comprometidas, manteniendo aprendizaje online.
También se publican resultados de la primera mitad y costes de preparación.

Dos cohortes nuevas: semillas `range(261001,261009)` y
`range(261101,261109)`; ocho parejas heterogéneas y ocho de igual preferencia
por cohorte. Los cuatro brazos se ejecutan en cada una. Cuerpos/preferencias
no son holdouts de leyes nuevas: la novedad son experiencias, parejas y orden.
Las recetas, fuentes y umbrales se guardan antes de ejecutar D.

En **cada cohorte heterogénea**, identity debe:

- acertar al menos 85% de los 1536 objetivos (abstenciones cuentan como fallo);
- tener al menos 95% de precisión entre predicciones emitidas;
- superar a pooled y self_copy por al menos 20 puntos porcentuales del total;
- superar a no_history por al menos 50 puntos del total;
- demostrar que las acciones privadas aciertan su propia tarea >=95% durante
  el encuentro, que son resultado de Q y que los brazos tienen trazas iguales.

En parejas de igual preferencia: identity y self_copy deben alcanzar >=85%
de aciertos; no se exige una ventaja inexistente por diseño. C e invariantes
deben pasar, sin falsos hechos, CAM destruida, LLM o acceso privado del modelo.
No sustituir criterios fallidos por medias entre cohortes. Si D falla,
conservar rojo; cambiar código/umbral exige otra versión y otro examen.

El informe solo declara elegibilidad y `other1_green=false`; auditoría en
proceso nuevo reconstruye resultados y verifica fuentes/custodia antes de
conceder verde. No es certificación de aislamiento de código host malicioso:
se verifica la interfaz, separación y no interferencia de este programa.
Hardware, Discord, web, Hugging Face y METAVERSE-1 quedan fuera de este corte.
