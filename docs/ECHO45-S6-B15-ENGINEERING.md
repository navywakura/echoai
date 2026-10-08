# S6-B15 — implementación y arranque, 4 de octubre de 2026

El servicio `echoai-s6b15` arrancó a las **17:29:25 CEST (Madrid)** y cerró el
microensayo a las **18:11:58**, con `MICRO_NO_PROMOTION`: ninguna de las doce
propuestas pasó V3 en A. El piloto y las fases posteriores no arrancaron.
El [informe de revisión](ECHO45-S6-B15-MICRO-REVIEW.md) registra el resultado
y el recálculo de los artefactos. S6 continúa abierto. Las ventanas de tiempo
que figuran más abajo son las previsiones iniciales, ya canceladas por este cierre.

A las 17:33 se confirmó la paridad del microensayo: 80 partidas A y 80 de
replay, ambas con 378 niveles y digest `4458a4c2…` idéntico. Comenzó la primera
de las doce llamadas al modelo. B y el examen siguen sin abrirse. La verificación
posterior al arranque encontró cero cambios en las 174 fuentes congeladas.

| Fallo B14 | Cambio B15 | Comprobación realizada antes de jugar |
| --- | --- | --- |
| WAIT producía REVALIDATE | Operador obligatorio en gramática y comprobador | Se rechaza una propuesta de otro operador |
| Se contaba intención como exploración | Registro separado solicitado/propuesto/medido y acciones distintas | Un REVALIDATE etiquetado WAIT acredita REVALIDATE; V1 no acredita exploración |
| El +13 ya incorporado dominaba | Crédito residual filtrado por hash de la base vigente | Conserva un ensayo histórico y cero crédito residual después de promoción |
| Una guarda se justificaba en otra partida | Gramática construida sobre lecturas pertinentes de los casos seleccionados | `reset_known=1` no entra cuando solo coincide fuera de la selección |
| Alternancia 1/2 sin diversidad de familia | Pausa de familia tras dos intentos infructuosos, compartida con FIJO | Cambiar el número no evita la pausa; no se vacía la única familia disponible |
| Extremos ordenados como texto | Extremos numéricos, rangos y frecuencias | En A53 se recuperan 14 y 899 sobre registros B14 reales |

Los cambios están en `echo_arc/repair_experiments.py`, `seed/s6b15_prompt.py`
y el coordinador `seed/s6b15.py`. La ejecución de los juegos, la semilla, las
primitivas y las puertas V1–V4/B1–B5 se importan sin alteración. Esto modifica
la forma en que ECHO selecciona y verifica experimentos con el modelo; todavía
no acredita una nueva habilidad general ni una puntuación ARC oficial.

FIJO ahora recorre REVALIDATE, HOLD y COOLDOWN_CAP de forma cíclica y comparte
las comprobaciones de aplicabilidad. Es un control más fuerte y una condición
diferente del FIJO genérico previo. RANDOM, auxiliar del piloto, sortea parches
dentro de ese operador. Los resultados B14/B15 no constituyen por sí solos una
comparación causal aislada: cambian varias piezas y también las semillas.
El microensayo cruza específicamente vínculo y resumen para observar sus efectos.

Validación previa: **20/20 pruebas B15 y 25/25 de regresión B14**. Se revisaron
36 contextos históricos, cuatro variantes del microensayo y un contexto con
32 reglas y objetivo de refinamiento. El máximo fue **2668/3072 tokens** con
el tokenizador real del modelo congelado. Se conservó el último recibo en todas
las variantes. Esta cualificación ejecutó cero partidas y cero inferencias.

La primera cualificación encontró un caso vacío en el resumen de lecturas: se
intentaba tomar un mínimo sin observaciones. Se corrigió antes del congelado,
se añadió una prueba y se repitió la cualificación. Se conserva el intento en
`lab/s6b15-qualification-attempt1.log`; la cualificación final es
`lab/seed/s6b15-20261004/validation.json`. Una respuesta de modelo inválida se
cuenta como V1 y consume la llamada; un replay discrepante detiene el instrumento.

Perfil congelado: `bd164f87457ac85195e86aaba7410badac04c5e56eda8cc8e156606d8242a980`.
Incluye 174 fuentes: las 166 de B14, verificadas sin cambios, y ocho nuevas.
Los archivos enumerados en `profile.json` no deben editarse mientras corre.
El trabajo y los datos se mantienen locales, sin publicación a web o GitHub.

| Proceso/fase | Estado al arranque | Qué permite validarlo o continuar |
| --- | --- | --- |
| `echoai-s6b15` / microensayo | En ejecución, cuatro trabajadores CPU | Paridad 378 exacta, doce intentos registrados, replays idénticos; al menos un caso vínculo+numérico con >=2 niveles extra y cero pérdidas A |
| `echoai-s6b15-observer` | Visor local del diario A | Solo muestra registros observados; no decide ni alimenta peticiones |
| Piloto | Condicional, todavía sin iniciar | Tres semillas, ECHO > FIJO en total, >=2 victorias, cero derrotas y alguna mejora aceptada tras V3/V4 |
| Auditoría del piloto | Encadenada tras el piloto, aunque sea negativo | Reconstruir 54 veredictos en otro proceso y caché nueva con las mismas solicitudes y respuestas |
| Campaña y auditoría | Condicional al piloto válido y promovible | 30 propuestas por brazo, ventaja ECHO y conservación A/B; reconstrucción independiente exacta |
| Examen de cuatro brazos | Cerrado hasta pasar las fases anteriores | B1 mejora frente a SEMILLA; B2 > FIJO; B3 > SIN FILTRO; B4 conserva habilidades; B5 auditoría válida |

Estimación inicial a las 17:29, con el equipo despierto: microensayo 1–2 horas,
piloto/preflight 4–7 horas adicionales, auditoría del piloto 3–6 horas,
campaña con auditoría 12–20 horas y examen final 1–3 horas. Como referencia,
B14 empleó 3 h 01 min en el piloto y 2 h 28 min en la auditoría, reutilizando
muchas políticas repetidas. B15 busca mayor diversidad y puede ejecutar más
partidas únicas; por eso se amplía el intervalo. No se estima a partir de las
primeras partidas rápidas ni se promete una hora para obtener un verde.

Ventanas orientativas, **solo si cada puerta anterior pasa**: microensayo entre
18:30 y 19:30 del día 4; piloto entre 22:30 del día 4 y 02:30 del día 5;
piloto auditado entre 01:30 y 08:30 del día 5. La cadena completa podría llegar
entre la tarde del día 5 y la mañana del día 6. Se recalculará con las medidas
de B15. Un resultado negativo detiene la cadena y conserva los artefactos.

La ventana del observador original se cerró al arrancar antes de existir el
diario. Se creó el archivo vacío y se relanzó el visor como servicio separado;
no se cambiaron fuentes congeladas ni resultados. El servicio científico sigue
independiente de la conversación y del visor. El cómputo es local: la suspensión
o apagado del equipo retrasa/interrumpe la ejecución; no necesita conexión a una API.

Seguimiento: `lab/seed/s6b15-20261004/status.json`, `run-process.log`,
`micro.json` cuando termine, `pilot.json`/`pilot-audit.json` cuando proceda,
y [resultado actualizado](ECHO45-S6-B15-RESULTS.md). El
[contrato](ECHO45-S6-B15-DESIGN.md) fija los criterios completos.
