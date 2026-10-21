# ECHO RSI 1 contrato privado de automejora

1 de octubre de 2026. Nav autoriza preparar el experimento y ejecutarlo
después de PROBE2. Esta primera condición utiliza el GGUF Qwen3 4B Instruct
existente, CPU y **0 euros de servicios externos**. ECHO-5.5 es un objetivo
posterior; el banco no acredita vida subjetiva ni capacidad general frontier.

## Preguntas y alcance

¿Conservar composiciones verificadas y prioridades aprendidas mejora la
resolución de nuevos puzzles? ¿Ese estado mejora la productividad de un
segundo ciclo de investigación con el mismo neocórtex y presupuesto?

Se reutilizan `seed.learn.Library`, `solve`, `prior_from` y las primitivas de
`seed.dsl`. La condición es **evolución de biblioteca ECHO-SEED en un lenguaje
cerrado**. No reescribe Python ni el núcleo situado. No crea otro bus ni
enciende el córtex de NEXUS-0. No se presenta como el examen de toda la
arquitectura ECHO-4.5, ni como resultado ARC, ni como cierre de S6.

## Modelo y presupuestos congelados

La preparación guarda SHA-256 del GGUF y `llama-cli`, runtime Python 3.12,
fuentes, configuración y archivo de fuentes. Se verifica el GGUF otra vez
antes de ejecutar. El modelo no aprende pesos: las versiones sucesivas
cambian biblioteca y prioridades verificadas, manteniendo ese modelo fijo.

- Tres réplicas independientes: 311, 719, 1201.
- Cinco generaciones por brazo, un candidato por generación.
- Un worker; llama-cli usa cuatro threads, CPU y `-ngl 0`.
- 60 expansiones por tarea, profundidad máxima 4.
- Propuestas: dos o tres pasos del vocabulario original completo S0 sin argumentos.
- Máximo 57 llamadas locales: 45 del desarrollo y 12 del ensayo de investigación.
- 384 tokens de salida, contexto 4096, timeout de 600 s por llamada.
- Ocho horas de límite de pared por ejecución; interrupciones conservan recibos.
- Cero API, alquiler de GPU o reservas de pago. Las llamadas fallidas consumen
  presupuesto y no se reintentan automáticamente.

Son **techos comunes de oportunidades, búsqueda y generación**, no cómputo
real idéntico: los brazos sin modelo gastarán menos. Se informan las llamadas,
expansiones y tiempos efectivos. La versión API requiere otra condición con
modelo, precios, créditos y límite monetario reales fijados antes de inferir.

## Los cinco brazos

| Brazo | Qué conserva y qué hace |
|---|---|
| SEMILLA (`frozen`) | Biblioteca inicial y búsqueda simbólica, sin propuestas |
| ALEATORIO (`random`) | Una composición aleatoria por generación; mismos criterios de aceptación |
| LLM SOLO (`llm_only`) | Solicitud genérica fija, macros aceptadas acumuladas y aplicación directa verificada contra demostraciones; sin búsqueda simbólica ni selector adaptativo ECHO |
| ECHO SIN ACUMULACIÓN (`echo_reset`) | Búsqueda, fallos observados, solicitud adaptativa y verificación; biblioteca y prior se reinician antes de cada generación |
| ECHO RECURSIVO (`echo_recursive`) | Mismo ejecutor que SIN ACUMULACIÓN, conservando biblioteca y prior entre generaciones |

LLM SOLO significa un ayudante que propone una regla reutilizable por lote,
no un modelo con llamadas ilimitadas por tarea. No puede atribuirse al
selector una ventaja obtenida exclusivamente por la búsqueda: el contraste
principal de acumulación es RECURSIVO frente a SIN ACUMULACIÓN.

## Datos y separación del evaluador

Banco sintético nuevo: seis familias de composición entre recorte, simetría,
rotación, escalado, selección del mayor objeto, gravedad y repetición. Los ejemplos usan grids con colores 0–3,
objetos interiores y borde vacío. Cada tarea entrega tres demostraciones y
un input de prueba. La receta y el output de prueba no se envían al modelo
ni a `solve`. **No se utilizan archivos ARC, A/B de S6 ni soluciones PROBE.**

Por réplica: 12 tareas ancla, 12 nuevas por generación, 48 finales y 12 del
ensayo de productividad. Las particiones tienen semillas separadas. Las
familias finales son conocidas pero las rejillas son nuevas: se mide
transferencia dentro de estas familias, no generalización a familias inéditas.

El verificador observa respuestas privadas de desarrollo para aceptar o
rechazar; la solicitud solo usa demostraciones públicas. Una macro pasa
si resuelve al menos dos tareas nuevas y no pierde ningún acierto anterior
en todas las tareas de desarrollo vistas y las anclas. Se exige replay
canónico idéntico de todas ellas. Actualizar el prior también exige conservar
esos aciertos. No se rebaja el umbral después de resultados rojos.

Todas las bibliotecas finales se sellan antes de medir la primera tarea
final. Después se puntúan también los snapshots de G1–G5 para la gráfica:
ninguna respuesta final vuelve al modelo ni cambia las generaciones.

## Examen separado del investigador

En las mismas 12 tareas nuevas, se comparan dos condiciones por réplica:
biblioteca fresca y copia de la biblioteca recursiva final. Ambas usan el
mismo modelo, dos propuestas y el mismo verificador. Se miden nuevas mejoras
aceptadas por llamada y tiempo del modelo. Las dos llamadas de cada condición
pueden incorporar su propia primera mejora; no alteran el candidato final.

Esto mide **productividad al añadir más composiciones dentro de esta gramática**.
No mide inventar arquitecturas o entrenar LLMs. El ensayo es pequeño, y su
incertidumbre se declara; no equivale a una explosión de inteligencia.

## Criterios fijados antes

`capability_green`: RECURSIVO supera al mejor de los otros cuatro brazos en
**al menos 3/48 tareas (6,25 puntos porcentuales)**, en cada una de las tres
réplicas, con replay final idéntico. Se publican diferencias por tarea,
familia y réplica, aciertos exactos, llamadas, expansiones y coste.

`successive_improvements`: al menos dos promociones de biblioteca recursiva
en cada réplica, comprobadas sin regresiones. `research_green`: más mejoras
aceptadas por llamada desde el estado retenido que desde el fresco en cada
réplica. `RSI1_green` requiere los tres. Una mejora de resolución sin mejora
de productividad no permite declarar ese cierre.

Un replay distinto, una fuente/peso alterado, fallo de proceso o violación
de presupuesto detiene el instrumento como `BLOCKED`; no es un resultado
científico negativo. Propuestas inválidas y duplicadas sí son rechazos
registrados. Una medición válida sin ventaja se informa roja.

## Ejecución posterior a PROBE2

`seed/rsi1_queue.py` espera DONE de PROBE2, 874 cribados, 88 replays,
cinco comprobaciones de solidez positivas, replays completos de los
supervivientes verificados y presupuesto dentro de 14.544. Comprueba además
la integridad congelada de PROBE2 sin cambiar sus fuentes. Si se detiene
PROBE2 por error, RSI no arranca. Su resultado puede ser rojo o parcialmente
verificado por límite de supervivientes: terminar ese sondeo no exige verde.

Directorio privado: `lab/research/echo-rsi1-20261001/`, modo 0700. Solicitudes,
salidas y veredictos son observaciones reales. No se genera monólogo interno.
El resultado incluye `S6_green: false` siempre. No se publica en la web.

Comandos con el Python congelado:

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.rsi1 prepare --model /home/roger/models/qwen3-4b-instruct-2507/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -u -m seed.rsi1_queue
```

Estado: `status.json` y `queue-status.json`. Resultados: `result.json`,
`research.json`, snapshots por generación, respuestas por llamada y
`generation-scores.svg`. La gráfica es una media de medidas sintéticas;
los datos individuales acompañan al SVG y no se sustituyen por la media.

## Límites de la primera condición

El lenguaje de composiciones acota lo que puede mejorar y el verificador
solo protege las tareas declaradas. Se ejecutará la inferencia local por
primera vez tras PROBE2: los tests de ahora comprueban custodia, parada,
privacidad de outputs, DSL, replay y presupuesto, no calidad del modelo.
Si el banco está saturado, se registra el techo y se diseña otra condición
antes de medirla; no se cambia este contrato durante la ejecución.

Antes de congelar se probó un instrumento simple de seis rejillas, distinto
de las cohortes: las transformaciones geométricas simples daban 6/6 y no
ofrecían margen útil. Se sustituyeron por composiciones con objetos y
gravedad y se amplió la base al vocabulario S0 completo. No se debilita el
solver para fabricar una ventaja. Esta calibración de diseño se conserva
separada del resultado científico y no usa el examen final.

La versión posterior sobre problemas de programación, relaciones más
complejas o ARC necesitará corpus nuevo y contrato propio. Aumentar GPU,
número de pesos o agentes no se contará como mejora sin controles de coste
y capacidad. La fecha objetivo de ECHO-5.5 no cambia esos criterios.
