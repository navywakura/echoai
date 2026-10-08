# ECHO-4.5 · S5-E: examen de v5.7 frente a v5.6

2026-09-27, fijado antes de abrir estas semillas. Roger autoriza continuar v5.7.
La implementación de `Arc3EchoV57` ya existía; no se atribuye a esta sesión.
El examen cierra su mejora en estado oculto, independientemente de S6-B0.

- Gym v3, semillas **7000–7059**, cinco niveles, reps 0, 1 y 2, 2000 acciones.
- Agentes congelados: v5.6, v5.7 y azar.
- E1: generador determinista y solucionador 300/300 niveles.
- E2: azar <15 % de niveles sumando tres reps.
- E3: v5.7 completa más niveles que v5.6, sumando tres reps.
- E4: puntuación oficial media de v5.7 mayor que v5.6.
- E5: fuentes intactas y replay de v5.7 rep 0 idéntico en acciones y frames.
- **Verde = E1 ∧ E2 ∧ E3 ∧ E4 ∧ E5**, una sola medición, se publica rojo o verde.

Fuente congelada: perfil `lab/seed/s6b0-final-20260927/profile.json`, más este
contrato y el evaluador `lab/kaggle/s6b0-20260927/evaluate.py` en el recibo local.
El modelo de S6-B0 no ve estas partidas. La pérdida conocida en una semilla
de g50t oficial se declara, aunque el gym salga verde: S5-E no demuestra mejora
universal ni satisface el objetivo R3 de ECHO-4.5.
