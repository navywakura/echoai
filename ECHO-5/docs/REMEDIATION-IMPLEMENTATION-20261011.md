# ECHO-5: revisión experimental posterior al cierre r3

Autorizada el 11 de octubre de 2026. El resultado r3 y sus fuentes archivadas
permanecen históricos. Esta revisión no hereda su verde y no reabre S6.

## Contrato antes de medir

1. Exploración: tres actores con percepción parcial, mapa adquirido, parser,
   manipulación y planificador idénticos. Una frontera candidata es una pose
   alcanzable, todavía no visitada, desde la que se predicen celdas desconocidas.
   Cambia únicamente su selección: información estimada/coste, distancia o azar
   reproducible. Se conserva además el modo histórico `informative` sin cambiar
   su algoritmo ni los controles de la campaña anterior. Los tres mantienen su
   destino hasta alcanzarlo o invalidarlo; el azar no cambia de meta por paso.
   Los tres nuevos modos
   comparten la elegibilidad de fronteras; por ello no son una reproducción
   literal de Active Neural SLAM ni una evaluación de aprendizaje neuronal.
2. Misiones: corpus semántico escrito independientemente del parser del actor,
   con órdenes, ubicaciones y referencias explícitas; pruebas negativas y
   mutaciones. Se distinguen referencias semánticas de trayectorias nativas.
3. Transferencia: generador independiente con oráculo propio, estructuras
   irregulares, distractores y composiciones; resultados por familia y límites
   del lenguaje. Ni test labels ni programas testigo entran en el actor.
4. Búsqueda: seguimiento pasivo de todos los prefijos evaluados y retenidos de
   programas testigo de desarrollo. El testigo se compara DESPUÉS de buscar:
   no se introduce en las propuestas. Clasificar poda, presupuesto, gramática,
   ejecución inválida y equivalencia, sin convertir una poda en prueba de que
   no existe otra solución. Antes de cambiar la política se necesita ese dato.
5. Currículo: predicciones calculadas por demanda y por brazo; coste explícito
   de preparar, elegir, adquirir y evaluar. El selector adaptativo paga también
   las consultas a candidatos descartados. La evaluación queda separada.

## Primera ejecución

Piloto de desarrollo, no examen de cierre ni confirmación independiente.
`REMEDIATION-PILOT.json` fija perfiles, semillas y techos antes de ejecutarlo.
Se conservan todas las familias, incluso las adversas a ECHO. Comparaciones
pareadas por mundo, porcentajes absolutos, victorias/pérdidas/empates, acciones,
trabajo lógico y tiempo observado. La prueba binomial sobre discordancias y un
intervalo pareado exploratorio ayudan a dimensionar una confirmación posterior;
no son licencia para escoger después familias favorables.

Los gastos de comprobación y reproducción se publican fuera del presupuesto
del actor. Los fallos del instrumento se distinguen de resultados científicos
negativos. Ante un error se detiene la cadena y se conserva la evidencia.

## Custodia y ejecución

Pruebas de contrato y regresión antes del piloto. Después, fuentes congeladas,
proceso CPU en segundo plano, `status.json`, `process.log` y el Recorder existente
en `thought.jsonl`. Reproducción en otro proceso y comparación de resultados;
ningún generador arranca al importar el módulo. No se modifica un criterio de
aceptación en función del resultado y no se publica una release automáticamente.

Popper, ARGA, Stitch y búsqueda guiada motivan intervenciones posteriores
condicionadas al diagnóstico. Este piloto no implementa ni atribuye a ECHO
los resultados completos de esos trabajos. Véanse los límites y referencias en
[la revisión bibliográfica](LITERATURE-TRANSFER-20261011.md).
