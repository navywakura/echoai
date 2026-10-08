# E4-BENCH-ARC2 · resultados del examen (2026-09-25)

Contrato: `ECHO4-BENCH-ARC2-DESIGN.md`, con los umbrales fijados antes del desarrollo.
- **Arnés congelado:** sha256 `e33c3d23…`.
- **Tareas:** las 120 públicas de evaluación de ARC-AGI-2 (Qwen y ECHO solo) y 30 elegidas por
  semilla (DeepSeek).
- **Auditoría:** re-ejecuta cada programa verificado y la búsqueda de ECHO solo, y vuelve a puntuar
  desde las salidas públicas. `valid: true`, 570 registros, 0 diferencias, resumen sha256
  `91eeea17…`.
- **Coste del examen:** 2,89 $ (Qwen 0,95; DeepSeek 1,94). Todo el bloque, con el desarrollo:
  ≈3,5 $.

## Veredicto: ROJO

| Id | Condición | Resultado |
|---|---|---|
| G1 | L+ECHO > L en al menos un modelo | DeepSeek: 6,7 % > 3,3 % **verde** |
| G2 | L+ECHO > C en ese mismo modelo | DeepSeek: 6,7 % = 6,7 % **rojo** (empate) |
| G3 | ECHO solo resuelve ≥ 1 tarea | 0 de 120 (se informa) |
| G4 | la auditoría cuadra | **verde** |

**Verde exigía G1 ∧ G2.** La mejora de DeepSeek con ECHO frente a DeepSeek solo se explica igual de
bien por **probar más programas**: el control, con 4 programas sin verificar, resuelve lo mismo. No
se demuestra que la verificación de ECHO aporte aciertos en ARC-AGI-2.

## Resultados (puntuación oficial = media por tarea de las salidas acertadas, con 2 intentos)

| Modelo | L (solo) | L+ECHO | C (control) |
|---|---|---|---|
| DeepSeek-V4.1-Flash (30 tareas) | 1 tarea · 3,3 % | 2 · 6,7 % | 2 · 6,7 % |
| Qwen3-30B-A3B (120 tareas) | 0 · 0 % | 0 · 0 % | 0 · 0 % |
| ECHO solo (120 tareas) | — | — | 0 · 0 % |

Tareas resueltas por DeepSeek:
- L: `2ba387bc`;
- L+ECHO: `1818057f` y `2ba387bc`;
- C: las mismas dos.

## Lo que sí se ve: ECHO no deja pasar respuestas sin verificar (sin umbral)

| Modelo y brazo | Tareas con respuesta enviada | Acertadas | **Incorrectas enviadas** |
|---|---|---|---|
| Qwen · L | 105 | 0 | **105** |
| Qwen · C | 97 | 0 | **97** |
| Qwen · L+ECHO | 0 | 0 | **0** |
| DeepSeek · L | 1 | 1 | 0 |
| DeepSeek · C | 4 | 2 | **2** |
| DeepSeek · L+ECHO | 3 | 2 | **1** |

- Es el mismo efecto que en SimpleQA: ECHO **se abstiene** cuando no puede verificar.
- **Un fallo a declarar:** un programa de DeepSeek pasó todos los ejemplos resueltos, pero falló en el
  test. Verificar contra los ejemplos **no garantiza** acertar la salida nueva.
- DeepSeek solo (L) envió respuesta en 1 de 30 tareas: la mayoría agotó el límite de 12 000 tokens
  razonando. El límite era igual para los tres brazos.

## Lectura

- **ARC-AGI-2 no es, hoy, un banco donde ECHO aporte aciertos.** Ni solo (0/120) ni verificando a un
  modelo, frente a un control justo.
- **Con un modelo débil, ECHO evita 105 respuestas falsas y no pierde nada**, porque ese modelo no
  acierta ninguna.
- Esto encaja con el diagnóstico de ECHO-4.5: sin vocabulario de objetos ni aprendizaje de
  conceptos, la búsqueda de ECHO no llega a las soluciones (`ECHO45-DECISIONES.md`).

## Qué no afirma

- Nada sobre el conjunto privado de ARC-AGI-2 ni sobre modelos más fuertes.
- DeepSeek se midió en 30 tareas por presupuesto: el margen de error es grande.
