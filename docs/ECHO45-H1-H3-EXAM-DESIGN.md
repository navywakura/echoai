# ECHO-4.5 · S5-F: examen reservado de H1/H3, v5.8

2026-09-27. Contrato fijado antes de generar o abrir esta cohorte.
**Estado inicial: preparación; examen sin abrir.** Continúa H1/H3, cuyo
[desarrollo está comprobado](ECHO45-H1-H3-RESULTS.md). No es una campaña S6.

## Cohorte y protocolo

- Generador existente ARC3-GYM, versiones 2 y 3, semillas **16000–16059**.
  No reutilizar entrenamiento 0–39, gym-test, S5-D/E ni S6-B0/B2.
- Cinco niveles por mundo, tres repeticiones 0/1/2, **2000 decisiones**.
  120 mundos, 360 partidas y 1800 niveles sumados por agente.
- Agentes congelados: **v5.7, v5.8 y azar**, 1080 partidas en total.
  La fábrica privada existente conserva el registro de agentes anterior.
- Misma semilla de actor `runner.seed_for(game_id, rep)` para la comparación.
  Actor nuevo por partida; aprende dentro del juego, sin arrastrar memoria
  desde otro mundo. No recibe identificador, familia o solucionador.
- Usar CPU local, sin LLM, GPU, API de pago ni juegos oficiales reservados.
- Antes de comenzar se fijan hashes de agente, memorias, runner, generador,
  evaluador, contrato y recibos de desarrollo. El marcador `opened.json`
  declara cuándo la cohorte se consume. No ajustar fuentes después.
- No instrumentar el examen con la mini terminal. Conservar los registros
  normales del runner: acciones, hashes de fotogramas, niveles, modelo final,
  presupuesto y reinicios automáticos. El smoke de entrenamiento sí se observa.
  Un contador de llamadas del entorno distingue un reset automático tras
  GAME_OVER de un reset elegido por el agente, sin trazar decisiones internas.
- Validar determinismo y solucionador en los 600 niveles. La familia sirve
  para el informe del evaluador, nunca como entrada del actor o de un LLM.
- Repetir **todas las 120 partidas v5.8 de rep 0** en un proceso/pool nuevo,
  sin cache de medición; exigir registro completo idéntico.
- Mantener la convención histórica: reinicios automáticos fuera del presupuesto
  y de `actions_per_level`, pero presentes en acciones/fotogramas y contados
  aparte. Declarar esta diferencia respecto de un scorecard de competición.

## Condiciones fijadas para VERDE S5-F

| Id | Condición |
|---|---|
| F1 | Generación determinista, solucionador 600/600 y representación de las siete familias v2 y cuatro v3; no sustituir semillas si falta una familia |
| F2 | Azar resuelve menos del 15 % de los 1800 niveles sumados |
| F3 | v5.8 supera los niveles de v5.7 en H1 **y** en H3, cada familia por separado |
| F4 | v5.8 no pierde niveles en H2/H4 ni en ninguna familia v2; puntuación media total v2 no baja |
| F5 | v5.8 supera la puntuación media de v5.7 en v3 |
| F6 | Fuentes y recibos protegidos intactos, registros válidos, contadores/puntuación reconstruidos y replay completo de rep 0 exacto |

**S5-F VERDE = F1 ∧ F2 ∧ F3 ∧ F4 ∧ F5 ∧ F6.** Un solo examen;
publicar también los resultados por repetición, familia y coste, y cualquier
regresión individual aunque pase el agregado. Si una condición falla, ROJO.
Si falta una medida, PENDIENTE. No seleccionar otro agente o cohorte después
de conocer resultados. Una corrección posterior requiere contrato y examen nuevos.

## Qué cierra y qué no

Este examen mide si el paquete v5.8 generaliza frente a v5.7 en mundos nuevos.
Las ablaciones de desarrollo siguen delimitando la contribución de cada módulo;
no se atribuye toda la ganancia a memoria ni se demuestra transferencia entre
generadores. Los ocho juegos oficiales de desarrollo ya se comprobaron sin
regresión con las fuentes actuales; no se vuelven a medir para elegir el agente.

No mide que un modelo externo mejore ECHO, que ECHO sepa preguntar mejor que
FIJO o que los filtros sean superiores a SIN FILTRO. **S6 sigue ROJO**, aunque
S5-F salga VERDE. La campaña siguiente requiere su propio contrato y otro examen.

Preparación y comandos: `lab/temporal/h1h3-exam-20260927/evaluate.py`.
La fase `prepare` no crea mundos de examen; `smoke` usa solo entrenamiento.
La fase `run` abre la cohorte y realiza la medición y auditoría.
