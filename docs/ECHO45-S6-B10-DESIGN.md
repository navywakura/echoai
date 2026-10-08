# S6-B10 · condiciones que coinciden con observaciones

29 septiembre 2026. Contrato previo a inferencia. B9 está cerrado y auditado:
18 propuestas, ninguna aceptada, ECHO/FIJO 534–534. El operador humano conserva
su control positivo auditado; sus valores y condiciones ganadores no entran en
los prompts. B10 parte de SEMILLA vacía y no hereda propuestas de B9.

Hipótesis: el generador necesita una comprobación mecánica de aplicabilidad.
B9 eligió revisar transiciones, pero produjo condiciones incompatibles con los
fallos observados o desactivó la operación. Se aísla ese mecanismo: propuestas
`REVALIDATE_NOOP` 1–8, con la biblioteca B5 de una a tres condiciones. El resto
del actor y los criterios de aceptación conservan su implementación.

El observador cuenta todas las combinaciones de rasgos realmente presentes
en contradicciones de transición de A. Usa el mismo diario, conserva registros
conjuntos y pasa controles de paridad. Para cada petición, una gramática deja
solo condiciones que coincidan con alguna de sus observaciones conjuntas,
excluye N=0 y propuestas exactamente repetidas del historial del propio brazo.
No puntúa candidatos, no ejecuta búsquedas para escogerlos ni consulta B/reserva.
El modelo sigue seleccionando el umbral y la condición. Una coincidencia no
demuestra evidencia consecutiva suficiente, cambio de acciones ni mejora.
Sin condiciones disponibles solo se permite abstención `{ "patches": [] }`,
que consume la llamada y pasa por el verificador ordinario.

La misma regla de decodificación se aplica a ECHO y FIJO; las condiciones
disponibles pueden diferir porque proceden de los casos que recibe cada uno.
FIJO recibe las tres partidas incompletas de menor nivel, petición genérica.
ECHO selecciona contradicciones en partidas incompletas, prioriza cercanía al
éxito y pide reparar/refinar el mecanismo según su feedback. Ambos reciben
su programa y resultados A propios; B solo proporciona rechazo booleano.
El efecto evaluado incluye selección de evidencia y restricción derivada de
ella, no solo la redacción de la pregunta. No demuestra autonomía general.

A: v2/v3, semillas 0–19, 2000 decisiones. B protegida 24620–24639 reutilizada
declaradamente tras control/B9. Reserva final nueva **24800–24859**, sin abrir.
No se consulta ninguna reserva anterior para ajustar este ensayo.
V1–V4: seguridad, ejecución/replay, +2 niveles A sin pérdida individual de
niveles/score A, ninguna pérdida individual B y replay. Sin cambios de umbral.

Piloto: semillas 655001/655017/655029, tres rondas × una propuesta por brazo y
pareja, +1000 a la semilla por ronda; 18 propuestas y dos calibraciones sin
tareas. Promueve con ≥1 aceptación ECHO y suma A ECHO > FIJO. Todas las
peticiones, gramáticas y 18 veredictos se reconstruyen en proceso/caché aparte.
Negativo: cierre sin campaña ni apertura de reserva.

Campaña condicional desde SEMILLA: semilla 665001, seis rondas × cinco
propuestas por brazo, con feedback entre rondas; 60 propuestas y dos
calibraciones. SIN FILTRO acumula propuestas ECHO seguras/ejecutables omitiendo
utilidad/conservación. Duplicados dentro de un lote cuentan; no hay reintentos
ocultos ni reparación manual. Auditoría independiente antes de examen.

Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, caché privada verificada. CPU int8
dinámico fbgemm, resto float32, cuatro hilos, temperatura 0,7, top_p 0,95,
máximo 900 tokens, prefill 512 sin truncar. Mismo backend para ambos brazos.
82 llamadas entrenadas máximo; nueve trabajos privados CPU de 3600 s;
hasta 40000 partidas locales; sin GPU, pago ni repetición automática de fallos.

Examen: 360 partidas por brazo (60 semillas ×2 versiones ×3 repeticiones),
1800 niveles posibles, replay de repetición 0 y solver del generador.
**Verde solo con B1–B5**: ECHO ≥105% niveles SEMILLA y score no menor;
ECHO > FIJO; ECHO > SIN FILTRO; conservación oficial de niveles/score;
auditoría de fuentes, propuestas/gramáticas, veredictos, replays y solver.
La transferencia a ARC oficial se mide después y no se infiere de este piloto.

[B9 cerrado](ECHO45-S6-B9-RESULTS.md) · [Control](ECHO45-S6-TRANSITION-RESULTS.md).
