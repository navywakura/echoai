# Roadmap: ECHO-4.5 y ECHO-5 (actualizado 2026-10-12)

**12 de octubre · ECHO-5 5.0.0: verde oficial dentro del alcance validado.**
Cierre r3 verificado, incluida confirmación Gazebo/PX4 en simulación. Correcciones
posteriores auditadas: 12/18 independientes y 9/9 plantillas, 28/28 exploración,
64/64 currículo. Seis tareas siguen abiertas; S6 se retoma después de 5.5.
[Estado vigente](PROJECT-CHECKPOINT-20261012.md) ·
[Release](../ECHO-5/docs/RELEASE-5.0.0.md).
Los bloques siguientes conservan sus estados históricos; no son el estado vigente.


**11 de octubre · ECHO-5 ya implementado; validación completa pendiente.**
Objetos, relaciones, conceptos, composición, interacción, currículo adaptativo,
MiniGrid/BabyAI, integración MissionAgent y panel local tienen implementación.
La confirmación cognitiva r1 está auditada; la confirmación física Gazebo/PX4
no pasó. Sigue abierta su corrección con nuevos recibos y casos de confirmación.
La prioridad de cierre es resolver y medir esa integración, preservar los
resultados negativos y ejecutar el finalizador con los criterios existentes.
Unity se publica como sandbox complementario en
[echounity](https://github.com/navywakura/echounity), con cámara, cartografía
observada y aprendizaje acotado de los efectos del movimiento.
La secuencia posterior mantiene ECHO-5.1 (colaboración), ECHO-5.5 (persistencia
y sistema instalable) y la investigación RSI. S6 se retoma después de 5.5.
[Checkpoint actual](PROJECT-CHECKPOINT-20261011.md) ·
[Checklist de ECHO-5](../ECHO-5/docs/CLOSURE-CHECKLIST.md).
Los hitos siguientes conservan la cronología anterior.

**9 de octubre, 14:15 Madrid · decisión vigente, posterior a los bloques históricos.**
Terminar B24, revisar sus recibos, conservar las mediciones ARC pendientes y
cerrar la etapa 4.5 con sus límites explícitos. S6 seguirá sin pase salvo la
evidencia exigida por su contrato; su nueva investigación se retomará después
de ECHO-5.5. El cierre oficial aún no se ha realizado. Primero en ECHO-5:
inventario y consolidación del runtime, recuperación de la cadena robótica
Gazebo/PX4 existente y diseño de GUI local de observabilidad. Comparar después
las contribuciones de memoria compartida, multiagente, competición, simulación
e investigador mediante ablaciones y casos nuevos. No se sustituye el protocolo
B24 en curso. [Decisión y alcance](ECHO45-TO-ECHO5-DECISION-20261009.md).

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


**B23-R4 cerrado sin pase; B24 integra reparación y cooperación.**
924 partidas y 36 propuestas: 16 duplicados, 12 inactivas medidas y ocho
activas con pérdidas. Ambos modelos alcanzaron 61→65 conservando niveles,
pero perdiendo score en cinco casos. La autopsia recalcula las 66 mediciones,
36 prompts y confirma 88 fuentes intactas. El control humano histórico permite
61→67 sin pérdidas en esos mismos casos; falta descubrimiento autónomo.
[Investigación reproducible](ECHO45-S6-B23-R4-FORENSICS-20261008.md).

**B23-R3 cerrado sin ganador**: [resultados auditados](ECHO45-S6-B23-KAGGLE-RESULTS-20261008.md).
Los tres brazos sin LLM midieron sus propuestas y no hallaron pase; los
dos brazos Qwen generaron 36 propuestas inválidas, ninguna ejecutada.
La comparación de tamaño de ese R3 quedó inconclusa. R4 reparó el formato,
pero tampoco acreditó ventaja del 14B ni conservación. S6 permanece abierto.

**Decisión actual: [B24 integrado](ECHO45-S6-B24-CONDITIONAL-PLAN.md).**
Reparar recuperación de evidencia, selección de padre, resumen numérico y
desperdicio por duplicados/inactividad en todos sus brazos. Comparar un
investigador, tres independientes y tres cooperativos; añadir referencia R4
y control sin LLM. Los cinco brazos permiten distinguir corrección, selección
con neocórtex e intercambio. Plan posterior a los resultados; todavía sin
implementación, contrato ejecutable congelado ni partidas B24. Los bloques
del día 7 siguientes conservan el estado histórico.
S6 conserva sus requisitos de confirmación desde SEMILLA y examen B1–B5.

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
**S6 continúa pendiente.** B17 demuestra 383 sin pérdidas en A con síntesis
sin LLM; el híbrido conserva una pérdida aunque dispone de la guarda válida.
El diagnóstico del 5 de octubre añade doce partidas reproducidas y localiza
el fallo en evidencia temporal, selección y repeticiones de comportamiento.
Próximo trabajo pendiente: usar consumos de candidatos, garantizar cobertura
acotada y certificar equivalencias del control; probarlo en escenarios nuevos
y en un micro comparativo. Después siguen conservación protegida, campaña,
auditoría y examen según sus puertas. Los análisis retrospectivos no cierran
esas fases. [Causas, contrastes y propuesta](ECHO45-S6-B17-FORENSICS.md).
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

Investigación B14, 4 de octubre: empate 1134–1134 auditado; ninguna de las 36
propuestas usa HOLD/COOLDOWN_CAP. **Pendiente:** acoplar foco y operador,
contabilizar exploración efectiva, corregir crédito marginal y conservar
extremos numéricos de evidencia; medir una microablación antes del siguiente
piloto. PROBE2 demuestra 383 en A sobre la misma base, sin acreditar ventaja
autónoma ni conservación B. [Diagnóstico](ECHO45-S6-B14-FORENSICS.md).

<!-- S6B13R1-BEGIN -->
**S6-B13-R1: PILOT_NO_PROMOTION; S6 abierto.** Reinicio declarado con runtime CPU nativo; criterios científicos y modelo conservados. Los resultados parciales del runtime anterior quedan separados. [Adenda](ECHO45-S6-B13-RUNTIME1.md) · [Resultado](ECHO45-S6-B13-RUNTIME1-RESULTS.md).
<!-- S6B13R1-END -->

<!-- S6B13-BEGIN -->
**S6-B13: INCOMPLETE_RUNTIME_REPLACED; S6 todavía abierto.** Trabajo reanudado por petición del propietario. PROBE2 reproducido en 240 partidas independientes (378 → 383); ese control humano no entra en los prompts. B13 prueba descubrimiento autónomo, con criterios V1–V4 y B1–B5 intactos. [Contrato](ECHO45-S6-B13-DESIGN.md) · [Resultado](ECHO45-S6-B13-RESULTS.md).
<!-- S6B13-END -->

**Corte de módulos del 3 de octubre:** el propietario autoriza demostrar utilidad
de módulos también fuera de ARC. V3 cierra seis puertas en bancos sintéticos,
con pruebas reproducidas. El estado de S6 se actualiza en el bloque superior
y en la tabla; el cierre final queda pendiente. Los resultados ARC históricos
no cambian. La investigación y sus datos son privados.

| Estado actual | Módulo | Evidencia y alcance |
|---|---|---|
| ✅ | REL-DSL-1 | Objetos/relaciones/roles/composición tipados; 160/192 frente a 64/192 del DSL anterior en la batería nueva |
| ✅ | Memoria 3E + ARC-3E-POLICY-1 | Ciclo completo para decidir recuperar/buscar; persistencia y crédito diferido; 19,21 % de ahorro en el contraste primario, 0,166 % global; intervención causal de recibos |
| ✅ | Refinamiento y síntesis | Composición 32/32 frente a 0/32 sin refinamiento; también 32/32 frente a 0/32 en composición girada |
| ✅ | Multi-view | 160/192 → 192/192 con igual presupuesto y sin pérdidas en este banco |
| ✅ | Consistencia | 16 errores comprometidos → 0 al abstenerse en 32 casos ambiguos; mantiene 32/32 controles inequívocos |
| ✅ | Guía de 500.000 unidades | Recuperación de programas ejecutables: 99,85 % vs 47,75 % con 65k y 2,66 % sin guía, una propuesta por consulta |
| ✅ | Integración técnica V3 | 192/192 sintéticos con memoria, política, vistas y consistencia; candidato persistente y CLI; auditorías completas |
| ❌ | S6 B1–B5 | B20: MICRO_CLOSED_NO_PROMOTION; S6 requiere conservación, piloto, campaña y examen. Ver el informe de ejecución |
| ❌ | Cierre final de ECHO-4.5 | Transferencia ARC y puertas finales, retención global y decisión de versión; `release_ready:false` |

[Informe V3 y gráficas](ECHO45-RELATIONAL-V3-RESULTS.md) ·
[Contrato y adenda previos a confirmar](ECHO45-RELATIONAL-V3-DESIGN.md).
El verde de módulos tiene el alcance indicado. No certifica ventaja ARC de
500k, invención autónoma de reglas o superioridad general de la política.

Lo que sigue conserva el corte del 2 de octubre y la historia previa.

**Orden anterior, sustituido por la reanudación S6-B13 del 3 de octubre:
memoria y solver antes de S6.** Se había aplazado la investigación S6; las dependencias cronológicas anteriores de
este documento son históricas y no impiden este trabajo. Sus criterios y
resultados científicos permanecen intactos.

| Prioridad actual | Estado comprobado | Pendiente para el verde completo |
|---|---|---|
| Memoria 3E → ARC | ✅ Adaptador, recibos, retirada causal y persistencia; 64/64 sintético con 71,04 % menos primitivas | ❌ Política adaptativa completa y mejora ARC fuera del ajuste |
| Refinamiento y síntesis | ✅ Composición 16/16 vs 0/16; V2: 4/64 vs 2/64 ARC-1 conocido | ❌ Confirmación: seguimiento empata 1/128, sin ventaja |
| Vistas y consistencia | ✅ Implementadas y medidas por ablación | ❌ Ventaja propia; vistas desactivadas por defecto |
| Capacidad 640–500k | ✅ Exportable; CAP-STRESS-1 mide ventaja de almacenamiento a carga alta | ❌ Ventaja ARC en el nuevo candidato; los tamaños empatan |
| Integración y evaluación 4.5 | ✅ Candidato local, adquisición de demostraciones y replays | ❌ Puertas finales ARC y conservación global; 4.5 todavía abierto |
| S6 B1–B5 | Aplazado, sin nuevas ejecuciones en esta serie | ❌ Descubrimiento autónomo, conservación, cuatro brazos y auditoría |

[Resultado completo de integración](ECHO45-INTEGRATION-RESULTS.md) ·
[contrato](ECHO45-INTEGRATION-DESIGN.md) ·
[seguimiento disjunto](ECHO45-INTEGRATION-FOLLOWUP-DESIGN.md).

**2 oct · siguiente revisión, todavía por implementar:** **ARC-3E-POLICY-1**
debe aprender dónde gastar mediante `choose/begin/charge/mature`, conservando
la verificación como operación separada. **REL-DSL-1** añade representación
tipada de objetos, relaciones, variables y composición. La inspección encontró
492 asociaciones y baja ocupación en el candidato actual. El ensayo de
capacidad **CAP-STRESS-1** pasó: 99,81 % con 500k frente a 46,88 % con 65k a
16.384 contextos sintéticos; veinte semillas y dos replays exactos. No acredita
transferencia ARC. [Diagnóstico y condiciones de verde](ECHO45-CAPACITY-TRANSFER-FORENSICS.md) ·
[contrato del banco](ECHO45-ASSOCIATIVE-STRESS-DESIGN.md).

**2 oct · LOCALDEV-1:** añadido el arnés de desarrollo local `echo-dev`, con
mapa AST, ejecución aislada, propiedades de las primitivas y reparación acotada
de archivos permitidos en una copia. Los contratos de S6/RSI permanecen
congelados. Su validación de ingeniería se registra aparte:
[funcionamiento](ECHO-LOCALDEV-HARNESS.md) · [mediciones y alcance](ECHO-LOCALDEV-RESULTS.md).

<!-- S6B12-R1-BEGIN -->
**S6-B12-R1 — CAMPAIGN_NO_PROMOTION.** Recuperación declarada del límite remoto; mismas propuestas y criterios, reproducción exacta obligatoria de las siete respuestas guardadas. [Adenda](ECHO45-S6-B12-RECOVERY1.md) · [Seguimiento](ECHO45-S6-B12-LIVE.md).
<!-- S6B12-R1-END -->

<!-- S6B12-RESULT-BEGIN -->
**S6-B12 — CAMPAIGN_NO_PROMOTION. S6 todavía no verde.** Contexto verificado antes de inferencia, piloto previo auditado y campaña nueva. [Contrato](ECHO45-S6-B12-DESIGN.md) · [Resultados](ECHO45-S6-B12-RESULTS.md).
<!-- S6B12-RESULT-END -->

**30 sep · CAPACITY-500K experimental:** banco disperso de 500.000 pesos
enteros para priorizar primitivas ARC, apagado por defecto. En un diagnóstico
sintético de cuatro transformaciones obtuvo 40/40 frente a 33/40 con 640
unidades; no es una puntuación ARC ni afecta S6-B11. La comparación posterior
en desarrollo con presupuesto común ha pasado su puerta; datos a continuación.
[Diseño, límites y fuentes](ECHO45-CAPACITY500K-RESEARCH.md).

**30 sep · validación y comparación real:** regresión NEXUS-0 aprobada:
488 pruebas, un fallo esperado histórico; el bloqueo de sockets de la GUI
se resolvió con el permiso del entorno, sin cambiar el núcleo.
Comparación ARC-1 **VERDE**: base 3/250 (1,2%), guía 640 5/250 (2,0%) y
guía 500k 6/250 (2,4%), con 60 programas de entrenamiento separados y
750 replays completos. Cero pérdidas frente a base; coste CPU 500k +3,6%.
Es una mejora de desarrollo con presupuesto común, no una nueva puntuación
oficial. El candidato opcional está exportado; S6-B11 permanece intacto.
[Validación](ECHO45-NEXUS0-VALIDATION-20260930.md) ·
[Resultado ARC-1](ECHO45-CAPACITY500K-ARC1-RESULTS.md).

**30 sep · S6-B11 detenido:** piloto 1129 frente a 1108, tres mejoras ECHO,
auditoría independiente válida de los 36 veredictos. Campaña: una de seis
rondas completada, una aceptación por brazo. La ronda c1 falló antes de
generar ECHO porque su prompt excedió el límite congelado de 6000 tokens.
Cinco respuestas FIJO parciales conservadas; examen sin abrir, S6 no verde.
[Diagnóstico y pendientes](ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS.md).

## HARNESS-1.5 · herramienta beta para desarrollar ECHO-4.5

Nuevo módulo de integración: **echo-nexus 1.5.0 beta**. Como el panel de un
vehículo, muestra registros del motor y permite consultar un asesor sin darle
el volante. No sustituye NEXUS-0 ni acredita S6.

| Estado | Submódulo | Qué hace y cuándo es verde |
| --- | --- | --- |
| ✅ | **N15.1 · HTTPS y catálogo** | OpenRouter usa HTTPS y rechaza modelos retirados antes de inferir. Respuestas gratuitas reales: Liquid 1.06 s, router 9.33 s; nunca cambia a pago |
| ✅ | **N15.2 · editor y copia** | Multilínea, Ctrl+V, F3 y `/copy`; pegar comandos dentro de un documento no los ejecuta |
| ✅ | **N15.3 · mundo de sesión** | Una instancia mantiene memoria entre episodios mientras el chat sigue disponible; integración real: 3 metas durante 171 pasos, 0 reinicios; detener cierra el proceso |
| ✅ | **N15.4 · procedencia** | `/echo` reporta registros sin LLM; `/ask` consulta al asesor sin enviarle coordenadas exclusivas del visor ni devolver su respuesta al motor |
| ✅ | **N15.5 · distribución** | Publicado e instalado desde HTTPS con hash verificado; escritorio/móvil, paquete instalado y página beta comprobados |

**Verde del módulo sólo cuando N15.1–N15.5 pasan.** No modifica fuentes
congeladas. 24 pruebas del arnés pasan y 190 fuentes protegidas permanecen
intactas. Su publicación sólo incluye el arnés; ECHO-4.5 sigue en investigación.
[Contrato y límites](ECHO45-HARNESS15-DESIGN.md) · [Cierre VERDE](ECHO45-HARNESS15-RESULTS.md).

<!-- ARC-PREPARATION-20260929-BEGIN -->
**29 sep, 19:43 — preparación de comparación ARC completada.** ✅ Referencias
auditadas 31/400, 0/120 y 11/112 reconstruidas; ✅ comparador con presupuestos
conservados y bloqueo de políticas provisionales; ✅ diagnóstico sintético
por capacidades: completo 12/12, sin relaciones 6/12, sin composición 9/12,
con 36 replays exactos. Son pruebas de desarrollo, no nuevos resultados ARC.
❌ Candidato final S6 y seguimiento ARC; ❌ adaptador y transferencia de memoria
a ARC. Las 190 fuentes protegidas siguen intactas; S6 continúa sin declararse
verde. [Implementación, evidencia y siguientes pasos](ECHO45-ARC-PREPARATION-RESULTS.md).
<!-- ARC-PREPARATION-20260929-END -->

<!-- S6B11-RESULT-BEGIN -->
**S6-B11 — PENDING_ERROR. S6 todavía no verde.** Desarrollo ampliado, contrastes antes/después y selección adaptativa; conservación estricta. [Contrato](ECHO45-S6-B11-DESIGN.md) · [Resultado](ECHO45-S6-B11-RESULTS.md) · [Estado](../lab/seed/s6b11-20260929/status.json).
<!-- S6B11-RESULT-END -->

<!-- S6B10-RESULT-BEGIN -->
**S6-B10 — PILOTO SIN PROMOCIÓN. S6 todavía no verde.** ECHO 534, FIJO 534; aceptaciones ECHO 0. Piloto auditado, reserva sin abrir. [Resultado](ECHO45-S6-B10-RESULTS.md) · [Estado](../lab/seed/s6b10-20260929/status.json).
<!-- S6B10-RESULT-END -->

<!-- S6-DIAGNOSIS-20260929-BEGIN -->
**Diagnóstico S6, 29 sep:** B10 mejora niveles A y B, sin pérdida individual de niveles, pero todas sus propuestas hacen más lenta una misma partida protegida. V4 exige conservar también cada puntuación individual. Trece programas dan seis conductas medidas; evidencia de tareas repetida y feedback protegido limitado. B7 ya tuvo una mejora ECHO aceptada, pero empató con FIJO. No se cambian umbrales ni se abre reserva. [Criterios, historia y causa investigada](ECHO45-S6-DIAGNOSIS-20260929.md).
<!-- S6-DIAGNOSIS-20260929-END -->

<!-- S6B9-RESULT-BEGIN -->
**S6-B9 — PILOTO SIN PROMOCIÓN. S6 todavía no verde.** ECHO 534, FIJO 534; aceptaciones ECHO 0. Piloto auditado, reserva sin abrir. [Resultado](ECHO45-S6-B9-RESULTS.md) · [Estado](../lab/seed/s6b9-20260929/status.json).
<!-- S6B9-RESULT-END -->

**Histórico del 29 sep, 05:15–07:07 Madrid — S6-B9:** seis pruebas y paridad de la base completas; piloto cerrado sin promoción y auditoría válida. ECHO/FIJO 534–534, cero aceptaciones; reserva sin abrir. El control humano positivo (+8 A sin pérdidas A/B) no se atribuye al modelo. [Resultado B9](ECHO45-S6-B9-RESULTS.md) · [Control](ECHO45-S6-TRANSITION-RESULTS.md).

**Histórico del 29 sep — continuaciones CPU de S6-B8:** float16 terminó parcial (2/6 respuestas); la condición Q8 cerró el piloto y su auditoría, sin mejora ni promoción (534–534). Los cambios de backend están declarados y las reservas permanecen sin abrir. [Float16](ECHO45-S6-B8-CPU-DESIGN.md) · [Q8](ECHO45-S6-B8-CPUQ8-RESULTS.md).

**29 sep — S6-B8 pendiente:** implementación y 14 pruebas completas; doce propuestas auditadas, cero aceptaciones, suma A ECHO/FIJO 534–534. Faltan seis propuestas: dos trabajos fallaron durante la descarga de pesos y quedan 13 segundos de GPU gratis. Reserva sin abrir. [Informe](ECHO45-S6-B8-RESULTS.md) · [Después de S6](ECHO45-POST-S6-PLAN-20260929.md).

**29 sep 2026 — cierre de esta iteración:** EGO-MEMORIA-3E VERDE: M1–M5 16/16 y M6 exacto 16/16; revisiones 3A–3D conservadas. S6-B6/B7 cerrados y auditados; B7 ECHO 537 frente a FIJO 537, aceptaciones ECHO 1; sin promoción; examen final sin abrir. B5 y los exámenes anteriores permanecen cerrados; S6 todavía no se declara VERDE. [Memoria](ECHO45-EGO-MEMORIA3-RESULTS.md) · [Registro actual](ECHO45-RECOVERY-20260929.md).

<!-- S6B5-AUTO-BEGIN -->
**Estado automático S6-B5 — 2026-09-28 17:36 Madrid: CLOSED.**

Control preciso cerrado: 6/12 positivos, ganador preregistrado `hold20_after_level`. Es una reparación humana, no automejora.

Piloto: ECHO acepta 0; suma A ECHO 534, FIJO 534; promoción no.

S6 todavía no acredita B1–B5. Examen nuevo sin abrir.

[Contrato](ECHO45-S6-B5-DESIGN.md) · [Informe](ECHO45-S6-B5-RESULTS.md) · [Estado](../lab/seed/s6b5-20260928/status.json).
<!-- S6B5-AUTO-END -->

Es un PLAN. Cada fase sigue la misma regla: contrato → criterio fijado antes de medir → medir →
publicar, sea verde o rojo.

**✅ = trabajo completado o experimento cerrado. ❌ = trabajo pendiente.**
El resultado científico se indica aparte: un experimento cerrado en ROJO está
completado, pero no demuestra su objetivo. **S6 todavía no está verde.**

**Actualización 28 sep, 17:19 Madrid:** [línea del tiempo ECHO-4 → ECHO-4.5 →
ECHO-5](ECHO4-ECHO5-TIMELINE.md). Cambios precisos S6 implementados/probados;
control cerrado: seis de doce positivos con B nueva. Primero preregistrado
178→181 A, sin pérdidas A/B, replay exacto. S6-B5 preparado, congelado y activo:
piloto LLM y continuación condicional hasta cuatro brazos,
reserva nueva y B1–B5. No es S6 VERDE. Solver de refinamiento/DSL/multi-view/
consistencia implementado y probado; cuatro ablaciones ARC-2 de entrenamiento
terminan 0/12 con S0. La condición posterior con la biblioteca aprendida S2v
da 2/12 en todos los brazos, incluido una pasada: ninguna ventaja adicional
de los mecanismos nuevos demostrada. Jerarquía, adquisición de abstracciones
y TTT pendientes.
[Contrato B5](ECHO45-S6-B5-DESIGN.md) · [Desarrollo](ECHO45-REFINEMENT-RESULTS.md).

## Dónde estamos

| Estado | Paso completado | Evidencia y alcance |
|---|---|---|
| ✅ | S0: semilla, sandboxes y gimnasio | Base experimental construida |
| ✅ | S1: objetos en rejillas | 15 → 21 tareas reservadas |
| ✅ | S2: aprender mejor | 21 → 24 tareas reservadas |
| ✅ | S3: juegos como objetos | 0,506 → 0,678 en desarrollo |
| ✅ | S4: modelo del mundo y planificación | v5: 0,849 en desarrollo |
| ✅ | S5: simulador ARC3-GYM y examen S5-D | VERDE; v5.2: 1103 frente a 940 niveles |
| ✅ | Caja y clic, v5.6: desarrollo y gym-test | 805 frente a 600 niveles; sin examen congelado específico |
| ✅ | Memoria de copia, v5.7, y examen S5-E | VERDE; 475 frente a 399 niveles de v5.6; replay exacto |
| ✅ | H1 y H3, v5.8: implementación y desarrollo | Orden 45 → 134/135; conteo 77 → 152/165 en entrenamiento; H2/H4 mantienen niveles; desarrollo oficial intacto. [Resultados](ECHO45-H1-H3-RESULTS.md) |
| ✅ | H1/H3: examen reservado S5-F2 | Cerrado VERDE a las 20:02: 1537 frente a 1239 niveles, F1–F6 pasan, 120 replays exactos y cero regresiones individuales. S5-F anterior queda incompleto y preservado. [Resultado](ECHO45-H1-H3-EXAM2-RESULTS.md) |
| ✅ | S6-B3: campaña y cierre auditado | Cerrado ROJO a las 23:04: ECHO/FIJO/SEMILLA 1668, SIN FILTRO 1586; B3/B4/B5 pasan, B1/B2 fallan; cero propuestas aceptadas. [Resultado](ECHO45-S6-B3-RESULTS.md) |
| ✅ | S6-B4: implementación y piloto auditado | Cerrado sin promoción a las 02:01: 24 propuestas verificadas, cero aceptadas; cuatro brazos 178/200 en A. Auditoría de inferencia pasa; examen reservado sin abrir. S6 sigue ROJO. [Piloto](ECHO45-S6-B4-PILOT-RESULTS.md) |
| ✅ | S6: diagnóstico y control manual | Cerrado 15:31: 20 reparaciones, ninguna pasa V1–V4. `hold20` gana tres niveles A sin pérdidas A, pero pierde puntuación en una partida B. Replays exactos, sin examen ni LLM. [Resultado](ECHO45-S6-CAPACITY-RESULTS.md) |
| ✅ | S6: ejecutor de piloto posterior | Congelado y probado; omitido automáticamente por falta de control positivo. Cero llamadas LLM/GPU. S6 permanece ROJO. [Resultado](ECHO45-S6-PROMPT-PILOT-RESULTS.md) |
| ✅ | S6-A: campaña, evaluación y documentación | Cerrado ROJO; ECHO/SEMILLA/FIJO 24/201, SIN FILTRO 25/201 |
| ✅ | S6-B: campañas y cierre auditado B2 | Cerrado ROJO; ECHO/FIJO 1350, SEMILLA/SIN FILTRO 1387; B5 pasa |
| ✅ | S6-B5/B6: pilotos completos | B5 cero aceptaciones ECHO; B6 ECHO 534 frente a FIJO 537, sin promoción. B6 auditado, doce veredictos reconstruidos. [Cierre B6](ECHO45-S6-B6-RESULTS.md) |
| ✅ | S6-B7: refinamiento medido y auditado | Una mejora ECHO aceptada 178→181 A sin pérdidas A/B; suma ECHO/FIJO 537. Piloto sin promoción; seis veredictos nuevos reproducidos. [Cierre B7](ECHO45-S6-B7-RESULTS.md) |
| ✅ | EGO-MEMORIA-1: desarrollo M2, M3 y M4 | 8/8 semillas de desarrollo; condición original conservada |
| ✅ | EGO-MEMORIA-2: implementación, examen y auditoría | Cerrado ROJO: M1–M4 pasan 16/16; M5 15/16; M6 16 replays exactos en proceso nuevo. Aprendizaje por acciones realmente ejecutadas, control sin reclamaciones y ablación de recuerdos. [Resultado](ECHO45-EGO-MEMORIA2-RESULTS.md) |
| ✅ | EGO-MEMORIA: cumplir todos los criterios | Condición 3E VERDE: M1–M5 16/16 y M6 exacto 16/16. La condición 2 conserva su ROJO; umbrales sin rebajar. [Cierre](ECHO45-EGO-MEMORIA3-RESULTS.md) |
| ✅ | R1–R4: evaluadores, medición y auditoría final | Cerrado 15:32; 1040 soluciones y 32 partidas reproducidas, contadores SDK y procedencia de 84 programas/tres conceptos válidos. R1/R4 pasan; R2/R3 fallan. Error original preservado y extensión explícita. [Resultado](ECHO45-FINAL-EXAM-RESULTS.md) |
| ✅ | Kaggle y participación RxLabs | Conexión y campañas privadas funcionan; reglas aceptadas y primer envío de prueba realizado |
| ✅ | Mini terminal de decisiones | Observabilidad implementada: 25 comprobaciones del núcleo y ocho pares de partidas ARC pasan; acciones y resultados coinciden con/sin observador. [Uso y evidencia](ECHO45-OBSERVABILITY.md) |
| ✅ | MUNDOS-1: propuesta documentada | Mundos virtuales, ayuda MCP, nota episódica, retención, estilos y reputación. Documentación completada; implementación y resultados pendientes. [Propuesta](ECHO45-MUNDOS1-PROPOSAL.md) |

## Próximo trabajo tras los pilotos B6/B7

EGO-MEMORIA-3E cumple M1–M6 en su condición de aldea. S6-B5 conserva su
cierre sin promoción. B6 mejora la información sobre consumo de parámetros;
B7 añade una corrección desde el resultado real de la propuesta previa.
B7 consigue una mejora aceptada ECHO (178→181 A, sin pérdidas individuales A/B),
pero ECHO y FIJO empatan a 537 en la suma de tres réplicas. El piloto no promueve
la campaña completa ni abre el examen final.

La siguiente hipótesis es seleccionar peticiones mediante aplicabilidad y
efecto medido en A: detectar guardas inactivas o cambios sin efecto antes de
refinar. Requiere otro contrato, controles, presupuesto total comparable y
conservación de B1–B5. No es una mejora demostrada ni una fecha de VERDE.
[Registro y propuesta](ECHO45-RECOVERY-20260929.md).

## Camino pendiente de ECHO-4.5

| Estado | Paso pendiente | Qué falta |
|---|---|---|
| ❌ | S6: demostrar automejora | B7 acepta una mejora ECHO, pero empata con FIJO: 537–537 en A. Falta superar el piloto y medir los cuatro brazos en reserva nueva; B1–B5 se mantienen. [Resultado](ECHO45-S6-B7-RESULTS.md) |
| ❌ | Kaggle: enviar el mejor agente actual | Constructor del borrador CPU/v5.8 implementado; falta ensayo privado contra gateway y visto bueno de Nav. [Borrador](../lab/kaggle/echo45-release-20260928/README.md) |
| ✅ | R1: medición ARC-AGI-1 | 31/400 frente a 20/400, 7,75 % frente a 5 %; criterio pasa y R4 certifica los registros. [Resultado](ECHO45-FINAL-EXAM-RESULTS.md) |
| ✅ | R2: medición ARC-AGI-2 | ROJO auditado: 0/120 en SEMILLA y ECHO |
| ✅ | R3: medición ARC-AGI-3 | ROJO auditado: 11/112 frente a 13/112; objetivo ≥23. Score contrato 0,643679 frente a 0,069413/100 |
| ✅ | R4: cierre de auditoría local final | Cerrado 15:32: 1040 soluciones y 32 partidas exactas; procedencia y contadores SDK válidos. Gateway remoto queda en el paso Kaggle pendiente |
| ❌ | ARC Prize: envíos finales | Seleccionar los dos envíos finales; paper si se participa en esa modalidad |
| ❌ | Publicación y cierre de ECHO-4.5 | Publicar resultados y limitaciones del examen final |

Prioridad actual: demostrar ventaja del selector ECHO frente a FIJO, desarrollar transferencia ARC-2/3, ensayar el borrador de envío y publicar los resultados auditados. Memoria 3E está VERDE en su dominio; S6 sigue pendiente. Otra iteración exige contrato y cohorte nuevos. MUNDOS-1 es una línea de
investigación adicional; sus resultados solo podrán incorporarse al cierre
mediante un contrato y una evaluación propios.

## Para acabar ECHO-4.5 (hasta el 25 de octubre)

1. ✅ **S6-A:** cerrado y auditado; resultados en `ECHO45-S6-RESULTS.md`.
2. ✅ **Memoria de copia (v5.7):** construido y medido: gym-test v3 494 frente a 369 niveles
   de v5.6, sobre todo por H4 (copia). Esa versión todavía no tenía módulos propios H1/H3.
   La puntuación oficial de desarrollo baja ligeramente (1,033 → 1,000), declarado.
   ✅ **Orden y conteo (v5.8):** módulos propios construidos y comprobados en
   desarrollo: 480 partidas comparativas, H1 45 → 134/135, H3 77 → 152/165;
   H2/H4 mantienen niveles y los ocho juegos oficiales mantienen sus resultados.
   Incluye ablaciones y trazas auditadas. ✅ Examen propio S5-F2 cerrado VERDE.
   [Funciones](ECHO45-H1-H3-MODULES.md) · [Resultados](ECHO45-H1-H3-RESULTS.md).
   ✅ **S5-F2 lanzado:** el primer S5-F se interrumpió por el registro de azar;
   se conserva. Adaptador probado antes, contrato nuevo y cohorte 17000–17059.
   ✅ Medición y auditoría terminadas a las 20:02 en 43 min 57 s: 1080 partidas,
   120 replays exactos y F1–F6 pasan; 1537 frente a 1239 niveles, cero regresiones
   individuales. No implica S6 VERDE. [Resultado](ECHO45-H1-H3-EXAM2-RESULTS.md).
3. ✅ **Examen congelado S5-E:** cerrado VERDE; v5.7 475 frente a 399 niveles de v5.6;
   puntuación 3,7604 frente a 2,2658; azar 4,1 %. Fuentes intactas y replay exacto.
   `ECHO45-S5-E-RESULTS.md`.
4. ❌ **Kaggle:** subir el mejor agente (con el visto bueno de Nav). La prueba del notebook ya solo
   juega los 8 juegos de desarrollo.
5. ✅ **EGO-MEMORIA-2:** condición nueva con coste de verificar mayor que el beneficio inmediato, reclamaciones diferidas y cuatro acciones conjuntas aprendidas por resultados reales. Contrato previo, ocho semillas de desarrollo, dieciséis semillas reservadas y auditoría independiente completados. **ROJO:** M1–M4 16/16, M5 15/16 y M6 exacto; en 31011 verificar crece 195 por mil (umbral 200), diferencia con control 165 (umbral 200). ✅ Cumplimiento completo alcanzado después por la condición 3E, con examen nuevo y M1–M6 completos. No se cambia el resultado ni el contrato de la condición 2. [Resultado](ECHO45-EGO-MEMORIA2-RESULTS.md).
6. ✅ **S6 fase B, campaña cerrada:** Nav ordenó abrirla pese al rojo de A. S6-B0 se ejecutó con contrato
   `ECHO45-S6-B-DESIGN.md`: estrategias acotadas de control de v5.7, 30 propuestas
   por brazo en GPU gratis, cuatro brazos y un examen nuevo. El verde exige superar
   a SEMILLA, FIJO y SIN FILTRO, conservar el desarrollo oficial y reproducir todo.
   B0: cerrado ROJO, 1378/1800 en los cuatro brazos y replay exacto; 60/60
   propuestas rechazadas por formato. B1 detenido
   antes de los brazos: una salida de calibración válida y otra con una
   condición inexistente. **B2 cerrado ROJO y auditado**, con 30 propuestas
   válidas por brazo: FIJO acepta dos y ECHO una; ambos mejoran A 56 → 62
   y B 28 → 30, pero sus estrategias finales son idénticas. Examen nuevo:
   ECHO/FIJO 1350/1800 frente a SEMILLA/SIN FILTRO 1387/1800. Desarrollo conserva
   24 niveles pero baja la puntuación de 23,9990 a 18,3599. B1–B4 fallan, B5
   pasa; replays exactos y fuentes intactas. No se promueve la configuración.
   ❌ **S6 verde sigue pendiente:** A/B no cubrían K4 ni M1; la mayor caída está
   en K4. La próxima iteración necesita cobertura A/B completa, evidencia de
   fallos más útil y propuestas capaces de añadir comportamiento temporal,
   con otro contrato y examen. No se garantiza una fecha de verde.
   `ECHO45-S6-B2-DESIGN.md` y `ECHO45-S6-B-RESULTS.md`.
   ✅ **B3 cerrado y auditado ROJO:** políticas acotadas sobre
   v5.8, A/B con las once familias y filtros sin regresión individual. El modelo
   selecciona controles de mecanismos existentes; no escribe los módulos H1/H3.
   Las 60 propuestas pasan formato/ejecución pero ninguna supera utilidad:
   ECHO/FIJO/SEMILLA 1668 niveles, SIN FILTRO 1586. B3/B4/B5 pasan.
   ✅ **B4 implementado y preflight pasado:** 16 pruebas y cuatro partidas,
   fuentes congeladas; parches de un control, episodios y feedback de A.
   ✅ **Piloto B4 cerrado:** servicio persistente iniciado el 28 a las 00:49, seis
   llamadas en cada uno de cuatro brazos de formato/petición. Si ECHO local
   acepta una mejora sin regresiones, continúa a 30 llamadas FIJO/ECHO y al
   examen nuevo 19000–19059 de SEMILLA/FIJO/ECHO/SIN FILTRO. Si no, publica el
   piloto sin abrir examen. El piloto no certifica VERDE. Cuota gratuita;
   sin pago y con espera si se agota. La ronda 3 se recuperó tras dos OOM y un fallo de caché: prefill completo en bloques con caché dinámica explícita; tres intentos archivados, adendas y runtime congelados aparte. Cierre a las 02:01: seis propuestas por brazo verificadas, cero aceptadas; campaña completa no promovida y examen 19000–19059 sin abrir. Auditoría semántica de seis payloads y wrappers válida, declarada en una adenda sin cambios al generador. [Recuperación](ECHO45-S6-B4-INFERENCE-RECOVERY2.md). [Contrato](ECHO45-S6-B4-DESIGN.md) ·
   [Estado](../lab/kaggle/s6b4-20260928/README.md) ·
   [Resultado B3](ECHO45-S6-B3-RESULTS.md).
7. ✅ **Implementación, medición y auditoría del examen final R1–R4:** cierre 15:32 del 28 sep. R1/R4 pasan y R2/R3 fallan; el resultado completo sigue ROJO. Error de comparación tupla/lista original conservado y recuperación explícita, sin cambiar agente ni criterios. [Resultado](ECHO45-FINAL-EXAM-RESULTS.md).
   - ✅ R1 medido y auditado: 31/400 frente a 20/400; criterio pasa;
   - ✅ R2 medido ROJO: 0/120 en ambos agentes;
   - ✅ R3 medido ROJO: 11/112 frente a 13/112; objetivo ≥23 niveles;
   - ✅ R4: auditoría completa, 1040 soluciones y 32 partidas exactas,
     procedencia y contabilidad de acciones/reinicios contrastadas con el SDK.
     Gateway remoto todavía pendiente en el paso Kaggle.

   Con dos cifras: con y sin las operaciones de S6. Se declara que la prueba de Kaggle ya vio el
   resultado global de v5.2 en los juegos del examen.
8. ❌ **ARC Prize 2026, envíos finales:** el calendario del plan indica el 2 nov
   (elegir 2), *paper track* el 9 nov; CC-BY 4.0 si ganamos. ✅ Participación
   RxLabs y primer envío de prueba ya realizados; no confundirlos con los finales.
9. ❌ **Publicar** los resultados del examen y cerrar ECHO-4.5.

## MUNDOS-1: propuesta reciente y camino de investigación

**Estado: propuesta documentada; implementación y campaña pendientes.**
El objetivo es medir si ECHO descubre las capacidades de distintos mundos,
aprende a pedir y verificar ayuda, y conserva una habilidad después de retirar
al LLM. El documento completo es [ECHO45-MUNDOS1-PROPOSAL.md](ECHO45-MUNDOS1-PROPOSAL.md).

| Estado | Fase | Qué debe quedar demostrado o construido |
|---|---|---|
| ✅ | Propuesta y controles | Hipótesis, secuencia y límites documentados; todavía no es un contrato congelado |
| ❌ | M0: contrato experimental | Generador, acciones, permisos, memoria que se conserva, presupuestos, cohortes reservadas, umbrales y auditor independiente |
| ❌ | M1: mundos virtuales | Mundo interior de ECHO, exterior simulado con archivo/contraseña y evaluador privado; caja → llave → puerta → premio, con herramientas limitadas a objetos virtuales |
| ❌ | M2: controles, nota y trazas | Calibrar con ECHO solo y ayudante programado. Exigir una nota antes de leer el archivo, basada en memoria real del episodio y hechos comprobables; medir también sin esa obligación |
| ❌ | M3: bucle ECHO–LLM mediante MCP | ECHO pregunta → recibe propuesta estructurada → comprueba permisos y presupuesto → prueba → verifica el resultado → conserva lo útil. Comparar SEMILLA, FIJO, ECHO, SIN FILTRO DE UTILIDAD, LLM SOLO, SIN MEMORIA y plan fijo |
| ❌ | M4: aprendizaje retenido | Retirar al LLM y medir al aprendiz frente a ECHO fresco y SIN MEMORIA en mundos nuevos resolubles sin ayudante; identificar y comprobar qué estado aprendido produce la ventaja |
| ❌ | M5: doce estilos de propuestas | Doce condiciones inspiradas en arquetipos más un estilo neutral; mismo modelo, ECHO inicial, permisos y presupuesto, con múltiples mundos y semillas |
| ❌ | M6: premio, memoria y reputación | Recompensas por resultados observados; reputación por competencia demostrada y por tipo de tarea, con identidad y procedencia de la evidencia |
| ❌ | M7: cooperación y competición | Comparar aprendizaje individual, cooperativo y competitivo con igual cómputo total, compañeros/adversarios nuevos y resultados individuales y conjuntos |
| ❌ | M8: capacidad y transferencia | Ensayos propios de KENYON-1/DEPTH-1 y posterior integración en ARC-AGI-1/2/3; medir con/sin lo aprendido sobre conjuntos nuevos reservados |
| ❌ | M9: auditoría y cierre | Publicar todos los brazos, costes, fallos, límites y replays; declarar el resultado según los criterios fijados antes |

La nota recogerá observaciones, acciones, resultados, hipótesis registradas y
lo que ECHO desconoce. La mini terminal ya permite ver decisiones reales; la
memoria y la nota exigidas por MUNDOS-1 todavía deben implementarse. Pedir una
nota mide una capacidad bajo esa condición, no reflexión espontánea.

Los estilos serán condiciones de prompt, no doce personalidades demostradas.
La prueba de capacidad neuronal se medirá aparte de la integración inicial.
La reputación requerirá evidencia de competencia; no basta un elogio del modelo.

Orden: M0 → M1/M2 → M3 → M4 → M5/M6 → M7 → M8 → M9.
Mejorar con ayuda, conservar aprendizaje sin ella y transferir a ARC son tres
resultados distintos. Resolver el archivo virtual no convierte S6 en verde ni
completa ARC. No se fija una fecha de verde antes de medir.

## ECHO-5 (después del examen de ECHO-4.5)

Programa «TIKKUN»: ideas tomadas como **hipótesis de ingeniería**, no como afirmaciones
metafísicas.

| Estado | Experimento | Qué prueba | Coste |
|---|---|---|---|
| ❌ | **SITRA-1** | ECHO detecta y bloquea propuestas «parásitas» de su propia IA (trampas, sobreajuste, tocar el verificador); objetivo 100 % | bajo, reutiliza S6 |
| ❌ | **RETRO-1** | aprender hacia atrás: planificar desde la meta y reetiquetar lo vivido con lo que salió bien | bajo, gym |
| ❌ | **TIKKUN-1** | romper partes de ECHO a propósito y que se repare solo verificando | medio |
| ❌ | **SPLIT-1** | clones que divergen y se recombinan con conceptos verificados, frente a un solo ECHO con el mismo cómputo | medio-alto (CPU) |
| ❌ | **MDL-1** | ¿comprender = comprimir? ¿Los conceptos que más acortan son los que más transfieren? | bajo |
| ❌ | **KENYON-1** | memoria inspirada en la abeja: expansión escasa de LIF enteros a 4k → 64k → 1M neuronas para saber «¿he estado aquí?» y «¿salió bien?»; ¿mejora la exploración? | por medir en hardware disponible; sin placa comprometida |
| ❌ | **DEPTH-1** | 0, 1, 3, 5, 10 y 15 niveles de abstracción: ¿cuántos hacen falta? (el 10 no se da por supuesto) | medio |
| ❌ | **S6 paso 1** | el mismo bucle con un modelo frontier: ¿un modelo mejor hace más listo a ECHO? | de pago, con visto bueno de Nav |

Orden propuesto: SITRA-1 y RETRO-1 → KENYON-1 (4k y 64k) y DEPTH-1 → TIKKUN-1 y MDL-1 → SPLIT-1
→ S6 paso 1 → KENYON a 1M, si la curva de mejora y coste lo justifica.

❌ **Examen de ECHO-5:** ARC-AGI-1, 2 y 3 frente a ECHO-4.5, con conjuntos
reservados comunes a ambos agentes y criterios fijados antes. Un conjunto cuyo
resultado ya se abrió no se presenta como un nuevo examen ciego.

**Reglas que no cambian:**
- enteros en el camino rápido;
- no se toca `Layer256` ni el Q6 del repo padre;
- ninguna IA puede modificar el verificador, el cortafuegos ni los criterios;
- ninguna afirmación de consciencia o de inteligencia general.
