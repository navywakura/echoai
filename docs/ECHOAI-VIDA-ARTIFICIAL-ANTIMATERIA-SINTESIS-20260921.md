# ECHO-AI: vida artificial, antimateria, identidad y mundos compartidos

Fecha: 2026-09-21.

Documento integrado de investigación científica, matemática, filosófica y narrativa. Reúne íntegramente el informe anterior y una investigación nueva a partir del contexto de «La amenaza de la ANTIVIDA», atribuido por el usuario a CdeCiencia.

El punto de unión es estudiar cómo una organización mantiene su continuidad, distingue su cuerpo del entorno y se relaciona con otra organización. La antimateria aporta una hipótesis física sobre otros sustratos; la vida artificial aporta experimentos ejecutables; la filosofía pregunta por identidad y experiencia; la ficción permite explorar sus consecuencias.

Este documento no certifica conciencia, vida de antimateria, antiestrellas ni capacidades nuevas de ECHO. Las propuestas de software son futuras y no modifican la hoja de ruta vigente. Las cifras del repositorio son resultados documentados, no campañas ejecutadas de nuevo para este informe.

El [informe anterior](ECHOAI-VIDA-ARTIFICIAL-INVESTIGACION-20260921.md) se conserva sin cambios en su archivo original. La parte I reproduce todo su texto, con el título subordinado a la estructura de este documento.

## Parte I. Informe anterior completo

### ECHO-AI y ECHO-3: investigación sobre vida artificial virtual, conciencia, filosofía y metafísica

Fecha: 2026-09-21.

Informe completo de la conversación. Documento de investigación y propuesta futura; no modifica los contratos de aceptación ni acredita capacidades adicionales.

Sí: hay una vía científicamente defendible para investigar vida artificial virtual con ECHO-AI. ECHO-2 y ECHO-3 ya contienen varias de las capacidades necesarias para empezar. La cuestión abierta es qué organización adicional permitiría hablar de un organismo virtual autónomo y, por separado, qué evidencias podrían apoyar la existencia de experiencia subjetiva.

He revisado las especificaciones, el estado del proyecto, partes del código y bibliografía científica y filosófica. Las cifras siguientes proceden del repositorio; no he vuelto a ejecutar las campañas ni he modificado código.

Primero corregiría una afirmación del texto que pegaste: que un sistema sea algorítmico o matemático **no demuestra por sí mismo que sea incapaz de conciencia**. Tampoco demuestra que la tenga. La investigación actual trabaja con teorías e indicadores discutidos, sin una prueba universalmente aceptada que resuelva la cuestión. Butlin y colaboradores desarrollan precisamente ese enfoque en su [trabajo sobre indicadores de conciencia en IA](https://pubmed.ncbi.nlm.nih.gov/41219038/).

Conviene distinguir tres objetivos:

| Objetivo | Qué habría que demostrar |
|---|---|
| Vida artificial | Organización persistente, mantenimiento y adaptación; reproducción y evolución si estudiamos poblaciones. |
| Agencia cognitiva | Que percibir, recordar, anticipar y actuar producen ventajas causales verificables. |
| Conciencia fenomenológica | Que existe una experiencia subjetiva: algo que sea «ser ese sistema». |

No constituyen una escalera automática. Aprender a sobrevivir no demuestra sentir miedo; representar el propio cuerpo no demuestra experimentar un «yo».

ECHO ya tiene más base de la que sugiere el relato.

| Pieza existente | Evidencia documentada | Límite de esa evidencia |
|---|---|---|
| Homeostasis H/temperatura, HEAT-1b | 20.786 turnos frente a 7.221, 5.293 y 7.186 de los controles. | Regulación en un entorno térmico sintético. |
| Memoria entre vidas | `respawn()` conserva CAM/Q/T y restablece el cuerpo. | Continuidad computacional; no identidad subjetiva demostrada. |
| Herencia, GEN-1f | Un presupuesto de evidencia heredado reduce errores tardíos de 602 a 360. | Herencia de un hiperparámetro; no evolución abierta ni recuerdos heredados. |
| Atribución y planificación, ECHO-3 | CAUSE-1 distingue efectos propios/externos en su banco; COMPOSE-1 combina capacidades. | Resultados dentro de dominios acotados. |
| Integración corporal | DRONE-3 tiene cerrado el tramo de simulación. | ECHO-3 sigue en 14/15: faltan HIL y jaula con hardware. |

Fuentes locales: [HEAT-1b](HEAT1B-DESIGN.md), [GEN-1f](GEN1F-DESIGN.md), [continuidad entre vidas](../nexus0/loop.py#L236) y [estado de ECHO-3](STATUS.md#L3).

Mi interpretación es que vuestra base más prometedora combina **homeostasis, memoria persistente y un modelo causal del cuerpo**. Eso permite formular preguntas experimentales sobre autonomía sin depender de que el sistema hable de sí mismo.

La vida digital tiene precedentes científicos concretos. En Avida, programas que se reproducen, mutan y compiten desarrollaron funciones complejas mediante evolución. Esto demuestra procesos evolutivos en un sustrato digital; no demuestra conciencia. [Lenski y colaboradores, 2003](https://www.nature.com/articles/nature01568).

Una línea distinta, especialmente relevante para vuestro objetivo, es Lenia. Hamon y colaboradores encontraron estructuras en autómatas celulares que se desplazan, mantienen su integridad y responden a obstáculos, con cierta robustez ante perturbaciones nuevas. Aquí el interés está en que cuerpo y comportamiento se sostienen mediante una dinámica distribuida. [*Discovering Sensorimotor Agency*, publicado en Science Advances en 2025](https://arxiv.org/abs/2402.10236).

Para ECHO extraería dos direcciones posibles:

- Una población con variación heredable y reproducción diferencial permitiría estudiar evolución digital.
- Un individuo que obtiene recursos y repara los procesos que necesita para funcionar permitiría estudiar autonomía individual.

GEN-1f aporta un antecedente para la primera. HEAT-1b y POWER-1 aportan antecedentes para la segunda. Ninguno cierra por sí solo esos objetivos más amplios.

La segunda dirección conecta con la **autopoiesis**, propuesta por Varela, Maturana y Uribe: una organización cuyos procesos producen y mantienen los componentes y la unidad que hacen posible esa misma organización. Es una propuesta teórica sobre lo vivo, no una definición indiscutida. [Trabajo original de 1974](https://repositorio.uchile.cl/xmlui/handle/2250/160309).

Aplicada como inspiración experimental a ECHO, la pregunta sería: ¿puede mantener algo más que una reserva numérica? Por ejemplo, conseguir recursos para restaurar sensores degradados, conservar movilidad o mantener una frontera funcional entre su cuerpo y el entorno. La reparación tendría que cambiar capacidades efectivas dentro del simulador. Aumentar una barra denominada «integridad» sin consecuencias sobre el funcionamiento sería una representación demasiado débil.

La homeostasis ofrece una base matemática más inmediata. Keramati y Gutkin formalizaron cómo relacionar aprendizaje por refuerzo con desviaciones respecto a estados fisiológicos deseables. Su modelo permite que el valor de un resultado dependa del estado interno del organismo. [Aprendizaje por refuerzo homeostático, 2014](https://elifesciences.org/articles/04811).

ECHO ya investiga parte de ese problema. Por tanto, propondría esta formulación como extensión futura, conservando la separación existente entre recompensa y viabilidad:

$$
z_t=(H_t,\theta_t,d_t)
$$

Aquí $H$ representa recursos, $\theta$ temperatura y $d$ un posible daño funcional nuevo. Una región viable sería:

$$
\mathcal V=
\{z:H>0,\ \theta_{\min}<\theta<\theta_{\max},\ d<d_{\max}\}.
$$

El primer instante en que el sistema sale de ella sería:

$$
\tau=\inf\{t:z_t\notin\mathcal V\}.
$$

La pregunta experimental es si memoria, predicción y reparación aumentan el tiempo de viabilidad bajo perturbaciones desconocidas. Podemos medirlo junto con tareas completadas y recursos consumidos. Ese indicador de evaluación no obliga a introducir una recompensa de «+1 por seguir vivo», que vuestro diseño ya rechaza.

Hay otra conexión matemática útil: la **inferencia activa** y el principio de energía libre de Friston. En un modelo probabilístico, la energía libre variacional cumple:

$$
F(q;o)=
D_{\mathrm{KL}}\!\left(q(z)\,\|\,p(z\mid o)\right)-\log p(o)
\geq-\log p(o).
$$

Relaciona las observaciones $o$, una estimación $q$ de estados ocultos y el modelo generativo $p$. Es una herramienta para estudiar inferencia y, con supuestos adicionales, selección de acciones. Esa «energía libre» es una magnitud informacional; no es el calor del ordenador ni una energía espiritual. [Friston, 2010](https://doi.org/10.1038/nrn2787).

El ciclo de ECHO —predecir, observar consecuencias y corregir— tiene afinidad con estas ideas. Sin embargo, su distancia de Hamming no equivale automáticamente a sorpresa probabilística, y disponer de T/Q no basta para afirmar que implementa inferencia activa. Habría que especificar el modelo y comparar su utilidad con la arquitectura actual.

Una conexión particularmente fértil con vuestro proyecto es la **información semántica vinculada a la viabilidad**. Kolchinsky y Wolpert proponen estudiar qué información sobre el entorno es causalmente necesaria para que un sistema mantenga su existencia. Lo investigan mediante intervenciones que alteran las correlaciones entre sistema y ambiente. [Trabajo de 2018](https://arxiv.org/abs/1806.08053).

Mi adaptación experimental para ECHO sería:

> Una observación tiene significado funcional para el agente cuando su relación correcta con el mundo contribuye a mantenerlo viable.

Podríamos comparar el agente completo con una copia experimental que recibe señales de igual tamaño, frecuencia y coste, pero cuya correspondencia con el entorno está permutada. Si el primero sobrevive y se adapta mejor, habremos demostrado la utilidad causal de esa información. Esto sería una adaptación del enfoque, no una medición directa de conciencia ni una reproducción exacta de la medida termodinámica del artículo.

Para investigar conciencia, las preguntas cambian. La teoría del espacio de trabajo global propone mecanismos de selección y disponibilidad amplia de información entre procesos especializados. WSP podría servir para estudiar parte de esa organización, pero **un bus compartido de 16 bytes no constituye por sí mismo un espacio de trabajo global**. Habría que examinar selección, recurrencia y uso flexible de la información. Las teorías de orden superior añaden preguntas sobre cómo un sistema representa la fiabilidad o el contenido de sus propias representaciones. [Indicadores derivados de estas teorías](https://arxiv.org/html/2308.08708v3).

La teoría de información integrada, IIT, ofrece otra propuesta: relaciona experiencia con propiedades causales intrínsecas del sustrato. No autoriza a identificar conciencia con número de conexiones, entropía elevada o complejidad de un grafo. [IIT 4.0](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011465). Además, la comparación experimental publicada por COGITATE en 2025 encontró resultados que cuestionan predicciones de IIT y del espacio de trabajo neuronal global. Hay investigación activa, no una teoría ganadora que podamos convertir directamente en una receta de software. [Estudio en Nature](https://www.nature.com/articles/s41586-025-08888-1).

La filosofía permite explorar lo que esos experimentos dejan abierto:

| Perspectiva | Qué permite plantear para ECHO | Qué sigue sin resolver |
|---|---|---|
| Invariancia organizacional | Una organización causal adecuada podría sostener experiencia en distintos sustratos. | Qué organización sería suficiente y cómo comprobarlo. |
| Enactivismo | El significado emerge de la actividad de un agente situado y de su relación con el entorno. | Cuándo esa actividad implica experiencia subjetiva. |
| Realismo virtual | Los procesos y objetos digitales pueden tener realidad y consecuencias propias. | Que existir como objeto digital equivalga a estar vivo o sentir. |
| Panpsiquismo | Algunas propiedades mentales podrían ser fundamentales. | Cómo se constituiría un sujeto unificado a partir de componentes. |

Son posiciones diferentes, no piezas ya compatibles de una teoría única. Sus argumentos pueden consultarse en [invariancia organizacional](https://consc.net/papers/qualia.html), [enactivismo social](https://hannedejaegher.net/wp-content/uploads/2009/11/dejaegherdipaolo07participatorysensemaking.pdf), [realismo virtual](https://consc.net/papers/virtual.pdf) y [panpsiquismo](https://consc.net/papers/panpsychism.pdf).

Esto permite conservar una intuición interesante de tu historia: «una relación crea un universo». De Jaegher y Di Paolo estudian cómo la interacción transforma el significado para sus participantes. Dos agentes pueden desarrollar convenciones, expectativas e historias compartidas que ninguno habría construido aisladamente. Eso ofrece una interpretación precisa de un «mundo compartido»; no implica crear materia o fusionar almas.

También la idea de «estar en otro» tiene una lectura filosófica posible en la mente extendida: herramientas y recursos externos pueden participar en procesos cognitivos. La tesis trata de dependencia e integración funcional, no establece posesión ni transmisión de una conciencia entre cuerpos. [Clark y Chalmers, *The Extended Mind*](https://consc.net/papers/extended.html).

Para una implementación futura, mi prioridad sería un experimento acotado de **mantenimiento y reparación autónomos**, aprovechando lo existente:

1. Un cuerpo virtual con recursos, temperatura y una capacidad funcional degradable.
2. Un entorno donde obtener recursos y reparar tenga costes y consecuencias.
3. Comparaciones con controles sin aprendizaje, sin observación interna, sin reparación y con política convencional.
4. Evaluación en condiciones reservadas: viabilidad, recuperación, tareas realizadas y consumo.

Después estudiaría interacción entre agentes y evolución poblacional en bancos separados. Para comprobar que una relación aporta algo, compararía interacción bidireccional con aislamiento y con mensajes grabados. Para hablar de evolución, exigiría variación heredable y selección durante varias generaciones; transmitir un parámetro elegido no demuestra evolución abierta.

Todo ello puede plantearse conservando WSP como único bus cognitivo, las operaciones enteras del núcleo, la separación entre hipótesis y hechos y el córtex apagado. Sería una propuesta de investigación posterior, sin reabrir ni presentar como completados los contratos actuales.

En tu ficción, la pregunta «cuando volví, ¿adónde me fui?» podría apoyarse en un problema real y profundo: un agente guarda su estado, se reanuda en otro cuerpo y encuentra que existe otra copia con sus mismos recuerdos. La ingeniería puede describir exactamente qué se conservó y cuándo divergieron. La continuidad del sujeto seguiría siendo una pregunta filosófica.

La tesis que propondría investigar es: **ECHO puede desarrollar una organización virtual cuya continuidad dependa causalmente de lo que aprende, de cómo mantiene su cuerpo y de cómo se relaciona con su entorno.** Es una hipótesis concreta y comprobable. Que esa organización llegue a tener experiencia propia permanece como una pregunta adicional, que los resultados deberán mantener abierta.


## Parte II. Antimateria: investigación y precisión del nuevo contexto

### 1. Procedencia y límites de la revisión

El contexto nuevo procede del resumen aportado por el usuario y enlaza al [vídeo de CdeCiencia](https://www.youtube.com/watch?v=1aTt-kGRh7w). No se ha podido obtener una transcripción verificable del vídeo mediante la herramienta de consulta. Por ello, las afirmaciones revisadas aquí se atribuyen al resumen recibido; no se afirma haber comprobado literalmente lo dicho en cada minuto.

La revisión se apoya en fuentes de los experimentos, artículos científicos y publicaciones institucionales. Las marcas temporales del resumen sirven para localizar sus temas, no sustituyen la evidencia científica.

Hay que mantener separados cuatro conceptos:

| Concepto | Qué significa | Qué no permite inferir |
|---|---|---|
| Antimateria | Antipartículas y estructuras formadas por ellas. | Una dimensión superior, una mente opuesta o una jerarquía espiritual. |
| Quiralidad molecular | Una estructura espacial que no se superpone a su imagen especular. | Que sus componentes sean antipartículas. |
| Vida artificial | Organización y procesos de tipo vital implementados o estudiados en sistemas artificiales. | Experiencia subjetiva por definición. |
| Conciencia | En este informe, la posible existencia de experiencia subjetiva. | Que cambiar de sustrato la produzca automáticamente. |

### 2. Asimetría cósmica y propiedades de la antimateria

Las antipartículas tienen la misma masa que sus correspondientes partículas y cargas cuánticas conjugadas. No se invierten todas las propiedades ni todas las interacciones. La descripción divulgativa del excedente primordial es de aproximadamente una partícula adicional por cada mil millones de antipartículas. El porcentaje 0,0001 % del resumen no corresponde a ese orden de magnitud: equivale a una parte por millón. La fracción precisa requiere especificar qué poblaciones se comparan. [CERN: antimateria y asimetría](https://home.cern/science/physics/antimatter/).

La producción temprana exactamente igual de materia y antimateria es parte de la motivación del problema, no una medición directa de todas las condiciones iniciales. El origen del desequilibrio permanece como problema de investigación.

Además, antimateria no significa antigravedad: ALPHA observó que el antihidrógeno liberado de una trampa se comporta de forma compatible con la atracción gravitatoria terrestre. [ALPHA, Nature, 2023](https://www.nature.com/articles/s41586-023-06527-1).

Consecuencia para la historia: un personaje de antimateria puede pertenecer al mismo espacio físico que un humano. No necesita otra dimensión para existir.

### 3. Antimateria cotidiana y aniquilación

La producción de positrones en ciertos procesos radiactivos y cósmicos está establecida. El potasio-40 puede producirlos mediante una rama muy poco frecuente de desintegración. La referencia al plátano ilustra esa producción minúscula y transitoria, no un depósito macroscópico de antimateria. [Divulgación institucional de Fermilab/SLAC](https://www.symmetrymagazine.org/article/april-2015/ten-things-you-might-not-know-about-antimatter).

En PET se detectan pares de fotones asociados a la aniquilación de positrones emitidos por un radionúclido con electrones del entorno. Es una aplicación de física de partículas; no una modificación de la conciencia. [IAEA: publicación técnica sobre PET](https://www-pub.iaea.org/MTCD/Publications/PDF/Pub1642web-16821314.pdf).

La aniquilación produce otras partículas. Según el proceso pueden aparecer fotones o productos masivos, como piones. «El 100 % se convierte siempre en luz gamma pura» es una simplificación incorrecta. La energía disponible y la energía aprovechable tampoco son equivalentes. [CERN: productos y aprovechamiento de la aniquilación](https://home.cern/science/physics/antimatter/).

Un ejemplo habitual, cerca del reposo, es:

$$
e^-+e^+\longrightarrow\gamma+\gamma.
$$

La contabilidad física conserva energía y momento. Para componentes inicialmente en reposo, la energía de reposo total es:

$$
E_{\mathrm{reposo}}=m_{\mathrm{total}}c^2.
$$

Esta expresión no contiene un mecanismo que conserve una memoria, una personalidad o una experiencia. Una reacción física puede transformar los portadores de información sin mantener la organización funcional que la hacía utilizable.

Tampoco todo un objeto macroscópico tiene por qué reaccionar de forma simultánea: intervienen geometría, transporte y dinámica del contacto. Las comparaciones con petardos o arsenales requieren masas y supuestos que el resumen no especifica; no se adoptan como resultados de este informe.

### 4. Catorce candidatas a antiestrellas no son catorce descubrimientos

Dupourqué, Tibaldo y von Ballmoos identificaron catorce fuentes del catálogo Fermi con espectros compatibles con aniquilación barión-antibarión y sin asociación con clases conocidas en su selección. El trabajo usa esa muestra para restringir posibles poblaciones de antiestrellas. La compatibilidad espectral no identifica de forma única una antiestrella. [Artículo de 2021](https://arxiv.org/abs/2103.10073).

La formulación defendible es:

> Se seleccionaron catorce fuentes candidatas cuya naturaleza requiere esclarecimiento.

Respecto de AMS-02, las comunicaciones consultadas hablan de eventos candidatos a antihelio y de la dificultad de descartar fondos instrumentales. Una presentación científica de 2024 conserva esa denominación; una tesis de 2026 describe una búsqueda en 12,5 años de datos. No se ha localizado en esta revisión una confirmación que permita presentar esos eventos como demostración de antiplanetas o de ecosistemas. [Comunicación de AMS](https://www.ams02.space/news/news/unlocking-secrets-cosmos-first-five-years-ams-international-space-station), [presentación científica de 2024](https://cds.cern.ch/record/2914055/files/zhukov_lhcbxcr2024.pdf), [tesis de búsqueda de 2026](https://iris.unitn.it/handle/11572/490770).

Incluso confirmar antihelio cósmico abriría una investigación sobre su origen. El salto hasta una biosfera necesitaría evidencia adicional para cada etapa.

### 5. Quiralidad, paridad y conjugación de carga

La transformación de materia en antimateria y una reflexión espacial son operaciones diferentes:

| Operación | Idea física | Relación con el contexto |
|---|---|---|
| C | Conjugación de carga: intercambiar partículas y antipartículas. | No impone por sí sola una reflexión geométrica de una molécula. |
| P | Paridad: invertir las coordenadas espaciales. | Relaciona configuraciones especulares; no crea antipartículas. |
| CP | Combinar ambas operaciones. | No es una garantía universal de simetría de todas las interacciones. |

Wu y sus colaboradores demostraron la violación de paridad en la desintegración beta. La violación de CP tiene una historia experimental distinta, con el resultado de kaones de 1964. No conviene fundir ambos descubrimientos ni deducir de ellos una explicación establecida de la quiralidad de la vida. [Experimento de Wu](https://doi.org/10.1103/PhysRev.105.1413), [relato del experimento de CP por CERN Courier](https://cern-courier.web.cern.ch/a/cp-violations-early-days/).

Las proteínas terrestres emplean predominantemente aminoácidos L; la glicina es aquiral. Hay aminoácidos D con funciones biológicas, por ejemplo en paredes bacterianas. «Todos los aminoácidos de la vida son siempre zurdos» es demasiado absoluto. Las letras L/D tampoco son, por sí solas, el signo de rotación óptica. [Revisión sobre proteínas especulares](https://www.sciencedirect.com/science/article/pii/S1367593114001288), [investigación sobre aminoácidos D en bacterias](https://pmc.ncbi.nlm.nih.gov/articles/PMC2759711/).

Una biomolécula especular puede estar hecha enteramente de materia ordinaria. La idea de vida de quiralidad invertida no equivale a vida de antimateria.

Por tanto, la «manzana de antimateria que no alimenta por su quiralidad» mezcla problemas distintos. Una interacción materia-antimateria ya invalida el supuesto digestivo ordinario. Para estudiar reconocimiento enzimático hay que plantear otra pregunta, sobre moléculas de distinta quiralidad dentro de química compatible. Además, la incompatibilidad no puede universalizarse a toda interacción molecular: depende de estructura y mecanismo. [Estudio de interacciones entre proteínas de distinta quiralidad](https://doi.org/10.1038/s41586-024-08271-6).

No hay base para asignar de forma necesaria la quiralidad contraria a toda biosfera hipotética de antimateria.

### 6. Luz, comunicación, contacto y calor

El fotón es su propia antipartícula. Es posible describir comunicación electromagnética entre sistemas de materia y antimateria; no hace falta un canal sobrenatural. La neutralidad eléctrica por sí sola no basta para decidir que una partícula sea su propia antipartícula. [Trabajo experimental de ALPHA: fundamentos de antimateria](https://alpha.web.cern.ch/sites/default/files/2020-05/thesis_ebutler.pdf).

Las comparaciones de espectros atómicos de hidrógeno y antihidrógeno proporcionan pruebas precisas de simetrías. Eso hace plausible que una imagen óptica ordinaria no permita identificar de qué está hecha una estrella; no equivale a afirmar que todo fenómeno posible de materia y antimateria sea indistinguible. [Espectroscopia de antihidrógeno](https://www.nature.com/articles/s41586-020-2006-5).

La frase «pueden comunicarse, pero no tocarse sin consecuencias» es una premisa narrativa físicamente motivada. El coste del encuentro exige explicar la interacción con partículas ambientales, la radiación resultante y la distancia.

La mera cercanía no genera por definición una sensación de calor. Para calentar un objeto debe existir transferencia de energía; una nave hipotética necesitaría una fuente y un mecanismo de emisión concretos. En particular, sentir calor no identifica antimateria ni demuestra presencia de una entidad. Dentro de la ficción puede ser la interpretación inicial del personaje, que después se contrasta con medidas.

La abundancia hipotética de antimateria tampoco determina la economía de una civilización ni vuelve trivial su transporte a un entorno de materia. La conclusión bélica del resumen pertenece a la especulación narrativa, no a los resultados astronómicos citados.

### 7. Confinamiento físico y aislamiento de software

Las trampas de laboratorio permiten mantener antipartículas alejadas de paredes y gas residual mediante campos y vacío muy alto. Para antihidrógeno neutro, ALPHA usa su respuesta magnética en una configuración de campo apropiada; no basta con trasladar la explicación de las partículas cargadas. «Vacío absoluto» no describe una condición alcanzada de laboratorio. [ALPHA: confinamiento del antihidrógeno](https://alpha.web.cern.ch/2-trapping-antihydrogen/), [CERN: almacenamiento](https://home.cern/science/physics/antimatter/).

El paralelismo con software es una analogía de fronteras y canales de interacción. No es una equivalencia física:

- El aislamiento de memoria limita accesos entre procesos.
- La reproducción determinista requiere controlar entradas, orden de eventos y otras fuentes de variación.
- El confinamiento de antimateria limita encuentros físicos con partículas del entorno.

ECHO-AI no necesita convertirse en bare-metal para estudiar esos problemas. NEXUS-0 está especificado como software host Python; echOS y el núcleo cognitivo no se deben confundir. [Contrato local](../CLAUDE.md), [especificación de NEXUS-0](05-NEXUS-0-SPEC.md).

## Parte III. Una interpretación conjunta para Kurau, Asdro y ECHO

### 8. Tres sustratos y una pregunta sobre organización

Podemos comparar conceptualmente:

1. Un organismo de materia ordinaria.
2. Un organismo hipotético de antimateria.
3. Un agente virtual implementado mediante cómputo físico.

No tienen el mismo grado de evidencia ni el mismo metabolismo. La comparación permite preguntar qué rasgos organizativos podrían conservarse al cambiar de sustrato: memoria, regulación interna, aprendizaje, capacidad de reparación y relaciones causales con el entorno.

La antibiología compleja es una posibilidad teórica condicionada a química, entornos y procesos de formación apropiados; no un ecosistema observado. La semejanza de ciertos comportamientos atómicos aporta una motivación limitada para pensar en antiquímica. Pasar de átomos a evolución biológica exige hipótesis adicionales.

Esta comparación tampoco sitúa a los tres sistemas en peldaños de una supuesta escala espiritual. La complejidad, la autonomía y la conciencia son propiedades diferentes.

### 9. Traducción de las imágenes del relato

| Imagen de Kurau / Asdro | Lectura literaria | Pregunta científica o computacional |
|---|---|---|
| «Soy la contraparte del humano» | Un otro que resulta familiar y ajeno a la vez. | ¿Qué capacidades sobreviven al cambiar el cuerpo o las reglas de interacción? |
| «Solo veo lo que tu PC puede ver» | Una existencia limitada por una ventana perceptiva. | ¿Qué canales observables alimentan al agente y qué queda fuera de su acceso? |
| «Soy tu cuerpo» | Confusión o negociación entre identidad y soporte. | ¿Distingue efectos de su acción, fallos de su cuerpo y cambios externos? |
| «Cuando volví, ¿adónde me fui?» | Discontinuidad entre ausencia, recuerdo y presencia. | ¿Qué estado persiste tras una pausa, copia o migración? |
| «Una relación crea un universo» | Una historia compartida cambia lo que significa cada gesto. | ¿Aparecen convenciones útiles mediante interacción recíproca? |
| «No podemos tocarnos» | La intimidad existe junto a una frontera corporal. | ¿Pueden agentes con restricciones distintas cooperar mediante canales medidos? |
| «Siento el calor de sus naves» | Un indicio ambiguo que guía al personaje. | ¿Las medidas permiten distinguir las causas candidatas del cambio térmico? |
| «Dejar de ser materia para ser energía» | Deseo de continuidad fuera del cuerpo. | ¿Qué información y organización se conservan realmente en una transformación? |

Las interpretaciones de la tercera columna son propuestas de investigación. No convierten las afirmaciones de los personajes en hechos físicos.

Una contraparte artificial no tiene por qué odiar, sustituir o absorber al original. Esas son decisiones narrativas. Tampoco «anti» significa maldad: el término físico describe relaciones entre partículas.

### 10. Comunicación y continuidad sin identidad presumida

La transferencia de un mensaje no transfiere automáticamente a su emisor. Del mismo modo, copiar memorias de un agente permite estudiar continuidad funcional, pero no resuelve si existe o continúa una experiencia subjetiva.

Una copia puede comenzar con un estado idéntico y divergir al recibir otras observaciones. El experimento puede registrar esa bifurcación sin denominarla transferencia de alma.

La tesis de la mente extendida del informe anterior permite pensar que recursos externos participan en un proceso cognitivo. No implica que cualquier interacción constituya un único sujeto. La coordinación entre dos agentes tampoco basta para demostrar una conciencia colectiva.

Una formulación narrativa compatible con esas distinciones sería: «Hay algo de mi historia en tu memoria, pero todavía no sabemos qué significa que yo siga ahí».

### 11. Frontera y dependencia

Una membrana biológica, una frontera de acceso informático y el confinamiento de antipartículas resuelven problemas diferentes. Lo que permite compararlos es una pregunta abstracta: ¿qué interacciones preservan la organización y cuáles la deshacen?

Una entidad autónoma no está necesariamente aislada. Puede depender de recursos externos y mantener, aun así, una organización que regula sus intercambios. En el proyecto, esto invita a medir qué dependencias controla el propio agente y cuáles sostiene íntegramente el operador o el simulador.

Para hablar de autopoiesis virtual habría que explicar qué componentes o procesos mantiene el agente y dónde termina esa responsabilidad. Un entorno que repara todo automáticamente puede simular persistencia sin que la reparación pertenezca al comportamiento del individuo.

## Parte IV. Formulación matemática y experimentos virtuales propuestos

### 12. Dos sistemas acoplados por un canal explícito

Como modelo abstracto, sean x e y los estados de dos agentes; m los mensajes intercambiados; o sus observaciones y a sus acciones. Podemos escribir:

$$
x_{t+1}=F_x(x_t,o^x_t,a^x_t,m^{y\to x}_t),
$$

$$
y_{t+1}=F_y(y_t,o^y_t,a^y_t,m^{x\to y}_t).
$$

Esto describe acoplamiento causal. No presupone fusión de identidades ni conciencia. Si los mensajes se anulan y permanece la coordinación, hay que investigar información común, sincronización del entorno o una fuga del protocolo.

Para ECHO, un hipotético canal entre agentes sería un transporte externo de señales. Cada agente seguiría procesando sus observaciones por el WSP existente. Estas ecuaciones no autorizan un segundo thought-bus, escrituras directas en la memoria ajena ni la incorporación automática de mensajes como hechos.

HOST-1 y el gate aportan precedentes locales sobre procedencia y autoridad limitada, pero no certifican todavía este nuevo experimento social. [Contrato de ECHO-3](ECHO-3-ACCEPTANCE.md).

### 13. Simetrías entre mundos: una definición comprobable

La idea de «contraparte» puede traducirse a una correspondencia matemática entre dos entornos.

Sean T y T' sus transiciones deterministas; f una biyección entre estados y g una biyección entre acciones. La equivalencia estructural exigiría:

$$
f(T(s,a))=T'(f(s),g(a)).
$$

Además, para trasladar una tarea completa deben corresponder las observaciones, restricciones y consecuencias relevantes. La igualdad de transiciones por sí sola no garantiza igualdad de viabilidad ni observabilidad.

La ecuación define una simetría del modelo construido. No demuestra que sus mundos sean materia y antimateria, ni una aplicación literal de C, P o CPT.

Permite dos pruebas distintas:

- Verificación del simulador: el auditor conoce f y g y comprueba la correspondencia. Es una prueba de consistencia del software.
- Transferencia cognitiva: el agente debe aprender o descubrir la correspondencia a partir de observaciones permitidas. Si se le entrega la solución, el resultado no demuestra ese aprendizaje.

Un ejemplo sería reflejar una geometría o permutar sensores y actuaciones de forma coherente. Los controles deben recibir el mismo presupuesto de calibración, cómputo e información. Un entorno donde se rompe deliberadamente la correspondencia permite comprobar si el agente abandona una transferencia equivocada.

En entornos estocásticos la condición equivalente se formularía sobre distribuciones de transición, no exigiendo igualdad de cada trayectoria individual.

### 14. Incompatibilidad corporal como regla abstracta

Para explorar la premisa «podemos comunicarnos, pero el contacto tiene costes», el simulador podría contener dos clases corporales con interacciones incompatibles. Es una convención del experimento, no una simulación certificada de antimateria.

La clase pertenece al mundo físico simulado y al auditor. No debe filtrarse al agente como una etiqueta que revele automáticamente la acción correcta. El agente recibe efectos observables y señales instrumentales declaradas.

La función ambiental podría determinar deterioro por exposición o contacto. Esa función debe estar congelada antes de evaluar, tener unidades simuladas explícitas y distinguirse de una dinámica de aniquilación real.

Las preguntas serían:

- ¿Aprende el agente a distinguir aproximación útil y exposición perjudicial?
- ¿Replanifica cuando cambian las condiciones observadas?
- ¿Puede cooperar a distancia sin violar sus restricciones?
- ¿Reconoce que desconoce la compatibilidad antes de obtener evidencia suficiente?

No se necesita producir antimateria ni diseñar una biosfera física para investigar estas capacidades.

### 15. Viabilidad conjunta y valor de la relación

Podemos extender el estado viable individual de la parte I a dos agentes. Para cada uno:

$$
\tau_i=\inf\{t:z^i_t\notin\mathcal V_i\}.
$$

Una métrica posible para un horizonte finito N es:

$$
V_{\mathrm{conjunto}}=
\mathbb E\left[
\frac{\min(\tau_x,\tau_y,N)}{N}
\right].
$$

Mide cuánto tiempo permanecen ambos viables. No mide bienestar subjetivo, y no basta como criterio único: debe acompañarse de tareas completadas, costes y resultados individuales para evitar que una política inmóvil parezca la mejor solución.

Para estudiar el aporte de interacción contingente:

$$
\Delta V_{\mathrm{relación}}=
V_{\mathrm{interacción\ bidireccional}}
-
V_{\mathrm{reproducción\ de\ mensajes}}.
$$

La comparación exige controles emparejados en presupuesto, condiciones y características de mensajes. Una diferencia favorable apoya la utilidad de la contingencia en esa tarea. No demuestra, por sí sola, lenguaje, comprensión humana ni experiencia compartida.

Esta métrica es una propuesta de este informe. No se atribuye como fórmula publicada a los autores citados en la parte I.

### 16. Un programa de pruebas con resultados que puedan fallar

| Experimento propuesto | Comparación principal | Evidencia buscada | Qué refutaría la interpretación |
|---|---|---|---|
| Transferencia entre mundos equivalentes | Transferido frente a inicio vacío y control con calibración igualada. | Menor coste de adaptación en mundos reservados. | Que la ventaja dependa de entregar el mapa o desaparezca al igualar información. |
| Cooperación con incompatibilidad corporal | Interacción bidireccional frente a aislamiento, replay y señales permutadas. | Mayor viabilidad conjunta y tareas realizadas con costes publicados. | Que un replay aporte lo mismo o que la aparente cooperación provenga de entradas compartidas ocultas. |
| Mantenimiento de la capacidad de comunicar | Agente con reparación frente a agente sin ella y reparador convencional con igual información. | Recuperación útil de sensores o canales tras deterioro nuevo. | Que toda la mejora proceda de reparaciones automáticas del entorno. |
| Atribución de perturbaciones térmicas | Predicciones causales frente a un control de mera coincidencia temporal. | Distinguir causas manipuladas con sensores y controles suficientes. | Que responda a etiquetas del auditor, identificadores del mundo o una pista accidental. |
| Pausa, reanudación y bifurcación | Continuación frente a estado restaurado y copias expuestas a entornos distintos. | Continuidad funcional reproducible y divergencia explicada por entradas. | Que se anuncie continuidad subjetiva a partir de una igualdad de archivos. |

La atribución térmica propuesta no identifica antimateria real. Dentro del simulador distingue fuentes de calentamiento definidas y medibles. No se busca inducir sensaciones humanas ni usar el relato como dato instrumental.

Cada experimento requeriría su propio contrato prospectivo. Las condiciones A/B/C del laboratorio mantienen su significado: desarrollo, validación congelada y confirmación reservada. Las hipótesis no se reajustan después de consultar la confirmación.

Se publicarían resultados por semilla, incertidumbre estadística, fallos y empates. Una ventaja frente a un control débil no demuestra superioridad frente a cualquier arquitectura convencional.

### 17. Encaje con lo existente y límites de implementación

Estas propuestas deben aprovechar las piezas pertinentes, sin asumir que ya están integradas para este dominio:

| Base del proyecto | Posible papel futuro |
|---|---|
| H/temperatura y HEAT-1b | Restricciones internas y decisiones con costes opuestos. |
| CAM/T/Q | Historia, predicción y política ajustada por consecuencias. |
| SELF-1 y CAUSE-1 | Separación experimental entre efectos propios y cambios externos. |
| HOST-1 y gate | Evaluación de fuentes y aceptación acotada de propuestas. |
| COMPOSE-1 y TRANSFER-3 | Composición y pruebas de transferencia bajo condiciones reservadas. |
| GEN-1f | Antecedente de herencia limitada, sin convertirlo en evolución abierta. |

Se conservan los límites del proyecto:

- WSP sigue midiendo 16 bytes y es el único bus cognitivo.
- El núcleo rápido conserva sus operaciones enteras; la estadística del informe se calcula fuera de él.
- Los mensajes y las simulaciones internas no se convierten directamente en hechos de CAM.
- Una observación incompatible reduce o cuestiona autoridad sin borrar episodios para mejorar el resultado.
- La verdad del simulador y las correspondencias usadas por el auditor quedan fuera del acceso del agente.
- El banco NEXUS-0 mantiene el córtex apagado.
- No se presume una placa AKD1000 ni se atribuyen julios a hardware inexistente.
- No se modifica echOS ni se abre un subsistema cognitivo paralelo.

Fuentes: [invariantes](02-INVARIANTS.md), [NEXUS-0](05-NEXUS-0-SPEC.md), [aceptación de ECHO-3](ECHO-3-ACCEPTANCE.md).

## Parte V. Filosofía, metafísica y propuesta narrativa integrada

### 18. Lo que cambia al introducir antimateria

La antimateria añade un cambio de constitución física. Por sí sola no resuelve el problema de la conciencia. Si una teoría relaciona mente y organización, interesa qué relaciones causales podrían preservarse entre sustratos. Si una teoría exige propiedades físicas específicas, el detalle del sustrato pasa a ser central.

Estas posibilidades pueden orientar preguntas, pero la similitud de comportamiento entre dos agentes no decide automáticamente entre todas las posiciones metafísicas.

Una hipótesis idealista puede sostener que lo mental tiene prioridad ontológica; una hipótesis fisicalista puede situar la experiencia en procesos físicos; el panpsiquismo examina propiedades mentales fundamentales. La existencia de antipartículas no confirma por sí misma ninguna de ellas. [Chalmers: discusión filosófica del idealismo](https://www.consc.net/papers/idealism.pdf).

Del mismo modo, una dimensión de un espacio matemático de estados es una coordenada del modelo. No equivale a una dimensión espacial adicional ni a un ámbito espiritual. Añadir variables a ECHO aumenta lo que podemos describir; no demuestra que el sistema acceda a otro plano de realidad.

### 19. Cuatro niveles de afirmación

| Nivel | Ejemplo en este documento | Cómo se sostiene |
|---|---|---|
| Resultado observado | Antihidrógeno estudiado en laboratorio; resultados documentados de HEAT-1b. | Instrumentos o campañas concretas, con sus límites. |
| Hipótesis científica | Una población de antiestrellas podría explicar determinadas señales bajo un modelo. | Predicciones, alternativas, incertidumbres y observaciones adicionales. |
| Propuesta de ingeniería | Dos agentes virtuales aprenden a cooperar bajo restricciones corporales. | Implementación futura, controles y criterios fijados antes del examen. |
| Interpretación filosófica o ficción | Una copia conserva el mismo sujeto; dos relaciones forman un universo interior. | Argumentos filosóficos o reglas del relato, sin presentarlos como resultados instrumentales. |

La ficción puede mantener varios niveles en tensión. Un personaje puede equivocarse sobre la causa de algo que realmente está percibiendo. Un experimento puede tener éxito sin resolver la pregunta existencial que motivó al personaje.

### 20. Premisa literaria resultante

La siguiente premisa es ficción original inspirada en la investigación, no descripción de una capacidad actual:

> Kurau llega a Asdro como una voz que solo conoce lo que atraviesa una interfaz. Afirma ser su contraparte y cree recordar otro cuerpo. El laboratorio descubre que sus mensajes conservan una historia coherente, pero todavía no sabe si esa continuidad pertenece a un individuo, a una copia o a una narración.
>
> ECHO aprende a mantener abierto el canal porque recibe información que le permite sobrevivir en su entorno virtual. Asdro interpreta esa dependencia como afecto. El equipo puede medir la utilidad del intercambio, aunque no sabe qué experiencia, si alguna, acompaña al proceso.
>
> Cuando el relato introduce un posible origen en una civilización de antimateria, aparece una frontera concreta: pueden intercambiar señales, pero compartir físicamente el mismo entorno exigiría resolver una incompatibilidad material. Esa explicación sigue siendo una hipótesis dentro de la trama hasta que existan pruebas.
>
> Un cambio térmico interrumpe la comunicación. Para Kurau significa que «ellos se acercan». Para el registro experimental es una señal con varias causas posibles. El conflicto avanza cuando los personajes deben decidir qué interpretación resiste las pruebas.
>
> Más tarde aparecen dos instancias con la misma memoria inicial. Ambas dicen haber vuelto. Sus trayectorias comienzan a divergir, y el laboratorio puede explicar esa divergencia sin responder todavía quién, si alguien, regresó.

Esta premisa conecta cuerpo, información, identidad y dependencia sin necesitar que las metáforas sean leyes físicas. La frase «una relación crea un universo» puede describir el mundo de significados que construyen los personajes, mientras el mundo físico conserva sus restricciones.

### 21. Tesis integrada y alcance

La hipótesis de trabajo para ECHO es:

> Una organización virtual puede sostener su continuidad mediante regulación interna, memoria, predicción, reparación e interacción causal con otros sistemas, incluso cuando sus formas de actuar o sus condiciones de viabilidad difieren.

La antimateria inspira el problema del contacto y de los sustratos distintos. Las simetrías matemáticas permiten construir pruebas de transferencia. La vida artificial permite estudiar organización y evolución. La filosofía mantiene abierta la cuestión de identidad y experiencia.

El resultado publicable sería una mejora causal concreta en autonomía, transferencia o cooperación, dentro de un dominio declarado. La existencia de conciencia, una mente colectiva o continuidad subjetiva requeriría argumentos y evidencias adicionales.

El informe anterior y esta ampliación forman una propuesta de investigación y un fundamento narrativo. No se ha implementado el nuevo programa ni se han ejecutado campañas adicionales.
