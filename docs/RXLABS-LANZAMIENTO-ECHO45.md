# RxLabs presenta ECHO · lanzamiento (25 de septiembre de 2026)

Página diseñada (Artifact privado): https://claude.ai/artifact/1PmboFx7ZMvFKpNuEscHUV
Marcas: RxLabs («Rx», R mayúscula y x minúscula, en blanco sobre negro) y el logo de echoAI.

## La IA que no afirma lo que no ha comprobado

ECHO es un agente de dos relojes. Un **núcleo rápido de enteros** percibe, recuerda, predice,
decide y aprende, y funciona **con el modelo de lenguaje apagado**. El reloj lento, el córtex, que
puede ser cualquier modelo de lenguaje, solo **propone**. ECHO decide qué es un hecho y qué acción
se permite.

> HECHO ∈ {VERIFICADO, DESCONOCIDO}. Una hipótesis nunca se escribe como hecho. Si no hay evidencia
> comprobada, ECHO dice «no lo sé».

## 1 · Lo que ECHO-4 ya hace, medido y auditado

Cada prueba tuvo sus umbrales escritos antes del examen, con muestras selladas y una auditoría que
reconstruye los números sin volver a llamar a ningún modelo. Publicamos verdes y rojos.

| Prueba | Resultado | Veredicto |
|---|---|---|
| **SimpleQA** (200 preguntas de hechos) | Con Claude Sonnet 5, DeepSeek V4.1 Flash, GPT-5.4 mini y Qwen3-30B, ECHO reduce las respuestas incorrectas entre un **81 y un 87 %** frente al modelo solo y **sube la precisión en los cuatro**. A cambio responde menos: el F-score baja en 3 de los 4. | VERDE |
| **ARC-AGI-2** (puzles de rejillas) | Qwen solo envió **105** respuestas incorrectas; con ECHO, **0**. Pero en aciertos, DeepSeek con ECHO (6,7 %) empató con un control que prueba más programas sin verificar: no demostramos que verificar sume aciertos. | ROJO |
| **ARC-AGI-3** (juegos sin instrucciones) | Sin modelo de lenguaje, ECHO completa **13 de 112** niveles, frente a **2** del azar. La puntuación oficial, que premia hacerlo con tan pocas acciones como un humano, es de solo **0,07/100** (corregida: antes publicamos 1). | VERDE en niveles |
| **Experimentos de ECHO-4** | BOUNDARY, SITUATE, CONTINUITY e INTEGRATE, en verde y auditados. Son resultados funcionales, no una prueba de conciencia. | VERDE |

La release **ECHO-4 4.0.0rc2** se descarga en https://www.rxlabs.org/echoai. Los resultados
completos, con gráficas, están en https://www.rxlabs.org/articulos/echo4-benchmarks-resultados.

## 2 · ECHO-4.5: lo que será capaz de hacer si todo sale verde (objetivos, no logros)

ECHO-4.5 parte de una **semilla sin preentrenar** que se clona en sandboxes y aprende en ellas:
- **fase despierta:** busca programas y guarda como hecho solo lo que reproduce todos los ejemplos;
- **fase de sueño:** convierte en **conceptos nuevos** lo que se repite en tareas distintas.

| Fase | Qué | Estado |
|---|---|---|
| S0 | Semilla, sandboxes clonables con diario encadenado, gimnasio de 1009 tareas con las evaluaciones selladas | HECHO |
| S1 | Ver las rejillas como objetos: de 15 a 21 tareas reservadas resueltas (+40 %), sin entrenar | HECHO |
| S2 | Aprender mejor: conceptos con parámetros, intuición sobre qué probar primero y evolución entre clones | EN CURSO |
| S3 | Ver los juegos como objetos, con reglas de acción verificadas e imaginar caminos. Pista medida: ECHO descubre solo cuál es su personaje, porque es lo que se mueve cuando él actúa, en 5 de 5 juegos de desarrollo con teclas | OBJETIVO |
| S4 | Inferir la meta de un juego y planificar hacia ella con pocas acciones | OBJETIVO |
| S5 | ARC3-GYM: un simulador propio de juegos por turnos | OBJETIVO |
| EGO-MEMORIA-1 | Que la necesidad de documentar surja sola, que las memorias con valencia cambien su conducta y que dos clones idénticos acaben siendo dos yoes distintos. En desarrollo, M2, M3 y M4 salen en verde en 8 de 8 semillas. Es un yo funcional, no conciencia | OBJETIVO |

**Requisitos del examen:**
- **R1 (ARC-AGI-1) y R2 (ARC-AGI-2):** superar el 0 % y a la semilla sin entrenar.
- **R3 (ARC-AGI-3):** al menos el 20 % de los 112 niveles.
- **R4:** auditoría completa.

**Si sale verde**, sería la primera evidencia medida y auditada de que un sistema pequeño, en una
CPU normal y sin preentrenamiento masivo, adquiere abstracciones por su cuenta y las traslada a
situaciones nuevas. No significaría que ECHO entienda como una persona, que sea consciente ni que
sea una inteligencia general.

## 3 · Cómo lo vamos a medir

Mediremos ECHO-4.5 en **ARC-AGI-1, ARC-AGI-2 y ARC-AGI-3**, con el método de siempre:
- contrato con umbrales antes del examen;
- evaluaciones selladas por código;
- auditoría completa;
- rojos publicados.

Competimos como equipo **RxLabs** en **ARC Prize 2026** en Kaggle y presentaremos el enfoque en
el paper track. Partimos de casi cero: hoy el primero de la tabla de ARC-AGI-3 tiene ≈19,45 sobre
100, y ECHO, entre 0,07 y 0,34. Nuestro objetivo es aprender en público, subir en la tabla y
demostrar con ablaciones cuánto aporta ECHO. No prometemos ganar.

## 4 · Por qué: IA para robots que actúan en el mundo real

Nos apasiona hacer evolucionar la IA para la **robótica autónoma**:
- un robot no puede fiarse de un modelo que afirma lo que no sabe;
- necesita un núcleo que actúe, compruebe y aprenda de las consecuencias;
- ese núcleo tiene que correr en hardware pequeño y poderse auditar.

ECHO ya tiene esas piezas. Su núcleo es de enteros y corre en CPU, y ya ha volado drones en
simulación. En el futuro queremos llevar su cabeza de acciones a un coprocesador neuromórfico como
Akida, y a placas de borde para robots.

**Los problemas que queremos resolver:**
- **Una IA que no afirma lo que no sabe:** que «no lo sé» sea una respuesta válida y medida.
- **Robots que aprenden actuando y verificando**, en vez de creerse un modelo de lenguaje.
- **Sistemas pequeños, baratos y auditables** frente a modelos gigantes y opacos.
- **Agentes que saben qué depende de ellos**, la base de un robot seguro.
- **Medición abierta, mantenida por la comunidad.**

## 5 · Participa

ECHO-4 lo mantiene la comunidad. Descárgalo y haz las pruebas que aún faltan:
- Humanity's Last Exam;
- MMLU;
- FrontierScience;
- ARC-AGI-2 y ARC-AGI-3 con modelos fuertes;
- SWE-bench.

Usa nuestro método y publica tu resultado con nosotros, también si sale rojo.

- Descargar ECHO-4: https://www.rxlabs.org/echoai
- Resultados: https://www.rxlabs.org/articulos/echo4-benchmarks-resultados
- Contacto: https://www.rxlabs.org/contact

*Todas las cifras proceden de exámenes con contrato previo y auditoría. Lo planificado se describe
como objetivo. Los resultados sobre el «yo» de ECHO son funcionales y no demuestran conciencia ni
experiencia subjetiva. ECHO no se presenta como una inteligencia general.*
