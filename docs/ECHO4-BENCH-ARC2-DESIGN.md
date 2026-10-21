# E4-BENCH-ARC2 · ARC-AGI-2 con un modelo, con ECHO y con ECHO solo — contrato

Aprobado: «ok perfecto haz», sobre la propuesta «Qwen completo + DeepSeek en 60
tareas + ECHO solo, con los 4,10 $ que quedan». **Los umbrales se fijan aquí, antes del
desarrollo.** Así no hace falta un contrato D aparte, y es más estricto.

## Pregunta

¿Un modelo resuelve más tareas de ARC-AGI-2 cuando ECHO **ejecuta y verifica** sus programas
contra los ejemplos resueltos, que cuando responde solo o prueba lo mismo sin verificar?

## Datos (congelados antes de mirar ninguna tarea del examen)

`lab/arc2/split.json`, sha256 `544f279c44ed526ef42d0ad0a6ee0579021ddab6e868d29b664be85a4c30ced5`.
Repositorio oficial `arcprize/ARC-AGI-2` (Apache-2.0), commit `f3283f72…`.
- **Examen:** las 120 tareas públicas de evaluación, con 167 salidas de test.
- **Examen de DeepSeek:** 60 de esas 120, elegidas por semilla.
- **Desarrollo:** 30 tareas de entrenamiento elegidas por semilla. Nunca tareas de evaluación.

## Brazos

| Brazo | Qué hace | Llamadas por tarea |
|---|---|---|
| **L** | el modelo ve los ejemplos y escribe hasta 2 rejillas de respuesta por test (regla oficial: 2 intentos) | 1 |
| **L+ECHO** | el modelo escribe una función `transform(grid)`. ECHO la **ejecuta** sobre los ejemplos resueltos y le dice en qué ejemplo y cuántas celdas falló. Hasta 4 rondas. **Solo se envía un programa que reproduce todos los ejemplos.** Si ninguno lo consigue, ECHO dice «no lo sé» y la tarea cuenta 0 | ≤ 4 |
| **C** (control) | 4 programas sin que ECHO diga nada; en cada ronda el modelo ve sus programas anteriores, pero no si funcionan. Se envían las salidas de los 2 primeros que se ejecutan sin error | 4 |
| **ECHO solo** | sin modelo: un buscador de programas con operaciones simples (girar, reflejar, trasponer, recolorear de forma consistente, recortar al contenido, escalar, repetir en mosaico, y combinaciones de dos). Solo envía un programa que reproduce todos los ejemplos | 0 (0 $) |

**Ejecución aislada:**
- el código del modelo corre en **otro proceso**, con límite de tiempo (5 s) y de memoria
  (512 MB);
- sin importaciones, sin ficheros, sin `eval` ni `exec`, sin atributos `__dunder__` y sin red;
- se comprueba el árbol sintáctico antes de ejecutarlo.

## Métrica

- **Puntuación oficial:** fracción de salidas de test acertadas exactamente, con 2 intentos por
  salida y la media por tarea.
- **Coste** en dólares y en llamadas por brazo.

## Umbrales (fijados antes del desarrollo)

| Id | Condición | Tipo |
|---|---|---|
| G1 | puntuación de L+ECHO > puntuación de L, **en al menos 1 de los 2 modelos** | principal |
| G2 | puntuación de L+ECHO > puntuación de C en ese mismo modelo | principal: la mejora viene de verificar, no de probar más |
| G3 | ECHO solo resuelve al menos 1 tarea de evaluación | se informa |
| G4 | la auditoría recalcula todo desde los recibos (respuestas del modelo y ejecuciones) con el mismo sha256 | custodia |

**Verde = (G1 ∧ G2 para el mismo modelo) ∧ G4.**

## Modelos y presupuesto

| Modelo | Tareas | Coste esperado |
|---|---|---|
| Qwen3-30B-A3B-Instruct-2507 | 120 | ≈1 $ |
| DeepSeek-V4.1-Flash (razona por defecto) | 60 | ≈2,3 $ |
| ECHO solo | 120 | 0 $ |

- **Tope duro:** 3,5 $ en total. Suelo de crédito de OpenRouter: 0,60 $.
- **El desarrollo** (30 tareas de entrenamiento) usa solo Qwen: ≈0,25 $.
- Si DeepSeek sale más caro de lo previsto en el desarrollo, se reduce su número de tareas
  **antes** del examen, por semilla, y se declara.

## Método

Contrato → desarrollo con las 30 tareas de entrenamiento → congelación del arnés con su sha256 →
examen → auditoría → resultados publicados en el artículo de benchmarks, con gráfica, también si
sale rojo.

## Qué no afirma

- Nada sobre el conjunto privado de ARC-AGI-2 ni sobre el premio.
- Nada sobre modelos más fuertes.

## Desarrollo y congelación (2026-09-25, antes del examen)

**Qwen, 30 tareas de entrenamiento** (`lab/arc2/dev-v1`). Ronda 1: fallos del arnés, no del
método, corregidos:
- programas cortados por el límite de tokens: se piden programas cortos y el límite sube a 6000;
- Qwen creía que la rejilla llegaba como texto: se aclara que es una lista de listas de enteros;
- JSON mal formado en L: lectura de reserva por filas.

La ronda 1 está guardada en `qwen-round1`. En la ronda 2: L 0, L+ECHO 1 (verificada) y C 1
tareas resueltas.

**DeepSeek, prueba de coste** (5 tareas de entrenamiento, `lab/arc2/dev-ds-probe`):
- aciertos: L 3/5, L+ECHO 5/5 (verificadas) y C 5/5;
- razona ~7000–9000 tokens por llamada: ~0,055 $ por tarea de evaluación, ≈3,3 $ para 60.

**Enmienda previa al examen, prevista en el contrato:** DeepSeek pasa a **30 tareas**, las 30
primeras de las 60 por orden de semilla (`lab/arc2/exam-v1/deepseek-30.txt`). Límite de 12 000
tokens igual en los tres brazos; una respuesta que lo agote cuenta como fallo.

**Arnés congelado:** `lab/arc2/exam-v1/arc2_bench-v1.py`, sha256 `e33c3d238f14b24dc4eec66432ba280003c72aa2570ec70eb37fc26618e366fc`.

**Enmienda de presupuesto durante el examen (orden de Nav, 2026-09-25: «quiero que complete
arc-agi-2 al 100 %»; saldo de 2,10 $):**
- el suelo de crédito baja de 0,60 $ a **0,05 $** y el tope de DeepSeek sube a 3,5 $, para
  terminar las 450 partidas;
- **no cambia ningún umbral, brazo ni tarea**; las partidas ya hechas se conservan y solo se
  juegan las que faltan;
- el suelo se comprueba antes de cada tarea, así que ninguna llamada falla por falta de saldo.
