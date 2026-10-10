# B24 — búsqueda reparada y cooperación entre investigadores

**Actualización del 9 de octubre:** el propietario autoriza completar B24.
El diseño siguiente se concreta en el [contrato de ejecución](ECHO45-S6-B24-DESIGN.md)
y en módulos `s6b24`. Implementación y comprobaciones en preparación de
lanzamiento; todavía sin resultado B24. El cierre de ECHO-4.5 podrá hacerse
posteriormente con S6 declarado abierto. La descripción «sin implementación»
del 8 de octubre que sigue queda como estado histórico.


8 de octubre de 2026. **PLAN_INTEGRADO_POST_R4. Sin implementación B24,
partidas B24, entrenamiento ni lanzamiento.** Se conserva la propuesta
original de cooperación y se añade la corrección derivada de la
[autopsia B23-R4](ECHO45-S6-B23-R4-FORENSICS-20261008.md), por petición del
propietario. La condición de entrada se ha cumplido: R4 terminó válidamente
sin una mejora aceptada. Esto autoriza preparar B24; no acredita que sus
correcciones funcionen ni activa automáticamente una campaña.

## Condición de activación

Se exige cierre y auditoría de B23. Un error de transporte, falta de
cuota, timeout o discrepancia de replay significa instrumento incompleto;
primero requiere recuperación y no cuenta como refutación científica.

Actualización posterior al cierre: [B23-R3](ECHO45-S6-B23-KAGGLE-RESULTS-20261008.md)
falló en el formato. R4 lo corrigió y cerró a las 16:55 de Madrid con ocho
pruebas de formato válidas, 36 propuestas legales y 924 partidas auditadas.
Hubo 16 duplicados, 12 propuestas inactivas medidas y ocho activas con
pérdidas. Ambos modelos encontraron la misma regla de +4; ninguna pasó.
La revisión local reproduce 36 prompts y 22 ternas de ejecución. El lenguaje
actual permite un control humano histórico de +6 conservador sobre las
mismas 14 partidas; su solución no estará disponible para B24.

Ningún finalista de R4 llegó a desarrollo amplio ni conservación. Por tanto,
la propuesta continúa como B24 junto con la reparación del investigador.
La decisión anterior de trasladarla a ECHO-5 si B23 pasaba queda como rama
histórica no activada. Un futuro resultado B24 podrá informar ECHO-5.1.
Un pase de B23 no equivale a S6 verde: el ejecutor actual deja explícitos
`s6_green=false`, campaña y confirmación pendientes, y examen sin abrir.

Si el diagnóstico muestra un límite de representación o un fallo del juez,
añadir investigadores no se presentará como solución suficiente. Primero se
documentará qué mecanismo puede mejorar la cooperación. No habrá lanzamiento
automático de B24 ni cambios sobre la ejecución congelada de B23.

## Pregunta y antecedentes

¿Compartir resultados comprobados entre investigadores permite descubrir
más políticas que conservan su mejora en casos nuevos, dentro de los mismos
límites de propuestas, llamadas, tokens y partidas?

ROLES-1 v5 dedujo competencias en una tribu de tres agentes y redujo consultas
aproximadamente un 25–27 %, pero obtuvo menos producción neta que el orden
fijo. Es un antecedente de selección de interlocutores; la ventaja de una
organización multiagente sigue siendo una hipótesis.
[Resultados de Tribu](ECHO4-ROLES1-V5-RESULTS.md).

B22 encontró problemas de transferencia y búsqueda. B23 separa selector y
neocórtex con cinco brazos independientes. Varios procesos de evaluación de
partidas no constituyen varios investigadores que aprenden juntos.

## Comparación propuesta

El actor, DSL, modelo base, cuantización, juez y presupuesto por partida
serán comunes. Los tres brazos B24 con LLM compartirán herramientas y todas
las correcciones descritas abajo. La referencia R4 conserva su interfaz
anterior precisamente para medir el efecto conjunto de corregirla.
Se estudiarán varios investigadores sobre el mismo
actor; introducir varios cuerpos cooperando en un mundo es otro experimento.

| Condición | Contextos y experiencia disponible | Máximo de propuestas / llamadas científicas |
|---|---|---:|
| R4-REF | Un 7B con el protocolo anterior; referencia contemporánea | 18 / 18 |
| B24-G | Sintetizador corregido, selección determinista, sin LLM | 18 / 0 |
| B24-S | Un investigador corregido con su archivo completo | 18 / 18 |
| B24-I | Tres investigadores corregidos; cada uno recibe solo su historial | 3 × 6 / 18 |
| B24-C | Tres investigadores corregidos que comparten recibos de desarrollo | 3 × 6 / 18 |

El contraste C/I aislará el intercambio: instrucciones y funciones
disponibles serán iguales en S/I/C. Exploración, reparación
y búsqueda de contraejemplos estarán disponibles para todos. No se añadirá
simultáneamente una personalidad, un modelo distinto y un selector adaptativo
solo al brazo cooperativo.

Para los dos grupos de tres se proponen tres rondas de seis plazas, dos por
investigador. En cooperación se compartirá el archivo al terminar cada ronda;
en independientes seguirá aislado. La primera ronda parte del mismo material
inicial. El orden se sembrará y el intercambio será una barrera determinista,
evitando que la velocidad de un proceso cambie los datos de otro.

Una instancia del modelo puede atender los contextos por turnos en las dos
T4. El número de investigadores lógicos no exige otras tantas copias de
pesos. Se registrarán memoria, latencia, tiempo GPU, consultas y coste de
coordinación; igualdad de límites no garantiza igualdad del gasto realizado.

Se propone usar primero el Qwen2.5-Coder-7B-Instruct Q4_K_M ya verificado,
con la revisión, pesos y ejecutor de R4. Esta elección se basa en el coste
observado: 186,6 s acumulados de procesos de inferencia frente a 350,7 s del
14B, con cero pases de ambos. No establece superioridad general del 7B.
Introducir otro modelo o cuantización se reservará para una ablación
posterior; cambiar tamaño y coordinación a la vez impediría atribuir efectos.

## Corrección común del investigador tras R4

### Semántica, objetivo y archivo

La petición describirá el consumo real de HOLD, el valor por defecto 40,
la conjunción y precedencia de las guardas, la diferencia entre iniciar un
intervalo y recortarlo, y la fórmula exacta del score. Los índices de caso
solo identificarán evidencias; no serán features legales de la política.
La gramática, actor y conjunto de diez duraciones se conservan.

Cada decisión tendrá `mode=EXPLORE|REPAIR`, `parent_id`, hash de política base
y hash del recibo del padre cuando proceda. El selector de ECHO elegirá un
padre con ganancia positiva y presupuesto de investigación disponible. El
modelo recibirá ese objetivo explícito. En REPAIR se fija el HOLD del padre
y solo se modifican condiciones; cada hijo se evalúa por completo y obtiene
su resultado propio. Un parentesco no se inferirá de una frase del LLM.

Se conserva el máximo de ocho reparaciones y al menos diez exploraciones si
se agotan las 18 plazas, salvo éxito temprano. Las ramas de +1 conservador
son investigables, sin modificar el umbral de aceptación. Un intento inactivo
posterior no borra la evidencia de una rama prometedora. La prioridad y los
límites de dos hijos por nodo y cuatro reparaciones por linaje se fijarán
en el contrato ejecutable, reutilizando las piezas M23 donde sean correctas.
En I/C, los límites de reparación por investigador se asignarán antes de
ver resultados, con una permutación sembrada de [3,3,2]; no se redistribuirán
según resultados privados del brazo independiente. Ambos brazos usan los
mismos límites, archivo por ronda y reglas de parentesco.

La estabilidad del actor sigue separada del archivo investigador: una rama
rechazada puede orientar la búsqueda y no puede sustituir la política base.
El valor de una mejora parcial es información para asignar experimentos;
no se contabiliza como mejora aceptada ni como entrenamiento de pesos.

### Propuestas nuevas y aplicables antes de llamar al LLM

El control de formato R4 se mantiene. Se añadirá un constructor común de
candidatos legales a partir de la base y el archivo al que cada investigador
tiene derecho. Primera implementación propuesta: por plaza inspeccionar
hasta 2.048 candidatos sintácticos y ofrecer hasta 64 propuestas completas.
El presupuesto incluye ese trabajo CPU, sus descartes y el tiempo de
construcción; no son partidas ni inferencias ocultas.

En EXPLORE se usa una corriente sembrada de la gramática actual, con
reparto entre duraciones, longitudes de guarda y features observadas. Los
desempates y el reparto se congelan antes de jugar. No se codifica que una
duración o umbral conocido por el analista sea la respuesta. En REPAIR se
enumeran vecinos de una edición de la guarda del padre manteniendo HOLD;
se ordenan por cobertura de casos ganados y exposición a contextos perdedores,
con reservas de diversidad. Esos valores sirven para ordenar; no predicen
con certeza el efecto del hijo. Se registran candidatos inspeccionados,
retenciones, cobertura del catálogo y truncamientos. El límite de 64 puede
introducir un cuello de botella: su efecto se medirá y no se ocultará.

Se excluyen duplicados exactos normalizados del historial visible y guardas
que no cambian ningún consumo HOLD de las trayectorias completas pertinentes
de la base. Cada exclusión por inactividad llevará un certificado reproducible
de base, lugar de consumo, casos completos y valores comparados. Su validez
depende de que esa sea la única intervención; no se extrapola a otras bases
ni a casos nuevos. Una firma igual en una muestra no autoriza eliminar una
regla activa. Tampoco se elimina una regla por coincidir con un contexto de
una partida que perdió: ese contexto puede no ser la causa.

El LLM seleccionará una propuesta completa de ese catálogo mediante un ID
tipado bajo gramática restringida. El recibo conservará catálogo, orden,
propuesta escogida, bytes de salida y reconstrucción exacta. El juez verá
esa propuesta, sin reparaciones posteriores silenciosas. B24-G recibe el
mismo constructor y selecciona determinísticamente, permitiendo medir el
aporte del LLM sobre el sintetizador. Los recorridos divergirán cuando sus
resultados diverjan; no comparten resultados entre brazos.

Si el catálogo se agota, se registra `NO_ELIGIBLE_CANDIDATE`, con el coste de
inspección y la plaza consumidos. No se rellenará con una solución histórica
ni habrá reintentos gratuitos. Los filtros reducen desperdicio conocido;
no aseguran que las propuestas restantes sean buenas. El cambio de interfaz
de generar JSON libre a seleccionar propuestas se declara como tratamiento
B24 y exige la referencia R4 para medir su efecto conjunto.

Dentro de I, cada investigador filtra contra su propio historial. Un registro
global de duplicados revelaría información de sus compañeros y contaminaría
el control. En C, los recibos y propuestas ajenas solo se incorporan tras
la barrera de intercambio de la ronda. Las coincidencias que ocurran antes
se conservan y contabilizan. No se intercambian resultados entre condiciones.

### Feedback que permita reparar condiciones

El dossier del padre contendrá todos sus efectos por partida y los rangos
completos de las features variables de sus consumos. Además conservará
vectores conjuntos reales mediante una selección por cobertura, contando
los omitidos. Así se evita que los extremos de la primera feature alfabética
ocupen todo el resumen. Los contraejemplos de todos los casos perdedores del
padre sobreviven al resumen; no solo los dos peores del último intento.

Se distinguirán: guarda que coincide, valor realmente consumido que cambia,
primera acción diferente y consecuencia final. Si las trazas disponibles
solo permiten asociar un consumo con una pérdida posterior, se marcará
atribución incierta. La fase inicial no añadirá intervenciones contrafactuales
gratuitas ni leerá estados secretos del mundo. Necesitar un replay alternativo
abriría una partida contabilizada bajo una ampliación previa del presupuesto.

El contexto máximo sigue siendo 8.192 tokens de entrada, 768 de salida y
9.216 de ventana con los tokenizadores verificados. Se medirán los bytes
reales de cada petición. Si el dossier y el catálogo esenciales no caben,
la preparación se detiene; no se recorta silenciosamente un contraejemplo.
Un fallo de transporte, parseo restringido o reconstrucción del catálogo es
un fallo instrumental, separado de un rechazo científico.

## Implementación y comprobaciones antes de jugar

Las piezas nuevas tendrán nombres B24 y un paquete propio. Se reutilizan los
ejecutores verificados; B23-R4 y sus 88 fuentes quedan intactos. El código del
investigador no importará artefactos humanos ni resultados del analista.
El formato B24 de propuesta/selección tendrá su contrato y recibos por hash.
El paquete de investigación excluirá los controles humanos B20, la autopsia,
sus CSV y cualquier reserva. El arnés custodio podrá referenciar hashes de
procedencia; el investigador solo recibe la base permitida y su archivo
autorizado. Se comprobará la ausencia de esos artefactos en el paquete y los
bytes efectivos de cada petición, no solo la redacción de las instrucciones.

| Trabajo | Prueba que debe pasar |
|---|---|
| Constructor y máscara de candidatos | Una regla inactiva y un duplicado exacto quedan excluidos; una regla activa con firma parcial coincidente sigue siendo investigable; cada descarte tiene motivo y coste. |
| Semántica y formato | Pruebas sintéticas de selección por ID, reconstrucción exacta, rechazo de ID ajeno, padre correcto y HOLD fijo en REPAIR. Los casos no contienen soluciones científicas. |
| Archivo y recuperación | Un ensayo inactivo posterior no elimina el dossier del padre +4 ficticio; un padre no concede su ganancia al hijo. Un linaje importado conserva autor y cuotas. |
| Resumen | Fixtures donde `goal_evidence` varía antes de `world_events` conservan los rangos de ambos, todos los casos perdedores y ejemplos conjuntos reales. No se inventan consumos. |
| Cooperación y aislamiento | I no puede leer el archivo ajeno; C solo recibe lo cerrado en su ronda; catálogo, orden y prompts se reconstruyen desde esos bytes. |
| Contabilidad y recuperación | Descartes, abstenciones, inferencias fallidas, duplicados entre investigadores y partidas interrumpidas dejan recibo; una recuperación no cambia contrato ni reusa un resultado de otra política. |
| Verificador | Paridad de base 61, criterio ≥2 y cero regresiones, score recalculado, replay y caché auditora independientes. El investigador no escribe el juez. |

El primer preflight remoto reservará ocho llamadas sintéticas del modelo
elegido: cuatro para el JSON de la referencia R4 y cuatro para selección y
reconstrucción por ID en B24, fuera de la historia científica. Su reserva está
incluida en el máximo de llamadas. Una prueba local del formateador no sustituye
esas ocho inferencias reales. Las pruebas de resumen y archivo pueden usar fixtures
artificiales con números de la autopsia, sin incluir el control humano ganador.
La mini terminal registrará observación, selección, propuesta y resultado
medidos mediante los mecanismos de visibilidad existentes.

Antes de congelar hay que concretar en el contrato ejecutable semillas,
orden de brazos y del catálogo, algoritmo de cobertura, manifiestos y
reglas de selección de finalistas. El plan no equivale a un paquete listo.
La primera implementación debe comprobar primero esas piezas baratas y
solo después permitir el micro completo.

## Memoria, crédito y verificación

El archivo compartido conservará identificador de propuesta y padre,
programa exacto, autor, contexto, resultados por caso, pérdidas, coste y hash
del recibo. Separará hipótesis, mediciones y políticas aceptadas. Las ganancias
de un padre nunca se atribuirán a un descendiente sin evaluarlo.

El intercambio utilizará estructuras existentes y mensajes de investigación;
no añadirá otro bus al núcleo ni activará un LLM en NEXUS-0. Los prompts
exactos serán auditables. El visor mostrará observaciones, propuestas,
explicaciones declaradas y resultados; no inventará pensamientos internos.

En el primer contraste, el reparto de plazas será fijo. Queda reservada una
ablación posterior para asignarlas por contribución verificada: una mejora,
una reparación útil o un contraejemplo reproducido. El desacuerdo verbal y
la mera acumulación de fallos no acreditarán competencia. Las contribuciones
compartidas conservarán su linaje para no premiar varias veces la misma idea.

La recompensa de investigación y el criterio de promoción estarán separados.
Seleccionar propuestas, actualizar memoria o dar más oportunidades a una rama
no modifica los pesos del LLM. Entrenarlos mediante RL o ajuste fino corresponde
a otro contrato, en la línea futura RSI-2.

El juez seguirá fuera del alcance de escritura de los investigadores. La
aceptación conservará ganancia de al menos dos niveles y ninguna pérdida
individual de niveles o score, con la tolerancia registrada, replay y
auditoría. Las ramas rechazadas podrán orientar investigación sin cambiar
la política estable. Un resultado inconcluso será «no resuelto con este
presupuesto»; declarar imposibilidad requeriría un certificado verificable
en un dominio acotado, sin puntos gratuitos por abandonar.

## Medición y cierre que habría que congelar

El primer diagnóstico propuesto usa las mismas 14 partidas de desarrollo
conocido de R4. Haberlas estudiado para diseñar B24 se declara explícitamente.
Las 160 partidas amplias también son desarrollo conocido; el éxito en ellas
no se presentará como transferencia nueva. Los 80 casos de conservación
requieren revisión de exposición y permiso de lectura de la política exacta
tras cualificación. No alimentan el investigador ni el analista de búsqueda.

Con cinco condiciones y una semilla de investigación, el techo propuesto es:

| Etapa | Máximo de partidas físicas |
|---|---:|
| Micro: 5 × (base + 18 candidatos) × 14 casos × 3 ejecuciones | 3.990 |
| Desarrollo amplio: base común + hasta 5 finalistas, 160 × 3 | 2.880 |
| Conservación: base común + hasta 5 finalistas, 80 × 3 | 1.440 |
| Total condicionado | 8.310 |

Hasta 72 llamadas científicas en los cuatro brazos con LLM y ocho de formato:
80 en total. G tiene el mismo techo de propuestas/partidas y cero tokens;
no se fingirá igualdad de gasto LLM. Los tres brazos S/I/C sí tienen iguales
límites de llamadas, tokens, CPU del constructor y partidas. Los costes
realizados de cada componente se reportan por separado. R4-REF reproduce el
desperdicio del diseño anterior como referencia, con todos sus costes.

Una plaza duplicada, agotada o inactiva no cede su reserva a otra condición.
No se usa el máximo de partidas como obligación de gastarlas: cada brazo se
detiene al primer pase auditado; fases posteriores se abren solo tras pase.
Un fracaso completo del micro cierra la condición sin lanzar una campaña.
La duración se calcula tras calibración del ejecutor real y se publica con
incertidumbre; una GPU mayor no justifica extrapolar las simulaciones CPU.

Se contará cada propuesta inválida, repetida o rechazada y cada llamada,
token, partida, replay, auditoría y comprobación adicional. Un coordinador
LLM, si se añadiera en otra condición, consumiría el mismo presupuesto total.
El contraste inicial no necesita un cuarto LLM coordinador.

Los indicadores serán: pases sin regresiones, tiempo y gasto hasta el primer
pase, niveles y score por caso, diversidad de propuestas, duplicados,
reparaciones útiles y supervivencia en desarrollo amplio y reserva nueva.
Se reportará tanto éxito dentro del presupuesto como coste realizado.

Antes de medir se fijarán modelo y hashes, cohortes y exposición histórica,
semillas de investigación, orden, límites totales de cómputo, reglas de parada,
selección de finalistas y criterio estadístico. La calibración tendrá datos
separados y no se incorporará después como confirmación. Una sola ejecución
serviría para diagnosticar el instrumento, no para afirmar superioridad.
El tamaño de la confirmación se dimensionará antes de abrir su reserva.

La selección usará solo desarrollo. Se congelarán todos los finalistas antes
de validarlos; las pérdidas reservadas no se devolverán al enjambre ni se
sustituirá al ganador tras verlas. Un fallo de integridad o replay detendrá
el ensayo y quedará separado de un resultado científico negativo.

Cooperativos frente a independientes medirá la aportación del intercambio.
Independientes frente a individual medirá el efecto de dividir contextos.
Si cooperativos no supera ambos controles con coste y conservación
comparables, no se acreditará ventaja de cooperación. Ninguno de esos pases
sustituirá piloto, campaña y examen B1–B5 para el cierre de S6.

S frente a R4-REF medirá el efecto conjunto de corregir la búsqueda y el
feedback; no separa todavía cada corrección. S frente a G medirá la utilidad
de seleccionar con LLM sobre el mismo generador. Si hace falta atribuir el
efecto a una corrección concreta se declarará una ablación antes de verla;
no se deducirá del resultado agregado del paquete.

La expectativa inmediata es reducir repetición/inactividad y sostener
reparaciones de condiciones. Obtener una ganancia conservadora es una
hipótesis. Si el catálogo activo se queda sin variedad o las reparaciones
solo intercambian unas pérdidas por otras, se medirá cobertura y suficiencia
de las features antes de proponer un nuevo lenguaje. No se abrirán reservas
para buscar la solución. El control humano de +6 prueba capacidad en el
desarrollo conocido, no que esta búsqueda vaya a descubrirla.

## Destino si B23 funciona

Se conserva como decisión histórica; R4 ya cerró sin pase, por lo que el
trabajo inmediato permanece en B24.

La misma propuesta pasará a ECHO-5, especialmente su línea 5.1 de organización,
memoria compartida y eficiencia. ECHO-5.5 estudiará retención entre sesiones;
RSI-1, mejora del investigador; RSI-2, actualización de adaptadores o pesos.
No se presuponen inteligencia general, alucinaciones cero ni mejora recursiva
por el mero hecho de aumentar el número de agentes.

Fuentes de la discusión previa: [OpenAI, incidente y medidas](https://openai.com/index/hugging-face-incident-and-the-road-ahead/),
[investigación independiente de METR](https://metr.org/blog/2026-08-26-openai-hugging-face-incident-investigation/),
[autojuego multiagente con entrenamiento PPO](https://openai.com/index/emergent-tool-use/)
y [comparación controlada de arquitecturas de agentes](https://arxiv.org/abs/2512.08296).
Sirven como antecedentes; no son resultados obtenidos por ECHO.

La corrección posterior a R4 se apoya principalmente en la autopsia local.
Como referencias metodológicas se han consultado
[CEGIS, Solar-Lezama](https://people.csail.mit.edu/asolar/SynthesisCourse2020/Lecture10.htm)
y [Reflexion](https://arxiv.org/abs/2303.11366). La analogía es empírica;
ninguna de esas publicaciones acredita este B24 ni garantiza conservación
fuera del banco medido.
