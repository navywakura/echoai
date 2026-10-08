# RXLABS_STATUS

**8 de octubre: B23-R4 en Kaggle; su puerta de formato pasó.**
N14 lleva tres propuestas ejecutadas sin ganancia ni pérdida en las 14 partidas
de desarrollo; la cuarta terminó medición y está en replay. N7 está pendiente. R3 había cerrado
con 2478 partidas y 36 respuestas inválidas. R4 corrige el formato y conserva
el umbral original; S6 y el cierre de ECHO-4.5 siguen pendientes.
[Estado](ECHO45-S6-B23-R4-STATUS-20261008.md) ·
[Contrato](ECHO45-S6-B23-R4-RECOVERY.md).
Los bloques siguientes conservan estados históricos fechados.

<!-- S6B23-BEGIN -->
**7 de octubre: B23 implementado; micro pendiente de los modelos.**
Cinco brazos: R22, M22, selector M23 y Qwen2.5-Coder 7B/14B.
42 pruebas B23 y 102 de regresión pasan; se verifica también el paquete aislado.
El instrumento real reproduce 61 niveles en 14 partidas, con replay y
auditoría independientes: 42 partidas, cero candidatos y cero LLM. Un primer
intento instrumental de otras 42 partidas queda supersedido por recibos mal
ubicados; el fallo está corregido y registrado sin alterar B22.
M23 conserva ramas de +1, sigue descendientes y filtra inactividad; el juez
mantiene ≥2 niveles extra y ninguna pérdida individual de niveles o score.
El ensayo admite hasta 18 propuestas por brazo, 36 inferencias y 8.310
partidas contando validaciones condicionadas. Los pesos 7B/14B verificados
no están disponibles y el entorno no resuelve Kaggle/Hugging Face.
No hay micro, campaña ni examen S6 ejecutándose desde esta implementación.
[Implementación y ejecución](ECHO45-S6-B23-IMPLEMENTATION.md) ·
[Contrato](ECHO45-S6-B23-MICRO-DESIGN.md) ·
[Comprobaciones](../lab/seed/s6b23-20261007/implementation-checks.json).
<!-- S6B23-END -->

<!-- S6B22-BEGIN -->
**7 de octubre: B22 cerrado y auditado; S6 sigue abierto.**
Cierre a las 14:31 Madrid: 11.976 partidas, cero llamadas LLM.
B22-V reproduce 52→56 en el micro y 740→748 en desarrollo amplio,
conservando niveles en cada partida, pero pierde score en los casos 144 y 154.
B22-S termina sin pases en 288 intentos de ocho pares R22/M22.
B22-N, B22-E, conservación nueva y examen no se ejecutaron.
La autopsia recalcula 924 mediciones: 79 propuestas eran inactivas sobre
la base; las 20 segundas reparaciones causaron pérdidas. El selector
descartaba ramas de +1 conservador y podía dejar sin explorar al mejor
descendiente. Un control humano B20 legal en B22 ya conserva +6 en el mismo
desarrollo amplio; falta descubrimiento autónomo y conservación nueva.
B23 implementa el micro comparativo; su ejecución espera los pesos 7B/14B.
[Resultados B22](ECHO45-S6-B22-RESULTS.md) ·
[Investigación reproducible](ECHO45-S6-B22-FORENSICS-20261007.md) ·
[Contrato del micro B23](ECHO45-S6-B23-MICRO-DESIGN.md).
<!-- S6B22-END -->

<!-- S6B21-IMPLEMENTATION-BEGIN -->
**6 de octubre: B21-A cerrado y auditado, sin promoción.**
110 propuestas y 4.212 partidas físicas, sin llamadas LLM; 70 fuentes intactas.
El segundo intento del control aleatorio descubre HOLD=2 bajo una guarda:
52 → 56 niveles, sin pérdidas en las 12 partidas del micro. Conserva los dos
casos conflictivos de B18, ahora conocidos. Los tres recorridos balanceados
no pasan; el contrato exigía uno para abrir desarrollo amplio y conservación.
El ganador aleatorio no se midió en 160 A ni en 80 casos nuevos: transferencia
pendiente, no fracaso observado. La revisión localiza cobertura insuficiente
de parejas duración/guarda, ranking poco informativo al cambiar duración y
una rama +4 con una pérdida que no recibió reparación de condiciones.
S6 y cierre final siguen abiertos. [Resultados](ECHO45-S6-B21-A-RESULTS.md) ·
[Investigación reproducible](ECHO45-S6-B21-FORENSICS-20261006.md) ·
[Contrato congelado](ECHO45-S6-B21-A-DESIGN.md).
<!-- S6B21-IMPLEMENTATION-END -->

<!-- S6B20-EXECUTION-BEGIN -->
**S6-B20: MICRO_CLOSED_NO_PROMOTION.** Implementación aislada y fuentes congeladas; 22 pruebas nuevas y 52 anteriores pasan. Control dirigido de capacidad → auditoría → micro factorial privado en Kaggle, condicionado al pase anterior → cualificación y conservación. S6 y cierre final siguen pendientes; piloto/campaña/examen requieren su contrato posterior. [Ejecución y resultados](ECHO45-S6-B20-RESULTS.md).
<!-- S6B20-EXECUTION-END -->

<!-- S6B20-RESEARCH-BEGIN -->
**6 de octubre: B19 investigado; B20 diseñado, todavía sin ejecutar.**
Las 36 propuestas no pasan V3. Se localizaron estancamiento del selector,
ganancias olvidadas entre ramas, huecos entre gramática y validador y crédito
asociativo que no predice conservación. En v3/28027 el híbrido conserva cinco
niveles pero aumenta de 784 a 1.264 acciones registradas y de 19 a 32 reinicios.
Las 65 fuentes B18 y 68 B19 siguen intactas. El nuevo análisis no ejecutó
partidas ni abrió reserva. B20 separará capacidad del lenguaje, búsqueda
autónoma y conservación; no hay promesa de verde ni procesos B20 activos.
Quedan dos bloques superiores: S6 y cierre final; los verdes V3 mantienen
su alcance sintético y la transferencia ARC sigue pendiente.
[Investigación](ECHO45-S6-B19-FORENSICS.md) ·
[Plan B20](ECHO45-S6-B20-PLAN.md) ·
[Prompt de implementación](ECHO45-S6-B20-IMPLEMENTATION-PROMPT.md).
<!-- S6B20-RESEARCH-END -->

<!-- S6B19-BEGIN -->
**S6-B19: CLOSED_NO_PROMOTION.** 36 propuestas, 1188 partidas físicas; auditorías y revisión aritmética válidas. No supera todas las puertas de cualificación; no hay promoción. S6 sigue abierto: piloto, campaña y examen B1–B5 pendientes. [Resultados revisados](ECHO45-S6-B19-RESULTS.md) · [Investigación](ECHO45-S6-B18-COST-FORENSICS.md).
<!-- S6B19-END -->

<!-- S6B18-BEGIN -->
**5 de octubre: S6-B18 cerrado y auditado, sin promoción.** Kaggle/T4: 14 propuestas (12 políticas distintas), 3.480 ejecuciones y ocho generaciones del LLM. El híbrido y la síntesis sin LLM pasan desarrollo con 383 frente a 378 niveles; en 40 partidas nuevas suben de 173 a 176, pero pierden score en dos casos. Ambas auditorías y la revisión local son válidas. El juez de conservación rechaza la promoción; S6, el piloto principal, la campaña y el examen B1–B5 siguen pendientes. [Resultados y recibos](ECHO45-S6-B18-RESULTS.md).
<!-- S6B18-END -->

<!-- S6B17-FORENSICS-BEGIN -->
El 5 de octubre, B17 cierra auditado sin promoción: síntesis sin LLM alcanza
383 niveles sin pérdidas en desarrollo; el híbrido alcanza 383 conservando
una regresión. La investigación identifica evidencia temporal incompleta,
un ranking que consulta la base aunque el candidato cree estados nuevos y
tres intentos que repiten comportamientos. Doce partidas controladas con
replays idénticos confirman el efecto de una condición disponible pero no
seleccionada. Hay avance de capacidad y diagnóstico; siguen pendientes la
ventaja del híbrido, la conservación protegida y el examen S6. La corrección
propuesta requiere una condición nueva y comparación con el sintetizador.
No se ha abierto otra campaña ni se han publicado estos datos.
[Informe reproducible](ECHO45-S6-B17-FORENSICS.md).
<!-- S6B17-FORENSICS-END -->

<!-- S6B17-BEGIN -->
**S6-B17: MICRO_AUDITED_NO_PROMOTION; S6 abierto.** Micro de tres brazos → auditoría independiente. [Contrato](ECHO45-S6-B17-DESIGN.md) · [Resultado](ECHO45-S6-B17-RESULTS.md).
<!-- S6B17-END -->

<!-- S6B16-BEGIN -->
**S6-B16: MICRO_NO_PROMOTION; S6 abierto.** Micro secuencial → piloto → auditoría → campaña → auditoría → examen. B15 cerrado negativo y reconstruido. [Contrato](ECHO45-S6-B16-DESIGN.md) · [Resultado](ECHO45-S6-B16-RESULTS.md).
<!-- S6B16-END -->

<!-- S6B15-BEGIN -->
**S6-B15: MICRO_NO_PROMOTION; S6 abierto.** Nueva condición después del empate auditado B14. Microensayo 2×2 → piloto → auditoría → campaña → examen, con puertas V1–V4 y B1–B5. [Contrato](ECHO45-S6-B15-DESIGN.md) · [Resultado](ECHO45-S6-B15-RESULTS.md).
<!-- S6B15-END -->

S6 se reanudó el 3 de octubre por petición del propietario, después del cierre
acotado de los módulos V3. La reejecución independiente de PROBE2 confirmó
las 240 partidas: base 378 niveles y dos variantes de 383, sin pérdidas en A.
Esto acredita una mejora disponible en el lenguaje de parches. El
descubrimiento autónomo, la conservación protegida y el examen B1–B5 siguen
pendientes. B13 prueba un objetivo persistente, una propuesta por llamada y
un control aleatorio, con pesos locales congelados. Sus procesos y recibos
son privados; se detuvo un publicador antiguo que seguía activo.
[Registro de ingeniería](ECHO45-S6-B13-ENGINEERING-NOTES.md).

El piloto B13-R1 arrancó a las 23:59 del 3 de octubre. B13 quedó incompleto al agotar
el tiempo de la primera llamada ECHO en el runtime CPU del sistema. El reinicio
usa una compilación privada con AVX2/FMA, calibrada y con tokenización
contrastada, y conserva las condiciones científicas. Todos los brazos empiezan
de nuevo; no se mezclan sus resultados con los del runtime anterior. El piloto,
sus auditorías, la campaña y el examen se encadenan si superan las puertas.
S6 sigue abierto. [Adenda](ECHO45-S6-B13-RUNTIME1.md) y
[resultado actualizado](ECHO45-S6-B13-RUNTIME1-RESULTS.md).

El piloto B13-R1 terminó el 4 de octubre a las 04:23 con ECHO 1113 y FIJO
1125 niveles agregados. Hay tres mejoras ECHO aceptadas, pero pierde los tres
pares y no es elegible para campaña. La auditoría independiente arrancó a las
04:44 tras recuperar un error de lanzamiento, con las fuentes científicas
intactas. Terminó válida a las 08:32:03 del 4 de octubre, con 54 veredictos
reconstruidos y 7720 partidas en una caché independiente. La condición quedó
cerrada sin promoción. S6 continúa abierto y el examen no se ha abierto.
[Recuperación documentada](ECHO45-S6-B13-AUDIT-LAUNCH-RECOVERY.md).

B14 quedó preparado el 4 de octubre a las 05:48, después de corregir la entrega
de memoria al modelo, la selección de casos, la exploración y el tratamiento
de repeticiones en el controlador de investigación de ECHO. Pasan 25 pruebas
del instrumento y 43 comprobaciones de contexto (36 historiales, seis casos
de refinamiento y una política de 32 reglas). La condición congelada salió
automáticamente de la espera tras el cierre B13; completó la paridad a las
08:38:20 y empezó el piloto. Terminó a las 11:39: ECHO 1134 y FIJO 1134,
con tres mejoras aceptadas por brazo. La auditoría terminó válida a las
14:07:14, tras 5080 partidas independientes y 54 veredictos reconstruidos.
B14 quedó cerrado sin promoción; campaña y examen no se ejecutaron.
[Registro de las correcciones](ECHO45-S6-B14-ENGINEERING-NOTES.md).

La investigación posterior comprobó que los seis recorridos aceptaron la
misma regla de 378 niveles y que las 36 propuestas del modelo usaron únicamente
REVALIDATE_NOOP. Pedir explorar esperas no llegó a probar un operador de espera.
El planificador conservó el crédito de su primer éxito y el resumen por orden
de texto omitió una observación temprana relevante. La memoria reciente sí
se conservó. Sobre exactamente la misma base, los controles humanos de PROBE2
ya alcanzan 383 sin pérdidas A; estaban permitidos pero no fueron propuestos.
La capacidad conocida del lenguaje supera la búsqueda realizada. La siguiente
condición debe medir correspondencia entre pregunta y experimento, utilidad
marginal y cobertura numérica antes de otra campaña. Las propuestas correctivas
siguen pendientes de implementación y medición; S6 permanece abierto.
[Diagnóstico y evidencias](ECHO45-S6-B14-FORENSICS.md).

El 3 de octubre se decidió continuar la investigación temporalmente en
privado. La web pública de RxLabs queda en Coming soon, con la descripción
de la organización y el correo knightsys@proton.me. Se mantiene contexto
general de echOS, echo-ai Edge para robótica, modelos agentes LLM y echo-rsi
en metadatos y llms.txt. Las subpáginas y los archivos detallados dejan de
estar publicados; no aparece el nombre personal ni Discord.

La web anterior se conservó localmente, con 1.754 archivos y el historial Git,
en `/home/roger/rxlabs-private-archive/20261003-130623/`, fuera del repositorio
desplegable. El repositorio de la web pasó a privado. El commit `16199cf` está
READY en Vercel; la portada y siete archivos de identidad/contexto coinciden
con los bytes del build local, y veinte rutas retiradas devuelven HTTP 410.
Los enlaces directos a despliegues anteriores requieren autenticación Vercel.
La documentación científica local, sus resultados y la cronología siguiente
se conservan. No publicar más investigación técnica sin una nueva instrucción
explícita del responsable del proyecto.

El 3 de octubre se completó V3 en una condición privada de módulos. El candidato
relacional con memoria, elección aprendida de búsqueda, vistas y consistencia
resolvió 192/192 puzzles sintéticos. La guía de programas de 500k recuperó
4.090/4.096 consultas frente a 1.956/4.096 con 65k, bajo un límite de una
propuesta. Se repitieron las campañas en procesos nuevos. Cada resultado tiene
un alcance concreto: consistencia incluye abstenciones, el ahorro principal
de política es 19,21 % en una mezcla equilibrada y 0,166 % en toda la batería,
y el banco asociativo recupera programas adquiridos. S6 y el examen final
continúan pendientes. Esta ruta fue autorizada por el propietario al aceptar
demostraciones de utilidad fuera de ARC. [Informe y evidencia](ECHO45-RELATIONAL-V3-RESULTS.md).

La decisión de ruta anterior, del 2 de octubre, aplaza S6 y prioriza la
integración de memoria y resolución de rejillas. Hay un adaptador persistente
del diario 3E, síntesis refinada y guías intercambiables. El banco causal de
memoria pasó 64/64 casos sintéticos con 71,04 % menos aplicaciones primitivas.
El avance ARC-1 de desarrollo, 2/64 → 4/64, no se confirmó en otras 128 tareas:
ambos candidatos acertaron una. El laboratorio conserva ese resultado y no
declara cerrada 4.5. Las referencias a S6 como «ruta inmediata» más abajo
describen el orden previo. [Implementación, datos y límites](ECHO45-INTEGRATION-RESULTS.md).

2 de octubre de 2026. RxLabs mantiene una línea de investigación en agentes híbridos, con un núcleo determinista que conserva estado, aprende de consecuencias y comprueba la ayuda de un modelo externo. El último producto registrado de esa línea es ECHO-4.0, publicado como candidato 4.0.0rc1/rc2 con acceso condicionado. ECHO-4.5 está en desarrollo. Ha mejorado algunas capacidades y tiene resultados negativos que impiden declarar su cierre: S6 sigue pendiente, ARC-2 continúa en cero y el objetivo de niveles ARC-3 todavía no se alcanza. PROBE2 acaba de demostrar dos mejoras V3 sin pérdidas en desarrollo A, mediante búsqueda dirigida del laboratorio. La explicación técnica y el estado operativo se mantienen en [NOW.md](NOW.md).

Roger define las preguntas y decide el alcance del proyecto. Los agentes de código implementan, revisan y ejecutan pruebas. Esa colaboración produce software y resultados; sus respuestas también necesitan contraste. En varios hitos el implementador, el ejecutor del examen y el revisor fueron distintos agentes o procesos. Esto aporta separación de funciones dentro del laboratorio. Una auditoría reconstruida por nosotros conserva el límite de ser una auditoría interna. La reproducción por un tercero externo sigue siendo una deuda concreta de la publicación.

La documentación disponible sitúa los primeros antecedentes del árbol actual en julio de 2026. rxOS v3 tenía interfaz gráfica, un pequeño editor, sistema de archivos en RAM, páginas `rgx://`, teclado español, ratón y funciones criptográficas. v4.0 reorganizó el sistema en boot, arquitectura, kernel, drivers, sistema de archivos, interfaz y userland; incorporó interrupciones, reloj, heap, registros y autopruebas de arranque. La tabla de procesos y otros componentes iniciales se declaraban todavía como stubs. Esas versiones de rxOS son versiones del sistema operativo; no son ECHO-4.0. [CHANGELOG histórico](../../CHANGELOG.md).

Las revisiones siguientes resolvieron persistencia, entrada por interrupciones, almacenamiento y comunicaciones. El backend de red se amplió de virtio a e1000. Hubo verificaciones en QEMU y límites que permanecieron sin validar en VirtualBox o máquinas concretas. El problema de una interfaz con apariencia terminada y funciones internas incompletas apareció temprano. Los registros conservaron qué operación escribía realmente en disco, qué servicio era solo una bandera y qué target se había probado. Esa distinción pasó a formar parte de los contratos de ECHO.

En agosto se añadió el tejido de eventos neuromórfico. Descriptores de 64 bytes, colas acotadas, actores LIF de punto fijo y plasticidad local permitían trabajar sin coma flotante en el kernel. Una avería de red dejó una enseñanza importante: hacer depender el drenaje de paquetes de un umbral neuronal podía detener el tráfico. El camino de servicio mantuvo disparo determinista y una vía de deadline. Los umbrales quedaron fuera de la autoridad sobre interrupciones, disco y fallos de página. El progreso consistió en encontrar dónde sirve una dinámica neuronal y dónde una garantía de ejecución tiene que ser explícita. [Registro de Event Fabric](../../CHANGELOG.md).

La línea NAVI se desarrolló junto al sistema. Primero reunió vocabulario, composición, búsqueda y fichas. NAVI 6/6.5/6.6 trabajó cadenas y lenguaje; NAVI 7/7.5 agregó mundo, memoria y cosecha de información; NAVI 9 separó actos y comprobación de hechos. El 19 de agosto, NAVI 10 fijó Q_N como producto Q8×Q8, memoria CAM de 4.096 ranuras, paquetes WSP de dieciséis bytes y un spoke LIF de 256 células. La cercanía Hamming debía ir acompañada de extracto para verificar un hecho. Tener 65.536 direcciones no implicaba tener 65.536 neuronas activas. [Inventario de componentes heredados](01-INVENTORY.md), [ficha NAVI 10](../../docs/NAVI10_SPEC.md).

También se investigó un modelo verbal pequeño propio. El trabajo LPU incorporó tokenización BPE, un decoder con RoPE/GQA/SwiGLU/RMSNorm, entrenamiento de laboratorio, exportación y cache. Un sobreajuste de texto llevó la loss muy abajo y reprodujo el material entrenado; el informe aclaró que eso no demostraba comprensión general. Un experimento de Wikipedia redujo perplejidad en una muestra pequeña, con la misma cautela sobre su alcance. Estos trabajos fueron útiles para aprender cómo medir y empaquetar un modelo. No constituyen un neocórtex propio equivalente a un frontier, ni acreditan entrenamiento completo de internet. [Cronología LPU](../../CHANGELOG.md).

El nombre echOS apareció en la línea Eclipse documentada el 22 de agosto. La arquitectura reunía ediciones, shell, ventanas, eventos, red, formatos de contenido y la integración prevista de ECHO. Parte de esa superficie era experimental y parte era plan. Después, echOS Universal y 2.1 se concentraron en una consola y un unikernel con una superficie más acotada. El cierre del 2 de septiembre quitó comandos incompletos de la lista ordinaria, etiquetó notas de laboratorio, corrigió banners y explicó que `rcctl start` guardaba una bandera. Las dependencias de terceros también quedaron enumeradas. [Eclipse](../../docs/ECHOS_ARCHITECTURE.md), [cierre 2.1](../../docs/ECHOS_2.1_HONEST.md).

El árbol padre conserva además el informe de echOS 3.0: imágenes x86_64/AArch64, colas estáticas, contabilidad de eventos, gate e interfaz MAVLink. En sus corridas registró cero asignaciones dinámicas en sensor→intent. PX4 conservó el control del avión y recibió intenciones de alto nivel. Sus latencias y balances se publicaron por plataforma; un número sin resolución suficiente se trató como límite de medida. No había una placa Akida trabajando en el laboratorio. La sonda PCI y los modelos LIF software no autorizaban cifras de eficiencia de silicio. [Informe 3.0](../../docs/ECHOS_3.0_REPORT.md), [README del sistema](../../README.md).

echoAI se separó como programa de agente host. El paso inicial verificable fue NEXUS-0: memoria, política, aprendizaje, transición y gate con el LLM apagado. Las tablas Q enteras aprendían de recompensas y error de predicción; CAM conservaba evidencia. WSP siguió como representación compartida. Los contratos evitaron crear un segundo bus o sustituir la comprobación por prosa del modelo. El sistema operativo, el agente host y una interfaz conversacional quedaron con funciones y versiones propias. [Contrato NEXUS-0](05-NEXUS-0-SPEC.md), [decisiones de reutilización](04-DECISIONS.md).

Durante ECHO-1 y ECHO-2 se amplió esa base con predicción, crédito, objetos, composición y transferencia en mundos pequeños. Aprender una acción nueva exigió que el mundo tuviera de verdad esa transición y que el gate dejara llegar la acción correcta. Los restos de crédito abordaron recompensas pequeñas que el redondeo entero perdía. La exploración plana abordó acciones que nunca se probaban. Los exámenes comparaban mecanismos y ablaciones; cada ampliación tenía que mantener el comportamiento basal cuando estaba apagada. Las fechas y revisiones de esta etapa están conservadas en el [registro anterior](NOW-HISTORY-20260905-20260930.md) y el [roadmap original](ROADMAP.md).

ECHO-3 llevó la percepción y el control a simulación de vuelo. SIM-3, FLIGHT-1S, SENSOR-1S, GROUND-1, PATTERN-1R, DYNAMIC-1, COMPOSE-1 y FUSION-1 fueron encadenando ejecutores, sensores, traducción a WSP, reconocimiento, composición y fusión. FLIGHT necesitó llegar a v6; GROUND tuvo un rojo antes de v2; PATTERN y COMPOSE conservaron varias revisiones. Que una suite del instrumento pase no asegura que el agente gane su examen. Esa diferencia se hizo visible al desarrollar estas fases. [FLIGHT v6](FLIGHT1S-V6-RESULTS.md), [GROUND v2](GROUND1-V2-RESULTS.md), [PATTERN v4](PATTERN1R-V4-RESULTS.md), [COMPOSE v4](COMPOSE1-V4-RESULTS.md), [FUSION](FUSION1-RESULTS.md).

TRANSFER-3 mostró otro obstáculo: un prior útil del generador podía confundirse con aprendizaje transferido por el agente. Los pilotos y los planes A/B/C separaron aprendizaje, geometría, canal, coste y controles. Algunos exámenes fallaron y se cerraron. Una revisión detectó que la ventaja del oráculo no cambiaba como sugería la hipótesis y que un filtro había rechazado incorrectamente un diseño. El cierre posterior usó nuevas salas, formas excluidas y una regla de atribución declarada. SAFE, POWER, HOST y DRONE continuaron con sus perfiles; DRONE pasó SITL, mientras HIL y jaula física siguieron pendientes. [TRANSFER Plan C1](TRANSFER3-PLAN-C1-RESULTS.md), [SAFE v2](SAFE1-V2-RESULTS.md), [POWER](POWER1-RESULTS.md), [DRONE](DRONE3-RESULTS.md).

El 21 de septiembre ECHO-4 abrió el trabajo de ego funcional en software. WORLD-1 hizo primero una pregunta de ingeniería: ¿el cuerpo virtual permite una vida larga con esas reglas? El analizador encontró un ciclo viable, pero el agente sin ayuda murió al paso 37. Se comprobó por separado la posibilidad física y el aprendizaje. SENSATION midió ambigüedad de observación; recordar más pasos ayudaba y seguía dejando muchos estados indistinguibles. BOUNDARY empleó intervenciones emparejadas para distinguir coincidencia y efecto. Ese orden evitó afirmar que detectar un cambio ya era saber quién lo causó. [WORLD](ECHO4-WORLD1-RESULTS.md), [SENSATION](ECHO4-SENSATION1-CLOSURE.md), [BOUNDARY](ECHO4-BOUNDARY1-RESULTS.md).

SELF-A descubrió causas incompatibles con la misma evidencia pública. SELF-B añadió ensayos que podían separar hipótesis dentro de un prior mecánico declarado. SELF-C v1 protegió memoria, pero no mejoró supervivencia porque los dos brazos ya resolvían los casos viables. La versión siguiente probó reutilización tras restauración del cuerpo y sí obtuvo ventaja. El examen final confirmó atribución condicionada, conservación y uso de memoria. El cuerpo restaurado lo proporcionaba el ejecutor; la restauración no se atribuyó a una reparación descubierta por ECHO. [SELF-A](ECHO4-SELF1-A-RESULTS.md), [C v1](ECHO4-SELF1-C-RESULTS.md), [C v2](ECHO4-SELF1-C-V2-RESULTS.md), [final](ECHO4-SELF1-FINAL-RESULTS.md).

CONTINUITY permitió guardar y reanudar exactamente, continuar sesiones activas y distinguir ramas, descendientes y cambios de cuerpo. Al heredar o cambiar cuerpo se revocan permisos y se recalibra. DREAM guardó intentos y probó programas con Qwen; sus dos primeras revisiones no superaron controles. La tercera amplió los ensayos y la seguridad condicionada a observaciones. Pasó el contrato, pero las ablaciones sin Qwen y sin feedback empataron: no hay ventaja exclusiva del modelo que atribuir. MAINTAIN añadió intervención virtual con repuestos y reserva preventiva. Su cierre acredita mantenimiento condicionado a ese modelo mecánico. [CONT-D](ECHO4-CONTINUITY1-D-RESULTS.md), [DREAM v3](ECHO4-DREAM1-D-V3-RESULTS.md), [MAINTAIN](ECHO4-MAINTAIN1-FINAL-RESULTS.md).

OTHER, INTERACTION, RELATION y ROLES desarrollaron convivencia. ECHO predice a una contraparte por observaciones separadas por identidad, aprende cuándo pedir ayuda y conserva encuentros. Las medidas incluyen coste formativo: INTERACTION mejoró el neto del tramo evaluado, pero no el neto individual de la vida completa. RELATION publicó también el caso del impostor y una generalización excesiva después de varios rechazos. ROLES corrigió controles que exploraban menos; la tribu pasó a derivar jerarquía de competencia verificada. Decir «tengo rango» no cambia esa jerarquía. Estos resultados dan una base concreta para investigar multiagentes en ECHO-5.1; todavía no prueban que cualquier enjambre gane a un agente con igual cómputo. [INTERACTION](ECHO4-INTERACTION1-BCD-RESULTS.md), [RELATION](ECHO4-RELATION1-D-RESULTS.md), [ROLES v5](ECHO4-ROLES1-V5-RESULTS.md).

SITUATE hizo que el agente respondiera sobre su proceso y entorno usando sensores y recibos. La versión con modelo externo rechazó afirmaciones fenomenales o contradictorias, incluso si venían formuladas con seguridad. INTEGRATE reunió cuerpo, tribu, relación, firewall y continuidad durante una vida, con ablaciones. RELEASE reprodujo ese examen desde un paquete compilado en sala limpia. Hubo fallos del empaquetado y una enmienda posterior al rojo de la prueba de introspección; ambos quedaron documentados. La publicación de septiembre entrega un candidato reproducible en la plataforma declarada. Falta reproducción externa. [SITUATE-2](ECHO4-SITUATE2-RESULTS.md), [INTEGRATE](ECHO4-INTEGRATE1-RESULTS.md), [RELEASE](ECHO4-RELEASE1-RESULTS.md).

El 25 de septiembre se aprobó ECHO-4.5. ECHO-SEED introdujo una semilla clonable y conceptos como programas pequeños sobre rejillas. Las subsecuencias repetidas en soluciones verificadas se comprimen en macros; la prioridad de búsqueda puede aprender de lo que funcionó. S1 pasó de quince a veintiuna tareas correctas en el seguimiento de 201. S2 inicial empató. Con vocabulario de 84 primitivas y prioridad, S2v llegó a veinticuatro con el mismo límite de cuatrocientas expansiones. Aumentarlo a mil quinientas no mejoró: había un límite de representación. La intuición neuronal y los currículos distintos produjeron datos útiles, pero no una ventaja adicional en esa reserva. [S1](ECHO45-S1-RESULTS.md), [S2](ECHO45-S2-DESIGN.md).

S3 y S4 trabajaron el juego como objetos: cuerpo por contingencia, reloj visual, clic interior, muros, metas candidatas y planificación. Los primeros caminos hacia objetos no resolvían mecánicas como dejar una copia en un interruptor. Se revisaron frames de desarrollo, se incorporaron causas remotas y se verificó cada transición prevista. S5 construyó un gimnasio de mundos. v5.7 añadió memoria de copia y pasó su examen; v5.8 incorporó orden y conteo. S5-F2 obtuvo 1.537 frente a 1.239 niveles sobre 1.800. Los exámenes de ese gimnasio y la evaluación ARC oficial mantienen nombres y poblaciones distintos. [S3](ECHO45-S3-DESIGN.md), [S4](ECHO45-S4-DESIGN.md), [S5-E](ECHO45-S5-E-RESULTS.md), [S5-F2](ECHO45-H1-H3-EXAM2-RESULTS.md).

El examen final de septiembre mostró la transferencia real disponible: ARC-1 pasó de 20/400 a 31/400, una mejora de 2,75 puntos porcentuales; ARC-2 siguió en 0/120; ARC-3 bajó de 13 a 11 niveles sobre 112, aunque mejoró el score de eficiencia del contrato. Las puertas R1/R4 pasaron y R2/R3 fallaron. Presentar solo el score ARC-3 habría ocultado la pérdida de cobertura. Ese resultado guía la siguiente arquitectura: relaciones entre objetos, reglas compuestas, abstracción de pocos ejemplos y mejor percepción, con comparación de coste. [Examen final](ECHO45-FINAL-EXAM-RESULTS.md).

S6 intenta demostrar algo más exigente que usar un LLM: ECHO debe generar peticiones útiles, aceptar mejoras comprobadas y superar SEMILLA, FIJO y SIN FILTRO en la condición declarada. Las revisiones A y B conservaron fallos de formato, sobreajuste de desarrollo y empates. B7 aceptó una mejora útil y empató con FIJO. B11 consiguió tres mejoras y ventaja de piloto 1.129 frente a 1.108; su campaña se detuvo por contexto. B12 corrigió cómo se cuentan y limitan los tokens, completó una campaña y quedó en 378 frente a 378. Una infraestructura que ejecuta y audita correctamente puede terminar con una hipótesis refutada. [Diagnóstico S6](ECHO45-S6-DIAGNOSIS-20260929.md), [B12](ECHO45-S6-B12-RESULTS.md).

La colaboración reciente con Claude revisó las propuestas y descubrió dos límites: REFINE generaba cambios de la regla ya aceptada en vez del objetivo, y las mejores ganancias de cooldown eran +1 cuando V3 exige +2. El siguiente paso fue un sondeo de capacidad sin LLM. PROBE1 midió doscientos candidatos y cincuenta pares: ninguno pasó V3. Una partida podía subir cuatro niveles, pero las propuestas perdían eficiencia en otras. La auditoría independiente repitió 480 partidas en otra caché y validó el resultado. PROBE2 buscó guardas que separan ganancia y daño, sin tocar B ni el examen; su cierre positivo de capacidad se recoge más abajo. Un candidato positivo encontrado de esa forma es control de capacidad del laboratorio; la autonomía se tendrá que demostrar después. [PROBE1](ECHO45-S6-PROBE1-RESULTS.md), [auditoría](../lab/seed/s6probe1-20260930-audit/audit.json), [PROBE2](ECHO45-S6-PROBE2-DESIGN.md).

EGO-MEMORIA probó si conviene conservar experiencias, pruebas y citas propias cuando escribir y verificar cuestan. Su segunda condición falló una semilla. Las revisiones 3A–3D tuvieron avances y nuevos fallos. 3E asignó correctamente las consecuencias demoradas a la prueba que realmente se conservó y pasó M1–M6 en dieciséis semillas nuevas. La estructura de crédito fue programada por el laboratorio; ECHO aprendió sus valores de utilidad. El siguiente trabajo es transferir esa memoria al actor de ARC mediante un adaptador y ablaciones. [Memoria 3E](ECHO45-EGO-MEMORIA3-RESULTS.md), [transferencia prevista](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md).

La petición de ampliar a 500.000 unidades se convirtió en una guía asociativa dispersa. Se midió primero con un control sintético y luego con doscientos cincuenta problemas ARC-1 de desarrollo. Base obtuvo tres, guía 640 cinco y guía 500k seis. La ampliación del 1 de octubre añadió 4.096, 16.384 y 65.536: esta última igualó los seis aciertos de 500k. Eso deja una recomendación distinta de la intuición inicial: comprobar capacidad suficiente y colisiones antes de aumentar tamaño. Las unidades de ese banco son pesos de un byte, no 500.000 neuronas LIF. La ganancia disponible es pequeña y no acredita transferencia a S6 o ARC-2/3. [Datos completos](../lab/seed/capacity-study-20261001/summary.json), [diseño](ECHO45-CAPACITY-STUDY-DESIGN.md).

echo-nexus permite usar conexiones locales y API, ejecutar pruebas de desarrollo y observar contadores y mundos. La versión 1.5 cerró HTTPS, catálogo, copia y edición, sesión de mundo y procedencia de respuestas. La herramienta se presenta como beta para desarrolladores. Una respuesta del neocórtex mantiene esa fuente; un árbol visible muestra decisiones registradas. Los GIF de la guía usan índices y pesos reales, con coordenadas ilustrativas, y no se presentan como anatomía o actividad neuronal medida. La web y GitHub sirven para distribuir el arnés y la media autorizada; el núcleo y las campañas privadas mantienen otra política de distribución. [Arnés 1.5](ECHO45-HARNESS15-RESULTS.md), [observabilidad](ECHO45-OBSERVABILITY.md).

PROBE2 terminó a las 04:16 Madrid tras 874 propuestas y 10.048 partidas A: dos reglas pasan V3 con 383 niveles frente a 378, sin pérdidas por partida y con replay completo idéntico. La gramática actual permite la mejora. La ruta inmediata es auditar esa capacidad mediante reejecución y comprobar si ECHO puede encontrarla con evidencia de desarrollo, sin recibir la solución del sondeo. Después se comprueba conservación V4 y una campaña autónoma, se congelan cuatro versiones y se abre un examen nuevo. S6 estará verde cuando pase B1–B5 con sus auditorías. ECHO-4.5 necesitará también las puertas finales de ARC y la transferencia pendiente que marque su roadmap. La fecha deseada no altera ese contrato. [Resultados](ECHO45-S6-PROBE2-RESULTS.md).

Las [visiones de ECHO-5, 5.1 y 5.5](ECHO5-51-55-RESEARCH-VISION.md) tienen un documento propio que distingue antecedentes, hipótesis y pruebas necesarias. ECHO-5 investigaría representación de objetos y relaciones, composición jerárquica, planificación hacia atrás y reparación precisa. ECHO-5.1 estudiaría especialistas y colaboración, memoria compartida con procedencia y asignación de cómputo. Para aceptar esas propuestas habría que comparar contra un agente con el mismo presupuesto total y contabilizar la coordinación. La comunicación vectorial entre módulos se estudiaría como interfaz con tests de compatibilidad. La memoria común necesita separar observación, hipótesis, autor y versión. Compartir un error con todo el grupo puede empeorar el sistema más rápido que compartir una estrategia útil.

El experimento privado RSI1 arrancó después de PROBE2, pero su primera llamada abortó porque llama.cpp usó la gráfica AMD pese a haberse pedido cero capas en GPU. Se conserva ese fallo y su coste. Una recuperación con manifiesto separado forzó CPU, pasó una calibración real y se ejecutó entre las 04:35:47 y las 08:16:37. Terminó roja: ECHO recursivo obtuvo 99/144, igual que el brazo sin acumulación y por debajo del aleatorio, con 101/144. El investigador no consiguió nuevas promociones. Compara bibliotecas acumuladas, reiniciadas, aleatorias, base y LLM solo en puzzles sintéticos. Tiene tres réplicas, cinco generaciones, modelo fijo, límites de búsqueda y llamadas, examen separado y ensayo de productividad del investigador. Cuesta cero euros externos; la recuperación cuenta además una llamada fallida y una de calibración. La aprobación del instrumento no demuestra que el modelo consiga promover mejoras. Un verde de este banco correspondería a su lenguaje cerrado; no acreditaría automejora general, conciencia, equivalencia frontier ni el cierre de S6. [Contrato privado](ECHO-RSI1-DESIGN.md), [recuperación](ECHO-RSI1-RECOVERY1.md).

ECHO-5.5 es un objetivo de candidato medido antes de diciembre. La propuesta de infraestructura reutiliza CPU para núcleo y verificador, GPU por horas para un adaptador pequeño y API opcional para un neocórtex fuerte. El presupuesto de 180 euros todavía es previsto. Permitiría perfiles y ajustes acotados, no preentrenar un modelo de escala frontier. Un modelo de API no entrega sus pesos. La selección del neocórtex se hará por mejoras aceptadas, conservación y coste, comparando varios proveedores y una base local abierta. [Plan de infraestructura](ECHO55-INFRASTRUCTURE-PLAN.md).

La línea posterior propuesta es [ECHO-RSI-1](ECHO-RSI-1-LAB-PLAN.md). Para sostener mejora recursiva tendría que demostrar que el investigador evolucionado produce mejores cambios en oportunidades nuevas, con el mismo neocórtex y presupuesto, y repetir el efecto en otro ciclo. El laboratorio comenzaría con un adaptador de una base abierta pequeña y alquiler por etapas. El nombre distingue el sistema futuro del experimento privado RSI1; una certificación se limitaría al contrato, datos y costes medidos. Esta etapa está pendiente en la [línea temporal](ECHO4-ECHO5-TIMELINE.md).

Para obtener ingresos mientras se investiga, la hipótesis actual es instalación y evaluación reproducible de agentes de código: definir tareas permitidas, comparar configuraciones y entregar resultados y costes. Existe una [oferta piloto en borrador](ECHO55-PILOT-OFFER-DRAFT.md). El precio sugerido aún no es demanda validada ni ingreso. La utilidad comercial tendrá que demostrarse con entregables y horas de trabajo. No se presupone que una etiqueta de autonomía o una puntuación sintética baste para vender el producto.

Los argumentos a favor de la seriedad del proyecto son verificables: hay fuentes ejecutables, transiciones y reglas concretas; contratos anteriores a sus mediciones; controles que pueden ganar; replays y manifiestos; paquetes probados en sala limpia; errores y resultados negativos preservados; y mejoras con denominadores y límites. WORLD distinguió posibilidad y conducta; SELF corrigió una prueba saturada; DREAM publicó el empate de sus ablaciones; ROLES igualó exploración; ARC mostró transferencia insuficiente; PROBE1 no convirtió ausencia en muestra en imposibilidad. Son decisiones que reducen lo que podemos afirmar y hacen las afirmaciones restantes más contrastables.

Esos argumentos tienen límites. Las pruebas están ejecutadas principalmente por el laboratorio, muchas tareas son sintéticas y algunas reservas ya se han consultado varias veces. El núcleo se distribuye compilado y el arnés es la parte pública; la transparencia documental y de datos no equivale a publicar todo el código. La replicación externa y las evaluaciones independientes tendrán que compensar ese límite. Tampoco hay evidencia de subjetividad, hardware neuromórfico medido, una mejora grande en ARC-2 o una versión final ECHO-4.5. En este estado conviven un producto experimental instalado, resultados científicos acotados y módulos todavía planeados.

La personalidad de RxLabs se reconoce en cómo trata esas diferencias. Roger mantiene una ambición amplia; el trabajo cotidiano la divide en problemas observables y contratos que pueden fallar. Se prueba primero la posibilidad de una mejora, se inspecciona dónde cambia la acción y se cuenta el daño que introduce. Se conservan la intervención humana y el coste del modelo en la explicación. Se aprovechan piezas anteriores cuando funcionan y se reduce la superficie cuando promete más de lo que ejecuta. Las analogías ayudan a entender el sistema; las decisiones se apoyan en transiciones, evidencia y resultados.

La nueva propuesta ECHO-RSI-2 estudia simulación ejecutable, memoria de propuestas, especialistas, selección de neocórtex y ajuste de adaptadores. El análisis posterior de RSI1 encontró solo tres programas válidos distintos en 57 llamadas; eso orienta primero un piloto de diversidad y feedback. Las trazas por sí solas no permiten calcular consecuencias de acciones nuevas. El primer laboratorio de pesos usaría CPU local y una GPU alquilada, con controles separados para biblioteca, modelo y organización. Es una línea pendiente, sin entrenamiento iniciado. [Plan de investigación](ECHO-RSI-2-RESEARCH-PLAN.md).

La próxima revisión de este documento debe incorporar la auditoría por reejecución de PROBE2 y cualquier nuevo contrato S6 o de propuestas. Cada publicación posterior distinguirá qué se implementó, qué se midió, qué fue reproducido y qué sigue abierto. La cronología y los detalles por módulo permanecen enlazados en [NOW](NOW.md), el [registro anterior](NOW-HISTORY-20260905-20260930.md) y los contratos originales.
