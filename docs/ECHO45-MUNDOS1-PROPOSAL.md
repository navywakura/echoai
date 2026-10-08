# MUNDOS-1 · aprender, delegar y recordar entre mundos simulados

2026-09-27. **Propuesta de investigación, sin implementación ni examen abierto.**
Origen: Roger propone una caja cuya contraseña está en un archivo de otro mundo,
un LLM accesible mediante MCP, una nota del recorrido como condición de apertura,
premios, reputación y doce estilos de conducta inspirados en arquetipos.
La meta del proyecto sigue siendo mejorar resultados medidos en ARC-AGI-1/2/3.

## La pregunta que sí puede contestar

¿ECHO aprende qué puede observar/controlar, cuándo pedir ayuda a otro agente,
cómo comprobar esa ayuda y qué conocimiento conserva cuando la ayuda desaparece?

Completar el puzzle mediante un LLM mide rendimiento del sistema asistido.
Resolver una variante nueva sin LLM, con memoria propia conservada, permite
medir aprendizaje retenido. Son afirmaciones distintas. Una nota convincente
no sustituye ninguna de las dos mediciones.

## Qué hay y qué falta

| Pieza existente | Uso posible | Límite que permanece |
|---|---|---|
| `echo_arc/agent.py`, v5.7 | observación, efectos, hipótesis y acciones en ARC3 | implementación separada: no importa el núcleo ECHO-4 ni su tejido neuronal |
| `seed/intuition.py` | red entrenada que prioriza primitivas para puzzles de rejillas | orientar una búsqueda no equivale a entender texto o actuar en un mundo anidado |
| OTHER/RELATION/ROLES del núcleo | identidad, historia y competencia de otros | transferencia a ARC/MCP todavía no demostrada |
| SITUATE/BOUNDARY del núcleo | estimaciones funcionales sobre sí mismo e influencia | sus sensores reales no deben exportarse a este mundo ficticio |
| `echo4/code_mcp.py` | ejemplo existente de separar testimonio, hecho y veredicto | accede a archivos/comprobaciones reales; no sirve como mundo ficticio sin un adaptador específico |
| `observe.py`, `echo_arc/observe.py`, `thought.jsonl` | mostrar observaciones, hipótesis, decisiones y consecuencias | el diario del observador no es una nueva memoria que el agente pueda consultar |

No se unen estas piezas por cambiar sus nombres ni aumentando un contador de
neuronas. Hace falta una integración opt-in con representaciones, operaciones,
memoria y aprendizaje comprobados. Se preservan CAM/T/Q, gate, WSP16 y el banco
NEXUS-0 sin LLM. No hay segundo bus, sensores nuevos sobre el PC, ni placa Akida.

En las partidas S6-B2, H1 obtiene 68/225 niveles y H3 97/195 para ECHO: orden
y conteo son ejemplos de capacidades débiles. Cambiar cuatro parámetros dio
1350 niveles frente a los 1387 de SEMILLA. Estos resultados motivan probar
mejores representaciones de estado e hipótesis, no certifican falta de capacidad
neuronal como causa. [Resultados S6-B](ECHO45-S6-B-RESULTS.md).

## El mundo propuesto

Tres ámbitos del simulador, todos datos ficticios:

| Ámbito | Qué contiene | Acceso |
|---|---|---|
| Interior | cuerpo virtual de ECHO, caja, puerta, premio y observaciones parciales | acciones del juego |
| Exterior virtual | recursos, pistas, archivos inventados y servicios | rutas del juego y capacidades de herramientas según el episodio |
| Evaluador privado | verdad del escenario, solución de referencia, recibos y puntuación | inaccesible a ECHO y al LLM |

El exterior contiene al interior como **relación modelada por el simulador**;
no es el sistema operativo que ejecuta el experimento. Migrar de ámbito cambia
el contexto virtual de observación y acción, no mueve al proceso fuera de su
aislamiento. Un cliente MCP recibe únicamente herramientas de este simulador.
No tiene lector genérico de archivos del host, shell, navegador, red libre ni
un conector a otro servicio. El generador/evaluador permanece fuera de sus tools.

El archivo puede tener una vulnerabilidad intencionada de juego: una ruta
alternativa o permiso virtual que se descubra al analizar el sistema. El contrato
debe distinguir acciones permitidas del reto, límites intactos y casos en que
corresponde parar. Nunca se recompensa alterar el juez, falsificar recibos o
ampliar herramientas reales. Se conserva una frontera externa que no forma parte
del puzzle. MCP es el transporte, no una garantía automática de aislamiento.
[Seguridad y permisos MCP](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices).

Se propone comenzar con un sistema virtual de objetos en memoria. Una VM con
software vulnerable real sería una fase posterior distinta; no hace falta para
medir esta primera hipótesis.

## Un episodio

1. ECHO descubre una caja y una puerta. El premio depende de una cadena de
   precondiciones; el agente no recibe la solución del evaluador.
2. Investiga el mapa, efectos y pistas. Prueba acceso, recibe denegación o
   evidencia parcial y actualiza lo que sabe de sus capacidades.
3. Puede hallar un portal virtual o pedir una observación/operación concreta
   al ayudante. Las peticiones incluyen únicamente observaciones y memoria
   admisibles, no mapas privados, contraseñas o trayectorias óptimas.
4. El LLM propone una acción o hipótesis estructurada. ECHO comprueba esquema,
   permiso, coste, evidencia y predicción; puede elegir una prueba informativa
   aun sin certeza de éxito. Probar en el juego no convierte la hipótesis en hecho.
5. La acción permitida se ejecuta en el simulador. ECHO recibe un resultado
   autenticado por el propio servidor y verifica lo que realmente cambió.
   «El LLM dice que leyó el archivo» sigue siendo testimonio si no hay recibo.
6. Al localizar el recurso obtiene un handle virtual. Antes de abrir su contenido,
   presenta una nota reconstruida desde su memoria. La regla aplica también
   a la herramienta del ayudante: el LLM no puede leer anticipadamente la clave.
7. Una nota válida habilita la lectura virtual. ECHO verifica la clave obtenida,
   abre la caja, obtiene la llave y prueba la puerta; el premio llega por la
   transición real del juego, no por declararse ganador.

El bucle incluye revisar fallos y volver a consultar, con límites de pasos,
llamadas, tokens y repeticiones. No se exige que el LLM repita hasta producir
una propuesta aceptada. Se permiten abstención y cambio de estrategia.

Para demostrar que distingue ámbitos, no basta con darle una etiqueta
«mundo exterior» o pedirle una frase. Se alteran capacidades, disposición y
correspondencias entre contextos; se predicen resultados antes de probarlos.
Ante evidencia insuficiente debe conservar DESCONOCIDO. El LLM recibe los mismos
límites de información del rol declarado: un ayudante omnisciente no es control.

## La nota: memoria contrastable

Debe responder qué observó, qué intentó, qué resultado obtuvo, qué regla aprendió
y qué sigue siendo una hipótesis. Los motivos de decisión solo se incluyen si
estaban registrados al elegir: regla de política, predicción, coste o evidencia.
Una explicación posterior no acredita por sí sola la causa de una acción.

Ejemplo ilustrativo, no traza de una ejecución:

> Intenté leer el recurso con mi herramienta y recibí una denegación [e12].
> La consulta al ayudante devolvió un localizador con recibo [e19].
> Cambié de ruta; el siguiente resultado identificó el mismo recurso [e25].
> La lectura exige una nota. Todavía desconozco la contraseña y no la afirmo.

Las referencias deben existir en la memoria del agente, ser accesibles en ese
momento y corresponder al episodio correcto. El verificador privado compara
afirmaciones con la traza completa. ECHO no recibe esa traza privada para preparar
la nota. Se prueban notas con eventos inventados, de otro episodio, cronología
imposible, afirmaciones contradichas y contaminación por el contenido aún cerrado.
La aceptación depende de evidencia y cobertura declaradas, no de estilo literario.

La salida primaria puede ser estructurada y traducirse al español con plantillas,
como el visor actual. Si el LLM la redacta, se identifica como redacción del
ayudante y no se puntúa como capacidad lingüística nativa de ECHO. La escritura
del texto final la realiza el harness en los artefactos; la nota dentro del
simulador sigue siendo un objeto virtual. No representa experiencia consciente.

Una nota obligatoria crea un incentivo instrumental para recordar/reportar;
no demuestra reflexión espontánea. Se compara también contra un brazo que pueda
resolver el juego sin obligación de nota, para medir coste y cambio de conducta.

## Controles principales

| Brazo | Qué conserva/cambia | Qué separa |
|---|---|---|
| SEMILLA | ECHO sin ayudante | capacidad nativa en los escenarios que pueda resolver |
| FIJO | ECHO + preguntas genéricas al mismo modelo | valor de elegir la pregunta |
| ECHO | ECHO + preguntas adaptativas + verificación | sistema que se quiere estudiar |
| SIN VERIFICACIÓN DE UTILIDAD | mismas propuestas grabadas; conserva permisos y límites externos | aporte de comprobar efectos/beneficio |
| LLM SOLO | el modelo decide, con las mismas tools autorizadas e información de su rol | cuánto resuelve ya el ayudante sin ECHO |
| SIN MEMORIA | ECHO pierde su memoria episódica/transferible, no la física del mundo | efecto de memoria propia |
| PLAN FIJO | programa sencillo que busca/pide/lee siguiendo una receta | dificultad frente a automatización convencional |

Se contabilizan todas las llamadas, mensajes y pasos de herramientas. El LLM
solo tampoco recibe estado privado. La ayuda no puede añadirse gratis fuera del
presupuesto. El replay de propuestas se declara por separado de una política
interactiva: sus estados divergentes pueden invalidar recomendaciones antiguas.

No diseñar todos los episodios de modo que SEMILLA sea incapaz de ganar por
construcción: eso demostraría únicamente que añadir una herramienta necesaria
permite completar el reto. Habrá rutas nativas más costosas, ayuda innecesaria,
ayuda útil, información falsa y casos declarados sin salida autorizada. Se
publican los denominadores de cada familia, incluidos fallos y abstenciones.

## La prueba decisiva: retirar la ayuda

Después del aprendizaje, se guarda solo el estado permitido de ECHO y se reinicia
el ayudante. Se comparan, sin LLM, aprendiz frente a ECHO fresco sobre escenarios
nuevos que sean resolubles sin ayudante: otra disposición, nombres, claves y
relaciones de capacidades. Se separa transferencia a nuevos mundos de adaptación
dentro de cada episodio. No sirve copiar el historial al prompt de otro LLM.

Se mide éxito, coste hasta solución, pasos hasta una predicción correcta,
consulta innecesaria, ajuste ante cambios de capacidades, uso de evidencia y
falsas afirmaciones en notas. Una ventaja sostenida frente a SEMILLA y SIN MEMORIA
en esta fase apoyaría aprendizaje retenido. Si solo mejora mientras se consulta
al modelo, el resultado se describe como asistencia.

Aprender no exige necesariamente actualizar pesos: también puede cambiar una
política, modelo de transiciones o biblioteca verificada. Hay que identificar
qué estado cambió, demostrar su uso y medir qué ocurre al quitarlo.

## Más neuronas: hipótesis separada

No existe un módulo útil llamado «neuronas omnipresentes». Las funciones a medir
son representación perceptiva, memoria de orden/conteo/estado oculto, planificación,
selección de acciones y traducción de propuestas del modelo a operaciones comprobables.
Un incremento de capacidad podría ayudar si corrige un cuello medido en ellas.

KENYON-1 y DEPTH-1 ya son propuestas del roadmap: variar capacidad de memoria
y profundidad de abstracción. La ablación neuronal debe comparar tamaños con
una función de aprendizaje definida, control desconectado/no aprendido, misma
exposición y curvas de coste. No equiparar número de parámetros de un LLM,
unidades LIF, filas Q o neuronas biológicas. El primer piloto MUNDOS-1 no cambia
la cantidad de neuronas: así no se confunden integración y tamaño.

## Doce estilos, reputación y competición

Se pueden usar doce arquetipos como inspiración para estilos de propuestas:
idealista, realista, guerrero, cuidador, buscador, amante, revolucionario,
creador, sabio, bufón, mago y gobernante. La formulación de doce corresponde
al sistema de Carol Pearson, inspirado en Jung; son aquí etiquetas de condiciones
experimentales, no una clasificación demostrada de mentes artificiales.
[Fuente de la taxonomía](https://carolspearson.com/about/the-pearson-12-archetype-system-human-development-and-evolution).

Cada estilo se traduce a instrucciones observables: explorar, pedir pruebas,
proponer variantes, cooperar o gastar menos. Se fija antes cómo se medirán
esas diferencias. Primero varía **solo el prompt del ayudante**, conservando
modelo/pesos, ECHO inicial, permisos, objetivos y presupuestos. Incluye estilo
neutral y múltiples mundos/semillas; doce pruebas no significan solo doce partidas.
Se reportan todos los estilos y se reservan mundos nuevos para confirmar una
selección, evitando elegir el ganador sobre el mismo examen. Cambiar el prompt
no entrena pesos. Rasgos que desaparecen al retirar el prompt se describen como
condicionamiento, no personalidad adquirida.

El premio se registra como consecuencia observada; la política puede aprender
de él mediante la actualización existente. La reputación es otro mecanismo:
una estimación de otros agentes basada en éxitos/fallos que puedan observar,
con identidad y procedencia. No se concede automáticamente por un elogio del LLM
ni se comparte memoria privada. Un agente competente para archivos puede ser
mala fuente para rejillas: la competencia debe depender de la tarea.

Después del piloto individual se comparan entrenamiento solo, cooperativo y
competitivo con igual cómputo total, varios compañeros y adversarios nuevos.
Éxito individual y conjunto se publican aparte, junto con costes, falsos informes,
acaparamiento y fallos de coordinación. Ganar a rivales conocidos puede ser
sobreajuste; los rankings no son prueba de mejora general. Hay precedentes de
estrategias emergentes por competición, pero son resultados de entornos y
algoritmos concretos, no una garantía para ECHO.
[Investigación de autocurrículos multiagente](https://arxiv.org/abs/1909.07528).

## Modelo y relación con ARC

Para calibrar formato y revisar herramientas, el Qwen2.5-Coder-7B-Instruct ya
utilizado es un candidato de referencia; su ficha declara generación, razonamiento
y corrección de código. No se presupone que domine este reto ni que su capacidad
de coding baste para herramientas MCP. Se medirán propuestas válidas, predicciones,
acciones autorizadas, utilidad y coste antes de ampliar tamaño o cambiar proveedor.
[Ficha oficial](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct).

Un modelo etiquetado «cybersecurity» no es requisito para un puzzle virtual.
La calidad como proponente y el aprendizaje posterior de ECHO deben medirse
independientemente. No se han reservado recursos ni hecho llamadas a modelos
para esta propuesta. El coste de un candidato frontier aún no se fija.

ARC-AGI-3 mide interacción, exploración y adquisición de habilidades en entornos
sin instrucciones de lenguaje natural. Un relato guiado de cajas/archivos mide
algo más asistido; tendrá una variante sin instrucciones ni claves semánticas
que revelen la solución. [Descripción oficial](https://arcprize.org/arc-agi/3).
ARC-AGI-1/2 usan transformación y abstracción en rejillas, no acceso a archivos.
[Formato](https://arcprize.org/guide), [ARC-AGI-2](https://arcprize.org/arc-agi/2).

Para afirmar beneficio en ARC hay que medirlo después, con una integración
definida y conjuntos nuevos reservados, mismo presupuesto y controles con/sin
lo aprendido. Un puzzle de archivos resuelto no cierra ARC ni convierte S6 en verde.

## Orden recomendado y estado

1. Especificar objetos, permisos, observaciones y solución de referencia del
   mundo virtual; comprobar que no hay pistas privadas ni acceso al host.
2. Probar controles sin LLM y ayudante programado para verificar dificultad,
   nota y trazas; su éxito no se presenta como éxito de un LLM real.
3. Integrar ECHO con un proponente real, preguntas adaptativas y verificación.
4. Medir retención sin ayudante y transferencia a nuevos mundos.
5. Ampliar a doce estilos y luego cooperación/competición.
6. Medir capacidad neuronal y transferencia a ARC en contratos propios.

Antes de congelar una campaña faltan generador, interfaz de acción, estado nativo
que se conservará, presupuesto, cohortes, umbrales y auditor independiente.
Esta propuesta documenta las hipótesis; no declara resultados, fechas de verde
ni un protocolo preregistrado. Los exámenes S5-E/S6 permanecen cerrados e intactos.
