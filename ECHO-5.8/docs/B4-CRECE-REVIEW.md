# B v4 · CRECE — revisión del método y encaje en ECHO-5.8.2

21 de octubre de 2026. **REVISIÓN documental y de código; sin implementación,
sin llamadas a modelos, sin ejecuciones de desarrollo ni de examen.**

Documento revisado: [B4-CRECE-METODO.md](B4-CRECE-METODO.md), junto con
[B4-LLM-PIEZAS-PROPUESTA.md](B4-LLM-PIEZAS-PROPUESTA.md), el traspaso,
el contrato y resultados de ACUMULA-3 y su código existente. No se modifica
el método ni ningún archivo congelado. Las soluciones de abajo son propuestas
para decidir antes de programar; no son decisiones ya aprobadas.

## Dictamen

La separación «el córtex propone; comprobaciones mecánicas limitan el código;
ECHO mide las consecuencias; se conserva cada campeón» encaja con el proyecto.
El método todavía necesita concretar la interfaz de F0 y corregir varias
reglas antes de que sus resultados puedan interpretarse como crecimiento.

**No recomiendo comenzar F0 con las dos firmas actuales como especificación
suficiente.** Sí recomiendo mantener F0 como primera tarea técnica, después
de resolver los hallazgos 1 y 2 y aprobar su alcance. No requiere llamar a un
LLM. Los demás hallazgos deben resolverse antes de las fases a las que afectan.
Esta revisión no autoriza por sí misma F0, un prototipo ni un examen.

## 1. Bloqueo de F0: la interfaz no representa todavía las cinco piezas

Referencia: método §3.1; `echo58/b3/policy.py`, especialmente líneas 87–101,
120–145 y 153–194.

Las piezas no están todas dentro de `_decide`, como dice el método:

- `no_repick` actualiza prohibiciones durante `_outcome` y las consulta en
  `belief`. Depende de efectos que duran más de una decisión.
- `commit` y `no_retoggle` cambian prohibiciones, invalidan la caché de
  creencias y vuelven a consultar la política, con un orden y una cota
  concretos. Filtrar una intención final no reproduce necesariamente eso.
- `clear` sustituye `_drop`, prueba conectividad y puede generar movimiento
  hacia una casilla de suelta durante hasta ocho pasos por identificador.
- `wander` sustituye una acción ociosa por movimiento hacia una casilla
  alcanzable. Ese movimiento no tiene por qué existir en una lista de
  candidatos de la política base.

Por tanto, `prefer(cands, v)` sobre «opciones que ya propone la política»
no basta para prometer equivalencia. Heredar de PAgent y dejar activadas sus
piezas originales tampoco demostraría que las piezas reescritas funcionan:
el comportamiento podría seguir viniendo del código original.

**Propuesta para cerrar F0:** describir primero qué candidatos ofrece el
adaptador, en qué momentos se evalúan piezas, qué efectos discretos admite
el runtime y quién actualiza contadores y prohibiciones. Las piezas deben
seguir siendo funciones puras; el runtime puede aplicar efectos explícitos,
acotados y auditables. Si se amplía el generador de candidatos, declarar que
esa capacidad es parte del adaptador común y medirla también sin piezas.
Resolver esta elección antes de programar.

La equivalencia debe comparar acciones primitivas, intenciones, resultados y
estado relevante del episodio, no solo éxito o daño. Fijar casos de desarrollo
que ejerciten cada pieza y sus combinaciones. Comparar también el adaptador
sin piezas con la base sin piezas. No usar semillas de exámenes cerrados.

## 2. Bloqueo de F0: faltan semántica de composición y frontera del veto

Referencia: método §3.1 y §7.

«Primero los vetos y luego prefer» no define qué ocurre con varias funciones
prefer, empates, abstenciones, candidatos vacíos o índices fuera de rango.
Hay además dos firmas distintas entre documentos: la nota anterior devuelve
un candidato; el método devuelve un entero. Falta fijar también si una
intención representa un objetivo de varios pasos o una primitiva.

La regla «si todo queda vetado, ignorar los vetos» solo puede aplicarse a
restricciones aprendidas que se hayan definido como revocables. Nunca puede
anular una prohibición del núcleo, del entorno o de una comprobación de
seguridad independiente. Si se mantiene, debe llamarse y medirse como tal;
no presentarla como garantía de seguridad.

**Propuesta:** contrato explícito para entrada/salida, orden estable y
abstención; conjuntos inmutables de candidatos válidos; tratamiento definido
de errores y presupuesto agotado en cualquier llamada real, no solo en el
banco previo. El fallback debe respetar siempre las restricciones duras y
registrar el fallo de la pieza. El snapshot de `v` debe ser inmutable también
en sus estructuras anidadas y no exponer el objeto agente ni métodos con
capacidad de modificarlo.

## 3. Importante antes de F1: AST y 200 estados no prueban seguridad general

Referencia: método §3.2 y §7.

La comprobación mecánica puede asegurar propiedades concretas del lenguaje
y detectar fallos; no demuestra que una conducta sea segura en cualquier
mundo. Un proceso aparte con límites tampoco define, por sí solo, qué
recursos del host puede alcanzar.

Faltan cotas para longitud del programa, profundidad, tamaño de enteros,
colecciones, rangos, operaciones costosas y composición de varias piezas.
Una pieza puede pasar 200 casos y fallar en un estado posterior.

**Propuesta:** lenguaje y llamadas permitidas enumerados, intérprete
restringido o aislamiento con capacidades explícitas, límites por invocación
y por decisión completa, y política de fallo aplicada siempre. Separar las
promesas: integridad del runtime, recursos acotados y ausencia de regresión
observada en las partidas son comprobaciones distintas. No prometer seguridad
universal por haber pasado AST, sandbox y una puerta finita.

## 4. Importante antes de F1: puerta, adaptación y aprendizaje necesitan definición

Referencia: método §3.3 y §4; `echo58/acumula3/bench.py:98–109`;
`echo58/acumula2/bench.py:55–60`; `echo58/memx/agent.py:127–140`.

La puerta de B v3 acepta mejora estricta en daño, éxito **o desperdicio**,
sin empeorar daño ni éxito. CRECE exige bajar fallos. Es una puerta nueva y
más restrictiva: debe declararse como elección nueva, no como equivalencia.
A número de episodios fijo, fallos = episodios − éxitos; exigir menos fallos
no es un segundo criterio independiente del aumento de éxitos.

«Sin aprender» en la validación existente significa que no se pasa una
memoria persistente como `learn`. Siguen existiendo evidencia y cambios del
episodio. Desactivar también ese estado rompería la comparación con B v3.
La sonda de B v3, además, aprende en una copia por familia que luego se tira.
Hay que distinguir ambos protocolos y restaurar snapshots idénticos por brazo.

Semillas frescas por generación no evitan por sí solas el ajuste adaptativo
si el LLM recibe los motivos de rechazo y puede reintentar indefinidamente
contra las mismas semillas de esa generación.

**Propuesta:** presupuesto fijo de propuestas, reparaciones, llamadas y
partidas, con reglas de parada; separar datos para proponer, validación de
promoción y sonda informativa. Definir qué respuesta de la puerta vuelve al
LLM. Cerrar el margen por familia y todas las reglas de promoción antes del
prototipo correspondiente. Registrar tiempo y coste añadido de cada pieza.

## 5. Importante antes de F1: no descartar para siempre piezas rechazadas

Referencia: método §3.2; [ACUMULA3-RESULTS.md](ACUMULA3-RESULTS.md), Q4.

B v3 documentó, en 10 de 10 macros, una edición aceptada después de haberse
probado y rechazado en una ronda anterior. Prohibir para siempre una pieza
rechazada elimina precisamente esa posibilidad cuando cambia el campeón.

Coincidir sobre 200 estados tampoco demuestra igualdad de comportamiento
fuera de esos estados. Puede ocultar una condición que aún no apareció.

**Propuesta:** separar duplicado de código, coincidencia en muestras y rechazo
contextual. Un rechazo de rendimiento debe quedar asociado al hash del campeón,
memoria, piezas activas y evaluación; no convertirse en una prohibición global.
Una pieza aceptada pero desactivada tras poda puede volver a ser candidata en
otro contexto. Todo se conserva con recibos, sin borrar.

## 6. Importante antes de F2/F3: el examen y la caché congelada son ambiguos

Referencia: método §2, §5 y §6.

El método pide examen separado del bucle, curva de examen por generación y
caché de prompts/respuestas congelada antes de examinar. Si el examen generase
nuevas fichas de fallo, esos prompts no se conocerían antes de la congelación.
Pedir una nueva respuesta tampoco es utilizar una caché ya congelada.
Temperatura cero no sustituye conservar la respuesta exacta.

**Propuesta coherente con «biblioteca que viaja sin LLM»:** producir en el
bucle de entrenamiento/validación los campeones g0…gG; congelar todos sus
snapshots, código, memoria y recibos; examinar esos snapshots en un único
protocolo reservado, con el córtex apagado. Ningún resultado del examen vuelve
a propuestas o promociones. Especificar el reinicio entre snapshots y si la
adaptación dentro de cada episodio está permitida. La curva compara snapshots
ya fijados, no selecciona nuevas generaciones a partir del examen.

Si se quiere medir aprendizaje generacional durante el examen, es otra
pregunta: necesita una fase de adaptación explícitamente autorizada y una
partición posterior de evaluación intocable. No mezclar ambos diseños.

## 7. Importante antes de F2/F3: controles y conclusiones estadísticas

Referencia: método §5 y §7.

- `sin_relevo` mezcla dos cosas: actualizar el campeón y actualizar las fichas.
  Aclarar si el aspirante se aplica siempre sobre g0 o sobre el campeón actual.
  Mantener separado qué se cambia para atribuir el efecto.
- `acepta_azar` necesita una regla para igualar la tasa o el número de
  aceptaciones sin usar información futura. Todas sus piezas siguen pasando
  la comprobación mecánica y las restricciones duras; solo se retira la puerta
  empírica cuya aportación se quiere medir.
- Declarar qué pasa con las ediciones de memoria de B v3. Si varían junto a las
  piezas, su mejora puede explicar parte de la curva. Mantener el mecanismo
  igual entre brazos o introducir la ablación necesaria.
- Contar reparaciones, invalidaciones, fallos de API, cache hits, duplicados,
  propuestas de poda y evaluaciones; «mismo presupuesto» necesita unidades y
  límites exactos. El número de llamadas estimado no sustituye esa definición.
- Las cinco piezas de B v3 son una referencia diseñada externamente, no un
  techo demostrado. No superar estadísticamente una referencia no demuestra
  empate ni no inferioridad. Fijar margen y criterio de no inferioridad por
  separado de las pruebas de superioridad, y tratar empates e incertidumbre.
- El comparador `sin_fichas` retira fichas de esta tarea; no elimina el
  conocimiento previo del LLM ni el diseño humano de API, ejemplos y banco.
  Hablar de piezas sin edición manual bajo este protocolo, no de ausencia de
  intervención humana ni de automejora general.
- En mundos de placa, una evaluación individual puede ser irresoluble por
  construcción. La transferencia debe fijar tareas alcanzables, capacidades
  disponibles e interfaces compatibles antes de medir; no penalizar una
  biblioteca por necesitar un compañero que no existe en el brazo individual.

## 8. Importante antes de podar: una ablación también puede cambiar el campeón

Referencia: método §3.4.

Que varias piezas sean redundantes al quitarlas por separado del mismo campeón
no implica que se puedan quitar todas juntas. La poda necesita orden y puerta
para la configuración que realmente quedará activa; su presupuesto cuenta.

La biblioteca portable necesita, además de hashes de piezas, versión/hash del
runtime, esquema de `v`, política base, memoria y orden de composición. Una
prueba de carga en proceso limpio, sin API y con las mismas trazas, verifica
la persistencia. No basta con conservar el archivo de código.

## 9. Fases y aprobaciones

La cabecera pide contrato antes de programar el experimento; la tabla sitúa
F1/F2 antes del contrato científico de F3. El §9 permite expresamente F0 sin
contrato, después del sí de Nav.

Distinguir dos cosas: F0 puede tener una especificación técnica y aprobación;
F1/F2 pueden ser pilotos de desarrollo sin contrato de examen, pero necesitan
un protocolo previo y una autorización explícita que delimiten datos,
presupuesto, puerta y parada. No resolver esa ambigüedad llamando «prototipo»
a un experimento ilimitado. La presente petición autoriza esta revisión.

## 10. Estado del trabajo restante y nombre 5.8.2

El nombre ECHO-5.8.2 agrupa aquí el trabajo pendiente indicado por Nav;
no convierte sus planes en una versión ya terminada o verde.

| Pista | Estado que corresponde hoy |
|---|---|
| ECHO-5.8: A, B v3 y C v1 | Verdes en examen según sus informes y verificaciones; se conservan intactos. B v1 y B v2 siguen rojos. |
| C v2, mentiroso | Sin contrato; el 181 → 1 pertenece a LINK-3 y no demuestra aún protección de la global de ENJAMBRE. |
| B v4, CRECE | Método propuesto; esta revisión identifica decisiones previas. No hay prototipo, contrato ni resultado nuevo. |
| D1 y D2 | Pendientes de contratos. Modelos elegidos según los documentos; disponibilidad y cuota no se han comprobado en esta revisión. |
| P, PERCIBE-X | Plan sin contrato: aprendizaje en vuelo en SITL, más familias y después identidades como claves de memoria. No hardware real. |
| W, WSP | Meta propuesta: ≥15 % de ahorro frente al mejor control JSON equivalente. Cualquier ensayo ARC posterior necesitaría su propio protocolo; no reabrir la campaña cerrada. |
| V, VISUALIZA | **Primera entrega implementada, revisada por Nav y publicada**, commit web `4867b1c`: reproducción de desarrollo, consultas, inspector WSP, tres gráficas, dos Mermaid y estado del proyecto. Ampliaciones futuras se pueden definir aparte. |
| E, deudas | Autopsias y cierres pendientes según el roadmap; SHIELD-2 sería un contrato nuevo. |
| Aparcado | Hardware real, ARC-2 y S6 antiguo, sin reetiquetar sus antecedentes. |

No se cambia el roadmap, el método, la numeración del código ni la web con
esta revisión. La entrega pública de VISUALIZA no publicó el nuevo método
CRECE ni una versión científica 5.8.2. ECHO-5.9 sigue siendo el frente separado
de WORLDBENCH; su examen permanece reservado.

## Próximo paso recomendado

Resolver y aprobar la especificación técnica de F0: candidatos, puntos de
extensión, estado persistente del episodio, composición y equivalencia real.
Después implementar solo ese adaptador en una carpeta nueva y comprobarlo
con semillas de desarrollo visibles en la mini terminal. No llamar al LLM,
medir cuotas ni iniciar F1 como consecuencia automática de aprobar F0.
