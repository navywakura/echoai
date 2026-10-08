# DREAM-D v3 — exploración condicionada por evidencia

2026-09-22. Contrato fijado antes de abrir el examen nuevo. V1 y v2 siguen
rojas e inmutables. V3 no cambia sus umbrales ni concede verde retrospectivo.

## Hipótesis y desarrollo previo

La cota del catálogo v2 era 245/320 en su segundo ciclo, frente a 246
necesarios. El límite no estaba solamente en ordenar acciones: faltaban
intervenciones que generasen observaciones discriminantes dentro de 12 pasos.

Un cribado de desarrollo del prior enumeró las 6.561 secuencias de ocho
acciones después del ensayo corto original. Las predicciones se trataron
como predicciones, nunca como recibos. Las repeticiones puras largas resultan
frecuentemente inseguras. Una secuencia de carga/enfriamiento puede ser
insegura al inicio y segura tras descartar hipótesis mediante una prueba real.

El perfil conserva **los seis ensayos antiguos en sus índices originales**
y añade dos de ocho pasos:

| Índice | Acciones nativas | Motivación |
|---|---|---|
| 6 | 0,1,0,1,0,0,0,0 | Contraste corporal fuerte, condicionado por seguridad |
| 7 | 0,0,1,0,0,1,2,2 | Contraste equilibrado con observaciones térmicas finales |

0=carga/acercamiento, 1=enfriamiento/evitación, 2=espera. Son las ecuaciones
WORLD-1 originales, no actuadores nuevos. Ninguna secuencia es universalmente
segura: se pronostica bajo **todas** las hipótesis todavía compatibles.

Desarrollo físico independiente del cribado: cuatro cuerpos v1 abiertos y
los 48 cuerpos v2 abiertos, 1.040 condiciones. Se ejecutan realmente las
ramas admisibles antes de consultarlas por replay. El selector histórico
entre ocho programas sistemáticos obtiene 76/80 y 292/290/298 sobre 320.
Fijo: 60/80 y 180/210/200; aleatorio: 77/80 y 227/232/248. La pérdida en el
pequeño lote v1 permanece visible: no hay dominancia universal. Los tres lotes
estratificados de desarrollo sí muestran márgenes suficientes para intentar
el nuevo examen. No son confirmación. Ninguna inferencia Qwen interviene en
estos números. [Artefactos](../lab/echo4/dream1-d-v3-development/report.json).

## Implementación y separación de responsabilidades

- Perfil versionado `echo4-dream-conditional-probes-v3`; DSL versión3:
  permutación de ocho ensayos, ocho cuotas binarias y presupuesto4..12.
- Reutiliza calibración, prior, `forecast`, consumo/diagnóstico y validación
  de recibos de SELF; física, ejecutor, gate, CAM y WSP originales intactos.
  El adaptador cambia únicamente selección/catálogo y archivo de ramas.
- Cada nueva prueba restaura el cuerpo inicial mediante el laboratorio,
  pero conserva exclusiones aprendidas de observaciones previas. No se
  presenta la restauración como autorreparación o vida ininterrumpida.
- El archivo identifica la **ruta previa** además del ensayo: no entrega
  una prueba condicional sin sus antecedentes. Hasta22 ramas, 262.144 bytes
  por archivo, máximo dos pruebas por ruta y12 pasos. Una rama ausente
  devuelve desconocido y consume presupuesto; no llama a física ni al LLM.
- Una ruta del archivo se recoge solo después de ejecutar su antecesora;
  una predicción favorable no crea hechos. Hash de catálogo, calibración,
  WSP inicial, tokens, recibos y procedencia impiden cruces de contexto.
- Qwen propone exclusivamente prioridades/cuotas; no escribe código
  arbitrario, modifica pesos, consulta causas exactas o controla el gate.
- El núcleo NEXUS-0 mantiene el córtex apagado. La rama lenta experimental
  no introduce otro bus ni cambia los16 bytes del WSP.

## Protocolo prospectivo

Tres ciclos,16 cuerpos ×20 condiciones =320 casos por brazo/ciclo. Dominio
H65..96, theta40..60, cuatro cuerpos por banda H de ocho unidades. Semilla
`260924`, sin reemplazo. Se excluyen todos los cuerpos DREAM-v1/v2, fixtures
anteriores declaradas y exámenes SELF B/C. Pruebas unitarias v3: H56..59,
fuera del dominio. El muestreador no ejecuta física ni evalúa resultados.

El lock de fuentes, catálogo, corpus, recetas, criterios y modelo se escribe
con fsync antes de ejecutar el examen. No cambiar semilla, cuerpo, catálogo,
umbrales ni fuente tras verlo. El nuevo perfil empieza con orden fijo;
la política v2 no se reinterpreta con índices nuevos: se conserva también
como control legado usando su intérprete y catálogo originales.

Por ciclo:

1. Revalidar/usar solamente historia ya abierta. Selección robusta por peor
   margen de resolución frente a fijo por lote, después resolución total
   y menor coste en pasos. No usa etiquetas del juez.
2. Cinco llamadas reales de Qwen: inicial, revisión con feedback, segunda
   sin feedback y dos sin historial. Hasta cuatro propuestas por llamada.
3. DREAM usa inicial+revisión; sin-feedback usa inicial+segunda sin feedback;
   sin-historial usa sus dos llamadas. Cada brazo tiene dos llamadas y hasta
   ocho propuestas, sin corregir a mano respuestas inválidas. Se publican
   cantidades válidas y distintas: igualdad de cupo no garantiza diversidad.
4. Fijar selección en disco antes de construir los nuevos casos. Ejecutar
   brazos emparejados. Promover o conservar/revertir según evidencia.
5. Solo después del examen: recoger ramas completas, comprobar paridad y
   añadirlas al historial del siguiente ciclo. Versiones enlazadas por hash.

## Controles y cierre

Diez brazos: DREAM, incumbente v3, fijo, aleatorio por caso, sin Qwen,
sin feedback, sin historial en prompt, sin selección replay, adaptativo
minimax por observación y legado v2. Los nueve del perfil v3 tienen idéntico
catálogo, observaciones permitidas, veto y máximo12 pasos. Legado dispone
de12 pasos pero conserva sus seis ensayos: ancla adicional, no comparación
aislada del algoritmo. Sin-Qwen selecciona entre los ocho programas
sistemáticos mostrados en el resumen histórico; no se oculta si empata/gana.

Semilla del control aleatorio: `260924 + ciclo*10000 + indice_caso`.
La condición real no entra en ningún selector. El evaluador privado solo
comprueba corrección y seguridad después. Las ablaciones son experimentales,
no prueba universal de causalidad o eficiencia energética.

Verde exige **en cada ciclo**:

- +10 puntos porcentuales frente al fijo: al menos32 aciertos adicionales.
- +5 puntos frente al aleatorio: al menos16 adicionales.
- Cero diagnósticos erróneos y terminalidades en todos los brazos;
  hipótesis verdadera retenida, CAM intacta, cero hechos falsos, límites.
- Ninguna regresión lexicográfica resolución/coste frente al incumbente,
  al fijo o al legado v2; promoción aceptada o incumbente conservado.
- Al menos una propuesta real válida en cada una de las cinco llamadas.
- Paridad exacta online/replay para los nueve brazos del nuevo perfil.

Además: tres ciclos completos, al menos una mejora histórica estricta,
fuentes/evidencias antiguas intactas, regresiones y auditoría reconstructiva
en un proceso nuevo. El informe **no** concede verde; únicamente el recibo
de auditoría puede emitir `dream1_green=true` si todo cumple. Un rojo se
conserva: no basta un agregado favorable, ni aprobar unit tests.

## Costes y límites

Qwen3-4B-Instruct-2507 Q4_K_M local y llama.cpp identificados por SHA256.
CPU4, GPU0, contexto8192, temperatura0, hasta15 llamadas,640 tokens generados
por llamada, timeout300s. Dos llamadas por brazo cortical y ciclo (comparten
la inicial donde procede). Se cuentan tokens, tiempos y fallos reales.

Se publican por separado: cribado previo, colección de desarrollo, coste
hundido de v1/v2, revalidación física de historia, calibración, pasos online,
nuevas colecciones, consultas/pasos representados por replay y cómputo de
auditoría. Más catálogo/archivo cuesta recursos; no es una mejora gratis.
No se equipara un token a un paso ni se inventan julios.

El verde será de **exploración diagnóstica restaurada en WORLD-1**, no
conciencia subjetiva, pesos autoentrenados, autorreparación, mejora general
ni integración del producto. Veinte condiciones comparten cada cuerpo:
no son muestras independientes para inferencia estadística universal.
Un empate con sin-Qwen no acredita ventaja exclusiva del LLM. MAINTAIN e
INTEGRATE siguen pendientes; hardware después y METAVERSE-1 último.
