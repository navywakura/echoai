# S6-B6 · aplicabilidad y evidencia de decisiones

2026-09-28. Nueva condición de piloto; B5 permanece cerrado sin promoción.
Hipótesis: las propuestas B5 activaban guardas en puntos que no consumían
el parámetro o proponían límites incapaces de cambiar su valor. El registro
de base A permite distinguir esos casos sin consultar soluciones humanas.

Los dos brazos reciben la misma gramática B5, límites y explicación literal
de cuándo consume cada operador el agente. FIJO recibe tres fallos y petición
genérica. ECHO recupera casi aciertos y puntos de consumo observados del diario
de la política SEMILLA, priorizando primero niveles y después número de
ocasiones de establecer espera. No recibe el ganador del control manual.
La selección es un algoritmo humano explícito: no se atribuye su programación
al aprendizaje del agente. Se evalúa si mejora el resultado de pedir ayuda.

Tres semillas de muestreo 613001/613017/613029; dos propuestas por brazo y
semilla, prompts fijados antes, 12 propuestas +2 calibraciones. Modelo,
revisión FP16 y configuración de inferencia iguales a B5. Un trabajo privado
Kaggle de hasta 900 segundos, solo cuota gratuita y pago desactivado. Fallos
de inferencia se conservan, sin duplicar envío automáticamente.

A conserva versiones 2/3, semillas 0–19, 2000 decisiones. B usa semillas
nuevas 24320–24339; nunca alimenta prompts. V1–V4 sin cambios: sintaxis segura,
replay completo, +2 niveles A sin regresión individual A y ninguna regresión
individual B. Cada pareja empieza vacía y aplica sus dos propuestas en orden.
Promoción solo si ECHO acepta ≥1 y su suma A supera estrictamente FIJO.

Este piloto no abre examen ni declara S6 verde. Si promueve, se preregistrará
continuación adaptativa y examen nuevo antes de ejecutarlos. El cierre S6
conserva B1–B5 completos y los cuatro brazos, incluido SIN FILTRO acumulativo.
Si no promueve, se publica el negativo sin gastar otra campaña.
