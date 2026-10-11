# Antecedentes experimentales para las mejoras de ECHO-5

11 de octubre de 2026. Revisión bibliográfica dirigida a los mecanismos del
[diagnóstico local](REMEDIATION-AND-TRANSFER-20261011.md). Se consultaron fuentes
primarias y secciones experimentales accesibles; no se reprodujeron sus
experimentos. Este documento propone adaptaciones, no acredita mejoras nuevas
de ECHO ni altera la campaña activa o sus umbrales. S6 permanece aplazado hasta
después de 5.5.

«Comprobado» significa aquí resultados publicados bajo un protocolo concreto.
Debe distinguirse de una réplica independiente y de una garantía matemática
bajo supuestos. Estar en arXiv no equivale por sí solo a revisión por pares.
Las aplicaciones a ECHO que siguen son propuestas de ingeniería propias.

## 1. Active Neural SLAM: aislar exploración y planificación

Chaplot et al., ICLR 2020, combinan mapa aprendido, selección de metas y
planificación analítica. La tabla 2 compara el sistema con una variante que
sustituye sólo la política global por exploración de frontera cercana. En
escenas grandes de Gibson, la cobertura pasa de 78,2 % a 86,2 %; en pequeñas,
98,2 % frente a 98,3 %. Son porcentajes de superficie explorada, no misiones
resueltas. También evalúan transferencia de Gibson a Matterport. El entrenamiento
usa diez millones de fotogramas: no se presupone una réplica barata.
[Artículo y tablas 1–2](https://arxiv.org/pdf/2004.05155).
[Código de los autores](https://github.com/devendrachaplot/Neural-SLAM).

**Adaptación propuesta:** conservar parser, memoria, planificación, acciones y
manipulación de `sandbox.ObservationActor`; variar únicamente `_explore`.
Comparar ECHO, frontera cercana y frontera aleatoria sembrada en mapas de
distinta escala y topología. Medir éxito de misión además de cobertura y coste.
Esto no convierte el actual mapa simbólico en SLAM visual ni valida percepción
desde imágenes. La hipótesis de que los mapas pequeños ocultan diferencias
debe comprobarse con estratos registrados antes de confirmar.

## 2. ARGA: representación alternativa y búsqueda sobre objetos

Xu, Khalil y Sanner, AAAI 2023, combinan abstracciones de grafos, DSL relacional,
restricciones y búsqueda. Resuelven 57/160 tareas de un subconjunto elegido de
ARC centrado en objetos; el comparador resuelve 64/160. No es una puntuación
sobre todo ARC. La ablación sin restricciones resuelve 55 y explora más nodos.
Menos nodos tampoco implica menos segundos: la tabla 4 informa tiempos medios
de 178,66 s para ARGA y 77,08 s para el comparador, sobre sus respectivos casos
resueltos, que además difieren. No es una comparación emparejada de velocidad.
[Artículo, tablas 4–5](https://ssanner.github.io/papers/aaai23_arga.pdf).
[Publicación](https://ojs.aaai.org/index.php/AAAI/article/view/25527).
[Código de los autores](https://github.com/khalil-research/ARGA-AAAI23).

**Adaptación propuesta:** cuando la autopsia muestre pérdida de entidades,
comparar unas pocas segmentaciones tipadas y relaciones. Registrar su coste,
ambigüedad y contribución individual. Mantener igual buscador al evaluar
representación; cambiar ambos juntos impediría atribuir la mejora. Coincidir
en demostraciones no prueba equivalencia de programas en entradas nuevas.

## 3. Popper: convertir fallos en restricciones útiles

Cropper y Morel, Machine Learning 2021, estudian un ciclo de generar, probar y
restringir programas lógicos. Los fallos permiten excluir generalizaciones o
especializaciones bajo su formalismo. Sus experimentos abarcan juegos de
juguete, estrategias robóticas y transformaciones de listas, con ventajas en
precisión y tiempo frente a otros sistemas de programación lógica inductiva.
[Prepublicación](https://arxiv.org/abs/2005.02259).
[Registro y resumen de la publicación revisada](https://ora.ox.ac.uk/objects/uuid%3A56baa899-b0ca-47bf-9557-6a7c3f2718b4).

**Adaptación propuesta:** `solver.py` podría conservar restricciones respaldadas
por contraejemplos de desarrollo, además del resultado individual. Primero
validar la poda contra enumeración exhaustiva en problemas pequeños: no debe
eliminar ninguna solución admisible. Las garantías para programas lógicos no
se trasladan automáticamente al DSL de rejillas. Un fallo aislado no autoriza
a descartar una familia completa; cada regla de poda necesita justificación
semántica. El testigo conocido permanece fuera del buscador evaluado.

## 4. PHS: medir el coste de encontrar una solución

Orseau y Lelis, 2021, combinan política y heurística en Policy-Guided Heuristic
Search. Presentan cotas bajo supuestos explícitos y comparaciones en Sokoban,
The Witness y sliding-tile. En la tabla 1, PHS* resuelve 1.000/1.000 casos de
Sokoban frente a 914 de búsqueda voraz. No domina cada métrica: otras variantes
producen caminos más cortos y Weighted A* gana en tiempo en sliding-tile.
El protocolo incluye siete días de entrenamiento por ejecución y redes
aprendidas. «Garantías» no significa éxito dentro de cualquier presupuesto.
[Artículo, secciones 3–5 y tabla 1](https://arxiv.org/html/2103.11505v1).

**Adaptación propuesta:** localizar primero dónde se descarta el prefijo de un
programa testigo en desarrollo. Comparar la búsqueda actual con una frontera
por prioridad que preserve alternativas, sobre el mismo DSL y presupuesto.
Registrar expansiones, memoria, coste de ordenar e inferencia, tiempo y éxito.
Una adaptación acotada o con poda adicional requiere analizar de nuevo sus
supuestos; no hereda automáticamente las cotas publicadas.

## 5. DreamCoder: aprender abstracciones y orientar la búsqueda

Ellis et al., PLDI 2021, evalúan seis dominios con problemas reservados. Separan
aprendizaje de biblioteca, guía neuronal y controles que memorizan programas
enteros. En LOGO y torres, el sistema conjunto se aproxima al 100 % de tareas
reservadas mientras las ablaciones citadas no superan el 60 %. Es evidencia
en esos dominios; no una cifra ARC. Reportan aproximadamente un día con
20–100 CPU para converger típicamente, por lo que el sistema entero no es una
incorporación trivial al portátil.
[Artículo, sección 5 y figura 7](https://people.csail.mit.edu/asolar/papers/EllisWNSMHCST21.pdf).
[arXiv](https://arxiv.org/abs/2006.08381).

**Adaptación propuesta:** distinguir recordar un programa de extraer una
función parametrizada reutilizable. Evaluar biblioteca adquirida, biblioteca
fija del mismo tamaño y memorización de programas completos. La guía aprendida
sería un factor posterior y separado. Los problemas soñados requieren un
ejecutor validado; no dan por sí mismos evidencia sobre mundos nuevos.

## 6. Stitch: hacer viable la extracción de bibliotecas

Bowers et al., POPL 2023, extraen funciones comunes de corpus de programas.
En sus pruebas de aprendizaje de bibliotecas, informan aceleraciones de
3–4 órdenes de magnitud y aproximadamente dos órdenes menos de memoria frente
al extractor deductivo de DreamCoder, con compresión comparable o mejor.
Se trata del extractor, no del agente completo. La sección 6.1 usa Stitch en
un hilo; la métrica principal de calidad es compresión, no éxito de tareas.
[Artículo, sección 6](https://arxiv.org/html/2211.16605v2).
[Código oficial](https://github.com/mlb2251/stitch).

**Adaptación propuesta:** piloto pequeño sobre programas verificados de
desarrollo, con traducción tipada y comprobación de equivalencia antes de
adquirir una abstracción. Medir si luego reduce búsqueda en tareas nuevas,
incluyendo extracción y validación. Penalizar tamaño de biblioteca y descartar
abstracciones que sólo memoricen una tarea. El beneficio sobre nuestro lenguaje
es una hipótesis; no se multiplicará su velocidad publicada por la de ECHO.

## 7. Go-Explore: conservar y recuperar progreso

Ecoffet et al., Nature 2021, obtienen resultados de exploración en Atari y una
tarea robótica simulada de recoger y colocar. Archivan estados prometedores,
vuelven a ellos y después exploran. Distinguen versiones que restauran el
simulador de variantes que aprenden a regresar, y contemplan robustificación
ante estocasticidad. Encontrar una trayectoria con restauración privilegiada
no demuestra ejecutarla de forma autónoma bajo ruido.
[Nature](https://www.nature.com/articles/s41586-020-03157-9).
[Versión accesible de los autores](https://arxiv.org/abs/2004.12919).

**Adaptación propuesta:** comparar un archivo pequeño de estados, recorridos
y ramas con la memoria actual, contando recuperación y exploración. En
simulación sólo usar snapshots si forman parte del contrato y están disponibles
para los controles. En ejecución física, volver exige acciones reales. No
atribuir al hijo el resultado del padre ni inferir estados no observados.

## 8. PAIRED y ACCEL: desafíos adaptados a lo que falta aprender

PAIRED (Dennis et al., NeurIPS 2020) usa la diferencia entre dos agentes para
orientar un generador hacia desafíos útiles. ACCEL (Parker-Holder et al.) edita
y conserva niveles según una estimación de regret y demuestra transferencia
en navegación parcialmente observable y control continuo. En MiniGrid, ACCEL
reporta unas 350 millones de acciones y cinco semillas; sus comparaciones
principales se organizan por actualizaciones del alumno. Esto no acredita
superioridad a igualdad de coste total para ECHO. Un fallo del alumno tampoco
demuestra que el entorno sea válido y resoluble.
[PAIRED](https://arxiv.org/abs/2012.02096).
[ACCEL, secciones 3–4](https://arxiv.org/html/2203.01302v3).

**Adaptación propuesta:** editar topología y dependencias de mundos, manteniendo
un testigo independiente de resolubilidad. Comparar currículo adaptativo y
aleatorio con todos los costes contabilizados, incluidos rechazos y selección.
El testigo valida el entorno, pero no se entrega al actor. La transferencia se
evalúa en otro generador congelado, separado del currículo adaptativo.

## 9. Replay prioritario: antecedente biológico, alcance distinto

Mattar y Daw, Nature Neuroscience 2018, proponen un modelo normativo de qué
experiencias conviene recordar según su efecto esperado en decisiones futuras.
Sus simulaciones relacionan patrones de replay con observaciones previas del
hipocampo. Es un modelo explicativo; no una prueba de que ECHO tenga el mismo
mecanismo cerebral o de que una prioridad aproximada garantice mejores planes.
[Artículo](https://www.nature.com/articles/s41593-018-0232-z).
[Texto de los autores](https://www.princeton.edu/~ndaw/md18.pdf).

**Adaptación propuesta:** comparar replay uniforme frente a prioridad estimada
por uso futuro y cambio de decisión, descontando el coste de estimarla. Mantener
el mismo número de simulaciones y evaluar retención y recuperación tras cambios.
No llamar a una reordenación de episodios «conciencia» ni «e-prop».

## Orden experimental recomendado

Las publicaciones ofrecen mecanismos y protocolos reutilizables; su combinación
no constituye una demostración nueva. Tras terminar la cadena vigente:

1. **Controles de exploración equivalentes**, inspirados en la ablación de
   Active Neural SLAM. Comenzar con misiones nativas, para no mezclar el problema
   de la semántica personalizada. Incluir tamaños y topologías prefijados.
2. **Autopsia de búsqueda con testigos sólo del evaluador**, antes de añadir
   operaciones: clasificar falta de representación, expresividad, poda,
   presupuesto y selección. Comparar una intervención cada vez de Popper/PHS;
   aplicar ideas de ARGA si se demuestra pérdida de objetos o relaciones.
3. **Abstracciones reutilizables pequeñas**, tomando DreamCoder como protocolo
   de controles y Stitch como posible extractor. Medir utilidad posterior,
   no únicamente compresión o ahorro en repetir tareas conocidas.
4. **Currículo con generación independiente y replay**, tras aislar los
   mecanismos previos. Go-Explore y PAIRED/ACCEL son antecedentes distintos;
   archivo de estados, prioridad de memoria y dificultad adaptativa tendrán
   ablaciones separadas.

Cada piloto sirve para estimar coste, variabilidad y tamaño de confirmación.
Fijar de antemano margen práctico y métricas, usar pares y resultados por
familia, conservar regresiones y negativos, y no reutilizar como prueba ciega
las tareas que hayan orientado el diseño. No se promete un porcentaje de
mejora ni se cambia retroactivamente el contrato de cierre de ECHO-5.

El primer conjunto de adaptaciones simbólicas parece viable para un prototipo
pequeño en CPU, pero su coste se medirá. Replicar íntegramente los agentes
visuales o campañas de RL citados es un trabajo y presupuesto diferentes.
