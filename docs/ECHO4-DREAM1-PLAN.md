# E4-DREAM-1 — exploración cortical offline inspirada en Dream-RSI

2026-09-22. **E4-DREAM-1 verde en su perfil experimental WORLD-1 restaurado:
DREAM-D v3 cerrada con auditoría reconstructiva válida y cero hallazgos.**
Quince llamadas reales, 60 propuestas válidas y tres exámenes nuevos:
300/298/302 sobre 320 frente a fijo 190/230/220 y aleatorio 238/246/237.
Cumple los márgenes +32/+16 en cada ciclo; cero errores/terminalidades en
diez brazos. Recibo `dream1_green=true` (`965ce6cb…`), 82 fuentes intactas.
Sin Qwen y sin feedback empatan: no se acredita beneficio exclusivo del LLM.
926 pruebas, 925 aprobadas y un fallo esperado en ese cierre.
MAINTAIN cerrada en su perfil virtual condicionado a modelo conocido:
[B/C/D y auditoría válidas](ECHO4-MAINTAIN1-FINAL-RESULTS.md), sin activar
LLM basal. [OTHER cerrada](ECHO4-OTHER1-RESULTS.md) en predicción observacional
discreta; [INTERACTION B/C/D cerradas](ECHO4-INTERACTION1-BCD-RESULTS.md) en
decisiones de un paso con ventaja posformación, no de vida completa.
[RELATION-A verificada](ECHO4-RELATION1-A-RESULTS.md): historia ordenada, todavía
sin ventaja transferible. Siguiente RELATION-B. ECHO-4 completo sigue abierto.
[Contrato v3](ECHO4-DREAM1-D-V3-DESIGN.md) ·
[Resultados y límites v3](ECHO4-DREAM1-D-V3-RESULTS.md).

**V1 y v2 conservan su rojo.** V2: nueve llamadas reales, 730/960 frente a
fijo 590/960 y aleatorio 674/960; falla el umbral por ciclo en dos etapas.
[Contrato v2](ECHO4-DREAM1-D-V2-DESIGN.md) y
[resultados v2](ECHO4-DREAM1-D-V2-RESULTS.md).
Primer incremento conservado: archivo/replay de intentos nativos nominales, sin LLM,
con contrato propio en [DREAM-A](ECHO4-DREAM1-A-DESIGN.md) y
[banco verificado](ECHO4-DREAM1-A-RESULTS.md). El antecedente B/C/D v1 añadió diagnóstico
SELF nativo, seis llamadas reales a Qwen y tres ciclos nuevos. La mejora
histórica no se convierte en la ventaja exigida en examen: DREAM 130/240,
fijo 150/240, aleatorio 155/240. Auditoría válida, `dream1_green=false`.
[Contrato congelado](ECHO4-DREAM1-BCD-DESIGN.md) y
[resultados y límites](ECHO4-DREAM1-BCD-RESULTS.md).
Depende de continuidad/procedencia verificables. Rama de investigación tras
E4-CONTINUITY-1, sin bloquear el programa basal sin LLM. Hardware después
del software; METAVERSE-1 permanece último.

## Referencia y diferencia

[Dream-RSI, sección 3](https://arxiv.org/html/2609.14858v1#S3), reutiliza
árboles de descubrimiento ejecutados para evaluar políticas de exploración.
Un agente de desarrollo modifica esa política; modelos, evaluador e
interfaces permanecen fijos. El replay solo cubre continuaciones registradas.
La selección que incluye al incumbente no empeora su puntuación histórica,
pero no garantiza mejora futura. «Dreaming» es una metáfora operacional.
El [repositorio de los autores](https://github.com/zhengkid/Dream-RSI) indica
que el código completo y scripts de reproducción están en preparación en
la fecha de consulta. Adoptamos una inspiración arquitectónica, no afirmamos
replicar sus resultados ni incorporamos código o dependencias suyas.

## Qué queremos construir en ECHO

Pregunta: **¿puede el córtex local proponer una estrategia que aproveche
experiencia verificada para investigar mejor, con un presupuesto fijo de
interacciones nuevas?** Los costes totales de colección, replay e inferencia
se publican aparte; el límite de 12 pasos no iguala todo el cómputo.

El adaptador existente `nexus0/tools/qwen_cortex.py` está orientado a letreros
y salida atómica restringida. No es un optimizador de estrategias. Podemos
reutilizar la infraestructura local de inferencia mediante el nuevo
`echo4/dream_qwen.py`, offline opt-in; no se cambia su gramática de producción.
La campaña identifica archivo, SHA-256, cuantización, servidor y parámetros
de Qwen3-4B-Instruct-2507 Q4_K_M. Produce candidatos válidos; su contribución
no superó los controles en el examen v1. `dream_v2.py` añade feedback y
selección robusta: mejora frente a fijo, pero no alcanza la ventaja exigida
frente a aleatorio en todos los ciclos. V3 añade dos ensayos y ramas
condicionadas por evidencia, sin cambiar fuentes SELF ni su presupuesto
online. Supera el examen, pero empata con la búsqueda sin Qwen. No utiliza
el proyecto Discord y no prueba que la inferencia cara sea necesaria aquí.

Qwen conserva sus pesos. Lo que persiste y mejora es un artefacto de estrategia
validado, no una afirmación autobiográfica ni un autoentrenamiento implícito.
Fine-tuning/RL de pesos sería otro contrato y no forma parte de E4-DREAM-1.

## Subfases y entregables

| Subfase | Implementación | Evidencia y estado actual |
|---|---|---|
| DREAM-A, primer incremento verificado | Historial privado con padre, contexto público, versión, coste y checkpoint; replay de ramas nativas observadas. | 3 árboles, 31 nodos, 28 intentos y 62 consultas; reconstrucción válida, 31 tests nuevos. No cierra DREAM-1. |
| DREAM-B | Qwen local propone prioridades, cuotas y presupuesto: seis ensayos en v1/v2, ocho en el perfil v3. | V3: 15 llamadas reales, 60 propuestas válidas; pesos intactos. |
| DREAM-C | Selección offline con incumbente, peor margen por lote, feedback y evaluador fijo. | V3: historial 1.040→1.360→1.680 antes de cada selección; mejora inicial y dos conservaciones, sin beneficio exclusivo frente al selector sin Qwen. |
| DREAM-D | Ensayos nuevos, ampliación posterior de historial, versiones, reversión y reconstrucción. | V3 verde: 300/298/302 sobre 320, márgenes +32/+16 superados en cada ciclo, auditoría válida. V1/v2 rojas preservadas. |

Primera superficie editable: **orden y reparto del presupuesto de exploración
experimental**, no el núcleo, las recompensas, el gate ni los criterios de
confirmación SELF. Preferimos una representación declarativa ejecutada por
un intérprete fijo a ejecutar Python arbitrario producido por el modelo.

El ciclo implementado es: experiencia → historial verificable → propuestas
corticales → replay → validación nueva → estrategia aceptada → experiencia.
Si el modelo local no genera candidatos válidos o no supera controles,
publicar el resultado rojo. Una búsqueda determinista sirve de control y
para probar infraestructura, no se presenta como Qwen «soñando».

## Fronteras de autoridad e información

- Sin segundo WSP/CAM/T/Q. Artefactos del laboratorio no son un bus cognitivo.
- NEXUS-0 y bancos basales siguen con `cortex_calls=0`; el ensayo cortical
  separado declara explícitamente sus llamadas, latencia y tokens. No se
  esconden llamadas de Qwen bajo el verde del banco sin LLM.
- Hipótesis no es hecho CAM. No entregar causas privadas, registros físicos
  exactos ni resultados futuros al candidato durante la evaluación.
- Checkpoints: acceso del custodio solamente. Exportar a Qwen únicamente
  historia pública permitida. Igual WSP no implica igual estado oculto.
- Rama no observada: desconocido o nueva ejecución medida. La imaginación
  aproximada de T sería otra condición experimental, nunca replay exacto.
- Qwen no cambia el evaluador, las pruebas, umbrales, archivos del núcleo,
  certificados previos ni permisos. Sin shell/red/autoimplantación de código.
- B/C publicados de SELF son regresiones, no un nuevo holdout para DREAM.
- Candidato aprobado se versiona; el operador conserva parada y reversión.
  La promoción experimental nunca se convierte en despliegue automático.

## Aceptación fijada y resultado v1

El [contrato B/C/D](ECHO4-DREAM1-BCD-DESIGN.md) fijó antes del examen las
particiones, semillas, tres ciclos, presupuestos y umbrales: por ciclo, al
menos +8 aciertos frente a fijo y +4 frente a aleatorio sobre 80 casos,
sin errores/terminalidades, sin regresión frente al incumbente, invariantes
intactos y auditoría reproducible. V1 falla ambos umbrales de ventaja en los
tres ciclos. No se reajustan tras observar el resultado. Los números del
paper no son promesas de rendimiento para el modelo local.

**V2 implementada y medida:** conserva los márgenes proporcionales +10/+5
puntos por ciclo y cambia a muestreo estratificado, 320 casos por ciclo.
Pasa frente a fijo en los tres, pero solo pasa frente a aleatorio en el primero.
El umbral no se rebaja por quedar a un acierto en el segundo; en el tercero
la ventaja es de solo +2. La cota posterior de aquel catálogo es 245 en
el segundo examen, frente al mínimo 246. Esto motivó los ensayos más
informativos y el archivo condicional de v3, con contrato/examen nuevos.
V1 y v2 se conservan rojas; sus casos abiertos ya son desarrollo.

**V3 cerrada:** 900/960, márgenes por ciclo superados, auditoría válida y
`dream1_green=true`. El sistema mejora cómo explora utilizando su historia;
el control sin Qwen empata. No demuestra conciencia subjetiva, alma, mejora
de los pesos de Qwen ni autorreparación general. Su integración posterior se evalúa en
E4-INTEGRATE-1 con brazos córtex OFF/ON separados; el núcleo debe seguir
funcionando con el córtex apagado.
