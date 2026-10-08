# S6-B2 · propuestas con gramática · contrato previo a llamadas

2026-09-27, continuación autorizada de S6-B. B0 conserva sus 60 rechazos V1.
B1 se detuvo **antes de iniciar los brazos**: su calibración dio un JSON válido
y otro con la condición inexistente `max_units`. Se conservan ambas respuestas
y sus fuentes; el resultado de calibración no se interpreta como utilidad.

B2 usa el mismo v5.7, A/B, presupuestos, modelo, temperatura, top-p, 30 llamadas
por brazo, seis rondas y **los mismos criterios de utilidad B1–B5 del contrato
B0**. Se mantiene V1, V2, V3 (dos niveles nuevos sobre el vigente) y V4
(no bajar niveles ni puntuación de B). No se relaja ningún criterio de verde.

La diferencia es sintáctica: una gramática de tokens genera directamente un
JSON válido. El modelo **elige los valores**, una condición observable y un
parámetro que cambia bajo esa condición. No se reparan respuestas ni se
seleccionan estrategias usando el examen.

Alcance reducido y declarado: cuatro parámetros (`HOLD`, `MIN_EVIDENCE`,
`BABBLE`, `WALL_MIN`), todos los enteros de sus límites originales, y una
regla con una condición y un parámetro. Condiciones: booleanos observados,
nivel, número de eventos y estancamiento, con los umbrales enumerados en
`echo_arc/strategy_grammar.py`. No equivale a inventar algoritmos nuevos.

Se preservan dos llamadas de calibración solo de formato, fuera de los brazos
y sin tareas. Deben pasar. Se registran 62 llamadas totales; máximo 600 tokens.
La generación restringida usa el callback oficial
[prefix_allowed_tokens_fn de Transformers](https://huggingface.co/docs/transformers/en/main_classes/text_generation).

Examen **10000–10059**, versiones 2 y 3, reps 0–2, 2000 acciones, después de
congelar estrategias. No se recibe ningún resultado del examen de B0, B1,
S5-E ni de los juegos oficiales. El examen B1 quedó sin abrir.

**B2 verde exige los cinco criterios originales de B0** en estas semillas
nuevas, desarrollo oficial sin regresión e integridad/replay exactos. Se
publicará el resultado aunque sea rojo. El verde de S5-E y el rojo de S6-A
permanecen separados.
