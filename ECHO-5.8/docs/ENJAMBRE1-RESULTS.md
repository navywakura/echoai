# C v1 · ENJAMBRE-1 — resultados del examen

21 de octubre de 2026. Contrato: [ENJAMBRE1-DESIGN.md](ENJAMBRE1-DESIGN.md)
(§11 enmienda 1, rediseño, aprobada por Roger; §12 enmienda 2 tras la
revisión). Examen corrido **una vez**: 140 trabajos (7 brazos × 20 equipos),
0 fallos de ejecución. Congelación `lab/echo58/enjambre/preflight.json`
(misiones `1e4a6b17…`); datos `lab/echo58/enjambre/exam/`; informe
`lab/echo58/enjambre/results.json`.

## Veredicto: **VERDE** (E1 ∧ E2 ∧ E3 ∧ E4, `destroyed == 0`, postales de 16 B) — confirmado por verificador independiente

El verificador recalculó la congelación (`frozen_state` y misiones `1e4a6b17…` idénticas), los cinco Wilcoxon exactos + Holm con su propio código (idénticos), revisó los brazos en el código, repitió cuatro trabajos del examen (idénticos salvo `secs`) y pasó los 11 tests. Corrigió tres frases de esta sección (ya corregidas abajo).

| Brazo | Puntuación (suma de 20) | Mundos resueltos (de 160) | Fallidos | Daño |
|---|---|---|---|---|
| **enjambre** | **691** | **160** | **287** | 137 |
| sin_global | 920 | 160 | 437 | 232 |
| global_barajada | 937 | 160 | 469 | 205 |
| sin_privada | 989 | 154 | 487 | 246 |
| sin_ayuda | 1685 | 120 | 1281 | 137 |
| aislados | 1866 | 119 | 1383 | 230 |
| uno_solo (se informa) | — | 119 | 1352 (en 1471 episodios) | 125 |

Puntuación: por cada mundo, la ronda en que se resolvió (31 si no); menos es mejor.

| Predicción | Comparación | Gana / empata / pierde | p | Holm |
|---|---|---|---|---|
| E1 | enjambre < sin_global (puntuación) | 20 / 0 / 0 | 9,5·10⁻⁷ | pasa |
| E1 | enjambre < global_barajada (puntuación) | 19 / 0 / 1 | 2,9·10⁻⁶ | pasa |
| E2 | enjambre < sin_ayuda (puntuación) | 20 / 0 / 0 | 9,5·10⁻⁷ | pasa |
| E3 | enjambre < sin_privada (fallidos) | 11 / 9 / 0 | 4,9·10⁻⁴ | pasa |
| E4 | enjambre < aislados (puntuación) | 20 / 0 / 0 | 9,5·10⁻⁷ | pasa |

## Lo que esto dice y lo que no

1. **La memoria global ayuda de verdad.** Con el idioma común y las
   identidades compartidas, el enjambre gana en las 20 macros a no compartir
   (691 frente a 920) y en 19 de 20 a compartir con las claves barajadas. Muere
   menos en la lava (48 frente a 89).
2. **La memoria privada importa donde el mundo contradice al grupo.** En los
   mundos con excepción local, quien solo tiene la global muere mucho más
   (daño 201 frente a 89). En 9 de 20 equipos empatan en fallidos: el efecto
   solo aparece cuando la excepción llega a quemar (en los 9 empates el daño
   local es igual). **La ventaja está concentrada:** las macros 10 y 14 dan 158
   de los 200 fallidos de diferencia; los 6 mundos que sin_privada no resuelve
   están todos en la macro 10 (2 locales, 2 placas, 2 de lava).
3. **Ayudarse cuenta, pero solo donde hace falta.** Sin los mundos de placa,
   enjambre y sin_ayuda empatan exactamente (445 = 445, p = 1). Toda la
   ventaja de la ayuda viene de los mundos que **no se pueden resolver solo**,
   es decir, en parte por construcción (declarado en §11). Ir a ayudar en los
   demás mundos no adelanta nada (como en el primer diseño).
4. Dentro de las placas, el protocolo de pedir y sujetar (programado a mano en
   `cagent.py`) funciona: 73 peticiones,
   403 pasos sujetando la placa, 85 viajes de ayuda, 937 notas pasadas, y
   las 40 placas del examen se resolvieron.
5. **Los mundos y la cooperación los diseñé yo (Claude).** El examen mide que
   los mecanismos de ECHO (memoria privada, global por WSP, peticiones)
   funcionan en ellos, no que ECHO haya inventado cooperar.
6. Un agente solo, con hasta 120 episodios por macro (30 por mundo), resuelve 119
   mundos de 160 en 1471 episodios; el equipo, 160 en 532 episodios.

Sin mentiroso (eso es C v2, sobre LINK-3).
