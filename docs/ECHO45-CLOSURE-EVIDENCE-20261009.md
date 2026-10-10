**ECHO-4.5 · evidencia de cierre y viabilidad de medición ARC**

Corte de evidencia: **9 de octubre de 2026, 00:30 Europe/Madrid**.
Nota operativa actualizada a las 00:44. Documento privado de
consulta; no ejecución, envío ni declaración de cierre ya conseguido.

Decisión actual del propietario: **terminar B24; después medir ARC-1/2/3 y cerrar oficialmente ECHO-4.5
aunque S6 siga rojo, cualquiera que sea el resultado**.
Cerrar la versión no convierte un criterio científico fallido en aprobado.
B24 se implementó en un trabajo separado y se envió a Kaggle a las 00:40
Madrid. **Sin resultado medido confirmado** en este corte; el estado operativo
posterior está en el [registro de ejecución](ECHO45-S6-B24-RUN-20261009.md).
[NOW](NOW.md) y el [roadmap específico](ECHO45-ECHO5-ROADMAP.md) todavía
describían B24 como plan el 8 de octubre; ese estado documental no sustituye
la actualización actual. Aquí solo se preparan opciones de evaluación.

La revisión leyó primero el
[spec NEXUS-0](05-NEXUS-0-SPEC.md), después estado, informes, resúmenes agregados
y código de los adaptadores. Los resultados siguientes proceden de auditorías
ya registradas: **no se repitieron experimentos ni se leyeron resultados por
tarea de exámenes sellados**. No se modifican contratos, fuentes congeladas,
NEXUS-0, observadores ni `echo-discord`.

**Capacidades confirmadas y alcance.** «Solo» significa sin llamadas LLM en
esa condición; no implica aprendizaje sin estructura o primitivas humanas.

| Capacidad / fuente ejecutable | Resultado confirmado | Solo / LLM | Alcance y límite |
|---|---|---|---|
| Cuerpo, reparación, relaciones y tribu heredados de ECHO-4 | [INTEGRATE-1](ECHO4-INTEGRATE1-RESULTS.md): 16 semillas, 256 ticks; mantenimiento 3.080 frente a 2.341 unidades de trabajo, preguntas 4.379 frente a 6.145 del control; 112/112 casos adversos. | Solo. | Mundos discretos definidos por el laboratorio. La tribu alimenta al cuerpo, pero el coste corporal no cambia sus decisiones sociales; el orden fijo resuelve más temas gastando más consultas. |
| Continuidad, identidad y verificación de testimonios | [INTEGRATE-1](ECHO4-INTEGRATE1-RESULTS.md): 48/48 reanudaciones exactas y rechazos de huella errónea; cero hechos falsos frente a 30 sin cortafuegos. | Solo. | Conservación de estado y evidencia en ese contrato; no prueba de conciencia ni de alucinaciones cero fuera del dominio. |
| Dreaming sobre ramas registradas | [DREAM-D v3](ECHO4-DREAM1-D-V3-RESULTS.md): 900/960 diagnósticos frente a 640/960 fijo y 721/960 aleatorio; 60 abstenciones y replay exacto. | DREAM y control sin Qwen empatan en 900/960. | Selección de pruebas corporales de un catálogo humano con presupuesto 12; ramas ausentes producen desconocido. Una mejora inicial, sin mejora recursiva ilimitada ni ventaja exclusiva del LLM. |
| Núcleo situado: [loop](../nexus0/loop.py), [Q](../nexus0/qtable.py), [T](../nexus0/world.py), [gate](../nexus0/gate.py) | [Regresión documentada](ECHO45-NEXUS0-VALIDATION-20260930.md): 488 pruebas, un fallo esperado histórico, sin fallos inesperados. | Solo; córtex apagado en el banco basal. | WSP16, CAM, política y transición discreta. La regresión no acredita todos los objetivos de sus extensiones. Software: no hay AKD1000 ni medición energética de NPU. |
| EGO-MEMORIA-3E: [diario](../seed/village3_receipts.py) | [Cierre](ECHO45-EGO-MEMORIA3-RESULTS.md): M1–M5 pasan en 16/16 semillas nuevas; M6 reproduce exactamente 16/16. Desarrollo: coste 748.872 → 733.548, −2,05 % agregado. | Solo. | Escritura selectiva, verificación aprendida y efecto causal de recuerdos en la aldea. La factorización causal es programada; no demuestra transferencia universal ni incorporación completa al núcleo. |
| V3 relacional e integración: [DSL](../seed/relational_dsl.py), [solver](../seed/relational_solver.py) | [V3](ECHO45-RELATIONAL-V3-RESULTS.md): DSL anterior 64/192; relacional 160/192; candidato integrado **192/192**. | Solo, CPU. | Seis familias sintéticas diseñadas por el laboratorio. Representación y orden de enumeración cambian juntos; no se separa su contribución. No es una puntuación ARC. |
| Memoria ARC y política V3: [adaptador](../seed/arc_memory.py), [política](../seed/arc_delayed_policy.py) | [V3](ECHO45-RELATIONAL-V3-RESULTS.md): 228.192 → 184.352 unidades de trabajo en 64 tareas equilibradas (**−19,21 %**); ahorro en toda la batería **0,166 %**. Retirar el recibo pertinente: 159.040 → 5.326.494, conservando 32/32 aciertos. | Solo. | `choose/begin/charge/mature` aprende dos decisiones: recuperar primero o buscar primero. No traslada todas las políticas de verificar/escribir de la aldea. Ajuste y adquisición tienen costes propios; no hay ganancia de acierto atribuida a esta política. |
| Síntesis/refinamiento: [solver V3](../seed/relational_solver.py) | [V3](ECHO45-RELATIONAL-V3-RESULTS.md): composición **32/32 frente a 0/32** sin refinamiento; composición girada también 32/32 frente a 0/32, sin memoria. | Solo. | Composición de operaciones conocidas, bajo presupuesto acotado. No acredita invención de primitivas arbitrarias. |
| Multi-view: [solver V3](../seed/relational_solver.py) | [V3](ECHO45-RELATIONAL-V3-RESULTS.md): sin memoria, **160/192 → 192/192**, sin pérdidas; familia orientada 0/32 → 32/32. | Solo. | Ocho vistas, con igual techo de trabajo y coste registrado. La mejora sintética sustituye el antiguo «sin ventaja demostrada» de V2 solo en este dominio. |
| Consistencia: [solver V3](../seed/relational_solver.py) | [V3](ECHO45-RELATIONAL-V3-RESULTS.md): 16 compromisos erróneos → 0 mediante **32 abstenciones** en 32 casos ambiguos; controles inequívocos 32/32 en ambos brazos. | Solo. | Evita comprometer una respuesta cuando programas compatibles discrepan; no resuelve los 32 casos ambiguos ni garantiza el test por ajustar demostraciones. |
| Guía ejecutable de 500k: [ProgramGuide](../seed/verified_program_guide.py) | [Resumen auditado](../lab/seed/program-guide-20261003/primary/summary.json): **4.090/4.096** con 500k, 1.956/4.096 con 65.536, 109/4.096 sin guía; búsqueda de 32 programas 4.096/4.096. [Auditoría](../lab/seed/program-guide-20261003/audit.json): ocho semillas. | Solo. | Una propuesta por consulta, salvo el control exhaustivo. Programas suministrados y verificados, motivos conocidos con color/posición cambiados. **500.000 posiciones uint8 asociativas; no 500.000 neuronas LIF ni parámetros de un LLM.** |
| Capacidad y transferencia ARC anteriores: [guía de primitivas](../seed/kenyon_capacity.py), [comparación](../seed/kenyon_arc1.py) | [ARC-1 training](ECHO45-CAPACITY500K-ARC1-RESULTS.md): base 3/250, guía 640 5/250, 500k **6/250**; 750 replays. [CAP-STRESS-1](ECHO45-CAPACITY-TRANSFER-FORENSICS.md): 99,81 % frente a 46,88 % con 65k, a 16.384 contextos, veinte semillas. | Solo. | Son condiciones distintas del GUIDE V3. El primer resultado es desarrollo conocido; el segundo, almacenamiento sintético. No justifican atribuir una ventaja ARC general a 500k. |
| Memoria temporal de juegos: [actor v5.8](../echo_arc/temporal_agent.py) | [Informe S5-F2](ECHO45-H1-H3-EXAM2-RESULTS.md): **1.537/1.800** niveles frente a 1.239/1.800 de v5.7, sin regresiones individuales; 120 replays según el [roadmap](ECHO45-ECHO5-ROADMAP.md). | Solo. | Orden y conteo en ARC3-GYM sintético. No son niveles ni score del conjunto privado de Kaggle. Se consultó el informe, no sus partidas reservadas. |

El [recibo agregado V3](../lab/seed/relational-v3-20261003/closure.json)
declara `valid:true`, seis puertas de módulos aprobadas, 1.952 resoluciones y
512 episodios de ajuste reproducidos, pero también
`ARC_improvement_certified:false`, `S6_green:false`, `release_ready:false`.
Esta revisión comprobó por lectura y hash que las **19 fuentes del candidato
V3 siguen coincidiendo** con su manifiesto. La reproducción registrada fue
interna, en procesos nuevos con el mismo código; no una réplica externa.
No hay una medición universal de «cero alucinaciones».

**V3 sintético y seguimiento ARC deben conservar cifras separadas.**
El [informe de integración V1/V2](ECHO45-INTEGRATION-RESULTS.md) acredita
64/64 sintéticos con memoria y 71,04 % menos aplicaciones primitivas
(58,21 % incluyendo adquisición, todavía sin todos los costes auxiliares).
En ARC-1 de desarrollo conocido, V2 pasó de 2/64 a 4/64; ARC-2 quedó 0/64.
En el seguimiento disjunto, ambos candidatos empataron en **1/128**:
**0/64 ARC-1 y 1/64 ARC-2**. Son tareas públicas de training, no una reserva
externa. Ese empate no queda revertido por los verdes sintéticos V3.

Las referencias históricas auditadas siguen siendo las del
[informe de preparación ARC](ECHO45-ARC-PREPARATION-RESULTS.md) y el
[roadmap](ECHO45-ECHO5-ROADMAP.md):

| Referencia local histórica, sin LLM | Resultado | Interpretación |
|---|---|---|
| ARC-1, evaluación pública | 31/400 tareas exactas frente a 20/400; 7,75 % frente a 5 %. | Resultado de aquel candidato y presupuesto; no medición de V3. |
| ARC-2, evaluación pública | 0/120 en ambos candidatos. | Negativo conservado; no score privado Kaggle. |
| ARC-3, 16 juegos / 112 niveles del contrato | 11/112 frente a 13/112; score local con contabilidad completa 0,6436787896/100 frente a aproximadamente 0,069413/100. | Completar más niveles y obtener mayor score son métricas distintas. No sustituye el score del gateway. |

**Solo frente a LLM: lo medido.**

| Comparación | Evidencia | Conclusión permitida |
|---|---|---|
| Interfaz de lenguaje y cortafuegos | [RELEASE-1](ECHO4-RELEASE1-RESULTS.md): Phi-3.5-mini local produjo cinco afirmaciones verificadas; «humano» fue contradicho y «vivo» quedó inverificable. Caída del servidor: creencia vacía y agente operativo; parada del operador en tick 230. | El LLM redacta propuestas de afirmación; el núcleo filtra qué puede creer. Resultado acotado, sin garantía general sobre conversación libre. |
| ARC-2, [DeepSeek y Qwen](ECHO4-BENCH-ARC2-RESULTS.md) | DeepSeek solo 1/30; con ECHO 2/30; control de más programas sin verificación 2/30. Qwen: 0/120 en sus tres brazos; ECHO solo 0/120. | El híbrido supera al modelo solo en esa muestra, pero empata con el control de presupuesto. No se demuestra un aporte de aciertos exclusivo de ECHO. |
| ARC-3, [Qwen3-30B y ECHO](ECHO4-BENCH-ARC3-LLM-RESULTS.md) | Modelo solo 0/112 niveles; percepción 1/112; híbrido 4/112; referencia ECHO v2 solo 13/112. Los cuatro niveles híbridos los completó ECHO mediante EXPLORE. | ECHO ayuda a ese modelo; ponerlo bajo ese modelo no supera a ECHO solo. El informe tiene una corrección de scores: sus valores originales no deben citarse. |
| S6 B23-R4, [cierre y autopsia](ECHO45-S6-B23-R4-FORENSICS-20261008.md) | **924 partidas; 36 llamadas/propuestas científicas LLM + 8 de preflight**. Mejor 7B y 14B: 61 → 65 niveles, pero cinco pérdidas individuales de score. 16 duplicados, 12 propuestas inactivas medidas y ocho activas con pérdidas; cero aceptadas. | Interfaz reparada y resultado negativo de búsqueda bajo ese contrato. No acredita ventaja del 14B ni S6 verde. El control humano retrospectivo 61 → 67 no es descubrimiento autónomo. |
| B24 | Implementación/lanzamiento por separado; sin resultado confirmado al corte. | No atribuirle mejoras, cooperación útil ni entrenamiento de pesos antes de medir. |

Las capacidades V3 de la primera tabla funcionan sin LLM. No existe aquí una
comparación nueva V3 frente a LLM que permita extrapolar las cifras anteriores
a cualquier modelo o afirmar superioridad general de una de las opciones.

**ARC oficial disponible al corte.** Se consultaron páginas actuales de ARC
Prize y las operaciones de lectura `get_competition` / `list_competition_pages`
de Kaggle. Las páginas HTML de Kaggle no devolvieron texto; su contenido y
calendario se verificaron mediante el conector. No se descargaron tareas.

| Vía | Estado comprobado | Medición viable después de B24 |
|---|---|---|
| ARC-1 / [ARC Prize 2024](https://www.kaggle.com/competitions/arc-prize-2024) | Cerró el 10-11-2024; metadata actual `submissions_disabled:true`. El [programa 2026](https://arcprize.org/competitions/2026) enumera ARC-2, ARC-3 y paper, no una competición ARC-1 nueva. | Notebook de Kaggle que evalúe el [corpus oficial ARC-1](https://github.com/fchollet/ARC-AGI): 400 tareas públicas de evaluación. Informar «evaluación pública ejecutada en Kaggle»; no prometer envío tardío ni score privado oficial. |
| ARC-2 / [2025](https://www.kaggle.com/competitions/arc-prize-2025) y [2026](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2) | 2025 cerrado, `submissions_disabled:true`. Calendario 2026 abierto: entrada 26-10 y envío final **02-11-2026 23:59 UTC**. | Ruta de competición 2026: notebook sin internet, hasta 12 h, `submission.json`, dos intentos por cada salida de test. La evaluación pública del [corpus ARC-2](https://github.com/arcprize/ARC-AGI-2) sigue siendo otra medición. [Formato y requisitos](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview/evaluation). |
| ARC-3 / [2026](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3) | Calendario abierto: entrada 26-10 y envío final **02-11-2026 23:59 UTC**. Notebook sin internet, hasta 9 h; archivo generado por el gateway. | Evaluación de competición: 110 juegos privados, 55 para cada leaderboard. No confundirlos con los juegos públicos o el gimnasio local. [Datos](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data) · [requisitos](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/code-requirements). |
| ARC-3 público, SDK/API | [OFFLINE](https://docs.arcprize.org/local-vs-online) permite juego local; ONLINE permite scorecards. [COMPETITION](https://docs.arcprize.org/toolkit/competition_mode) impone una sola tarjeta y una apertura por entorno; Kaggle usa ese modo. | Un scorecard de juegos públicos o una entrada del leaderboard no verificado no constituye una evaluación privada de Kaggle. No se abrió ninguna tarjeta en esta revisión. |

La consulta autenticada `gh repo view navywakura/echoai` del 9 de octubre
confirma que el repositorio sigue **PRIVATE**, con licencia detectada como
`Other`. La apertura/relicencia exigida por la página general de la competición
no se presume a partir de la petición de evaluar el modelo.

No está verificado que **esta cuenta pueda enviar ahora**: la consulta de
historial de envíos de ambas competiciones devolvió `Unauthenticated`.
El [plan local del 25 de septiembre](ARCPRIZE2026-CAMPANA.md) registraba reglas
aceptadas, y el roadmap un primer envío de prueba; son antecedentes, no una
comprobación actual ni una puntuación nueva de ECHO-4.5.

Hay tres discrepancias oficiales que afectan a la preparación:

- El timeline ARC-3 dice 26-10 a las 23:59 UTC; `new_entrant_deadline` de su
  metadata devuelve **11:59 UTC**. Usar la hora anterior para planificar y
  verificar el estado de la cuenta; no esperar al último día.
  [Timeline](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/timeline).
- La [metodología actual ARC-3](https://docs.arcprize.org/methodology) describe
  un tope por nivel de 1,15; la [página de datos Kaggle](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/data)
  conserva `min(humano/agente,1)^2`, como el runner local. Registrar versión
  de wheels, contadores y score devuelto por el gateway; no corregir resultados
  históricos ni asumir equivalencia entre esas fórmulas.
- La [página general ARC Prize 2026](https://arcprize.org/competitions/2026)
  exige abrir código antes de recibir scores privados oficiales y menciona
  CC0/MIT-0; las reglas específicas de
  [ARC-2](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/rules) y
  [ARC-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/rules)
  conservan CC-BY 4.0 para ganadores. Hay que aclarar esta diferencia antes
  de prometer una evaluación privada manteniendo todo privado. Este documento
  no autoriza ni realiza publicación o cambio de licencia.

**Opciones accionables de runner, inspeccionadas pero no ejecutadas.**
Comandos desde `/home/roger/REALRXOS/RXos/echoai`, para una fase posterior.

1. **Rejillas ARC-1/2: candidato V3 sin LLM, una tarea permitida.**
   [CLI real](../seed/echo45_v3.py): acepta `train` con demostraciones y
   `test` con entradas; `solver_input` excluye salidas de test. Devuelve
   predicciones o abstención, no un `submission.json` de competición.
   `TASK_JSON` debe apuntar a una tarea autorizada del nuevo protocolo.

   ```bash
   python3 observe.py --launch
   TASK_JSON=/ruta/absoluta/a/tarea-permitida.json
   PYTHONPATH=.. python3 -m seed.echo45_v3 "$TASK_JSON" \
     --candidate lab/seed/relational-v3-20261003/primary/candidate.json
   ```

   Variante existente: añadir
   `--guide lab/seed/program-guide-20261003/primary/guide500k.json`.
   Ambos archivos existen. Medirla como brazo separado; no seleccionar guía
   después de ver evaluación. Sin `--learn-to`, no se guarda un hijo aprendido.

2. **ARC-3 público de desarrollo, v5.8 sin LLM.**
   El [observador existente](../echo_arc/observe.py) admite v5.8 y selección
   explícita de juegos. Este ID pertenece al split de desarrollo y su carpeta
   existe; el intérprete gestionado ARC también existe, sin comprobarlo en ejecución.

   ```bash
   PYTHONPATH=.. lab/arc3/ARC-AGI-3-Agents/.venv/bin/python \
     -m echo_arc.observe offline lab/arc3/environment_files \
     --agent v5.8 --games bp35-0a0ad940 --budget 2000
   ```

   Es una opción de desarrollo con el visor anterior, no un examen oficial.
   El directorio contiene **24 juegos**: no omitir `--games`, porque el
   valor por defecto los recorrería todos. El [temporal_bench](../echo_arc/temporal_bench.py)
   exige exactamente ocho entornos en modo offline y no sirve directamente
   con ese directorio completo. No añadir observación a campañas selladas.

3. **ARC-3 Kaggle: borrador CPU v5.8 ya empaquetado.**
   [Script](../lab/kaggle/echo45-release-20260928/preview-v58/echo45_submission.py),
   [constructor](../lab/kaggle/echo45-release-20260928/build.py) y
   [estado de preparación](../lab/kaggle/echo45-release-20260928/README.md).
   Inspección estática del payload: 16 fuentes con hashes válidos e iguales
   a sus archivos actuales; `patches:[]`, `final_profile_digest:null`.
   Es la base v5.8, **no V3 de rejillas ni un candidato B24**.

   ```bash
   # Solo dentro de Kaggle, con la copia del paquete y la competición adjunta:
   python3 lab/kaggle/echo45-release-20260928/preview-v58/echo45_submission.py
   ```

   El script distingue ensayo offline de `KAGGLE_IS_COMPETITION_RERUN` y
   conecta al gateway en el segundo caso. El parquet ficticio del ensayo
   offline solo satisface formato: no demuestra una puntuación. Falta ensayo
   privado con los wheels actuales. No regenerar el borrador histórico en
   su sitio: `build.py preview` escribe en ese directorio existente.

4. **Alternativa ARC-3 si el wrapper antiguo no es compatible:** adaptar ECHO
   en una copia nueva del [starter oficial](https://docs.arcprize.org/arc-prize-2026),
   con Python 3.12 y `MyAgent.is_done/choose_action`. Tras su instalación,
   `make notebook` construye sin subir. `make submit` sube un notebook; la
   evaluación oculta ocurre al enviar ese notebook a competición. Ninguna
   de esas fases se ha realizado aquí y el starter no integra ECHO por sí solo.

**Preparación que falta, separada de los runners existentes.**

- **Cerrar B24 con su resultado real**, incluido negativo o instrumento
  incompleto, y fijar qué actor se evalúa. Si no hay política aceptada,
  conservar la base e identificar expresamente cualquier brazo experimental.
  Cierre administrativo de 4.5 y estado científico S6 deben figurar separados.
- **Crear un protocolo nuevo para la medición post-B24.**
  [arc_comparison.py](../seed/arc_comparison.py) está ligado a S6-B11 verde y
  reconstruye registros históricos: no ejecutarlo ni saltarse su guarda para
  esta petición. El constructor `final` también depende de la campaña antigua.
  Fijar candidatos, hashes, exposición previa, presupuestos, intentos, reset
  de estado por tarea y criterios antes de medir. Las evaluaciones públicas
  ya conocidas se describirán como seguimiento, sin recuperar su condición ciega.
- **ARC-1/2 en Kaggle necesitan empaquetado por lote y juez separado.** No se
  encontró exportador V3 de competición en los módulos inspeccionados. Debe
  recorrer todos los IDs y tests, mantener fuera del solver las soluciones,
  preservar abstenciones en el informe y generar un formato válido para
  cada `attempt_1/attempt_2` exigido por ARC-2. Registrar cualquier predicción
  de respaldo como tal. Informar tanto exactitud por tarea histórica como
  la métrica Kaggle por salida de test, sin mezclarlas.
- **Verificar acceso Kaggle y compatibilidad del gateway**: autenticación,
  reglas, wheels y dependencias offline, archivo de salida, reloj máximo y
  contabilidad de todos los reinicios. Un notebook `COMPLETE` no prueba que
  exista un envío de competición válido ni un score. Resolver las discrepancias
  oficiales indicadas; no se hacen envíos ni publicaciones desde este sidecar.
- **Separar procedencia de aprendizaje y coste de inferencia.** Comparar
  ECHO solo, LLM solo y ECHO+LLM solo donde exista un adaptador probado, con
  iguales datos y presupuestos declarados. Los [adaptadores históricos ARC-2](../echo4/arc2_bench.py)
  y [ARC-3 LLM](../echo4/arc3_llm.py) usan servicios externos; no son entradas
  Kaggle offline listas. Un brazo híbrido requeriría modelo/pesos locales y
  su propio empaquetado. Distinguir «LLM durante investigación» de «LLM durante
  evaluación»: ejecutar sin llamadas un programa propuesto antes por un modelo
  no elimina esa procedencia.

La medición posterior registrará el score aunque sea cero. Los resultados
sintéticos, los seguimientos públicos y los scores emitidos por competición
seguirán siendo evidencias distintas, con su versión, denominador y coste.
