# S6-B16 — registro de ejecución y validación

El 4 de octubre se confirmó y registró el cierre negativo del microensayo B15:
terminó a las 18:12 Madrid, con 12 propuestas, 1280 partidas físicas en A y
13 comparaciones de replay idénticas. El mejor resultado agregado fue 381
frente a 378 con tres regresiones individuales; no habilitó el piloto. La
[revisión](ECHO45-S6-B15-MICRO-REVIEW.md) conserva el diagnóstico y el recibo
de reconstrucción de artefactos. No se alteraron sus fuentes ni resultados.

Se implementó B16 para comprobar las correcciones antes de abrir las fases
largas. Conserva la mayor ganancia local de niveles y los contraejemplos de
pérdida en el feedback; permite refinar una propuesta propia con ganancias
locales aunque el total sea negativo. Mantiene tres intentos por objetivo,
la contabilidad real por operador, las pausas de familia, la gramática y todas
las puertas V1–V4. Los ejemplos se muestran con nombres de features y las
constantes comunes se codifican una vez. El visor ahora espera un diario existente.

Validación previa: **14/14 pruebas nuevas**, **20/20 de regresión B15** y
**27 contextos** comprobados con el tokenizador real. El máximo es
**2802/3072 tokens**. Todos los tamaños de contexto conservan la ganancia y
la pérdida del objetivo cuando existen, además del último recibo. Los tests
reconstruyen la fase con un ejecutor simulado y verifican la ruta del subproceso
de auditoría; las auditorías con ejecución independiente siguen pendientes.

Perfil congelado a las 19:12:49 Madrid:
`bc384326ef7436fca30a0e8eb9f781a7c4f16c5f222b1ea67a59f950a949266c`.
Son 183 fuentes, incluidas las 174 B15 sin cambios. Ninguna de las enumeradas
en `profile.json` se debe editar durante la ejecución. El archivo de
cualificación es `lab/seed/s6b16-20261004/validation.json`.

El servicio **`echoai-s6b16` arrancó a las 19:14:00 Madrid**, PID inicial 474404,
y se detuvo a las 19:17:30 después de las 160 partidas de base/replay, antes
de la primera llamada al modelo. La comparación Python confundió tuplas en
el informe vivo con listas de JSON. Los registros persistidos de la base,
el replay y B14 coinciden exactamente. Dos partidas A de diagnóstico
identificaron el problema; quedan contabilizadas, con 162 partidas al reanudar.

Se corrigió el comparador mediante un módulo separado y cuatro pruebas de
regresión, sin editar ninguna de las 183 fuentes congeladas. El fallo original,
los diagnósticos y la enmienda están en la [recuperación declarada](ECHO45-S6-B16-RECOVERY1.md).
El recibo se congeló a las 19:27:00 Madrid, antes de realizar llamadas al modelo.
**`echoai-s6b16-recovery1`** es el servicio de continuación; conserva las 160
partidas previas en caché y utiliza el mismo plan, semillas, prompts y puertas.
Arrancó a las **19:27:16 Madrid**, PID inicial 474912. A las 19:27:43 había
superado la paridad íntegra y comenzó `micro/previous-740101/000`, la primera
de 24 llamadas. Se comprobó el proceso real `llama-cli` y el visor activo;
el log de recuperación no mostraba un nuevo error en esa comprobación.

El diario se crea antes de abrir el visor para evitar la carrera observada en
B15. El observador es pasivo y nunca se usa como fuente de instrucciones para
el agente. Un servicio separado mantiene la ejecución tras cerrar esta sesión;
no mantiene el portátil trabajando si se suspende o apaga.

| Fase | Estado al arranque | Condición para continuar |
| --- | --- | --- |
| Micro B16 | En ejecución | Base/replay exactos, 24 intentos registrados, algún candidato actualizado con ≥2 niveles agregados nuevos, cero pérdidas individuales y replay idéntico |
| Piloto | Pendiente de micro | Parte de SEMILLA sin historial de calibración; ECHO > FIJO, ≥2/3 victorias, ninguna derrota y mejora aceptada |
| Auditoría de piloto | Pendiente de piloto | Reconstrucción de los 54 veredictos en otro proceso con caché nueva; también se ejecuta si el piloto es negativo |
| Campaña y auditoría | Pendientes de piloto promovible y auditado | 30 propuestas por brazo, ventaja ECHO y conservación, reconstrucción independiente |
| Examen | Cerrado | B1–B5 completos: mejora frente a SEMILLA, FIJO y SIN FILTRO, conservación y auditoría |

El micro compara controlador previo y corregido, tres semillas emparejadas y
cuatro intentos por brazo. El primer prompt es idéntico; los siguientes usan
solo el historial propio. No se transfiere al piloto ningún parche del micro
ni se proporcionan los ganadores humanos de PROBE2. Una mejora en A se marca
`A_ONLY_PASS`; no se considera aceptada sin conservación protegida.

Previsión tras la recuperación: **1,5–2,5 horas para el micro**, aproximadamente
entre **21:00 y 22:00 Madrid del día 4**, según políticas repetidas y coste de los
prompts de refinamiento. B15 empleó 42,5 minutos con 12 llamadas y 1280 partidas;
B16 tiene hasta 24 llamadas y 4000 partidas. No se toma la velocidad de las
primeras partidas fáciles como ritmo representativo del conjunto.

Si supera el micro: piloto/preflight unas 4–7 horas adicionales; auditoría
unas 3–6 horas. Campaña con auditoría, aproximadamente 12–20 horas más;
examen, 1–3 horas. Son estimaciones condicionales, no una fecha para un verde.
Un fallo de una puerta cierra la condición; una discrepancia de replay o
custodia detiene el instrumento. Suspender el equipo retrasa los cálculos.

Estado actual: `lab/seed/s6b16-20261004/status.json`; proceso:
`recovery1/process.log`; el log fallido original sigue en `run-process.log`;
cierre del micro: `micro.json`; criterios:
[contrato B16](ECHO45-S6-B16-DESIGN.md). Los resultados y la documentación
se actualizan localmente. S6 sigue abierto hasta cumplir su examen completo.

Comprobación posterior, 4 de octubre a las 23:15–23:17 Madrid: el micro
terminó a las **20:34:56**, con estado **MICRO_NO_PROMOTION**. Empleó 67,5
minutos desde la reanudación del micro; terminó antes de la previsión porque
la caché evitó volver a ejecutar varias políticas repetidas. Se completaron
24/24 propuestas y el presupuesto conserva 1762 partidas físicas, incluidas
las dos de diagnóstico. Coste de API: 0 euros.

| Brazo del micro | Propuestas | Mejor total A | Propuestas que pasan V3 |
| --- | --- | --- | --- |
| Controlador anterior | 12 | 378 | 0 |
| Controlador actualizado B16 | 12 | 378 | 0 |

La revisión recalculó los 24 resultados por partida y comprobó 24/24 replays
de candidatos idénticos, los hashes de artefactos, las fuentes congeladas y
el recibo de recuperación. Es una reconstrucción de registros existentes,
sin nuevas partidas; no sustituye una auditoría independiente con caché nueva.
El log posterior a la recuperación no contiene otro bloqueo ni traceback.

El controlador actualizado sí dirigió seis refinamientos al objetivo HOLD
propio. Sus nueve propuestas HOLD, contando los tres intentos iniciales,
conservaron +5 niveles locales, pero perdieron entre 7 y 9 en otros casos:
totales de 374 o 376 sobre la base de 378. Las tres propuestas REVALIDATE_NOOP
quedaron en 378. Todas las propuestas de ambos brazos usaron el operador
solicitado. La selección y el enlace funcionan en este micro; todavía falta
producir una guarda que conserve las ganancias y evite las pérdidas. Ninguna
de las guardas HOLD actualizadas utilizó `level` ni `world_events`.

El piloto, su auditoría, la campaña y el examen **no se iniciaron**. La cadena
se cerró correctamente al fallar la puerta del micro; las previsiones de esas
fases quedan sin activar. El servicio de recuperación terminó. Los visores
de B13/B15 que siguen abiertos muestran diarios históricos y no son pruebas
en ejecución. S6 permanece abierto y necesita una condición nueva antes de
reanudar experimentos; no hay un tiempo restante de ejecución S6 en este momento.

La [investigación posterior de B16](ECHO45-S6-B16-FORENSICS.md) identifica el
alcance excesivo de las guardas, el retraso entre consumo y primera acción
distinta, y las limitaciones del selector de refinamiento. Incluye un análisis
retrospectivo de síntesis de guardas, con sus límites y controles necesarios.
