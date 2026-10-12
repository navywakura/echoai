# PCWORLD-1 · runtime y primer piloto local

Autoridad: RESEARCH.md §13 y continuación solicitada por el usuario. Base: 75eb305.

## Alcance congelado antes de medir

1. Empaquetar Python y sus bibliotecas en un rootfs con manifiesto íntegro,
   montado sin `/usr` del host. Exportar/importar con identidad verificable.
   No se promete reproducir kernel, CPU ni tiempos de pared.
2. Habilitar caché persistente únicamente de propiedades puras del verificador
   sobre bytes observados. Toda ejecución de código candidato se repite: reloj,
   aleatoriedad y `/proc` impiden asumir que cualquier programa sea puro.
3. Conectar llama.cpp local con plantilla y tokenización antes de inferencia,
   hashes del GGUF y servidor, presupuesto compartido de 25.000 tokens por
   tarea/brazo, misma configuración en S/I2/F/E. No tocar NEXUS-0.
4. Añadir seis familias de reparación independientes de las cuatro fixtures,
   con bugs inducidos, referencias externas al candidato y casos no entregados
   a los roles. Son tareas nuevas de desarrollo, no benchmark oficial ni examen
   ciego. Un diagnóstico sembrado puede iniciar el ciclo en código defectuoso;
   se etiqueta por separado y no cuenta como fallo espontáneo del modelo.
5. Probar, revisar y congelar fuentes; ejecutar en segundo plano el piloto
   local y auditar resultados. Publicar costes y errores, incluso resultado nulo.

## Interfaces y decisiones

- Runtime → runner: capacidad Snapshot validada, no ruta arbitraria a `/usr`.
- Runtime → identidad/caché: fijar dependencias no certifica determinismo.
- Modelo → presupuesto: contar tokens de plantilla real y salida; separar
  CPU del candidato, supervisor e inferencia. Un fallo de contabilidad consume
  la reserva de forma conservadora.
- Corpus → crítico/verificador: mismo dominio público; referencias y casos de
  evaluación sólo en supervisor. CAM conserva evidencia; cada reparación se ejecuta.
- Piloto → cierre: esta muestra comprueba infraestructura y estima resultados;
  superioridad multiagente exige ablaciones y confirmación independientes.

## Registro de ejecución

- Runtime: rootfs de 597 archivos, archivo exportado de 35.758.080 bytes,
  identidad verificada tras restauración, sin herramientas del `/usr` host.
- Conector: GGUF oficial verificado; calibración local 201 tokens y 20,52 s
  con build CPU nativo. Se conserva el ensayo inicial más lento (93,95 s).
- Corpus: seis familias con fallos inducidos comprobados; referencias independientes.
- Revisión independiente: cinco hallazgos importantes reproducidos y corregidos:
  metadatos TAR antes de límites, dependencias del checker en la identidad,
  unión null/list de topología, contabilidad incoherente y testigos de caché
  ausentes. Pruebas focalizadas finales: 20/20; suite PCWorld: 162/162;
  regresiones seleccionadas: 59/59. Recibos de verificación en
  `PHASE2-VERIFICATION.json`.
- Se conserva el diagnóstico real que falló por envoltorio de input (332 tokens).
  La gramática ahora usa el dominio público. Otra calibración produjo un input
  elegible que no refutó el programa; no se presentó como contraejemplo.
- Código congelado en `2b68216`. Diagnóstico sembrado: 1/1 aceptado,
  1.704 tokens, auditoría válida de 51 recibos, ciclo de reparación observado.
- Piloto emparejado: 24/24 completados, 2/6 aceptados en cada brazo; 22.412
  tokens y 860 recibos auditados sin discrepancias. Sin contraejemplos retenidos:
  15 críticas elegibles no refutaron, tres inputs de rutas fuera del dominio.
  No hay mejora multiagente demostrada. Fuentes y contrato sin cambios.
- Informe, costes, autopsia y checklist publicados en la documentación local:
  `LOCAL-PILOT-20261013.md`, `LOCAL-PILOT-SUMMARY.json` y
  `CLOSURE-CHECKLIST.md`. Pendientes científicos conservados explícitamente.

Decisión T10: acotar caché a verificación pura; riesgo de una interpretación más
amplia: no se acelera la ejecución de candidatos arbitrarios. Se mantiene prohibida.
Decisión de cómputo: Qwen 7B autorizado; CPU local, procesos en segundo plano.
La descarga se detuvo a petición del usuario y se reanudó tras su aclaración.

Decisión de revisión: los bytes del verificador ejecutado por el supervisor
también necesitan identidad. Se incluyen stdlib, módulos nativos, dependencias
ELF y enlaces de funciones relevantes. La consulta tiene coste y no se presenta
como ahorro probado. El supervisor y sus módulos cargados siguen siendo confiables.

Menor aplazado: `pilot --dry-run` estima cuatro brazos aunque se especifique
`--arms` con menos. La estimación de los cuatro brazos principales es correcta;
para un diagnóstico de un brazo, dividir ese techo entre cuatro.

Fuera de esta revisión: seguridad del baseline ya revisada, calidad del modelo
(la decide el ensayo), estudio con potencia, T20 y S6. Se mantienen pendientes;
no se convierten en requisitos silenciosamente aprobados.
