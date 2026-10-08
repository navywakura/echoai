# Prompt para Claude Code Opus 5 — TRANSFER-3, planes A/B/C y autocrítica

## Encargo de Roger

Trabaja en `/home/roger/REALRXOS/RXos/echoai` y ejecuta el siguiente encargo.
No te limites a proponer trabajo: implementa, mide, audita y continúa con la
siguiente hipótesis cuando los resultados lo justifiquen.

**Tu objetivo es poner TRANSFER-3 en verde mediante una demostración real:**
lo aprendido en A mejora el comportamiento en mundos nuevos B/C frente al
mismo agente sin ese aprendizaje, sin transferir mapas ni conocer el examen.

No tenemos hardware. El alcance es software/simulación y debe quedar
explícito. No confundas ese verde con vuelo real, HIL o DRONE-3.

Lee íntegramente `docs/TRANSFER3-PROPUESTA-TRANSFERENCIA-UTIL.md`: es la
propuesta autorizada de este encargo. Sustituye la insistencia en reparar
feature 504 como única vía, **no** los invariantes ni los contratos superiores.
El archivo `docs/TRANSFER3-CLAUDE-OPUS5-IMPLEMENTATION.md` ahora contiene un
registro histórico: no lo sobrescribas ni lo confundas con este prompt.

## Antes de actuar

1. Lee `AGENTS.md`, `CLAUDE.md`, sus lecturas obligatorias,
   `docs/05-NEXUS-0-SPEC.md`, `docs/ECHO-3-ACCEPTANCE.md` y
   `docs/SIM3-DESIGN.md` (incluida custodia).
2. Lee la propuesta, los resultados v5–v8 y el borrador final. Contrasta
   afirmaciones importantes con datos y código: «sólo bloqueaba feature 504»
   no es correcto; también faltaban ahorro y significación.
3. Comprueba cambios locales, procesos pertinentes, memoria y disco. Acuerda
   un solo escritor si hay otro agente activo; no mates procesos ajenos.
4. Preserva las fuentes y artefactos congelados. Los cambios son versionados
   y aditivos; no modifiques contratos previos para hacer pasar resultados.
   No hagas commits, push, publicaciones ni borrados sin encargo específico.

No segundo bus, no LLM dentro de NEXUS-0, no Akida, no kernel, WSP=16 B,
estado cognitivo entero. Reutiliza el modelo y las tablas existentes; cualquier
extensión necesaria debe ser versionada, acotada y documentada, no otro núcleo
cognitivo ni una tabla oracle que se haga pasar por aprendizaje.

## Estrategia: cambiar de hipótesis, no perseguir una tabla

Empieza por **A: calibración de costes de movimiento**. Si una prueba mínima
lo refuta o muestra falta de margen, pasa a **B: calibración del modelo de
ejecución** o **C: calibración perceptiva**, según la evidencia. La propuesta
describe los controles y límites de cada alternativa.

No tienes que implementar las tres si A funciona; tampoco debes insistir en A
sólo porque está primero. Puedes elaborar D/E dentro del mismo objetivo y
dominio si los tres anteriores fallan. Una ampliación material fuera de ese
alcance, cambios de contrato superior, recursos externos o hardware requieren
decisión de Roger.

Para cada rama:

1. **Contrato previo:** variable aprendida, qué observa realmente el agente,
   mecanismo común A/B/C, brazos, distribución de condiciones, presupuesto,
   coste primario, geometrías, reglas de selección, estadística y parada.
2. **Prueba mínima de identificabilidad y margen:** ¿puede aprenderse desde
   la interfaz? ¿puede influir en decisiones? ¿existe ahorro suficiente incluso
   con calibración perfecta? No ejecutes miles de casos antes de responder.
   En A, descarta el error de costes direccionales cuya suma se cancela entre
   rutas con los mismos extremos; comprueba alternativas realmente distintas.
3. **Implementación mínima:** observación → actualización real de parámetros
   → exportación acotada → restauración limpia → influencia en el mismo planner.
   Ninguna lectura privada de la geometría, seed o solución durante aprendizaje
   o ejecución del consumidor.
4. **Comparación justa:** nominal competente, aprendido, retirada/permutación
   del aprendizaje y oracle sólo externo como cota. Mismas capacidades, datos
   de entrada y gates. No sustituir scratch por un agente que no sabe moverse.
5. **Resultado público:** tablas completas, coste escolar + mismo examen,
   errores y regresiones, incertidumbre, cobertura y efecto causal del payload.
6. **Autocrítica y decisión:** continuar, revisar un factor, cambiar de rama
   o descartar esta variante. Escribe qué resultado justificaría cada opción.

No basta con copiar costes verdaderos dentro del agente y llamarlo aprender.
Tampoco basta con mostrar menor error del modelo, más cobertura o una Q
distinta: tiene que mejorar una misión nueva y pagar el coste que se declara.

## Política de persistencia y prevención del bucle

No termines al primer rojo con «no hay candidato». Si quedan hipótesis seguras,
autorizadas y razonables, ejecuta el siguiente experimento discriminante.

Trabaja en ciclos públicos acotados. Antes de cada ciclo fija límite de
variantes, movimientos, tiempo y volumen de artefactos, con una regla de
parada por falta de progreso. Como pauta, no encadenes más de dos revisiones
del mismo mecanismo sin evidencia nueva que cambie el diagnóstico: entonces
revisa otra rama. Esto limita el bucle, no determina significación estadística.

Antes de renovar un ciclo, compara explícitamente lo aprendido con su coste.
No repitas corridas deterministas para simular más evidencia. No filtres salas
por resultados. No cambies métricas, N, horizonte de amortización o criterios
después de mirar el examen. Registra todas las variantes y su selección.

Si una búsqueda extensa requiere más recursos de los razonables para el
workspace, presenta el coste y pide dirección; no llenes el disco ni lances
campañas indefinidas. El objetivo «hasta verde» no garantiza que exista una
solución ni autoriza ignorar bloqueos humanos o fabricar un certificado.

## Razona críticamente sobre tu propio trabajo

Mantén un registro de decisiones. Para cada experimento entrega una
justificación breve y verificable con estos apartados:

- **Hipótesis y predicción:** qué debe ocurrir si tienes razón.
- **Evidencia:** datos y referencias exactas, separados de interpretación.
- **Explicación rival:** otra causa que produciría el mismo resultado.
- **Prueba discriminante:** cómo distinguirlas con el menor cambio posible.
- **Autorrevisión:** qué error de implementación, control injusto, selección
  de datos o fuga podría estar favoreciendo tu propuesta.
- **Actualización:** qué creencia abandonas o mantienes y por qué.
- **Siguiente decisión y criterio de parada.**

No se pide razonamiento interno privado ni una narración interminable: se
piden supuestos explícitos, argumentos contrastables y pruebas. Busca refutar
tu candidato antes de defenderlo. Revisa también conclusiones anteriores:
fracasar con un suelo pesimista no descarta todo tratamiento de incertidumbre;
cero conflictos en A no demuestra ausencia de aliasing fuera de A.

## Criterios de éxito y coste

Fija un contrato específico de la rama antes de medir y vincúlalo al contrato
superior. Éxito de misión y restricciones duras tienen prioridad sobre coste.
No abarates el resultado abandonando misiones o comparando sólo las salas que
te convienen. Publica todos los casos y también la comparación entre éxitos
conjuntos; conserva la protección frente a fallos nuevos del control.

Para A, el coste principal será energía simulada medida; para B/C conserva
esa pregunta de economía de misión salvo que Roger apruebe prospectivamente
otra. No presentes unidades simuladas como julios físicos ni escondas tiempo,
movimientos, cómputo o memoria que empeoren.

Exige separadamente amortización de **escuela + el mismo bloque de examen**.
No elijas después un despliegue enorme que haga desaparecer el coste inicial.
Una proyección de punto de equilibrio es secundaria, requiere ahorro positivo
defendible y no convierte en verde un bloque que no lo consigue.

Registra prueba estadística, intervalos, multiplicidad, N y potencia con
supuestos explícitos antes de confirmación. No copies mecánicamente un test
de movimientos a una pregunta distinta ni aflojes el nivel de evidencia para
aprobar. El cambio de variable y contrato debe quedar visible, sin reinterpretar
como verdes los experimentos históricos.

## Separar desarrollo de confirmación

Usa un generador versionado con suficiente capacidad y exclusión geométrica
comprobada. Los resultados ya observados son desarrollo. Los cambios de
distribución escolar y representación deben separarse o evaluarse mediante un
diseño declarado; no mezcles factores y atribuyas todo a uno.

Tras selección, congela un candidato y una confirmación pública prospectiva
con tamaño y reglas fijados. Si la usas para depurar, deja de ser confirmación.
La búsqueda A/B/C/D debe resolverse **antes** del examen final, no probando
candidatos sucesivamente sobre el mismo C hasta encontrar un ganador.

No abras confirmaciones finales repetidas hasta que una pase. Un fallo
reservado no se borra; cualquier campaña nueva exige protocolo independiente,
registro del intento anterior, control de selección y autorización pertinente.

## Infraestructura, aislamiento y auditoría

- Congela un manifiesto explícito y completo de dependencias, código del
  consumidor, criterios, recursos y configuración. No cambies `inventory()`
  histórico. Añadir una fuente ajena no debe invalidar una auditoría; cambiar
  una dependencia sí. Comprueba antes y después de la ejecución.
- Conserva trazas reconstruibles de aprendizaje, no sólo el payload final.
- El nuevo consumidor debe estar realmente aislado del evaluador y de los
  mundos privados; una igualdad con ejecución local no prueba aislamiento.
- Exporta sólo parámetros aprendidos permitidos; limpia estado episódico;
  parámetros congelados durante examen, percepción y seguimiento activos.
- Prueba serialización, capacidad, terminalidad, truncamiento, captura única,
  ausencia de datos oracle y misma semántica de adjudicación entre brazos.
- Añade mutantes que el auditor deba rechazar: reporte manipulado, caso omitido,
  payload o dependencia cambiados, calibración injertada desde verdad privada,
  aprendizaje en examen, mapa/seed filtrado, costes mal sumados, éxito falso,
  doble apertura, concurrencia, crash y B rojo seguido de intento de C.
- Ejecuta regresión TRANSFER-3 y auditoría fresca. La suite global tuvo un OOM
  comunicado en `test_dynamic1.py`: registra límites y alcance real, investiga
  proporcionalmente y no afirmes que toda la suite pasa si no la completas.

## Custodia: aquí sí necesitarás a Roger

No generes B/C reales ni secretos en este árbol o en otro lugar accesible a
los mismos agentes. No pidas secretos por chat. `.gitignore`, otra carpeta
o permisos bajo el mismo usuario no son custodia externa.

Prepara y prueba toda la integración con fixtures explícitamente públicos.
Cuando exista candidato y arnés verificados, pide a Roger el custodio/principal
externo y entrega instrucciones precisas. No te declares bloqueado por esa
custodia mientras puedas completar trabajo público independiente.

La campaña final necesita protocolo y compromisos B/C publicados **antes del
entrenamiento A final**, congelación posterior del payload, B una vez, auditoría
de B y C sólo si B pasa, bajo el mismo freeze. La revelación ocurre después
de abrir el pestillo y debe verificarse contra aviso, sello e inventario antes
de entregar datos. Un crash consume independencia. No hay verde sin esa cadena.

## Entrega y cuándo puedes decir «verde»

Guarda contratos, resultados, diario de decisiones, código, tests, manifiestos,
artefactos, hashes y comandos. No sobrescribas intentos anteriores. Actualiza
`docs/NOW.md` indicando qué está demostrado y quién tiene la siguiente acción.

Distingue siempre:

1. **Efecto público observado:** todavía selección y desarrollo.
2. **Candidato confirmado prospectivamente:** todavía no cierre de custodia.
3. **Campaña final válida y auditada:** único punto donde se puede evaluar
   `transfer3_green=true` contra todas las exigencias del contrato.

Si obtienes el tercero con todos los criterios cumplidos, entrega el certificado
y el alcance exacto. Si no, continúa con la siguiente hipótesis justificada o
pide la intervención material que falte. Si agotas las vías razonables,
documenta el límite con evidencia en vez de fingir una solución.

**Sé persistente con el objetivo, flexible con las hipótesis y estricto con
la evidencia. Que el plan pueda cambiar no significa que el criterio pueda
moverse después de conocer el resultado.**
