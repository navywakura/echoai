# E4-ROLES-1 v4 «la tribu: la deducción propone» — contrato (aprobado por Roger 2026-09-24)

**Declarado:** se formula después de la exploración de v3 (no sellada). En v3,
la inferencia era correcta (M1 ≈97 %, rango correcto 4/4, M6 idéntico), pero
la Q no la explotaba en ~250 decisiones: M2, M3 y M7 no se cumplían.
Todo está publicado en el [contrato v3](ECHO4-ROLES1-V3-DESIGN.md).

## Único cambio: saber → proponer → decidir

La deducción ya no es solo una fila de contexto: **propone** un orden de
candidatos, como hipótesis:

1. el sugerido (último sabedor verificado del tema; si no hay, el líder de
   rango derivado entre los no eliminados);
2. los demás no eliminados, por rango derivado;
3. los eliminados de esta ronda, al final.

La Q original elige **0 = seguir la propuesta, 1 = la siguiente, 2 = la última**.
Todo pasa por el gate. La fila WSP16 derivada indica de dónde viene la propuesta
(ninguna, último sabedor o rango) y cuántos se han eliminado. La Q **puede
aprender a no fiarse**: no hay regla escrita que obligue a seguirla. Es el
patrón de ECHO: proponer no es decidir.

Los controles usan el mismo mecanismo con su propia propuesta:
`no_elimination` (ignora los «no»), `no_rank` (sin rango: orden relativo fijo),
`claimed_rank` (quien afirma rango va primero) y `fixed_order` (fijo, sin Q).

Mundo, pagos, reparto, ventanas, semillas 411/423/439, M1–M8 y criterio de
desarrollo: **sin cambios**. M1 (modo aleatorio) sigue siendo solo predicción.
Si falla, se publica.

## Resultado exploratorio de v4 (2026-09-24, no sellado, no evidencia)

Vida completa (neto de ECHO): `tribe` 1732/1780/1831 frente a `no_elimination`
1811/1836/1804, `no_rank` 1809/1793/1838, `claimed_rank` 1813/1858/1821 y
`fixed_order` 1705/1720/1715. B tras un «no»: 13/30, 18/29, 13/35.

Diagnóstico adicional, puntuando solo tras 192 rondas de formación y en greedy
(el método de INTERACTION/RELATION): `tribe` 958/927/947 frente a `no_rank`
992/992/990. Temas nuevos a la primera: `tribe` 5/3/3 de 12 frente a `no_rank` 7/6/7.

Causa: el rango derivado es histórico. En este mundo la jerarquía cambia
(rondas 192 y 288) justo cuando llegan temas nuevos, y el líder del régimen
anterior engaña. Además, `evidence_budget=4` fuerza unas 144 exploraciones por
vida, lo que tapa diferencias pequeñas entre brazos.

Se sostiene: eliminación ≈97 %, jerarquía propia correcta 4/4 y actualizada,
afirmación de rango ignorada (idéntico bit a bit), menos preguntas por
respuesta (≈143 frente a 239 de `fixed_order`) y cortafuegos. No se sostiene:
más neto que los controles, ni ventaja del rango en temas nuevos.
Iteración detenida para no ajustar hasta obtener verde. Decisión de Roger pendiente.
