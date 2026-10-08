# ECHO-4.5 · ECHO-SEED: un ECHO sin entrenar que aprende conceptos en sandboxes clonables — contrato (APROBADO por Roger el 2026-09-25)

2026-09-25. Idea de Roger: «una versión de ECHO sin preentrenar, como base, que se pueda clonar
en otro sandbox y que en ese sandbox se pueda entrenar; entrenar significa que aprenda,
evolucione y entienda significado abstracto». Objetivo de Roger: **ECHO-4.5 debe superar
ARC-AGI-1 y ARC-AGI-2 en porcentaje (aunque sea poco) y hacer un 20–25 % en ARC-AGI-3 como
requisito mínimo.**

## Punto de partida (medido, 2026-09-24/25)

| Banco | ECHO hoy, sin modelo | Fuente |
|---|---|---|
| ARC-AGI-1 evaluación | sin medir (sellada) | — |
| ARC-AGI-2 evaluación | **0 / 120** (búsqueda fija de 17 operaciones) | `ECHO4-BENCH-ARC2-*` |
| ARC-AGI-3, 16 juegos de examen | **13 / 112 niveles (11,6 %)**; puntuación oficial **0,07 / 100** (corregida el 2026-09-25: antes ponía 1,0) | `ECHO4-BENCH-ARC3-RESULTS.md` |
| Semilla sin entrenar, 201 tareas reservadas del gimnasio | **17 verificadas, 15 con el test correcto (7,5 %)** | prueba de humo del 2026-09-25 (borrada; se repite en cada ronda) |

## Qué es ECHO-SEED (ya construido: `echoai/seed/`)

| Pieza | Qué hace |
|---|---|
| `dsl.py` | 44 familias de primitivas pequeñas sobre rejillas: geometría, objetos, gravedad, mitades, lógica entre mitades y colores. **Es todo lo que la semilla sabe al nacer.** |
| `learn.py` | **Despierto:** búsqueda de programas con la biblioteca; un programa solo es un HECHO si reproduce todos los ejemplos. **Sueño:** los trozos que se repiten en programas verificados de ≥2 tareas distintas se convierten en **conceptos nuevos**, que cuestan un solo paso en la búsqueda siguiente. |
| `gym.py` | Gimnasio: 1009 tareas de entrenamiento de ARC-AGI-1 y ARC-AGI-2. El 20 % (201) queda **reservado**: nunca se aprende de él, solo mide si lo aprendido **se transfiere**. Las evaluaciones están **selladas**: el código se niega a leerlas. |
| `sandbox.py` | Sandboxes **clonables** en `lab/seed/sandboxes/NOMBRE/`: `new`, `clone`, `train`, `status`, `verify`. Cada uno tiene su biblioteca, su diario con cadena de hashes (cada hecho y cada concepto nacido) y su curva de aprendizaje. |

«Entender significado abstracto» se mide de forma operativa: **un concepto aprendido en unas
tareas que resuelve tareas que la sandbox no ha visto nunca.**

## Plan por fases

**S1 · rejillas (ARC-AGI-1 y ARC-AGI-2)**
1. **Entrenar** varias sandboxes clonadas de la misma semilla con órdenes de tareas distintos;
   se conservan las bibliotecas que más transfieren al conjunto reservado (**evolución**).
2. **Primitivas por objeto**, lo que más falta hoy: «para cada objeto haz X», recolorear por
   tamaño o forma, copiar un patrón donde haya una marca, trazar líneas entre puntos y
   completar patrones periódicos. Conceptos con **parámetros**, no solo fijos.
3. **Córtex opcional:** un modelo propone programas o conceptos; **solo entran si ECHO los
   verifica** (el mismo cortafuegos de siempre). Es la forma de aprender de un modelo sin
   creérselo.

**S2 · juegos (ARC-AGI-3)**
1. **Inferir la meta:** comparar el estado justo antes y después de cada nivel completado y
   proponer metas («el bloque rojo en la casilla roja»), verificadas contra los niveles
   siguientes.
2. **Planificar hacia la meta** con el modelo del mundo que ya existe (T, BOUNDARY), en lugar de
   explorar a ciegas. Menos acciones significa más puntuación oficial.
3. **Simulador propio (ARC3-GYM):** un generador de juegos pequeños por turnos (empujar a una
   meta, llaves y puertas, interruptores, movimiento en espejo) para entrenar la inferencia de
   metas sin tocar los juegos del examen. Solo hay 8 juegos públicos de desarrollo y no bastan.

## Exámenes y requisitos (se fijan antes de entrenar)

- Cada examen compara **ECHO-4.5 entrenado** con **la semilla sin entrenar**, en el mismo
  proceso y con el mismo presupuesto de búsqueda.
- La semilla sin entrenar también se mide en ese momento: así se ve **qué aporta el
  entrenamiento**.

| Id | Condición | Requisito de Roger |
|---|---|---|
| R1 | ARC-AGI-1, 400 tareas de evaluación: ECHO-4.5 solo > 0 % **y** > la semilla sin entrenar | «superar en porcentaje, aunque sea poco» |
| R2 | ARC-AGI-2, 120 tareas de evaluación: ECHO-4.5 solo > 0 % **y** > la semilla | igual |
| R3 | ARC-AGI-3, 16 juegos de examen: **≥ 20 % de los 112 niveles completados** (decisión de Roger: métrica a). La puntuación oficial se publica siempre, sin umbral | «20–25 % como requisito mínimo» |
| R4 | la auditoría rehace cada programa, cada concepto y la cadena del diario | custodia |

**Decisión de Roger (2026-09-25): métrica (a), % de niveles.** Las opciones que se le presentaron:
- **(a) % de niveles completados.** Hoy estamos en 11,6 %. El 20–25 % exige casi doblarlo: difícil
  pero alcanzable si ECHO aprende a inferir metas.
- **(b) Puntuación oficial de ARC Prize** (niveles × eficiencia frente a un humano). Hoy
  estamos en 0,07 / 100 (corregido: antes ponía 1 / 100). El 20 % exigiría resolver bastantes niveles con casi tan pocas acciones como
  una persona. **No sabemos si es alcanzable** y podría no llegar nunca con este enfoque.

Recomendación: **(a) como requisito de ECHO-4.5**, y (b) publicada siempre, como meta
a largo plazo.

## Reglas

- Las evaluaciones de ARC-AGI-1 y ARC-AGI-2 **no se abren** hasta el examen.
- Los 16 juegos de examen de ARC-AGI-3 ya se usaron en exámenes anteriores, pero **nunca para
  entrenar**, y el gimnasio no los incluye. Se declara que ya no son «nuevos para nosotros»,
  aunque sí para ECHO-4.5.
- Coste: todo en CPU y **0 $**. El córtex, si se usa, va en un bloque aparte con presupuesto.
- Se publica siempre, también si sale rojo.

## Qué no afirma

- Que ECHO «entienda» como una persona. «Entender» significa aquí reutilizar un concepto
  verificado en tareas nuevas.
- Nada sobre los conjuntos privados de ARC Prize.
