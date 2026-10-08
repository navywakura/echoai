# ARC Prize 2026 · plan de campaña de RxLabs (2026-09-25)

Decisión de Roger: **«vamos a participar para intentar ganar, vamos con todo»**. Primero se termina
y se entrena ECHO-4.5, y eso es lo que se sube. Reglas revisadas en `ARCPRIZE2026-KAGGLE-REVISION.md`.

## Decisiones tomadas

| Tema | Decisión |
|---|---|
| Equipo | una persona: Roger (`rogeernavarro`), nombre RxLabs |
| Licencia | paquete aparte **`echo-arc`**, autocontenido: agente de ARC-3, ECHO-SEED y la memoria verificada mínima. Si ganamos, **solo eso** se publica en CC-BY 4.0. La release de ECHO-4 (núcleo, EGO…) sigue en PolyForm-NC y la entrega **no la importa** |
| Reglas aceptadas | ARC-AGI-3 ✅ · ARC-AGI-2 ✅ · paper track ✅ (comprobado por la API el 2026-09-25) |
| Qué se sube | **ECHO-4.5** (ECHO-SEED con S1–S5) integrado en `echo-arc` |

## Dónde estamos frente a la tabla (2026-09-25, sin inflar)

| | 1.º de la tabla | 10.º | ECHO hoy |
|---|---|---|---|
| ARC-AGI-3 (puntuación oficial) | 19,45 | 8,81 | 0,07–0,34 (en nuestros 16 juegos) |
| ARC-AGI-2 (%) | 83,06 | — | 0 solo · 6,7 con DeepSeek (30 tareas) |

**Lectura honesta:**
- ganar la clasificación de ARC-2 en 5 semanas **no es realista**;
- en ARC-3 la distancia es enorme, pero el campo es más abierto;
- **nuestra mejor opción de premio es el paper track**: la rúbrica pesa por igual precisión,
  universalidad, progreso, **teoría**, completitud y **novedad**.

## Estrategia

1. **ARC-3, el objetivo principal.** ECHO-4.5 con S3 (el juego como objetos), S4 (inferir la meta y
   planificar) y S5 (simulador para entrenar), para reducir acciones: con la fórmula oficial al
   cuadrado, la eficiencia lo es todo.
   - **Opción acordada:** construir sobre el mejor agente **público y abierto** de la competición.
     El «duck harness» de Tufa Labs, ganador del hito de junio, usa un Qwen de 27B en GPU. Se le
     añaden las piezas de ECHO y se mide **con ablación** cuánto sube gracias a ECHO.
   - **Licencia confirmada por Roger (2026-09-25): Apache 2.0.** Se puede reutilizar. Lo suyo conserva
     su aviso y su licencia Apache 2.0; lo que añadamos va en CC-BY 4.0.
2. **ARC-2, entrada digna sin expectativa de premio:** ECHO-SEED (búsqueda verificada, CPU) + un
   modelo abierto en la GPU L4 que propone programas, con ECHO como juez.
3. **Paper track:** el informe con todo lo medido y auditado. Es el objetivo con más probabilidad
   de premio.

## Calendario (fechas límite a las 23:59 UTC)

| Semana | Fechas | Trabajo |
|---|---|---|
| 1 | 26 sep – 2 oct | **Canal de envío:** esqueleto de `echo-arc`, puntuación oficial correcta en local y un notebook de Kaggle sin internet con el agente actual. **Primer envío de prueba a ARC-3**: da una puntuación real y detecta pronto problemas de formato o tiempo. Revisar la licencia del agente público |
| 2–3 | 3 – 16 oct | **ECHO-4.5, juegos:** S3 + S4 + S5 mínimo, integrados en el agente fuerte; ablación en los juegos públicos. Un envío al día como señal, sin sobreajustar a la tabla pública (55 juegos) |
| 4 | 17 – 25 oct | **Examen interno de ECHO-4.5** (R1–R4, con las evaluaciones selladas y los 16 juegos) + S2 para ARC-2. Congelar las candidatas |
| 5 | 26 oct – 2 nov | **26 oct:** último día para aceptar reglas y unir equipos. Envíos finales; elegir las 2 finales de cada competición |
| 6 | 3 – 9 nov | **Paper** (≤1500 palabras), notebook público y publicación de `echo-arc` en CC-BY 4.0 |

## Reglas internas durante la campaña

- Nuestro examen de ECHO-4.5 (16 juegos y evaluaciones selladas) **sigue limpio**: no se desarrolla
  sobre él. Para la competición, los 25 juegos públicos sirven de desarrollo, porque la prueba real
  son 110 juegos privados.
- La tabla pública (55 juegos) solo se mira como señal: los premios los decide la privada.
- La entrega **no importa** el núcleo ECHO-4. Todo lo que ejecuta vive en `echo-arc`.
- Todo sigue auditado y los rojos se publican. Coste de ejecución: 0 $ (GPU gratuita de Kaggle).
