# H1/H3 · segundo examen reservado S5-F2

2026-09-27. Contrato previo a abrir **17000–17059**. El primer examen
S5-F se interrumpió por `KeyError: random`: faltaba el adaptador del control
en la fábrica privada. Se conserva entero, PENDIENTE por ejecución incompleta.
No se seleccionan agentes ni parámetros usando sus resultados parciales.

Se mantienen las 20 fuentes congeladas de S5-F, sus tres agentes v5.7/v5.8/azar,
versiones 2/3, repeticiones 0/1/2, 2000 decisiones y cuatro trabajadores.
Son 1080 partidas y 1800 niveles por agente, más 120 replays independientes
de v5.8 rep 0. Se repiten exactamente los criterios F1–F6 del
[contrato original](ECHO45-H1-H3-EXAM-DESIGN.md), incluidos la puntuación y
los contadores históricos. No hay LLM ni observador en el examen.

Única corrección operativa: cada proceso trabajador registra `arc3gym._Random`,
adaptador ya existente de `RandomAgent`, en la fábrica privada de
`temporal_runner`; el registro global del runner y las fuentes del actor siguen
intactos. Se prueba antes en entrenamiento para los tres agentes. Se congela
este contrato y el nuevo evaluador, además de verificar el freeze anterior.
No se reutiliza ni sobrescribe ninguna partida de 16000–16059. La cohorte
17000–17059 es nueva; si este examen falla, se publica ROJO o PENDIENTE.

Se publican familia, repetición, regresiones individuales y resultados F1–F6.
S6 permanece ROJO hasta superar su propio contrato de cuatro brazos.
