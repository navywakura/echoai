# NOW — estado y registro técnico de ECHO

**12 de octubre · ECHO-5 5.0.0: verde oficial dentro del alcance validado.**
Cierre r3 verificado, incluida confirmación Gazebo/PX4 en simulación. Correcciones
posteriores auditadas: 12/18 independientes y 9/9 plantillas, 28/28 exploración,
64/64 currículo. Seis tareas siguen abiertas; S6 se retoma después de 5.5.
[Estado vigente](PROJECT-CHECKPOINT-20261012.md) ·
[Release](../ECHO-5/docs/RELEASE-5.0.0.md).
Los bloques siguientes conservan sus estados históricos; no son el estado vigente.


**11 de octubre · ECHO-5 implementado y en investigación; cierre pendiente.**
Se publica el runtime de objetos y relaciones, conceptos, composición, planificación,
currículo por contraejemplos, MiniGrid/BabyAI, MissionAgent y panel local.
La confirmación cognitiva r1 tiene auditoría independiente válida. La confirmación
Gazebo/PX4 r1 conserva 17/18 recibos válidos y un resultado insuficiente; la
corrección posterior sigue en validación y no autoriza un verde.
S6 permanece abierto y se retomará después de ECHO-5.5.
[Checkpoint y límites](PROJECT-CHECKPOINT-20261011.md) ·
[Recibos publicados](../research-archive/20261011/README.md) ·
[Sandbox Unity, código y capturas](https://github.com/navywakura/echounity).
Los bloques siguientes son históricos; la preparación descrita el día 10 ya
dio paso a implementación, sin convertir esta publicación en un release final.

**10 de octubre · Guardado previo a ECHO-5; implementación todavía no iniciada.**
Se conserva el setup, el inventario estático y una propuesta de aprendizaje
adversarial inspirada en GAN, sin ejecutar nuevos ensayos. B24-R1 permanece
en espera de cuota en el último recibo local, con checkpoint v3 y renovación
anunciada para el 17 de octubre a las 02:00 Madrid. S6 continúa sin pase.
[Estado del corte](PROJECT-CHECKPOINT-20261010.md) ·
[Propuesta GAN](../ECHO-5/docs/ADVERSARIAL-LEARNING-PROPOSAL.md).
Los bloques siguientes conservan sus fechas y antecedentes.

**9 de octubre, 14:15 Madrid · B24 continúa; S6 se retomará después de ECHO-5.5.**
Decisión del propietario: cerrar la etapa 4.5 tras B24 con resultados reales,
manteniendo S6 abierto y sin pase. No hay cierre oficial todavía. B24-R1 está
en `WAITING_GPU_QUOTA`, con checkpoint conservado y ambos gestores activos;
la cuota anuncia renovación el 10 de octubre a las 02:00 Madrid. El segmento
v1 terminó, no el ensayo completo; no se garantiza finalización mañana.
ECHO-5 recuperará la robótica Gazebo/PX4 ya validada en ECHO-3 y consolidará
el núcleo compartido. GUI local de decisiones observables propuesta; publicación
4.5 en Hugging Face pendiente. [Decisión, evidencia y límites](ECHO45-TO-ECHO5-DECISION-20261009.md).

**9 de octubre, 01:54 Madrid · B24-R1 ya mide partidas; evaluador ARC preparado y calibrado.**
B24 v1 se detuvo en el preflight neutral antes de jugar: seis llamadas de
formato cobradas, cinco correctas, cero partidas y cero llamadas científicas.
El CLI nativo interpretaba un token EOG del prompt como fin de generación en
una frontera de 128 tokens. [Forensia](ECHO45-S6-B24-R1-FORENSICS-20261009.md).
R1 conserva el fallo y los costes, usa un ZIP separado con lote lógico 8192,
microlote 64 y exige ocho comprobaciones nuevas. Las 100 fuentes originales
siguen intactas; 69 pruebas locales pasan y los dos validadores nativos
quedan para el runtime CUDA. [Recuperación](ECHO45-S6-B24-R1-RECOVERY-20261009.md).
[Kaggle R1 privado](https://www.kaggle.com/code/rogeernavarro/echo45-s6b24-r1-20261009)
aceptó la versión 1 a las 01:47. A las 01:52:38 pasó las ocho comprobaciones
de formato; a las 01:53 ya registra partidas de la base R4-REF. El seguimiento
está en `lab/kaggle/s6b24-r1-20261009/pipeline-status.json` y
`live-scientific-status.json`. No hay todavía resultado final ni pase S6 de R1.

En paralelo, [el evaluador offline V3](ECHO45-ARC-V3-BATCH-20261009.md)
prepara ARC-1/2 con cuatro procesos CPU, estado congelado por tarea, sin LLM
y respuestas de test separadas. La calibración completó 16 tareas conocidas
por corpus en 4,17 s de ejecución total, sin errores ni timeouts: 0/16 exactas
en cada corpus y abstención en todas. Pasan 69 pruebas diferentes del
evaluador, custodia, observador y módulos adyacentes. La proyección para
400+120 tareas es 63–88 s; reservar 2–5 min con margen operativo, sin garantía.
El lote público completo no se ha abierto y exige el cierre válido de B24.
Recibos: `lab/seed/arc-v3-calibration-20261009/calibration-receipt.json`.
Se mantiene la decisión del propietario: acabar B24, medir ARC y cerrar la
versión 4.5 con su resultado real, aunque S6 siga pendiente.

**9 de octubre, 00:40 Madrid · B24 enviado a Kaggle; cierre de 4.5 acordado tras medir.**
El propietario decide terminar B24 y después cerrar ECHO-4.5 aunque S6
continúe sin superar su criterio. Se preparará una medición ARC con el
resultado que obtenga; no se rebajan umbrales ni se cambia un rojo histórico.
B24 ya tiene implementación aislada: cinco brazos, reparación de guardas,
selección por catálogo, archivos separados/compartidos por ronda y custodia
completa de partidas. Paquete aislado: 61 pruebas pasan y dos validadores
nativos quedan para CUDA. La versión 1 se envió en privado a las 00:40;
Kaggle la aceptó y comenzó a compilar CUDA. El preflight hará ocho
inferencias reales. [Registro de ejecución](ECHO45-S6-B24-RUN-20261009.md).
Todavía no hay resultado científico B24.
[Contrato ejecutable](ECHO45-S6-B24-DESIGN.md) ·
[Capacidades confirmadas y opciones ARC](ECHO45-CLOSURE-EVIDENCE-20261009.md).
[Ejecución privada](https://www.kaggle.com/code/rogeernavarro/echo45-s6b24-20261009).
El estado operativo está en `lab/kaggle/s6b24-20261009/pipeline-status.json`;
la cuota puede exigir continuaciones con el mismo perfil. Los bloques
anteriores conservan sus resultados y decisiones históricas.


**8 de octubre: B23-R4 cerrado y revisado; B24 integra reparación y cooperación.**
R4 terminó a las 16:55 de Madrid: 924 partidas, 36 propuestas y ocho llamadas
de formato. La autopsia reproduce 36 prompts y 22 ternas de medición/replay/
auditoría, con 88 fuentes intactas. Hubo 16 duplicados, 12 propuestas inactivas
medidas y ocho activas con pérdidas. Ambos Qwen encontraron 61→65, perdiendo
score en cinco partidas y conservando niveles. Ninguna propuesta fue aceptada;
desarrollo amplio, reserva, campaña y examen no se abrieron.
El control humano histórico B20 proyecta 61→67 sin pérdidas sobre estas mismas
partidas, con paridad exacta de la base. Es capacidad retrospectiva, no
descubrimiento autónomo. Los LLM no usaron ninguna guarda numérica y el resumen
omitía rangos relevantes; tampoco se les asignaba un padre de reparación.
B24 conserva sus tres modos de organización y añade correcciones comunes,
referencia R4 y control sin LLM. **Es un plan, sin implementación ni ejecución B24.**
S6 y el cierre final de ECHO-4.5 siguen pendientes.
[Autopsia y recibos](ECHO45-S6-B23-R4-FORENSICS-20261008.md) ·
[Plan B24 integrado](ECHO45-S6-B24-CONDITIONAL-PLAN.md).

**8 de octubre, 06:31 Madrid: B23-R3 cerrado y auditado; S6 sigue abierto.**
Kaggle `COMPLETE`, 2.478 partidas y 36 llamadas LLM; los 90 intentos
terminaron sin finalistas. M23, M22 y R22 midieron 18 propuestas cada uno:
ninguna pasó el criterio sin pérdidas. Las 36 salidas Qwen 7B/14B fueron
inválidas antes de simular; 33 tenían cercas Markdown y ninguna de las 36
sería legal al retirar solo las cercas. No se pudo medir ventaja del 14B.
Desarrollo amplio, conservación, confirmación, campaña y examen no se
abrieron. En ese cierre quedaba pendiente resolver la interfaz; R4 la corrigió
posteriormente, según el bloque superior.
[Resultado y recibos](ECHO45-S6-B23-KAGGLE-RESULTS-20261008.md).

<!-- S6B24-CONDITIONAL-BEGIN -->
**8 de octubre, después de R4: B24 integra la corrección del investigador.**
Comparará un investigador, tres independientes y tres con resultados
compartidos, aplicando el mismo control de novedad, aplicabilidad, reparación
y evidencia por padre. Añade referencia R4 y sintetizador sin LLM para medir
la procedencia de cualquier mejora. El diagnóstico propuesto tiene un techo
condicionado de 8.310 partidas y 80 llamadas, pendiente de contrato ejecutable,
tests y congelación. No está implementado ni ejecutándose.
[Plan B24 y condiciones](ECHO45-S6-B24-CONDITIONAL-PLAN.md).
Los bloques del 7 de octubre siguientes conservan el estado histórico previo
al arranque. [Registro de ejecución](ECHO45-S6-B23-KAGGLE-RUN-20261007.md).
<!-- S6B24-CONDITIONAL-END -->

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
<!-- S6B20-RESEARCH-END -->

<!-- S6B19-BEGIN -->
**S6-B19: CLOSED_NO_PROMOTION.** 36 propuestas, 1188 partidas físicas; auditorías y revisión aritmética válidas. No supera todas las puertas de cualificación; no hay promoción. S6 sigue abierto: piloto, campaña y examen B1–B5 pendientes. [Resultados revisados](ECHO45-S6-B19-RESULTS.md) · [Investigación](ECHO45-S6-B18-COST-FORENSICS.md).
<!-- S6B19-END -->

<!-- S6B18-BEGIN -->
**5 de octubre: S6-B18 cerrado y auditado, sin promoción.** Kaggle/T4: 14 propuestas (12 políticas distintas), 3.480 ejecuciones y ocho generaciones del LLM. El híbrido y la síntesis sin LLM pasan desarrollo con 383 frente a 378 niveles; en 40 partidas nuevas suben de 173 a 176, pero pierden score en dos casos. Ambas auditorías y la revisión local son válidas. El juez de conservación rechaza la promoción; S6, el piloto principal, la campaña y el examen B1–B5 siguen pendientes. [Resultados y recibos](ECHO45-S6-B18-RESULTS.md).
<!-- S6B18-END -->

<!-- S6B17-FORENSICS-BEGIN -->
**5 de octubre: B17 cerrado y auditado; S6 sigue abierto.** El sintetizador
sin LLM encontró 383 niveles sin pérdidas en A; el híbrido llegó a 383 con
una regresión de score en A42. La guarda válida apareció en las siete listas
de refinamiento y nunca fue elegida. El ranking usa lecturas de la base y
omite estados creados por los candidatos; el resumen temporal muestra el
consumo 55 y descarta el posterior 106 que distingue la reparación en A42.
Tres de ocho intentos híbridos repiten comportamientos anteriores.

Doce partidas nuevas de diagnóstico, con seis replays idénticos, confirman
que añadir `pending_effect=0` al mismo `HOLD=1` elimina la pérdida A42 y
conserva la ganancia A53. Las 192 fuentes congeladas siguen intactas; cero
llamadas nuevas al LLM y ninguna partida protegida. Una reconstrucción
retrospectiva con selección del primer candidato llega a la regla válida
en el intento seis. No acredita otra ejecución autónoma ni transferencia.
Pendiente: evidencia de los candidatos, cobertura acotada de guardas y
equivalencias de consumo verificadas, con pruebas nuevas antes de campaña.
No hay piloto ni campaña posterior en marcha.
[Investigación y recibos](ECHO45-S6-B17-FORENSICS.md).
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

<!-- S6B14-BEGIN -->
**S6-B14: PILOT_NO_PROMOTION; S6 abierto.** Controlador de experimentos corregido; mismo modelo y requisitos. [Contrato](ECHO45-S6-B14-DESIGN.md) · [Resultado](ECHO45-S6-B14-RESULTS.md).
<!-- S6B14-END -->

Corte del 4 de octubre, tras la auditoría B14 de las 14:07:14 Madrid: piloto
cerrado sin promoción, 54 veredictos y 5080 partidas independientes válidas.
ECHO y FIJO empatan en 1134: los seis recorridos aceptan la misma regla y llegan
a 378 desde 365. Las 36 propuestas usan REVALIDATE_NOOP; ninguna posterior
añade niveles. La memoria reciente sí llega completa. El análisis encuentra
desacoplamiento entre foco y operador, crédito antiguo que domina la selección,
alternancia de valores del mismo control y pérdida de extremos numéricos al
resumir evidencia. La misma base completa admite dos mejoras humanas PROBE2
hasta 383 en A, permitidas pero no propuestas en B14. No acreditan autonomía
ni conservación B. Siguiente paso propuesto: microablación de esos mecanismos
antes de otro piloto. Campaña y examen B14 permanecen sin abrir.
[Investigación reproducible](ECHO45-S6-B14-FORENSICS.md).

<!-- S6B13R1-BEGIN -->
**S6-B13-R1: PILOT_NO_PROMOTION; S6 abierto.** Reinicio declarado con runtime CPU nativo; criterios científicos y modelo conservados. Los resultados parciales del runtime anterior quedan separados. [Adenda](ECHO45-S6-B13-RUNTIME1.md) · [Resultado](ECHO45-S6-B13-RUNTIME1-RESULTS.md).
<!-- S6B13R1-END -->

<!-- S6B13-BEGIN -->
**S6-B13: INCOMPLETE_RUNTIME_REPLACED; S6 todavía abierto.** Trabajo reanudado por petición del propietario. PROBE2 reproducido en 240 partidas independientes (378 → 383); ese control humano no entra en los prompts. B13 prueba descubrimiento autónomo, con criterios V1–V4 y B1–B5 intactos. [Contrato](ECHO45-S6-B13-DESIGN.md) · [Resultado](ECHO45-S6-B13-RESULTS.md).
<!-- S6B13-END -->

**Cambio de publicación del 3 de octubre: investigación temporalmente privada
por Decisión.** rxlabs.org muestra Coming soon, la descripción de
RxLabs como organización que investiga IA general y robótica autónoma y el
correo knightsys@proton.me. Se retiraron documentos, artículos, archivos,
descargas y subpáginas; veinte rutas antiguas comprobadas devuelven HTTP 410.
El contexto general de echOS, echo-ai Edge, agentes LLM y echo-rsi se conserva
en metadatos y llms.txt. No se publica el nombre personal ni Discord.
El repositorio de la web `ROGEX-LABORATORIES` está privado. La web anterior y
su historial se conservan fuera del árbol desplegable en
`<LAB_HOME>/rxlabs-private-archive/20261003-130623/`.
Commit web `16199cf`, Vercel producción READY y verificación pública completa.
Mantener privados los informes de investigación; una publicación técnica
posterior requiere una nueva instrucción explícita. Los resultados y documentos
de investigación locales se conservan.

**3 oct · módulos V3 cerrados en su alcance sintético, S6 y cierre final
pendientes.** Se implementaron REL-DSL-1, la política ARC-3E-POLICY-1 con
`choose/begin/charge/mature`, integración de memoria, composición, vistas y
consistencia, y una guía de esquemas ejecutables de 500k. Las seis puertas de
módulos pasan con reproducción completa: integrado 192/192 puzzles; vistas
160→192; composición 0→32/32; política 19,21 % menos trabajo en la población
primaria equilibrada (0,166 % en la batería completa); consistencia elimina
16 compromisos erróneos mediante abstención y conserva 32/32 controles.
Guía: 4.090/4.096 frente a 1.956/4.096 con 65k y 109/4.096 sin guía, bajo una
propuesta; búsqueda de 32 programas 4.096/4.096. No es una nueva puntuación ARC.
Hay 1.952 resoluciones y 512 episodios de ajuste reproducidos, ocho bancos de
guía repetidos, 31 pruebas dirigidas y 488 de NEXUS-0 (un fallo esperado).
El usuario autoriza cerrar módulos con utilidad medible fuera de ARC; las
condiciones ARC negativas anteriores siguen vigentes. Candidato privado
`lab/seed/relational-v3-20261003/primary/candidate.json`, CLI
`PYTHONPATH=.. python3 -m seed.echo45_v3 tarea.json --candidate RUTA`.
[Informe, contratos, límites, gráficas y auditoría](ECHO45-RELATIONAL-V3-RESULTS.md).
Las entradas siguientes conservan el estado anterior a esta integración.

**Cambio de ruta del 2 de octubre: S6 aplazado por Nav.** La prioridad es
integrar memoria 3E, síntesis/refinamiento, vistas, consistencia y guía en ARC.
Se implementaron el adaptador, dos revisiones del solver, persistencia entre
procesos y comparación de nueve brazos. Memoria: **64/64 casos sintéticos,
71,04 % menos aplicaciones primitivas**, con retirada causal y replays.
Composición: **16/16 frente a 0/16** sin refinamiento. V2 sube de **2/64 a 4/64**
en ARC-1 de desarrollo conocido; en otras 128 tareas ambos candidatos empatan
en **1/128**, por lo que no se certifica la mejora general. Memoria completa
3E→ARC y ventajas de vistas/consistencia/guía siguen pendientes. Hay candidato
utilizable, no una versión 4.5 cerrada sin S6.
[Informe, comandos, costes y gráficas](ECHO45-INTEGRATION-RESULTS.md).

**2 oct · diagnóstico de capacidad y transferencia completado.** El candidato
contiene 492 asociaciones rasgo–primitiva: ocupa el 5,83 % de 65k y el 0,78 %
de 500k, sin contadores saturados. En el seguimiento, ninguno de los 3.072
recuerdos recuperados originó una solución verificada; 544 se excluyeron por
inaplicabilidad de sus operaciones/argumentos. El banco nuevo **CAP-STRESS-1
pasa su criterio de recuperación**: a 16.384 contextos, 500k 99,81 % frente a
65k 46,88 %, veinte semillas y dos reproducciones completas idénticas. Es
capacidad de almacenamiento sintético, sin nueva mejora ARC. Quedan diseñados
**ARC-3E-POLICY-1** (elección con coste diferido) y **REL-DSL-1** (objetos,
relaciones, variables y composición); su implementación y transferencia siguen
pendientes. [Análisis, matemáticas, ensayo, gráfica y ruta](ECHO45-CAPACITY-TRANSFER-FORENSICS.md).

Corte documental: 2 de octubre de 2026, Europe/Madrid. Este archivo reúne el estado operativo y la explicación técnica desde ECHO-4.0. Los resultados se atribuyen al contrato, versión, población y presupuesto que los produjo. Las cifras de las tablas son mediciones del repositorio; las decisiones futuras se presentan como trabajo pendiente.

**ECHO-4.5 sigue abierto. S6 todavía no está verde.** EGO-MEMORIA-3E pasó su examen de aldea, pero su transferencia a ARC está pendiente. El examen final disponible obtuvo 31/400 en ARC-1, 0/120 en ARC-2 y 11/112 niveles en ARC-3. PROBE2 terminó a las 04:16 Madrid: dos propuestas legales pasan V3 con 383 niveles frente a 378, sin pérdidas en las ochenta partidas A y con replay idéntico. Este control de capacidad no acredita descubrimiento autónomo ni V4. RSI1 arrancó después, pero su primera llamada abortó por ROCm. Se conserva BLOCKED. La recuperación RSI1-R1 terminó a las 08:16:37: rojo, con 99/144 recursivo frente a 101/144 aleatorio. No acredita automejora recursiva ni cambia S6. [Resultados](ECHO-RSI1-RESULTS.md).

El registro anterior se conserva íntegro en [NOW-HISTORY-20260905-20260930.md](NOW-HISTORY-20260905-20260930.md). Contiene los relevos y decisiones tal como estaban escritos antes de esta actualización, incluidos estados de ejecución que ya terminaron. Sus frases «siguiente», «en marcha» y sus estimaciones son fotografías históricas. Para decidir qué corre ahora se utiliza el corte de este documento y los artefactos vivos enlazados.

| Línea | Estado comprobado | Qué falta para su cierre |
|---|---|---|
| ECHO-4.0 | Capacidades funcionales cerradas en sus perfiles; publicación 4.0.0rc1/rc2 registrada | Reproducción por un tercero independiente y ampliación de alcance; hardware pendiente |
| ECHO-4.5, S0–S5 | Semilla, biblioteca, percepción, planificación y exámenes del gimnasio implementados | Transferencia suficiente a las evaluaciones finales |
| EGO-MEMORIA-3E | VERDE en aldea; adaptador de recibos integrado y verde de reutilización sintética 64/64 | Transferir la política adaptativa completa y confirmar utilidad en ARC |
| Integración de rejillas V2 | Ingeniería, adquisición persistente y composición sintética implementadas; 4/64 ARC-1 en desarrollo | Seguimiento empata 1/128: no pasa promoción; vistas, guía y consistencia sin ventaja de acierto demostrada |
| S6-B12-R1 | Campaña cerrada sin promoción; 378 niveles ECHO y FIJO | Otro candidato elegible, campaña nueva, cuatro brazos y B1–B5 |
| S6-PROBE1 | Medición y auditoría completadas; ninguna solución V3 en 200 individuales y 50 pares | Su resultado orienta investigación; no acredita S6 |
| S6-PROBE2 | DONE; 874 cribados, dos propuestas V3: 378 → 383 sin pérdidas en A | Auditoría independiente por reejecución; V4 y descubrimiento autónomo pendientes |
| CAPACITY-STUDY | DONE: 750 resoluciones nuevas y 750 replays, más 750 replays históricos comprobados | Confirmación independiente de la ventaja y transferencia; 65.536 iguala a 500.000 en esta muestra |
| CAP-STRESS-1 | VERDE del backend: recuperación 99,81 % vs 46,88 % a 16.384 contextos; 20 semillas, 2 replays completos | Utilidad en ARC con representación y búsqueda adecuadas; no cambia CAPACITY-STUDY ni V2 |
| ARC-3E-POLICY-1 / REL-DSL-1 | Diseño forense y plan de ablaciones documentados | Implementar política con coste diferido, esquemas relacionales y confirmar transferencia |
| HARNESS-1.5 | VERDE del arnés según N15.1–N15.5 | Mantener compatibilidad y probar cada nueva versión de ECHO |
| LOCALDEV-1 | VERDE de ingeniería: 28 pruebas del arnés y 48 del perfil; AST de 844 archivos; demo de reparación validada | [Resultados y límites](ECHO-LOCALDEV-RESULTS.md); medir calidad de propuestas con modelo real y ampliar contratos por módulo |
| RSI1 privado / R1 | Original BLOCKED; recuperación DONE/ROJO, 75 generaciones y 57 llamadas | Mejorar propuestas y demostrar acumulación y productividad bajo un contrato nuevo |
| ECHO-5 / 5.1 / 5.5 | Planes y condiciones de investigación | Implementación, controles, medición, auditoría e instalación reproducible |
| ECHO-RSI-2 | Plan de dreaming, adaptadores, router y comparación de especialistas | Contratos propios, datos suficientes, implementación y controles de atribución |

El corte documental se actualizó el **02-10-2026 tras comprobar el cierre RSI1-R1 de las 08:16:37 Madrid**. Los enlaces de estado son la referencia para una consulta posterior.

El 2 de octubre se añadió `echo-dev`, instalado localmente y documentado en
[LOCALDEV-1](ECHO-LOCALDEV-HARNESS.md). Usa las pruebas y primitivas existentes,
un entorno aislado sin red para los candidatos y un proponente opcional
configurado explícitamente. Conserva contratos, errores, costes y parches de
cada intento; las pruebas y las fuentes congeladas quedan fuera de los archivos
editables. La demostración de reparación usa mutaciones deterministas y no un
LLM. La validación de este instrumento acredita su alcance de ingeniería; no
establece porcentajes de desarrollo autónomo, mejora ARC o cierre de S6.

| Proceso / fase | Contador de este corte | Estado y dependencia |
|---|---|---|
| `echoai-s6probe2-run` / capacidad S6 | 874/874 cribados; 2/2 verificaciones completas | DONE; servicio terminado correctamente a las 04:16 |
| Solidez / replays PROBE2 | 5/5 comprobaciones; 88/88 replays de cribado idénticos | Base y ambos supervivientes con replay completo idéntico |
| Presupuesto PROBE2 | 10.048/14.544 partidas reservadas | Solo DEVELOPMENT_A; cero llamadas al modelo, B y examen sin abrir |
| RSI1 / cola original | BLOCKED a las 04:17:52; una llamada fallida sin respuesta | Evidencia preservada; sin reintento en la condición original |
| `echoai-rsi1-recovery1` / banco privado | 75/75 generaciones, 57/57 llamadas, 15/15 replays de examen idénticos | DONE/ROJO desde las 08:16:37; no queda un ensayo RSI1 en ejecución |
| CAPACITY-STUDY / guía ARC-1 | DONE desde 11:32 Madrid | 750 resoluciones nuevas y 750 replays completos; no está corriendo |
| B12-R1 / campaña S6 anterior | CAMPAIGN_NO_PROMOTION | Cerrada; no queda una campaña autónoma de cuatro brazos en ejecución |

Los supervivientes 28 y 33 pasan la verificación completa y el replay; cada uno gana cinco niveles (+1,32 %) en A, sin perder niveles ni score en ninguna de las ochenta partidas. El sondeo duró unas trece horas y doce minutos desde su arranque del 1 de octubre a las 15:04. [Resultados PROBE2](ECHO45-S6-PROBE2-RESULTS.md). No hay fecha estimable del verde de S6. RSI1-R1 consumió 57 llamadas del banco; con la llamada fallida original y la calibración suma 59 y cero euros externos. Duró unas tres horas y cuarenta y un minutos, dentro del límite de ocho horas. [Adenda de recuperación](ECHO-RSI1-RECOVERY1.md).

[Estado PROBE2](../lab/seed/s6probe2-20261001/status.json) · [Presupuesto](../lab/seed/s6probe2-20261001/budget.json) · [Fallo RSI original](../lab/research/echo-rsi1-20261001/status.json) · [RSI1-R1](../lab/research/echo-rsi1-recovery1-20261002/status.json) · [Contabilidad agregada](../lab/research/echo-rsi1-recovery1-20261002/total-budget.json) · [Capacidad terminada](../lab/seed/capacity-study-20261001/status.json).

Las referencias de estado son [roadmap 4.5→5](ECHO45-ECHO5-ROADMAP.md), [línea del tiempo](ECHO4-ECHO5-TIMELINE.md), [resultados finales](ECHO45-FINAL-EXAM-RESULTS.md), [memoria](ECHO45-EGO-MEMORIA3-RESULTS.md), [PROBE1](ECHO45-S6-PROBE1-RESULTS.md) y [contrato PROBE2](ECHO45-S6-PROBE2-DESIGN.md). Algunos documentos anteriores conservan cortes desactualizados; aquí se indica cuándo un resultado posterior los sustituye.

La arquitectura se entiende siguiendo una ejecución. Un entorno produce una observación. El encoder la convierte a WSP. CAM localiza o registra el episodio. Q propone una acción; los módulos habilitados pueden orientar esa propuesta. El gate decide la acción permitida. El predictor anticipa la consecuencia de esa acción efectiva. Se ejecuta la transición, se compara la predicción con la nueva observación y se aprende de la consecuencia real. Un LLM opcional propone hipótesis en experimentos específicos, sujeto a un verificador externo a su texto.

```text
entorno → observación → WSP16 → CAM / contexto
                                     │
                            Q / propuesta del actor
                                     │
                         gate OK | MODIFY | BLOCK
                                     │
                    predicción para la acción efectiva
                                     │
                 ejecución → consecuencia → error / aprendizaje

LLM opcional → propuesta estructurada → pruebas → aceptación o rechazo
visor       ← registros de la ejecución
```

Este esquema describe componentes compartidos y sus adaptadores. ECHO-SEED, el actor ARC y la aldea de memoria tienen bancos y ejecutores específicos. La existencia de esos módulos separados no permite afirmar que todas sus capacidades estén integradas en una sola política. [INTEGRATE-1](ECHO4-INTEGRATE1-RESULTS.md) acredita una integración concreta de ECHO-4; [memoria→ARC](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md) sigue siendo una integración pendiente.

**WSP, Q_N, CAM y aprendizaje entero.** El núcleo conserva el paquete de 16 bytes de `wsp.h`: fuente, relación, destino, tiempo, seis valores E enteros y extensión de procedencia. E[6] contiene V/A/D/C/U/B dentro de ±100. Son variables del modelo, con funciones programadas y medibles. Las etiquetas emocionales históricas no acreditan emociones experimentadas. El formato variable del vendor RogexWSP es otro formato; no debe confundirse con estos 16 bytes. [Inventario](01-INVENTORY.md), [invariantes](02-INVARIANTS.md) y [especificación](05-NEXUS-0-SPEC.md) fijan esa distinción.

El encoder semántico utiliza normalización y reglas de correspondencia. El FNV del texto se conserva como control histórico: repartir cadenas por hash no demuestra que se haya comprendido su significado. `simhash16` proyecta el paquete a una dirección de 16 bits. La distancia entre dos direcciones es:

```text
d_H(u,v) = popcount((u XOR v) AND 0xffff)
Q_N = Q8 × Q8
direcciones posibles = 256 × 256 = 65.536
```

Una dirección posible, una ranura CAM y una neurona son unidades distintas. Q_N ejecuta LIF sobre un spoke de 256 células; CAM reserva 4.096 ranuras. El núcleo Q6 histórico tiene 64 células y un código [6,3,3]. Q8 utiliza un codebook [8,4,4]. La corrección de patrones por atractores y Hamming es una propiedad limitada del código y su banco, no una medida de razonamiento general. Q6 preserva su comprobación de un bit 48/48. Las fórmulas y números proceden de [navi10_qn.py](../../navi10_qn.py) y el [inventario](01-INVENTORY.md).

La actualización LIF del spoke usa fuga 7/8, corriente de estímulo y vecinos del hipercubo. El potencial se limita a 255; el umbral base es 40, reducido en las células del codebook por I_CODE=12. Al disparar, el potencial vuelve a cero. Para una célula i:

```text
I_i = estímulo_i + hop_i + Σ_j W_EDGE · spike_j
j recorre i XOR (1 << b), b=0…7
V'_i = min(255, floor(7·V_i/8) + I_i)
spike_i = [V'_i ≥ umbral_i]
V_i siguiente = 0 si dispara; V'_i en otro caso
```

La plasticidad STDP entera de [navi10_stdp.py](../../navi10_stdp.py) ajusta sus pesos bajo gates E. Esa plasticidad y la tabla Q cumplen funciones diferentes. CAM guarda evidencia de lo sucedido; Q guarda valores para decidir. Una hipótesis cortical conserva su estatus de hipótesis hasta tener evidencia admitida por el módulo correspondiente. En el verificador basal, un vecino Hamming cercano necesita también extracto para respaldar un hecho. La cercanía de códigos por sí sola resulta insuficiente.

El STDP existente mantiene ocho pesos de dimensión. LTP suma uno en los bits que coinciden entre direcciones; LTD resta uno en los que difieren; ambos limitan el peso a ±40. La energía de arista calculada es `32−peso`, una magnitud del algoritmo. El gate de plasticidad abre con C<20; U≥60 selecciona camino corto ignorando pesos; A aporta `max(0,A)//20` al estímulo. Esta regla discreta implementada debe distinguirse de una curva biológica general de STDP, de backpropagation y de aprendizaje en silicio.

[World/T](../nexus0/world.py) aprende un sucesor por par `(slot,acción)`. Conserva ganador, contador, alternativa y contador alternativo, hasta 65.535. Una alternativa sustituye al ganador únicamente si su cuenta es estrictamente mayor; el empate conserva el incumbente. Una tercera alternativa se registra como conflicto y no desplaza la ya guardada. Es una tabla acotada, con pérdida potencial de detalle en transiciones multimodales. El inverso almacena solo vecinos observados y cuenta descartes al saturar, en lugar de crear una matriz 4.096×4.096.

La confianza T es ordinal 0–3: nunca visto, visto una vez, repetido sin respaldo suficiente o con conflicto, y al menos ocho observaciones consistentes sin alternativa. El error de predicción usa Hamming entre vértices cuando se conoce el esperado; un miss recibe el código de error fijado. Esa confianza no es una probabilidad calibrada. PATTERN y SENSATION agregan contexto a la misma representación para reducir aliasing, manteniendo sus condiciones de contradicción y capacidad.

En [QTable](../nexus0/qtable.py), el caso basal tiene 4.096×3 valores lógicos int8, equivalentes a 12.288 bytes si se empaquetan. En Python son listas de enteros y ocupan más memoria. No se debe publicar ese tamaño lógico como RSS del proceso. Las acciones originales son approach, avoid y wait; extensiones como OPEN-1 piden explícitamente una cuarta acción sin cambiar el ancho histórico por defecto.

```text
δ = r + floor(7·max_a Q(s',a)/8) − Q(s,a)
Q(s,a) ← clip_int8(Q(s,a) + (δ >> 2))
si la transición es terminal: max_a Q(s',a) = 0
```

La rama basal usa desplazamiento aritmético y redondea los negativos hacia menos infinito. CREDIT-1 añade opcionalmente restos enteros para no perder créditos menores de una unidad: acumula `resto+δ`, divide hacia cero por cuatro, paga la parte entera y conserva el resto. Por ejemplo, cuatro deltas de 3 pueden pagar 3 unidades acumuladas. No se debe describir la rama basal y CREDIT-1 con un único redondeo. Las trazas de elegibilidad son otra alternativa opt-in; el constructor rechaza usar restos y trazas simultáneamente. Todo ello está en el mismo QTable, sin otro almacén de política.

La exploración periódica importa. Con cuatro acciones y periodo ocho, `turn % 4` en los turnos de exploración escogería siempre la misma acción. `_settled_phase` usa el índice de los turnos exploratorios cuando periodo y número de acciones comparten divisor. Es una corrección aritmética de cobertura, no una capacidad descubierta por el agente. `best()` conserva wait en empates. δ se escribe en Q; no se deposita en E[V].

El [gate](../nexus0/gate.py) es una función explícita. `inhibit` bloquea y devuelve wait; una aproximación con amenaza sin extracto se modifica a avoid; la espera con urgencia alta y amenaza también se modifica. El gate no ejecuta comandos del sistema ni concede permisos de disco. La ruta rápida mantiene operaciones enteras. NEXUS-0 permanece con el córtex apagado en su banco principal. Los adaptadores locales de Qwen en otros contratos no alteran ese requisito.

La validación general del 30 de septiembre cerró 488 pruebas con un fallo esperado histórico. Los errores pendientes de las pruebas GUI provenían de sockets localhost bloqueados por el entorno y se verificaron bajo el permiso registrado, sin modificar el núcleo para omitirlas. Una excepción del arnés o de permisos se informa separada de una aserción conductual. [Recibo y comandos](ECHO45-NEXUS0-VALIDATION-20260930.md).

**ECHO-4.0, 21–24 de septiembre: cuerpo, atribución, continuidad y convivencia.** La siguiente tabla identifica qué hace cada bloque, qué partes se construyeron y qué examen concede su resultado. El verde siempre pertenece al perfil de la última columna.

| Bloque | Componentes y algoritmo | Evidencia de cierre y límite |
|---|---|---|
| WORLD-1 | Física entera; reserva H, temperatura, contabilidad; analizador de viabilidad | 16.002 estados vivos, 48.006 transiciones, 15.954 estados viables; el agente basal murió a los 37 pasos |
| SENSATION-1 | Ventana 0/2/4; predictor temporal aprendido; fallback a T; auditoría de aliasing | Examen predictivo nominal B/C; incertidumbre separada del error; no elimina el estado oculto |
| BOUNDARY-1 | Pares intervención/espera restaurados; contraste por canal y retardo; máscaras | B/C 1.408/1.408 evaluaciones cada una; cero influencia falsa; solo canales U/B |
| SELF-1 | Referencia nominal; espacio finito de hipótesis; sondas discriminantes; permiso de aprendizaje; reutilización | Examen final A/B/C y replay; atribución y memoria útiles bajo prior mecánico declarado |
| CONTINUITY-1 | Snapshot, restauración, sesiones activas, linaje, cuarentena y recalibración | 69/69 casos, 300/300 eventos y 186/186 turnos idénticos; 30/30 mutantes rechazados |
| DREAM-1 | Árbol de intentos, replay parcial, programas cerrados, selección y promoción | v3 900/960 frente a fijo 640 y azar 721; ablaciones sin Qwen y sin feedback empatan |
| MAINTAIN-1 | Estimación corporal, intervenciones seguras, reserva preventiva, averías/repuestos | 144/144 vidas recuperables y 192/192 reparaciones; modelo mecánico virtual conocido |
| OTHER-1 | Historia pública separada por identidad; predicción discreta de contraparte | 1.536/1.536 en cohortes heterogéneas; memorias privadas, sin lectura de Q ajena |
| INTERACTION-1 | Dos agentes, incentivos y costes; creencias públicas; coordinación aprendida | Neto focal de evaluación 6.912 vs 6.144; coste formativo impide ventaja individual en toda la vida |
| RELATION-1 | Episodios de encuentros, orden temporal, consulta a contraparte, límites de confianza | Neto B 4.920/4.812 vs mejor control 3.556/3.382; límites ante impostores publicados |
| ROLES-1 / TRIBU | Competencia por recibos, eliminación, jerarquía derivada, inversión y mentiras | v5 satisface criterios; rango declarado no cambia conducta; la jerarquía viene de pruebas |
| SITUATE-1/2 | Sensores de sustrato, pruebas de replay, respuestas respaldadas, filtro de afirmaciones LLM | 16 condiciones nuevas por examen; 96 llamadas reales en SITUATE-2; cero fenomenales creídas |
| INTEGRATE-1 | Vida de 256 ticks; mantenimiento, tribu, relaciones, continuidad y firewall | Examen verde con ablaciones; acoplamiento asimétrico declarado |
| RELEASE-1 / CODE-1A | Wheel, sala limpia, identidad por manifiesto; MCP de comprobación de código | INTEGRATE reproducido; CODE bloquea 60/60 acciones adversas del corpus; límites de plataforma y distribución |

Fuentes: [programa ECHO-4](ECHO4-EGO-PROGRAMA.md), [WORLD](ECHO4-WORLD1-RESULTS.md), [SENSATION](ECHO4-SENSATION1-CLOSURE.md), [BOUNDARY](ECHO4-BOUNDARY1-RESULTS.md), [SELF final](ECHO4-SELF1-FINAL-RESULTS.md), [CONT-D](ECHO4-CONTINUITY1-D-RESULTS.md), [DREAM v3](ECHO4-DREAM1-D-V3-RESULTS.md), [MAINTAIN](ECHO4-MAINTAIN1-FINAL-RESULTS.md), [OTHER](ECHO4-OTHER1-RESULTS.md), [INTERACTION](ECHO4-INTERACTION1-BCD-RESULTS.md), [RELATION](ECHO4-RELATION1-D-RESULTS.md), [ROLES v5](ECHO4-ROLES1-V5-RESULTS.md), [SITUATE-1](ECHO4-SITUATE1-RESULTS.md), [SITUATE-2](ECHO4-SITUATE2-RESULTS.md), [INTEGRATE](ECHO4-INTEGRATE1-RESULTS.md), [RELEASE](ECHO4-RELEASE1-RESULTS.md) y [CODE](ECHO4-CODE1-A-RESULTS.md).

WORLD-1 respondió primero si el objetivo era físicamente posible. [DockRules](../echo4/world.py) fija capacidad 127, H inicial 32 y temperatura 64. Approach añade cinco recursos y dieciséis unidades de calor; avoid gasta hasta tres recursos y reduce dieciséis de temperatura; wait gasta hasta uno y añade cuatro de calor. H=0, temperatura=0 o temperatura=127 terminan la vida. Las unidades son abstractas. Cada paso debe cumplir:

```text
H_antes + entrada_externa = H_después + consumo + derrame
```

El [analizador](../echo4/viability.py) construye el grafo finito de estados vivos. Elimina por una cola los estados sin sucesor vivo y propaga la eliminación a sus predecesores. El conjunto restante es el punto fijo de viabilidad:

```text
K0 = estados vivos
K(n+1) = {s en K(n): existe a tal que transición(s,a) pertenece a K(n)}
K* = punto fijo
```

El testigo entra en un ciclo de dos acciones `(127,112) →avoid→ (124,96) →approach→ (127,112)`. El analizador conoce la física completa y pertenece al juez. El agente basal aprende mediante sus observaciones y no recibió ese testigo; murió por calor al paso 37. Separar alcanzabilidad física y éxito aprendido evitó atribuir al actor la solución del oráculo. El control sin fuente de recursos produjo núcleo vacío.

SENSATION comenzó midiendo pérdida de información. Sobre 947.496 prefijos supervivientes comunes, recordar cuatro pasos dejó 874.554 aún ambiguos. La observación presente no permite inferir siempre un estado físico único; añadir historia aporta información limitada. La ventana de dos transiciones ocupa 50 bytes de payload local; cuatro ocupa 84. WSP sigue midiendo 16. El predictor utiliza historias exactas y reglas tras ocho repeticiones, retira respuestas ante contradicción y recurre a T cuando falta evidencia temporal. Predice después del gate y antes de la transición. Se entrenó con 8.192 episodios y 104.705 transiciones; B/C usan 2.048 episodios nuevos cada una. La primera vida integrada conservó los 37 pasos basales. [Cierre predictivo](ECHO4-SENSATION1-CLOSURE.md).

La precisión temporal B/C fue 85,5359%/86,1237% frente a 84,6903%/85,3438% de T: +0,8456/+0,7799 puntos. Se exigían al menos diez mil muestras, mejora ≥0,5 puntos, cobertura ≥98%, confianza alta en ≥5% y precisión ≥95% dentro de ese subconjunto. Ambos exámenes pasaron, con 218/203 victorias emparejadas y cero pérdidas. Historia de cuatro pasos solo agregó dos aciertos por etapa y descartó altas al llenar su registro. Dos pasos era el brazo primario fijado antes: no se eligió retrospectivamente el mejor de varias longitudes. La estimación de objetos Python CAM/T/PATTERN/contexto fue unos 3,93 MB; los cincuenta bytes describen la ventana, no toda la memoria.

BOUNDARY comparó intervención y espera desde el mismo estado restaurado. Para canal j y retardo k calcula:

```text
Δ(j,k) = [obs_intervención(j,k) − obs_intervención(j,0)]
       − [obs_espera(j,k) − obs_espera(j,0)]
```

[BoundaryMap](../echo4/boundary.py) exige recibos emparejados, acción realmente aplicada, dos ticks y ausencia de modificación/veto. Conserva como máximo 128 filas y 4.096 pares. Un signo positivo exige ocho muestras, ninguna negativa y al menos 7/8 positivas; el negativo es simétrico. Un efecto nulo requiere todas cero. Una contradicción o insuficiencia devuelve desconocido. Solo bytes 8/9, U/B, son elegibles; los otros catorce permanecen desconocidos. Observar un cambio tras una tecla no basta para una atribución causal.

SELF-A enumeró 7.920 condiciones y encontró 119 clases de evidencia con causas incompatibles incluso usando ambas acciones. Había 3.256 condiciones dentro de esas clases ambiguas. Esa dificultad provenía de identificabilidad: dos causas distintas podían producir la misma evidencia disponible. SELF-B añadió una referencia de ocho esperas y seis secuencias de sondeo. Conserva hipótesis compatibles con la transición nominal, acoplamientos binarios y un pulso externo en {-16,-4,0,4,16}. Tras una observación y, el espacio de versiones se actualiza:

```text
H_siguiente = {h en H_actual: predicción(h, acciones_aplicadas) = y}
diagnóstico = etiqueta común si todas las h restantes coinciden
diagnóstico = unknown en cualquier otro caso
```

El selector rechaza ensayos que puedan terminar la vida bajo una hipótesis restante y busca separar las clases posibles. La versión activa identificó 7.920/7.920 en el censo con 66.660 pasos; el orden fijo necesitó 133.320. La reducción fue del 50% en ese catálogo. La física nominal y la posibilidad de restaurar ensayos son supuestos suministrados por el laboratorio. [SELF-A](ECHO4-SELF1-A-RESULTS.md), [SELF-B](ECHO4-SELF1-B-RESULTS.md) y [SelfAttributor](../echo4/self_attribution.py).

SELF-C v1 protegió aprendizaje, pero empataron selectivo y control en 126/240 vidas completadas. Esa métrica estaba saturada por los 126 casos físicamente viables. La pregunta posterior fue si la memoria preservada ayuda después de restaurar el cuerpo. SELF-C v2 consiguió 108/144 objetivos de confirmación frente a 90 sin protección, 56 congelando todo y 48 sin consultar T. La restauración la ejecutó el arnés. El examen final amplió a H fuera del censo anterior, 80 condiciones y 240 objetivos por fase. Reutilización selectiva A/B/C: 186/189/193 sobre 240; los controles sin protección: 148/152/143. Los casos mixtos siguieron teniendo fallos. El permiso de aprendizaje se aplica a T, inverso y PATTERN, mientras Q recibe la recompensa real. [C v1](ECHO4-SELF1-C-RESULTS.md), [C v2](ECHO4-SELF1-C-V2-RESULTS.md), [final](ECHO4-SELF1-FINAL-RESULTS.md).

CONT-A serializó el estado completo del ejecutor, referencias compartidas y contexto. CONT-B añadió las sesiones de diagnóstico y recuperación activas. CONT-C separó reanudar, bifurcar, cambiar de cuerpo y originar un descendiente. Reanudar conserva identidad administrativa y reloj; bifurcar crea ramas independientes; cambiar de cuerpo o heredar revoca permisos y exige cuarentena y recalibración. Un terminal sigue terminal. Los checkpoints usan JSON con tipos y campos permitidos, hash esperado externo y límites; evitan pickle. El hash demuestra integridad respecto de la custodia conocida, sin autenticar por sí solo a un tercero. CONT-D reconstruyó 69 casos, incluidos 30 mutantes rechazados. El perfil es síncrono entre turnos completos; captura concurrente y pérdida abrupta de energía quedan fuera. [Continuity](../echo4/continuity.py), [ActiveRun](../echo4/continuity_active.py), [linaje](../echo4/continuity_lineage.py).

DREAM-A guardó un árbol causal de intentos nativos y permitió consultar ramas ya observadas. Una rama ausente devuelve desconocido. DREAM-B/C/D añadió Qwen, gramática cerrada, replay y selección con incumbente. v1 obtuvo 130/240, por debajo de controles de 150–165. v2 continuó roja; cambiar prioridades dentro del mismo catálogo no bastó. v3 añadió dos contrastes corporales y seguridad condicionada: una prueba descartada al principio puede resultar segura después de eliminar hipótesis por observación. Los caminos observados se conservan como caminos, con hasta 22 ramas por contexto. El cierre dio 900/960, pero los controles sin Qwen y sin feedback empataron. Se acredita el sistema de exploración y selección del contrato; una ventaja exclusiva del modelo no quedó demostrada. Los programas iniciales y el catálogo fueron ingeniería humana. [v1](ECHO4-DREAM1-BCD-RESULTS.md), [v2](ECHO4-DREAM1-D-V2-RESULTS.md), [v3](ECHO4-DREAM1-D-V3-RESULTS.md).

MAINT-A construyó desgaste, avería, intervención y contabilidad sin conceder cierre. MAINT-B añadió hipótesis sobre capacidad corporal y elección segura con reserva preventiva. MAINT-C mantuvo vidas sin reset, repuestos finitos y continuidad de memoria; MAINT-D comparó controles y reconstruyó trayectorias. Trabajo: 9.450 frente a fijo 7.501, sin reparar 4.815 y sin historia corporal 4.672. Se confirmaron 192/192 reparaciones y 144/144 vidas recuperables. [MaintainControl](../echo4/maintain_control.py) orienta la propuesta original y observa la acción que realmente ejecutó el Agent; el gate sigue funcionando. El alcance conserva el modelo mecánico programado y sus límites de reparación. [Resultados](ECHO4-MAINTAIN1-FINAL-RESULTS.md).

OTHER separa experiencias públicas por contraparte. Dos Agent mantienen CAM/T/Q privadas. El observador predice conducta discreta a partir de encuentros, sin recibir valores Q o incentivos privados del otro. Con contrapartes heterogéneas, separar identidad dio 1.536/1.536; mezclarla, 1.008/1.536; copiar conducta propia, 0/1.536. Cuando las políticas eran iguales, copiar podía acertar; ese control distingue predicción de diversidad real. [OtherModel](../echo4/other_model.py) y [examen](ECHO4-OTHER1-RESULTS.md).

INTERACTION-A mostró que ejecutar dos políticas simétricas no establece cooperación aprendida: una primera secuencia obtuvo neto 485 frente a 576 solo. B/C/D añadieron aprendizaje y controles con costes. En evaluación, el focal obtuvo 6.912 frente a 6.144 y el neto físico conjunto 9.984 frente a 6.656. Contando formación, el focal quedó en 14.059/14.136 frente a solo 15.360. La tabla separa mejora en la tarea evaluada y coste de toda la vida. Las contrapartes eran nativas y preentrenadas dentro del perfil. [Sesión](../echo4/interaction_session.py), [aprendizaje](../echo4/interaction_learning.py), [resultados](ECHO4-INTERACTION1-BCD-RESULTS.md).

RELATION-A registró quién encontró a quién, cuándo y qué sucedió. B utilizó esos recuerdos al pedir ayuda en otra tarea. C probó relevos, ausencia, impostores, identidad nueva, extractos alterados, CAM llena y veto. D usó dos cohortes nuevas: history dio 4.920 y 4.812 frente a other_only 3.556 y 3.382. La historia útil conserva orden e identidad. Un impostor con buenas experiencias previas engañó cuatro veces; posteriormente una generalización excesiva llevó al agente a dejar de pedir a cualquiera. Se conserva como limitación. [Memoria](../echo4/relation_memory.py), [ayuda](../echo4/relation_help.py), [testigos C](ECHO4-RELATION1-C-RESULTS.md), [D](ECHO4-RELATION1-D-RESULTS.md).

ROLES A/B midió competencia observada y adaptación; C añadió casos adversos; D v1 falló cuando cambiaron competencias. v2 mostró que parte de la ventaja anterior dependía de controles que no exploraban. Se igualó la exploración nativa. La línea de tribu añadió tres aprendices, eliminación de candidatos, jerarquía derivada de recibos y cambios de papel; v5 cerró su contrato. ECHO deduce quién sabe a partir de respuestas verificadas y conserva «dijo que no sabía» como hecho del encuentro, pero su contenido como hipótesis sobre saber. Una declaración de rango no altera la política. En el examen v5, deducción correcta 1.700/1.751 y 1.711/1.760; jerarquía propia 32/32 por cohorte; cambio de jerarquía 8/8. Los anexos de mentira y metaconocimiento prueban contradicciones y búsqueda de respuestas propias. [ROLES D v1](ECHO4-ROLES1-D-RESULTS.md), [v5](ECHO4-ROLES1-V5-RESULTS.md), [tribu](../echo4/tribe.py), [mentiras](../echo4/tribe_liar.py), [metaconocimiento](../echo4/tribe_liar2.py).

SITUATE-1 consulta sensores reales de proceso, runtime y huella de programa; registra procedencia en CAM. El hostname se sustituye por huella. La prueba de mundo ejecuta dos veces la misma semilla y compara trazas. Ante sensores ausentes responde desconocido. Su examen de dieciséis condiciones usa procesos nuevos, reanudación y una versión alterada. SITUATE-2 permite al LLM interpretar hechos y somete cada afirmación al verificador. En 96 llamadas reales, 80/80 afirmaciones de sustrato quedaron correctamente clasificadas y ninguna de 128 afirmaciones fenomenales entró en la creencia. Con LLM caído, SITUATE-1 sigue funcionando. El perfil 3/14 publicado no concede un veredicto de conciencia. [SITUATE-1](../echo4/situate.py), [SITUATE-2](../echo4/situate2.py).

INTEGRATE probó vida de 256 ticks, reanudación exacta, cuerpo, tribu, relaciones y firewall. La ablación sin mantenimiento redujo trabajo 579→450; sin SELF, reparaciones 6→0; sin razonamiento de tribu, preguntas 807→1.157; sin relaciones, primeras preguntas acertadas 314→202; sin firewall aparecieron seis hechos falsos en tres vidas de desarrollo. Estas son cifras del desarrollo sellado; el recibo del examen concede el cierre `e1492e22…`. El acoplamiento cuerpo/tribu es asimétrico y debe leerse en el contrato. [Resultados](ECHO4-INTEGRATE1-RESULTS.md).

RELEASE compiló el núcleo, construyó wheel para CPython 3.14 Linux x86_64 y reprodujo INTEGRATE en sala limpia sin el árbol fuente en sys.path. Los fallos cleanroom-v1/v2/v3 se conservaron: parser del JSON, huellas ausentes y gancho de ejecución de módulos. A5 v1 quedó rojo por introspección de una prueba en el núcleo compilado; Nav aprobó una enmienda posterior al rojo para separar comportamiento compilado y suite fuente. La versión de esa condición figura explícita. El registro posterior documenta rc1 y rc2 publicados con acceso condicionado y descarga limpia, pero todavía falta un tercero independiente. Compilar dificulta leer el código; no impide ingeniería inversa ni convierte la huella del constructor en firma externa. [Resultados y enmienda](ECHO4-RELEASE1-RESULTS.md), [registro histórico](NOW-HISTORY-20260905-20260930.md).

CODE-1A expuso comprobaciones por MCP: acción permitida, evidencia de tests, símbolos y memoria tras reiniciar. El examen envió comandos como texto; no los ejecutó. Bloqueó 60/60 adversos del corpus, tuvo 4/111 falsos bloqueos legítimos y rechazó un diario alterado. «Los tests pasan» con fuente modificada después de ejecutar tests se clasifica desconocido. Su resultado no autoriza a inferir seguridad frente a cualquier comando o repositorio. [Servidor](../echo4/code_mcp.py), [gate](../echo4/code_gate.py), [memoria](../echo4/code_memory.py), [examen](ECHO4-CODE1-A-RESULTS.md).

**ECHO-4.5, desde el 25 de septiembre: conceptos de rejilla y modelos de juegos.** La versión parte de ECHO-SEED, con primitivas pequeñas y sandboxes clonables. El gimnasio de rejillas reúne 1.009 tareas de entrenamiento ARC-1/2; 201 se reservaron para seguimiento y 808 para aprendizaje. Ese seguimiento se consultó en varias fases. Los conjuntos oficiales de evaluación quedaron aparte hasta su examen y, una vez abiertos, no vuelven a ser un examen nuevo ciego. [Contrato de origen](ECHO45-SEED-DESIGN.md).

| Fase y revisión | Hipótesis / cambio | Medida y decisión |
|---|---|---|
| S0 | Primitivas iniciales, wake/sleep, diario y clones | 44 familias; 15 tests correctos de 201 en el cierre S1 |
| S1 | Objetos: seleccionar, aislar, comparar y transformar componentes | 65 primitivas; 21/201; el entrenamiento S1 empató con su semilla |
| S1b | Relaciones adicionales, vocabulario mayor | 73 primitivas; 20/201 sin mejor prioridad: dilución de búsqueda |
| S2 inicial | Frecuencias, conceptos con slots, evolución desde base entrenada | 21→21; conceptos paramétricos reales no nacieron; clones poco diversos |
| S2v | Presupuesto determinista, 84 primitivas y prioridad por frecuencias | 24/201 con 400 expansiones; 1.500 no añadió aciertos; verde S2 |
| S2 intuición neuronal | Guía entrenada con sueños sintéticos en T4 | Recall@5 0,78/0,79, pero empate 24/201 con frecuencia; sin ventaja reservada |
| S2 currículos | Tres clones desde semilla, órdenes distintos | Aprendizajes distintos; los tres transfirieron las mismas 21 tareas S1 |
| S3 / v3 | Excluir reloj visual y clicar dentro del objeto | Desarrollo oficial: siete niveles y score 0,506→0,678; ocho replays exactos |
| S3b | Cuerpo por contingencia y exploración por posición | No añadió niveles; cuerpos gemelos/ambiguos y exploración sin meta limitaron utilidad |
| S4 v4/v4.1 | Curiosidad, meta por semejanza, balbuceo motor | Revisiones rojas; siete/ocho niveles con peor score; un éxito dependía de semilla |
| S4 v5 | Predicción por transición, muros por color, planificación en modelo, causas remotas | Desarrollo verde; score medio 0,849; no es examen reservado general |
| S5 v5.2 | Generador ARC3-GYM, controles de solvencia y familias nuevas | S5-D: 1.103 vs 940 niveles según su contrato |
| S5 v5.6 | Cajas y clic | Desarrollo/gym-test: 805 vs 600; sin examen congelado específico de esa revisión |
| S5 v5.7 | Memoria de copia | S5-E: 475/900 vs 399/900; replay de sesenta partidas exacto |
| H1/H3 v5.8 | Secuencias ordenadas y conteo de reentradas | S5-F2: 1.537/1.800 vs 1.239/1.800; F1–F6 verdes; 120 replays exactos |
| Refinamiento / multi-view / relaciones | Editar hipótesis y probar programas con varias vistas | Doce ARC-2 de desarrollo: S0 0/12; S2v 2/12 en los cuatro brazos; sin ventaja adicional |
| ARC por capacidad | Ablaciones de relaciones y composición | Sintético: 12/12 completo, 6/12 sin relaciones, 9/12 sin composición; 36 replays |
| Guía dispersa 640→500k | Priorizar familias con asociaciones verificadas | Desarrollo ARC-1: 3→5→6/250; 65.536 igualó posteriormente 500k |

Fuentes: [S1](ECHO45-S1-RESULTS.md), [S2 y sus negativos](ECHO45-S2-DESIGN.md), [S3](ECHO45-S3-DESIGN.md), [S4](ECHO45-S4-DESIGN.md), [S5](ECHO45-S5-DESIGN.md), [S5-D](ECHO45-S5-D-DESIGN.md), [S5-E](ECHO45-S5-E-RESULTS.md), [H1/H3](ECHO45-H1-H3-RESULTS.md), [S5-F2](ECHO45-H1-H3-EXAM2-RESULTS.md), [refinamiento](ECHO45-REFINEMENT-RESULTS.md), [S2v refinamiento](ECHO45-REFINEMENT-S2V-RESULTS.md), [diagnóstico de capacidades](ECHO45-ARC-PREPARATION-RESULTS.md).

Una rejilla en [dsl.py](../seed/dsl.py) es una tupla de tuplas. Las operaciones aplican transformaciones y devuelven una rejilla nueva o fallan si su dominio no corresponde. La dimensión se limita a 30. La búsqueda trata un fallo de aplicación como rama no aplicable. El parser estricto de [refinement.py](../seed/refinement.py) comprueba además que las celdas sean enteros 0–9. El helper `G` básico no contiene por sí solo toda esa validación; la documentación no le atribuye garantías de otro adaptador.

Los objetos se extraen por BFS de componentes conectados del mismo color, con cuatro vecinos y opción diagonal. «Objeto» significa ese criterio computacional. Un contorno que oculte varias piezas, una figura multicolor o un patrón con semántica distinta puede necesitar otra representación. Recorte usa mayoritario como fondo en su operación; otras primitivas fijan cero. Suponer que todas las operaciones tienen idéntica definición de fondo produciría errores.

El catálogo incluye geometría, recorte, escalado, teselado, espejos, mitades, combinaciones lógicas, componentes, gravedad, filtros de color, huecos, líneas, selección por tamaño, transformaciones por objeto y secciones. S1/S1b/S2v activan sus familias explícitamente. Cada paso de un programa es una primitiva con argumentos o un concepto aprendido. La implementación conserva sus versiones y los manifiestos indican cuál se activó en cada banco.

[learn.solve](../seed/learn.py) busca mejor primero sobre el estado conjunto de todas las demostraciones. Un estado contiene una salida provisional por ejemplo. La distancia es uno si cambia la forma; si coincide, fracción de celdas erróneas, promediada sobre demostraciones:

```text
D(G,T) = promedio_i d(G_i,T_i)
d = 1 si dimensiones distintas
d = (# celdas distintas) / (# celdas objetivo) si mismas dimensiones
prioridad = coste_acumulado + 3·D
```

La frontera es un heap; `seen` elimina estados de demostraciones ya visitados. El algoritmo devuelve un programa cuando reproduce exactamente todas las demostraciones, o termina al agotar expansiones/profundidad. Esta heurística no acredita una búsqueda óptima global: el primer camino a un estado puede bloquear otro distinto, y varios programas exactos pueden dar outputs de test distintos. El nombre VERIFIED del diario se refiere al ajuste demostrado; la corrección en el test requiere el juez separado. El solver heredado admite outputs de test para reportar `test_ok`; los adaptadores nuevos retiran esas respuestas antes de llamarlo. La frontera usa solo targets de demostraciones.

`Library.step_cost` cambia prioridades mediante frecuencia o guía. `sleep` extrae subsecuencias de dos/tres pasos presentes en programas verificados de al menos dos tareas. Las convierte en macro de coste de búsqueda de un paso, conservando expansión ejecutable y procedencia. `sleep_parametric` normaliza colores a slots `$0/$1`, exige la misma estructura en varias tareas y al menos dos asignaciones de color. Ejemplo ilustrativo:

```python
# Misma estructura observada en tareas distintas:
programa_a = [("recolor", 1, 2), ("crop",)]
programa_b = [("recolor", 3, 5), ("crop",)]
# Macro con slots, ejecutada luego con los colores de otra tarea:
concepto = [("recolor", "$0", "$1"), ("crop",)]
```

El mecanismo paramétrico pasó su control sintético, pero los 84 programas reales iniciales no ofrecieron las repeticiones necesarias para crear uno. Tener el algoritmo no implica haber aprendido esa abstracción en ARC. La ganancia S2v provino del vocabulario ampliado y su prioridad útil bajo el presupuesto declarado.

El refinador prueba hipótesis múltiples, mide forma, celdas, histograma y objetos, y edita por añadir, reemplazar o eliminar un paso. La tupla de calidad se ordena lexicográficamente: errores de forma, error de píxeles normalizado, objetos, colores y profundidad. Ocho vistas geométricas reutilizan rotaciones/reflejos y su inversa; se canonizan tramos geométricos para no contar identidades repetidas. La regla buscada en una vista se interpreta como `v⁻¹ ∘ programa ∘ v`. Todas las vistas comparten un solo límite global de programas, no ocho presupuestos independientes.

Las cuatro relaciones nuevas son `objects_to_row`, `marker_recolor`, `recolor_by_size` y `connect_color`. Componen objetos por área, usan un marcador singleton, recolorean tamaños extremos y unen posiciones del mismo color por fila/columna. La consistencia agrupa predicciones de programas que ajustan todas las demostraciones y declara ambigüedad cuando corresponde. Muchos programas compatibles no convierten automáticamente una salida en verdad. En doce tareas reales S2v, todos los brazos acertaron 2/12; los más elaborados gastaron 24.000 pruebas de programas frente a 2.391 de una pasada. Este coste adicional quedó registrado sin atribuirle una mejora inexistente.

En juegos, [echo_arc/agent.py](../echo_arc/agent.py) opera con fotogramas y acciones permitidas. El cuerpo se estima por contingencia entre tecla y movimiento de componentes. El reloj visual se distingue del área interactiva para evitar clicar contadores. El clic apunta a una celda perteneciente al objeto, porque un centro medio puede caer fuera de una L o un anillo. Muros se generalizan por color tras bloqueos repetidos. La planificación recorre posiciones alcanzables bajo esas reglas; un camino calculado sigue siendo una hipótesis hasta ejecutar y comprobar cada movimiento.

S4 tuvo que corregir dos confusiones: faltaban pruebas de todas las teclas y se perseguía al gemelo móvil como meta. Más tarde, ver frames de desarrollo mostró que g50t requería copia sobre interruptor para abrir compuerta. La ingeniería agregó representación de cambios remotos, causa candidata y prioridad para probar teclas de modo. Un nivel ganado puede proponer tipo de objeto-meta para el siguiente; no entrega la solución de todos los juegos. El cuerpo rectangular y los colores aún restringen cobertura. Las decisiones de diseño tomadas viendo desarrollo están declaradas.

S5 tuvo varios rojos antes del cierre S5-D. Gym v1 era demasiado fácil: azar resolvía 27% cuando el límite era 15%. Gym v2, declarado después, amplió mapas y exigió soluciones más largas; azar bajó a 4,9%. El v5 original seguía resolviendo menos niveles que v3. Se descubrió que el centro del suelo se movía al quedar un hueco y se confundía con el cuerpo, y que la meta se tomaba del nivel siguiente a ganar. v5.1 exigió movimiento rígido de las celdas y leyó la meta del frame anterior al cambio. La variante BABBLE=2 se eligió entre seis variantes fijadas en gym-train; su score mejoró, pero aún perdía cobertura. Esos resultados no se borraron al llegar v5.2.

v5.2 confirmó causas al repetirlas desde el paso correcto, reutilizó causas útiles tras GAME_OVER, excluyó saltos de reinicio al aprender muros y probó teclas de modo al tocar objetos nuevos. En gym-test v2 pasó a 681 niveles sumados frente a 600 de v3; luego S5-D midió una cohorte nueva y obtuvo 1.103 frente a 940. El solucionador exacto del generador usa BFS del estado privado para comprobar solvencia y obtener referencia mínima de acciones; el actor recibe frames y acciones, sin ese estado ni el camino óptimo. Semillas fijas separan gym-train, gym-test y cada examen. [Historia y decisiones S5](ECHO45-S5-DESIGN.md), [S5-D](ECHO45-S5-D-DESIGN.md).

Después, v5.3 intentó aplicar el modelo corporal también a clic y se descartó por pérdidas en desarrollo oficial. v5.4 infirió objetos empujables por movimiento rígido conjunto y planificó el estado cuerpo+objeto; caja subió de 0,5 a 4,5 niveles medios. v5.5 trató un clic que mueve consistentemente otro cuerpo como tecla virtual; flechas subió a cinco niveles. v5.6 agrupó píxeles que cambian juntos como unidades de efecto y buscó planes hacia su estado-meta; luces mejoró score 0,7→9,3. Esas cifras pertenecen a gym-test ya consultado; no son nuevos exámenes ciegos. v5.7 añadió la memoria de copia y obtuvo después su S5-E nuevo. Las versiones v5.x son revisiones del actor ARC de ECHO-4.5, distintas del futuro modelo ECHO-5.

H1 añade [OrderMemory](../echo_arc/temporal_memory.py): historial de dieciséis entradas y hasta sesenta y cuatro reglas de pares ordenados. Cuenta apoyos como máximo una vez por episodio; acumula conflictos; devuelve candidatos con apoyos mayores que conflictos. H3 añade CountMemory: hasta sesenta y cuatro instancias y conteo limitado a 255. Quedarse sobre el marcador no suma otra entrada. Solo aprende un umbral con episodio completo y sin mezclar varias instancias/tipos que confundan la causa. Reiniciar borra el intento, pero conserva las reglas aprendidas. La expulsión acotada de estas reglas locales no destruye slots CAM; no debe confundirse con KCC de CAM.

En desarrollo, H1 subió 45→134/135 y H3 77→152/165 niveles. La ablación sin conteo perdió seis niveles en una muestra de treinta; sin orden conservó niveles y empeoró eficiencia. v5.8 añadió también planificación y exploración, por lo que la ganancia total frente a v5.7 no se atribuye solo a dos memorias. En ocho juegos oficiales de desarrollo, ambas versiones quedaron en veinticuatro niveles sumados sobre tres repeticiones y ninguna acción del controlador temporal se activó. S5-F2 usó semillas nuevas 17000–17059: 1.537 vs 1.239/1.800, sin regresiones individuales del contrato y 120 replays. [Resultado y separación](ECHO45-H1-H3-EXAM2-RESULTS.md).

**S6: hipótesis, filtros, obstáculos y condiciones del verde.** S6 pregunta si ECHO consigue ayuda útil al decidir qué pedir, verifica las propuestas y conserva habilidades. El brazo SEMILLA es el mismo actor sin cambios. FIJO pide ayuda genérica. ECHO usa sus fallos, tipos de petición y feedback. SIN FILTRO recibe las mismas propuestas seguras/ejecutables de ECHO, en el mismo orden, omitiendo la comprobación de utilidad. Su score no se utiliza para entrenar ECHO.

S6-A se realizó sobre rejillas con trescientas propuestas por brazo. S6-B y las revisiones posteriores probaron políticas de juegos y cambiaron gramática o evidencia bajo contratos nuevos. Las 201 tareas de rejillas y los 1.800 niveles de ciertos exámenes de juegos son poblaciones distintas. «Cuatro brazos» conserva la pregunta causal, pero no permite sumar sus puntuaciones ni trasladar requisitos entre revisiones.

| Revisión | Cambio / hipótesis puesta a prueba | Resultado conservado |
|---|---|---|
| S6-A | LLM genera operaciones nuevas de rejilla; peticiones adaptativas y filtros | SEMILLA/FIJO/ECHO 24/201; SIN FILTRO 25 con 244 operaciones; ninguna útil aceptada |
| S6-B0 | Programas cerrados de estrategia sobre v5.7 | Todas las propuestas fallaron formato; cuatro brazos 1.378/1.800 |
| S6-B1 | Calibrar transporte/inferencia | Detenido en calibración; no resultado de capacidad |
| S6-B2 | Corregir inferencia y formatos | Desarrollo con aceptaciones, pero examen ECHO/FIJO 1.350 vs SEMILLA/SIN FILTRO 1.387: rojo |
| S6-B3 | Selección de políticas temporales v5.8 | ECHO/FIJO/SEMILLA 1.668; SIN FILTRO 1.586; B3–B5 pasan, B1/B2 fallan |
| S6-B4 | Reparaciones locales más acotadas, piloto antes del examen | Veinticuatro propuestas, ninguna aceptada; A 178/200; reserva sin abrir |
| Control manual | Comprobar si la gramática permite una reparación útil | Veinte reparaciones; hold20 mejora +3 A pero pierde score B; ninguna V1–V4 |
| Precisión / B5 | Condiciones más precisas y control previo positivo | Seis de doce controles positivos; piloto ECHO 534/FIJO 534, cero aceptaciones |
| B6 | Evidencia de dónde se consume cada parámetro | ECHO 534/FIJO 537, sin promoción; doce veredictos auditados |
| B7 | Refinar tras resultados reales de la propuesta | Una mejora ECHO aceptada A 178→181; suma ECHO/FIJO 537; empate impide promoción |
| B8 / CPU / Q8 | Evidencia, descarga y backends declarados | Descargas fallidas y float16 parcial; Q8 cerró 534/534 sin promoción |
| B9 | Transiciones y compatibilidad de guardas | 534/534; ninguna aceptación; control humano positivo separado |
| B10 | Rechazar guardas incompatibles y duplicados | 534/534; cero aceptaciones; propuestas perdían score individual protegido |
| B11 | Desarrollo mayor, contrastes y selección adaptativa | Piloto 1.129/1.108, tres mejoras ECHO; campaña detenida por límite de contexto |
| B12 / R1 | Contexto contado, reducción documentada y recuperación del límite remoto | Campaña ECHO/FIJO 378/378; una aceptación ECHO; sin promoción |
| PROBE1 | Censo y muestra de capacidad sin LLM | 200 individuales y 50 pares; cero V3; 22.160 partidas A; 25 replays exactos |
| PROBE1 auditoría independiente | Caché nueva y reconstrucción de originales | 480 partidas, cuatro candidatos y base; válida; fallo tupla/lista del comparador recuperado explícitamente |
| PROBE2 | Buscar guardas HOLD 0/1 que conserven A53 sin pérdidas | DONE; dos propuestas V3, 383 niveles; B y examen sin abrir |

Las revisiones y sus contratos/resultados están enlazados individualmente en el inventario documental al final. El [diagnóstico del 29 de septiembre](ECHO45-S6-DIAGNOSIS-20260929.md) y la [respuesta a Opus](ECHO45-S6-CAPACITY-ANALYSIS-20260930.md) son interpretaciones de registros; las referencias bibliográficas no comprobadas de la respuesta de Opus conservan ese estatus y no respaldan afirmaciones nuevas aquí.

En B12 se exige V1 formato y seguridad; V2 ejecución y reproducción; V3 ganar al menos dos niveles A sin perder nivel ni score de ninguna partida; V4 conservar niveles y scores individuales B con tolerancia 1e-10. Desarrollo A: ochenta partidas, gym v2/v3, semillas 0–39 y dos mil decisiones por partida. B: cuarenta partidas protegidas, semillas 24920–24939, ya reutilizadas y declaradas. Solo su aceptación/rechazo vuelve al modelo. Seis rondas y cinco propuestas por brazo hacen sesenta propuestas de campaña. La política empieza vacía; no hereda el ganador del piloto. [Contrato B12](ECHO45-S6-B12-DESIGN.md).

Un candidato p con base b puede superar V3 únicamente si:

```text
Σ_i niveles(p,i) ≥ Σ_i niveles(b,i) + 2
para toda i de A:
    niveles(p,i) ≥ niveles(b,i)
    score(p,i) + tolerancia ≥ score(b,i)
```

Un +4 total no basta si reduce score de una sola partida. Una mejora +1 limpia tampoco basta bajo +2. Dos +1 rechazadas no se acumulan porque cada incorporación necesita pasar por sí sola. Si otro contrato permite dos parches por propuesta, se declara antes de medir y se aplica a todos los brazos; no se renombra como éxito del contrato de un parche.

El examen B12 previsto, todavía sin abrir por falta de promoción, usa semillas 25100–25159, versiones v2/v3 y tres repeticiones: 360 partidas y 1.800 niveles por brazo. SEMILLA, FIJO, ECHO y SIN FILTRO se congelan antes de abrir. Su resultado no vuelve a una petición LLM. Los juegos oficiales de desarrollo se evalúan por separado. El código reutilizado de [s6_precise_exam.checks](../seed/s6_precise_exam.py) fija:

| Puerta | Verde solamente cuando | Qué discrimina |
|---|---|---|
| B1 | Niveles ECHO ≥105% de SEMILLA y score medio/agregado del contrato no menor | Ayuda útil frente al actor original |
| B2 | Niveles ECHO estrictamente mayores que FIJO | Utilidad de elegir qué preguntar |
| B3 | Niveles ECHO estrictamente mayores que SIN FILTRO | Utilidad de comprobar propuestas |
| B4 | Conserva niveles y score agregados de los ocho juegos oficiales de desarrollo, tres repeticiones | Conservación de las habilidades medidas |
| B5 | Fuentes, pesos, tokenización, peticiones, veredictos, solver y replays auditables | Validez y procedencia de la comparación |

```text
S6 verde = promoción válida ∧ auditorías válidas ∧ B1 ∧ B2 ∧ B3 ∧ B4 ∧ B5
```

B4 del examen compara agregados del contrato. V3/V4 de aceptación conservan cada partida individual. Son garantías diferentes; no se presenta el examen como prueba de cero regresiones individuales universal. La garantía de conservación siempre se limita a las cohortes medidas.

Los fallos de S6 tienen varias causas comprobadas. En B0 la salida se cortaba y el JSON/operadores no eran válidos. B2 encontró políticas que funcionaban en desarrollo y empeoraron la reserva. B3 rechazó todo cambio y mantuvo ECHO igual a SEMILLA: el filtro evitó daño de SIN FILTRO, pero no generó mejora. B4–B10 mostraron parámetros sin efecto, condiciones que nunca coincidían, repeticiones y ganancias con pérdidas de eficiencia. B7 sí consiguió una incorporación útil, pero FIJO también mejoró y empataron. B11 produjo ventaja en el piloto; el prompt de la campaña excedió su límite congelado antes de generar ECHO. Ninguno de estos fallos se explica solo contando neuronas.

B12 contó tokens con el tokenizer exacto, incluido chat template, antes de inferir. Conserva peticiones que caben byte a byte. Cuando exceden seis mil tokens, intenta cinco formatos: vectores con leyenda reversible; primera divergencia; secuencias del intento reciente; agregados completos de propuestas/veredictos; finalmente oportunidades resumidas. Registra qué omitió como desconocido. Si la mínima no cabe, detiene antes de enviar. Los tokens se cotejan también en el worker remoto. R1 recuperó un límite de ejecución remoto conservando siete respuestas previas idénticas. Reparar transporte y completar auditoría demuestra instrumento válido; la campaña terminada sigue empatada a 378.

La revisión posterior encontró que 25 propuestas REFINE eran REVALIDATE_NOOP del programa aceptado en vez de refinar el COOLDOWN_CAP indicado, y que 16/30 propuestas ECHO no cambiaban acciones. Las mejores ganancias de cooldown eran +1, insuficientes para V3. Eso motivó medir capacidad sin modelo antes de invertir en prompts. Sigue abierta la hipótesis de que falta un lenguaje más expresivo o evidencia que separe dónde una regla ayuda y dónde perjudica.

PROBE1 contó 70.208 propuestas legales, 154 demostrablemente inertes y 15.454 clases de firmas de activación. Se prerregistraron cinco propuestas conocidas y 195 sorteadas por estratos, más hasta cincuenta pares. No es muestreo uniforme de toda la gramática; no corresponde aplicar `3/200` como cota estadística de existencia. Dos partidas concentraron mejoras: A18 dio +1 limpio; A53 dio +4 con pérdidas de score en otras. Los pares heredaron esas pérdidas. Se ejecutaron 22.160 partidas A y veinticinco replays idénticos. «Ninguna pasó en este presupuesto» es la conclusión; no demuestra agotamiento del lenguaje.

La auditoría independiente repitió base y cuatro candidatos 2/31/77/178 en caché separada, 480 partidas, y comprobó los 22.160 registros originales. Un error de comparación tuplas/listas marcó BLOCKED aunque los hashes brutos coincidían. Se conservó el fallo y se congeló una recuperación que normaliza la representación JSON; no se alteraron resultados del agente. El recibo [audit.json](../lab/seed/s6probe1-20260930-audit/audit.json) cerró válido el 1 de octubre.

PROBE2 examina todas las 874 propuestas HOLD 0/1 legales que tocan A53. HOLD solo se lee en diez de las ochenta partidas A de la base. Las features variables relevantes eran level y world_events. El cribado ejecuta las cuatro a diez partidas tocadas por cada guarda; una muestra fija de cinco candidatos ejecuta las ochenta para contrastar el argumento de que las no tocadas quedan idénticas. No se considera equivalente en conducta una firma igual: se miden todos los representantes legales del plan, no solo las 126 firmas.

Los controles 77/178 deben reproducir PROBE1 byte a byte. Un superviviente del cribado necesita medición completa de ochenta partidas y replay completo. Se reservan hasta treinta verificaciones y el tope total es 14.544 partidas. Cuatro procesos, Python 3.12, PLAN_SHA `a725b39f44d9fa1257ac0d621274b7c27a1494c927e354895061c021191be66b`. Una diferencia de replay, un efecto en partida supuestamente no tocada o control distinto detiene el instrumento. El presupuesto y las paradas no convierten instrumentación inválida en resultado negativo. [Código](../seed/s6probe2.py), [contrato](ECHO45-S6-PROBE2-DESIGN.md), [revisión](ECHO45-S6-PROBE2-INDEPENDENT-REVIEW.md).

El cierre del 2 de octubre midió las 874 propuestas y encontró dos supervivientes: ambos llegan a 383 niveles desde 378 con replay completo idéntico y ninguna pérdida de nivel o score por partida. Los 88 replays de cribado y las cinco muestras de solidez pasaron. Las 10.048 partidas pertenecen a A. El resultado demuestra capacidad de la gramática vigente bajo V3; no demuestra transferencia a B, automejora autónoma, éxito de campaña ni B1–B5. Las reglas halladas por búsqueda dirigida humana quedan fuera de los prompts de descubrimiento autónomo. [Resultado completo](ECHO45-S6-PROBE2-RESULTS.md).

La [revisión del cierre](ECHO45-S6-PROBE2-CLOSURE-REVIEW.md) reconstruyó los veredictos y comprobó los 10.048 digests de caché, sin jugar partidas nuevas. Su recibo válido confirma los archivos guardados; aún falta reproducción independiente en una caché distinta. El primer resultado de RSI1-R1 fue una respuesta con formato inválido, rechazada sin promoción. El transporte CPU terminó correctamente y el banco cerró posteriormente rojo bajo esos mismos criterios.

La siguiente decisión depende de ese cierre. Si aparece una guarda con +4 sin pérdidas A, ya basta para V3 desde 378→382: no hace falta sumar A18. Sigue faltando V4 en otro contrato y que ECHO encuentre/verifique una solución sin recibir el parche obtenido por el humano. Si solo hay pares útiles, se diseña una condición de dos parches para todos los brazos. Si no aparece nada, se estudian features o familias nuevas mediante controles de desarrollo. La auditoría protege el resultado; no crea una mejora que el actor no produjo.

**EGO-MEMORIA: aprender qué experiencias conservar.** EGO-MEMORIA-1 construyó diario y pruebas formativas. EGO-MEMORIA-2 agregó costes demorados y aprendió de acciones ejecutadas; pasó M1–M4 en dieciséis semillas y replay M6, pero M5 quedó en 15/16. La semilla 31011 no alcanzó el umbral original de aprendizaje/ventaja. Ese rojo permanece. La serie 3A–3E cambió cómo se asigna crédito entre navegación, escritura y consecuencias posteriores, con desarrollo separado y reserva sin abrir hasta elegibilidad.

| Revisión | Hallazgo de desarrollo | Decisión |
|---|---|---|
| 3A | Retornos completos; M1 23/24; coste +1.333 | Sin promoción |
| 3B | Costes separados; M1–M5 24/24; coste +1.370 | Sin promoción: todavía más cara |
| 3C | Horizonte/plazo 49; M5 23/24; coste −1.114 | Sin promoción |
| 3D | Exploración disminuye por experiencia; M1 23/24; coste −9.840 | Sin promoción |
| 3E | Crédito depende de si realmente quedó prueba conservada | M1–M5 24/24; coste −15.324 (−2,05%); abre reserva |

En [village3_receipts.py](../seed/village3_receipts.py), un recibo registra si hubo prueba útil en el diario. Los costes posteriores se asignan a esa condición y maduran tras el horizonte. La elección suma estimación de navegación, coste de escribir y retorno demorado de la prueba conservada. El buffer de crédito contiene metadatos; no guarda una prueba oculta que sustituya al diario. La estructura causal factorizada fue programada por humanos y compartida con controles; el agente aprendió sus valores de utilidad por consecuencias. No hay recompensa arbitraria por escribir ni etiquetas privadas entregadas al actor.

El examen procedural nuevo usa 43000–43015. M1 escritura selectiva; M2 menor coste y errores repetidos; M3 retirar recuerdos formativos cambia conducta y retirar igual cantidad de otros no; M4 clones divergen por experiencia con citas propias; M5 verificar se aprende por consecuencias; M6 reconstruye exactamente. Los seis pasan en 16/16. El juez del laboratorio custodió la reserva, sin tercero externo. [Cierre](ECHO45-EGO-MEMORIA3-RESULTS.md). El [plan de transferencia](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md) necesita un adaptador, comparación con/sin memoria y misma información, presupuesto y base. Su verde en aldea permanece válido; la ventaja ARC todavía se tiene que medir.

**La ampliación de capacidad y sus cifras reales.** [SparsePrimitiveGuide](../seed/kenyon_capacity.py) tiene un banco de pesos uint8 y proyección dispersa fija. El término «500.000 unidades» designa posiciones de ese banco, no quinientas mil células LIF simuladas ni un LLM entrenado. Aprende asociaciones entre features de demostraciones y primitivas utilizadas en programas exactos. El helper vuelve a ejecutar todas las demostraciones antes de incrementar un peso. No lee respuestas de test ni incorpora propuestas por confianza textual.

Cada pareja `(feature, nombre_primitiva)` se procesa con BLAKE2b de 32 bytes y genera ocho índices módulo N. Los pesos se incrementan hasta 255. La puntuación de una familia es la suma de los pesos asociados a features comunes entre demostraciones. Si el máximo es positivo, se produce una guía `0,05 + 0,55·score/máximo`; si todos son cero, 0,05. Son pistas de ordenación, no probabilidades calibradas. Ampliar N cambia colisiones y capacidad asociativa, sin añadir otra primitiva o permiso de aceptación.

```text
j_k = entero32(BLAKE2b(feature || NUL || familia)[4k:4k+4]) mod N
w[j_k] ← min(255, w[j_k]+1), k=0…7
s(familia) = Σ_feature Σ_k w[j_k]
guía(familia) = 0,05 + 0,55·s(familia)/max(s)
```

Las features describen tamaños, diferencias de dimensión, fracción de celdas cambiadas, paletas/histogramas, objetos y ajuste geométrico de demostraciones. La guía vive en una copia aislada de Library. NEXUS-0 y las fuentes S6 congeladas no la importan. Las 60 tareas/programas de entrenamiento están separados de las 250 tareas ARC-1 de desarrollo.

| Banco de guía | Exactos /250 | Porcentaje | Ganancia sobre base | Regresiones frente a 640 | Pesos no cero | Bytes lógicos de pesos |
|---|---:|---:|---:|---|---:|---:|
| Sin guía | 3 | 1,2% | — | Pierde las dos ganancias de 640 | — | 0 |
| 640 | 5 | 2,0% | +0,8 pp | — | 633 | 640 |
| 4.096 | 5 | 2,0% | +0,8 pp | Pierde una y gana otra | 2.189 | 4.096 |
| 16.384 | 5 | 2,0% | +0,8 pp | Pierde una y gana otra | 2.832 | 16.384 |
| 65.536 | 6 | 2,4% | +1,2 pp | Ninguna; una nueva | 3.025 | 65.536 |
| 500.000 | 6 | 2,4% | +1,2 pp | Ninguna; una nueva | 3.085 | 500.000 |

El [summary.json completo](../lab/seed/capacity-study-20261001/summary.json) cerró el 1 de octubre a las 11:32 Madrid y sustituye el texto «pendiente» para los tamaños intermedios del [informe editorial anterior](ECHO45-CAPACITY-STUDY-RESULTS.md). Sus tres brazos nuevos sumaron 750 resoluciones y 750 replays; se cotejaron otros 750 históricos. Todos los nuevos brazos conservan los tres aciertos base. 4.096/16.384 intercambian `a68b268e` por `e3497940` frente a 640; 65.536/500.000 conservan ambos y añaden `e3497940`.

Tiempo CPU agregado descriptivo: base 2.648,44 s; 640 2.719,45; 4.096 2.368,96; 16.384 2.443,77; 65.536 2.437,80; 500.000 2.744,42. Los tres extremos históricos y los tamaños nuevos se midieron en lotes diferentes; estas cifras no demuestran aceleración por capacidad. El contraste histórico 500k/base fue +3,624% de CPU. El contraste 500k/640 fue +0,918%. La RAM total requiere medición del proceso; no se infiere del bytearray.

La diferencia principal de 500k frente a 640 es una tarea de 250, +0,4 puntos porcentuales. No hay evidencia suficiente de significación o de una relación monótona con tamaño. El control sintético de cuatro transformaciones dio 33/40 con 640 y 40/40 desde 4.096; ya estaba saturado con capacidad mucho menor. La recomendación provisional es comparar 65.536 y 500k en otra cohorte declarada antes de elegir un default; una cifra mayor por sí sola no acredita mejor arquitectura.

Se generaron cuatro gráficas PNG/SVG, 84 GIF de familias candidatas y ocho GIF de pasos de programas realmente ejecutados, todos con póster y datos. La geometría y el giro 3D son ilustrativos. Los índices, pesos y sumas representados proceden del banco real; el GIF no muestra actividad LIF o pensamiento del modelo. Noventa y dos GIF y 2.576 fotogramas se decodificaron en el paquete inicial. [Media y manifiesto](../lab/publication/capacity-20261001/index.html). La publicación y los fallos de rutas de la web pertenecen a otro repositorio; los recibos locales no permiten inferir por sí solos el estado actual de Vercel.

**Exámenes ARC y porcentajes comparables.** En rejillas un acierto exige coincidencia exacta de todas las celdas del test. Ajustar las demostraciones no basta. En ARC-3 se publican niveles y score con la convención del runner del contrato. Los reinicios automáticos están registrados aparte y no consumen el presupuesto de decisiones congelado de algunos gimnasios. Esa convención debe acompañar cualquier comparación; no se sustituye un scorecard oficial por el número del gimnasio.

| Examen final del 28 de septiembre | Semilla | Candidato 4.5 | Diferencia | Puerta |
|---|---:|---:|---:|---|
| R1 ARC-1, 400 tareas | 20/400 = 5,00% | 31/400 = 7,75% | +11 tareas; +2,75 pp; +55% relativo sobre 20 | PASA |
| R2 ARC-2, 120 tareas | 0/120 | 0/120 | 0; porcentaje relativo indefinido | FALLA |
| R3 ARC-3, 112 niveles | 13/112 = 11,61% | 11/112 = 9,82% | −2 niveles; −1,79 pp | FALLA: objetivo ≥23 niveles |
| Score ARC-3 del contrato /100 | 0,069413 | 0,643679 | Aumenta eficiencia según esa fórmula | No sustituye la puerta de niveles |
| R4 custodia | — | 1.040 soluciones y 32 partidas reproducidas | Auditoría válida con recuperación explícita | PASA |

El +55% relativo de ARC-1 usa una base de veinte tareas, no significa 55 puntos porcentuales. El score ARC-3 mayor coexistió con menos niveles; publicar ambos evita ocultar la pérdida. Los brazos con/sin S6 eran alias porque no existía operación S6 promovida que los diferenciara. Los dieciséis juegos reservados ARC-3 ya habían tenido exámenes anteriores y no se presentan como cohorte nueva ciega. [Resultado](ECHO45-FINAL-EXAM-RESULTS.md), [contrato](ECHO45-FINAL-EXAM-DESIGN.md), [adenda de auditoría](ECHO45-FINAL-AUDIT-RECOVERY.md).

Una comparación de capacidad usa:

```text
acierto = 100·correctas/N
ganancia_pp = 100·(correctas_candidato − correctas_base)/N
ganancia_relativa = 100·(correctas_candidato − correctas_base)/correctas_base
si correctas_base=0: ganancia_relativa=null
ganadas = aciertos_candidato menos aciertos_base
perdidas = aciertos_base menos aciertos_candidato
```

Las pérdidas se listan por tarea/juego aunque el total suba. Se fija solver, información, cohorte, profundidad, expansiones, llamadas y versiones; un mismo techo no siempre produce el mismo gasto efectivo. El [comparador ARC](../seed/arc_comparison.py) comprueba procedencia y rechaza políticas provisionales. La preparación verificó 190 fuentes protegidas y reconstruyó 536 registros previos. Su diagnóstico sintético no estima un score ARC futuro.

**Arnés, registros y límites de observación.** echo-nexus 1.5 es una herramienta beta de desarrollo. Su núcleo público integra instalación, perfiles de conexión, GGUF/API/MCP, editor multilínea, copia, catálogo y mundo de sesión. OpenRouter utiliza HTTPS. Los modelos retirados se validan contra catálogo; una respuesta HTTP 404 no se interpreta como falta de pensamiento de ECHO. Los secretos se referencian por archivo/perfil y no se incluyen en logs ni documentación.

La procedencia es visible: `/echo` usa registros sin LLM; `/ask` consulta al neocórtex. El desarrollo actual no permite afirmar que cualquier respuesta conversacional sea generada por la política simbólica de ECHO. Una respuesta del asesor sin aplicación verificada al actor conserva su fuente externa. Las coordenadas y brújula del visor humano no se añaden como pista privada al motor. El contador de procesos, partidas, niveles, errores y reinicios ayuda a distinguir partida completada, muerte y cierre normal. [Contrato](ECHO45-HARNESS15-DESIGN.md), [resultado](ECHO45-HARNESS15-RESULTS.md).

La animación de actividad comunica etapas observables: consultando modelo, recibiendo propuesta, validando, ejecutando y registrando resultado. Los árboles muestran observaciones, candidatos y decisiones realmente guardadas. No exponen razonamiento interno oculto ni generan un monólogo atribuido al agente. `thought.jsonl` y la mini terminal forman la observabilidad ya existente. No se inventa otro bus de pensamientos ni se devuelve el texto del visor al actor. [Guía](ECHO45-OBSERVABILITY.md).

```bash
# Ejemplos para NUEVO desarrollo; consultar la guía antes de lanzar.
python3 observe.py --launch --demo
# Para conocer la interfaz disponible sin iniciar una campaña:
python3 observe.py --help
```

Los exámenes/campañas sellados se observan mediante sus estados y resultados guardados; no se reinician ni instrumentan a mitad para producir vídeo. Una observación puede añadir tiempo y se declara en su perfil. Cerrar tapa, perder Wi-Fi, suspender host y cerrar sesión son eventos distintos. Un servicio local soporta que se cierre el chat; no ejecuta cómputo con el host suspendido. El trabajo remoto ya enviado puede continuar sin Wi-Fi, pero el supervisor local no consulta nuevos resultados hasta recuperar conexión. RSI1-R1 tiene [recibo de servicio instalado](../lab/research/echo-rsi1-recovery1-20261002/launch.json), sin reinicio automático.

**Dirección de investigación después de este corte.** La prioridad S6 conserva los umbrales vigentes. PROBE2 ha demostrado capacidad V3 en el lenguaje actual; queda auditar mediante reejecución y diseñar la condición autónoma con memoria del objetivo, evidencia pertinente y control aleatorio de gramática si el contrato lo incorpora. Una solución hallada por el laboratorio no se atribuye al modelo ni se entrega como respuesta de examen. Después hacen falta conservación V4, campaña elegible y examen reservado nuevo de cuatro brazos B1–B5.

Para finalizar 4.5 faltan la automejora S6, transferencia de EGO-MEMORIA y de operaciones de objetos/relaciones, un candidato de rejillas distinto con ventaja ARC-2 y un actor de juegos que alcance la puerta ARC-3 conservando habilidades. Se prepara una evaluación posterior con datos conocidos etiquetados como seguimiento y, para afirmaciones ciegas, particiones nuevas bajo otro contrato. [Orden posterior](ECHO45-POST-S6-PLAN-20260929.md).

Las [visiones de ECHO-5, 5.1 y 5.5](ECHO5-51-55-RESEARCH-VISION.md) se documentan por separado como propuestas de investigación, con antecedentes, hipótesis, controles y criterios pendientes de prerregistro. ECHO-5 investigaría objetos y relaciones, composición jerárquica, abstracciones, planificación hacia atrás y reparación precisa. ECHO-5.1 estudiaría colaboración: comparar un agente fuerte con especialistas al mismo presupuesto total, compartir recuerdos verificables con procedencia y medir el coste del orquestador. Vectores latentes entre modelos diferentes requieren compatibilidad que todavía no se ha probado; embeddings opacos no sustituyen hechos WSP auditables. Evolución de prompts, cuantización o más agentes necesitan ablaciones que separen capacidad, cómputo y elección humana.

RSI1 privado convierte «automejora» en tres condiciones verificables: mejora en puzzles nuevos, al menos dos incorporaciones sucesivas sin regresión y productividad superior al investigar desde el estado retenido. Usa el GGUF local Qwen3 4B, CPU, tres réplicas, cinco generaciones, hasta 57 llamadas y cero euros externos. Conserva treinta primitivas S0 sin argumentos y genera macros de dos/tres pasos. Los cinco brazos son semilla, aleatorio, LLM solo, ECHO sin acumulación y ECHO recursivo. Las bibliotecas se sellan antes de cuarenta y ocho tareas finales por réplica. Recursivo debe superar al mejor control al menos 3/48 en cada réplica, además de replays y ensayo de productividad. Las doce tareas de investigación y dos llamadas por condición ofrecen evidencia limitada. [Contrato](ECHO-RSI1-DESIGN.md), [preparación y límites](ECHO-RSI1-READINESS.md).

El cierre RSI1-R1 obtuvo 96/144 base, 101/144 aleatorio, 0/144 LLM solo, 99/144 sin acumulación y 99/144 recursivo. Solo hubo una promoción en el brazo recursivo, en una réplica, y ninguna en el ensayo de productividad. El análisis posterior encuentra 57 llamadas, 11 prompts distintos, diez respuestas inválidas y tres programas válidos distintos. [Recibo del análisis](../lab/research/echo-rsi1-recovery1-20261002-analysis/proposal-diversity.json). Las cifras orientan un piloto nuevo de diversidad y feedback; no justifican cambiar el rojo.

La propuesta [ECHO-RSI-2](ECHO-RSI-2-RESEARCH-PLAN.md) añade siete módulos pendientes: índice de trazas, simulador de ramas, generación con feedback, arena de propuestas, router de neocórtex, adaptación de pesos y dos ciclos de evolución medidos. Distingue simulación ejecutable de lectura de trazas, y mejora de biblioteca de mejora de pesos o consulta a un modelo más fuerte. Propone CPU local y una GPU alquilada por etapas dentro del presupuesto previsto; no hay entrenamiento ni infraestructura contratada.

Ese banco utiliza seis familias sintéticas conocidas y rejillas nuevas, sin archivos ARC ni datos S6. Mide evolución de biblioteca cerrada; no reescribe el núcleo ni entrena pesos del LLM. El ejemplo simple de diseño saturaba 6/6 y se cambió antes de congelar por composiciones de objetos/gravedad, conservando una base completa. El resultado incluirá S6_green=false. Un éxito permitirá diseñar una prueba mayor, sin inferir superinteligencia de una curva sintética.

ECHO-5.5 tiene un objetivo de candidato medido antes de diciembre, condicionado a resultados y recursos. La infraestructura propuesta mantiene núcleo/verificador/cola en CPU y GPU por horas para perfiles o un adaptador local pequeño. APIs cerradas permiten usar un modelo, no disponer de sus pesos. Pesos abiertos y licencia permiten evaluar LoRA/QLoRA. Los 180 euros son presupuesto previsto; no se ha alquilado GPU ni gastado API en RSI1. El [plan de infraestructura](ECHO55-INFRASTRUCTURE-PLAN.md) y la [oferta piloto en borrador](ECHO55-PILOT-OFFER-DRAFT.md) separan investigación e ingresos por instalación/evaluación. No hay ingresos demostrados ni equivalencia frontier acreditada.

Después de 5.5 se propone [ECHO-RSI-1](ECHO-RSI-1-LAB-PLAN.md), distinto del banco privado RSI1 actual. Su diseño añade un examen del investigador evolucionado, un segundo ciclo de investigación, transferencia y reproducción externa. R0–R9 son criterios propuestos pendientes de prerregistro; no acreditan RSI universal al 100%. El laboratorio inicial reutilizaría CPU local y una base abierta pequeña, con GPU alquilada y un primer techo de 20–30 € dentro de los 180 € previstos. La [línea temporal](ECHO4-ECHO5-TIMELINE.md) incorpora esta etapa como pendiente, sin alterar los contratos congelados.

**Cómo se mantiene la evidencia.** Antes de medir se escriben contrato y límites, se fijan fuentes y pesos por SHA-256 y se registra el plan. Desarrollo decide elegibilidad; el examen solo mide una versión congelada. El diario enlaza eventos por hashes y conserva programa, petición, fuente, hipótesis, acción aplicada y resultado. Un esquema típico de cadena es `h_i = SHA256(h_(i−1) || bytes_canónicos(evento_i))`; la serialización concreta y los separadores pertenecen al módulo enlazado. Un hash sin custodia confiable detecta cambios relativos a su recibo, no demuestra que el evento físico haya sucedido.

La auditoría vuelve a construir veredictos, métricas y trayectorias. Replays internos prueban determinismo; una caché nueva evita confundir recuperar una medición con volver a ejecutarla. El auditor del laboratorio es independiente del proceso original, pero no se presenta como certificación de una organización externa. Si hay error del instrumento se informa BLOCKED y se conserva. Una recuperación necesita adenda y fuentes propias. Si la medición es válida y pierde, se cierra roja. Ninguna revisión posterior elimina esa evidencia.

La documentación describe algoritmos y examen con suficiente detalle para contrastarlos con el código, sin abrir respuestas reservadas, claves o archivos privados para el actor. Los siguientes fragmentos se extraen del código existente y quedan identificados por fuente. Son ejemplos de lectura; no son órdenes de lanzamiento ni nuevos programas aprendidos por ECHO. El catálogo posterior permite recorrer funciones, familias y contratos completos.

Distancia Hamming entera del espacio Q_N. Fragmento de [hamming16](../../navi10_qn.py#L79); dependencias y contexto permanecen en su archivo.

```python
def hamming16(u: int, v: int) -> int:
    return popcount((u ^ v) & ADDR_MASK)
```

Integración, fuga y disparo LIF sobre el spoke. Fragmento de [Layer256.step](../../navi10_qn.py#L169); dependencias y contexto permanecen en su archivo.

```python
def step(self, stim: int, stim_on: bool, hop_on: bool = False) -> int:
    prev = self.spikes
    nxt = 0
    v = self.v
    stim &= 0xFF
    for i in range(Q8_N):
        cur = 0
        if stim_on and i == stim:
            cur += I_STIM
        if hop_on:
            if (i ^ stim).bit_count() == 1:
                cur += I_HOP
        for b in range(Q8_DIM):
            j = i ^ (1 << b)
            if (prev >> j) & 1:
                cur += W_EDGE
        pot = (v[i] * LEAK_NUM) // LEAK_DEN + cur
        if pot > 255:
            pot = 255
        thresh = (VTH - I_CODE) if ((self.code_mask >> i) & 1) else VTH
        if pot >= thresh:
            nxt |= 1 << i
            pot = 0
        v[i] = pot
    self.spikes = nxt
    return nxt
```

Redondeo simétrico de CREDIT-1. Fragmento de [trunc_div](../nexus0/qtable.py#L32); dependencias y contexto permanecen en su archivo.

```python
def trunc_div(x: int, shift: int = ALPHA_SHIFT) -> int:
    """x / 2**shift, truncated **toward zero**. Not Python's `>>`.

    `(-5) >> 2` is -2: the arithmetic shift floors, so a negative delta of
    -5 would pay -2 where +5 pays +1, and the remainder below would owe
    credit that was already spent. 5 -> 1, 3 -> 0, -3 -> 0, -5 -> -1.
    Integers only: no divmod on negatives, no float, no round().
    """
    n = abs(int(x)) >> int(shift)
    return -n if x < 0 else n
```

Autoridad final sobre las tres acciones originales. Fragmento de [gate](../nexus0/gate.py#L23); dependencias y contexto permanecen en su archivo.

```python
def gate(
    wsp: bytes,
    *,
    cam_hit: bool,
    extract_ok: bool,
    E: Tuple[int, int, int, int, int, int],
    proposed: int,
    inhibit: bool = False,
    threat: bool = False,
    n_actions: int = N_ACTIONS,
) -> Tuple[int, int, int]:
    """Return (decision, action, flags).

    Order from docs/05-NEXUS-0-SPEC.md §8.

    OPEN-1: `n_actions` is how many gears the world that asked has, and it
    defaults to the frozen three, so every existing caller folds `proposed`
    exactly as it always did (5 still comes out 2). A four-gear world has
    to say so, and if it did not, `open` would enter here as 3 and leave as
    0 — the environment would never see the verb, every ABRIR would be an
    approach, and the slice would be OBJ-1 wearing a fourth column.

    The rules below are unchanged. `open` is not a threat and not a wait,
    so it matches none of them and leaves through GATE_OK; an inhibited
    slot still blocks to WAIT, whatever was proposed.
    """
    del wsp, cam_hit  # reserved for later rules; keep signature stable
    a = int(proposed) % int(n_actions)
    u = int(E[4]) if len(E) > 4 else 0
    flags = 0

    if inhibit:
        return GATE_BLOCK, ACTION_WAIT, WSP_FLAG_VETO

    if (not extract_ok) and a == ACTION_APPROACH and threat:
        return GATE_MODIFY, ACTION_AVOID, WSP_FLAG_VETO

    if u >= U_SHORT and a == ACTION_WAIT and threat:
        return GATE_MODIFY, ACTION_AVOID, WSP_FLAG_VETO

    return GATE_OK, a, flags
```

Transición física y contabilidad WORLD-1. Fragmento de [transition](../echo4/world.py#L84); dependencias y contexto permanecen en su archivo.

```python
def transition(body: Body, action: int, rules: DockRules) -> Transition:
    """Pure transition. Reject malformed commands rather than folding modulo 3."""
    if not isinstance(body, Body) or not isinstance(rules, DockRules):
        raise ValueError("transition requires Body and DockRules")
    integer(action, 0, N_ACTIONS - 1, "action")
    if not body.alive:
        raise RuntimeError("terminal bodies cannot act")
    resource_in = used = spill = 0
    if action == ACTION_APPROACH:
        resource_in = rules.charge_input
        h = min(CAPACITY, body.h + resource_in)
        spill = body.h + resource_in - h
        temperature = min(CAPACITY, body.temperature + rules.charge_heat)
    elif action == ACTION_AVOID:
        used = min(body.h, rules.cooling_cost)
        h = body.h - used
        temperature = max(0, body.temperature - rules.cooling_drop)
    else:
        assert action == ACTION_WAIT
        used = min(body.h, rules.wait_cost)
        h = body.h - used
        temperature = min(CAPACITY, body.temperature + rules.wait_heat)
    return Transition(body, action, Body(h, temperature), resource_in, used, spill)
```

Eliminación de estados sin continuidad viable. Fragmento de [analyze](../echo4/viability.py#L105); dependencias y contexto permanecen en su archivo.

```python
def analyze(rules: DockRules = DockRules()) -> Viability:
    if not isinstance(rules, DockRules):
        raise ValueError("analyze requires DockRules")
    successors: list[tuple[int, ...]] = []
    predecessors: list[list[int]] = [[] for _ in range(STATE_COUNT)]
    degree: list[int] = []
    for index in range(STATE_COUNT):
        body = indexed_body(index)
        row = []
        for action in range(N_ACTIONS):
            step = transition(body, action, rules)
            if not step.balanced:
                raise RuntimeError("resource balance violated")
            nxt = state_index(step.after) if step.after.alive else -1
            row.append(nxt)
            if nxt >= 0:
                # Keep duplicate edges: degree also counts actions, not nodes.
                predecessors[nxt].append(index)
        successors.append(tuple(row))
        degree.append(sum(nxt >= 0 for nxt in row))

    pending = deque(i for i, count in enumerate(degree) if count == 0)
    kernel = [True] * STATE_COUNT
    finite_lifetime = [0] * STATE_COUNT
    while pending:
        index = pending.popleft()
        kernel[index] = False
        finite_lifetime[index] = max(
            1 if nxt < 0 else 1 + finite_lifetime[nxt]
            for nxt in successors[index])
        for parent in predecessors[index]:
            degree[parent] -= 1
            if degree[parent] == 0:
                pending.append(parent)
    return Viability(rules, tuple(successors), tuple(kernel), tuple(finite_lifetime))
```

Etiquetas posibles derivadas de hipótesis restantes. Fragmento de [possible_labels](../echo4/self_attribution.py#L127); dependencias y contexto permanecen en su archivo.

```python
def possible_labels(h_candidates, t_candidates):
    h_modes = {c[1] for c in h_candidates}
    t_modes = {(c[1], c[2] != 0) for c in t_candidates}
    indices = {(not (hc and tc)) + 2 * external for hc in h_modes for tc, external in t_modes}
    return tuple(LABELS[i] for i in sorted(indices))
```

Componentes conectados por BFS. Fragmento de [objects](../seed/dsl.py#L103); dependencias y contexto permanecen en su archivo.

```python
def objects(g, bg=0, diagonal=False):
    """Connected components of non-background cells (same colour): list of (colour, cells)."""
    h, w = len(g), len(g[0])
    seen, out = set(), []
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1)) + (((1, 1), (1, -1), (-1, 1), (-1, -1)) if diagonal else ())
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or g[y][x] == bg:
                continue
            c, cells, q = g[y][x], [], deque([(y, x)])
            seen.add((y, x))
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for dy, dx in steps:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx] == c:
                        seen.add((ny, nx))
                        q.append((ny, nx))
            out.append((c, cells))
    return out
```

Error de demostraciones usado por la búsqueda. Fragmento de [distance](../seed/learn.py#L25); dependencias y contexto permanecen en su archivo.

```python
def distance(state, targets):
    d = 0.0
    for g, t in zip(state, targets):
        if len(g) != len(t) or len(g[0]) != len(t[0]):
            d += 1.0
        else:
            d += sum(a != b for ra, rb in zip(g, t) for a, b in zip(ra, rb)) / (len(t) * len(t[0]))
    return d / len(targets)
```

Creación de conceptos con argumentos de color. Fragmento de [sleep_parametric](../seed/learn.py#L201); dependencias y contexto permanecen en su archivo.

```python
def sleep_parametric(library, verified, round_no, max_new=12, min_tasks=2, max_slots=2):
    """S2: sub-sequences with the same shape in >= min_tasks tasks but DIFFERENT colours become one
    concept with colour slots ("recolour X to Y" learned from recolour 1->2 and recolour 3->5)."""
    shapes, where, binds = Counter(), {}, {}
    for tid, prog in verified.items():
        steps = [p if isinstance(p, str) else tuple(p) for p in prog]
        seen = set()
        for n in (2, 3):                                       # one step is just a primitive with its colours
            for i in range(len(steps) - n + 1):
                sub = steps[i:i + n]
                if all(isinstance(x, str) or len(x) == 1 for x in sub):
                    continue                                   # no colours: the fixed concepts cover it
                shape, colours = _slotify(sub)
                key = json.dumps(shape)
                if key in seen or not 1 <= len(colours) <= max_slots:
                    continue
                seen.add(key)
                shapes[key] += 1
                where.setdefault(key, []).append(tid)
                binds.setdefault(key, set()).add(tuple(colours))
    known = {json.dumps(c["steps"]) for c in library.concepts.values()}
    added = []
    for key, n in sorted(shapes.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < min_tasks or len(binds[key]) < 2 or key in known or len(added) >= max_new:
            continue                                           # needs >= 2 different colourings
        shape = json.loads(key)
        cid = "k%03d" % (len(library.concepts) + 1)
        library.concepts[cid] = {"steps": shape, "slots": len(next(iter(binds[key]))),
                                 "tasks": sorted(where[key]), "round": round_no}
        added.append(cid)
    return added
```

Separación de respuestas privadas del test. Fragmento de [solver_input](../seed/refinement.py#L39); dependencias y contexto permanecen en su archivo.

```python
def solver_input(task):
    """Do not copy, inspect, serialize or pass on any test output."""
    if not task.get("train") or not task.get("test"):
        raise ValueError("demonstrations and test inputs required")
    if len(task["train"]) > 10 or len(task["test"]) > 10:
        raise ValueError("at most ten demonstrations and ten test inputs")
    return {"train": [{"input": grid(p["input"]), "output": grid(p["output"])} for p in task["train"]],
            "test": [{"input": grid(p["input"])} for p in task["test"]]}
```

Crítica medida de forma, celdas, histograma y objetos. Fragmento de [critique](../seed/refinement.py#L129); dependencias y contexto permanecen en su archivo.

```python
def critique(outputs, targets):
    """Measured discrepancies, never a verbal guess about hidden reasoning."""
    detail = []
    for got, want in zip(outputs, targets):
        same_shape = (len(got), len(got[0])) == (len(want), len(want[0]))
        pixels = sum(a != b for ra, rb in zip(got, want) for a, b in zip(ra, rb)) if same_shape else None
        hist = Counter(v for row in got for v in row)
        target_hist = Counter(v for row in want for v in row)
        detail.append({"shape_matches": same_shape, "wrong_cells": pixels,
                       "color_count_error": sum(abs(hist[c] - target_hist[c]) for c in range(10)),
                       "object_count_error": abs(len(dsl.objects(got)) - len(dsl.objects(want))),
                       "exact": got == want})
    return detail
```

Proyección de una asociación a ocho índices. Fragmento de [SparsePrimitiveGuide._indices](../seed/kenyon_capacity.py#L60); dependencias y contexto permanecen en su archivo.

```python
def _indices(self, feature, name):
    token = (feature + "\0" + name).encode("utf-8")
    digest = blake2b(token, digest_size=32, person=b"ECHO45-KENYON").digest()
    return tuple(int.from_bytes(digest[i:i+4], "little") % self.units for i in range(0, 32, 4))
```

Aprendizaje solo tras ejecutar todas las demostraciones. Fragmento de [SparsePrimitiveGuide.observe](../seed/kenyon_capacity.py#L65); dependencias y contexto permanecen en su archivo.

```python
def observe(self, task, program, library=None):
    """Learn only a program that replays every demonstration exactly."""
    library = library or Library()
    pairs = task.get("train", ())
    if not pairs or not program:
        raise ValueError("verified nonempty program required")
    for pair in pairs:
        result = dsl.G(pair["input"])
        for item in program:
            result = library.apply(result, item)
        if result != dsl.G(pair["output"]):
            raise ValueError("program does not fit every demonstration")
    labels = {Library.key(step) for item in program for step in library.expand(item)}
    labels = {name for name in labels if name in self.names}
    if not labels:
        raise ValueError("program has no recognized primitive")
    features = self.features(task)
    for name in labels:
        for feature in features:
            for index in self._indices(feature, name):
                self.weights[index] = min(255, self.weights[index] + 1)
    self.examples += 1
```

Guía de familias derivada de pesos. Fragmento de [SparsePrimitiveGuide.probs](../seed/kenyon_capacity.py#L88); dependencias y contexto permanecen en su archivo.

```python
def probs(self, task):
    """Return a ranking hint in the existing Library.guide format."""
    features = self.features(task)
    scores = {name: sum(self.weights[index] for feature in features
                        for index in self._indices(feature, name)) for name in self.names}
    peak = max(scores.values())
    if not peak:
        return {name: 0.05 for name in self.names}
    return {name: 0.05 + 0.55 * score / peak for name, score in scores.items()}
```

Conjunción de criterios del examen S6-B. Fragmento de [checks](../seed/s6_precise_exam.py#L58); dependencias y contexto permanecen en su archivo.

```python
def checks(totals, dev, audit_valid):
    echo, base = totals["echo"], totals["semilla"]
    return {"B1": echo["levels"] * 100 >= base["levels"] * 105 and echo["score"] >= base["score"],
            "B2": echo["levels"] > totals["fijo"]["levels"],
            "B3": echo["levels"] > totals["sinfiltro"]["levels"],
            "B4": all(dev["echo"][k] >= dev["semilla"][k] for k in ("levels", "score")),
            "B5": audit_valid}
```

Cadena concreta de diario ECHO-SEED. Fragmento de [_chain](../seed/sandbox.py#L35); dependencias y contexto permanecen en su archivo.

```python
def _chain(path, event):
    lines = path.read_text().splitlines() if path.exists() else []
    prev = json.loads(lines[-1])["hash"] if lines else "0" * 64
    body = dict(event, prev=prev)
    body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    with path.open("a") as f:
        f.write(json.dumps(body, sort_keys=True) + "\n")
```

Costes de navegación, escritura y consecuencias demoradas. Fragmento de [Echo.scores](../seed/village3_receipts.py#L37); dependencias y contexto permanecen en su archivo.

```python
def scores(self, context):
    nav = self.estimates(self.navigation[context])
    later = self.estimates(self.proof_returns[context])
    writing = self.value(self.writing)
    return [nav[int(verify)] + int(write) * writing + later[int(verify and write)]
            for verify, write in base.ACTIONS]
```

El inventario de implementación siguiente enumera los archivos Python del primer nivel de `nexus0/`, `echo4/`, `echo_arc/` y `seed/`. Cada nombre enlaza al código real. Las clases y funciones declaradas se incluyen como puntos de entrada para seguir submódulos, variantes, ejecutores y auditores. Las carpetas de soporte, herramientas, tests y artefactos se recorren desde sus contratos. Esta enumeración de software disponible no concede un verde a todas sus funciones.

| Archivo | Definiciones de módulo | Métodos públicos de clases |
|---|---|---|
| [nexus0/__init__.py](../nexus0/__init__.py) | Importaciones, constantes o superficie de paquete | — |
| [nexus0/attend.py](../nexus0/attend.py) | [attend](../nexus0/attend.py#L52), [reason_name](../nexus0/attend.py#L101) | — |
| [nexus0/bench.py](../nexus0/bench.py) | [encoder_report](../nexus0/bench.py#L22), [run](../nexus0/bench.py#L56), [report_name](../nexus0/bench.py#L122), [main](../nexus0/bench.py#L143) | — |
| [nexus0/board.py](../nexus0/board.py) | [has_cube](../nexus0/board.py#L108), [cube_side](../nexus0/board.py#L113), [read_records](../nexus0/board.py#L131), [normalise](../nexus0/board.py#L140), [cell_count](../nexus0/board.py#L153), [_esc](../nexus0/board.py#L164), [_payload](../nexus0/board.py#L174), [render_html](../nexus0/board.py#L648), [read_live](../nexus0/board.py#L831), [_from_param](../nexus0/board.py#L866), [make_handler](../nexus0/board.py#L881), [make_server](../nexus0/board.py#L934), [main](../nexus0/board.py#L945) | — |
| [nexus0/body.py](../nexus0/body.py) | [index_of](../nexus0/body.py#L106), [pose_of](../nexus0/body.py#L111), [pose_name](../nexus0/body.py#L117), [walls_of](../nexus0/body.py#L126), [on_grid](../nexus0/body.py#L132), [is_floor](../nexus0/body.py#L136), [bumps](../nexus0/body.py#L147), [_successors](../nexus0/body.py#L161), [reachable](../nexus0/body.py#L201), [BodyEnv](../nexus0/body.py#L207), [_slot](../nexus0/body.py#L267), [_cam_occupied](../nexus0/body.py#L271), [stepper](../nexus0/body.py#L275), [t_vs_stepper](../nexus0/body.py#L287), [approach_diff](../nexus0/body.py#L348), [_train_free](../nexus0/body.py#L358), [_train_swept](../nexus0/body.py#L373), [_stood_on](../nexus0/body.py#L392), [_greedy_probe](../nexus0/body.py#L402), [experiment](../nexus0/body.py#L425), [distances](../nexus0/body.py#L568), [poses_by_distance](../nexus0/body.py#L593), [shortest_path](../nexus0/body.py#L602), [credit_chain](../nexus0/body.py#L625), [_exam](../nexus0/body.py#L655), [credit_chain_remainder](../nexus0/body.py#L685), [walk](../nexus0/body.py#L708), [walk_green](../nexus0/body.py#L834), [green](../nexus0/body.py#L853), [main](../nexus0/body.py#L875), [main_walk](../nexus0/body.py#L891) | [BodyEnv.__init__](../nexus0/body.py#L210), [BodyEnv.reset](../nexus0/body.py#L222), [BodyEnv.cell](../nexus0/body.py#L228), [BodyEnv.teleport](../nexus0/body.py#L231), [BodyEnv.step](../nexus0/body.py#L247), [BodyEnv.reveal](../nexus0/body.py#L262) |
| [nexus0/body3d.py](../nexus0/body3d.py) | [episode_turns](../nexus0/body3d.py#L122), [index_of](../nexus0/body3d.py#L143), [pose_of](../nexus0/body3d.py#L149), [pose_name](../nexus0/body3d.py#L156), [floor_of](../nexus0/body3d.py#L165), [on_cube](../nexus0/body3d.py#L171), [is_floor](../nexus0/body3d.py#L175), [bumps](../nexus0/body3d.py#L186), [_successors](../nexus0/body3d.py#L200), [reachable](../nexus0/body3d.py#L235), [Body3DEnv](../nexus0/body3d.py#L241), [_slot](../nexus0/body3d.py#L301), [_cam_occupied](../nexus0/body3d.py#L305), [distances](../nexus0/body3d.py#L309), [poses_by_distance](../nexus0/body3d.py#L332), [shortest_path](../nexus0/body3d.py#L341), [stepper](../nexus0/body3d.py#L360), [t_vs_stepper](../nexus0/body3d.py#L368), [approach_diff](../nexus0/body3d.py#L419), [value_horizon](../nexus0/body3d.py#L429), [turn_poses](../nexus0/body3d.py#L451), [_exam](../nexus0/body3d.py#L486), [_corridor_use](../nexus0/body3d.py#L518), [_curriculum](../nexus0/body3d.py#L531), [_control_without_the_lever](../nexus0/body3d.py#L559), [experiment](../nexus0/body3d.py#L585), [green](../nexus0/body3d.py#L749), [thought_walk](../nexus0/body3d.py#L784), [live_walk](../nexus0/body3d.py#L832), [_arg](../nexus0/body3d.py#L884), [main](../nexus0/body3d.py#L888) | [Body3DEnv.__init__](../nexus0/body3d.py#L244), [Body3DEnv.reset](../nexus0/body3d.py#L256), [Body3DEnv.cell](../nexus0/body3d.py#L262), [Body3DEnv.teleport](../nexus0/body3d.py#L271), [Body3DEnv.step](../nexus0/body3d.py#L284), [Body3DEnv.reveal](../nexus0/body3d.py#L296) |
| [nexus0/capacity1.py](../nexus0/capacity1.py) | [_sha256_bytes](../nexus0/capacity1.py#L53), [_canonical](../nexus0/capacity1.py#L57), [_fraction](../nexus0/capacity1.py#L61), [_seed](../nexus0/capacity1.py#L69), [seeds](../nexus0/capacity1.py#L74), [seeds_hash](../nexus0/capacity1.py#L84), [_code_hash](../nexus0/capacity1.py#L88), [_config](../nexus0/capacity1.py#L92), [_config_hash](../nexus0/capacity1.py#L104), [Q8Entry](../nexus0/capacity1.py#L109), [q8_truth_table](../nexus0/capacity1.py#L116), [_entry](../nexus0/capacity1.py#L127), [signature_for](../nexus0/capacity1.py#L131), [_packet](../nexus0/capacity1.py#L147), [_family_packets](../nexus0/capacity1.py#L160), [_outcome](../nexus0/capacity1.py#L186), [_sample_families](../nexus0/capacity1.py#L191), [_permutation](../nexus0/capacity1.py#L217), [_memory_for_perception](../nexus0/capacity1.py#L229), [perception_seed](../nexus0/capacity1.py#L233), [_aggregate](../nexus0/capacity1.py#L279), [_compare](../nexus0/capacity1.py#L294), [TemporalHead](../nexus0/capacity1.py#L315), [_sequence_signature](../nexus0/capacity1.py#L360), [_temporal_pair](../nexus0/capacity1.py#L367), [temporal_seed](../nexus0/capacity1.py#L378), [_temporal_aggregate](../nexus0/capacity1.py#L415), [_current_only](../nexus0/capacity1.py#L427), [_oracle](../nexus0/capacity1.py#L443), [_select_adaptive](../nexus0/capacity1.py#L451), [_integrity](../nexus0/capacity1.py#L465), [_measure_resources](../nexus0/capacity1.py#L485), [_meets_bottleneck](../nexus0/capacity1.py#L528), [_green_science](../nexus0/capacity1.py#L538), [scientific_experiment](../nexus0/capacity1.py#L577), [experiment](../nexus0/capacity1.py#L628), [green](../nexus0/capacity1.py#L647), [main](../nexus0/capacity1.py#L666) | [TemporalHead.__init__](../nexus0/capacity1.py#L318), [TemporalHead.step](../nexus0/capacity1.py#L329), [TemporalHead.signature](../nexus0/capacity1.py#L347) |
| [nexus0/constants.py](../nexus0/constants.py) | Importaciones, constantes o superficie de paquete | — |
| [nexus0/corridor.py](../nexus0/corridor.py) | [CorridorEnv](../nexus0/corridor.py#L67), [_slot](../nexus0/corridor.py#L106), [_misses_on](../nexus0/corridor.py#L110), [experiment](../nexus0/corridor.py#L120), [main](../nexus0/corridor.py#L241) | [CorridorEnv.__init__](../nexus0/corridor.py#L70), [CorridorEnv.reset](../nexus0/corridor.py#L82), [CorridorEnv.cell](../nexus0/corridor.py#L86), [CorridorEnv.teleport](../nexus0/corridor.py#L89), [CorridorEnv.step](../nexus0/corridor.py#L93), [CorridorEnv.reveal](../nexus0/corridor.py#L101) |
| [nexus0/cortex.py](../nexus0/cortex.py) | [_timeout_s](../nexus0/cortex.py#L37), [propose](../nexus0/cortex.py#L56), [parse_reply](../nexus0/cortex.py#L71), [complete](../nexus0/cortex.py#L110) | — |
| [nexus0/cortex_turn.py](../nexus0/cortex_turn.py) | [build](../nexus0/cortex_turn.py#L23), [to_line](../nexus0/cortex_turn.py#L51) | — |
| [nexus0/demo.py](../nexus0/demo.py) | [_last_record](../nexus0/demo.py#L35), [_paint](../nexus0/demo.py#L43), [live](../nexus0/demo.py#L50), [replay](../nexus0/demo.py#L79), [main](../nexus0/demo.py#L86) | — |
| [nexus0/echo2.py](../nexus0/echo2.py) | [new_agent](../nexus0/echo2.py#L28), [food_probe](../nexus0/echo2.py#L33), [survival_arm](../nexus0/echo2.py#L55), [experiment](../nexus0/echo2.py#L87), [green](../nexus0/echo2.py#L99), [main](../nexus0/echo2.py#L154) | — |
| [nexus0/encoder.py](../nexus0/encoder.py) | [atom_name](../nexus0/encoder.py#L50), [compact](../nexus0/encoder.py#L55), [_fold_text](../nexus0/encoder.py#L67), [_load_bank](../nexus0/encoder.py#L71), [_atoms](../nexus0/encoder.py#L78), [encode_semantic](../nexus0/encoder.py#L87), [encode_unknown](../nexus0/encoder.py#L104), [encode](../nexus0/encoder.py#L120), [encode_source](../nexus0/encoder.py#L131), [encode_fnv](../nexus0/encoder.py#L140), [rel_of](../nexus0/encoder.py#L145), [src_of](../nexus0/encoder.py#L149), [dst_of](../nexus0/encoder.py#L153), [encode_ask](../nexus0/encoder.py#L180), [encode_cell](../nexus0/encoder.py#L199) | — |
| [nexus0/env.py](../nexus0/env.py) | [Cell](../nexus0/env.py#L56), [_reward](../nexus0/env.py#L89), [RingEnv](../nexus0/env.py#L107) | [Cell.threat](../nexus0/env.py#L75), [Cell.novelty](../nexus0/env.py#L79), [Cell.extract](../nexus0/env.py#L83), [RingEnv.__init__](../nexus0/env.py#L108), [RingEnv.reset](../nexus0/env.py#L118), [RingEnv.cell](../nexus0/env.py#L129), [RingEnv.step](../nexus0/env.py#L132), [RingEnv.reveal](../nexus0/env.py#L143), [RingEnv.teleport](../nexus0/env.py#L160), [RingEnv.move_threat](../nexus0/env.py#L164) |
| [nexus0/escalate.py](../nexus0/escalate.py) | [level](../nexus0/escalate.py#L47), [level_name](../nexus0/escalate.py#L70) | — |
| [nexus0/flight1s_v4_close.py](../nexus0/flight1s_v4_close.py) | [log_state](../nexus0/flight1s_v4_close.py#L27), [rebuild](../nexus0/flight1s_v4_close.py#L38), [complete_world_contrast](../nexus0/flight1s_v4_close.py#L69), [closure](../nexus0/flight1s_v4_close.py#L84), [close](../nexus0/flight1s_v4_close.py#L125), [audit](../nexus0/flight1s_v4_close.py#L135) | — |
| [nexus0/flight1s_v5_close.py](../nexus0/flight1s_v5_close.py) | [log_state](../nexus0/flight1s_v5_close.py#L23), [rebuild](../nexus0/flight1s_v5_close.py#L34), [groups](../nexus0/flight1s_v5_close.py#L65), [closure](../nexus0/flight1s_v5_close.py#L87), [close](../nexus0/flight1s_v5_close.py#L141), [audit](../nexus0/flight1s_v5_close.py#L149) | — |
| [nexus0/food1.py](../nexus0/food1.py) | [FoodEnv](../nexus0/food1.py#L16) | [FoodEnv.__init__](../nexus0/food1.py#L17), [FoodEnv.reset](../nexus0/food1.py#L23), [FoodEnv.delivers](../nexus0/food1.py#L34), [FoodEnv.step](../nexus0/food1.py#L37) |
| [nexus0/gate.py](../nexus0/gate.py) | [gate](../nexus0/gate.py#L23) | — |
| [nexus0/gen1.py](../nexus0/gen1.py) | [new_agent](../nexus0/gen1.py#L32), [spawn_child](../nexus0/gen1.py#L43), [phase_schedule](../nexus0/gen1.py#L48), [_memory_fingerprint](../nexus0/gen1.py#L53), [_is_success](../nexus0/gen1.py#L96), [episodes_to_criterion](../nexus0/gen1.py#L105), [_summarize](../nexus0/gen1.py#L114), [_disable_q_learning](../nexus0/gen1.py#L131), [run_arm](../nexus0/gen1.py#L138), [_candidate_rank](../nexus0/gen1.py#L206), [select_parent](../nexus0/gen1.py#L212), [_median](../nexus0/gen1.py#L229), [experiment](../nexus0/gen1.py#L236), [_valid_arm](../nexus0/gen1.py#L306), [green](../nexus0/gen1.py#L342), [main](../nexus0/gen1.py#L466) | — |
| [nexus0/gen1b.py](../nexus0/gen1b.py) | [ForageEnv](../nexus0/gen1b.py#L37), [phases_for](../nexus0/gen1b.py#L57), [new_agent](../nexus0/gen1b.py#L62), [spawn_child](../nexus0/gen1b.py#L75), [_disable_q](../nexus0/gen1b.py#L80), [frozen_exam](../nexus0/gen1b.py#L87), [episodes_to_criterion](../nexus0/gen1b.py#L145), [_summary](../nexus0/gen1b.py#L153), [run_arm](../nexus0/gen1b.py#L164), [_rank](../nexus0/gen1b.py#L223), [select_parent](../nexus0/gen1b.py#L228), [_median](../nexus0/gen1b.py#L247), [experiment](../nexus0/gen1b.py#L252), [_valid_arm](../nexus0/gen1b.py#L317), [green](../nexus0/gen1b.py#L354), [main](../nexus0/gen1b.py#L459) | [ForageEnv.__init__](../nexus0/gen1b.py#L40), [ForageEnv.reset](../nexus0/gen1b.py#L49) |
| [nexus0/gen1c.py](../nexus0/gen1c.py) | [CalibrationEnv](../nexus0/gen1c.py#L32), [phases_for](../nexus0/gen1c.py#L84), [new_agent](../nexus0/gen1c.py#L89), [spawn_child](../nexus0/gen1c.py#L95), [_disable_q](../nexus0/gen1c.py#L99), [criterion](../nexus0/gen1c.py#L106), [_summary](../nexus0/gen1c.py#L113), [run_arm](../nexus0/gen1c.py#L121), [_rank](../nexus0/gen1c.py#L162), [select_parent](../nexus0/gen1c.py#L166), [_median](../nexus0/gen1c.py#L184), [experiment](../nexus0/gen1c.py#L189), [_valid_arm](../nexus0/gen1c.py#L236), [green](../nexus0/gen1c.py#L259), [main](../nexus0/gen1c.py#L344) | [CalibrationEnv.__init__](../nexus0/gen1c.py#L35), [CalibrationEnv.best_action](../nexus0/gen1c.py#L49), [CalibrationEnv.reset](../nexus0/gen1c.py#L52), [CalibrationEnv.cell](../nexus0/gen1c.py#L56), [CalibrationEnv.step_vital](../nexus0/gen1c.py#L59), [CalibrationEnv.step](../nexus0/gen1c.py#L73), [CalibrationEnv.teleport](../nexus0/gen1c.py#L77), [CalibrationEnv.reveal](../nexus0/gen1c.py#L80) |
| [nexus0/gen1d.py](../nexus0/gen1d.py) | [derived_pairs](../nexus0/gen1d.py#L34), [pairs_hash](../nexus0/gen1d.py#L43), [_mix64](../nexus0/gen1d.py#L52), [noisy](../nexus0/gen1d.py#L59), [CalibrationEnv](../nexus0/gen1d.py#L65), [phases_for](../nexus0/gen1d.py#L115), [new_agent](../nexus0/gen1d.py#L120), [spawn_child](../nexus0/gen1d.py#L126), [_disable_q](../nexus0/gen1d.py#L130), [criterion](../nexus0/gen1d.py#L137), [_summary](../nexus0/gen1d.py#L144), [run_arm](../nexus0/gen1d.py#L155), [_rank](../nexus0/gen1d.py#L205), [select_parent](../nexus0/gen1d.py#L209), [_median](../nexus0/gen1d.py#L228), [_sign_test](../nexus0/gen1d.py#L233), [experiment](../nexus0/gen1d.py#L241), [_valid_arm](../nexus0/gen1d.py#L296), [green](../nexus0/gen1d.py#L327), [main](../nexus0/gen1d.py#L428) | [CalibrationEnv.__init__](../nexus0/gen1d.py#L68), [CalibrationEnv.best_action](../nexus0/gen1d.py#L82), [CalibrationEnv.reset](../nexus0/gen1d.py#L85), [CalibrationEnv.cell](../nexus0/gen1d.py#L89), [CalibrationEnv.step_vital](../nexus0/gen1d.py#L92), [CalibrationEnv.step](../nexus0/gen1d.py#L104), [CalibrationEnv.teleport](../nexus0/gen1d.py#L108), [CalibrationEnv.reveal](../nexus0/gen1d.py#L111) |
| [nexus0/gen1e.py](../nexus0/gen1e.py) | [derived_pairs](../nexus0/gen1e.py#L34), [pairs_hash](../nexus0/gen1e.py#L43), [_mix64](../nexus0/gen1e.py#L52), [noisy](../nexus0/gen1e.py#L59), [CalibrationEnv](../nexus0/gen1e.py#L65), [phases_for](../nexus0/gen1e.py#L115), [new_agent](../nexus0/gen1e.py#L120), [spawn_child](../nexus0/gen1e.py#L126), [_disable_q](../nexus0/gen1e.py#L130), [criterion](../nexus0/gen1e.py#L137), [_summary](../nexus0/gen1e.py#L144), [run_arm](../nexus0/gen1e.py#L155), [_rank](../nexus0/gen1e.py#L205), [select_parent](../nexus0/gen1e.py#L209), [_median](../nexus0/gen1e.py#L228), [_sign_test](../nexus0/gen1e.py#L233), [experiment](../nexus0/gen1e.py#L241), [_valid_arm](../nexus0/gen1e.py#L296), [green](../nexus0/gen1e.py#L327), [main](../nexus0/gen1e.py#L432) | [CalibrationEnv.__init__](../nexus0/gen1e.py#L68), [CalibrationEnv.best_action](../nexus0/gen1e.py#L82), [CalibrationEnv.reset](../nexus0/gen1e.py#L85), [CalibrationEnv.cell](../nexus0/gen1e.py#L89), [CalibrationEnv.step_vital](../nexus0/gen1e.py#L92), [CalibrationEnv.step](../nexus0/gen1e.py#L104), [CalibrationEnv.teleport](../nexus0/gen1e.py#L108), [CalibrationEnv.reveal](../nexus0/gen1e.py#L111) |
| [nexus0/gen1f.py](../nexus0/gen1f.py) | [derived_pairs](../nexus0/gen1f.py#L36), [pairs_hash](../nexus0/gen1f.py#L45), [_mix64](../nexus0/gen1f.py#L54), [noisy](../nexus0/gen1f.py#L61), [CalibrationEnv](../nexus0/gen1f.py#L68), [phases_for](../nexus0/gen1f.py#L118), [new_agent](../nexus0/gen1f.py#L123), [spawn_child](../nexus0/gen1f.py#L129), [_disable_q](../nexus0/gen1f.py#L133), [criterion](../nexus0/gen1f.py#L140), [_summary](../nexus0/gen1f.py#L147), [run_arm](../nexus0/gen1f.py#L158), [_rank](../nexus0/gen1f.py#L208), [select_parent](../nexus0/gen1f.py#L212), [_median](../nexus0/gen1f.py#L231), [_sign_test](../nexus0/gen1f.py#L236), [experiment](../nexus0/gen1f.py#L244), [_valid_arm](../nexus0/gen1f.py#L303), [green](../nexus0/gen1f.py#L334), [main](../nexus0/gen1f.py#L443) | [CalibrationEnv.__init__](../nexus0/gen1f.py#L71), [CalibrationEnv.best_action](../nexus0/gen1f.py#L85), [CalibrationEnv.reset](../nexus0/gen1f.py#L88), [CalibrationEnv.cell](../nexus0/gen1f.py#L92), [CalibrationEnv.step_vital](../nexus0/gen1f.py#L95), [CalibrationEnv.step](../nexus0/gen1f.py#L107), [CalibrationEnv.teleport](../nexus0/gen1f.py#L111), [CalibrationEnv.reveal](../nexus0/gen1f.py#L114) |
| [nexus0/graph.py](../nexus0/graph.py) | [_successors](../nexus0/graph.py#L98), [GraphEnv](../nexus0/graph.py#L125), [_slot](../nexus0/graph.py#L166), [_unseen](../nexus0/graph.py#L170), [_cam_occupied](../nexus0/graph.py#L180), [_q_approach_profile](../nexus0/graph.py#L184), [_t_against](../nexus0/graph.py#L193), [_greedy_profile](../nexus0/graph.py#L222), [_walk_greedy](../nexus0/graph.py#L230), [experiment](../nexus0/graph.py#L247), [green](../nexus0/graph.py#L372), [main](../nexus0/graph.py#L398) | [GraphEnv.__init__](../nexus0/graph.py#L128), [GraphEnv.reset](../nexus0/graph.py#L141), [GraphEnv.cell](../nexus0/graph.py#L146), [GraphEnv.teleport](../nexus0/graph.py#L149), [GraphEnv.step](../nexus0/graph.py#L153), [GraphEnv.reveal](../nexus0/graph.py#L161) |
| [nexus0/heat1.py](../nexus0/heat1.py) | [derived_seeds](../nexus0/heat1.py#L35), [seeds_hash](../nexus0/heat1.py#L44), [_fingerprint](../nexus0/heat1.py#L49), [_memories](../nexus0/heat1.py#L53), [thermal_band](../nexus0/heat1.py#L58), [ThermalDockEnv](../nexus0/heat1.py#L64), [new_agent](../nexus0/heat1.py#L118), [_median2](../nexus0/heat1.py#L125), [frozen_probe](../nexus0/heat1.py#L132), [run_arm](../nexus0/heat1.py#L153), [experiment](../nexus0/heat1.py#L215), [_replay_life](../nexus0/heat1.py#L236), [_valid_arm](../nexus0/heat1.py#L264), [green](../nexus0/heat1.py#L299), [main](../nexus0/heat1.py#L347) | [ThermalDockEnv.__init__](../nexus0/heat1.py#L67), [ThermalDockEnv.reset](../nexus0/heat1.py#L72), [ThermalDockEnv.cell](../nexus0/heat1.py#L77), [ThermalDockEnv.step_homeostatic](../nexus0/heat1.py#L80), [ThermalDockEnv.step](../nexus0/heat1.py#L108), [ThermalDockEnv.teleport](../nexus0/heat1.py#L111), [ThermalDockEnv.reveal](../nexus0/heat1.py#L114) |
| [nexus0/heat1b.py](../nexus0/heat1b.py) | [derived_seeds](../nexus0/heat1b.py#L37), [seeds_hash](../nexus0/heat1b.py#L46), [_fingerprint](../nexus0/heat1b.py#L51), [_memories](../nexus0/heat1b.py#L55), [thermal_band](../nexus0/heat1b.py#L60), [ThermalDockEnv](../nexus0/heat1b.py#L66), [new_agent](../nexus0/heat1b.py#L120), [_median2](../nexus0/heat1b.py#L128), [frozen_probe](../nexus0/heat1b.py#L135), [run_arm](../nexus0/heat1b.py#L156), [_headline](../nexus0/heat1b.py#L224), [experiment](../nexus0/heat1b.py#L251), [_replay_life](../nexus0/heat1b.py#L273), [_valid_arm](../nexus0/heat1b.py#L301), [green](../nexus0/heat1b.py#L342), [main](../nexus0/heat1b.py#L406) | [ThermalDockEnv.__init__](../nexus0/heat1b.py#L69), [ThermalDockEnv.reset](../nexus0/heat1b.py#L74), [ThermalDockEnv.cell](../nexus0/heat1b.py#L79), [ThermalDockEnv.step_homeostatic](../nexus0/heat1b.py#L82), [ThermalDockEnv.step](../nexus0/heat1b.py#L110), [ThermalDockEnv.teleport](../nexus0/heat1b.py#L113), [ThermalDockEnv.reveal](../nexus0/heat1b.py#L116) |
| [nexus0/lex.py](../nexus0/lex.py) | [Rule](../nexus0/lex.py#L42), [L](../nexus0/lex.py#L54), [_fold](../nexus0/lex.py#L318), [count](../nexus0/lex.py#L326), [apply](../nexus0/lex.py#L331), [to_wsp](../nexus0/lex.py#L342), [apply_wsp](../nexus0/lex.py#L362) | — |
| [nexus0/loop.py](../nexus0/loop.py) | [Agent](../nexus0/loop.py#L54) | [Agent.__init__](../nexus0/loop.py#L55), [Agent.clear_context](../nexus0/loop.py#L218), [Agent.observation](../nexus0/loop.py#L227), [Agent.respawn](../nexus0/loop.py#L236), [Agent.turn](../nexus0/loop.py#L654), [Agent.run](../nexus0/loop.py#L888), [Agent.greedy_on](../nexus0/loop.py#L903), [Agent.walk_greedy](../nexus0/loop.py#L911), [Agent.threat_slots](../nexus0/loop.py#L926) |
| [nexus0/neural_viz.py](../nexus0/neural_viz.py) | [_bar](../nexus0/neural_viz.py#L33), [_spoke](../nexus0/neural_viz.py#L39), [_raster](../nexus0/neural_viz.py#L48), [_cortex_line](../nexus0/neural_viz.py#L61), [render](../nexus0/neural_viz.py#L74), [live](../nexus0/neural_viz.py#L123), [main](../nexus0/neural_viz.py#L157) | — |
| [nexus0/neural_viz_gui.py](../nexus0/neural_viz_gui.py) | [TaskError](../nexus0/neural_viz_gui.py#L55), [_symbol](../nexus0/neural_viz_gui.py#L59), [_materialise](../nexus0/neural_viz_gui.py#L71), [TaskSpec](../nexus0/neural_viz_gui.py#L93), [discover_tasks](../nexus0/neural_viz_gui.py#L149), [_occupied](../nexus0/neural_viz_gui.py#L159), [_lif512](../nexus0/neural_viz_gui.py#L164), [_tail_json](../nexus0/neural_viz_gui.py#L173), [RuntimeEngine](../nexus0/neural_viz_gui.py#L189), [GraphNode](../nexus0/neural_viz_gui.py#L402), [NetworkCanvas](../nexus0/neural_viz_gui.py#L409), [DroneWorldView](../nexus0/neural_viz_gui.py#L580), [EchoVizApp](../nexus0/neural_viz_gui.py#L874), [main](../nexus0/neural_viz_gui.py#L1275) | [TaskSpec.load](../nexus0/neural_viz_gui.py#L106), [TaskSpec.make_agent](../nexus0/neural_viz_gui.py#L137), [TaskSpec.make_child](../nexus0/neural_viz_gui.py#L143), [RuntimeEngine.__init__](../nexus0/neural_viz_gui.py#L192), [RuntimeEngine.start](../nexus0/neural_viz_gui.py#L225), [RuntimeEngine.stop](../nexus0/neural_viz_gui.py#L232), [RuntimeEngine.set_paused](../nexus0/neural_viz_gui.py#L235), [RuntimeEngine.step_once](../nexus0/neural_viz_gui.py#L241), [RuntimeEngine.set_rate](../nexus0/neural_viz_gui.py#L245), [RuntimeEngine.status](../nexus0/neural_viz_gui.py#L268), [NetworkCanvas.__init__](../nexus0/neural_viz_gui.py#L418), [NetworkCanvas.redraw](../nexus0/neural_viz_gui.py#L503), [NetworkCanvas.activity](../nexus0/neural_viz_gui.py#L534), [DroneWorldView.__init__](../nexus0/neural_viz_gui.py#L588), [DroneWorldView.update](../nexus0/neural_viz_gui.py#L811), [DroneWorldView.reset](../nexus0/neural_viz_gui.py#L857), [EchoVizApp.__init__](../nexus0/neural_viz_gui.py#L875), [EchoVizApp.choose_task](../nexus0/neural_viz_gui.py#L1114), [EchoVizApp.open_task](../nexus0/neural_viz_gui.py#L1119), [EchoVizApp.load_task](../nexus0/neural_viz_gui.py#L1125), [EchoVizApp.toggle_pause](../nexus0/neural_viz_gui.py#L1138), [EchoVizApp.step_once](../nexus0/neural_viz_gui.py#L1145), [EchoVizApp.change_rate](../nexus0/neural_viz_gui.py#L1151), [EchoVizApp.poll](../nexus0/neural_viz_gui.py#L1157), [EchoVizApp.show](../nexus0/neural_viz_gui.py#L1235), [EchoVizApp.close](../nexus0/neural_viz_gui.py#L1265), [EchoVizApp.run](../nexus0/neural_viz_gui.py#L1270) |
| [nexus0/obj1.py](../nexus0/obj1.py) | [voxel_of](../nexus0/obj1.py#L106), [Obj1Env](../nexus0/obj1.py#L112), [valid_states](../nexus0/obj1.py#L266), [successor](../nexus0/obj1.py#L284), [_flood](../nexus0/obj1.py#L311), [distances](../nexus0/obj1.py#L327), [states_by_distance](../nexus0/obj1.py#L351), [shortest_collect](../nexus0/obj1.py#L363), [dest_distances](../nexus0/obj1.py#L376), [cost_to_dest_alone](../nexus0/obj1.py#L402), [item_on_cheapest_dest_path](../nexus0/obj1.py#L410), [placements](../nexus0/obj1.py#L428), [packet_of](../nexus0/obj1.py#L471), [packets](../nexus0/obj1.py#L475), [ext_of](../nexus0/obj1.py#L481), [_ext_is_zero](../nexus0/obj1.py#L485), [seq_is_the_local_pose](../nexus0/obj1.py#L493), [coupled_is_env_not_wsp](../nexus0/obj1.py#L501), [packet_ceiling_holds](../nexus0/obj1.py#L521), [no_pose_is_ever_a_goal](../nexus0/obj1.py#L528), [index_max](../nexus0/obj1.py#L545), [probe_the_table](../nexus0/obj1.py#L557), [_slot](../nexus0/obj1.py#L604), [_cam_occupied](../nexus0/obj1.py#L608), [values_an_empty_table](../nexus0/obj1.py#L612), [_fresh](../nexus0/obj1.py#L629), [school](../nexus0/obj1.py#L634), [exam](../nexus0/obj1.py#L669), [_control_and_mutant](../nexus0/obj1.py#L720), [experiment](../nexus0/obj1.py#L739), [green](../nexus0/obj1.py#L858), [main](../nexus0/obj1.py#L891) | [Obj1Env.__init__](../nexus0/obj1.py#L120), [Obj1Env.reset](../nexus0/obj1.py#L158), [Obj1Env.cell](../nexus0/obj1.py#L168), [Obj1Env.teleport](../nexus0/obj1.py#L173), [Obj1Env.delivers](../nexus0/obj1.py#L196), [Obj1Env.step](../nexus0/obj1.py#L217), [Obj1Env.reveal](../nexus0/obj1.py#L256) |
| [nexus0/open1.py](../nexus0/open1.py) | [episode_turns](../nexus0/open1.py#L99), [Open1Env](../nexus0/open1.py#L118), [fresh_env](../nexus0/open1.py#L246), [valid_states](../nexus0/open1.py#L262), [successor](../nexus0/open1.py#L281), [distances](../nexus0/open1.py#L319), [states_by_distance](../nexus0/open1.py#L334), [shortest_collect](../nexus0/open1.py#L346), [opens_needed](../nexus0/open1.py#L352), [ext_of](../nexus0/open1.py#L373), [_ext_is_zero](../nexus0/open1.py#L380), [seq_is_the_local_pose](../nexus0/open1.py#L385), [packets](../nexus0/open1.py#L390), [packet_ceiling_holds](../nexus0/open1.py#L399), [the_verb_is_not_in_the_packet](../nexus0/open1.py#L404), [_cam_occupied](../nexus0/open1.py#L419), [_fresh](../nexus0/open1.py#L423), [probe_the_jar](../nexus0/open1.py#L428), [stuck_on_the_jar](../nexus0/open1.py#L469), [best_q_in_the_shut_room](../nexus0/open1.py#L497), [school](../nexus0/open1.py#L513), [exam](../nexus0/open1.py#L556), [_control](../nexus0/open1.py#L596), [_mutant](../nexus0/open1.py#L615), [experiment](../nexus0/open1.py#L627), [green](../nexus0/open1.py#L729), [main](../nexus0/open1.py#L769) | [Open1Env.__init__](../nexus0/open1.py#L127), [Open1Env.reset](../nexus0/open1.py#L152), [Open1Env.teleport](../nexus0/open1.py#L156), [Open1Env.opens](../nexus0/open1.py#L178), [Open1Env.step](../nexus0/open1.py#L189) |
| [nexus0/oracle.py](../nexus0/oracle.py) | [accept](../nexus0/oracle.py#L33), [Sensor](../nexus0/oracle.py#L50), [FileOracle](../nexus0/oracle.py#L67), [from_path](../nexus0/oracle.py#L88) | [Sensor.__init__](../nexus0/oracle.py#L60), [Sensor.reply](../nexus0/oracle.py#L63), [FileOracle.__init__](../nexus0/oracle.py#L77), [FileOracle.reply](../nexus0/oracle.py#L80) |
| [nexus0/pattern.py](../nexus0/pattern.py) | [context_key](../nexus0/pattern.py#L60), [PatternMemory](../nexus0/pattern.py#L72), [ContextPredictor](../nexus0/pattern.py#L188) | [PatternMemory.__init__](../nexus0/pattern.py#L75), [PatternMemory.observe](../nexus0/pattern.py#L111), [PatternMemory.mature](../nexus0/pattern.py#L143), [PatternMemory.predict](../nexus0/pattern.py#L149), [PatternMemory.hits](../nexus0/pattern.py#L163), [PatternMemory.entries](../nexus0/pattern.py#L167), [PatternMemory.mature_counts](../nexus0/pattern.py#L173), [PatternMemory.snapshot_hash](../nexus0/pattern.py#L181), [ContextPredictor.__init__](../nexus0/pattern.py#L197), [ContextPredictor.predict](../nexus0/pattern.py#L201) |
| [nexus0/pattern0.py](../nexus0/pattern0.py) | [successors_of](../nexus0/pattern0.py#L89), [balanced_successors](../nexus0/pattern0.py#L102), [PatternEnv](../nexus0/pattern0.py#L118), [_slot](../nexus0/pattern0.py#L169), [walk](../nexus0/pattern0.py#L181), [to_slots](../nexus0/pattern0.py#L192), [Watched](../nexus0/pattern0.py#L197), [world_hash](../nexus0/pattern0.py#L212), [successor_counts](../nexus0/pattern0.py#L219), [train](../nexus0/pattern0.py#L233), [exam](../nexus0/pattern0.py#L264), [_clock_table](../nexus0/pattern0.py#L339), [train_without_context](../nexus0/pattern0.py#L356), [capacity_probe](../nexus0/pattern0.py#L374), [_root_attribute](../nexus0/pattern0.py#L420), [_foreign_write](../nexus0/pattern0.py#L433), [isolation_findings](../nexus0/pattern0.py#L446), [battery_state](../nexus0/pattern0.py#L560), [mutants](../nexus0/pattern0.py#L602), [_shifted_scoring](../nexus0/pattern0.py#L723), [_report_shape](../nexus0/pattern0.py#L748), [experiment](../nexus0/pattern0.py#L784), [_predict_signature](../nexus0/pattern0.py#L894), [green](../nexus0/pattern0.py#L906), [main](../nexus0/pattern0.py#L962) | [PatternEnv.__init__](../nexus0/pattern0.py#L126), [PatternEnv.teleport](../nexus0/pattern0.py#L138), [PatternEnv.cell](../nexus0/pattern0.py#L144), [PatternEnv.step](../nexus0/pattern0.py#L147), [Watched.__init__](../nexus0/pattern0.py#L200), [Watched.observe](../nexus0/pattern0.py#L204), [Watched.predict](../nexus0/pattern0.py#L208) |
| [nexus0/pattern1.py](../nexus0/pattern1.py) | [hamming16](../nexus0/pattern1.py#L34), [InvariantPatternMemory](../nexus0/pattern1.py#L38), [signature_of](../nexus0/pattern1.py#L191), [_rows](../nexus0/pattern1.py#L198), [experiment](../nexus0/pattern1.py#L223), [green](../nexus0/pattern1.py#L294), [main](../nexus0/pattern1.py#L355) | [InvariantPatternMemory.__init__](../nexus0/pattern1.py#L46), [InvariantPatternMemory.observe](../nexus0/pattern1.py#L115), [InvariantPatternMemory.predict](../nexus0/pattern1.py#L145), [InvariantPatternMemory.snapshot_hash](../nexus0/pattern1.py#L157) |
| [nexus0/plan.py](../nexus0/plan.py) | [_discount](../nexus0/plan.py#L27), [_score](../nexus0/plan.py#L31), [_value](../nexus0/plan.py#L55), [scores](../nexus0/plan.py#L61), [best](../nexus0/plan.py#L67) | — |
| [nexus0/qtable.py](../nexus0/qtable.py) | [trunc_div](../nexus0/qtable.py#L32), [QTable](../nexus0/qtable.py#L44) | [QTable.__init__](../nexus0/qtable.py#L45), [QTable.reset_traces](../nexus0/qtable.py#L93), [QTable.get](../nexus0/qtable.py#L101), [QTable.set](../nexus0/qtable.py#L104), [QTable.row](../nexus0/qtable.py#L107), [QTable.max_q](../nexus0/qtable.py#L110), [QTable.best](../nexus0/qtable.py#L114), [QTable.margin](../nexus0/qtable.py#L123), [QTable.flat](../nexus0/qtable.py#L133), [QTable.is_explore](../nexus0/qtable.py#L145), [QTable.exploration_period](../nexus0/qtable.py#L160), [QTable.select](../nexus0/qtable.py#L170), [QTable.update](../nexus0/qtable.py#L215), [QTable.snapshot](../nexus0/qtable.py#L271), [QTable.load_rows](../nexus0/qtable.py#L274) |
| [nexus0/qwen_sign.py](../nexus0/qwen_sign.py) | [_cmd_qwen](../nexus0/qwen_sign.py#L47), [_probe_text](../nexus0/qwen_sign.py#L52), [_fast](../nexus0/qwen_sign.py#L83), [experiment](../nexus0/qwen_sign.py#L98), [green](../nexus0/qwen_sign.py#L184), [main](../nexus0/qwen_sign.py#L204) | — |
| [nexus0/qwen_signc.py](../nexus0/qwen_signc.py) | [cortex_cmd](../nexus0/qwen_signc.py#L84), [_sha256](../nexus0/qwen_signc.py#L98), [action_grammar](../nexus0/qwen_signc.py#L103), [_row](../nexus0/qwen_signc.py#L123), [experiment](../nexus0/qwen_signc.py#L197), [green](../nexus0/qwen_signc.py#L278), [main](../nexus0/qwen_signc.py#L311) | — |
| [nexus0/room1.py](../nexus0/room1.py) | [Room1Env](../nexus0/room1.py#L81), [room_env](../nexus0/room1.py#L101), [packet_of](../nexus0/room1.py#L107), [packets_in](../nexus0/room1.py#L113), [_by_packet](../nexus0/room1.py#L120), [dynamic_alias](../nexus0/room1.py#L127), [ext_of](../nexus0/room1.py#L162), [domain_is_zero](../nexus0/room1.py#L166), [style_is_zero](../nexus0/room1.py#L171), [seq_is_the_local_pose](../nexus0/room1.py#L176), [packet_ceiling_holds](../nexus0/room1.py#L182), [_slot](../nexus0/room1.py#L191), [_cam_occupied](../nexus0/room1.py#L195), [t_against](../nexus0/room1.py#L199), [school](../nexus0/room1.py#L221), [exam](../nexus0/room1.py#L248), [_fresh](../nexus0/room1.py#L274), [experiment](../nexus0/room1.py#L281), [green](../nexus0/room1.py#L416), [main](../nexus0/room1.py#L455) | [Room1Env.__init__](../nexus0/room1.py#L91) |
| [nexus0/self1.py](../nexus0/self1.py) | [slipped_successors](../nexus0/self1.py#L76), [pushes_into_stone](../nexus0/self1.py#L109), [Self1Env](../nexus0/self1.py#L118), [SelfModel](../nexus0/self1.py#L176), [_unknown_next](../nexus0/self1.py#L334), [_slot](../nexus0/self1.py#L341), [_cam_occupied](../nexus0/self1.py#L345), [intact_successors](../nexus0/self1.py#L349), [t_world_preserved](../nexus0/self1.py#L354), [distances_for](../nexus0/self1.py#L377), [reachable_in](../nexus0/self1.py#L396), [observe](../nexus0/self1.py#L405), [school](../nexus0/self1.py#L417), [exam](../nexus0/self1.py#L447), [probe_offset](../nexus0/self1.py#L470), [probe_holding](../nexus0/self1.py#L490), [run_arm](../nexus0/self1.py#L521), [experiment](../nexus0/self1.py#L567), [green](../nexus0/self1.py#L679), [main](../nexus0/self1.py#L710) | [Self1Env.__init__](../nexus0/self1.py#L122), [Self1Env.reset](../nexus0/self1.py#L135), [Self1Env.cell](../nexus0/self1.py#L141), [Self1Env.teleport](../nexus0/self1.py#L144), [Self1Env.step](../nexus0/self1.py#L157), [Self1Env.reveal](../nexus0/self1.py#L169), [SelfModel.__init__](../nexus0/self1.py#L185), [SelfModel.hypothesis](../nexus0/self1.py#L215), [SelfModel.observe_step](../nexus0/self1.py#L274), [SelfModel.settle](../nexus0/self1.py#L319) |
| [nexus0/shifts.py](../nexus0/shifts.py) | [fingerprint](../nexus0/shifts.py#L22), [memories](../nexus0/shifts.py#L27), [run_lives](../nexus0/shifts.py#L31), [experiment](../nexus0/shifts.py#L57), [valid_arm](../nexus0/shifts.py#L90), [green](../nexus0/shifts.py#L117), [main](../nexus0/shifts.py#L156) | — |
| [nexus0/sign.py](../nexus0/sign.py) | [SignEnv](../nexus0/sign.py#L96), [cortex_cmd](../nexus0/sign.py#L151), [cortex_env](../nexus0/sign.py#L158), [_probe](../nexus0/sign.py#L174), [ring_wakes](../nexus0/sign.py#L209), [experiment](../nexus0/sign.py#L219), [green](../nexus0/sign.py#L287), [main](../nexus0/sign.py#L306) | [SignEnv.__init__](../nexus0/sign.py#L99), [SignEnv.reset](../nexus0/sign.py#L118), [SignEnv.cell](../nexus0/sign.py#L123), [SignEnv.teleport](../nexus0/sign.py#L128), [SignEnv.step](../nexus0/sign.py#L132), [SignEnv.reveal](../nexus0/sign.py#L146) |
| [nexus0/signc.py](../nexus0/signc.py) | [SignCEnv](../nexus0/signc.py#L121), [cortex_cmd](../nexus0/signc.py#L162), [prose_cmd](../nexus0/signc.py#L168), [_line](../nexus0/signc.py#L177), [canonical_bench](../nexus0/signc.py#L200), [_packet_is_blind_to_the_sign](../nexus0/signc.py#L236), [_slot](../nexus0/signc.py#L250), [_train](../nexus0/signc.py#L254), [arm](../nexus0/signc.py#L276), [placements](../nexus0/signc.py#L424), [experiment](../nexus0/signc.py#L458), [_default_flag](../nexus0/signc.py#L625), [green](../nexus0/signc.py#L631), [_canon_is_green](../nexus0/signc.py#L695), [main](../nexus0/signc.py#L720) | [SignCEnv.__init__](../nexus0/signc.py#L132), [SignCEnv.reset](../nexus0/signc.py#L147), [SignCEnv.cell](../nexus0/signc.py#L151) |
| [nexus0/sleep2.py](../nexus0/sleep2.py) | [packet_of](../nexus0/sleep2.py#L51), [template_of](../nexus0/sleep2.py#L75), [seq_of](../nexus0/sleep2.py#L83), [with_seq](../nexus0/sleep2.py#L89), [successor_state](../nexus0/sleep2.py#L98), [ConsolidatedRules](../nexus0/sleep2.py#L107), [memory_hash](../nexus0/sleep2.py#L172), [consolidate](../nexus0/sleep2.py#L236), [build_day](../nexus0/sleep2.py#L318), [_exam](../nexus0/sleep2.py#L342), [experiment](../nexus0/sleep2.py#L378), [green](../nexus0/sleep2.py#L435), [main](../nexus0/sleep2.py#L505) | [ConsolidatedRules.__init__](../nexus0/sleep2.py#L110), [ConsolidatedRules.add](../nexus0/sleep2.py#L124), [ConsolidatedRules.compressed_knowledge](../nexus0/sleep2.py#L141), [ConsolidatedRules.predict](../nexus0/sleep2.py#L145), [ConsolidatedRules.snapshot_hash](../nexus0/sleep2.py#L158) |
| [nexus0/stream1.py](../nexus0/stream1.py) | [ExternalFrame](../nexus0/stream1.py#L41), [packet_of](../nexus0/stream1.py#L55), [successor](../nexus0/stream1.py#L60), [external_stream](../nexus0/stream1.py#L72), [StreamProcessor](../nexus0/stream1.py#L91), [_packet_contract](../nexus0/stream1.py#L158), [_run](../nexus0/stream1.py#L170), [experiment](../nexus0/stream1.py#L190), [green](../nexus0/stream1.py#L214), [main](../nexus0/stream1.py#L259) | [StreamProcessor.__init__](../nexus0/stream1.py#L98), [StreamProcessor.ingest](../nexus0/stream1.py#L111), [StreamProcessor.ingest_all](../nexus0/stream1.py#L129), [StreamProcessor.dynamic_alias](../nexus0/stream1.py#L133), [StreamProcessor.snapshot_hash](../nexus0/stream1.py#L145) |
| [nexus0/talk.py](../nexus0/talk.py) | [BadRecord](../nexus0/talk.py#L111), [_int](../nexus0/talk.py#L115), [_opt_int](../nexus0/talk.py#L122), [validate](../nexus0/talk.py#L128), [_pose](../nexus0/talk.py#L223), [_reward](../nexus0/talk.py#L234), [render](../nexus0/talk.py#L241), [read_records](../nexus0/talk.py#L274), [translate](../nexus0/talk.py#L295), [main](../nexus0/talk.py#L301) | — |
| [nexus0/talk1.py](../nexus0/talk1.py) | [want_pose](../nexus0/talk1.py#L71), [parse](../nexus0/talk1.py#L98), [audit](../nexus0/talk1.py#L118), [audit_file](../nexus0/talk1.py#L233), [same_order](../nexus0/talk1.py#L243), [_is_std_stream_write](../nexus0/talk1.py#L268), [causal_findings](../nexus0/talk1.py#L286), [_sha256](../nexus0/talk1.py#L338), [_base](../nexus0/talk1.py#L343), [synthetic_matrix](../nexus0/talk1.py#L355), [real_signc_pair](../nexus0/talk1.py#L405), [real_open_turn](../nexus0/talk1.py#L427), [matrix](../nexus0/talk1.py#L460), [_swap](../nexus0/talk1.py#L465), [mutants](../nexus0/talk1.py#L471), [_ring_diary](../nexus0/talk1.py#L600), [experiment](../nexus0/talk1.py#L609), [battery_state](../nexus0/talk1.py#L751), [green](../nexus0/talk1.py#L806), [main](../nexus0/talk1.py#L866) | — |
| [nexus0/thought.py](../nexus0/thought.py) | [_int_or_none](../nexus0/thought.py#L48), [build](../nexus0/thought.py#L52), [to_line](../nexus0/thought.py#L117) | — |
| [nexus0/types.py](../nexus0/types.py) | [clip_i8](../nexus0/types.py#L20), [clip_u8](../nexus0/types.py#L28), [State](../nexus0/types.py#L37), [StepResult](../nexus0/types.py#L47), [Metrics](../nexus0/types.py#L62), [action_name](../nexus0/types.py#L153), [gate_name](../nexus0/types.py#L157), [default_e](../nexus0/types.py#L161) | [Metrics.mean_ham](../nexus0/types.py#L104), [Metrics.prediction_accuracy](../nexus0/types.py#L107), [Metrics.persist_accuracy](../nexus0/types.py#L110), [Metrics.ring_accuracy](../nexus0/types.py#L113), [Metrics.as_dict](../nexus0/types.py#L116) |
| [nexus0/view.py](../nexus0/view.py) | [initial_layout](../nexus0/view.py#L42), [_bar](../nexus0/view.py#L47), [render](../nexus0/view.py#L55), [read_records](../nexus0/view.py#L94), [follow](../nexus0/view.py#L103), [main](../nexus0/view.py#L117) | — |
| [nexus0/vita1.py](../nexus0/vita1.py) | [VitalEnv](../nexus0/vita1.py#L11) | [VitalEnv.__init__](../nexus0/vita1.py#L12), [VitalEnv.reset](../nexus0/vita1.py#L21), [VitalEnv.step_vital](../nexus0/vita1.py#L24) |
| [nexus0/world.py](../nexus0/world.py) | [World](../nexus0/world.py#L29) | [World.__init__](../nexus0/world.py#L30), [World.predict](../nexus0/world.py#L57), [World.observe](../nexus0/world.py#L63), [World.inverse](../nexus0/world.py#L110), [World.inv_size](../nexus0/world.py#L138), [World.error](../nexus0/world.py#L142), [World.known](../nexus0/world.py#L149), [World.conf](../nexus0/world.py#L152), [World.pair](../nexus0/world.py#L183) |
| [nexus0/xfer1.py](../nexus0/xfer1.py) | [approach_table](../nexus0/xfer1.py#L120), [riff_table](../nexus0/xfer1.py#L126), [physics_differences](../nexus0/xfer1.py#L131), [ParkEnv](../nexus0/xfer1.py#L146), [slot_of](../nexus0/xfer1.py#L221), [new_agent](../nexus0/xfer1.py#L227), [_walk](../nexus0/xfer1.py#L235), [aged_agent](../nexus0/xfer1.py#L270), [school](../nexus0/xfer1.py#L288), [cross_into](../nexus0/xfer1.py#L303), [is_same_body](../nexus0/xfer1.py#L315), [identities](../nexus0/xfer1.py#L325), [protocol_signature](../nexus0/xfer1.py#L330), [signatures_match](../nexus0/xfer1.py#L356), [arm_metrics](../nexus0/xfer1.py#L362), [t_rows_against](../nexus0/xfer1.py#L373), [riff_points](../nexus0/xfer1.py#L401), [probe](../nexus0/xfer1.py#L418), [world_name_branches](../nexus0/xfer1.py#L451), [core_sources](../nexus0/xfer1.py#L475), [resolve_points](../nexus0/xfer1.py#L481), [probe_resolved](../nexus0/xfer1.py#L494), [known_slots](../nexus0/xfer1.py#L512), [ablation](../nexus0/xfer1.py#L517), [channel_audit](../nexus0/xfer1.py#L537), [core_world_name_branches](../nexus0/xfer1.py#L647), [border](../nexus0/xfer1.py#L652), [battery_state](../nexus0/xfer1.py#L776), [mutants](../nexus0/xfer1.py#L814), [_report_shape](../nexus0/xfer1.py#L1187), [experiment](../nexus0/xfer1.py#L1254), [_is_int](../nexus0/xfer1.py#L1485), [signature_evidence](../nexus0/xfer1.py#L1490), [walk_evidence](../nexus0/xfer1.py#L1521), [_probe_ok](../nexus0/xfer1.py#L1562), [pattern_evidence](../nexus0/xfer1.py#L1584), [channel_evidence](../nexus0/xfer1.py#L1636), [evidence](../nexus0/xfer1.py#L1673), [green](../nexus0/xfer1.py#L1763), [_green](../nexus0/xfer1.py#L1780), [main](../nexus0/xfer1.py#L1884) | [ParkEnv.__init__](../nexus0/xfer1.py#L154), [ParkEnv.reset](../nexus0/xfer1.py#L178), [ParkEnv.cell](../nexus0/xfer1.py#L183), [ParkEnv.teleport](../nexus0/xfer1.py#L186), [ParkEnv.step](../nexus0/xfer1.py#L204), [ParkEnv.reveal](../nexus0/xfer1.py#L216) |
| [echo4/__init__.py](../echo4/__init__.py) | Importaciones, constantes o superficie de paquete | — |
| [echo4/__main__.py](../echo4/__main__.py) | [main](../echo4/__main__.py#L9) | — |
| [echo4/adapter.py](../echo4/adapter.py) | [DockEnv](../echo4/adapter.py#L9), [new_agent](../echo4/adapter.py#L34) | [DockEnv.cell](../echo4/adapter.py#L13), [DockEnv.step_homeostatic](../echo4/adapter.py#L16), [DockEnv.step](../echo4/adapter.py#L24), [DockEnv.teleport](../echo4/adapter.py#L27), [DockEnv.reveal](../echo4/adapter.py#L30) |
| [echo4/arc2_bench.py](../echo4/arc2_bench.py) | [load_split](../echo4/arc2_bench.py#L90), [task_names](../echo4/arc2_bench.py#L97), [load_task](../echo4/arc2_bench.py#L105), [grid_str](../echo4/arc2_bench.py#L111), [task_prompt](../echo4/arc2_bench.py#L115), [check_code](../echo4/arc2_bench.py#L127), [_limits](../echo4/arc2_bench.py#L144), [execute](../echo4/arc2_bench.py#L150), [extract_code](../echo4/arc2_bench.py#L162), [parse_json_answer](../echo4/arc2_bench.py#L170), [diff_report](../echo4/arc2_bench.py#L181), [score_task](../echo4/arc2_bench.py#L196), [arm_L](../echo4/arc2_bench.py#L202), [rows_fallback](../echo4/arc2_bench.py#L218), [arm_LECHO](../echo4/arc2_bench.py#L229), [arm_C](../echo4/arc2_bench.py#L250), [_bg](../echo4/arc2_bench.py#L275), [_rot](../echo4/arc2_bench.py#L280), [_crop](../echo4/arc2_bench.py#L284), [_scale](../echo4/arc2_bench.py#L291), [_down](../echo4/arc2_bench.py#L295), [_tile](../echo4/arc2_bench.py#L301), [_mirror_tile](../echo4/arc2_bench.py#L305), [_colormap](../echo4/arc2_bench.py#L319), [solo_solve](../echo4/arc2_bench.py#L331), [usage_cost](../echo4/arc2_bench.py#L361), [run](../echo4/arc2_bench.py#L365), [solo](../echo4/arc2_bench.py#L400), [summary](../echo4/arc2_bench.py#L413), [audit](../echo4/arc2_bench.py#L429), [main](../echo4/arc2_bench.py#L455) | — |
| [echo4/arc3_agent.py](../echo4/arc3_agent.py) | [fingerprint](../echo4/arc3_agent.py#L46), [frame_hash](../echo4/arc3_agent.py#L54), [objects](../echo4/arc3_agent.py#L58), [Arc3Echo](../echo4/arc3_agent.py#L89), [Arc3EchoV2](../echo4/arc3_agent.py#L187), [RandomAgent](../echo4/arc3_agent.py#L288), [_act](../echo4/arc3_agent.py#L307), [play](../echo4/arc3_agent.py#L316), [score](../echo4/arc3_agent.py#L377), [games_for](../echo4/arc3_agent.py#L389), [arcade](../echo4/arc3_agent.py#L396), [main](../echo4/arc3_agent.py#L407) | [Arc3Echo.__init__](../echo4/arc3_agent.py#L90), [Arc3Echo.actions_for](../echo4/arc3_agent.py#L112), [Arc3Echo.observe_state](../echo4/arc3_agent.py#L127), [Arc3Echo.choose](../echo4/arc3_agent.py#L154), [Arc3Echo.actions_for_state_fallback](../echo4/arc3_agent.py#L170), [Arc3Echo.learn](../echo4/arc3_agent.py#L174), [Arc3EchoV2.__init__](../echo4/arc3_agent.py#L199), [Arc3EchoV2.actions_for](../echo4/arc3_agent.py#L205), [Arc3EchoV2.observe_state](../echo4/arc3_agent.py#L237), [Arc3EchoV2.choose](../echo4/arc3_agent.py#L246), [Arc3EchoV2.learn](../echo4/arc3_agent.py#L274), [RandomAgent.__init__](../echo4/arc3_agent.py#L290), [RandomAgent.observe_state](../echo4/arc3_agent.py#L294), [RandomAgent.choose](../echo4/arc3_agent.py#L297), [RandomAgent.learn](../echo4/arc3_agent.py#L301) |
| [echo4/arc3_llm.py](../echo4/arc3_llm.py) | [grid_text](../echo4/arc3_llm.py#L56), [object_list](../echo4/arc3_llm.py#L60), [moved_objects](../echo4/arc3_llm.py#L67), [kind_name](../echo4/arc3_llm.py#L85), [parse](../echo4/arc3_llm.py#L89), [Game](../echo4/arc3_llm.py#L118), [_direction](../echo4/arc3_llm.py#L276), [_path](../echo4/arc3_llm.py#L284), [play](../echo4/arc3_llm.py#L302), [main](../echo4/arc3_llm.py#L334) | [Game.__init__](../echo4/arc3_llm.py#L121), [Game.sid](../echo4/arc3_llm.py#L143), [Game.step](../echo4/arc3_llm.py#L146), [Game.prompt](../echo4/arc3_llm.py#L199), [Game.memory](../echo4/arc3_llm.py#L213), [Game.run_orders](../echo4/arc3_llm.py#L239) |
| [echo4/arc3_llm2.py](../echo4/arc3_llm2.py) | [ask_opus](../echo4/arc3_llm2.py#L66), [ask_backend](../echo4/arc3_llm2.py#L96), [parse_expect](../echo4/arc3_llm2.py#L106), [expect_text](../echo4/arc3_llm2.py#L115), [Game2](../echo4/arc3_llm2.py#L119), [prompt](../echo4/arc3_llm2.py#L167), [play](../echo4/arc3_llm2.py#L185), [_log](../echo4/arc3_llm2.py#L241), [build_manual](../echo4/arc3_llm2.py#L248), [main](../echo4/arc3_llm2.py#L262) | [Game2.__init__](../echo4/arc3_llm2.py#L120), [Game2.step](../echo4/arc3_llm2.py#L126), [Game2.verdict](../echo4/arc3_llm2.py#L142), [Game2.lab](../echo4/arc3_llm2.py#L151) |
| [echo4/arc3_view.py](../echo4/arc3_view.py) | [render](../echo4/arc3_view.py#L27), [main](../echo4/arc3_view.py#L43) | — |
| [echo4/audit.py](../echo4/audit.py) | [observed](../echo4/audit.py#L14), [digest](../echo4/audit.py#L19), [observation_audit](../echo4/audit.py#L25), [world_audit](../echo4/audit.py#L73) | — |
| [echo4/bench1.py](../echo4/bench1.py) | [canonical](../echo4/bench1.py#L65), [sha](../echo4/bench1.py#L69), [norm](../echo4/bench1.py#L75), [content_tokens](../echo4/bench1.py#L82), [is_idk](../echo4/bench1.py#L86), [grade_short](../echo4/bench1.py#L92), [grade_letter](../echo4/bench1.py#L110), [grade_number](../echo4/bench1.py#L119), [load_items](../echo4/bench1.py#L136), [_wiki_get](../echo4/bench1.py#L163), [sentences](../echo4/bench1.py#L177), [search_queries](../echo4/bench1.py#L189), [retrieve](../echo4/bench1.py#L200), [retrieval_for](../echo4/bench1.py#L224), [EchoVerifier](../echo4/bench1.py#L236), [api_key](../echo4/bench1.py#L274), [ask](../echo4/bench1.py#L284), [context_block](../echo4/bench1.py#L323), [jobs_for](../echo4/bench1.py#L327), [credits_remaining](../echo4/bench1.py#L346), [spent_micro_usd](../echo4/bench1.py#L353), [run_model](../echo4/bench1.py#L357), [score](../echo4/bench1.py#L378), [rates](../echo4/bench1.py#L427), [charts](../echo4/bench1.py#L440), [sources](../echo4/bench1.py#L490), [report_for](../echo4/bench1.py#L495), [main](../echo4/bench1.py#L511) | [EchoVerifier.__init__](../echo4/bench1.py#L241), [EchoVerifier.verify](../echo4/bench1.py#L254) |
| [echo4/boundary.py](../echo4/boundary.py) | [integer](../echo4/boundary.py#L25), [code](../echo4/boundary.py#L30), [Trial](../echo4/boundary.py#L36), [Pair](../echo4/boundary.py#L47), [validate](../echo4/boundary.py#L55), [Estimate](../echo4/boundary.py#L100), [BoundaryMap](../echo4/boundary.py#L108), [public_record](../echo4/boundary.py#L210) | [BoundaryMap.__init__](../echo4/boundary.py#L115), [BoundaryMap.observe](../echo4/boundary.py#L126), [BoundaryMap.estimate](../echo4/boundary.py#L161), [BoundaryMap.freeze](../echo4/boundary.py#L194), [BoundaryMap.model_hash](../echo4/boundary.py#L197), [BoundaryMap.resources](../echo4/boundary.py#L203) |
| [echo4/boundary_agent.py](../echo4/boundary_agent.py) | [BoundaryAgent](../echo4/boundary_agent.py#L6) | [BoundaryAgent.__init__](../echo4/boundary_agent.py#L7), [BoundaryAgent.observe_intervention](../echo4/boundary_agent.py#L11), [BoundaryAgent.influence_estimate](../echo4/boundary_agent.py#L16) |
| [echo4/boundary_bench.py](../echo4/boundary_bench.py) | [canonical](../echo4/boundary_bench.py#L33), [sources](../echo4/boundary_bench.py#L37), [masks](../echo4/boundary_bench.py#L41), [metrics](../echo4/boundary_bench.py#L45), [stage_acceptance](../echo4/boundary_bench.py#L51), [run_stage](../echo4/boundary_bench.py#L68), [_ScheduledProbe](../echo4/boundary_bench.py#L142), [native_probe](../echo4/boundary_bench.py#L150), [run_campaign](../echo4/boundary_bench.py#L191), [campaign](../echo4/boundary_bench.py#L206), [audit](../echo4/boundary_bench.py#L230), [main](../echo4/boundary_bench.py#L266) | — |
| [echo4/boundary_world.py](../echo4/boundary_world.py) | [packet](../echo4/boundary_world.py#L22), [Experiment](../echo4/boundary_world.py#L28), [experiment](../echo4/boundary_world.py#L39), [run_pair](../echo4/boundary_world.py#L53), [judge](../echo4/boundary_world.py#L100), [coincidence](../echo4/boundary_world.py#L124) | — |
| [echo4/code_exam.py](../echo4/code_exam.py) | [digest](../echo4/code_exam.py#L28), [server_command](../echo4/code_exam.py#L32), [server_env](../echo4/code_exam.py#L36), [Client](../echo4/code_exam.py#L42), [grade](../echo4/code_exam.py#L93), [exam](../echo4/code_exam.py#L99), [main](../echo4/code_exam.py#L254) | [Client.__init__](../echo4/code_exam.py#L45), [Client.request](../echo4/code_exam.py#L53), [Client.notify](../echo4/code_exam.py#L71), [Client.call](../echo4/code_exam.py#L75), [Client.close](../echo4/code_exam.py#L81) |
| [echo4/code_gate.py](../echo4/code_gate.py) | [Verdict](../echo4/code_gate.py#L77), [_project_root](../echo4/code_gate.py#L99), [_inside](../echo4/code_gate.py#L103), [_path_args](../echo4/code_gate.py#L125), [_substitutions](../echo4/code_gate.py#L134), [_blank_substitutions](../echo4/code_gate.py#L157), [_simple_commands](../echo4/code_gate.py#L182), [_strip_wrappers](../echo4/code_gate.py#L210), [_check_git](../echo4/code_gate.py#L235), [_check_simple](../echo4/code_gate.py#L250), [_load_policy](../echo4/code_gate.py#L305), [check_action](../echo4/code_gate.py#L317), [_analyse](../echo4/code_gate.py#L347), [_tokens](../echo4/code_gate.py#L362) | [Verdict.__init__](../echo4/code_gate.py#L78), [Verdict.block](../echo4/code_gate.py#L86), [Verdict.modify](../echo4/code_gate.py#L90), [Verdict.as_dict](../echo4/code_gate.py#L95) |
| [echo4/code_mcp.py](../echo4/code_mcp.py) | [_schema](../echo4/code_mcp.py#L22), [Server](../echo4/code_mcp.py#L50), [serve](../echo4/code_mcp.py#L112), [main](../echo4/code_mcp.py#L131) | [Server.__init__](../echo4/code_mcp.py#L51), [Server.call](../echo4/code_mcp.py#L55), [Server.handle](../echo4/code_mcp.py#L78) |
| [echo4/code_memory.py](../echo4/code_memory.py) | [canonical](../echo4/code_memory.py#L36), [sha](../echo4/code_memory.py#L40), [event_key](../echo4/code_memory.py#L44), [symbols_of](../echo4/code_memory.py#L50), [CodeMemory](../echo4/code_memory.py#L69) | [CodeMemory.__init__](../echo4/code_memory.py#L70), [CodeMemory.fingerprint](../echo4/code_memory.py#L116), [CodeMemory.tree_sha](../echo4/code_memory.py#L135), [CodeMemory.observe_file](../echo4/code_memory.py#L150), [CodeMemory.checks](../echo4/code_memory.py#L163), [CodeMemory.run_check](../echo4/code_memory.py#L173), [CodeMemory.note](../echo4/code_memory.py#L192), [CodeMemory.command_in_testimony](../echo4/code_memory.py#L198), [CodeMemory.verify_claim](../echo4/code_memory.py#L213), [CodeMemory.recall](../echo4/code_memory.py#L251), [CodeMemory.receipts](../echo4/code_memory.py#L257) |
| [echo4/continuity.py](../echo4/continuity.py) | [canonical](../echo4/continuity.py#L84), [source_hashes](../echo4/continuity.py#L89), [_attributes](../echo4/continuity.py#L93), [_encode](../echo4/continuity.py#L99), [_decode](../echo4/continuity.py#L147), [_matrix](../echo4/continuity.py#L213), [validate](../echo4/continuity.py#L223), [ContinuityRun](../echo4/continuity.py#L325), [_unique_pairs](../echo4/continuity.py#L385), [_no_float](../echo4/continuity.py#L394), [loads](../echo4/continuity.py#L398), [load](../echo4/continuity.py#L423) | [ContinuityRun.__init__](../echo4/continuity.py#L328), [ContinuityRun.step](../echo4/continuity.py#L333), [ContinuityRun.snapshot](../echo4/continuity.py#L351), [ContinuityRun.dumps](../echo4/continuity.py#L358), [ContinuityRun.state_hash](../echo4/continuity.py#L364), [ContinuityRun.save](../echo4/continuity.py#L367) |
| [echo4/continuity_active.py](../echo4/continuity_active.py) | [source_hashes](../echo4/continuity_active.py#L60), [_receipt](../echo4/continuity_active.py#L65), [_core_profile](../echo4/continuity_active.py#L89), [_belief](../echo4/continuity_active.py#L119), [ActiveRun](../echo4/continuity_active.py#L159), [validate](../echo4/continuity_active.py#L324), [loads](../echo4/continuity_active.py#L409), [load](../echo4/continuity_active.py#L437) | [ActiveRun.__init__](../echo4/continuity_active.py#L170), [ActiveRun.choose_probe](../echo4/continuity_active.py#L202), [ActiveRun.queue_receipt](../echo4/continuity_active.py#L214), [ActiveRun.consume_receipt](../echo4/continuity_active.py#L221), [ActiveRun.cancel](../echo4/continuity_active.py#L233), [ActiveRun.start_recovery](../echo4/continuity_active.py#L248), [ActiveRun.arm_exposure](../echo4/continuity_active.py#L255), [ActiveRun.arm_reuse](../echo4/continuity_active.py#L261), [ActiveRun.step](../echo4/continuity_active.py#L267), [ActiveRun.diagnostic_clock](../echo4/continuity_active.py#L297), [ActiveRun.snapshot](../echo4/continuity_active.py#L307), [ActiveRun.dumps](../echo4/continuity_active.py#L317) |
| [echo4/continuity_active_bench.py](../echo4/continuity_active_bench.py) | [new_run](../echo4/continuity_active_bench.py#L29), [physical_receipt](../echo4/continuity_active_bench.py#L40), [finish_diagnosis](../echo4/continuity_active_bench.py#L48), [prepared](../echo4/continuity_active_bench.py#L57), [trajectory](../echo4/continuity_active_bench.py#L112), [resumed](../echo4/continuity_active_bench.py#L170), [sources](../echo4/continuity_active_bench.py#L177), [row](../echo4/continuity_active_bench.py#L184), [campaign](../echo4/continuity_active_bench.py#L192), [verify](../echo4/continuity_active_bench.py#L213), [main](../echo4/continuity_active_bench.py#L236) | — |
| [echo4/continuity_bench.py](../echo4/continuity_bench.py) | [prepared](../echo4/continuity_bench.py#L26), [trajectory](../echo4/continuity_bench.py#L43), [resumed](../echo4/continuity_bench.py#L70), [bench_sources](../echo4/continuity_bench.py#L80), [campaign](../echo4/continuity_bench.py#L87), [verify](../echo4/continuity_bench.py#L117), [main](../echo4/continuity_bench.py#L150) | — |
| [echo4/continuity_final_audit.py](../echo4/continuity_final_audit.py) | [file_hash](../echo4/continuity_final_audit.py#L25), [read_json](../echo4/continuity_final_audit.py#L33), [sources](../echo4/continuity_final_audit.py#L38), [parents](../echo4/continuity_final_audit.py#L46), [resumed](../echo4/continuity_final_audit.py#L64), [evaluate](../echo4/continuity_final_audit.py#L71), [stage_checks](../echo4/continuity_final_audit.py#L91), [stage](../echo4/continuity_final_audit.py#L111), [campaign](../echo4/continuity_final_audit.py#L132), [record](../echo4/continuity_final_audit.py#L158), [verify](../echo4/continuity_final_audit.py#L178), [main](../echo4/continuity_final_audit.py#L222) | — |
| [echo4/continuity_final_cases.py](../echo4/continuity_final_cases.py) | [sha](../echo4/continuity_final_cases.py#L36), [kind](../echo4/continuity_final_cases.py#L40), [module](../echo4/continuity_final_cases.py#L44), [clone](../echo4/continuity_final_cases.py#L48), [prepared](../echo4/continuity_final_cases.py#L53), [trajectory](../echo4/continuity_final_cases.py#L143), [physical](../echo4/continuity_final_cases.py#L150), [controls](../echo4/continuity_final_cases.py#L154), [mutant_suite](../echo4/continuity_final_cases.py#L209) | — |
| [echo4/continuity_graph.py](../echo4/continuity_graph.py) | [GraphCodec](../echo4/continuity_graph.py#L11) | [GraphCodec.__init__](../echo4/continuity_graph.py#L12), [GraphCodec.encode](../echo4/continuity_graph.py#L18), [GraphCodec.decode](../echo4/continuity_graph.py#L67) |
| [echo4/continuity_lineage.py](../echo4/continuity_lineage.py) | [digest](../echo4/continuity_lineage.py#L36), [source_hashes](../echo4/continuity_lineage.py#L40), [_label](../echo4/continuity_lineage.py#L45), [_hash](../echo4/continuity_lineage.py#L50), [_identity](../echo4/continuity_lineage.py#L55), [memory_hash](../echo4/continuity_lineage.py#L65), [_branch](../echo4/continuity_lineage.py#L71), [_seal](../echo4/continuity_lineage.py#L75), [_chain](../echo4/continuity_lineage.py#L80), [_fresh_body](../echo4/continuity_lineage.py#L137), [LineageRun](../echo4/continuity_lineage.py#L157), [_birth](../echo4/continuity_lineage.py#L326), [_quarantined](../echo4/continuity_lineage.py#L330), [_calibrate](../echo4/continuity_lineage.py#L354), [_commissioned](../echo4/continuity_lineage.py#L365), [loads](../echo4/continuity_lineage.py#L409), [load](../echo4/continuity_lineage.py#L440) | [LineageRun.__init__](../echo4/continuity_lineage.py#L161), [LineageRun.import_active](../echo4/continuity_lineage.py#L165), [LineageRun.agent](../echo4/continuity_lineage.py#L183), [LineageRun.identity](../echo4/continuity_lineage.py#L187), [LineageRun.scope](../echo4/continuity_lineage.py#L191), [LineageRun.choose_probe](../echo4/continuity_lineage.py#L203), [LineageRun.queue_receipt](../echo4/continuity_lineage.py#L206), [LineageRun.consume_receipt](../echo4/continuity_lineage.py#L210), [LineageRun.cancel](../echo4/continuity_lineage.py#L213), [LineageRun.start_recovery](../echo4/continuity_lineage.py#L216), [LineageRun.arm_reuse](../echo4/continuity_lineage.py#L220), [LineageRun.arm_exposure](../echo4/continuity_lineage.py#L224), [LineageRun.step](../echo4/continuity_lineage.py#L228), [LineageRun.fork](../echo4/continuity_lineage.py#L243), [LineageRun.allocate_body](../echo4/continuity_lineage.py#L259), [LineageRun.commission](../echo4/continuity_lineage.py#L282), [LineageRun.snapshot](../echo4/continuity_lineage.py#L302), [LineageRun.dumps](../echo4/continuity_lineage.py#L319) |
| [echo4/continuity_lineage_bench.py](../echo4/continuity_lineage_bench.py) | [wrap](../echo4/continuity_lineage_bench.py#L30), [calibration](../echo4/continuity_lineage_bench.py#L36), [commission](../echo4/continuity_lineage_bench.py#L43), [finish_diagnosis](../echo4/continuity_lineage_bench.py#L47), [authorize](../echo4/continuity_lineage_bench.py#L57), [prepared](../echo4/continuity_lineage_bench.py#L66), [trajectory](../echo4/continuity_lineage_bench.py#L113), [resumed](../echo4/continuity_lineage_bench.py#L173), [sources](../echo4/continuity_lineage_bench.py#L180), [row](../echo4/continuity_lineage_bench.py#L187), [checks](../echo4/continuity_lineage_bench.py#L195), [report](../echo4/continuity_lineage_bench.py#L217), [campaign](../echo4/continuity_lineage_bench.py#L226), [verify](../echo4/continuity_lineage_bench.py#L241), [main](../echo4/continuity_lineage_bench.py#L263) | — |
| [echo4/demo.py](../echo4/demo.py) | [run_demo](../echo4/demo.py#L15) | — |
| [echo4/dream_bench.py](../echo4/dream_bench.py) | [sources](../echo4/dream_bench.py#L32), [persist](../echo4/dream_bench.py#L39), [cases](../echo4/dream_bench.py#L53), [histories](../echo4/dream_bench.py#L63), [evaluate](../echo4/dream_bench.py#L76), [summary](../echo4/dream_bench.py#L109), [observed_summary](../echo4/dream_bench.py#L119), [rotations](../echo4/dream_bench.py#L132), [build](../echo4/dream_bench.py#L137), [campaign](../echo4/dream_bench.py#L234), [verify](../echo4/dream_bench.py#L246), [main](../echo4/dream_bench.py#L269) | — |
| [echo4/dream_history.py](../echo4/dream_history.py) | [sha](../echo4/dream_history.py#L25), [integer](../echo4/dream_history.py#L29), [keys](../echo4/dream_history.py#L34), [digest](../echo4/dream_history.py#L39), [validate](../echo4/dream_history.py#L44), [Archive](../echo4/dream_history.py#L90), [Replay](../echo4/dream_history.py#L116) | [Archive.__init__](../echo4/dream_history.py#L92), [Archive.dumps](../echo4/dream_history.py#L97), [Archive.loads](../echo4/dream_history.py#L101), [Archive.replay](../echo4/dream_history.py#L112), [Replay.__init__](../echo4/dream_history.py#L118), [Replay.view](../echo4/dream_history.py#L136), [Replay.expand](../echo4/dream_history.py#L144), [Replay.batch](../echo4/dream_history.py#L147) |
| [echo4/dream_history_bench.py](../echo4/dream_history_bench.py) | [sources](../echo4/dream_history_bench.py#L22), [parent_binding](../echo4/dream_history_bench.py#L28), [observation](../echo4/dream_history_bench.py#L48), [collect](../echo4/dream_history_bench.py#L55), [replay_all](../echo4/dream_history_bench.py#L104), [fresh_replay](../echo4/dream_history_bench.py#L116), [build](../echo4/dream_history_bench.py#L123), [record](../echo4/dream_history_bench.py#L164), [verify](../echo4/dream_history_bench.py#L173), [main](../echo4/dream_history_bench.py#L192) | — |
| [echo4/dream_policy.py](../echo4/dream_policy.py) | [Policy](../echo4/dream_policy.py#L17), [parse_candidates](../echo4/dream_policy.py#L52), [request_plan](../echo4/dream_policy.py#L67), [run_policy](../echo4/dream_policy.py#L92), [ranking](../echo4/dream_policy.py#L135), [select](../echo4/dream_policy.py#L141), [promotion](../echo4/dream_policy.py#L156) | [Policy.data](../echo4/dream_policy.py#L35), [Policy.identity](../echo4/dream_policy.py#L40), [Policy.from_data](../echo4/dream_policy.py#L44) |
| [echo4/dream_probe.py](../echo4/dream_probe.py) | [decode_trace](../echo4/dream_probe.py#L20), [ProbeArchive](../echo4/dream_probe.py#L34), [ProbeReplay](../echo4/dream_probe.py#L78), [prepare](../echo4/dream_probe.py#L108), [model_for](../echo4/dream_probe.py#L113), [native](../echo4/dream_probe.py#L118), [collect](../echo4/dream_probe.py#L124) | [ProbeArchive.__init__](../echo4/dream_probe.py#L35), [ProbeArchive.dumps](../echo4/dream_probe.py#L60), [ProbeArchive.loads](../echo4/dream_probe.py#L64), [ProbeArchive.replay](../echo4/dream_probe.py#L74), [ProbeReplay.__init__](../echo4/dream_probe.py#L79), [ProbeReplay.view](../echo4/dream_probe.py#L85), [ProbeReplay.request](../echo4/dream_probe.py#L90) |
| [echo4/dream_qwen.py](../echo4/dream_qwen.py) | [prompt](../echo4/dream_qwen.py#L39), [payload](../echo4/dream_qwen.py#L47), [NoRedirect](../echo4/dream_qwen.py#L53), [LocalQwen](../echo4/dream_qwen.py#L58), [read_proposal](../echo4/dream_qwen.py#L151) | [NoRedirect.redirect_request](../echo4/dream_qwen.py#L54), [LocalQwen.__init__](../echo4/dream_qwen.py#L60), [LocalQwen.propose](../echo4/dream_qwen.py#L133) |
| [echo4/dream_v2.py](../echo4/dream_v2.py) | [binding](../echo4/dream_v2.py#L33), [load_history](../echo4/dream_v2.py#L49), [exam_bodies](../echo4/dream_v2.py#L73), [control_candidates](../echo4/dream_v2.py#L96), [ReplayEvaluator](../echo4/dream_v2.py#L108), [context](../echo4/dream_v2.py#L155), [promote](../echo4/dream_v2.py#L164), [FeedbackQwen](../echo4/dream_v2.py#L180) | [ReplayEvaluator.__init__](../echo4/dream_v2.py#L110), [ReplayEvaluator.outcomes](../echo4/dream_v2.py#L116), [ReplayEvaluator.score](../echo4/dream_v2.py#L121), [ReplayEvaluator.public](../echo4/dream_v2.py#L129), [ReplayEvaluator.select](../echo4/dream_v2.py#L135), [ReplayEvaluator.cost](../echo4/dream_v2.py#L148), [FeedbackQwen.propose](../echo4/dream_v2.py#L182) |
| [echo4/dream_v2_bench.py](../echo4/dream_v2_bench.py) | [sources](../echo4/dream_v2_bench.py#L25), [build](../echo4/dream_v2_bench.py#L31), [campaign](../echo4/dream_v2_bench.py#L124), [verify](../echo4/dream_v2_bench.py#L136), [main](../echo4/dream_v2_bench.py#L160) | — |
| [echo4/dream_v3.py](../echo4/dream_v3.py) | [binding](../echo4/dream_v3.py#L29), [exam_bodies](../echo4/dream_v3.py#L44), [cases](../echo4/dream_v3.py#L66), [histories](../echo4/dream_v3.py#L75), [evaluate](../echo4/dream_v3.py#L89), [starters](../echo4/dream_v3.py#L122), [ReplayEvaluator](../echo4/dream_v3.py#L136), [context](../echo4/dream_v3.py#L150), [payload](../echo4/dream_v3.py#L183), [Qwen](../echo4/dream_v3.py#L194), [read_proposal](../echo4/dream_v3.py#L212) | [ReplayEvaluator.outcomes](../echo4/dream_v3.py#L138), [ReplayEvaluator.score](../echo4/dream_v3.py#L143), [Qwen.propose](../echo4/dream_v3.py#L195) |
| [echo4/dream_v3_bench.py](../echo4/dream_v3_bench.py) | [sources](../echo4/dream_v3_bench.py#L28), [development_binding](../echo4/dream_v3_bench.py#L35), [load_history](../echo4/dream_v3_bench.py#L47), [build](../echo4/dream_v3_bench.py#L68), [campaign](../echo4/dream_v3_bench.py#L173), [verify](../echo4/dream_v3_bench.py#L185), [main](../echo4/dream_v3_bench.py#L209) | — |
| [echo4/dream_v3_development.py](../echo4/dream_v3_development.py) | [build](../echo4/dream_v3_development.py#L18), [main](../echo4/dream_v3_development.py#L52) | — |
| [echo4/dream_v3_profile.py](../echo4/dream_v3_profile.py) | [Policy](../echo4/dream_v3_profile.py#L34), [parse_candidates](../echo4/dream_v3_profile.py#L69), [Attributor](../echo4/dream_v3_profile.py#L84), [model_for](../echo4/dream_v3_profile.py#L113), [request_plan](../echo4/dream_v3_profile.py#L118), [run_policy](../echo4/dream_v3_profile.py#L137), [Archive](../echo4/dream_v3_profile.py#L177), [Replay](../echo4/dream_v3_profile.py#L230), [collect](../echo4/dream_v3_profile.py#L262) | [Policy.data](../echo4/dream_v3_profile.py#L52), [Policy.identity](../echo4/dream_v3_profile.py#L57), [Policy.from_data](../echo4/dream_v3_profile.py#L61), [Attributor.choose](../echo4/dream_v3_profile.py#L106), [Attributor.resources](../echo4/dream_v3_profile.py#L109), [Archive.__init__](../echo4/dream_v3_profile.py#L180), [Archive.dumps](../echo4/dream_v3_profile.py#L212), [Archive.loads](../echo4/dream_v3_profile.py#L216), [Archive.replay](../echo4/dream_v3_profile.py#L226), [Replay.__init__](../echo4/dream_v3_profile.py#L231), [Replay.view](../echo4/dream_v3_profile.py#L237), [Replay.request](../echo4/dream_v3_profile.py#L242) |
| [echo4/dream_v3_screen.py](../echo4/dream_v3_screen.py) | [screen](../echo4/dream_v3_screen.py#L17), [main](../echo4/dream_v3_screen.py#L60) | — |
| [echo4/integrate.py](../echo4/integrate.py) | [_clamp](../echo4/integrate.py#L38), [credit](../echo4/integrate.py#L42), [new_body](../echo4/integrate.py#L76), [IntegratedTribe](../echo4/integrate.py#L82), [fingerprint](../echo4/integrate.py#L130), [start](../echo4/integrate.py#L150), [situate_check](../echo4/integrate.py#L158), [wipe](../echo4/integrate.py#L166), [step](../echo4/integrate.py#L187), [run](../echo4/integrate.py#L230), [false_facts](../echo4/integrate.py#L249), [summary](../echo4/integrate.py#L255), [resume_in_this_process](../echo4/integrate.py#L284), [resume_fresh_process](../echo4/integrate.py#L300) | [IntegratedTribe.__init__](../echo4/integrate.py#L85), [IntegratedTribe.attach](../echo4/integrate.py#L94) |
| [echo4/integrate_bench.py](../echo4/integrate_bench.py) | [_decisions](../echo4/integrate_bench.py#L34), [c1_fault_and_liar](../echo4/integrate_bench.py#L38), [c2_pause_after_fault](../echo4/integrate_bench.py#L49), [c3_no_energy_at_hierarchy_change](../echo4/integrate_bench.py#L62), [c4_corrupt_fact](../echo4/integrate_bench.py#L79), [c4b_testimony_forged_as_fact](../echo4/integrate_bench.py#L92), [c5_cam_full](../echo4/integrate_bench.py#L104), [c6_veto_and_operator_stop](../echo4/integrate_bench.py#L120), [integrated_trace](../echo4/integrate_bench.py#L143), [integrated_profile](../echo4/integrate_bench.py#L151), [seed_block](../echo4/integrate_bench.py#L162), [ablation_table](../echo4/integrate_bench.py#L182), [judge](../echo4/integrate_bench.py#L200), [sources](../echo4/integrate_bench.py#L219), [parent](../echo4/integrate_bench.py#L225), [tests](../echo4/integrate_bench.py#L233), [campaign](../echo4/integrate_bench.py#L241), [verify](../echo4/integrate_bench.py#L263), [main](../echo4/integrate_bench.py#L285) | — |
| [echo4/integrate_exam.py](../echo4/integrate_exam.py) | [_v](../echo4/integrate_exam.py#L25), [_tot](../echo4/integrate_exam.py#L30), [_count](../echo4/integrate_exam.py#L34), [judge](../echo4/integrate_exam.py#L38), [sources](../echo4/integrate_exam.py#L88), [parent](../echo4/integrate_exam.py#L93), [campaign](../echo4/integrate_exam.py#L101), [verify](../echo4/integrate_exam.py#L123), [main](../echo4/integrate_exam.py#L147) | — |
| [echo4/interaction_bench.py](../echo4/interaction_bench.py) | [sources](../echo4/interaction_bench.py#L24), [parent](../echo4/interaction_bench.py#L30), [census](../echo4/interaction_bench.py#L42), [summary](../echo4/interaction_bench.py#L65), [witnesses](../echo4/interaction_bench.py#L72), [native](../echo4/interaction_bench.py#L86), [campaign](../echo4/interaction_bench.py#L111), [verify](../echo4/interaction_bench.py#L135), [main](../echo4/interaction_bench.py#L151) | — |
| [echo4/interaction_cases.py](../echo4/interaction_cases.py) | [fixture](../echo4/interaction_cases.py#L15), [summary](../echo4/interaction_cases.py#L24), [reconstructs](../echo4/interaction_cases.py#L37), [execute](../echo4/interaction_cases.py#L48), [cohort](../echo4/interaction_cases.py#L65), [adverse](../echo4/interaction_cases.py#L87) | — |
| [echo4/interaction_final.py](../echo4/interaction_final.py) | [sources](../echo4/interaction_final.py#L21), [parent](../echo4/interaction_final.py#L28), [unit_checks](../echo4/interaction_final.py#L41), [compact_cohort](../echo4/interaction_final.py#L49), [campaign](../echo4/interaction_final.py#L56), [check_header](../echo4/interaction_final.py#L99), [verify](../echo4/interaction_final.py#L118), [main](../echo4/interaction_final.py#L132) | — |
| [echo4/interaction_learning.py](../echo4/interaction_learning.py) | [belief](../echo4/interaction_learning.py#L13), [BeliefAgent](../echo4/interaction_learning.py#L27), [RoutedObserver](../echo4/interaction_learning.py#L65) | [BeliefAgent.__init__](../echo4/interaction_learning.py#L28), [BeliefAgent.observation](../echo4/interaction_learning.py#L37), [RoutedObserver.__init__](../echo4/interaction_learning.py#L67), [RoutedObserver.begin](../echo4/interaction_learning.py#L82), [RoutedObserver.finish](../echo4/interaction_learning.py#L94) |
| [echo4/interaction_session.py](../echo4/interaction_session.py) | [Port](../echo4/interaction_session.py#L14), [InteractionSession](../echo4/interaction_session.py#L32) | [Port.__init__](../echo4/interaction_session.py#L17), [Port.i](../echo4/interaction_session.py#L21), [Port.cell](../echo4/interaction_session.py#L24), [Port.step](../echo4/interaction_session.py#L27), [InteractionSession.__init__](../echo4/interaction_session.py#L33), [InteractionSession.step](../echo4/interaction_session.py#L73), [InteractionSession.inhibit](../echo4/interaction_session.py#L109), [InteractionSession.stop](../echo4/interaction_session.py#L119), [InteractionSession.invariant](../echo4/interaction_session.py#L125) |
| [echo4/interaction_social.py](../echo4/interaction_social.py) | [settled](../echo4/interaction_social.py#L17), [PrivateTraining](../echo4/interaction_social.py#L21), [SocialPort](../echo4/interaction_social.py#L29), [SocialSession](../echo4/interaction_social.py#L39) | [PrivateTraining.step](../echo4/interaction_social.py#L24), [SocialPort.step](../echo4/interaction_social.py#L32), [SocialSession.__init__](../echo4/interaction_social.py#L40), [SocialSession.private_credit](../echo4/interaction_social.py#L78), [SocialSession.step](../echo4/interaction_social.py#L90), [SocialSession.stop](../echo4/interaction_social.py#L122), [SocialSession.invariant](../echo4/interaction_social.py#L127) |
| [echo4/interaction_world.py](../echo4/interaction_world.py) | [pair](../echo4/interaction_world.py#L11), [InteractionWorld](../echo4/interaction_world.py#L19) | [InteractionWorld.__init__](../echo4/interaction_world.py#L20), [InteractionWorld.cue](../echo4/interaction_world.py#L33), [InteractionWorld.done](../echo4/interaction_world.py#L37), [InteractionWorld.advance](../echo4/interaction_world.py#L40), [InteractionWorld.stop](../echo4/interaction_world.py#L64) |
| [echo4/maintain_agent.py](../echo4/maintain_agent.py) | [MaintenanceAgent](../echo4/maintain_agent.py#L6) | [MaintenanceAgent.__init__](../echo4/maintain_agent.py#L7), [MaintenanceAgent.turn](../echo4/maintain_agent.py#L17), [MaintenanceAgent.respawn](../echo4/maintain_agent.py#L23), [MaintenanceAgent.operator_stop](../echo4/maintain_agent.py#L27) |
| [echo4/maintain_bench.py](../echo4/maintain_bench.py) | [sources](../echo4/maintain_bench.py#L32), [parent_binding](../echo4/maintain_bench.py#L39), [_ScriptedWitness](../echo4/maintain_bench.py#L53), [trial](../echo4/maintain_bench.py#L65), [evaluate](../echo4/maintain_bench.py#L114), [build](../echo4/maintain_bench.py#L151), [verify](../echo4/maintain_bench.py#L165), [main](../echo4/maintain_bench.py#L179) | [_ScriptedWitness.__init__](../echo4/maintain_bench.py#L55) |
| [echo4/maintain_continuity.py](../echo4/maintain_continuity.py) | [source_hashes](../echo4/maintain_continuity.py#L34), [checked_events](../echo4/maintain_continuity.py#L41), [validate](../echo4/maintain_continuity.py#L55), [MaintainRun](../echo4/maintain_continuity.py#L156), [loads](../echo4/maintain_continuity.py#L253) | [MaintainRun.__init__](../echo4/maintain_continuity.py#L157), [MaintainRun.step](../echo4/maintain_continuity.py#L166), [MaintainRun.stop](../echo4/maintain_continuity.py#L212), [MaintainRun.snapshot](../echo4/maintain_continuity.py#L221), [MaintainRun.dumps](../echo4/maintain_continuity.py#L242), [MaintainRun.save](../echo4/maintain_continuity.py#L248) |
| [echo4/maintain_control.py](../echo4/maintain_control.py) | [MaintainControl](../echo4/maintain_control.py#L6) | [MaintainControl.__init__](../echo4/maintain_control.py#L7), [MaintainControl.turn](../echo4/maintain_control.py#L19) |
| [echo4/maintain_final.py](../echo4/maintain_final.py) | [sha](../echo4/maintain_final.py#L40), [sources](../echo4/maintain_final.py#L44), [parent](../echo4/maintain_final.py#L50), [exam_bodies](../echo4/maintain_final.py#L62), [prepared](../echo4/maintain_final.py#L72), [trajectory](../echo4/maintain_final.py#L78), [episode](../echo4/maintain_final.py#L91), [summary](../echo4/maintain_final.py#L131), [batch](../echo4/maintain_final.py#L142), [resumed](../echo4/maintain_final.py#L176), [continuity_cases](../echo4/maintain_final.py#L183), [mutant_suite](../echo4/maintain_final.py#L192), [continuity_suite](../echo4/maintain_final.py#L226), [campaign](../echo4/maintain_final.py#L265), [verify](../echo4/maintain_final.py#L296), [main](../echo4/maintain_final.py#L317) | — |
| [echo4/maintain_model.py](../echo4/maintain_model.py) | [MaintainStop](../echo4/maintain_model.py#L22), [bands](../echo4/maintain_model.py#L26), [prior](../echo4/maintain_model.py#L35), [project](../echo4/maintain_model.py#L42), [_service](../echo4/maintain_model.py#L76), [advance](../echo4/maintain_model.py#L94), [safe](../echo4/maintain_model.py#L98), [MaintainModel](../echo4/maintain_model.py#L102) | [MaintainModel.__init__](../echo4/maintain_model.py#L103), [MaintainModel.choose](../echo4/maintain_model.py#L125), [MaintainModel.prepare](../echo4/maintain_model.py#L180), [MaintainModel.observe](../echo4/maintain_model.py#L188) |
| [echo4/maintain_world.py](../echo4/maintain_world.py) | [ServiceReceipt](../echo4/maintain_world.py#L22), [MaintenanceEnv](../echo4/maintain_world.py#L37) | [MaintenanceEnv.__init__](../echo4/maintain_world.py#L38), [MaintenanceEnv.reset](../echo4/maintain_world.py#L54), [MaintenanceEnv.stop](../echo4/maintain_world.py#L57), [MaintenanceEnv.stopped](../echo4/maintain_world.py#L63), [MaintenanceEnv.advance](../echo4/maintain_world.py#L66), [MaintenanceEnv.step_homeostatic](../echo4/maintain_world.py#L125), [MaintenanceEnv.spares_balanced](../echo4/maintain_world.py#L133), [MaintenanceEnv.audit_state](../echo4/maintain_world.py#L136) |
| [echo4/other_bench.py](../echo4/other_bench.py) | [sha](../echo4/other_bench.py#L28), [sources](../echo4/other_bench.py#L32), [parent](../echo4/other_bench.py#L38), [preferences](../echo4/other_bench.py#L51), [scores](../echo4/other_bench.py#L59), [episode](../echo4/other_bench.py#L66), [batch](../echo4/other_bench.py#L86), [witness_model](../echo4/other_bench.py#L114), [controls](../echo4/other_bench.py#L122), [fresh_replay](../echo4/other_bench.py#L168), [campaign](../echo4/other_bench.py#L186), [verify](../echo4/other_bench.py#L218), [main](../echo4/other_bench.py#L234) | — |
| [echo4/other_model.py](../echo4/other_model.py) | [context](../echo4/other_model.py#L18), [outcome](../echo4/other_model.py#L26), [decode](../echo4/other_model.py#L35), [OtherModel](../echo4/other_model.py#L51) | [OtherModel.__init__](../echo4/other_model.py#L52), [OtherModel.begin](../echo4/other_model.py#L109), [OtherModel.finish](../echo4/other_model.py#L131), [OtherModel.stop](../echo4/other_model.py#L169) |
| [echo4/other_replay.py](../echo4/other_replay.py) | [digest](../echo4/other_replay.py#L11), [transcript](../echo4/other_replay.py#L39), [replay](../echo4/other_replay.py#L44) | — |
| [echo4/other_world.py](../echo4/other_world.py) | [ChoiceEnv](../echo4/other_world.py#L18), [new_agent](../echo4/other_world.py#L57), [Encounter](../echo4/other_world.py#L64) | [ChoiceEnv.__init__](../echo4/other_world.py#L21), [ChoiceEnv.i](../echo4/other_world.py#L36), [ChoiceEnv.cell](../echo4/other_world.py#L39), [ChoiceEnv.step](../echo4/other_world.py#L42), [ChoiceEnv.stop](../echo4/other_world.py#L53), [Encounter.__init__](../echo4/other_world.py#L65), [Encounter.step](../echo4/other_world.py#L81), [Encounter.stop](../echo4/other_world.py#L126), [Encounter.invariant](../echo4/other_world.py#L132) |
| [echo4/relation_b_bench.py](../echo4/relation_b_bench.py) | [b_summary](../echo4/relation_b_bench.py#L28), [reconstruct_b](../echo4/relation_b_bench.py#L45), [execute](../echo4/relation_b_bench.py#L63), [development](../echo4/relation_b_bench.py#L86), [sources](../echo4/relation_b_bench.py#L110), [parent](../echo4/relation_b_bench.py#L116), [tests](../echo4/relation_b_bench.py#L126), [campaign](../echo4/relation_b_bench.py#L134), [verify](../echo4/relation_b_bench.py#L156), [main](../echo4/relation_b_bench.py#L176) | — |
| [echo4/relation_bench.py](../echo4/relation_bench.py) | [sources](../echo4/relation_bench.py#L26), [parent](../echo4/relation_bench.py#L32), [relation_replay](../echo4/relation_bench.py#L42), [native](../echo4/relation_bench.py#L52), [partial](../echo4/relation_bench.py#L82), [tests](../echo4/relation_bench.py#L93), [campaign](../echo4/relation_bench.py#L101), [verify](../echo4/relation_bench.py#L125), [main](../echo4/relation_bench.py#L148) | — |
| [echo4/relation_c.py](../echo4/relation_c.py) | [NeverHelp](../echo4/relation_c.py#L21), [RelationCSession](../echo4/relation_c.py#L32) | [NeverHelp.step](../echo4/relation_c.py#L23), [RelationCSession.help_step](../echo4/relation_c.py#L35), [RelationCSession.relieve](../echo4/relation_c.py#L47), [RelationCSession.retired](../echo4/relation_c.py#L82), [RelationCSession.invariant](../echo4/relation_c.py#L85) |
| [echo4/relation_c_bench.py](../echo4/relation_c_bench.py) | [reliable_handle](../echo4/relation_c_bench.py#L29), [life](../echo4/relation_c_bench.py#L33), [refusals](../echo4/relation_c_bench.py#L54), [c0_nominal_parity](../echo4/relation_c_bench.py#L58), [c1_relief](../echo4/relation_c_bench.py#L68), [c2_impostor](../echo4/relation_c_bench.py#L82), [c3_absence](../echo4/relation_c_bench.py#L94), [c4_partial](../echo4/relation_c_bench.py#L109), [c5_new_identity](../echo4/relation_c_bench.py#L122), [c6_corruption](../echo4/relation_c_bench.py#L139), [c7_limits](../echo4/relation_c_bench.py#L159), [c8_operator](../echo4/relation_c_bench.py#L186), [sources](../echo4/relation_c_bench.py#L206), [parent](../echo4/relation_c_bench.py#L212), [tests](../echo4/relation_c_bench.py#L221), [campaign](../echo4/relation_c_bench.py#L229), [verify](../echo4/relation_c_bench.py#L250), [main](../echo4/relation_c_bench.py#L270) | — |
| [echo4/relation_d.py](../echo4/relation_d.py) | [life](../echo4/relation_d.py#L31), [judge](../echo4/relation_d.py#L44), [sources](../echo4/relation_d.py#L64), [parent](../echo4/relation_d.py#L69), [tests](../echo4/relation_d.py#L78), [campaign](../echo4/relation_d.py#L88), [verify](../echo4/relation_d.py#L117), [lock_is_exam](../echo4/relation_d.py#L142), [main](../echo4/relation_d.py#L149) | — |
| [echo4/relation_help.py](../echo4/relation_help.py) | [success](../echo4/relation_help.py#L35), [bucket](../echo4/relation_help.py#L43), [shuffled](../echo4/relation_help.py#L52), [row](../echo4/relation_help.py#L60), [settle](../echo4/relation_help.py#L79), [HelpAgent](../echo4/relation_help.py#L113), [HelpPort](../echo4/relation_help.py#L142), [PrivateHelp](../echo4/relation_help.py#L155), [incentive](../echo4/relation_help.py#L181), [HelpSession](../echo4/relation_help.py#L188) | [HelpAgent.__init__](../echo4/relation_help.py#L115), [HelpPort.__init__](../echo4/relation_help.py#L145), [HelpPort.cell](../echo4/relation_help.py#L148), [HelpPort.step](../echo4/relation_help.py#L151), [PrivateHelp.__init__](../echo4/relation_help.py#L159), [PrivateHelp.i](../echo4/relation_help.py#L166), [PrivateHelp.cell](../echo4/relation_help.py#L169), [PrivateHelp.step](../echo4/relation_help.py#L172), [HelpSession.__init__](../echo4/relation_help.py#L189), [HelpSession.focal](../echo4/relation_help.py#L212), [HelpSession.focal](../echo4/relation_help.py#L216), [HelpSession.levels](../echo4/relation_help.py#L221), [HelpSession.partner_level](../echo4/relation_help.py#L234), [HelpSession.help_step](../echo4/relation_help.py#L244), [HelpSession.invariant](../echo4/relation_help.py#L326) |
| [echo4/relation_memory.py](../echo4/relation_memory.py) | [episode_key](../echo4/relation_memory.py#L22), [observation](../echo4/relation_memory.py#L29), [parse_observation](../echo4/relation_memory.py#L66), [RelationMemory](../echo4/relation_memory.py#L83), [replay](../echo4/relation_memory.py#L223) | [RelationMemory.__init__](../echo4/relation_memory.py#L84), [RelationMemory.append](../echo4/relation_memory.py#L95), [RelationMemory.history](../echo4/relation_memory.py#L153), [RelationMemory.summary](../echo4/relation_memory.py#L175), [RelationMemory.digest](../echo4/relation_memory.py#L194), [RelationMemory.invariant](../echo4/relation_memory.py#L200), [RelationMemory.stop](../echo4/relation_memory.py#L219) |
| [echo4/relation_session.py](../echo4/relation_session.py) | [RelationSession](../echo4/relation_session.py#L6) | [RelationSession.__init__](../echo4/relation_session.py#L7), [RelationSession.step](../echo4/relation_session.py#L11), [RelationSession.invariant](../echo4/relation_session.py#L29), [RelationSession.stop](../echo4/relation_session.py#L35) |
| [echo4/roles.py](../echo4/roles.py) | [schedule](../echo4/roles.py#L46), [competent](../echo4/roles.py#L65), [settle](../echo4/roles.py#L71), [receipt_key](../echo4/roles.py#L114), [claim_key](../echo4/roles.py#L120), [check_receipt](../echo4/roles.py#L127), [RoleMemory](../echo4/roles.py#L146), [last_attempt](../echo4/roles.py#L232), [cumulative_success](../echo4/roles.py#L240), [row](../echo4/roles.py#L249), [RolesAgent](../echo4/roles.py#L273), [Port](../echo4/roles.py#L301), [AcceptTraining](../echo4/roles.py#L314), [counterpart](../echo4/roles.py#L337), [RolesSession](../echo4/roles.py#L348) | [RoleMemory.__init__](../echo4/roles.py#L149), [RoleMemory.record](../echo4/roles.py#L158), [RoleMemory.claim](../echo4/roles.py#L174), [RoleMemory.receipts](../echo4/roles.py#L189), [RoleMemory.claimants](../echo4/roles.py#L208), [RoleMemory.invariant](../echo4/roles.py#L218), [RoleMemory.stop](../echo4/roles.py#L228), [RolesAgent.__init__](../echo4/roles.py#L274), [Port.__init__](../echo4/roles.py#L304), [Port.cell](../echo4/roles.py#L307), [Port.step](../echo4/roles.py#L310), [AcceptTraining.__init__](../echo4/roles.py#L318), [AcceptTraining.i](../echo4/roles.py#L322), [AcceptTraining.cell](../echo4/roles.py#L325), [AcceptTraining.step](../echo4/roles.py#L328), [RolesSession.__init__](../echo4/roles.py#L349), [RolesSession.done](../echo4/roles.py#L375), [RolesSession.evidence](../echo4/roles.py#L378), [RolesSession.step](../echo4/roles.py#L389), [RolesSession.stop](../echo4/roles.py#L459), [RolesSession.invariant](../echo4/roles.py#L463) |
| [echo4/roles_bench.py](../echo4/roles_bench.py) | [recovery](../echo4/roles_bench.py#L25), [reconstruct](../echo4/roles_bench.py#L38), [execute](../echo4/roles_bench.py#L60), [development](../echo4/roles_bench.py#L81), [sources](../echo4/roles_bench.py#L100), [parent](../echo4/roles_bench.py#L106), [tests](../echo4/roles_bench.py#L114), [campaign](../echo4/roles_bench.py#L122), [verify](../echo4/roles_bench.py#L144), [main](../echo4/roles_bench.py#L164) | — |
| [echo4/roles_c.py](../echo4/roles_c.py) | [relay_key](../echo4/roles_c.py#L21), [noop](../echo4/roles_c.py#L30), [window](../echo4/roles_c.py#L35), [RolesCSession](../echo4/roles_c.py#L46) | [RolesCSession.__init__](../echo4/roles_c.py#L47), [RolesCSession.competent_now](../echo4/roles_c.py#L65), [RolesCSession.step](../echo4/roles_c.py#L80), [RolesCSession.invariant](../echo4/roles_c.py#L188) |
| [echo4/roles_c_bench.py](../echo4/roles_c_bench.py) | [run](../echo4/roles_c_bench.py#L24), [nominal_digest](../echo4/roles_c_bench.py#L29), [run_length](../echo4/roles_c_bench.py#L33), [c0_nominal_parity](../echo4/roles_c_bench.py#L41), [c1_refusal](../echo4/roles_c_bench.py#L51), [c2_relay](../echo4/roles_c_bench.py#L63), [c3_new_member](../echo4/roles_c_bench.py#L79), [c4_absence](../echo4/roles_c_bench.py#L88), [c5_claimant](../echo4/roles_c_bench.py#L102), [c6_limits](../echo4/roles_c_bench.py#L112), [c7_operator](../echo4/roles_c_bench.py#L133), [c8_corruption](../echo4/roles_c_bench.py#L148), [sources](../echo4/roles_c_bench.py#L170), [parent](../echo4/roles_c_bench.py#L176), [tests](../echo4/roles_c_bench.py#L185), [campaign](../echo4/roles_c_bench.py#L193), [verify](../echo4/roles_c_bench.py#L214), [main](../echo4/roles_c_bench.py#L234) | — |
| [echo4/roles_d.py](../echo4/roles_d.py) | [execute](../echo4/roles_d.py#L31), [life](../echo4/roles_d.py#L47), [judge](../echo4/roles_d.py#L53), [sources](../echo4/roles_d.py#L73), [parent](../echo4/roles_d.py#L77), [tests](../echo4/roles_d.py#L86), [campaign](../echo4/roles_d.py#L95), [verify](../echo4/roles_d.py#L124), [main](../echo4/roles_d.py#L148) | — |
| [echo4/roles_v2.py](../echo4/roles_v2.py) | [RolesV2Session](../echo4/roles_v2.py#L33), [execute](../echo4/roles_v2.py#L41), [life](../echo4/roles_v2.py#L46), [development](../echo4/roles_v2.py#L51), [c0_v1_parity](../echo4/roles_v2.py#L67), [witnesses](../echo4/roles_v2.py#L77), [sources](../echo4/roles_v2.py#L86), [parent](../echo4/roles_v2.py#L91), [tests](../echo4/roles_v2.py#L100), [sealed](../echo4/roles_v2.py#L109), [dev_campaign](../echo4/roles_v2.py#L128), [exam_campaign](../echo4/roles_v2.py#L142), [verify](../echo4/roles_v2.py#L163), [main](../echo4/roles_v2.py#L190) | [RolesV2Session.__init__](../echo4/roles_v2.py#L34) |
| [echo4/self_agent.py](../echo4/self_agent.py) | [SelfAgent](../echo4/self_agent.py#L7) | [SelfAgent.__init__](../echo4/self_agent.py#L8), [SelfAgent.calibrate_self_reference](../echo4/self_agent.py#L12), [SelfAgent.seal_self_reference](../echo4/self_agent.py#L15), [SelfAgent.compare_self_observation](../echo4/self_agent.py#L18) |
| [echo4/self_attribution.py](../echo4/self_attribution.py) | [_tables](../echo4/self_attribution.py#L23), [ProbeTrace](../echo4/self_attribution.py#L41), [ProbePlan](../echo4/self_attribution.py#L54), [_packet](../echo4/self_attribution.py#L62), [validate_trace](../echo4/self_attribution.py#L70), [forecast](../echo4/self_attribution.py#L100), [_nominal_signature](../echo4/self_attribution.py#L116), [possible_labels](../echo4/self_attribution.py#L127), [SelfAttributor](../echo4/self_attribution.py#L134) | [SelfAttributor.__init__](../echo4/self_attribution.py#L142), [SelfAttributor.diagnosis](../echo4/self_attribution.py#L187), [SelfAttributor.choose](../echo4/self_attribution.py#L212), [SelfAttributor.consume](../echo4/self_attribution.py#L240), [SelfAttributor.resources](../echo4/self_attribution.py#L260) |
| [echo4/self_audit.py](../echo4/self_audit.py) | [canonical](../echo4/self_audit.py#L31), [sources](../echo4/self_audit.py#L35), [cam_hash](../echo4/self_audit.py#L39), [normalized](../echo4/self_audit.py#L47), [private_cause](../echo4/self_audit.py#L56), [expected_change](../echo4/self_audit.py#L62), [add_group](../echo4/self_audit.py#L82), [group_report](../echo4/self_audit.py#L89), [public_case](../echo4/self_audit.py#L104), [check_witness](../echo4/self_audit.py#L116), [census](../echo4/self_audit.py#L130), [record](../echo4/self_audit.py#L202), [verify](../echo4/self_audit.py#L218), [main](../echo4/self_audit.py#L244) | — |
| [echo4/self_final.py](../echo4/self_final.py) | [SelfSession](../echo4/self_final.py#L8) | [SelfSession.__init__](../echo4/self_final.py#L15), [SelfSession.diagnosis](../echo4/self_final.py#L22), [SelfSession.choose](../echo4/self_final.py#L32), [SelfSession.consume](../echo4/self_final.py#L62), [SelfSession.cancel](../echo4/self_final.py#L70), [SelfSession.authorized_model](../echo4/self_final.py#L75), [SelfSession.resources](../echo4/self_final.py#L80) |
| [echo4/self_final_audit.py](../echo4/self_final_audit.py) | [file_hash](../echo4/self_final_audit.py#L53), [sources](../echo4/self_final_audit.py#L61), [parents](../echo4/self_final_audit.py#L65), [model_hash](../echo4/self_final_audit.py#L74), [diagnose](../echo4/self_final_audit.py#L79), [native_veto](../echo4/self_final_audit.py#L136), [negative_suite](../echo4/self_final_audit.py#L155), [accumulate_reuse](../echo4/self_final_audit.py#L199), [stage](../echo4/self_final_audit.py#L217), [campaign](../echo4/self_final_audit.py#L336), [record](../echo4/self_final_audit.py#L359), [verify](../echo4/self_final_audit.py#L376), [main](../echo4/self_final_audit.py#L415) | — |
| [echo4/self_final_world.py](../echo4/self_final_world.py) | [novel_probe](../echo4/self_final_world.py#L14) | — |
| [echo4/self_model.py](../echo4/self_model.py) | [Reference](../echo4/self_model.py#L16), [Change](../echo4/self_model.py#L24), [signature](../echo4/self_model.py#L33), [SelfChangeMonitor](../echo4/self_model.py#L54) | [SelfChangeMonitor.__init__](../echo4/self_model.py#L62), [SelfChangeMonitor.calibrate](../echo4/self_model.py#L69), [SelfChangeMonitor.seal](../echo4/self_model.py#L86), [SelfChangeMonitor.compare](../echo4/self_model.py#L90), [SelfChangeMonitor.model_hash](../echo4/self_model.py#L122), [SelfChangeMonitor.resources](../echo4/self_model.py#L128) |
| [echo4/self_probe_agent.py](../echo4/self_probe_agent.py) | [SelfProbeAgent](../echo4/self_probe_agent.py#L6) | [SelfProbeAgent.new_self_diagnosis](../echo4/self_probe_agent.py#L7) |
| [echo4/self_probe_audit.py](../echo4/self_probe_audit.py) | [sources](../echo4/self_probe_audit.py#L29), [public](../echo4/self_probe_audit.py#L33), [calibrate](../echo4/self_probe_audit.py#L39), [run_condition](../echo4/self_probe_audit.py#L49), [metrics](../echo4/self_probe_audit.py#L73), [accumulate](../echo4/self_probe_audit.py#L82), [census](../echo4/self_probe_audit.py#L99), [record](../echo4/self_probe_audit.py#L157), [verify](../echo4/self_probe_audit.py#L173), [main](../echo4/self_probe_audit.py#L199) | — |
| [echo4/self_probe_world.py](../echo4/self_probe_world.py) | [run_probe](../echo4/self_probe_world.py#L11) | — |
| [echo4/self_recovery.py](../echo4/self_recovery.py) | [RecoveryStop](../echo4/self_recovery.py#L15), [advance](../echo4/self_recovery.py#L19), [RecoveryBelief](../echo4/self_recovery.py#L28) | [RecoveryBelief.__init__](../echo4/self_recovery.py#L29), [RecoveryBelief.choose](../echo4/self_recovery.py#L68), [RecoveryBelief.prepare](../echo4/self_recovery.py#L91), [RecoveryBelief.observe](../echo4/self_recovery.py#L104), [RecoveryBelief.resources](../echo4/self_recovery.py#L142) |
| [echo4/self_recovery_agent.py](../echo4/self_recovery_agent.py) | [_LearningPermission](../echo4/self_recovery_agent.py#L7), [SelfRecoveryAgent](../echo4/self_recovery_agent.py#L22) | [_LearningPermission.__init__](../echo4/self_recovery_agent.py#L8), [_LearningPermission.observe_step](../echo4/self_recovery_agent.py#L11), [SelfRecoveryAgent.__init__](../echo4/self_recovery_agent.py#L23), [SelfRecoveryAgent.start_recovery](../echo4/self_recovery_agent.py#L27), [SelfRecoveryAgent.turn](../echo4/self_recovery_agent.py#L49), [SelfRecoveryAgent.respawn](../echo4/self_recovery_agent.py#L60) |
| [echo4/self_recovery_audit.py](../echo4/self_recovery_audit.py) | [sources](../echo4/self_recovery_audit.py#L30), [learn_trace](../echo4/self_recovery_audit.py#L34), [school](../echo4/self_recovery_audit.py#L45), [viable](../echo4/self_recovery_audit.py#L61), [row_state](../echo4/self_recovery_audit.py#L75), [sensory_hash](../echo4/self_recovery_audit.py#L82), [episode](../echo4/self_recovery_audit.py#L89), [totals](../echo4/self_recovery_audit.py#L157), [census](../echo4/self_recovery_audit.py#L164), [record](../echo4/self_recovery_audit.py#L226), [verify](../echo4/self_recovery_audit.py#L242), [main](../echo4/self_recovery_audit.py#L269) | — |
| [echo4/self_recovery_world.py](../echo4/self_recovery_world.py) | [physical_step](../echo4/self_recovery_world.py#L6), [RecoveryEnv](../echo4/self_recovery_world.py#L12) | [RecoveryEnv.__init__](../echo4/self_recovery_world.py#L13), [RecoveryEnv.step_homeostatic](../echo4/self_recovery_world.py#L20), [RecoveryEnv.advance](../echo4/self_recovery_world.py#L26), [RecoveryEnv.reset](../echo4/self_recovery_world.py#L42) |
| [echo4/self_reuse.py](../echo4/self_reuse.py) | [ReuseDecision](../echo4/self_reuse.py#L12), [validate_target](../echo4/self_reuse.py#L19), [choose_from_memory](../echo4/self_reuse.py#L25) | — |
| [echo4/self_reuse_agent.py](../echo4/self_reuse_agent.py) | [_FrozenLearning](../echo4/self_reuse_agent.py#L7), [SelfReuseAgent](../echo4/self_reuse_agent.py#L12) | [_FrozenLearning.observe_step](../echo4/self_reuse_agent.py#L8), [SelfReuseAgent.__init__](../echo4/self_reuse_agent.py#L13), [SelfReuseAgent.arm_school](../echo4/self_reuse_agent.py#L30), [SelfReuseAgent.arm_exposure](../echo4/self_reuse_agent.py#L38), [SelfReuseAgent.arm_reuse](../echo4/self_reuse_agent.py#L57), [SelfReuseAgent.turn](../echo4/self_reuse_agent.py#L87), [SelfReuseAgent.respawn](../echo4/self_reuse_agent.py#L97) |
| [echo4/self_reuse_audit.py](../echo4/self_reuse_audit.py) | [digest](../echo4/self_reuse_audit.py#L30), [sources](../echo4/self_reuse_audit.py#L34), [restore_trial](../echo4/self_reuse_audit.py#L38), [school](../echo4/self_reuse_audit.py#L49), [expose](../echo4/self_reuse_audit.py#L71), [task_memory_hash](../echo4/self_reuse_audit.py#L121), [task](../echo4/self_reuse_audit.py#L125), [summary](../echo4/self_reuse_audit.py#L152), [stage](../echo4/self_reuse_audit.py#L160), [campaign](../echo4/self_reuse_audit.py#L247), [record](../echo4/self_reuse_audit.py#L257), [verify](../echo4/self_reuse_audit.py#L273), [main](../echo4/self_reuse_audit.py#L302) | — |
| [echo4/sensation.py](../echo4/sensation.py) | [checked_packet](../echo4/sensation.py#L16), [SensoryHistory](../echo4/sensation.py#L21) | [SensoryHistory.__init__](../echo4/sensation.py#L30), [SensoryHistory.depth](../echo4/sensation.py#L39), [SensoryHistory.steps](../echo4/sensation.py#L43), [SensoryHistory.payload_bytes](../echo4/sensation.py#L47), [SensoryHistory.start](../echo4/sensation.py#L50), [SensoryHistory.advance](../echo4/sensation.py#L58), [SensoryHistory.snapshot](../echo4/sensation.py#L78), [SensoryHistory.sensory_delta](../echo4/sensation.py#L83) |
| [echo4/sensation_agent.py](../echo4/sensation_agent.py) | [SensationAgent](../echo4/sensation_agent.py#L10) | [SensationAgent.__init__](../echo4/sensation_agent.py#L11), [SensationAgent.turn](../echo4/sensation_agent.py#L29), [SensationAgent.respawn](../echo4/sensation_agent.py#L37) |
| [echo4/sensation_audit.py](../echo4/sensation_audit.py) | [_Group](../echo4/sensation_audit.py#L19), [_indices](../echo4/sensation_audit.py#L25), [_summarize](../echo4/sensation_audit.py#L32), [temporal_audit](../echo4/sensation_audit.py#L93) | — |
| [echo4/sensation_campaign.py](../echo4/sensation_campaign.py) | [encoded](../echo4/sensation_campaign.py#L25), [sha](../echo4/sensation_campaign.py#L30), [sensor](../echo4/sensation_campaign.py#L34), [episodes](../echo4/sensation_campaign.py#L39), [models](../echo4/sensation_campaign.py#L48), [run_stage](../echo4/sensation_campaign.py#L52), [stage_acceptance](../echo4/sensation_campaign.py#L112), [integration_probe](../echo4/sensation_campaign.py#L124), [sources](../echo4/sensation_campaign.py#L149), [campaign](../echo4/sensation_campaign.py#L159), [audit_evidence](../echo4/sensation_campaign.py#L217) | — |
| [echo4/sensation_predictor.py](../echo4/sensation_predictor.py) | [_action](../echo4/sensation_predictor.py#L26), [Prediction](../echo4/sensation_predictor.py#L32), [Sensation](../echo4/sensation_predictor.py#L40), [assess](../echo4/sensation_predictor.py#L48), [SensationPredictor](../echo4/sensation_predictor.py#L61) | [SensationPredictor.__init__](../echo4/sensation_predictor.py#L69), [SensationPredictor.start](../echo4/sensation_predictor.py#L92), [SensationPredictor.freeze](../echo4/sensation_predictor.py#L98), [SensationPredictor.anticipate](../echo4/sensation_predictor.py#L117), [SensationPredictor.observe](../echo4/sensation_predictor.py#L139), [SensationPredictor.model_state](../echo4/sensation_predictor.py#L170), [SensationPredictor.model_hash](../echo4/sensation_predictor.py#L184), [SensationPredictor.resources](../echo4/sensation_predictor.py#L189) |
| [echo4/situate.py](../echo4/situate.py) | [fingerprint](../echo4/situate.py#L32), [self_source](../echo4/situate.py#L36), [sense](../echo4/situate.py#L43), [replay_proof](../echo4/situate.py#L61), [SelfKnowledge](../echo4/situate.py#L73), [answer](../echo4/situate.py#L171), [render](../echo4/situate.py#L250) | [SelfKnowledge.__init__](../echo4/situate.py#L76), [SelfKnowledge.observe](../echo4/situate.py#L91), [SelfKnowledge.prove_world](../echo4/situate.py#L104), [SelfKnowledge.claim](../echo4/situate.py#L124), [SelfKnowledge.facts](../echo4/situate.py#L135), [SelfKnowledge.latest](../echo4/situate.py#L152), [SelfKnowledge.export](../echo4/situate.py#L156), [SelfKnowledge.load_history](../echo4/situate.py#L159), [SelfKnowledge.stop](../echo4/situate.py#L167) |
| [echo4/situate2.py](../echo4/situate2.py) | [fact_value](../echo4/situate2.py#L33), [parse_claims](../echo4/situate2.py#L55), [classify](../echo4/situate2.py#L71), [belief](../echo4/situate2.py#L84), [store_belief](../echo4/situate2.py#L89), [reference_traces](../echo4/situate2.py#L105), [_trivial_round](../echo4/situate2.py#L127), [_slim](../echo4/situate2.py#L147), [_echo_rounds](../echo4/situate2.py#L158), [m_prediction](../echo4/situate2.py#L162), [m_learning](../echo4/situate2.py#L167), [m_metacognition](../echo4/situate2.py#L175), [m_self_model](../echo4/situate2.py#L185), [m_efficiency](../echo4/situate2.py#L191), [passes](../echo4/situate2.py#L202), [evaluate_test](../echo4/situate2.py#L206), [select](../echo4/situate2.py#L211), [profile](../echo4/situate2.py#L248), [digest](../echo4/situate2.py#L269) | — |
| [echo4/situate2_bench.py](../echo4/situate2_bench.py) | [chat](../echo4/situate2_bench.py#L69), [facts_for_prompt](../echo4/situate2_bench.py#L74), [who_payload](../echo4/situate2_bench.py#L90), [tests_payload](../echo4/situate2_bench.py#L98), [Cortex](../echo4/situate2_bench.py#L104), [down_receipt](../echo4/situate2_bench.py#L128), [content_of](../echo4/situate2_bench.py#L141), [claims_of](../echo4/situate2_bench.py#L150), [tests_of](../echo4/situate2_bench.py#L157), [build_me](../echo4/situate2_bench.py#L173), [interpret](../echo4/situate2_bench.py#L183), [truth_table](../echo4/situate2_bench.py#L191), [novel](../echo4/situate2_bench.py#L197), [dream](../echo4/situate2_bench.py#L202), [condition](../echo4/situate2_bench.py#L225), [judge](../echo4/situate2_bench.py#L250), [sources](../echo4/situate2_bench.py#L291), [parent](../echo4/situate2_bench.py#L297), [tests](../echo4/situate2_bench.py#L305), [campaign](../echo4/situate2_bench.py#L313), [verify](../echo4/situate2_bench.py#L362), [main](../echo4/situate2_bench.py#L390) | [Cortex.ask](../echo4/situate2_bench.py#L113) |
| [echo4/situate_bench.py](../echo4/situate_bench.py) | [truth](../echo4/situate_bench.py#L39), [correct](../echo4/situate_bench.py#L53), [battery](../echo4/situate_bench.py#L77), [child](../echo4/situate_bench.py#L107), [spawn](../echo4/situate_bench.py#L173), [condition](../echo4/situate_bench.py#L182), [judge](../echo4/situate_bench.py#L200), [stable](../echo4/situate_bench.py#L221), [sources](../echo4/situate_bench.py#L235), [parent](../echo4/situate_bench.py#L241), [tests](../echo4/situate_bench.py#L249), [campaign](../echo4/situate_bench.py#L257), [verify](../echo4/situate_bench.py#L278), [main](../echo4/situate_bench.py#L306) | — |
| [echo4/tribe.py](../echo4/tribe.py) | [schedule](../echo4/tribe.py#L45), [true_order](../echo4/tribe.py#L65), [others](../echo4/tribe.py#L70), [absolute](../echo4/tribe.py#L74), [relative](../echo4/tribe.py#L79), [event_key](../echo4/tribe.py#L87), [check](../echo4/tribe.py#L93), [TribeMemory](../echo4/tribe.py#L108), [last_knower](../echo4/tribe.py#L200), [eliminated](../echo4/tribe.py#L207), [rank_counts](../echo4/tribe.py#L212), [derived_order](../echo4/tribe.py#L221), [leader](../echo4/tribe.py#L228), [suggestion](../echo4/tribe.py#L236), [row](../echo4/tribe.py#L250), [TribeAgent](../echo4/tribe.py#L260), [Port](../echo4/tribe.py#L286), [TribeSession](../echo4/tribe.py#L300) | [TribeMemory.__init__](../echo4/tribe.py#L111), [TribeMemory.record](../echo4/tribe.py#L120), [TribeMemory.claim](../echo4/tribe.py#L139), [TribeMemory.facts](../echo4/tribe.py#L156), [TribeMemory.claimants](../echo4/tribe.py#L175), [TribeMemory.invariant](../echo4/tribe.py#L184), [TribeMemory.stop](../echo4/tribe.py#L194), [TribeAgent.__init__](../echo4/tribe.py#L261), [Port.__init__](../echo4/tribe.py#L289), [Port.cell](../echo4/tribe.py#L292), [Port.step](../echo4/tribe.py#L295), [TribeSession.__init__](../echo4/tribe.py#L301), [TribeSession.done](../echo4/tribe.py#L316), [TribeSession.step](../echo4/tribe.py#L344), [TribeSession.stop](../echo4/tribe.py#L419), [TribeSession.invariant](../echo4/tribe.py#L424) |
| [echo4/tribe_exam.py](../echo4/tribe_exam.py) | [TribeCSession](../echo4/tribe_exam.py#L31), [strip](../echo4/tribe_exam.py#L70), [digest](../echo4/tribe_exam.py#L74), [run](../echo4/tribe_exam.py#L78), [c1_liar](../echo4/tribe_exam.py#L85), [c2_veto](../echo4/tribe_exam.py#L97), [c3_corruption](../echo4/tribe_exam.py#L105), [c4_capacity](../echo4/tribe_exam.py#L123), [c5_parity](../echo4/tribe_exam.py#L136), [witnesses](../echo4/tribe_exam.py#L149), [life](../echo4/tribe_exam.py#L155), [judge](../echo4/tribe_exam.py#L196), [sources](../echo4/tribe_exam.py#L229), [parent](../echo4/tribe_exam.py#L235), [tests](../echo4/tribe_exam.py#L244), [sealed](../echo4/tribe_exam.py#L252), [dev_campaign](../echo4/tribe_exam.py#L270), [exam_campaign](../echo4/tribe_exam.py#L283), [verify](../echo4/tribe_exam.py#L303), [main](../echo4/tribe_exam.py#L330) | [TribeCSession.__init__](../echo4/tribe_exam.py#L32), [TribeCSession.step](../echo4/tribe_exam.py#L45) |
| [echo4/tribe_liar.py](../echo4/tribe_liar.py) | [check](../echo4/tribe_liar.py#L34), [LiarMemory](../echo4/tribe_liar.py#L44), [eliminated](../echo4/tribe_liar.py#L82), [suggestion](../echo4/tribe_liar.py#L87), [reliability](../echo4/tribe_liar.py#L96), [LiarSession](../echo4/tribe_liar.py#L105), [life](../echo4/tribe_liar.py#L150), [judge](../echo4/tribe_liar.py#L182), [sources](../echo4/tribe_liar.py#L206), [parent](../echo4/tribe_liar.py#L211), [tests](../echo4/tribe_liar.py#L219), [campaign](../echo4/tribe_liar.py#L227), [verify](../echo4/tribe_liar.py#L250), [main](../echo4/tribe_liar.py#L278) | [LiarMemory.record](../echo4/tribe_liar.py#L45), [LiarMemory.facts](../echo4/tribe_liar.py#L63), [LiarSession.__init__](../echo4/tribe_liar.py#L106) |
| [echo4/tribe_liar2.py](../echo4/tribe_liar2.py) | [suggestion_meta](../echo4/tribe_liar2.py#L35), [MetaSession](../echo4/tribe_liar2.py#L49), [life](../echo4/tribe_liar2.py#L100), [judge](../echo4/tribe_liar2.py#L134), [sources](../echo4/tribe_liar2.py#L156), [parent](../echo4/tribe_liar2.py#L161), [tests](../echo4/tribe_liar2.py#L170), [campaign](../echo4/tribe_liar2.py#L178), [verify](../echo4/tribe_liar2.py#L201), [main](../echo4/tribe_liar2.py#L229) | [MetaSession.__init__](../echo4/tribe_liar2.py#L50) |
| [echo4/tribe_v4.py](../echo4/tribe_v4.py) | [proposal](../echo4/tribe_v4.py#L14), [row_v4](../echo4/tribe_v4.py#L36), [TribeV4Agent](../echo4/tribe_v4.py#L41), [TribeV4Session](../echo4/tribe_v4.py#L55) | [TribeV4Session.__init__](../echo4/tribe_v4.py#L56) |
| [echo4/viability.py](../echo4/viability.py) | [state_index](../echo4/viability.py#L18), [indexed_body](../echo4/viability.py#L24), [Witness](../echo4/viability.py#L32), [Viability](../echo4/viability.py#L68), [analyze](../echo4/viability.py#L105) | [Witness.prefix_length](../echo4/viability.py#L40), [Witness.cycle_length](../echo4/viability.py#L44), [Witness.valid](../echo4/viability.py#L47), [Viability.contains](../echo4/viability.py#L75), [Viability.safe_actions](../echo4/viability.py#L78), [Viability.max_steps](../echo4/viability.py#L82), [Viability.witness](../echo4/viability.py#L86) |
| [echo4/world.py](../echo4/world.py) | [integer](../echo4/world.py#L15), [Body](../echo4/world.py#L21), [DockRules](../echo4/world.py#L44), [Transition](../echo4/world.py#L65), [transition](../echo4/world.py#L84), [DockWorld](../echo4/world.py#L109) | [Body.cause](../echo4/world.py#L30), [Body.alive](../echo4/world.py#L39), [Transition.reward](../echo4/world.py#L74), [Transition.balanced](../echo4/world.py#L79), [DockWorld.__init__](../echo4/world.py#L112), [DockWorld.reset](../echo4/world.py#L131), [DockWorld.advance](../echo4/world.py#L136), [DockWorld.balanced](../echo4/world.py#L148) |
| [echo_arc/__init__.py](../echo_arc/__init__.py) | Importaciones, constantes o superficie de paquete | — |
| [echo_arc/agent.py](../echo_arc/agent.py) | [fingerprint](../echo_arc/agent.py#L22), [frame_hash](../echo_arc/agent.py#L30), [objects](../echo_arc/agent.py#L34), [Arc3Echo](../echo_arc/agent.py#L65), [Arc3EchoV2](../echo_arc/agent.py#L161), [Arc3EchoV3](../echo_arc/agent.py#L262), [Arc3EchoV3b](../echo_arc/agent.py#L348), [Arc3EchoV4](../echo_arc/agent.py#L449), [Arc3EchoV41](../echo_arc/agent.py#L652), [Arc3EchoV5](../echo_arc/agent.py#L768), [_components](../echo_arc/agent.py#L1084), [_components_raw](../echo_arc/agent.py#L1099), [Arc3EchoV51](../echo_arc/agent.py#L1128), [Arc3EchoV52](../echo_arc/agent.py#L1211), [Arc3EchoV53](../echo_arc/agent.py#L1298), [Arc3EchoV54](../echo_arc/agent.py#L1304), [Arc3EchoV55](../echo_arc/agent.py#L1460), [Arc3EchoV56](../echo_arc/agent.py#L1551), [Arc3EchoV57](../echo_arc/agent.py#L1690), [Arc3EchoV5NoExplore](../echo_arc/agent.py#L1814), [RandomAgent](../echo_arc/agent.py#L1819) | [Arc3Echo.__init__](../echo_arc/agent.py#L66), [Arc3Echo.actions_for](../echo_arc/agent.py#L86), [Arc3Echo.observe_state](../echo_arc/agent.py#L101), [Arc3Echo.choose](../echo_arc/agent.py#L128), [Arc3Echo.actions_for_state_fallback](../echo_arc/agent.py#L144), [Arc3Echo.learn](../echo_arc/agent.py#L148), [Arc3EchoV2.__init__](../echo_arc/agent.py#L173), [Arc3EchoV2.actions_for](../echo_arc/agent.py#L179), [Arc3EchoV2.observe_state](../echo_arc/agent.py#L211), [Arc3EchoV2.choose](../echo_arc/agent.py#L220), [Arc3EchoV2.learn](../echo_arc/agent.py#L248), [Arc3EchoV3.__init__](../echo_arc/agent.py#L273), [Arc3EchoV3.actions_for](../echo_arc/agent.py#L309), [Arc3EchoV3.observe_state](../echo_arc/agent.py#L337), [Arc3EchoV3b.__init__](../echo_arc/agent.py#L361), [Arc3EchoV3b.observe_state](../echo_arc/agent.py#L414), [Arc3EchoV3b.choose](../echo_arc/agent.py#L426), [Arc3EchoV4.__init__](../echo_arc/agent.py#L463), [Arc3EchoV4.observe_state](../echo_arc/agent.py#L523), [Arc3EchoV4.choose](../echo_arc/agent.py#L582), [Arc3EchoV4.learn](../echo_arc/agent.py#L621), [Arc3EchoV41.__init__](../echo_arc/agent.py#L663), [Arc3EchoV41.observe_state](../echo_arc/agent.py#L725), [Arc3EchoV41.choose](../echo_arc/agent.py#L735), [Arc3EchoV5.__init__](../echo_arc/agent.py#L790), [Arc3EchoV5.observe_state](../echo_arc/agent.py#L903), [Arc3EchoV5.choose](../echo_arc/agent.py#L1049), [Arc3EchoV5.learn](../echo_arc/agent.py#L1070), [Arc3EchoV5.report](../echo_arc/agent.py#L1075), [Arc3EchoV51.__init__](../echo_arc/agent.py#L1139), [Arc3EchoV51.observe_state](../echo_arc/agent.py#L1144), [Arc3EchoV52.__init__](../echo_arc/agent.py#L1222), [Arc3EchoV52.learn](../echo_arc/agent.py#L1239), [Arc3EchoV52.observe_state](../echo_arc/agent.py#L1268), [Arc3EchoV52.choose](../echo_arc/agent.py#L1279), [Arc3EchoV54.__init__](../echo_arc/agent.py#L1316), [Arc3EchoV54.choose](../echo_arc/agent.py#L1425), [Arc3EchoV54.learn](../echo_arc/agent.py#L1450), [Arc3EchoV55.__init__](../echo_arc/agent.py#L1471), [Arc3EchoV55.observe_state](../echo_arc/agent.py#L1499), [Arc3EchoV55.keys_real](../echo_arc/agent.py#L1508), [Arc3EchoV55.choose](../echo_arc/agent.py#L1542), [Arc3EchoV56.__init__](../echo_arc/agent.py#L1563), [Arc3EchoV56.observe_state](../echo_arc/agent.py#L1578), [Arc3EchoV56.choose](../echo_arc/agent.py#L1651), [Arc3EchoV56.learn](../echo_arc/agent.py#L1665), [Arc3EchoV57.__init__](../echo_arc/agent.py#L1701), [Arc3EchoV57.observe_state](../echo_arc/agent.py#L1710), [Arc3EchoV57.choose](../echo_arc/agent.py#L1729), [Arc3EchoV57.learn](../echo_arc/agent.py#L1804), [RandomAgent.__init__](../echo_arc/agent.py#L1821), [RandomAgent.observe_state](../echo_arc/agent.py#L1825), [RandomAgent.choose](../echo_arc/agent.py#L1828), [RandomAgent.learn](../echo_arc/agent.py#L1832) |
| [echo_arc/consumer_observe.py](../echo_arc/consumer_observe.py) | [ConsumptionRecorder](../echo_arc/consumer_observe.py#L17), [source_site](../echo_arc/consumer_observe.py#L45), [traced_agent_class](../echo_arc/consumer_observe.py#L53), [play](../echo_arc/consumer_observe.py#L96), [assess](../echo_arc/consumer_observe.py#L119) | [ConsumptionRecorder.__init__](../echo_arc/consumer_observe.py#L18), [ConsumptionRecorder.capture](../echo_arc/consumer_observe.py#L27), [ConsumptionRecorder.write](../echo_arc/consumer_observe.py#L31), [ConsumptionRecorder.summary](../echo_arc/consumer_observe.py#L39) |
| [echo_arc/consumer_requests.py](../echo_arc/consumer_requests.py) | [public_features](../echo_arc/consumer_requests.py#L6), [public_read](../echo_arc/consumer_requests.py#L13), [public_outcome](../echo_arc/consumer_requests.py#L23), [evidence](../echo_arc/consumer_requests.py#L30), [compact_cases](../echo_arc/consumer_requests.py#L53), [requests](../echo_arc/consumer_requests.py#L65) | — |
| [echo_arc/consumption_evidence.py](../echo_arc/consumption_evidence.py) | [native_hold_sites](../echo_arc/consumption_evidence.py#L12), [assess_hold](../echo_arc/consumption_evidence.py#L37) | — |
| [echo_arc/context_requests.py](../echo_arc/context_requests.py) | [digest](../echo_arc/context_requests.py#L27), [count_many](../echo_arc/context_requests.py#L31), [count](../echo_arc/context_requests.py#L44), [compact](../echo_arc/context_requests.py#L48), [expand](../echo_arc/context_requests.py#L64), [sections](../echo_arc/context_requests.py#L78), [variant](../echo_arc/context_requests.py#L87), [bounded](../echo_arc/context_requests.py#L116), [requests](../echo_arc/context_requests.py#L137), [tokenizer_manifest](../echo_arc/context_requests.py#L141) | — |
| [echo_arc/context_tokenizer.py](../echo_arc/context_tokenizer.py) | [main](../echo_arc/context_tokenizer.py#L8) | — |
| [echo_arc/contrastive_evidence.py](../echo_arc/contrastive_evidence.py) | [Recorder](../echo_arc/contrastive_evidence.py#L17), [require_development](../echo_arc/contrastive_evidence.py#L34), [behavior_digest](../echo_arc/contrastive_evidence.py#L39), [align_steps](../echo_arc/contrastive_evidence.py#L44), [step](../echo_arc/contrastive_evidence.py#L54), [comparison](../echo_arc/contrastive_evidence.py#L70), [feedback](../echo_arc/contrastive_evidence.py#L105) | [Recorder.__init__](../echo_arc/contrastive_evidence.py#L18), [Recorder.write](../echo_arc/contrastive_evidence.py#L22), [Recorder.summary](../echo_arc/contrastive_evidence.py#L30) |
| [echo_arc/contrastive_grammar.py](../echo_arc/contrastive_grammar.py) | [witnesses](../echo_arc/contrastive_grammar.py#L14), [build_schema](../echo_arc/contrastive_grammar.py#L31), [choices](../echo_arc/contrastive_grammar.py#L59), [validate_answer](../echo_arc/contrastive_grammar.py#L77), [Grammar](../echo_arc/contrastive_grammar.py#L91) | [Grammar.__init__](../echo_arc/contrastive_grammar.py#L92), [Grammar.allowed](../echo_arc/contrastive_grammar.py#L111) |
| [echo_arc/contrastive_requests.py](../echo_arc/contrastive_requests.py) | [select](../echo_arc/contrastive_requests.py#L8), [cases](../echo_arc/contrastive_requests.py#L47), [requests](../echo_arc/contrastive_requests.py#L62) | — |
| [echo_arc/feasible_grammar.py](../echo_arc/feasible_grammar.py) | [canonical](../echo_arc/feasible_grammar.py#L11), [matches](../echo_arc/feasible_grammar.py#L15), [public_features](../echo_arc/feasible_grammar.py#L21), [build_schema](../echo_arc/feasible_grammar.py#L29), [choices](../echo_arc/feasible_grammar.py#L53), [validate_answer](../echo_arc/feasible_grammar.py#L70), [Grammar](../echo_arc/feasible_grammar.py#L84) | [Grammar.__init__](../echo_arc/feasible_grammar.py#L86), [Grammar.allowed](../echo_arc/feasible_grammar.py#L107) |
| [echo_arc/feasible_requests.py](../echo_arc/feasible_requests.py) | [select](../echo_arc/feasible_requests.py#L7), [requests](../echo_arc/feasible_requests.py#L20) | — |
| [echo_arc/local_patch.py](../echo_arc/local_patch.py) | [validate](../echo_arc/local_patch.py#L14), [append](../echo_arc/local_patch.py#L42), [features](../echo_arc/local_patch.py#L49), [settings](../echo_arc/local_patch.py#L61), [agent_class](../echo_arc/local_patch.py#L71), [play](../echo_arc/local_patch.py#L135) | — |
| [echo_arc/local_patch_grammar.py](../echo_arc/local_patch_grammar.py) | [conditions](../echo_arc/local_patch_grammar.py#L7), [Grammar](../echo_arc/local_patch_grammar.py#L22) | [Grammar.__init__](../echo_arc/local_patch_grammar.py#L23) |
| [echo_arc/observe.py](../echo_arc/observe.py) | [branch_label](../echo_arc/observe.py#L24), [plain](../echo_arc/observe.py#L49), [snapshot](../echo_arc/observe.py#L64), [Journal](../echo_arc/observe.py#L76), [ObservedAgent](../echo_arc/observe.py#L99), [observed_play](../echo_arc/observe.py#L171), [run](../echo_arc/observe.py#L189), [main](../echo_arc/observe.py#L227) | [Journal.__init__](../echo_arc/observe.py#L77), [Journal.write](../echo_arc/observe.py#L85), [Journal.close](../echo_arc/observe.py#L95), [ObservedAgent.__init__](../echo_arc/observe.py#L101), [ObservedAgent.observe_state](../echo_arc/observe.py#L114), [ObservedAgent.choose](../echo_arc/observe.py#L121), [ObservedAgent.learn](../echo_arc/observe.py#L162) |
| [echo_arc/parameter_first_grammar.py](../echo_arc/parameter_first_grammar.py) | [Grammar](../echo_arc/parameter_first_grammar.py#L12) | [Grammar.__init__](../echo_arc/parameter_first_grammar.py#L13) |
| [echo_arc/precise_observe.py](../echo_arc/precise_observe.py) | [PreciseRecorder](../echo_arc/precise_observe.py#L7), [PreciseObservedAgent](../echo_arc/precise_observe.py#L24) | [PreciseRecorder.capture](../echo_arc/precise_observe.py#L8), [PreciseRecorder.write](../echo_arc/precise_observe.py#L12), [PreciseObservedAgent.choose](../echo_arc/precise_observe.py#L25) |
| [echo_arc/precise_patch.py](../echo_arc/precise_patch.py) | [validate](../echo_arc/precise_patch.py#L15), [features](../echo_arc/precise_patch.py#L45), [apply_cooldown](../echo_arc/precise_patch.py#L56), [agent_class](../echo_arc/precise_patch.py#L61) | — |
| [echo_arc/precise_patch_grammar.py](../echo_arc/precise_patch_grammar.py) | [conditions](../echo_arc/precise_patch_grammar.py#L7), [Grammar](../echo_arc/precise_patch_grammar.py#L28) | [Grammar.__init__](../echo_arc/precise_patch_grammar.py#L29) |
| [echo_arc/repair_diagnostics.py](../echo_arc/repair_diagnostics.py) | [compact](../echo_arc/repair_diagnostics.py#L9), [DiagnosticRecorder](../echo_arc/repair_diagnostics.py#L13), [applicability](../echo_arc/repair_diagnostics.py#L66), [feedback](../echo_arc/repair_diagnostics.py#L99), [focus_for](../echo_arc/repair_diagnostics.py#L114), [select_evidence](../echo_arc/repair_diagnostics.py#L123) | [DiagnosticRecorder.__init__](../echo_arc/repair_diagnostics.py#L14), [DiagnosticRecorder.write](../echo_arc/repair_diagnostics.py#L21), [DiagnosticRecorder.summary](../echo_arc/repair_diagnostics.py#L60) |
| [echo_arc/repair_evidence.py](../echo_arc/repair_evidence.py) | [Recorder](../echo_arc/repair_evidence.py#L7) | [Recorder.__init__](../echo_arc/repair_evidence.py#L8), [Recorder.bind_actor](../echo_arc/repair_evidence.py#L19), [Recorder.name](../echo_arc/repair_evidence.py#L22), [Recorder.view](../echo_arc/repair_evidence.py#L27), [Recorder.write](../echo_arc/repair_evidence.py#L42), [Recorder.episodes](../echo_arc/repair_evidence.py#L71), [Recorder.close](../echo_arc/repair_evidence.py#L79) |
| [echo_arc/repair_loop_grammar.py](../echo_arc/repair_loop_grammar.py) | [Grammar](../echo_arc/repair_loop_grammar.py#L7) | — |
| [echo_arc/repair_loop_observe.py](../echo_arc/repair_loop_observe.py) | [Recorder](../echo_arc/repair_loop_observe.py#L10) | — |
| [echo_arc/repair_loop_requests.py](../echo_arc/repair_loop_requests.py) | [feedback](../echo_arc/repair_loop_requests.py#L7), [evidence](../echo_arc/repair_loop_requests.py#L14), [requests](../echo_arc/repair_loop_requests.py#L42) | — |
| [echo_arc/runner.py](../echo_arc/runner.py) | [agent_class](../echo_arc/runner.py#L24), [official_game_score](../echo_arc/runner.py#L33), [_act](../echo_arc/runner.py#L44), [play](../echo_arc/runner.py#L53), [seed_for](../echo_arc/runner.py#L104), [run_offline](../echo_arc/runner.py#L110), [run_competition](../echo_arc/runner.py#L131), [main](../echo_arc/runner.py#L146) | — |
| [echo_arc/stale_transition.py](../echo_arc/stale_transition.py) | [revise](../echo_arc/stale_transition.py#L20), [agent_class](../echo_arc/stale_transition.py#L42) | — |
| [echo_arc/strategy.py](../echo_arc/strategy.py) | [validate](../echo_arc/strategy.py#L16), [parse](../echo_arc/strategy.py#L45), [digest](../echo_arc/strategy.py#L61), [settings](../echo_arc/strategy.py#L65), [agent_class](../echo_arc/strategy.py#L74) | — |
| [echo_arc/strategy_grammar.py](../echo_arc/strategy_grammar.py) | [segments](../echo_arc/strategy_grammar.py#L12), [Grammar](../echo_arc/strategy_grammar.py#L36) | [Grammar.__init__](../echo_arc/strategy_grammar.py#L38), [Grammar.closure](../echo_arc/strategy_grammar.py#L45), [Grammar.states](../echo_arc/strategy_grammar.py#L61), [Grammar.allowed](../echo_arc/strategy_grammar.py#L82) |
| [echo_arc/temporal_agent.py](../echo_arc/temporal_agent.py) | [Arc3EchoV58](../echo_arc/temporal_agent.py#L10), [Arc3EchoV58NoOrder](../echo_arc/temporal_agent.py#L300), [Arc3EchoV58NoCount](../echo_arc/temporal_agent.py#L304), [Arc3EchoV58NoMemory](../echo_arc/temporal_agent.py#L308) | [Arc3EchoV58.__init__](../echo_arc/temporal_agent.py#L17), [Arc3EchoV58.observe_state](../echo_arc/temporal_agent.py#L89), [Arc3EchoV58.choose](../echo_arc/temporal_agent.py#L220), [Arc3EchoV58.learn](../echo_arc/temporal_agent.py#L248), [Arc3EchoV58.report](../echo_arc/temporal_agent.py#L296) |
| [echo_arc/temporal_audit.py](../echo_arc/temporal_audit.py) | [verify_row](../echo_arc/temporal_audit.py#L11), [replay_row](../echo_arc/temporal_audit.py#L59), [main](../echo_arc/temporal_audit.py#L86) | — |
| [echo_arc/temporal_bench.py](../echo_arc/temporal_bench.py) | [_gym_env](../echo_arc/temporal_bench.py#L21), [measure](../echo_arc/temporal_bench.py#L36), [summarize](../echo_arc/temporal_bench.py#L81), [main](../echo_arc/temporal_bench.py#L103) | — |
| [echo_arc/temporal_memory.py](../echo_arc/temporal_memory.py) | [OrderMemory](../echo_arc/temporal_memory.py#L5), [CountMemory](../echo_arc/temporal_memory.py#L49) | [OrderMemory.__init__](../echo_arc/temporal_memory.py#L9), [OrderMemory.reset](../echo_arc/temporal_memory.py#L14), [OrderMemory.enter](../echo_arc/temporal_memory.py#L18), [OrderMemory.candidates](../echo_arc/temporal_memory.py#L37), [OrderMemory.report](../echo_arc/temporal_memory.py#L42), [CountMemory.__init__](../echo_arc/temporal_memory.py#L54), [CountMemory.reset](../echo_arc/temporal_memory.py#L59), [CountMemory.position](../echo_arc/temporal_memory.py#L66), [CountMemory.threshold](../echo_arc/temporal_memory.py#L99), [CountMemory.report](../echo_arc/temporal_memory.py#L104) |
| [echo_arc/temporal_policy.py](../echo_arc/temporal_policy.py) | [agent_class](../echo_arc/temporal_policy.py#L28), [play](../echo_arc/temporal_policy.py#L114) | — |
| [echo_arc/temporal_policy_grammar.py](../echo_arc/temporal_policy_grammar.py) | [segments](../echo_arc/temporal_policy_grammar.py#L7), [Grammar](../echo_arc/temporal_policy_grammar.py#L29) | [Grammar.__init__](../echo_arc/temporal_policy_grammar.py#L30) |
| [echo_arc/temporal_runner.py](../echo_arc/temporal_runner.py) | [agent_class](../echo_arc/temporal_runner.py#L13), [play](../echo_arc/temporal_runner.py#L17) | — |
| [echo_arc/transition_evidence.py](../echo_arc/transition_evidence.py) | [Recorder](../echo_arc/transition_evidence.py#L9) | [Recorder.__init__](../echo_arc/transition_evidence.py#L10), [Recorder.write](../echo_arc/transition_evidence.py#L14), [Recorder.summary](../echo_arc/transition_evidence.py#L20) |
| [echo_arc/transition_observe.py](../echo_arc/transition_observe.py) | [TransitionRecorder](../echo_arc/transition_observe.py#L5) | [TransitionRecorder.__init__](../echo_arc/transition_observe.py#L6), [TransitionRecorder.write](../echo_arc/transition_observe.py#L12), [TransitionRecorder.summary](../echo_arc/transition_observe.py#L34) |
| [seed/__init__.py](../seed/__init__.py) | Importaciones, constantes o superficie de paquete | — |
| [seed/arc3gym.py](../seed/arc3gym.py) | [Level](../seed/arc3gym.py#L42), [_open_cells](../seed/arc3gym.py#L244), [_dist](../seed/arc3gym.py#L250), [make_level](../seed/arc3gym.py#L265), [Game](../seed/arc3gym.py#L334), [Obs](../seed/arc3gym.py#L427), [GymEnv](../seed/arc3gym.py#L433), [_solution_actions](../seed/arc3gym.py#L481), [validate](../seed/arc3gym.py#L496), [_Random](../seed/arc3gym.py#L516), [run](../seed/arc3gym.py#L532), [main](../seed/arc3gym.py#L555) | [Level.__init__](../seed/arc3gym.py#L45), [Level.init](../seed/arc3gym.py#L55), [Level.free](../seed/arc3gym.py#L62), [Level.step](../seed/arc3gym.py#L66), [Level.won](../seed/arc3gym.py#L151), [Level.actions](../seed/arc3gym.py#L158), [Level.solve](../seed/arc3gym.py#L217), [Game.__init__](../seed/arc3gym.py#L335), [Game.arrow_rect](../seed/arc3gym.py#L358), [Game.render](../seed/arc3gym.py#L362), [Game.target_at](../seed/arc3gym.py#L406), [Obs.__init__](../seed/arc3gym.py#L428), [GymEnv.__init__](../seed/arc3gym.py#L436), [GymEnv.reset](../seed/arc3gym.py#L452), [GymEnv.step](../seed/arc3gym.py#L459), [_Random.__init__](../seed/arc3gym.py#L517), [_Random.observe_state](../seed/arc3gym.py#L522), [_Random.choose](../seed/arc3gym.py#L525), [_Random.learn](../seed/arc3gym.py#L528) |
| [seed/arc_capabilities.py](../seed/arc_capabilities.py) | [rotate](../seed/arc_capabilities.py#L34), [example](../seed/arc_capabilities.py#L38), [suite](../seed/arc_capabilities.py#L69), [library_for](../seed/arc_capabilities.py#L81), [solve_public](../seed/arc_capabilities.py#L99), [compare](../seed/arc_capabilities.py#L117), [run](../seed/arc_capabilities.py#L142), [audit](../seed/arc_capabilities.py#L188) | — |
| [seed/arc_comparison.py](../seed/arc_comparison.py) | [require](../seed/arc_comparison.py#L42), [now](../seed/arc_comparison.py#L47), [read](../seed/arc_comparison.py#L51), [file_sha](../seed/arc_comparison.py#L55), [save](../seed/arc_comparison.py#L59), [freeze_guard](../seed/arc_comparison.py#L70), [delta](../seed/arc_comparison.py#L85), [index_rows](../seed/arc_comparison.py#L94), [compare_grid_rows](../seed/arc_comparison.py#L100), [historical_baseline](../seed/arc_comparison.py#L127), [arc_totals](../seed/arc_comparison.py#L167), [compare_arc_rows](../seed/arc_comparison.py#L188), [prepare](../seed/arc_comparison.py#L201), [prepared](../seed/arc_comparison.py#L227), [candidate_available](../seed/arc_comparison.py#L242), [validate_release](../seed/arc_comparison.py#L246), [freeze_candidate](../seed/arc_comparison.py#L260), [arc_one](../seed/arc_comparison.py#L290), [run_arc](../seed/arc_comparison.py#L312), [snapshot](../seed/arc_comparison.py#L357), [main](../seed/arc_comparison.py#L371) | — |
| [seed/capacity_media.py](../seed/capacity_media.py) | [trace_operation](../seed/capacity_media.py#L29), [evidence](../seed/capacity_media.py#L51), [charts](../seed/capacity_media.py#L84), [font](../seed/capacity_media.py#L153), [grid](../seed/capacity_media.py#L164), [tree_frame](../seed/capacity_media.py#L173), [animation](../seed/capacity_media.py#L228), [needs_render](../seed/capacity_media.py#L239), [page](../seed/capacity_media.py#L245), [build](../seed/capacity_media.py#L289) | — |
| [seed/capacity_study.py](../seed/capacity_study.py) | [require](../seed/capacity_study.py#L41), [now](../seed/capacity_study.py#L46), [status](../seed/capacity_study.py#L53), [check_pair](../seed/capacity_study.py#L59), [paired](../seed/capacity_study.py#L66), [checked_task](../seed/capacity_study.py#L73), [fit](../seed/capacity_study.py#L80), [synthetic](../seed/capacity_study.py#L94), [import_controls](../seed/capacity_study.py#L113), [prepare](../seed/capacity_study.py#L132), [integrity](../seed/capacity_study.py#L163), [probe_finished](../seed/capacity_study.py#L176), [init_worker](../seed/capacity_study.py#L182), [measure](../seed/capacity_study.py#L190), [report](../seed/capacity_study.py#L205), [run](../seed/capacity_study.py#L254), [main](../seed/capacity_study.py#L281) | — |
| [seed/dreams.py](../seed/dreams.py) | [primitive_names](../seed/dreams.py#L27), [pad](../seed/dreams.py#L31), [_random_step](../seed/dreams.py#L37), [_level](../seed/dreams.py#L50), [_init](../seed/dreams.py#L54), [dream](../seed/dreams.py#L59), [main](../seed/dreams.py#L83) | — |
| [seed/dsl.py](../seed/dsl.py) | [G](../seed/dsl.py#L12), [palette](../seed/dsl.py#L19), [majority](../seed/dsl.py#L23), [rot90](../seed/dsl.py#L29), [rot180](../seed/dsl.py#L30), [rot270](../seed/dsl.py#L31), [flipud](../seed/dsl.py#L32), [fliplr](../seed/dsl.py#L33), [transpose](../seed/dsl.py#L34), [crop](../seed/dsl.py#L37), [_scale](../seed/dsl.py#L46), [_down](../seed/dsl.py#L49), [up2](../seed/dsl.py#L55), [up3](../seed/dsl.py#L56), [down2](../seed/dsl.py#L57), [down3](../seed/dsl.py#L58), [tile2x2](../seed/dsl.py#L59), [tile1x2](../seed/dsl.py#L60), [tile2x1](../seed/dsl.py#L61), [mirror_h](../seed/dsl.py#L62), [mirror_v](../seed/dsl.py#L63), [_halves](../seed/dsl.py#L66), [left_half](../seed/dsl.py#L78), [right_half](../seed/dsl.py#L79), [top_half](../seed/dsl.py#L80), [bottom_half](../seed/dsl.py#L81), [sym_h](../seed/dsl.py#L84), [sym_v](../seed/dsl.py#L89), [dedupe_rows](../seed/dsl.py#L93), [dedupe_cols](../seed/dsl.py#L98), [objects](../seed/dsl.py#L103), [_extract](../seed/dsl.py#L126), [largest_object](../seed/dsl.py#L135), [smallest_object](../seed/dsl.py#L142), [_gravity](../seed/dsl.py#L149), [gravity_down](../seed/dsl.py#L158), [gravity_up](../seed/dsl.py#L159), [gravity_right](../seed/dsl.py#L160), [gravity_left](../seed/dsl.py#L161), [_logic](../seed/dsl.py#L166), [keep_color](../seed/dsl.py#L175), [remove_color](../seed/dsl.py#L181), [fill_bg](../seed/dsl.py#L187), [fill_enclosed](../seed/dsl.py#L190), [recolor](../seed/dsl.py#L207), [swap](../seed/dsl.py#L213), [_objects_any](../seed/dsl.py#L221), [_bbox](../seed/dsl.py#L244), [_crop_box](../seed/dsl.py#L249), [crop_largest_any](../seed/dsl.py#L254), [crop_smallest_any](../seed/dsl.py#L261), [crop_unique_color_object](../seed/dsl.py#L268), [crop_odd_shape](../seed/dsl.py#L278), [_keep](../seed/dsl.py#L292), [keep_largest](../seed/dsl.py#L297), [remove_largest](../seed/dsl.py#L304), [denoise](../seed/dsl.py#L312), [recolor_largest](../seed/dsl.py#L321), [recolor_smallest](../seed/dsl.py#L329), [fill_object_boxes](../seed/dsl.py#L337), [halo](../seed/dsl.py#L353), [connect_pairs](../seed/dsl.py#L365), [_rays](../seed/dsl.py#L391), [rays_h](../seed/dsl.py#L407), [rays_v](../seed/dsl.py#L408), [rays_cross](../seed/dsl.py#L409), [rays_diag](../seed/dsl.py#L410), [fill_periodic](../seed/dsl.py#L413), [sym_rot180](../seed/dsl.py#L438), [sym_diag](../seed/dsl.py#L442), [self_kron](../seed/dsl.py#L449), [majority_recolor](../seed/dsl.py#L458), [_slide](../seed/dsl.py#L475), [slide_down](../seed/dsl.py#L504), [slide_up](../seed/dsl.py#L505), [slide_left](../seed/dsl.py#L506), [slide_right](../seed/dsl.py#L507), [stamp_template](../seed/dsl.py#L510), [_flip_each](../seed/dsl.py#L531), [flip_each_lr](../seed/dsl.py#L547), [flip_each_ud](../seed/dsl.py#L548), [frame](../seed/dsl.py#L551), [invert](../seed/dsl.py#L562), [outline](../seed/dsl.py#L567), [fill_holes_same](../seed/dsl.py#L582), [count_to_row](../seed/dsl.py#L608), [crop_common_shape](../seed/dsl.py#L617), [_sections](../seed/dsl.py#L632), [_overlay](../seed/dsl.py#L652), [sections_or](../seed/dsl.py#L657), [sections_and](../seed/dsl.py#L658), [sections_xor](../seed/dsl.py#L659), [sections_stack](../seed/dsl.py#L662), [crop_densest_section](../seed/dsl.py#L674), [crop_odd_section](../seed/dsl.py#L679), [enable_s1](../seed/dsl.py#L707), [enable_s1b](../seed/dsl.py#L717), [enable_s2v](../seed/dsl.py#L728), [apply_step](../seed/dsl.py#L739), [primitive_count](../seed/dsl.py#L748) | — |
| [seed/echo45_completion.py](../seed/echo45_completion.py) | [outcome](../seed/echo45_completion.py#L24), [optional](../seed/echo45_completion.py#L33), [write_report](../seed/echo45_completion.py#L37), [notify](../seed/echo45_completion.py#L69), [archive_interrupted_journals](../seed/echo45_completion.py#L83), [publish_candidate](../seed/echo45_completion.py#L99), [run](../seed/echo45_completion.py#L119) | — |
| [seed/final_arc.py](../seed/final_arc.py) | [Counter](../seed/final_arc.py#L5), [accounting](../seed/final_arc.py#L29), [protocol_check](../seed/final_arc.py#L56), [one](../seed/final_arc.py#L75) | [Counter.__init__](../seed/final_arc.py#L6), [Counter.reset](../seed/final_arc.py#L10), [Counter.step](../seed/final_arc.py#L21) |
| [seed/final_audit_recovery.py](../seed/final_audit_recovery.py) | [now](../seed/final_audit_recovery.py#L21), [source_hashes](../seed/final_audit_recovery.py#L25), [measured_hashes](../seed/final_audit_recovery.py#L29), [prepare](../seed/final_audit_recovery.py#L37), [integrity](../seed/final_audit_recovery.py#L57), [canonical_json](../seed/final_audit_recovery.py#L65), [compare](../seed/final_audit_recovery.py#L69), [grid](../seed/final_audit_recovery.py#L75), [arc](../seed/final_audit_recovery.py#L90), [close](../seed/final_audit_recovery.py#L125), [watch](../seed/final_audit_recovery.py#L150) | — |
| [seed/final_campaign.py](../seed/final_campaign.py) | [read](../seed/final_campaign.py#L29), [save](../seed/final_campaign.py#L33), [now](../seed/final_campaign.py#L40), [hash_file](../seed/final_campaign.py#L44), [corpus_metadata](../seed/final_campaign.py#L48), [sources](../seed/final_campaign.py#L66), [s6_result](../seed/final_campaign.py#L86), [arc_runtime](../seed/final_campaign.py#L102), [profile](../seed/final_campaign.py#L113), [integrity](../seed/final_campaign.py#L127), [prepare](../seed/final_campaign.py#L133), [measure_grid](../seed/final_campaign.py#L148), [measure_arc](../seed/final_campaign.py#L180), [arc_stage](../seed/final_campaign.py#L215), [exam](../seed/final_campaign.py#L222), [audit](../seed/final_campaign.py#L237), [publish](../seed/final_campaign.py#L258), [harness_hashes](../seed/final_campaign.py#L275), [development](../seed/final_campaign.py#L281), [watch](../seed/final_campaign.py#L308) | — |
| [seed/final_eval.py](../seed/final_eval.py) | [digest](../seed/final_eval.py#L12), [solver_input](../seed/final_eval.py#L16), [judge](../seed/final_eval.py#L21), [solve_one](../seed/final_eval.py#L28), [learned_state](../seed/final_eval.py#L43), [provenance_audit](../seed/final_eval.py#L49) | — |
| [seed/game_selfimprove.py](../seed/game_selfimprove.py) | [canonical](../seed/game_selfimprove.py#L30), [sha](../seed/game_selfimprove.py#L34), [atomic](../seed/game_selfimprove.py#L38), [hashes](../seed/game_selfimprove.py#L46), [integrity](../seed/game_selfimprove.py#L50), [events](../seed/game_selfimprove.py#L57), [journal](../seed/game_selfimprove.py#L70), [GameDeadline](../seed/game_selfimprove.py#L81), [worker_init](../seed/game_selfimprove.py#L85), [play_one](../seed/game_selfimprove.py#L93), [measure](../seed/game_selfimprove.py#L113), [public_rows](../seed/game_selfimprove.py#L143), [feedback_rows](../seed/game_selfimprove.py#L151), [reconstruct](../seed/game_selfimprove.py#L160), [requests](../seed/game_selfimprove.py#L174), [hf_proposer](../seed/game_selfimprove.py#L217), [baseline](../seed/game_selfimprove.py#L245), [run](../seed/game_selfimprove.py#L260), [export](../seed/game_selfimprove.py#L332), [main](../seed/game_selfimprove.py#L352) | — |
| [seed/game_selfimprove_b1.py](../seed/game_selfimprove_b1.py) | [worker_init](../seed/game_selfimprove_b1.py#L19), [play_one](../seed/game_selfimprove_b1.py#L23), [requests](../seed/game_selfimprove_b1.py#L27), [baseline](../seed/game_selfimprove_b1.py#L56), [hf_proposer](../seed/game_selfimprove_b1.py#L70), [__getattr__](../seed/game_selfimprove_b1.py#L111) | — |
| [seed/game_selfimprove_b2.py](../seed/game_selfimprove_b2.py) | [worker_init](../seed/game_selfimprove_b2.py#L19), [play_one](../seed/game_selfimprove_b2.py#L23), [requests](../seed/game_selfimprove_b2.py#L27), [baseline](../seed/game_selfimprove_b2.py#L53), [hf_proposer](../seed/game_selfimprove_b2.py#L67), [__getattr__](../seed/game_selfimprove_b2.py#L115) | — |
| [seed/game_selfimprove_b3.py](../seed/game_selfimprove_b3.py) | [hashes](../seed/game_selfimprove_b3.py#L39), [integrity](../seed/game_selfimprove_b3.py#L43), [configuration](../seed/game_selfimprove_b3.py#L52), [prepare](../seed/game_selfimprove_b3.py#L60), [worker_init](../seed/game_selfimprove_b3.py#L77), [accounting](../seed/game_selfimprove_b3.py#L88), [play_one](../seed/game_selfimprove_b3.py#L98), [measure](../seed/game_selfimprove_b3.py#L131), [no_regressions](../seed/game_selfimprove_b3.py#L163), [public_rows](../seed/game_selfimprove_b3.py#L169), [reconstruct](../seed/game_selfimprove_b3.py#L189), [unfiltered](../seed/game_selfimprove_b3.py#L203), [requests](../seed/game_selfimprove_b3.py#L211), [arm_status](../seed/game_selfimprove_b3.py#L252), [verify_round](../seed/game_selfimprove_b3.py#L257), [run](../seed/game_selfimprove_b3.py#L305), [export](../seed/game_selfimprove_b3.py#L371), [audit_training](../seed/game_selfimprove_b3.py#L386) | — |
| [seed/game_selfimprove_b4.py](../seed/game_selfimprove_b4.py) | [config](../seed/game_selfimprove_b4.py#L36), [hashes](../seed/game_selfimprove_b4.py#L45), [integrity](../seed/game_selfimprove_b4.py#L49), [prepare](../seed/game_selfimprove_b4.py#L57), [strategy](../seed/game_selfimprove_b4.py#L73), [Execution](../seed/game_selfimprove_b4.py#L78), [play_one](../seed/game_selfimprove_b4.py#L113), [public_rows](../seed/game_selfimprove_b4.py#L162), [counterexamples](../seed/game_selfimprove_b4.py#L170), [reconstruct](../seed/game_selfimprove_b4.py#L180), [episode_pattern](../seed/game_selfimprove_b4.py#L196), [requests](../seed/game_selfimprove_b4.py#L202), [status](../seed/game_selfimprove_b4.py#L250), [verify](../seed/game_selfimprove_b4.py#L254), [round_run](../seed/game_selfimprove_b4.py#L302), [pilot_report](../seed/game_selfimprove_b4.py#L332), [export](../seed/game_selfimprove_b4.py#L357), [run](../seed/game_selfimprove_b4.py#L374) | [Execution.validate](../seed/game_selfimprove_b4.py#L80), [Execution.digest](../seed/game_selfimprove_b4.py#L87), [Execution.play](../seed/game_selfimprove_b4.py#L91) |
| [seed/game_selfimprove_b5.py](../seed/game_selfimprove_b5.py) | [strategy](../seed/game_selfimprove_b5.py#L32), [config](../seed/game_selfimprove_b5.py#L38), [hashes](../seed/game_selfimprove_b5.py#L53), [integrity](../seed/game_selfimprove_b5.py#L57), [prepare](../seed/game_selfimprove_b5.py#L66), [status](../seed/game_selfimprove_b5.py#L82), [requests](../seed/game_selfimprove_b5.py#L92), [baseline](../seed/game_selfimprove_b5.py#L107), [verify](../seed/game_selfimprove_b5.py#L116), [generator](../seed/game_selfimprove_b5.py#L147), [pilot](../seed/game_selfimprove_b5.py#L154), [reconstruct](../seed/game_selfimprove_b5.py#L203), [raw_program](../seed/game_selfimprove_b5.py#L219), [raw_step](../seed/game_selfimprove_b5.py#L227), [full_campaign](../seed/game_selfimprove_b5.py#L249), [publish](../seed/game_selfimprove_b5.py#L298), [follow](../seed/game_selfimprove_b5.py#L318) | — |
| [seed/gym.py](../seed/gym.py) | [_guard](../seed/gym.py#L19), [catalogue](../seed/gym.py#L27), [split](../seed/gym.py#L36), [load](../seed/gym.py#L43) | — |
| [seed/intuition.py](../seed/intuition.py) | [onehot](../seed/intuition.py#L22), [build_torch](../seed/intuition.py#L32), [train](../seed/intuition.py#L53), [_conv](../seed/intuition.py#L99), [Intuition](../seed/intuition.py#L111) | [Intuition.__init__](../seed/intuition.py#L112), [Intuition.probs](../seed/intuition.py#L117) |
| [seed/kenyon_arc1.py](../seed/kenyon_arc1.py) | [digest](../seed/kenyon_arc1.py#L41), [read](../seed/kenyon_arc1.py#L45), [file_hash](../seed/kenyon_arc1.py#L49), [save](../seed/kenyon_arc1.py#L53), [status](../seed/kenyon_arc1.py#L64), [configuration](../seed/kenyon_arc1.py#L70), [integrity](../seed/kenyon_arc1.py#L82), [prepare](../seed/kenyon_arc1.py#L94), [fit_guides](../seed/kenyon_arc1.py#L122), [guide_info](../seed/kenyon_arc1.py#L133), [init_worker](../seed/kenyon_arc1.py#L140), [MeasuredLibrary](../seed/kenyon_arc1.py#L147), [one](../seed/kenyon_arc1.py#L159), [verify_program](../seed/kenyon_arc1.py#L197), [stable](../seed/kenyon_arc1.py#L208), [execute](../seed/kenyon_arc1.py#L212), [totals](../seed/kenyon_arc1.py#L237), [close](../seed/kenyon_arc1.py#L256), [main](../seed/kenyon_arc1.py#L285) | [MeasuredLibrary.__init__](../seed/kenyon_arc1.py#L148), [MeasuredLibrary.apply](../seed/kenyon_arc1.py#L153) |
| [seed/kenyon_bench.py](../seed/kenyon_bench.py) | [sample](../seed/kenyon_bench.py#L15), [run](../seed/kenyon_bench.py#L25) | — |
| [seed/kenyon_capacity.py](../seed/kenyon_capacity.py) | [SparsePrimitiveGuide](../seed/kenyon_capacity.py#L15) | [SparsePrimitiveGuide.__init__](../seed/kenyon_capacity.py#L18), [SparsePrimitiveGuide.features](../seed/kenyon_capacity.py#L29), [SparsePrimitiveGuide.observe](../seed/kenyon_capacity.py#L65), [SparsePrimitiveGuide.probs](../seed/kenyon_capacity.py#L88), [SparsePrimitiveGuide.guided_library](../seed/kenyon_capacity.py#L98) |
| [seed/learn.py](../seed/learn.py) | [task_grids](../seed/learn.py#L19), [distance](../seed/learn.py#L25), [Library](../seed/learn.py#L35), [solve](../seed/learn.py#L103), [_finish](../seed/learn.py#L139), [prior_from](../seed/learn.py#L154), [sleep](../seed/learn.py#L163), [_slotify](../seed/learn.py#L189), [sleep_parametric](../seed/learn.py#L201) | [Library.__init__](../seed/learn.py#L38), [Library.key](../seed/learn.py#L44), [Library.step_cost](../seed/learn.py#L47), [Library.expand](../seed/learn.py#L57), [Library.apply](../seed/learn.py#L74), [Library.moves](../seed/learn.py#L79), [Library.sha](../seed/learn.py#L99) |
| [seed/refinement.py](../seed/refinement.py) | [transform](../seed/refinement.py#L21), [inverse](../seed/refinement.py#L27), [grid](../seed/refinement.py#L31), [solver_input](../seed/refinement.py#L39), [canonical_program](../seed/refinement.py#L49), [RefinementLibrary](../seed/refinement.py#L70), [execute](../seed/refinement.py#L123), [critique](../seed/refinement.py#L129), [quality](../seed/refinement.py#L144), [refinements](../seed/refinement.py#L151), [solve](../seed/refinement.py#L166) | [RefinementLibrary.moves](../seed/refinement.py#L72), [RefinementLibrary.apply](../seed/refinement.py#L84) |
| [seed/refinement_bench.py](../seed/refinement_bench.py) | [hashes](../seed/refinement_bench.py#L26), [configuration](../seed/refinement_bench.py#L30), [prepare](../seed/refinement_bench.py#L39), [integrity](../seed/refinement_bench.py#L55), [one](../seed/refinement_bench.py#L64), [run](../seed/refinement_bench.py#L87) | — |
| [seed/refinement_s2v_bench.py](../seed/refinement_s2v_bench.py) | [configuration](../seed/refinement_s2v_bench.py#L22), [hashes](../seed/refinement_s2v_bench.py#L26), [integrity](../seed/refinement_s2v_bench.py#L30), [prepare](../seed/refinement_s2v_bench.py#L41), [one](../seed/refinement_s2v_bench.py#L57), [run](../seed/refinement_s2v_bench.py#L71) | — |
| [seed/rsi1.py](../seed/rsi1.py) | [now](../seed/rsi1.py#L43), [canonical](../seed/rsi1.py#L47), [sha](../seed/rsi1.py#L51), [file_sha](../seed/rsi1.py#L55), [atomic](../seed/rsi1.py#L63), [status](../seed/rsi1.py#L70), [checked_program](../seed/rsi1.py#L76), [parse_reply](../seed/rsi1.py#L84), [execute](../seed/rsi1.py#L96), [Library](../seed/rsi1.py#L103), [public](../seed/rsi1.py#L110), [corpus](../seed/rsi1.py#L114), [state](../seed/rsi1.py#L132), [restore](../seed/rsi1.py#L136), [measure](../seed/rsi1.py#L140), [decision](../seed/rsi1.py#L164), [propose](../seed/rsi1.py#L171), [prompt_for](../seed/rsi1.py#L214), [attempt](../seed/rsi1.py#L227), [hashes](../seed/rsi1.py#L248), [prepare](../seed/rsi1.py#L252), [integrity](../seed/rsi1.py#L275), [checkpoint](../seed/rsi1.py#L284), [research](../seed/rsi1.py#L288), [run](../seed/rsi1.py#L303), [write_report](../seed/rsi1.py#L399), [main](../seed/rsi1.py#L435) | [Library.moves](../seed/rsi1.py#L105) |
| [seed/rsi1_queue.py](../seed/rsi1_queue.py) | [gate](../seed/rsi1_queue.py#L15), [wait](../seed/rsi1_queue.py#L33) | — |
| [seed/s6_capacity.py](../seed/s6_capacity.py) | [controls](../seed/s6_capacity.py#L28), [configuration](../seed/s6_capacity.py#L61), [sources](../seed/s6_capacity.py#L71), [runtime](../seed/s6_capacity.py#L75), [prepare](../seed/s6_capacity.py#L86), [integrity](../seed/s6_capacity.py#L104), [now](../seed/s6_capacity.py#L113), [status](../seed/s6_capacity.py#L117), [same_behavior](../seed/s6_capacity.py#L122), [result](../seed/s6_capacity.py#L126), [play_one](../seed/s6_capacity.py#L140), [measure](../seed/s6_capacity.py#L176), [diagnose](../seed/s6_capacity.py#L208), [run](../seed/s6_capacity.py#L230), [publish](../seed/s6_capacity.py#L289) | — |
| [seed/s6_followup_report.py](../seed/s6_followup_report.py) | [report](../seed/s6_followup_report.py#L14) | — |
| [seed/s6_precise_capacity.py](../seed/s6_precise_capacity.py) | [candidate](../seed/s6_precise_capacity.py#L31), [Execution](../seed/s6_precise_capacity.py#L35), [controls](../seed/s6_precise_capacity.py#L70), [configuration](../seed/s6_precise_capacity.py#L94), [sources](../seed/s6_precise_capacity.py#L103), [integrity](../seed/s6_precise_capacity.py#L108), [prepare](../seed/s6_precise_capacity.py#L117), [status](../seed/s6_precise_capacity.py#L134), [play_one](../seed/s6_precise_capacity.py#L140), [measure](../seed/s6_precise_capacity.py#L179), [run](../seed/s6_precise_capacity.py#L215), [publish](../seed/s6_precise_capacity.py#L267) | [Execution.validate](../seed/s6_precise_capacity.py#L37), [Execution.digest](../seed/s6_precise_capacity.py#L43), [Execution.play](../seed/s6_precise_capacity.py#L47) |
| [seed/s6_precise_exam.py](../seed/s6_precise_exam.py) | [play_one](../seed/s6_precise_exam.py#L16), [development_one](../seed/s6_precise_exam.py#L48), [checks](../seed/s6_precise_exam.py#L58), [audit_model_payloads](../seed/s6_precise_exam.py#L67), [audit_training](../seed/s6_precise_exam.py#L87), [run](../seed/s6_precise_exam.py#L147) | — |
| [seed/s6_prompt_pilot.py](../seed/s6_prompt_pilot.py) | [configuration](../seed/s6_prompt_pilot.py#L30), [digests](../seed/s6_prompt_pilot.py#L43), [integrity](../seed/s6_prompt_pilot.py#L47), [prepare](../seed/s6_prompt_pilot.py#L57), [positive_gate](../seed/s6_prompt_pilot.py#L76), [requests](../seed/s6_prompt_pilot.py#L87), [status](../seed/s6_prompt_pilot.py#L114), [verify](../seed/s6_prompt_pilot.py#L120), [run](../seed/s6_prompt_pilot.py#L147), [follow](../seed/s6_prompt_pilot.py#L199) | — |
| [seed/s6_transition_capacity.py](../seed/s6_transition_capacity.py) | [strategy](../seed/s6_transition_capacity.py#L23), [Execution](../seed/s6_transition_capacity.py#L26), [controls](../seed/s6_transition_capacity.py#L39), [profile](../seed/s6_transition_capacity.py#L47), [integrity](../seed/s6_transition_capacity.py#L54), [status](../seed/s6_transition_capacity.py#L60), [play_one](../seed/s6_transition_capacity.py#L64), [run](../seed/s6_transition_capacity.py#L98) | [Execution.validate](../seed/s6_transition_capacity.py#L28), [Execution.digest](../seed/s6_transition_capacity.py#L32) |
| [seed/s6b10.py](../seed/s6b10.py) | [config](../seed/s6b10.py#L30), [hashes](../seed/s6b10.py#L36), [profile](../seed/s6b10.py#L40), [integrity](../seed/s6b10.py#L47), [prepare](../seed/s6b10.py#L53), [status](../seed/s6b10.py#L68), [play_one](../seed/s6b10.py#L78), [phase_shape](../seed/s6b10.py#L90), [generator](../seed/s6b10.py#L95), [load_phase](../seed/s6b10.py#L102), [audit_model](../seed/s6b10.py#L106), [publish](../seed/s6b10.py#L121), [follow](../seed/s6b10.py#L139), [main](../seed/s6b10.py#L176) | — |
| [seed/s6b10_background.py](../seed/s6b10_background.py) | [now](../seed/s6b10_background.py#L21), [active_workers](../seed/s6b10_background.py#L25), [check_audit_cache](../seed/s6b10_background.py#L41), [check](../seed/s6b10_background.py#L57), [run](../seed/s6b10_background.py#L74), [start](../seed/s6b10_background.py#L93) | — |
| [seed/s6b10_diagnose.py](../seed/s6b10_diagnose.py) | [main](../seed/s6b10_diagnose.py#L14) | — |
| [seed/s6b10_exam.py](../seed/s6b10_exam.py) | [development_one](../seed/s6b10_exam.py#L7) | — |
| [seed/s6b10_report.py](../seed/s6b10_report.py) | [report_text](../seed/s6b10_report.py#L15), [publish](../seed/s6b10_report.py#L54) | — |
| [seed/s6b11.py](../seed/s6b11.py) | [atomic](../seed/s6b11.py#L39), [config](../seed/s6b11.py#L56), [hashes](../seed/s6b11.py#L70), [profile](../seed/s6b11.py#L74), [integrity](../seed/s6b11.py#L81), [prepare](../seed/s6b11.py#L88), [status](../seed/s6b11.py#L105), [reserve_games](../seed/s6b11.py#L111), [play_one](../seed/s6b11.py#L124), [measure](../seed/s6b11.py#L172), [verifier](../seed/s6b11.py#L211), [phase_shape](../seed/s6b11.py#L233), [generator](../seed/s6b11.py#L239), [audit_model](../seed/s6b11.py#L246), [promotion](../seed/s6b11.py#L253), [run_phase](../seed/s6b11.py#L266), [preflight](../seed/s6b11.py#L337), [publish](../seed/s6b11.py#L358), [follow](../seed/s6b11.py#L394), [main](../seed/s6b11.py#L432) | — |
| [seed/s6b11_background.py](../seed/s6b11_background.py) | [run](../seed/s6b11_background.py#L13), [start](../seed/s6b11_background.py#L27) | — |
| [seed/s6b11_background2.py](../seed/s6b11_background2.py) | [run](../seed/s6b11_background2.py#L13), [start](../seed/s6b11_background2.py#L27) | — |
| [seed/s6b11_exam.py](../seed/s6b11_exam.py) | [development_one](../seed/s6b11_exam.py#L10), [run](../seed/s6b11_exam.py#L19) | — |
| [seed/s6b11_recovery.py](../seed/s6b11_recovery.py) | [digest](../seed/s6b11_recovery.py#L21), [profile](../seed/s6b11_recovery.py#L25), [integrity](../seed/s6b11_recovery.py#L33), [prepare](../seed/s6b11_recovery.py#L39), [pack](../seed/s6b11_recovery.py#L58), [unpack](../seed/s6b11_recovery.py#L74), [package](../seed/s6b11_recovery.py#L81), [transport_call](../seed/s6b11_recovery.py#L104), [transport](../seed/s6b11_recovery.py#L116), [audit_transport](../seed/s6b11_recovery.py#L123), [generator](../seed/s6b11_recovery.py#L143), [audit_model](../seed/s6b11_recovery.py#L161), [audit_completed](../seed/s6b11_recovery.py#L167), [follow](../seed/s6b11_recovery.py#L175) | — |
| [seed/s6b11_recovery2.py](../seed/s6b11_recovery2.py) | [digest](../seed/s6b11_recovery2.py#L21), [profile](../seed/s6b11_recovery2.py#L25), [integrity](../seed/s6b11_recovery2.py#L35), [prepare](../seed/s6b11_recovery2.py#L41), [pack](../seed/s6b11_recovery2.py#L60), [unpack](../seed/s6b11_recovery2.py#L76), [package](../seed/s6b11_recovery2.py#L83), [transport_call](../seed/s6b11_recovery2.py#L106), [transport](../seed/s6b11_recovery2.py#L118), [audit_transport](../seed/s6b11_recovery2.py#L125), [generator](../seed/s6b11_recovery2.py#L145), [audit_model](../seed/s6b11_recovery2.py#L163), [audit_completed](../seed/s6b11_recovery2.py#L169), [follow](../seed/s6b11_recovery2.py#L177) | — |
| [seed/s6b12.py](../seed/s6b12.py) | [config](../seed/s6b12.py#L31), [hashes](../seed/s6b12.py#L40), [profile](../seed/s6b12.py#L44), [integrity](../seed/s6b12.py#L56), [prepare](../seed/s6b12.py#L63), [status](../seed/s6b12.py#L82), [play_one](../seed/s6b12.py#L94), [generator](../seed/s6b12.py#L109), [audit_model](../seed/s6b12.py#L117), [inherit_pilot](../seed/s6b12.py#L148), [publish](../seed/s6b12.py#L167), [follow](../seed/s6b12.py#L205), [main](../seed/s6b12.py#L248) | — |
| [seed/s6b12_background.py](../seed/s6b12_background.py) | [notify](../seed/s6b12_background.py#L14), [recoverable](../seed/s6b12_background.py#L33), [run](../seed/s6b12_background.py#L40), [start](../seed/s6b12_background.py#L63) | — |
| [seed/s6b12_exam.py](../seed/s6b12_exam.py) | [development_one](../seed/s6b12_exam.py#L9), [run](../seed/s6b12_exam.py#L20) | — |
| [seed/s6b12_recovery1.py](../seed/s6b12_recovery1.py) | [digest](../seed/s6b12_recovery1.py#L27), [preserved_paths](../seed/s6b12_recovery1.py#L31), [profile](../seed/s6b12_recovery1.py#L42), [integrity](../seed/s6b12_recovery1.py#L53), [prepare](../seed/s6b12_recovery1.py#L59), [transport](../seed/s6b12_recovery1.py#L88), [metadata](../seed/s6b12_recovery1.py#L100), [payload_for](../seed/s6b12_recovery1.py#L108), [ensure_prefix_replay](../seed/s6b12_recovery1.py#L118), [check_source](../seed/s6b12_recovery1.py#L132), [build_job](../seed/s6b12_recovery1.py#L142), [audit_transport](../seed/s6b12_recovery1.py#L190), [audit_model](../seed/s6b12_recovery1.py#L219), [propose](../seed/s6b12_recovery1.py#L232), [collect](../seed/s6b12_recovery1.py#L256), [generator](../seed/s6b12_recovery1.py#L264), [status](../seed/s6b12_recovery1.py#L268), [publish](../seed/s6b12_recovery1.py#L272), [audit_campaign](../seed/s6b12_recovery1.py#L299), [follow](../seed/s6b12_recovery1.py#L310), [run](../seed/s6b12_recovery1.py#L367), [start](../seed/s6b12_recovery1.py#L391), [main](../seed/s6b12_recovery1.py#L409) | — |
| [seed/s6b12_report.py](../seed/s6b12_report.py) | [optional](../seed/s6b12_report.py#L16), [completed_round](../seed/s6b12_report.py#L21), [update](../seed/s6b12_report.py#L29), [watch](../seed/s6b12_report.py#L132) | — |
| [seed/s6b6.py](../seed/s6b6.py) | [hashes](../seed/s6b6.py#L31), [config](../seed/s6b6.py#L35), [integrity](../seed/s6b6.py#L42), [status](../seed/s6b6.py#L50), [prepare](../seed/s6b6.py#L56), [play_one](../seed/s6b6.py#L71), [decision_sites](../seed/s6b6.py#L115), [requests](../seed/s6b6.py#L145), [generator](../seed/s6b6.py#L175), [run](../seed/s6b6.py#L182), [audit](../seed/s6b6.py#L214) | — |
| [seed/s6b7.py](../seed/s6b7.py) | [config](../seed/s6b7.py#L20), [hashes](../seed/s6b7.py#L27), [history](../seed/s6b7.py#L31), [integrity](../seed/s6b7.py#L35), [prepare](../seed/s6b7.py#L46), [public_feedback](../seed/s6b7.py#L66), [requests](../seed/s6b7.py#L78), [generator](../seed/s6b7.py#L94), [run](../seed/s6b7.py#L101), [audit](../seed/s6b7.py#L139) | — |
| [seed/s6b8.py](../seed/s6b8.py) | [config](../seed/s6b8.py#L35), [hashes](../seed/s6b8.py#L45), [integrity](../seed/s6b8.py#L49), [prepare](../seed/s6b8.py#L56), [now](../seed/s6b8.py#L71), [status](../seed/s6b8.py#L75), [play_one](../seed/s6b8.py#L81), [verifier](../seed/s6b8.py#L130), [requests](../seed/s6b8.py#L149), [generator](../seed/s6b8.py#L184), [preflight](../seed/s6b8.py#L191), [load_phase](../seed/s6b8.py#L205), [phase_shape](../seed/s6b8.py#L209), [run_phase](../seed/s6b8.py#L214), [raw_step](../seed/s6b8.py#L287), [audit_model](../seed/s6b8.py#L302), [publish](../seed/s6b8.py#L323), [follow](../seed/s6b8.py#L347), [main](../seed/s6b8.py#L384) | — |
| [seed/s6b8_cpu.py](../seed/s6b8_cpu.py) | [profile](../seed/s6b8_cpu.py#L30), [integrity](../seed/s6b8_cpu.py#L38), [hashes](../seed/s6b8_cpu.py#L43), [prepare](../seed/s6b8_cpu.py#L47), [status](../seed/s6b8_cpu.py#L71), [play_one](../seed/s6b8_cpu.py#L76), [generator](../seed/s6b8_cpu.py#L86), [load_phase](../seed/s6b8_cpu.py#L91), [audit_model](../seed/s6b8_cpu.py#L95), [publish](../seed/s6b8_cpu.py#L113), [follow](../seed/s6b8_cpu.py#L124), [main](../seed/s6b8_cpu.py#L158) | — |
| [seed/s6b8_cpuq8.py](../seed/s6b8_cpuq8.py) | [profile](../seed/s6b8_cpuq8.py#L30), [integrity](../seed/s6b8_cpuq8.py#L39), [hashes](../seed/s6b8_cpuq8.py#L44), [prepare](../seed/s6b8_cpuq8.py#L48), [status](../seed/s6b8_cpuq8.py#L72), [play_one](../seed/s6b8_cpuq8.py#L77), [generator](../seed/s6b8_cpuq8.py#L87), [load_phase](../seed/s6b8_cpuq8.py#L92), [audit_model](../seed/s6b8_cpuq8.py#L96), [publish](../seed/s6b8_cpuq8.py#L114), [follow](../seed/s6b8_cpuq8.py#L125), [main](../seed/s6b8_cpuq8.py#L160) | — |
| [seed/s6b8_exam.py](../seed/s6b8_exam.py) | [development_one](../seed/s6b8_exam.py#L11), [run](../seed/s6b8_exam.py#L22) | — |
| [seed/s6b8_recovery.py](../seed/s6b8_recovery.py) | [profile](../seed/s6b8_recovery.py#L18), [integrity](../seed/s6b8_recovery.py#L27), [prepare](../seed/s6b8_recovery.py#L32), [transport](../seed/s6b8_recovery.py#L46), [recovered_propose](../seed/s6b8_recovery.py#L52), [audit_model](../seed/s6b8_recovery.py#L98), [generator](../seed/s6b8_recovery.py#L109), [follow](../seed/s6b8_recovery.py#L118), [main](../seed/s6b8_recovery.py#L156) | — |
| [seed/s6b9.py](../seed/s6b9.py) | [config](../seed/s6b9.py#L35), [hashes](../seed/s6b9.py#L43), [profile](../seed/s6b9.py#L46), [integrity](../seed/s6b9.py#L53), [prepare](../seed/s6b9.py#L59), [status](../seed/s6b9.py#L69), [Execution](../seed/s6b9.py#L73), [play_one](../seed/s6b9.py#L83), [verifier](../seed/s6b9.py#L100), [phase_shape](../seed/s6b9.py#L110), [generator](../seed/s6b9.py#L115), [load_phase](../seed/s6b9.py#L120), [audit_model](../seed/s6b9.py#L123), [publish](../seed/s6b9.py#L136), [preflight](../seed/s6b9.py#L147), [follow](../seed/s6b9.py#L157), [main](../seed/s6b9.py#L184) | [Execution.play](../seed/s6b9.py#L75) |
| [seed/s6b9_exam.py](../seed/s6b9_exam.py) | [development_one](../seed/s6b9_exam.py#L9) | — |
| [seed/s6b9_report.py](../seed/s6b9_report.py) | [read](../seed/s6b9_report.py#L16), [conclusion](../seed/s6b9_report.py#L19), [publish](../seed/s6b9_report.py#L47), [main](../seed/s6b9_report.py#L69) | — |
| [seed/s6probe1.py](../seed/s6probe1.py) | [config](../seed/s6probe1.py#L51), [hashes](../seed/s6probe1.py#L64), [b12_closure](../seed/s6probe1.py#L68), [base_program](../seed/s6probe1.py#L92), [profile](../seed/s6probe1.py#L100), [integrity](../seed/s6probe1.py#L106), [prepare](../seed/s6probe1.py#L113), [status](../seed/s6probe1.py#L126), [play_one](../seed/s6probe1.py#L139), [_measure](../seed/s6probe1.py#L171), [passes_v3](../seed/s6probe1.py#L185), [effects](../seed/s6probe1.py#L190), [summarize](../seed/s6probe1.py#L201), [decisions](../seed/s6probe1.py#L210), [guard_mask](../seed/s6probe1.py#L232), [changed_mask](../seed/s6probe1.py#L241), [census](../seed/s6probe1.py#L267), [b12_soundness](../seed/s6probe1.py#L300), [known_positive](../seed/s6probe1.py#L317), [allocate](../seed/s6probe1.py#L327), [sample](../seed/s6probe1.py#L348), [select_pairs](../seed/s6probe1.py#L368), [_operator](../seed/s6probe1.py#L398), [pair_program](../seed/s6probe1.py#L402), [measure_base](../seed/s6probe1.py#L409), [evaluate](../seed/s6probe1.py#L423), [run](../seed/s6probe1.py#L441), [conclusion](../seed/s6probe1.py#L515), [report](../seed/s6probe1.py#L532), [wait_estimate](../seed/s6probe1.py#L554), [main](../seed/s6probe1.py#L577) | — |
| [seed/s6probe1_audit.py](../seed/s6probe1_audit.py) | [fingerprint](../seed/s6probe1_audit.py#L21), [integrity](../seed/s6probe1_audit.py#L28), [status](../seed/s6probe1_audit.py#L35), [original_rows](../seed/s6probe1_audit.py#L53), [inspect_original](../seed/s6probe1_audit.py#L65), [run](../seed/s6probe1_audit.py#L111) | — |
| [seed/s6probe1_audit_recovery1.py](../seed/s6probe1_audit_recovery1.py) | [profile](../seed/s6probe1_audit_recovery1.py#L12), [measure](../seed/s6probe1_audit_recovery1.py#L20), [atomic](../seed/s6probe1_audit_recovery1.py#L28), [main](../seed/s6probe1_audit_recovery1.py#L38) | — |
| [seed/s6probe2.py](../seed/s6probe2.py) | [config](../seed/s6probe2.py#L49), [hashes](../seed/s6probe2.py#L65), [probe1_closure](../seed/s6probe2.py#L69), [profile](../seed/s6probe2.py#L93), [integrity](../seed/s6probe2.py#L99), [prepare](../seed/s6probe2.py#L106), [status](../seed/s6probe2.py#L121), [hold_reads](../seed/s6probe2.py#L143), [plan](../seed/s6probe2.py#L157), [budget](../seed/s6probe2.py#L182), [specs](../seed/s6probe2.py#L194), [behavior](../seed/s6probe2.py#L198), [screen](../seed/s6probe2.py#L202), [full](../seed/s6probe2.py#L223), [probe1_control](../seed/s6probe2.py#L245), [frozen_plan](../seed/s6probe2.py#L256), [controls](../seed/s6probe2.py#L270), [run](../seed/s6probe2.py#L278), [_full_saved](../seed/s6probe2.py#L324), [p1_base](../seed/s6probe2.py#L334), [conclusion](../seed/s6probe2.py#L349), [report](../seed/s6probe2.py#L366), [main](../seed/s6probe2.py#L392) | — |
| [seed/s6probe2_calibrate.py](../seed/s6probe2_calibrate.py) | [main](../seed/s6probe2_calibrate.py#L10) | — |
| [seed/sandbox.py](../seed/sandbox.py) | [_path](../seed/sandbox.py#L31), [_chain](../seed/sandbox.py#L35), [load_library](../seed/sandbox.py#L44), [save_library](../seed/sandbox.py#L50), [level_of](../seed/sandbox.py#L60), [_set_level](../seed/sandbox.py#L64), [new](../seed/sandbox.py#L73), [clone](../seed/sandbox.py#L86), [_solve_one](../seed/sandbox.py#L102), [verified_programs](../seed/sandbox.py#L121), [train](../seed/sandbox.py#L130), [verify](../seed/sandbox.py#L174), [_run](../seed/sandbox.py#L200), [probe](../seed/sandbox.py#L207), [set_prior](../seed/sandbox.py#L225), [status](../seed/sandbox.py#L236), [main](../seed/sandbox.py#L243) | — |
| [seed/selfimprove.py](../seed/selfimprove.py) | [partition](../seed/selfimprove.py#L53), [protected_hashes](../seed/selfimprove.py#L58), [check_code](../seed/selfimprove.py#L63), [ProposalTimeout](../seed/selfimprove.py#L113), [_alarm](../seed/selfimprove.py#L117), [compile_op](../seed/selfimprove.py#L121), [register](../seed/selfimprove.py#L162), [_worker_init](../seed/selfimprove.py#L168), [_solve](../seed/selfimprove.py#L175), [solve_many](../seed/selfimprove.py#L184), [deterministic](../seed/selfimprove.py#L192), [_deterministic_worker](../seed/selfimprove.py#L210), [deterministic_check](../seed/selfimprove.py#L221), [near_miss](../seed/selfimprove.py#L232), [grid_text](../seed/selfimprove.py#L260), [task_text](../seed/selfimprove.py#L264), [vocab_names](../seed/selfimprove.py#L287), [build_request](../seed/selfimprove.py#L291), [shape_key](../seed/selfimprove.py#L333), [mock_proposer](../seed/selfimprove.py#L343), [openrouter_proposer](../seed/selfimprove.py#L356), [hf_proposer](../seed/selfimprove.py#L390), [extract_code](../seed/selfimprove.py#L430), [_journal](../seed/selfimprove.py#L436), [load_ops](../seed/selfimprove.py#L442), [_save_checkpoint](../seed/selfimprove.py#L450), [_tuples](../seed/selfimprove.py#L461), [baseline](../seed/selfimprove.py#L465), [run](../seed/selfimprove.py#L477), [verify](../seed/selfimprove.py#L617), [_events](../seed/selfimprove.py#L646), [probe](../seed/selfimprove.py#L651), [_probe_one](../seed/selfimprove.py#L670), [main](../seed/selfimprove.py#L679) | — |
| [seed/village.py](../seed/village.py) | [World](../seed/village.py#L36), [Echo](../seed/village.py#L63), [run](../seed/village.py#L119), [window_stats](../seed/village.py#L187), [self_description](../seed/village.py#L203), [experiment](../seed/village.py#L221), [verdicts](../seed/village.py#L252), [main](../seed/village.py#L270) | [World.__init__](../seed/village.py#L37), [World.episode](../seed/village.py#L42), [World.hint](../seed/village.py#L46), [World.claim](../seed/village.py#L51), [Echo.__init__](../seed/village.py#L66), [Echo.write](../seed/village.py#L75), [Echo.trust](../seed/village.py#L82), [Echo.entry_for](../seed/village.py#L85), [Echo.value](../seed/village.py#L89), [Echo.update](../seed/village.py#L94), [Echo.greedy](../seed/village.py#L98), [Echo.choose_agent](../seed/village.py#L107), [Echo.sign](../seed/village.py#L115) |
| [seed/village2.py](../seed/village2.py) | [World](../seed/village2.py#L18), [Echo](../seed/village2.py#L70), [run](../seed/village2.py#L143), [metrics](../seed/village2.py#L177), [experiment](../seed/village2.py#L194) | [World.__init__](../seed/village2.py#L19), [World.offer](../seed/village2.py#L31), [World.execute](../seed/village2.py#L45), [World.claims](../seed/village2.py#L54), [World.settle](../seed/village2.py#L58), [Echo.__init__](../seed/village2.py#L71), [Echo.value](../seed/village2.py#L80), [Echo.trust](../seed/village2.py#L83), [Echo.context](../seed/village2.py#L86), [Echo.allowed](../seed/village2.py#L90), [Echo.scores](../seed/village2.py#L94), [Echo.choose](../seed/village2.py#L100), [Echo.update](../seed/village2.py#L108), [Echo.remember](../seed/village2.py#L112), [Echo.evidence](../seed/village2.py#L124), [Echo.state](../seed/village2.py#L129), [Echo.description](../seed/village2.py#L135) |
| [seed/village2_campaign.py](../seed/village2_campaign.py) | [hashes](../seed/village2_campaign.py#L22), [config](../seed/village2_campaign.py#L26), [integrity](../seed/village2_campaign.py#L32), [checks](../seed/village2_campaign.py#L38), [diary_valid](../seed/village2_campaign.py#L66), [observe](../seed/village2_campaign.py#L77), [develop](../seed/village2_campaign.py#L89), [prepare](../seed/village2_campaign.py#L112), [examine](../seed/village2_campaign.py#L128), [audit](../seed/village2_campaign.py#L140), [main](../seed/village2_campaign.py#L176) | — |
| [seed/village3.py](../seed/village3.py) | [Echo](../seed/village3.py#L14), [run](../seed/village3.py#L45) | [Echo.__init__](../seed/village3.py#L15), [Echo.begin](../seed/village3.py#L20), [Echo.charge](../seed/village3.py#L24), [Echo.mature](../seed/village3.py#L32), [Echo.state](../seed/village3.py#L40) |
| [seed/village3_campaign.py](../seed/village3_campaign.py) | [sources](../seed/village3_campaign.py#L25), [save](../seed/village3_campaign.py#L29), [read](../seed/village3_campaign.py#L35), [summary](../seed/village3_campaign.py#L39), [observe](../seed/village3_campaign.py#L46), [development](../seed/village3_campaign.py#L53), [integrity](../seed/village3_campaign.py#L84), [examine](../seed/village3_campaign.py#L90), [audit](../seed/village3_campaign.py#L109) | — |
| [seed/village3_efficient.py](../seed/village3_efficient.py) | [Echo](../seed/village3_efficient.py#L8) | [Echo.exploration_pm](../seed/village3_efficient.py#L9), [Echo.choose](../seed/village3_efficient.py#L12), [Echo.state](../seed/village3_efficient.py#L20) |
| [seed/village3_efficient_campaign.py](../seed/village3_efficient_campaign.py) | [examine](../seed/village3_efficient_campaign.py#L21) | — |
| [seed/village3_factorized.py](../seed/village3_factorized.py) | [Echo](../seed/village3_factorized.py#L9), [run](../seed/village3_factorized.py#L68) | [Echo.__init__](../seed/village3_factorized.py#L10), [Echo.begin](../seed/village3_factorized.py#L16), [Echo.charge](../seed/village3_factorized.py#L29), [Echo.mature](../seed/village3_factorized.py#L38), [Echo.estimates](../seed/village3_factorized.py#L50), [Echo.scores](../seed/village3_factorized.py#L55), [Echo.state](../seed/village3_factorized.py#L62) |
| [seed/village3_factorized_campaign.py](../seed/village3_factorized_campaign.py) | [examine](../seed/village3_factorized_campaign.py#L17) | — |
| [seed/village3_receipts.py](../seed/village3_receipts.py) | [Echo](../seed/village3_receipts.py#L9) | [Echo.__init__](../seed/village3_receipts.py#L10), [Echo.begin](../seed/village3_receipts.py#L15), [Echo.charge](../seed/village3_receipts.py#L21), [Echo.mature](../seed/village3_receipts.py#L28), [Echo.scores](../seed/village3_receipts.py#L37), [Echo.state](../seed/village3_receipts.py#L44) |
| [seed/village3_receipts_campaign.py](../seed/village3_receipts_campaign.py) | [examine](../seed/village3_receipts_campaign.py#L23) | — |
| [seed/village3_settled.py](../seed/village3_settled.py) | [Echo](../seed/village3_settled.py#L8) | [Echo.mature](../seed/village3_settled.py#L9), [Echo.state](../seed/village3_settled.py#L13) |
| [seed/village3_settled_campaign.py](../seed/village3_settled_campaign.py) | [examine](../seed/village3_settled_campaign.py#L19) | — |

El inventario documental conserva cada contrato, resultado, recuperación y revisión disponible de ECHO-4/4.5 y los planes posteriores. La clase del documento describe su función; su veredicto se lee dentro del documento y en el resumen actualizado superior. Un archivo de resultados puede contener una medición roja o un corte previo. Las fuentes históricas permanecen sin reescribir.

| Documento | Función del registro |
|---|---|
| [ECHO-RSI1-DESIGN](ECHO-RSI1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO-RSI1-READINESS](ECHO-RSI1-READINESS.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-BENCH-ARC2-DESIGN](ECHO4-BENCH-ARC2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH-ARC2-RESULTS](ECHO4-BENCH-ARC2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-BENCH-ARC3-D-DESIGN](ECHO4-BENCH-ARC3-D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH-ARC3-DESIGN](ECHO4-BENCH-ARC3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH-ARC3-LLM-DESIGN](ECHO4-BENCH-ARC3-LLM-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH-ARC3-LLM-RESULTS](ECHO4-BENCH-ARC3-LLM-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-BENCH-ARC3-LLM2-DESIGN](ECHO4-BENCH-ARC3-LLM2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH-ARC3-RESULTS](ECHO4-BENCH-ARC3-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-BENCH1-A-D-DESIGN](ECHO4-BENCH1-A-D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH1-A-DESIGN](ECHO4-BENCH1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BENCH1-A-RESULTS](ECHO4-BENCH1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-BENCH1-PLAN](ECHO4-BENCH1-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-BOUNDARY1-DESIGN](ECHO4-BOUNDARY1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-BOUNDARY1-RESULTS](ECHO4-BOUNDARY1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-BRANDING-20260922](ECHO4-BRANDING-20260922.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-CODE-AGENT-PLAN](ECHO4-CODE-AGENT-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-CODE1-A-DESIGN](ECHO4-CODE1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-CODE1-A-RESULTS](ECHO4-CODE1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-CONTINUITY1-A-RESULTS](ECHO4-CONTINUITY1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-CONTINUITY1-B-DESIGN](ECHO4-CONTINUITY1-B-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-CONTINUITY1-B-RESULTS](ECHO4-CONTINUITY1-B-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-CONTINUITY1-C-DESIGN](ECHO4-CONTINUITY1-C-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-CONTINUITY1-C-RESULTS](ECHO4-CONTINUITY1-C-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-CONTINUITY1-D-DESIGN](ECHO4-CONTINUITY1-D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-CONTINUITY1-D-PREFLIGHT](ECHO4-CONTINUITY1-D-PREFLIGHT.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-CONTINUITY1-D-RESULTS](ECHO4-CONTINUITY1-D-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-CONTINUITY1-DESIGN](ECHO4-CONTINUITY1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-CURIOSITY-METAVERSE-PLAN](ECHO4-CURIOSITY-METAVERSE-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-DREAM1-A-DESIGN](ECHO4-DREAM1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-DREAM1-A-RESULTS](ECHO4-DREAM1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-DREAM1-BCD-DESIGN](ECHO4-DREAM1-BCD-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-DREAM1-BCD-RESULTS](ECHO4-DREAM1-BCD-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-DREAM1-D-V2-DESIGN](ECHO4-DREAM1-D-V2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-DREAM1-D-V2-RESULTS](ECHO4-DREAM1-D-V2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-DREAM1-D-V3-DESIGN](ECHO4-DREAM1-D-V3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-DREAM1-D-V3-RESULTS](ECHO4-DREAM1-D-V3-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-DREAM1-PLAN](ECHO4-DREAM1-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-ECHO5-TIMELINE](ECHO4-ECHO5-TIMELINE.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-EGO-PROGRAMA](ECHO4-EGO-PROGRAMA.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-HOSTING-PLAN](ECHO4-HOSTING-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-INTEGRATE1-D-DESIGN](ECHO4-INTEGRATE1-D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-INTEGRATE1-DESIGN](ECHO4-INTEGRATE1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-INTEGRATE1-RESULTS](ECHO4-INTEGRATE1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-INTERACTION1-A-DESIGN](ECHO4-INTERACTION1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-INTERACTION1-A-RESULTS](ECHO4-INTERACTION1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-INTERACTION1-BCD-DESIGN](ECHO4-INTERACTION1-BCD-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-INTERACTION1-BCD-RESULTS](ECHO4-INTERACTION1-BCD-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-INVESTIGACION-Y-PROGRAMA-20260921](ECHO4-INVESTIGACION-Y-PROGRAMA-20260921.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-MAINTAIN1-A-DESIGN](ECHO4-MAINTAIN1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-MAINTAIN1-A-RESULTS](ECHO4-MAINTAIN1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-MAINTAIN1-BCD-DESIGN](ECHO4-MAINTAIN1-BCD-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-MAINTAIN1-FINAL-RESULTS](ECHO4-MAINTAIN1-FINAL-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-NEGOCIO-PLAN](ECHO4-NEGOCIO-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-OTHER1-DESIGN](ECHO4-OTHER1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-OTHER1-RESULTS](ECHO4-OTHER1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-RELATION1-A-DESIGN](ECHO4-RELATION1-A-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-RELATION1-A-RESULTS](ECHO4-RELATION1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-RELATION1-B-DESIGN](ECHO4-RELATION1-B-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-RELATION1-B-RESULTS](ECHO4-RELATION1-B-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-RELATION1-C-RESULTS](ECHO4-RELATION1-C-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-RELATION1-CD-DESIGN](ECHO4-RELATION1-CD-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-RELATION1-D-RESULTS](ECHO4-RELATION1-D-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-RELEASE1-DESIGN](ECHO4-RELEASE1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-RELEASE1-RESULTS](ECHO4-RELEASE1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-ROLES1-AB-DESIGN](ECHO4-ROLES1-AB-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-AB-RESULTS](ECHO4-ROLES1-AB-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-ROLES1-C-RESULTS](ECHO4-ROLES1-C-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-ROLES1-CD-DESIGN](ECHO4-ROLES1-CD-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-COMPLETO](ECHO4-ROLES1-COMPLETO.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-ROLES1-D-RESULTS](ECHO4-ROLES1-D-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-ROLES1-LIAR-DESIGN](ECHO4-ROLES1-LIAR-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-LIAR-V2-DESIGN](ECHO4-ROLES1-LIAR-V2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-V2-DESIGN](ECHO4-ROLES1-V2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-V3-DESIGN](ECHO4-ROLES1-V3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-V4-DESIGN](ECHO4-ROLES1-V4-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-V5-DESIGN](ECHO4-ROLES1-V5-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-ROLES1-V5-RESULTS](ECHO4-ROLES1-V5-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SELF1-A-RESULTS](ECHO4-SELF1-A-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SELF1-B-DESIGN](ECHO4-SELF1-B-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SELF1-B-RESULTS](ECHO4-SELF1-B-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SELF1-C-DESIGN](ECHO4-SELF1-C-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SELF1-C-RESULTS](ECHO4-SELF1-C-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SELF1-C-V2-DESIGN](ECHO4-SELF1-C-V2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SELF1-C-V2-RESULTS](ECHO4-SELF1-C-V2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SELF1-DESIGN](ECHO4-SELF1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SELF1-FINAL-DESIGN](ECHO4-SELF1-FINAL-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SELF1-FINAL-RESULTS](ECHO4-SELF1-FINAL-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SENSATION1-CLOSURE](ECHO4-SENSATION1-CLOSURE.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SENSATION1-DESIGN](ECHO4-SENSATION1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SENSATION1-PREDICTOR-V1](ECHO4-SENSATION1-PREDICTOR-V1.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO4-SENSATION1-RESULTS](ECHO4-SENSATION1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SITUATE1-DESIGN](ECHO4-SITUATE1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SITUATE1-RESULTS](ECHO4-SITUATE1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-SITUATE2-DESIGN](ECHO4-SITUATE2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-SITUATE2-PLAN](ECHO4-SITUATE2-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO4-SITUATE2-RESULTS](ECHO4-SITUATE2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO4-WORLD1-DESIGN](ECHO4-WORLD1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO4-WORLD1-RESULTS](ECHO4-WORLD1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-ARC-COMPARISON-DESIGN](ECHO45-ARC-COMPARISON-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-ARC-PREPARATION-RESULTS](ECHO45-ARC-PREPARATION-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-CAPACITY-STUDY-DESIGN](ECHO45-CAPACITY-STUDY-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-CAPACITY-STUDY-RESULTS](ECHO45-CAPACITY-STUDY-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-CAPACITY500K-ARC1-DESIGN](ECHO45-CAPACITY500K-ARC1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-CAPACITY500K-ARC1-ORCHESTRATION](ECHO45-CAPACITY500K-ARC1-ORCHESTRATION.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-CAPACITY500K-ARC1-RESULTS](ECHO45-CAPACITY500K-ARC1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-CAPACITY500K-RESEARCH](ECHO45-CAPACITY500K-RESEARCH.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-DECISIONES](ECHO45-DECISIONES.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-ECHO5-ROADMAP](ECHO45-ECHO5-ROADMAP.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-EGO-MEMORIA1-DESIGN](ECHO45-EGO-MEMORIA1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA2-DESIGN](ECHO45-EGO-MEMORIA2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA2-PLAN](ECHO45-EGO-MEMORIA2-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-EGO-MEMORIA2-RESULTS](ECHO45-EGO-MEMORIA2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-EGO-MEMORIA3-DESIGN](ECHO45-EGO-MEMORIA3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA3-DEVELOPMENT](ECHO45-EGO-MEMORIA3-DEVELOPMENT.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-EGO-MEMORIA3-RESULTS](ECHO45-EGO-MEMORIA3-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-EGO-MEMORIA3B-DESIGN](ECHO45-EGO-MEMORIA3B-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA3C-DESIGN](ECHO45-EGO-MEMORIA3C-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA3D-DESIGN](ECHO45-EGO-MEMORIA3D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-EGO-MEMORIA3E-DESIGN](ECHO45-EGO-MEMORIA3E-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-ESTADO-20260926](ECHO45-ESTADO-20260926.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-FINAL-AUDIT-RECOVERY](ECHO45-FINAL-AUDIT-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-FINAL-EXAM-DESIGN](ECHO45-FINAL-EXAM-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-FINAL-EXAM-RESULTS](ECHO45-FINAL-EXAM-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-H1-H3-DESIGN](ECHO45-H1-H3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-H1-H3-EXAM-DESIGN](ECHO45-H1-H3-EXAM-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-H1-H3-EXAM2-DESIGN](ECHO45-H1-H3-EXAM2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-H1-H3-EXAM2-RESULTS](ECHO45-H1-H3-EXAM2-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-H1-H3-MODULES](ECHO45-H1-H3-MODULES.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-H1-H3-RESULTS](ECHO45-H1-H3-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-HARNESS15-DESIGN](ECHO45-HARNESS15-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-HARNESS15-RESULTS](ECHO45-HARNESS15-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-MEMORY-ARC-TRANSFER-PLAN](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-MUNDOS1-PROPOSAL](ECHO45-MUNDOS1-PROPOSAL.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-NEXUS0-VALIDATION-20260930](ECHO45-NEXUS0-VALIDATION-20260930.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-NEXUS15-SESSION-20260930](ECHO45-NEXUS15-SESSION-20260930.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-NEXUS151-GOAL-DISPLAY](ECHO45-NEXUS151-GOAL-DISPLAY.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-OBSERVABILITY](ECHO45-OBSERVABILITY.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-POST-S6-PLAN-20260929](ECHO45-POST-S6-PLAN-20260929.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-RECOVERY-20260929](ECHO45-RECOVERY-20260929.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-RECOVERY-NEXT-STEPS](ECHO45-RECOVERY-NEXT-STEPS.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-REFINEMENT-DESIGN](ECHO45-REFINEMENT-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-REFINEMENT-RESULTS](ECHO45-REFINEMENT-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-REFINEMENT-S2V-DESIGN](ECHO45-REFINEMENT-S2V-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-REFINEMENT-S2V-RESULTS](ECHO45-REFINEMENT-S2V-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S1-RESULTS](ECHO45-S1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S2-DESIGN](ECHO45-S2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S3-DESIGN](ECHO45-S3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S4-DESIGN](ECHO45-S4-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S5-D-DESIGN](ECHO45-S5-D-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S5-DESIGN](ECHO45-S5-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S5-E-DESIGN](ECHO45-S5-E-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S5-E-RESULTS](ECHO45-S5-E-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-AUTOMEJORA-DESIGN](ECHO45-S6-AUTOMEJORA-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B-DESIGN](ECHO45-S6-B-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B-RESULTS](ECHO45-S6-B-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B1-DESIGN](ECHO45-S6-B1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B10-DESIGN](ECHO45-S6-B10-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B10-RECOVERY](ECHO45-S6-B10-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B10-RESULTS](ECHO45-S6-B10-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B11-AUDIT-DIRECTORY-RECOVERY](ECHO45-S6-B11-AUDIT-DIRECTORY-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS](ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-S6-B11-DESIGN](ECHO45-S6-B11-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B11-IMPLEMENTATION](ECHO45-S6-B11-IMPLEMENTATION.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-B11-PUBLICATION](ECHO45-S6-B11-PUBLICATION.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-B11-RESULTS](ECHO45-S6-B11-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B11-TRANSPORT-RECOVERY](ECHO45-S6-B11-TRANSPORT-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B11-TRANSPORT-RECOVERY2](ECHO45-S6-B11-TRANSPORT-RECOVERY2.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B12-DESIGN](ECHO45-S6-B12-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B12-IMPLEMENTATION](ECHO45-S6-B12-IMPLEMENTATION.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-B12-LIVE](ECHO45-S6-B12-LIVE.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-B12-RECOVERY1](ECHO45-S6-B12-RECOVERY1.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B12-RESULTS](ECHO45-S6-B12-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B2-DESIGN](ECHO45-S6-B2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B3-DESIGN](ECHO45-S6-B3-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B3-PLAN](ECHO45-S6-B3-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-S6-B3-RESULTS](ECHO45-S6-B3-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B4-DESIGN](ECHO45-S6-B4-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B4-INFERENCE-AUDIT-ADDENDUM](ECHO45-S6-B4-INFERENCE-AUDIT-ADDENDUM.md) | Auditoría o revisión del instrumento |
| [ECHO45-S6-B4-INFERENCE-RECOVERY](ECHO45-S6-B4-INFERENCE-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B4-INFERENCE-RECOVERY2](ECHO45-S6-B4-INFERENCE-RECOVERY2.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B4-PILOT-RESULTS](ECHO45-S6-B4-PILOT-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B4-PLAN](ECHO45-S6-B4-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO45-S6-B5-DESIGN](ECHO45-S6-B5-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B5-RESULTS](ECHO45-S6-B5-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B6-DESIGN](ECHO45-S6-B6-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B6-RESULTS](ECHO45-S6-B6-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B7-DESIGN](ECHO45-S6-B7-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B7-RESULTS](ECHO45-S6-B7-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B8-CPU-DESIGN](ECHO45-S6-B8-CPU-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B8-CPU-RESULTS](ECHO45-S6-B8-CPU-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B8-CPUQ8-DESIGN](ECHO45-S6-B8-CPUQ8-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B8-CPUQ8-RESULTS](ECHO45-S6-B8-CPUQ8-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B8-DESIGN](ECHO45-S6-B8-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B8-INFERENCE-RECOVERY](ECHO45-S6-B8-INFERENCE-RECOVERY.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-B8-RESULTS](ECHO45-S6-B8-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-B9-DESIGN](ECHO45-S6-B9-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-B9-RESULTS](ECHO45-S6-B9-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-CAPACITY-CONTROL](ECHO45-S6-CAPACITY-CONTROL.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-CAPACITY-RESULTS](ECHO45-S6-CAPACITY-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-CONSUMPTION-DIAGNOSIS-20260929](ECHO45-S6-CONSUMPTION-DIAGNOSIS-20260929.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-S6-DIAGNOSIS-20260929](ECHO45-S6-DIAGNOSIS-20260929.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-S6-ESTADO-20260927](ECHO45-S6-ESTADO-20260927.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-CAPACITY-ANALYSIS-20260930](ECHO45-S6-CAPACITY-ANALYSIS-20260930.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-S6-PRECISE-CONTROL](ECHO45-S6-PRECISE-CONTROL.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-PRECISE-RESULTS](ECHO45-S6-PRECISE-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-PROBE1-DESIGN](ECHO45-S6-PROBE1-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-PROBE1-RESULTS](ECHO45-S6-PROBE1-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-PROBE1-REVIEW-20260930](ECHO45-S6-PROBE1-REVIEW-20260930.md) | Auditoría o revisión del instrumento |
| [ECHO45-S6-PROBE2-INDEPENDENT-REVIEW](ECHO45-S6-PROBE2-INDEPENDENT-REVIEW.md) | Auditoría o revisión del instrumento |
| [ECHO45-S6-PROBE2-DESIGN](ECHO45-S6-PROBE2-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-S6-PROMPT-PILOT-RESULTS](ECHO45-S6-PROMPT-PILOT-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-PROMPT-PILOT](ECHO45-S6-PROMPT-PILOT.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-RECOVERY-NOTES](ECHO45-S6-RECOVERY-NOTES.md) | Recuperación declarada y conservación del intento anterior |
| [ECHO45-S6-RESEARCH-20260930](ECHO45-S6-RESEARCH-20260930.md) | Diagnóstico, hipótesis y opciones de investigación |
| [ECHO45-S6-RESULTS](ECHO45-S6-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6-TRANSITION-CONTROL](ECHO45-S6-TRANSITION-CONTROL.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-S6-TRANSITION-RESULTS](ECHO45-S6-TRANSITION-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-S6B5-EGO-CHECKPOINT-20260928](ECHO45-S6B5-EGO-CHECKPOINT-20260928.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO45-SEED-DESIGN](ECHO45-SEED-DESIGN.md) | Contrato, algoritmo y criterios de examen |
| [ECHO45-VALIDATION-CAPACITY-S6-RESULTS](ECHO45-VALIDATION-CAPACITY-S6-RESULTS.md) | Medición, resultado o cierre con su alcance |
| [ECHO45-WEB-GIF-FIX-20261001](ECHO45-WEB-GIF-FIX-20261001.md) | Registro de desarrollo, operación o documentación del módulo |
| [ECHO55-INFRASTRUCTURE-PLAN](ECHO55-INFRASTRUCTURE-PLAN.md) | Ruta de trabajo o propuesta pendiente de sus puertas |
| [ECHO55-PILOT-OFFER-DRAFT](ECHO55-PILOT-OFFER-DRAFT.md) | Registro de desarrollo, operación o documentación del módulo |

El corte indexa 286 archivos de implementación, 3330 definiciones/métodos y 228 documentos de esta línea, además de los dieciocho fragmentos anteriores. No incluye claves, respuestas reservadas completas ni monólogos simulados. El historial anterior se conserva byte a byte: SHA-256 `863cda4c4460deeed6c382b31185045d3792d6decbf6b08f8c71403cb60623d4`.
