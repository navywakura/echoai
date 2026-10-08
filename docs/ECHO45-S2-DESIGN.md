# ECHO-4.5 · S2 (aprender mejor) · criterio (fijado el 2026-09-25, antes de medir) y cierre: VERDE

**S2 verde** si la biblioteca final de S2 resuelve **más de 21** tareas reservadas (el resultado de
S1) con la búsqueda **determinista** y el mismo presupuesto (400 expansiones), y `verify` cuadra en
sus diarios. Una mejora que solo aparezca con más presupuesto se informa aparte y no cuenta como
verde de S2.

Primer intento (2026-09-25), con intuición por frecuencias, conceptos con parámetros y evolución
desde una sandbox entrenada: **21 → 21, rojo.**
- Con solo 84 programas verificados de 808, ninguno comparte forma con otros colores, así que no
  nació ningún concepto con parámetros.
- Los clones partían de la misma base entrenada, así que no hubo diversidad.
- Con el límite de 8 s por tarea, las medidas oscilaban entre 20 y 21: la búsqueda no era
  determinista.

Pendiente, por orden:
1. determinismo (solo límite de expansiones);
2. 400 frente a 1500 expansiones;
3. intuición neuronal en GPU;
4. evolución desde la semilla con currículos distintos;
5. cierre.

## Cierre (2026-09-25, 23:55): S2 VERDE

| Medida (201 reservadas, 400 expansiones, búsqueda determinista) | Verificadas | Test correcto |
|---|---|---|
| S1 | 25 | 21 |
| S2: intuición por frecuencias (+ conceptos con parámetros y evolución desde una base entrenada) | 25 | 21 |
| S2 + red de intuición (65 primitivas) | 26 | 21 |
| **S2v: vocabulario ampliado (84) + intuición por frecuencias** | **30** | **24** |
| S2v + red de intuición | 30 | 24 |

- **Criterio:** más de 21 → **24. Verde.**
- **Custodia:** `verify echo45-s2v` → `valid: true` (84 programas, cadena intacta).
- **Determinismo:** dos medidas seguidas dan el mismo conjunto de tareas.
- **Presupuesto:** 1500 expansiones dan exactamente las mismas tareas que 400; el techo era el
  vocabulario, no el tiempo de búsqueda.
- **Red de intuición** (entrenada en la GPU T4 de Kaggle con 100 000 y 150 000 sueños):
  recall@5 de 0,78 y 0,79 en sueños no vistos. En las reservadas **empata** con la intuición por
  frecuencias, cambiando una tarea por otra. Se conserva para vocabularios mayores.
- **Conceptos con parámetros:** el mecanismo funciona (prueba unitaria: aprende «recolorear X→Y y
  recortar» y resuelve una tarea nueva con colores no vistos). En datos reales no nació ninguno,
  porque con 84 programas no hay dos con la misma forma y distinto color.
- **Lectura:** la mejora viene del vocabulario ampliado, que S1b demostró que sin intuición diluía la
  búsqueda (20). La intuición es lo que permite crecer.
- La evolución desde la semilla con currículos distintos sigue en marcha. Se añadirá como anexo; no
  forma parte del criterio.

Base oficial de ECHO-4.5 tras S2: sandbox `echo45-s2v` (nivel S2v, 84 primitivas, 3 conceptos,
intuición por frecuencias; red en `lab/seed/intuition-v2/intuition-s2v.npz`).

## Anexo (2026-09-26): evolución desde la semilla con currículos distintos

Tres clones de `echo45-s1-seed` (vocabulario S1, intuición por frecuencias), cada uno con un orden y
un subconjunto de 400 tareas por ronda, 2 rondas:

| Clon | Tareas de entrenamiento verificadas | Conceptos | Reservadas correctas |
|---|---|---|---|
| evo-a | 36 → 61 | 2 | 21 · 21 |
| evo-b | 34 → 55 | 1 | 21 · 21 |
| evo-c | 46 → 67 | 1 | 21 · 21 |

El currículo cambia lo que aprende cada clon, pero **no lo que transfiere**: con el vocabulario S1,
los tres llegan a las mismas 21 tareas. Confirma la lectura de S2: el techo lo marca el vocabulario.
No cambia el verde de S2, que se obtuvo con S2v.
