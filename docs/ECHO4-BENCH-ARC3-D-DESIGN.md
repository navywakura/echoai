# E4-BENCH-ARC3 · contrato D (APROBADO por Roger el 2026-09-24: «haz las 2»)

Examen de ARC-AGI-3 con los 16 juegos congelados (`lab/arc3/split.json`, sha256 `91f23200…`,
sin ls20). Contrato de origen: `ECHO4-BENCH-ARC3-DESIGN.md`.

## Resultado del desarrollo (8 juegos de desarrollo, 2000 acciones)

| Brazo | Niveles | Dónde |
|---|---|---|
| ECHO v1 | 3 | lp85, m0r0, su15 |
| RANDOM | 1 | m0r0 |
| ECHO sin BOUNDARY | 0 | — |

Auditoría por repetición: 24 partidas, 0 diferencias.

## Dos versiones, declaradas antes del examen

- **v1:** el agente tal como salió del desarrollo. Se congela **antes** de tocar nada más:
  `lab/arc3/exam-v1/arc3_agent-v1.py`, sha256
  `4614984cdec41a06435f4a3351563db6ca2d8212ee1584b052ef214d443e39c7`.
- **v2:** una ronda más de desarrollo **solo con los 8 juegos de desarrollo**. El examen de v1
  se ejecuta en segundo plano y **nadie mira sus resultados** hasta que v2 esté congelado. Así,
  v2 no se ajusta a lo que v1 haya hecho en el examen.
- Las dos versiones se publican, sea cual sea el resultado de cada una.

## Examen (igual para v1 y v2)

- 16 juegos de examen, **2000 acciones por juego** y brazo.
- Brazos: ECHO (vN), ECHO sin BOUNDARY (vN) y RANDOM con **3 semillas** (`--rep 0,1,2`).
  RANDOM no cambia entre versiones: v2 usa las mismas partidas de RANDOM que v1.

## Umbrales (fijados antes del examen)

| Id | Condición | Tipo |
|---|---|---|
| D1 | niveles totales de ECHO > media de niveles totales de RANDOM (3 semillas) | principal |
| D2 | niveles totales de ECHO > niveles totales de ECHO sin BOUNDARY | secundario |
| D3 | la auditoría repite todas las partidas con 0 diferencias en fotogramas y niveles | custodia |

**Verde = D1 ∧ D3.** D2 se informa, pero no decide el verde. La puntuación oficial (fórmula
de ARC Prize) se publica siempre, **sin umbral**: esperamos que sea muy baja.

## Qué no afirma

- Nada sobre el conjunto privado ni sobre el premio ARC.
- Que ECHO «resuelva» ARC-AGI-3. Un verde significa solo que completa más niveles que el
  azar con el mismo presupuesto.
- Sin modelo de lenguaje y sin gasto: 0 $.

## Congelación de v2 (antes de mirar el examen de v1)

- El examen de v1 terminó en segundo plano (`lab/arc3/exam-v1/`) y sus resultados **no se
  abrieron** antes de este punto.
- Cambios de v2 (clase `Arc3EchoV2`, brazos `ECHO2` y `NOBOUNDARY2`), sacados de fallos medidos
  en desarrollo:
  1. **Culpa:** un «fin de partida» tras una acción que ya se había sobrevivido desde el mismo
     estado es el presupuesto de pasos agotándose, no esa acción. v1 la marcaba como mortal.
  2. **Memoria de efectos:** lo que hace un **tipo** de acción se generaliza entre estados
     (teclas por su número, clics por el color y el tamaño del objeto). Las acciones sin probar
     se ordenan por la probabilidad estimada de cambiar algo, y los clics inertes dejan de gastar
     el presupuesto. Hasta 64 objetivos de clic por estado.
- Desarrollo (`lab/arc3/dev-v2`, 8 juegos de desarrollo, 2000 acciones): ECHO2 completa
  **7 niveles** (bp35 1, lp85 3, m0r0 1, s5i5 1, su15 1) y NOBOUNDARY2 **0**. v1 completaba 3.
- Instantánea: `lab/arc3/exam-v2/arc3_agent-v2.py`, sha256
  `8d0c16ac1673dd9b1b39a9e88aa5d5bd087a03f25957664e1ca532e7c73bbf50`.
- El examen de v2 reutiliza las 3 partidas de RANDOM de v1 (el mismo agente y las mismas
  semillas).
