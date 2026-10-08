# ECHO-4.5 · 500k unidades de capacidad, alcance y diagnóstico

30 septiembre 2026. Experimento de desarrollo **CAPACITY-500K**, separado de
NEXUS-0, de las fuentes congeladas de S6-B11 y de los exámenes ARC.

## Qué se añadió

`seed/kenyon_capacity.py` ofrece un banco asociativo de **500.000 unidades
direccionables**, un byte de peso entrenable por unidad (500.000 bytes). Activa
solo un subconjunto por tarea. Extrae rasgos de las parejas públicas de
demostración —forma, colores, objetos y concordancia geométrica— y aprende
prioridades de familias DSL únicamente de programas que reproducen **todos**
los ejemplos. `guided_library()` conecta esa prioridad con `Library.guide`,
interfaz ya existente. La verificación del programa y la respuesta final siguen
en el solver. Está apagado por defecto; no toca S6-B11 ni NEXUS-0.

No son 500.000 neuronas LIF biológicas ni 500.000 parámetros de un LLM. Son
pesos enteros de una memoria dispersa. La rama ya existente de 512 LIF + 128
Adaptive-LIF es principalmente perceptiva/observable; no genera las reglas ARC
ni las reparaciones de S6. Contar sus 640 unidades como si fueran toda la
capacidad cognitiva confunde módulos diferentes. Qwen 7B tiene sus propios
pesos fijos; este cambio no los entrena.

## Primera medición, limitada

`PYTHONPATH=.. python3 -m echoai.seed.kenyon_bench`, desde el directorio padre:
80 tareas sintéticas de entrenamiento, 40 distintas de prueba; cuatro
transformaciones geométricas. Mismo extractor y datos, solo cambia la capacidad.

| Capacidad | Familia correcta top-1 | Pesos no cero | Memoria de pesos |
|---:|---:|---:|---:|
| 640 | 33/40 | 266 | 640 B |
| 500.000 | 40/40 | 344 | 500.000 B |

El benchmark mide **clasificar una primitiva en un juguete sintético**. No mide
salidas ARC, composición, generalización fuera de distribución ni S6. Solo 344
pesos del banco grande quedaron no cero: la capacidad adicional apenas se ha
usado. Más tamaño sin ejemplos, abstracciones y una tarea de entrenamiento
adecuada no implica más inteligencia.

## Por qué S6 no se arregla contando neuronas

El cuello de botella observado en S6-B10 es distinto: sus 18 propuestas
mejoraban niveles en desarrollo, pero todas empeoraban la eficiencia de una
partida protegida; fallaban V4. En B7 se aceptó una mejora ECHO, pero empató
con FIJO. B9/B10 también expusieron propuestas repetidas o poco diversas.
S6 compara **qué evidencia pide el agente, qué repara el modelo y si el
verificador conserva rendimiento**. Un banco de rejillas no resuelve ninguna de
esas tres condiciones sin una conexión causal demostrada en un contrato nuevo.
S6-B11 sigue su propia medición congelada.

## Lo que falta para mejorar ARC-AGI-1 de manera sustancial

1. Representar objetos, relaciones y programas jerárquicos que el DSL actual no
   puede expresar; las cuatro ablaciones de refinamiento en 12 tareas ARC-2 de
   entrenamiento obtuvieron 0 ajustes exactos.
2. Entrenar un prior sobre tareas sintéticas diversas y comparar **respuestas
   exactas** bajo presupuesto igual, con ablaciones de capacidad 640/500k,
   entrenamiento y guía apagada. Priorizar una primitiva no cuenta como acierto.
3. Generar y refinar varias hipótesis por tarea; verificar demostraciones,
   conservar diversidad y penalizar soluciones ambiguas. Una adaptación de
   pesos por tarea sería un experimento diferente, con datos y presupuesto
   explícitos.
4. Mantener separados ARC-1, ARC-2, ARC-3 y S6. La última medición local ARC-1
   fue 31/400; ARC-2, 0/120; ARC-3, 11/112. No extrapolar el juguete a esos
   porcentajes ni abrir reservas para escoger hiperparámetros.

## Evidencia externa y posible transferencia

- [Informe técnico ARC Prize 2024](https://arcprize.org/media/arc-prize-2024-technical-report.pdf): los grandes avances en ARC-1 combinaron síntesis guiada de programas y entrenamiento durante la prueba. No fue una simple ampliación de neuronas.
- [Resultados ARC Prize 2025](https://arcprize.org/blog/arc-prize-2025-results-analysis): NVARC logró 24 % en la evaluación privada ARC-2 con datos sintéticos, adaptación por tarea y un conjunto de modelos. Las condiciones y el coste son distintos a ECHO.
- [Li y colaboradores, inducción y transducción](https://arxiv.org/abs/2411.02272): ambos enfoques resuelven tipos de tarea diferentes. Sugiere evaluar un brazo generativo perceptivo además del DSL, sin sumarlos informalmente.
- [Tiny Recursive Models](https://arxiv.org/abs/2510.04871): el trabajo informa 45 % ARC-1 y 8 % ARC-2 con 7M parámetros y refinamiento recursivo. El mecanismo de entrenamiento y el cómputo importan más que una comparación de número de unidades.
- [OpenAI, aprendizaje de razonamiento](https://openai.com/index/learning-to-reason-with-llms/): documenta ganancias con aprendizaje por refuerzo y cómputo durante la prueba, pero no publica una arquitectura completa reproducible de o1. Tampoco Anthropic ha publicado los detalles completos de los modelos frontier; no podemos simplemente copiar sus pesos o método.

**Próxima puerta de decisión:** entrenamiento solo en datos permitidos, evaluación
de respuestas ARC-1 de desarrollo frente al mismo solver sin guía y con 640
unidades, coste y regresiones declarados. Solo si gana ahí merece promoción a
un contrato nuevo; no se altera el contrato S6-B11 en curso.
