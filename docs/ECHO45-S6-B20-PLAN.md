# S6-B20 — capacidad, búsqueda y conservación

6 de octubre de 2026. **Diseño propuesto, sin congelar ni ejecutar.** Es una
condición nueva después del rechazo auditado B19. Investigación privada.
[Diagnóstico que motiva el diseño](ECHO45-S6-B19-FORENSICS.md).

La pregunta primaria será si una búsqueda con memoria de varias hipótesis y
una biblioteca de guardas explícita encuentra una mejora conservadora desde
el mismo programa basal. La pregunta secundaria será cuánto aporta el LLM.
Ni una guarda escrita por el investigador ni un control de capacidad pueden
presentarse como descubrimiento autónomo.

**Paso 0: contrato ejecutable y comprobaciones antes de gastar GPU.**
Crear fuentes B20 aisladas. Mantener intactas B18/B19 y sus dependencias
congeladas; una ampliación de guardas debe vivir en otro módulo con inyección
explícita de dependencias. Evitar herencias dinámicas que importen inadvertidamente
la gramática anterior. El manifiesto debe cubrir toda la dependencia transitiva,
incluidos validador, certificados, modelo, runner, límites y particiones.

Las fixtures de B19 servirán como desarrollo retrospectivo. Exigir pruebas que
detecten: objetivo +1 perpetuo; pérdida de una rama con +4; más descendientes
que el límite; empates resueltos siempre por orden textual; guarda permitida
pero no enumerable; certificado construido con otra biblioteca; cambio tardío
de estado; coste negativo estimado cero que no significa conservación real.
Los tests no deben exigir seleccionar una solución conocida ni emplear índices
de casos para guiar el controlador.

**Paso 1: comprobar capacidad antes de culpar al investigador.**
Diseñar un control dirigido en desarrollo, separado del experimento autónomo.
Enumerar un conjunto acotado y reproducible de conjunciones de una, dos y tres
features distintas, con umbrales declarados. Puede generarse perezosamente;
no es necesario materializar millones de programas. Separar el máximo
sintáctico del máximo realmente medido. Si se muestrea, registrar selección,
estratos, semillas y cobertura. No presentar un muestreo como exhaustividad.

Comparar biblioteca antigua y ampliada bajo igual presupuesto. Incluir las
guardas ausentes del informe solo como controles humanos de cobertura, con
etiqueta explícita y sin insertarlas en prompts, prioridades o respuestas del
ensayo autónomo. Los resultados de capacidad pueden informar una nueva decisión
de diseño; no pueden filtrarse después de congelar la prueba de descubrimiento.

Primero ejecutar en desarrollo el prefijo basal exacto y después simular la
nueva política. Las trazas antiguas no predicen los estados que esa política
creará. Un diagnóstico de una intervención aislada puede fijar todo salvo una
lectura, restaurando agente, entorno, memoria y RNG; debe reproducir la rama
original antes de interpretar el contrafactual. Los snapshots privados no
entran como observaciones del agente. Si no hay snapshot completo fiable,
repetir la partida con la intervención instrumentada y declarada en desarrollo.

El éxito de este paso exige +2 niveles y cero pérdidas individuales en el
banco declarado, replay y luego comprobación amplia. Si no aparece, informar
el espacio medido y detener la promoción. No encadenar por defecto otra campaña.
Si los estados positivos y negativos requieren respuestas distintas con las
mismas features, investigar observaciones temporales antes de ampliar cómputo.

**Paso 2: cambiar el investigador sin cambiar el juez.**

| Pieza | Cambio propuesto | Criterio verificable |
|---|---|---|
| Archivo de hipótesis | Conservar varias ramas no dominadas por ganancia, pérdidas y coste, con su procedencia | Una rama reparable no desaparece por empeorar provisionalmente otra métrica |
| Selección | Presupuesto por rama y retorno tras estancamiento; reservar exploración de mecanismos | No repetir diez veces el mismo objetivo sin una decisión de continuidad justificada y acotada |
| Evidencia | Separar lectura, intervención efectiva, divergencia y coste por nivel | No etiquetar todas las lecturas de una partida perdida como causas de pérdida |
| Crédito | Mantener negativos por base, operador, valor y linaje; otras experiencias son advertencias | Una pérdida HOLD=1 no certifica que HOLD=4 sea imposible |
| Ganancia prevista | Conservar ganancias de distintas ramas, con incertidumbre; no sumar composiciones sin medir | Predicción y resultado se registran por separado; se mide su calibración |
| Biblioteca | Conjunciones declaradas sin anclajes obligatorios; enumeración igual para brazos comparables | Validador, generador, límites y certificados usan la misma versión |
| Evidencia disponible | Sintetizador usa desarrollo propio completo; prompt recibe resumen con procedencia y cobertura | Ninguna solución desaparece solo por no afectar a tres ejemplos arbitrarios |
| Experimentos | Contrastes guardafija/valordistinto y valorfijo/guardadistinta; exploración separada | Puede atribuirse cada cambio de resultado al factor modificado en el contraste |
| Repeticiones | Huellas de conducta y casos reparados; poda únicamente con prueba válida | Equivalencia observada informa estancamiento, no una garantía en estados nuevos |
| Agotamiento | Salida explícita cuando faltan hipótesis o presupuesto | No hay bucles infinitos, candidatos duplicados gratuitos ni ascenso silencioso de límites |

La cola no debe optimizar un único escalar que esconda regresiones. V3 continúa
exigiendo +2 y ninguna pérdida individual. Puede priorizar hipótesis de reparación
que aún fallan; estas no se integran en el agente aceptado. Combinar dos parches,
si resulta necesario, exige otro subcontrato común a todos los brazos, evaluación
de precedencia/interacciones y respeto al límite de 32 reglas.

**Paso 3: ablación y descubrimiento desde el arranque real.**
El control de capacidad no basta. Propuesta de micro factorial con cuatro brazos:

| Brazo | Primera propuesta | Búsqueda posterior |
|---|---|---|
| C0 | Inicializador determinista | B19 |
| C1 | Inicializador determinista | B20 |
| H0 | Propuesta LLM compartida con H1 | B19 |
| H1 | La misma propuesta que H0 | B20 |

Usar la misma biblioteca en los cuatro brazos de esta comparación para aislar
el buscador; la biblioteca antigua/nueva se compara separadamente en el paso 1.
Empezar del programa basal y su historia aceptada, sin una guarda exitosa
preinsertada. No compartir feedback entre brazos. Tres semillas LLM predeclaradas
permiten observar sensibilidad al arranque; la duplicación de un inicializador
determinista no se cuenta como tres muestras estadísticas independientes.

Esta primera ablación mantiene una llamada inicial por par H0/H1. Si se quiere
un LLM que critique durante el bucle, registrarlo como subcondición posterior:
mismos turnos y tokens máximos para controles comparables, todos los errores
y reintentos contabilizados. No mezclar a la vez cambio de modelo, lenguaje,
nuevas features y controlador sin controles que distingan sus efectos.

Congelar antes de medir: número de propuestas por brazo, topes de expansión
de gramática, partidas, CPU, wall time, tokens y llamadas. Calibrar primero el
coste del nuevo generador y de casos rápidos/lentos; las doce oportunidades B19
son una referencia, no evidencia de presupuesto suficiente. El presupuesto debe
incluir candidatos rechazados, replays, auditoría y reinicios del proceso.
Reportar también gasto real, ya que un sintetizador no consume el cupo LLM.

Métricas: primer candidato que pasa por coste acumulado; ganancia; vector de
regresiones; acciones y reinicios por nivel; propuestas y conductas distintas;
ramas exploradas; error de predicción; tokens, segundos CPU y GPU. Un empate
se registra como empate. La mejora del buscador puede ser útil aunque no haya
una contribución propia del LLM.

**Paso 4: cualificación amplia y reserva.**
Congelar la regla de selección de candidato antes de ver resultados. El primero
que pase el micro se prueba en desarrollo amplio con replay y auditoría. Si falla
esa ampliación y se decide usarla para reparar, cerrar esa condición como negativa
y declarar el siguiente entrenamiento: no conservar la apariencia de prueba ciega.

Solo después se mide conservación en datos nuevos. El B de B19 no se abrió según
sus recibos, pero comprobar todo el registro de exposiciones antes de reutilizarlo;
si no puede acreditarse, asignar otra partición. Separar la cuenta del evaluador
de la del buscador y no enviar los resultados por caso ni los IDs a la selección.
Incluso un bit repetido de aceptación puede sobreajustar: limitar intentos protegidos
y no escoger otro candidato después de inspeccionar un rechazo.

El desarrollo de doce casos está sesgado deliberadamente hacia fallos conocidos.
Exigir casos nuevos de las mismas familias, controles de coste sin fallos,
variantes observables y retención de habilidades anteriores. Reportar análisis
por familia sin convertirlo en nuevos umbrales después de ver datos.

**Paso 5: S6 completo.**
Una cualificación B20 positiva habilita la siguiente fase, no `s6_green=true`.
El piloto emparejado, su auditoría, la campaña, su auditoría y el examen de
SEMILLA/FIJO/ECHO/SIN FILTRO mantienen los criterios originales:

- B1: ECHO alcanza al menos 105 % de los niveles SEMILLA y no reduce score medio.
- B2: ECHO supera a FIJO en niveles.
- B3: ECHO supera a SIN FILTRO en niveles.
- B4: conserva niveles y score del conjunto oficial de desarrollo reservado a retención.
- B5: auditoría válida de fuentes, procedencia, presupuesto, ejecución y replays.

El micro parte de la base ya aceptada para aislar la reparación; piloto/campaña
deben respetar su punto de partida formal y demostrar el descubrimiento completo.
No sustituirlos por una campaña inicializada con el ganador escrito por el analista.
En la nueva condición, todos los brazos comparables tienen el mismo lenguaje,
límites y acceso permitido. SIN FILTRO deriva de las mismas propuestas ECHO y
solo mantiene los filtros de seguridad y ejecutabilidad establecidos.

**Riesgos que deben probarse antes del ensayo largo.**

| Obstáculo posible | Prevención o respuesta prevista |
|---|---|
| Explosión combinatoria al quitar anclajes | Generación perezosa, topes previos, métricas de cobertura; nunca ocultar un truncamiento |
| Ranking sigue atrapado en +1 | Fixture de rama estancada, cuotas por rama y reapertura de otra hipótesis |
| Características observables insuficientes | Pruebas de historias indistinguibles; subcondición de memoria temporal si procede |
| Contrafactual restaura mal el agente o RNG | Paridad completa antes de interpretar efectos; fallo del instrumento si difiere |
| Poda elimina una solución por certificado viejo | Incluir hash del lenguaje, base, datos y sitio de consumo; invalidar ante cambios |
| Memoria/caché compartida contamina brazos | Directorios y claves por condición, brazo y estado; pruebas de contaminación deliberada |
| Coste tardío mejora una parte y empeora otra | Medir partida completa y coste por nivel; mantener juez individual |
| Sobreajuste a 28027/28039 | Identificadores fuera de la política; variantes y nuevas particiones; separar diagnóstico y confirmación |
| Híbrido empata o pierde contra síntesis | Informar ausencia de ventaja; no excluir ese brazo ni repetir hasta ganar |
| ECHO no supera SIN FILTRO | Mantener B3 rojo; estudiar selección en desarrollo en condición posterior |
| Formato LLM, contexto o truncamiento | Gramática y tokenización comprobadas; objetivo y evidencia obligatorios; fallar explícitamente |
| Reinicio Kaggle duplica llamadas o partidas | Identificadores idempotentes y recibos atómicos; reservar presupuesto antes de ejecutar |
| GPU no disponible/cuota agotada | Registrar bloqueo de infraestructura; no mutar modelo/runtime silenciosamente |
| Mismo error compartido por ejecución y auditoría | Recalcular métricas independientemente; fixtures de referencia del entorno y revisión de invariantes |
| El criterio es inalcanzable en el lenguaje medido | Resultado negativo con cobertura declarada; ampliar representación en otra condición |

Kaggle privado puede reutilizar T4, modelo y runtime cualificados de B19. La
inferencia usa GPU; los juegos siguen siendo trabajo CPU. Cuatro workers son
el punto de partida calibrado, no una propiedad científica universal. Guardar
artefactos y recibos antes de borrar diarios temporales; verificar privacidad
y excluir credenciales del paquete. No contratar servicios ni publicar fuentes.
Solo el desarrollo usa el observador existente; ninguna instrumentación nueva
se introduce en reserva o examen.

**Expectativas.** Hay razones concretas para esperar mejor cobertura y menos
intentos redundantes. La ausencia de regresiones, la transferencia y la ventaja
del LLM son hipótesis abiertas. El mejor resultado B20 sería una mejora autónoma
conservadora reproducida en desarrollo amplio y reserva nueva. Un resultado
parcial útil sería demostrar que el lenguaje contiene una solución que el
investigador aún no encuentra, o localizar qué información observable falta.

No hay una hora de finalización porque no hay proceso B20 iniciado y su coste
depende de la calibración. Tampoco una probabilidad de verde justificable con
una sola trayectoria B19. B20 estará preparado cuando el contrato ejecutable,
las pruebas previas, el presupuesto y la regla de parada estén congelados.
