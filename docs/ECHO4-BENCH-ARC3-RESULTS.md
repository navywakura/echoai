# E4-BENCH-ARC3 · resultados del examen (2026-09-24)

Contrato: `ECHO4-BENCH-ARC3-D-DESIGN.md`. 16 juegos de examen, 2000 acciones por juego y
brazo, sin modelo de lenguaje, 0 $.

## Veredicto

| Id | Condición | v1 | v2 |
|---|---|---|---|
| D1 | niveles de ECHO > media de RANDOM (3 semillas) | 8 > 2 **VERDE** | 13 > 2 **VERDE** |
| D2 | niveles de ECHO > niveles sin BOUNDARY | 8 > 1 VERDE | 13 > 2 VERDE |
| D3 | la repetición da 0 diferencias | 80 partidas, 0 **VERDE** | 32 partidas, 0 **VERDE** |

**v1 VERDE y v2 VERDE.** Auditoría: `lab/arc3/exam-v1/audit.txt` y `lab/arc3/exam-v2/audit.txt`.

## Totales

| Brazo | Niveles (de 112) | Juegos con ≥1 nivel | Puntuación oficial media (0–100) |
|---|---|---|---|
| ECHO v1 | 8 | 7 | 1,73 |
| ECHO v2 | **13** | **9** | 1,00 |
| sin BOUNDARY v1 | 1 | 1 | 0,03 |
| sin BOUNDARY v2 | 2 | 2 | 0,10 |
| RANDOM (3 semillas, media) | 2 | 2 | 1,09 |

## Por juego (niveles completados · puntuación)

| Juego | ECHO v1 | ECHO v2 | RANDOM s0 / s1 / s2 |
|---|---|---|---|
| ar25 | 0 | 1 · 0,21 | 0 / 0 / 0 |
| cd82 | 1 · 0,59 | 1 · 0,61 | 0 / 0 / 0 |
| cn04 | 0 | 0 | 0 / 0 / 0 |
| dc22 | 0 | 1 · 1,07 | 0 / 0 / 0 |
| ft09 | 0 | 1 · 1,03 | 0 / 0 / 0 |
| ka59 | 0 | 0 | 0 / 0 / 0 |
| lf52 | 1 · 1,32 | 1 · 1,00 | 0 / 0 / 0 |
| r11l | 2 · 17,00 | 1 · 1,12 | 1 / 1 / 1 |
| re86 | 0 | 0 | 0 / 0 / 0 |
| sb26 | 0 | 0 | 0 / 0 / 0 |
| sc25 | 0 | 0 | 0 / 0 / 0 |
| sp80 | 1 · 6,13 | 1 · 0,59 | 1 / 1 / 1 (≈16 cada una) |
| tn36 | 1 · 0,76 | 0 | 0 / 0 / 0 |
| tr87 | 0 | 0 | 0 / 0 / 0 |
| tu93 | 0 | **4 · 7,03** | 0 / 0 / 0 |
| vc33 | 2 · 1,93 | 2 · 3,32 | 0 / 0 / 0 |

## Lectura honesta

- **En niveles, ECHO gana al azar con claridad:** 13 frente a 2, y en 9 de 16 juegos frente a 2.
- **En la puntuación oficial, no.** La fórmula premia completar un nivel con **tan pocas
  acciones como un humano**. ECHO explora: necesita cientos de acciones donde un humano usa
  decenas. v2 completa más niveles que v1, pero con más acciones cada uno, y su puntuación
  media (1,00) queda **por debajo** de la del azar (1,09). Esa media del azar sale casi
  entera de sp80, donde acierta pronto por suerte. v1 sí la supera (1,73), sobre todo por r11l.
- **La ablación confirma la pieza:** sin BOUNDARY (clics al azar, el borde del tiempo cuenta
  como estado), ECHO cae al nivel del azar.
- **7 de 16 juegos siguen en 0 niveles** para todos los brazos.

## Por qué no «resuelve» ARC-AGI-3

ECHO-ARC3 sabe qué depende de él, recuerda lo vivido y no repite lo que no sirve. **No sabe
cuál es el objetivo del juego.** Completa un nivel cuando su exploración lo alcanza, no
porque haya entendido la regla. Para puntuar alto hace falta **inferir la regla** («hay que
llevar el bloque a la casilla del mismo color») y actuar directamente. Ese es el papel del
brazo con córtex del contrato: el modelo propone la regla y ECHO la comprueba actuando. Es de
pago y necesita la orden de Roger.

## Qué no afirma

- Nada sobre el conjunto privado de ARC-AGI-3 ni sobre el premio.
- La puntuación la calcula nuestro código con la fórmula publicada y las acciones de
  referencia que trae cada juego. No es una puntuación enviada a ARC Prize.

## Corrección (2026-09-25): la puntuación oficial estaba mal calculada

Las reglas de ARC Prize 2026 en Kaggle definen la puntuación así:
- **por nivel:** `min(acciones_humano / acciones_agente, 1)` **al cuadrado**;
- **por juego:** media **ponderada por el número de nivel** (el nivel 1 pesa 1, el nivel 2 pesa 2…);
- **total:** media de los juegos.

Nuestra función `score()` hacía una media simple sin cuadrado, lo que **inflaba** la puntuación.
Recalculada desde los mismos registros (los niveles no cambian y los veredictos D1–D3 tampoco,
porque se basaban en niveles):

| Brazo | Niveles | Oficial correcta | Publicada antes |
|---|---|---|---|
| ECHO v1 | 8 | **0,34** | 1,73 |
| ECHO v2 | 13 | **0,07** | 1,00 |
| RANDOM (media de 3 semillas) | 2 | **0,29** | 1,09 |
| sin BOUNDARY v1 / v2 | 1 / 2 | 0,00 / 0,00 | 0,03 / 0,09 |

**Lectura corregida:** en puntuación oficial, ECHO v1 queda apenas por encima del azar y v2 por
debajo. Los niveles completados (13 frente a 2) siguen siendo el resultado que se sostiene.
