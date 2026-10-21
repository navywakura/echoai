# S6-B1 · corregir el protocolo de propuestas, sin rebajar la prueba

2026-09-27. Continuación de la orden de Nav de hacer S6-B. B0 conserva su
campaña: 30/30 por brazo, todas V1. Las respuestas quedaron cortadas cerca de
400 tokens y contienen también operadores sin comillas, nombres incorrectos
y condiciones no permitidas. No se aceptan ni reparan a posteriori.

Se conserva la base v5.7, DSL, V1–V4, A/B, seis rondas de cinco propuestas por
brazo, modelo Qwen2.5-Coder-7B-Instruct y criterios B1–B5 del contrato B0.
No se cambia el agente para obtener un verde. Esta iteración comprueba si una
petición de formato comprensible permite probar estrategias útiles.

Cambios fijados antes de la primera llamada de B1:

- ejemplos **válidos** de JSON, operadores entre comillas y nombres literales;
- pedir como máximo tres parámetros por sección, una sola regla y una sola
  condición; el validador conserva el límite de ocho reglas de B0;
- máximo **600 tokens**, sin truncar el prompt ni reparar respuestas incompletas;
- dos llamadas genéricas de calibración, sin tareas ni selección por utilidad:
  ambas deben producir JSON válido. Se guardan aparte, no cuentan en los brazos
  ni se incorporan al agente; se informa el coste de las 62 llamadas totales.
  Si falla la calibración, no se inicia la campaña y no se llama verde;
- examen distinto: **9000–9059**, versiones 2 y 3, reps 0–2, 2000 acciones.
  Nunca usar el examen 8000–8059 de B0 para elegir peticiones o estrategias.

El modelo no recibe los resultados del examen B0, S5-E ni juegos oficiales.
Se publica también el rechazo de propuestas válidas y si los dos modos de
pedir realmente difieren. Fuentes originales de B0 intactas; adaptación en
`seed/game_selfimprove_b1.py`, perfiles y resultados en carpetas nuevas.

**Verde B1 = mismos B1 ∧ B2 ∧ B3 ∧ B4 ∧ B5**, medidos en el examen nuevo.
No se cambia el verde histórico de S6-A o B0. Un eventual verde solo demuestra
control adaptativo de los mecanismos existentes; no creación de algoritmos,
inteligencia general ni cumplimiento de R3 en los juegos oficiales de examen.
