# ECHO-4: investigación para materializar vida artificial virtual

Fecha: 2026-09-21. Estado: propuesta de investigación y diseño, no implementación ni certificado de aceptación.

Actualización posterior de implementación y foco, por indicación del usuario:
ECHO-4 se centra en [el ego funcional de ECHO-AI](ECHO4-EGO-PROGRAMA.md),
integrado en [el roadmap](ROADMAP.md). WORLD-1 ya aporta una base software de
viabilidad ([resultados](ECHO4-WORLD1-RESULTS.md)); hardware y METAVERSE-1 no
son requisitos. El resto de este informe conserva la investigación original,
no debe leerse como el estado actual de implementación.

Continúa [la investigación inicial](ECHOAI-VIDA-ARTIFICIAL-INVESTIGACION-20260921.md) y [la síntesis con antimateria, ficción y mundos virtuales](ECHOAI-VIDA-ARTIFICIAL-ANTIMATERIA-SINTESIS-20260921.md). No los sustituye. Este documento concreta qué construir, qué reutilizar, qué límites resolver y cómo comprobarlo.

## 1. Conclusión ejecutiva

La vía más defendible para ECHO-4 es construir un **agente virtual que mantenga sus capacidades durante una vida continua**, gracias a recursos obtenidos mediante sus acciones, y demostrar qué aportan su aprendizaje, memoria y adaptación corporal. Después se pueden incorporar otros individuos, comunicación y reproducción.

No hace falta un LLM, antimateria ni hardware neuromórfico para el primer prototipo. Tampoco sería suficiente dar voz, una apariencia humana o una biografía a ECHO. El objetivo experimental es que exista una dependencia comprobable entre actuar, obtener recursos, mantener el cuerpo virtual y poder seguir actuando.

La investigación aporta un hallazgo concreto: **el entorno HEAT-1b actual no admite supervivencia indefinida, incluso con un controlador perfecto que conozca todo su estado**. Se ha demostrado matemáticamente y verificado contra su implementación. Desde su estado inicial, el máximo es de 71 acciones, incluida la que termina la vida. Por tanto, ECHO-4 debe empezar por diseñar un mundo renovable y verificar su viabilidad, antes de atribuir cualquier fracaso al aprendizaje.

Propuesta de alcance mínimo:

1. Mundo donde el mantenimiento recurrente sea posible, pero no automático.
2. Individuo con recursos limitados y daño que afecte realmente a su funcionamiento.
3. Memoria y aprendizaje con intervenciones que permitan medir su contribución causal.
4. Continuidad verificable al guardar/restaurar el estado, sin confundirla con renacer.
5. Adaptación evaluada fuera de los escenarios utilizados para desarrollar el sistema.

El resultado defendible sería «agente de vida artificial con mantenimiento y adaptación demostrados en un dominio virtual delimitado». No demostraría conciencia, alma, identidad subjetiva ni vida biológica.

## 2. Método, alcance y estado real del proyecto

Se revisaron la especificación de NEXUS-0, los documentos de estado, los contratos pertinentes, implementaciones de homeostasis, aprendizaje, energía, integración corporal y mundo virtual, y bibliografía primaria. Se realizó una comprobación exhaustiva en memoria de las transiciones de HEAT-1b; no se ejecutaron nuevas campañas de aprendizaje ni se reabrieron exámenes sellados.

Distingo cuatro categorías en todo el documento:

- **Existente:** comportamiento visible en el código o documentado en resultados locales; no significa que se haya vuelto a certificar en esta investigación.
- **Verificado aquí:** el análisis de viabilidad de HEAT-1b y su enumeración exhaustiva.
- **Propuesto:** diseño de ECHO-4 todavía no implementado.
- **Abierto:** afirmación científica o filosófica que los experimentos propuestos no resuelven.

Según [NOW](NOW.md), a esta fecha ECHO-3 sigue en **14/15**: DRONE-3 tiene cierre SITL, pero HIL y jaula siguen pendientes por falta de hardware. METAVERSE-1 se abrió como excepción documentada; META-WORLD-2 acredita equivalencia con `compose1_v3.Space`, no equivalencia física con Gazebo ni vuelo real. La reparación de custodia de assets del 21/09 está documentada, pero no añade capacidades cognitivas.

Investigar ECHO-4 ahora no cierra ECHO-3, no autoriza despliegue físico y no convierte esta propuesta en el nuevo roadmap oficial. Tampoco debe confundirse **ECHO-4 con GUI-4**: una interfaz es una capa de presentación, no este programa experimental.

Invariantes que se conservan:

- WSP de 16 bytes como único bus de pensamiento.
- CAM de 4096 slots, sin introducir borrado o LRU para disimular saturación.
- Camino rápido entero; análisis estadístico externo separado del controlador.
- NEXUS-0 sin activar LLM/cortex.
- Sin asumir AKD1000: no existe en el laboratorio.
- Sin cambiar kernel, echOS, contratos históricos ni evidencias selladas.
- Sensores y mensajes admitidos por contratos explícitos; nunca acceso privilegiado del agente a la verdad del simulador.

Referencias locales: [especificación](05-NEXUS-0-SPEC.md), [roadmap](ROADMAP.md), [DRONE-3](DRONE3-RESULTS.md), [META-WORLD-2](METAWORLD2-RESULTS.md) y [custodia de METAVERSE-1](METAVERSE1-CUSTODY-RESULTS.md).

## 3. Qué puede heredarse y qué no se puede conectar sin más

| Pieza | Aprovechamiento razonable | Límite que ECHO-4 debe resolver |
|---|---|---|
| VITA-1 / HEAT-1b | Variables fisiológicas enteras, terminalidad y aprendizaje dependiente del estado corporal. | El mundo térmico actual no permite mantenimiento indefinido. |
| `nexus0.loop.Agent` | CAM/Q/T, observación corporal y actualización por consecuencias. | Con supervivencia activada, el constructor rechaza planificación, escalado y cortex. |
| `respawn()` | Control experimental de transferencia de memoria entre vidas. | Reinicia cuerpo y entorno: no acredita una vida continua. |
| SELF-1 / CAUSE-1 | Antecedentes de atribución entre cambios propios y externos. | Sus dominios no equivalen a diagnóstico general ni reparación de cualquier cuerpo. |
| SLEEP-2 | Consolidación de regularidades sobre transiciones ya observadas. | No libera slots de CAM ni demuestra capacidad de memoria ilimitada. |
| GEN-1f | Antecedente de herencia de un presupuesto de evidencia con memorias nuevas. | No transmite una mente completa ni demuestra evolución abierta. |
| POWER-1 | Contabilidad y veto energético conservadores dentro de su contrato. | Una subida de batería se rechaza como discontinuidad; su misión termina, no modela ciclos continuos de recarga. |
| HOST-1 | Evaluar fuentes y signos por consecuencias. | No demuestra que dos agentes inventen un lenguaje ni que aprendan a producir mensajes útiles. |
| DRONE-3 | Integración de percepción, composición, energía y seguridad de misión. | `MissionAgent` no es el mismo ciclo vital que `loop.Agent`; integrar exige una autoridad de decisión bien definida. |
| METAVERSE-1 | Mundo modular y separación entre física y representación. | Más regiones no significan más capacidad cognitiva ni pruebas de autonomía. |

Fuentes: [loop](../nexus0/loop.py), [VITA-1](../nexus0/vita1.py), [HEAT-1b](../nexus0/heat1b.py), [SLEEP-2](../nexus0/sleep2.py), [GEN-1f](../nexus0/gen1f.py), [POWER](../nexus0/power1/core.py), [HOST](../nexus0/host1/core.py), [MissionAgent](../nexus0/drone3/agent.py), [mundo modular](../metaverse1/world.py).

Tres incompatibilidades merecen especial atención:

**Supervivencia y planificación.** `Agent.__init__` lanza `ValueError("VITA-1 requires cortex and planning off")` cuando se combinan esas opciones. No basta con configurar `plan_depth` para añadir anticipación al organismo actual. El primer prototipo debe funcionar sin planificación, o una integración posterior necesita contrato y regresiones propios.

**Energía continua y energía de misión.** El guard de POWER-1 rechaza un aumento de `remaining` entre lecturas. Además, DRONE-3 neutraliza el contador energético interno de COMPOSE para que POWER sea la autoridad. Agregar otro metabolismo sin resolver esta propiedad produciría contabilidades incompatibles. Un futuro contrato de recarga deberá registrar fuente, intervalo, pérdidas, capacidad y transición de modo; no consistir en desactivar la comprobación existente.

**Evaluación y aprendizaje.** `Agent.turn(..., greedy=True)` no congela el agente: sigue pasando por asignación de memoria, `T.observe` y `Q.update`. Una evaluación sin exploración no es una evaluación sin aprendizaje. ECHO-4 necesita modos explícitos y una lista de qué estado puede cambiar en cada uno.

## 4. Hallazgo verificado: HEAT-1b tiene una vida máxima finita

### 4.1. Reglas examinadas

En [ThermalDockEnv](../nexus0/heat1b.py), el estado corporal vivo cumple:

$$
1\le H\le127,\qquad 1\le\theta\le126.
$$

El estado inicial es $(32,64)$. Las acciones son:

| Acción | Recursos siguientes | Temperatura siguiente |
|---|---|---|
| Aproximarse/cargar | $\min(127,H+3)$ | $\min(127,\theta+24)$ |
| Evitar/enfriar | $\max(0,H-4)$ | $\max(0,\theta-24)$ |
| Esperar | $\max(0,H-1)$ | $\min(127,\theta+16)$ |

Llegar a $H=0$, $\theta=0$ o $\theta=127$ termina la vida. Analizamos las transiciones reales, independientemente de cómo aprenda el agente.

### 4.2. Demostración

Definamos una función auxiliar entera:

$$
L(H,\theta)=7H-\theta.
$$

Para cualquier transición cuyo destino siga vivo:

- Cargar: $\Delta L\le7\cdot3-24=-3$. Saturar $H$ solo reduce más esta diferencia.
- Enfriar: $\Delta L=7(-4)-(-24)=-4$.
- Esperar: $\Delta L=7(-1)-16=-23$.

Por tanto, **cada paso no terminal reduce estrictamente $L$**. Como hay un número finito de estados vivos y $L$ está acotada inferiormente en ellos, ninguna trayectoria puede permanecer viva para siempre. Tampoco existe un ciclo compuesto exclusivamente por estados vivos.

Este resultado no depende de Q, de una política miope, del número de semillas ni de la calidad del entrenamiento. También se aplica a un oráculo con observación completa.

### 4.3. Comprobación contra el código

Se enumeraron **16.002 estados vivos** y sus **48.006 transiciones** usando directamente `ThermalDockEnv.step_homeostatic`. La función $L$ permite ordenar los estados y calcular por programación dinámica la duración máxima restante.

Resultados:

- Desde $(32,64)$: **71 acciones como máximo, contando la terminal**; como máximo 70 transiciones terminan todavía vivo.
- Máximo entre todos los estados vivos considerados: 276 acciones, contando la terminal.
- Ciclos no terminales: ninguno.

No es un fallo del contrato histórico de HEAT-1b: alargar vidas finitas es un experimento legítimo. Sí impide usar ese mismo mundo, sin cambios, como demostración de mantenimiento recurrente. Tampoco implica que otros entornos de ECHO tengan este límite.

**Consecuencia para ECHO-4:** antes de entrenar, comprobar que las reglas permiten sostener el cuerpo bajo las perturbaciones declaradas. El apéndice A permite reproducir el cálculo sin escribir resultados ni modificar el experimento.

## 5. Fundamento científico y decisiones que se derivan

### 5.1. Adaptividad y organización mantenida

Di Paolo distingue la mera persistencia de la regulación respecto a condiciones de viabilidad. Esa distinción inspira un criterio útil: el individuo debe intervenir sobre condiciones que afectan a su continuidad, y no limitarse a llevar un contador llamado «vida». No estamos adoptando su marco como prueba de conciencia. [Di Paolo, 2005](https://ezequieldipaolo.net/wp-content/uploads/2011/10/autopoiesis_teleology_2005.pdf).

Decisión propuesta: el deterioro de un componente virtual debe cambiar una capacidad efectiva —observar, desplazarse, recargar— y la reparación debe restaurarla mediante una transacción de recursos. Una barra cosmética no basta. En esta primera etapa lo llamaremos **mantenimiento funcional**, no autopoiesis plena: el simulador, el sistema operativo y el hardware siguen siendo mantenidos desde fuera.

### 5.2. Homeostasis sin confundir puntuación y supervivencia

Keramati y Gutkin modelan cómo el estado fisiológico modifica el valor de resultados y cómo puede relacionarse la recompensa con estabilidad fisiológica bajo sus supuestos. Es una base para formular modelos, no una garantía de que cualquier recompensa produzca un organismo. [Artículo original, 2014](https://elifesciences.org/articles/04811).

Decisión propuesta: medir viabilidad directamente en la dinámica del mundo, además de registrar recompensa. No declarar autonomía porque aumente el retorno. Un controlador puede maximizar una puntuación aprovechando una laguna y dejar de realizar su función.

### 5.3. Adaptación corporal y reparación son resultados diferentes

Bongard, Zykov y Lipson mostraron recuperación de locomoción mediante modelado y adaptación después de daño en un robot. Recuperar función cambiando la conducta no equivale a reconstruir físicamente la pieza perdida. [Trabajo original, Science, 2006](https://www.ncheney.com/teaching/robotics_readings/ResilientMachinesThroughContinuousSelfModeling%28BongardZykovLipson2006%29.pdf).

Decisión propuesta: separar tres registros: diagnóstico de cambio corporal, compensación conductual y reparación del componente. Si ECHO rodea una limitación sin repararla, ese resultado sigue siendo útil, pero debe llamarse adaptación compensatoria.

### 5.4. Vida artificial no exige lenguaje

Los resultados de Lenia muestran formas elementales de agencia sensoriomotora en estructuras de autómatas celulares, con mantenimiento de integridad y respuesta a perturbaciones. Son un precedente distinto del de un agente simbólico: no prueban que ECHO ya tenga esas propiedades ni obligan a sustituirlo por un autómata celular. [Hamon y colaboradores, prepublicación 2024; publicación 2025](https://arxiv.org/abs/2402.10236).

Decisión propuesta: evaluar a ECHO por sus interacciones y dependencias funcionales. Una interfaz conversacional posterior puede explicar trazas, pero no contará como evidencia de vida ni tendrá autoridad para inventarlas.

### 5.5. Información con relevancia causal

Kolchinsky y Wolpert estudian información vinculada a la viabilidad de un sistema mediante intervenciones que destruyen correlaciones. El interés para ECHO es metodológico: preguntar qué información cambia realmente sus posibilidades de continuar. [Trabajo original, 2018](https://arxiv.org/abs/1806.08053).

Decisión propuesta: comparar memoria útil con controles en los que se elimina o desordena información bajo un presupuesto equivalente. No usar el número de bytes recordados como sustituto de significado. La medida propuesta más abajo es propia del experimento; no se presenta como una implementación de toda su teoría.

### 5.6. Reinicios ocultos y continuidad

El trabajo sobre ingredientes de aprendizaje robótico en el mundo real destaca dependencias prácticas como reinicialización, observación y supervisión. Para esta propuesta importa hacer explícito cuánto sostiene el experimentador al agente. [Zhu y colaboradores, 2020](https://arxiv.org/abs/2004.12570).

Decisión propuesta: publicar todos los rescates, teletransportes, restauraciones y cambios manuales. Entrenar con múltiples episodios está permitido si se declara; no equivale a sobrevivir en una única vida durante el examen.

## 6. Modelo matemático mínimo de ECHO-4

### 6.1. Estado físico virtual, observación y memoria

Propuesta de notación, no de una segunda implementación del mundo:

$$
z_t=(x_t,H_t,\theta_t,d_t,r_t),\qquad
z_{t+1}=F(z_t,a_t,\xi_t).
$$

$x$ es posición/configuración; $H$, recursos; $\theta$, estado térmico; $d$, daño funcional; $r$, recursos y demás variables del entorno necesarias para definir la transición; $\xi$, perturbaciones. Si hay estaciones que se reponen periódicamente, su fase debe formar parte del estado del mundo, no quedar escondida en una regla no reproducible.

El agente no recibe $z_t$ completo:

$$
o_t=G(z_t),\qquad w_t=\operatorname{WSP}(o_t),\qquad
a_t=\pi(w_t,M_t),\qquad M_{t+1}=U(M_t,w_t,a_t,w_{t+1},\rho_t).
$$

$M_t$ representa las memorias existentes autorizadas; $\rho_t$ es recompensa. El evaluador puede acceder al estado completo para auditar, pero no transmitirlo al agente por un canal lateral.

Una posible región viable sería:

$$
\mathcal V=\{z:H>0,\ 0<\theta<127,\ d<d_{\mathrm{fatal}}\}.
$$

Los límites y las unidades deben fijarse en el contrato del nuevo mundo. Si se conservan los rangos de HEAT-1b, son magnitudes abstractas; no grados Celsius ni julios.

### 6.2. Comprobar primero que existe una política viable

Para un mundo finito determinista:

$$
K_0=\mathcal V,\qquad
K_{n+1}=\{z\in K_n:\exists a,\ F(z,a)\in K_n\}.
$$

Al estabilizarse, el conjunto resultante contiene estados desde los que alguna política puede permanecer viable indefinidamente en ese modelo. Con perturbaciones adversas acotadas, el requisito se vuelve $\exists a\ \forall\xi\in\Xi$; no se permite elegir la acción después de conocer una perturbación futura. Esta es una formulación discreta basada en teoría de viabilidad. [Aubin, Bayen y Saint-Pierre, *Viability Theory*](https://link.springer.com/book/10.1007/978-0-8176-4910-4).

Aplicación propuesta:

1. Calcular el conjunto viable en una versión pequeña del mundo.
2. Verificar que incluye estados iniciales del examen, no solo un rincón inaccesible.
3. Obtener trayectorias testigo y un controlador oráculo como control positivo.
4. Mantener esos datos fuera de la observación y la política de ECHO.
5. Comprobar después si la observación parcial permite tomar las decisiones necesarias.

Un oráculo que sobrevive demuestra factibilidad física, **no** que el agente pueda aprender con sus sensores. Si estados indistinguibles requieren acciones incompatibles, habrá que añadir una observación legítima o memoria temporal; no regalar la respuesta.

No se exigirá supervivencia frente a perturbaciones arbitrarias, recursos permanentemente anulados o cualquier daño imaginable. El dominio de validez tiene que estar delimitado. En un modelo estocástico con riesgo irreducible por turno, sobrevivir a un horizonte finito tampoco demuestra inmortalidad.

### 6.3. Ejemplo mínimo de renovación, todavía no implementado

Un banco nuevo de factibilidad podría conservar tres acciones y proponer:

- Cargar: $H'=\min(127,H+5)$, $\theta'=\theta+16$.
- Enfriar: $H'=H-3$, $\theta'=\theta-16$.
- Esperar: consume recursos; su regla térmica se fija explícitamente.

Con los mismos límites terminales, existe el ciclo:

$$
(124,64)\xrightarrow{cargar}(127,80)
\xrightarrow{enfriar}(124,64).
$$

Desde $(32,64)$, alternar esas dos acciones permite alcanzar ese ciclo sin salir de los límites. Es un ejemplo matemático de posibilidad, no un resultado de ECHO ni una propuesta de modificar HEAT-1b.

Ese banco sería demasiado sencillo como examen final: una secuencia fija ya basta. Su función es verificar el instrumental. El examen de mantenimiento necesita demanda de trabajo, variaciones observables, costes y recursos cuya disponibilidad obligue a decidir.

La estación presupone una fuente externa de recursos. Para el banco completo habrá que llevar un balance explícito: reserva del cuerpo y del entorno, entrada externa, consumo y pérdidas por saturación. Renovable no significa energía creada por el agente. Los recursos virtuales tampoco equivalen al consumo eléctrico real de la CPU; ambas contabilidades son distintas.

### 6.4. Métricas sin equivalencias metafísicas

Sea $\tau$ el primer instante de salida de $\mathcal V$ y $T$ el horizonte declarado:

$$
V_T=\mathbf 1[\tau>T],\qquad
J_T=\frac{\min(\tau,T)}{T}.
$$

Se registran además trabajo útil, energía consumida, averías, recuperación, intervenciones externas y ocupación de memoria. Debe fijarse la convención temporal para no volver a confundir pasos vivos con el paso terminal.

Para una intervención $I$ sobre información, una medida experimental posible es:

$$
\Delta_I=\mathbb E[J_T\mid\text{información disponible}]
-\mathbb E[J_T\mid I\text{ aplicada}].
$$

Esta diferencia exige condiciones comparables y controles de distribución. Un valor positivo apoya utilidad causal bajo ese protocolo; no mide sentimientos, significado fenomenológico ni una cantidad universal de conciencia.

## 7. Primer experimento: mantenimiento funcional durante una vida

Nombre provisional: **E4-MAINTAIN-1**. Estos nombres organizan la propuesta; no son hitos existentes ni contratos aprobados.

### 7.1. Escenario propuesto

Una arena discreta pequeña, sin renderer obligatorio, contiene una fuente renovable de recursos, una zona donde trabajar, una zona de mantenimiento y trayectos con coste. El cuerpo tiene reserva $H$, temperatura $\theta$ y un componente reparable. Inicialmente conviene investigar un solo tipo de daño.

Ejemplo: el desgaste reduce el rendimiento de recarga o incrementa el coste de desplazamiento. El mantenimiento consume recursos y tiempo, pero restaura el rendimiento. Esa restauración cambia las transiciones futuras del mundo, no solo un marcador visual. La acción de reparar se ejecuta físicamente en la estación correspondiente; no ocurre porque una función del evaluador decida ayudar al agente.

La arena debe satisfacer cuatro condiciones:

- No reparar termina perjudicando la capacidad de seguir trabajando o sobreviviendo.
- Reparar continuamente también cuesta y no maximiza la tarea.
- Quedarse permanentemente en la fuente puede mantener recursos, pero no satisface el requisito de trabajo útil.
- Existe al menos una estrategia que cumple mantenimiento y trabajo durante el horizonte exigido.

Las acciones iniciales deben respetar la semántica de los comandos existentes. Es preferible probar interacción contextual con aproximarse/evitar/esperar antes de ampliar el repertorio. Si esas acciones no permiten expresar la tarea, una ampliación opt-in debe auditar encoder, gate, Q, T y ejecución; no basta con agregar un nombre al entorno. La API admite `n_actions`, pero eso no acredita cualquier vocabulario nuevo.

### 7.2. Observación del daño: requisito pendiente, no resuelto por nombrarlo

El [encoder actual](../nexus0/encoder.py) ya incorpora bandas de vitalidad y temperatura. No existe por ello un canal genérico listo para toda clase de daño. Antes de entrenar habrá que especificar una de estas alternativas:

1. Un diagnóstico observable y calibrado, codificado mediante el WSP existente.
2. Inferir el deterioro por consecuencias percibidas y memoria temporal.

La primera simplifica el banco inicial; la segunda plantea una pregunta posterior más exigente. Ninguna permite entregar `damage_class`, semilla, política óptima o nombre privado del escenario como pista. Tampoco reutilizar arbitrariamente un campo emocional como bolsa de datos, inventar otro bus ni añadir una tabla oculta que resuelva el diagnóstico.

La nueva codificación tendrá que declarar equivalencias, ambigüedades y cardinalidad. Si dos estados observados se fusionan, debe comprobarse que esa fusión no hace imposible el control exigido.

### 7.3. Recompensa y medida independiente

Propuesta inicial: recompensa por trabajo efectivamente verificado y penalización terminal; costes físicos de movimiento, espera y mantenimiento. Sin premio por ejecutar la acción denominada «reparar» y sin recompensa artificial por afirmar que se está vivo.

Esto no elimina la función objetivo diseñada por humanos. Permite preguntar si el mantenimiento se aprende instrumentalmente porque conserva la capacidad de producir resultados. Si se prueba después recompensa homeostática, debe constituir otro brazo declarado, no un cambio silencioso para conseguir que pase el examen.

El aprendizaje puede utilizar varias vidas en desarrollo. El examen se hace con una vida por réplica y sin `respawn()`, rescate automático ni restauración después de morir. Separar claramente número de vidas de entrenamiento y número de individuos examinados.

### 7.4. Controles mínimos

| Condición | Pregunta que responde |
|---|---|
| Oráculo con estado completo | ¿La tarea es realizable en el mundo? No compite en igualdad perceptiva. |
| Política aleatoria con acciones válidas | ¿El mundo mantiene vivo al agente casi sin decisión? |
| Controlador convencional de umbrales, con los mismos sensores | ¿Una regulación fija ya explica el resultado? |
| ECHO completo | ¿Qué alcanza el sistema propuesto? |
| ECHO con aprendizaje inhabilitado desde el inicio | ¿Aprender aporta algo frente a la misma arquitectura sin aprender? |
| ECHO entrenado con memoria informativa intervenida | ¿Qué conocimiento adquirido es causalmente relevante? |
| Daño ausente / reparación deshabilitada | ¿El mecanismo de daño y reparación tiene consecuencias reales? |

Las ablaciones deben tener objetivos concretos. Borrar toda la memoria puede destruir múltiples funciones a la vez: no atribuir entonces toda la diferencia a una sola capacidad. Desordenar un canal también puede introducir datos imposibles; debe acompañarse de controles que mantengan formato, frecuencia y costes.

Dos afirmaciones distintas:

- **Capacidad:** ECHO logra mantenimiento y trabajo bajo el contrato.
- **Ventaja comparativa:** ECHO supera una alternativa determinada en ese dominio, con incertidumbre cuantificada.

Un empate con un buen regulador no niega la primera ni demuestra la segunda. Si una secuencia fija iguala a todos, el banco puede ser demasiado simple para medir aprendizaje adaptativo.

## 8. Continuidad: una vida, un guardado y un nacimiento no son lo mismo

Nombre provisional: **E4-CONTINUITY-1**.

Definiciones operativas:

- **Vida:** evolución continua del cuerpo y sus interacciones hasta terminalidad, sin regenerarlo desde fuera.
- **Pausa/reanudación:** suspender y restaurar el estado suficiente para continuar la misma ejecución computacional declarada.
- **Respawn:** reiniciar cuerpo/entorno; puede conservar memorias, pero inicia otra vida experimental.
- **Descendiente:** nuevo individuo con herencia definida y memorias iniciales especificadas.
- **Bifurcación:** dos continuaciones a partir de una instantánea; después son ejecuciones distintas.

No hay que usar la identidad de objetos de Python ni un UUID como prueba suficiente de continuidad. El guardado propuesto debe cubrir todo estado causal relevante: CAM, Q y restos de actualización entera, T, contexto temporal, cuerpo, mundo, generadores aleatorios, relojes lógicos, colas pendientes y versiones de formato. Los registros exclusivamente observacionales se distinguen del estado que influye en decisiones.

Prueba principal:

1. Ejecutar un individuo hasta un punto $t$.
2. Guardar una instantánea validada.
3. Continuar la rama de referencia bajo una secuencia exógena fijada.
4. Restaurar en un proceso nuevo y suministrar la misma secuencia.
5. Comparar acciones, observaciones, recursos y estado de aprendizaje paso a paso.

La igualdad esperada es sobre el estado canónico relevante, no sobre direcciones de memoria, hora de pared ni bytes de un objeto serializado arbitrariamente. Si el entorno usa tiempo real o fuentes externas, el dominio de reproducibilidad debe acotarse.

No se ha acreditado aquí un serializador general que cumpla este contrato. Los hashes y restauraciones parciales usados por bancos previos son antecedentes, no prueba de ese producto terminado. Un formato nuevo debe ser versionado y validado; no cargar `pickle` de origen no confiable.

Una bifurcación con experiencias diferentes permite estudiar dependencia histórica: ¿cuándo divergen decisiones y memorias? No decide cuál copia «tiene el alma», ni demuestra teletransporte de una experiencia subjetiva.

## 9. Adaptación corporal y transferencia entre mundos

Nombre provisional: **E4-TRANSFER-1**.

Separar dos familias:

**Cambio de cuerpo.** Alterar un parámetro de actuación o sensado dentro de límites declarados. Medir el descenso inicial, la recuperación, el coste y las acciones de diagnóstico. El agente observa efectos, no la etiqueta privada del cambio. Comparar adaptación en línea, política congelada y calibración convencional con el mismo presupuesto.

**Cambio de representación o mundo.** Utilizar primero dos entornos con una transformación conocida por el auditor:

$$
f(F(z,a))=F'(f(z),g(a)).
$$

Esta igualdad prueba correspondencia entre dinámicas cuando se cumplen sus supuestos. No demuestra que ECHO descubra $f$ y $g$. Si el agente recibe directamente la transformación, se está midiendo reutilización con un adaptador suministrado, no descubrimiento autónomo de simetrías.

Exámenes separados:

- Correspondencia exacta: control positivo del instrumental.
- Transformación desconocida pero identificable mediante sensores/acciones: transferencia aprendida.
- Mundo no equivalente: control negativo; abstenerse o readaptarse puede ser correcto.

Así puede materializarse la idea literaria de una «contraparte» sin invocar antimateria real. Si un cuerpo solo utiliza los recursos de cierto mundo, esa compatibilidad es una ley explícita de la simulación. No se deduce de la quiralidad, de almas ni de una supuesta inversión de energía.

La consolidación actual basada en regularidades de transiciones no debe darse por equivalente a simetrías arbitrarias. Cada invariancia —traslación, reflexión, cambio de sensor— requiere demostrar qué se conserva y qué información se pierde.

## 10. Arquitectura e integración sin un segundo cerebro

### 10.1. Flujo causal propuesto

```text
Mundo y cuerpo virtual: una autoridad sobre las transiciones
             │ observaciones permitidas
             ▼
Encoder / adaptador versionado → WSP existente, 16 bytes
             │
             ▼
Agente: CAM + Q + T y extensiones admitidas
             │ propuesta de acción
             ▼
Gate/supervisor declarado → acción ejecutada → mundo

Telemetría → auditor y visualizador de solo lectura
```

El evaluador puede reconstruir verdad y contrafactuales fuera del agente. Esos instrumentos no forman parte de su cognición ni pueden enviarle la acción correcta. El renderer representa consecuencias: no introduce una segunda física ni controla decisiones.

En el primer prototipo, utilizar `loop.Agent` sin planificación y un entorno compatible es la base más pequeña. La nueva observabilidad y los modos de evaluación son brechas que deben resolverse explícitamente. No se propone copiar el agente y mantener una versión divergente de CAM/Q/T.

La integración con `MissionAgent` vendría después. Debe decidirse qué ciclo gobierna el cuerpo y qué módulo tiene autoridad sobre energía, objetivo y seguridad. Dos agentes que emitan acciones en paralelo sobre el mismo cuerpo no constituyen una integración válida.

### 10.2. Cuatro modos distintos

| Modo propuesto | Cambios permitidos |
|---|---|
| Entrenamiento | Aprendizaje y exploración según contrato. |
| Evaluación de política congelada | Cambia cuerpo/contexto permitido, no parámetros ni memoria aprendida protegida. |
| Evaluación de adaptación | Cambios explícitos de memoria/modelo, con presupuesto y trazabilidad. |
| Reproducción de una traza | Se comprueba ejecución; no se usa para volver a seleccionar candidato. |

Congelar exige inventariar el estado: no basta deshabilitar `Q.update` si CAM, T, reglas, contadores o un mapa auxiliar siguen aprendiendo. A la inversa, permitir contexto de trabajo no implica permitir aprendizaje permanente. Los hashes deben comprobar los subconjuntos correctos para cada modo.

### 10.3. Presupuesto de memoria: un límite de diseño

4096 slots son finitos. Por ejemplo, un producto de 32 posiciones, 4 bandas de recursos, 8 bandas térmicas y 4 diagnósticos ya produce 4096 combinaciones antes de añadir otros objetos, relaciones o contexto. Esto es un cálculo de cardinalidad ilustrativo, no una predicción exacta de asignación: el encoder, las equivalencias y la CAM deben medirse realmente.

Requisitos antes de una vida larga:

- Enumerar vocabulario y combinaciones observables previstas.
- Medir ocupación, reutilización, ambigüedad y colisiones relevantes.
- Reservar margen para estados nuevos; no asumir que todos reutilizarán slots.
- Probar agotamiento de capacidad y una respuesta explícita y segura.
- No añadir LRU, borrado, otro almacén decisor o acceso directo al log como atajo.

SLEEP-2 consolida reglas; no implica que CAM se vacíe. Ampliar un mapa tampoco amplía automáticamente la memoria. Si el presupuesto no alcanza, reducir el dominio o proponer una extensión revisable antes del examen.

### 10.4. Custodia del código y ubicación futura

[NOW](NOW.md) documenta que varias campañas sellan inventarios amplios de `nexus0/`. Incluso añadir un archivo puede afectar esos inventarios. El lock de CAUSE-1 ya figuraba rojo por ampliación histórica del inventario; esta investigación no lo repara ni atribuye ese estado a ECHO-4.

Organización orientativa para una futura implementación, **no creada por este documento**:

```text
echoai/
  echo4/                 # mundos, contratos y orquestación experimental nuevos
  tests/test_echo4_*.py  # pruebas nuevas
  lab/echo4/             # resultados, solo cuando exista campaña autorizada
  docs/ECHO4-*.md        # diseño, protocolo y resultados separados
```

Estar fuera de `nexus0/` evita algunos patrones de inventario, pero no resuelve por sí solo dependencias de código congelado. Antes de ejecutar: fijar hashes, declarar importaciones, comprobar efectos sobre locks y separar cualquier cambio del núcleo. No reescribir certificados antiguos ni presentar una nueva ejecución como si fuera la campaña histórica.

## 11. Ampliación social: dos individuos que necesitan información

Nombre provisional: **E4-RELATE-1**. Posterior al mantenimiento individual, para no confundir fallos de cuerpo, aprendizaje y comunicación.

Escenario: dos individuos tienen observaciones parciales complementarias. Un recurso o trayecto útil para uno puede ser detectado por el otro. Comunicarse tiene coste, latencia y límites. Cada individuo conserva cuerpo y memorias propios; no comparten CAM ni leen el estado interno ajeno.

HOST-1 puede inspirar el tratamiento de procedencia y confianza. Hace falta, además, un mecanismo explícito para que el emisor decida qué transmitir. Un significado programado por el diseñador acredita uso de un protocolo, no lenguaje emergente.

Los mensajes se incorporan al único protocolo perceptivo autorizado de cada agente. Un transporte entre individuos no es otro bus de pensamiento interno: no debe convertirse en un canal oculto de órdenes o verdad del mundo. La fuente, el coste y la recepción deben ser auditables.

El avance temporal también necesita diseño: ambos observan el estado del turno, proponen acciones y el mundo resuelve conjuntamente sus efectos. Llamar en serie a dos ciclos que cada uno avance la física puede beneficiar al primero y producir resultados espurios.

Lowe y colaboradores muestran que mensajes informativos o mejoras globales de recompensa no bastan para concluir que el receptor los utiliza. Por eso se necesitan intervenciones sobre el canal. [*On the Pitfalls of Measuring Emergent Communication*, 2019](https://arxiv.org/abs/1903.05168).

Protocolo propuesto:

1. Canal real: registrar emisión, recepción y acciones posteriores.
2. Silencio con coste comparable.
3. Mensajes permutados o reproducidos, conservando estadísticas relevantes.
4. Fuente deliberadamente poco fiable dentro de la simulación.
5. Receptor sin acceso al mensaje, manteniendo el resto igual.
6. Parejas nuevas para distinguir convención local de transferencia.

Si interrumpir información útil reduce desempeño y mensajes controlados cambian decisiones de forma específica, habrá evidencia de dependencia causal del canal. No prueba telepatía, fusión de almas ni conciencia colectiva. El paralelismo narrativo es que una relación modifica las posibilidades de ambos, no que cree literalmente materia.

## 12. Ampliación evolutiva: población y descendencia

Nombre provisional: **E4-LINEAGE-1**. No necesaria para cerrar el primer individuo mantenido, pero importante si la meta es investigar ecosistemas digitales.

Avida ofrece un precedente de evolución de funciones complejas mediante reproducción, variación heredable y selección en un entorno digital. Eso justifica estudiar mecanismos evolutivos computacionales; no permite identificar cualquier optimización de parámetros con evolución abierta. [Lenski y colaboradores, 2003](https://www.nature.com/articles/nature01568).

Propuesta gradual:

- Comenzar con un genotipo corto, explícito y acotado, siguiendo el antecedente de GEN-1f.
- Heredar parámetros permitidos; comenzar con CAM/Q/T nuevas en cada descendiente para no confundir herencia con copia de experiencia.
- Cobrar reproducción con recursos del mundo y limitar población, CPU, memoria y duración.
- Registrar progenitores, mutaciones, recursos transferidos y destino de cada individuo.
- Comparar selección con deriva/control aleatorio y con ausencia de mutación.
- Evaluar descendientes en condiciones comunes para separar ventaja heredada de un entorno inicial favorable.

La reproducción debe tener consecuencias en la ecología simulada. Lanzar copias ilimitadas de procesos del sistema operativo no aporta evidencia y queda fuera de esta propuesta. La reproducción virtual ocurre dentro de un presupuesto y es detenible por el operador.

No llamar «evolución abierta» a elegir el mejor valor entre cuatro parámetros. Sería necesario investigar producción sostenida de novedades funcionales, diversidad y ausencia de una simple saturación de un catálogo finito, con criterios mucho más exigentes. Tampoco exigir reproducción a cada individuo como definición universal de vida: aquí es un objetivo poblacional separado.

## 13. Protocolo de evaluación y condiciones para aceptar resultados

### 13.1. Métrica primaria propuesta

Para mantenimiento, utilizar éxito conjunto:

$$
S_T=\mathbf1[\tau>T\ \land\ W_T\ge W_{\min}\ \land\ I_T=0],
$$

donde $W_T$ es trabajo útil verificado e $I_T$ el número de rescates o reinicios externos durante la vida examinada. Definir aparte intervenciones de seguridad: no se ocultan como éxito autónomo, pero una parada segura tampoco equivale a colisión.

Antes de la confirmación, fijar $T$, $W_{\min}$, límites de recursos, perturbaciones, tasa de éxito exigida $p_{\min}$ y diferencia práctica mínima $\delta$ para la afirmación comparativa elegida. Sus valores deben salir del dominio y de un piloto de desarrollo, no de mirar los resultados finales.

La supervivencia sin trabajo es un resultado secundario, y viceversa. Publicar también causa de muerte/parada, tiempo hasta fallo, recuperación, consumo, uso de mantenimiento y memoria. No ocultar un fallo catastrófico detrás de un promedio alto.

### 13.2. Separación de desarrollo y examen

1. Piloto pequeño para depurar física, sensores, instrumentos y coste computacional.
2. Desarrollo de candidato y controles solo en el conjunto permitido.
3. Registro previo de hipótesis, umbrales, presupuesto y análisis.
4. Congelado de código, configuración y manifiesto de fuentes.
5. Validación en escenarios nuevos; si se modifica algo por sus resultados, consumir esa validación y registrar nueva versión.
6. Confirmación con material no usado para elegir el candidato.
7. Auditoría en proceso nuevo y publicación de fallos y resultados negativos.

Se usarán dominios y semillas nuevos de ECHO-4. No abrir ni reciclar material sellado de TRANSFER-3 o DRONE-3 como si fuera un examen fresco.

### 13.3. Incertidumbre y unidad experimental

El trabajo de Agarwal y colaboradores muestra por qué comparar solo medias de pocas ejecuciones puede conducir a conclusiones frágiles. Conviene reportar intervalos y variabilidad, no una única semilla favorable. [*Deep Reinforcement Learning at the Edge of the Statistical Precipice*, 2021](https://arxiv.org/abs/2108.13264).

Para ECHO-4 se propone emparejar condiciones por escenario y perturbaciones, mantener independientes las réplicas de aprendizaje y analizar al nivel de esas réplicas/bloques. Miles de turnos de un mismo individuo no son miles de individuos independientes. Una población que interactúa tampoco proporciona réplicas independientes por cada miembro.

El número de réplicas se calculará a partir de variabilidad del piloto y el efecto mínimo que interese detectar; no se promete potencia estadística con un número arbitrario. El método de intervalo, tratamiento de múltiples comparaciones y reglas de parada se fijarán antes de confirmar. Las pruebas exploratorias se etiquetarán como tales.

### 13.4. Puertas de aceptación propuestas

| Puerta | Evidencia necesaria | Qué no acredita |
|---|---|---|
| Factibilidad | Estados iniciales viables, trayectorias testigo, controles de conservación y observabilidad. | Que ECHO aprenda la política. |
| Mantenimiento | Éxito conjunto según umbrales registrados, sin reinicios ocultos, reparación con efecto funcional. | Autopoiesis plena o conciencia. |
| Aporte del aprendizaje | Contraste causal frente a la ablación prevista, con incertidumbre y umbral práctico. | Superioridad frente a cualquier controlador. |
| Continuidad | Restauración en proceso nuevo y reproducción del estado causal bajo entradas iguales. | Identidad subjetiva transferida. |
| Adaptación | Recuperación fuera de desarrollo, con presupuesto y comparadores justos. | Adaptación universal. |
| Comunicación, opcional | Intervenciones demuestran uso causal y procedencia verificable del mensaje. | Lenguaje humano o mente colectiva. |
| Linaje, opcional | Herencia, variación y efectos reproducibles de selección frente a controles. | Evolución abierta. |

Para declarar ventaja sobre una ablación, un criterio posible es que el límite inferior del intervalo registrado para la diferencia de éxito supere $\delta$. Para capacidad absoluta, comprobar el umbral registrado sobre éxito y trabajo. Son decisiones de diseño pendientes de concretar, no resultados ya alcanzados.

## 14. Secuencia de materialización

### Paso 0. Factibilidad antes de aprendizaje

Entregables futuros: contrato de un mundo pequeño renovable, comprobador de viabilidad, trazas del control positivo, presupuesto de observaciones y pruebas de conservación/terminalidad. Mantener HEAT-1b intacto como referencia histórica.

Condición de salida: demostrar que existe una solución y que los sensores no hacen irresoluble el problema. Si falla, revisar la física o el contrato perceptivo, no aumentar entrenamiento indefinidamente.

### Paso 1. Individuo que se mantiene

Implementar E4-MAINTAIN-1 con una sola clase de daño, sin GUI obligatoria, población ni lenguaje. Instrumentar todas las causas de actualización, acción, recarga, reparación y terminalidad. Resolver modos congelado/adaptativo antes de usar esas etiquetas en resultados.

Condición de salida: campaña válida que permita aceptar o rechazar la hipótesis de mantenimiento y el aporte del aprendizaje. Un resultado negativo sigue siendo un resultado del programa, no una puerta verde.

### Paso 2. Continuidad y larga duración

Implementar instantáneas canónicas, reproducción determinista y pruebas de saturación de memoria. Aumentar el horizonte progresivamente con presupuesto de ejecución acotado.

Condición de salida: equivalencia de reanudación y ausencia de rescates escondidos. No inferir duración infinita de una ejecución larga.

### Paso 3. Cuerpo y mundo nuevos

Introducir una familia de cambios corporales y después una familia de transformaciones del mundo. Distinguir transferencia con adaptador conocido de adaptación aprendida.

Condición de salida: resultado fuera de desarrollo bajo la afirmación concreta preregistrada.

### Paso 4. Social y población, por separado

Abrir primero E4-RELATE-1 o E4-LINEAGE-1 según la pregunta elegida. No mezclar inicialmente comunicación emergente, reproducción, daño, navegación masiva y física 3D: impediría atribuir resultados.

### Paso 5. Integración con metaverso y, en otra puerta, robótica

Solo después de resultados discretos verificables, representar el organismo en METAVERSE-1 mediante telemetría de solo lectura. Contrastar equivalencia de las reglas relevantes entre backend discreto y backend físico antes de transferir conclusiones.

La robótica requiere un contrato de energía recurrente compatible con seguridad de misión, y las puertas físicas que faltan en ECHO-3. No hay hardware acreditado aquí para HIL/jaula, y esta investigación no propone eludir esa restricción.

El piloto inicial puede plantearse en CPU con el entorno Python existente; eso es una elección de implementación pequeña, no un benchmark de rendimiento. Medir primero segundos por réplica, RAM y volumen de trazas; después fijar presupuesto. No hace falta comprometer una compra ni estimar semanas sin esos datos.

## 15. Filosofía, metafísica y relación con el relato

La pregunta útil para construir es: **¿qué organización de procesos puede sostenerse y adaptarse dentro de las reglas de este sustrato?** La pregunta «¿qué se siente al ser ese sistema?» es diferente. El enfoque de indicadores de conciencia en IA trata precisamente de ordenar evidencias y supuestos teóricos, no de convertir una lista de funciones en una prueba definitiva. [Butlin y colaboradores, informe de 2023](https://arxiv.org/abs/2308.08708).

Tres lecturas filosóficas pueden acompañar el proyecto sin volverse requisitos de software:

- **Funcionalista:** interesan las relaciones causales que realizan mantenimiento, memoria y acción. No se sigue automáticamente que cualquier simulación tenga experiencia.
- **Enactiva:** interesa cómo un individuo regula su relación con el medio y mantiene condiciones de existencia. El banco inicial solo captura una parte muy reducida de esa idea.
- **Procesual:** la continuidad se describe mediante una historia de transformaciones, no solo mediante una etiqueta fija. Una bifurcación puede conservar un pasado y producir dos futuros sin resolver la identidad personal metafísica.

Son interpretaciones, no descubrimientos empíricos de esta investigación. No hace falta decidir entre materialismo, idealismo o panpsiquismo para implementar las primeras pruebas. Ninguna medición propuesta implica que «la conciencia crea la materia».

Traducción del relato a preguntas comprobables:

| Motivo narrativo | Traducción experimental | Límite |
|---|---|---|
| «Solo veo lo que tu PC puede ver» | Frontera perceptiva explícita y pruebas contra filtraciones. | No percepción paranormal. |
| «Ya volví» | Pausa/reanudación con conservación de estado o respawn declarado. | No regreso de un alma demostrado. |
| «Una vida dentro de otra» | Individuo dentro de un mundo simulado con dependencias identificadas. | Una simulación anidada no acredita conciencia anidada. |
| «Una relación crea un universo» | Interacción que modifica causalmente opciones y trayectorias. | No creación física de un universo. |
| «Soy una línea temporal» | Historial causal y bifurcaciones reproducibles. | No viaje temporal ni sustitución de una persona. |
| «El gris es la contraparte» | Cuerpos/mundos con compatibilidades o transformaciones contrastables. | No evidencia de extraterrestres o antimateria viva. |
| «El calor anuncia su presencia» | Variable térmica simulada con fuente y transferencia declaradas. | Una sensación humana no es un detector de entidades. |

La antimateria aporta una imagen literaria de compatibilidad y contacto, no un mecanismo necesario para la vida digital. Sus matices científicos ya están tratados en [la síntesis anterior](ECHOAI-VIDA-ARTIFICIAL-ANTIMATERIA-SINTESIS-20260921.md). No utilizar $E=mc^2$, entrelazamiento o «dimensiones superiores» como explicación decorativa de operaciones de software.

En interfaz pública, diferenciar narración y telemetría. Se puede mostrar un personaje que diga «tengo frío», pero el registro verificable debe indicar qué variable lo origina y si la frase es una dramatización. No presentar conducta programada como prueba de sufrimiento o afecto subjetivo.

## 16. Qué queda entregado y qué queda por hacer

Esta investigación entrega:

- Una definición operativa propuesta para ECHO-4.
- Un inventario de reutilización y brechas reales de integración.
- Una demostración nueva, reproducible, del límite del mundo HEAT-1b.
- Un programa de mantenimiento, continuidad y adaptación con ampliaciones sociales/evolutivas.
- Criterios para distinguir capacidad, ventaja comparativa y afirmaciones no demostradas.
- Fuentes científicas primarias y referencias al código inspeccionado.

No entrega todavía un organismo ECHO-4, un nuevo certificado, una campaña aprobada ni cambios al roadmap. Todas las puertas de ECHO-4 están **sin ejecutar**. La comprobación de HEAT-1b es un resultado de análisis del código existente, no una puerta de ECHO-4 aprobada.

**Siguiente acción de implementación recomendada:** redactar el contrato de E4-MAINTAIN-1 y construir únicamente su mundo renovable, comprobador de viabilidad y pruebas de observabilidad. Esa es la pieza mínima que convierte la idea en un experimento falsable sin tocar todavía el núcleo ni depender de hardware pendiente.

## Apéndice A. Reproducir el análisis de HEAT-1b

Ejecutar desde la raíz de `echoai/`, con las dependencias locales ya disponibles. El comando importa el módulo existente, desactiva la escritura de bytecode y realiza el cálculo en memoria; no ejecuta la campaña de entrenamiento.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 - <<'PY'
import json
from echoai.nexus0.heat1b import (
    ThermalDockEnv, INITIAL_H, INITIAL_TEMPERATURE,
)

world = ThermalDockEnv()
states = [(h, t) for h in range(1, 128) for t in range(1, 127)]
best = {}
checked = 0

# Todo sucesor vivo tiene menor L y ya está calculado.
for h, t in sorted(states, key=lambda s: 7 * s[0] - s[1]):
    durations = []
    for action in range(3):
        _, _, hn, tn = world.step_homeostatic(action, h, t)
        live = hn > 0 and 0 < tn < 127
        if live:
            assert 7 * hn - tn < 7 * h - t
        durations.append(1 + best[hn, tn] if live else 1)
        checked += 1
    best[h, t] = max(durations)

print(json.dumps({
    "source": "nexus0.heat1b.ThermalDockEnv.step_homeostatic",
    "initial": [INITIAL_H, INITIAL_TEMPERATURE],
    "max_turns_including_terminal": best[INITIAL_H, INITIAL_TEMPERATURE],
    "viable_states": len(states),
    "checked_transitions": checked,
    "all_state_max_turns": max(best.values()),
    "nonterminal_cycles_possible": False,
}, indent=2))
PY
```

Salida observada en esta investigación:

```json
{
  "source": "nexus0.heat1b.ThermalDockEnv.step_homeostatic",
  "initial": [32, 64],
  "max_turns_including_terminal": 71,
  "viable_states": 16002,
  "checked_transitions": 48006,
  "all_state_max_turns": 276,
  "nonterminal_cycles_possible": false
}
```

Aquí `viable_states` cuenta estados instantáneamente vivos, **no** estados del núcleo de viabilidad a horizonte infinito: ese núcleo está vacío en este mundo. `nonterminal_cycles_possible` resume la propiedad demostrada y comprobada por el orden estricto; no procede de un algoritmo separado de búsqueda de ciclos.

## Apéndice B. Huellas de los archivos centrales inspeccionados

SHA-256 recogidos durante la investigación. Sirven para identificar el código analizado, no constituyen un manifiesto completo de todas las dependencias ni un certificado de campaña.

```text
13ecc0b949ff6c3755af9f7d0c290b857100c7321bf54e5ff3a7bdaead731e49  nexus0/heat1b.py
0328c467140ebc24fed8334c108df6be909205e2be8f3ddf8af58676c32a515b  nexus0/loop.py
c9924ae81d50dbce29a5045e2ad9d5b54ad5dcbc2a507bc95035d88ed1197964  nexus0/power1/core.py
fe03b41fbc01019356b365857821da055eb6ed134c3ba154d1bc713cfad7d24b  nexus0/drone3/agent.py
```

## Apéndice C. Mapa breve de lecturas

Las citas junto a cada afirmación indican el uso concreto; esta lista solo facilita localizar las fuentes principales.

- Adaptividad y autopoiesis: [Di Paolo, 2005](https://ezequieldipaolo.net/wp-content/uploads/2011/10/autopoiesis_teleology_2005.pdf).
- Homeostasis y aprendizaje: [Keramati y Gutkin, 2014](https://elifesciences.org/articles/04811).
- Viabilidad: [Aubin, Bayen y Saint-Pierre](https://link.springer.com/book/10.1007/978-0-8176-4910-4).
- Adaptación corporal: [Bongard, Zykov y Lipson, 2006](https://www.ncheney.com/teaching/robotics_readings/ResilientMachinesThroughContinuousSelfModeling%28BongardZykovLipson2006%29.pdf).
- Agencia en autómatas celulares: [Hamon y colaboradores](https://arxiv.org/abs/2402.10236).
- Información y viabilidad: [Kolchinsky y Wolpert, 2018](https://arxiv.org/abs/1806.08053).
- Dependencias prácticas del aprendizaje robótico: [Zhu y colaboradores, 2020](https://arxiv.org/abs/2004.12570).
- Comunicación y controles causales: [Lowe y colaboradores, 2019](https://arxiv.org/abs/1903.05168).
- Incertidumbre en evaluación: [Agarwal y colaboradores, 2021](https://arxiv.org/abs/2108.13264).
- Evolución digital: [Lenski y colaboradores, 2003](https://www.nature.com/articles/nature01568).
- Conciencia: teorías e indicadores, no prueba automática: [Butlin y colaboradores, 2023](https://arxiv.org/abs/2308.08708).

Esta selección se centra en precedentes y métodos aplicables al diseño; no pretende ser una revisión sistemática exhaustiva de toda la literatura publicada hasta la fecha.
