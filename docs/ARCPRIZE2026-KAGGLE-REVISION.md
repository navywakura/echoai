# ARC Prize 2026 en Kaggle · revisión de reglas (2026-09-25)

Leído con la API de Kaggle (cuenta `rogeernavarro`). Copias de las páginas en
`lab/kaggle/arcprize2026/*-pages.json`.

## Las tres competiciones

| | ARC-AGI-3 | ARC-AGI-2 | Paper track |
|---|---|---|---|
| Qué se evalúa | agente en **110 juegos privados**: 55 para la tabla pública y 55 para la privada | tareas de rejilla ocultas, 2 intentos por salida | un **informe** (≤1500 palabras) sobre nuestra entrada a ARC-3 o ARC-2, con un notebook público |
| Puntuación | por nivel `min(humano/agente, 1)²`; por juego, media ponderada por número de nivel; total, media de juegos | % de salidas exactas | rúbrica 0–5: precisión, universalidad, progreso, **teoría**, completitud y **novedad** |
| Cómo se entrega | notebook de Kaggle, **≤9 h, sin internet**; se permiten modelos preentrenados públicos; GPU T4/P100 y RTX 6000 solo para esta competición | notebook, **≤12 h, sin internet**; L4×4 con 96 GB solo para esta competición | writeup + notebook público |
| Envíos | 1 al día; 2 finales | 1 al día; 2 finales | 1 writeup |
| Fechas | aceptar las reglas antes del **26-10-2026**; envío final **2-11-2026** | igual | **9-11-2026** |
| Premios | 75 000 $ en la tabla final (1.º 40 000 $); 700 000 $ extra solo si alguien llega al **100 %** | 275 000 $ de progreso; 275 000 $ al mejor informe; 150 000 $ extra si alguien llega al **85 %** | 50 000 / 20 000 / 5 000 $; hasta 375 000 $ repartidos entre informes con más de 4,5/5 |
| Equipos | hasta 8 personas | hasta 8 | el mismo equipo que envía a ARC-2 o ARC-3 |

## Licencia: el punto que choca con nuestra release

- **Para cobrar un premio** hay que liberar la solución y el código que la genera con licencia
  **CC-BY 4.0**, que permite el uso comercial.
- En ARC-3 exigen además, según la definición de IA abierta de la OSI, que el **sistema, el modelo
  y los pesos** sean abiertos.
- Un participante que pueda ganar premio y no libere su código **queda fuera**.
- Se puede **participar y aparecer en la tabla** sin premio. Liberar solo es obligatorio para cobrar.
- **Conflicto:** la release 4.0.0rc2 de ECHO es PolyForm-NC con el núcleo compilado. Para optar a
  premio habría que liberar **la parte que genera la entrada** (por ejemplo `echoai/seed/` y el
  agente de ARC-3) en CC-BY 4.0. **Es una decisión de negocio de Nav.** Se puede separar: liberar
  el agente de la competición y mantener el resto como está.

## Lo que cambia para nosotros

1. **Puntuación de ARC-3 corregida.** Nuestra fórmula inflaba el resultado. ECHO v2 hace 0,07/100
   y no 1,0 (ver `ECHO4-BENCH-ARC3-RESULTS.md`). Ya está corregido en la web.
2. **La comparación oficial existe.** La tabla de Kaggle en 110 juegos privados es la comparación
   justa con otros sistemas, con la **puntuación oficial**, no con el % de niveles de nuestro
   requisito R3.
3. **Encaje técnico:** sin internet, ≤9 h y modelos públicos permitidos. ECHO es CPU y encaja. Con
   la fórmula al cuadrado, **la eficiencia en acciones pesa muchísimo**: completar niveles
   explorando con cientos de acciones puntúa casi 0. Eso refuerza S3 y S4 (inferir la meta y
   planificar), no solo completar más niveles.
4. **El paper track encaja con ECHO:** premia teoría, novedad y universalidad, además de la
   precisión. La propuesta (cortafuegos, verificación, núcleo en enteros, aprendizaje por sueño) es
   nuestro punto fuerte.
5. **Calendario:** quedan unas 5 semanas para el envío final (2-11) y 6 para el informe (9-11).
