# S6-B9 · del fallo observado a la revisión de una predicción

29 septiembre 2026. Contrato previo a inferencia B9. Nueva condición, partiendo
de SEMILLA vacía; no hereda propuestas de B5–B8 ni de sus recuperaciones CPU.
El control de capacidad sobre transiciones debe terminar positivo y pasar su
auditoría independiente antes de congelar/enviar B9. Su parche ganador y los
datos B no se proporcionan al modelo.

Instrumento: DSL preciso B5 más `REVALIDATE_NOOP` (0–8), declarado en el control
de transiciones. SEMILLA usa la política vacía, con operación desactivada. Los
dos brazos pueden proponer exactamente los mismos parámetros y guardas; no se
inyecta ninguna reparación en el actor. Gramática parámetro antes de guarda.
El observador pasivo reúne lecturas reales de esperas y contradicciones de
transiciones; los controles de paridad deben pasar antes de medir.

FIJO: petición genérica con las tres tareas incompletas de menor puntuación.
ECHO: elige entre fallo de transición y espera, ponderando observaciones por
niveles que faltan y penalizando tipos de petición que no ganaron niveles.
Selecciona casos incompletos con evidencia del mecanismo y cercanos a resolver.
Ambos reciben su propio programa y feedback de A. El único detalle de rechazo
B es un booleano. ECHO nunca recibe el programa humano que pasó el control.
No se afirma que estas dos preguntas cubran toda autonomía de ECHO.

A conocida: v2/v3, semillas 0–19, 2000 decisiones. B de desarrollo protegida
24620–24639, declaradamente reutilizada después del control humano. La reserva
final distinta 24700–24759 permanece sin abrir. No hay ajuste a sus resultados.
V1–V4 conservados: seguridad, ejecución y replay, +2 niveles A sin regresión
individual de niveles/score A, y ninguna regresión individual B con replay.

Piloto: tres parejas de semillas 635001/635017/635029; tres rondas, una propuesta
por brazo/pareja/ronda, semillas +1000 por ronda. 18 propuestas y dos calibraciones.
Promueve solo con aceptación ECHO y suma A ECHO estrictamente mayor que FIJO.
Auditor independiente reconstruye todas las peticiones y los 18 veredictos en
otro proceso y caché. Si no promueve, se cierra negativo y no se abre reserva.

Campaña condicional desde SEMILLA vacía: semilla 645001, seis rondas de cinco
propuestas por brazo y feedback entre rondas. 60 propuestas y dos calibraciones.
SIN FILTRO acumula todas las propuestas ECHO seguras/ejecutables, omitiendo
ganancia y conservación. La campaña también se reconstruye independientemente.

Modelo: Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, desde caché privada verificada por
SHA256. **CPU int8 dinámico, fbgemm**, parámetros no cuantizados float32,
cuatro hilos; transformación declarada igual para ambos brazos. No equivalencia
numérica con GPU/float16. Temperatura 0,7, top_p 0,95, máximo 900 tokens, prefill
en bloques 512, sin truncar prompts. Comprobación previa con Qwen2 diminuto de
pesos aleatorios y dos tokens, sin tareas. 82 llamadas al modelo entrenado,
hasta nueve trabajos CPU privados de 3600 s, sin GPU ni pago ni reintentos
automáticos tras un fallo. Hasta 40000 partidas CPU locales; sin cambiar umbrales.

Examen de cuatro brazos únicamente tras promoción y auditorías: 360 partidas
por brazo (60 semillas ×2 versiones ×3 repeticiones), 1800 niveles posibles,
replay de repetición 0, solver del generador y conservación oficial. B1 exige
≥105% de niveles SEMILLA y score no menor; B2/B3 superioridad estricta sobre
FIJO/SIN FILTRO; B4 conserva niveles y score de desarrollo oficial; B5 auditoría
completa de fuentes, prompts, inferencia, propuestas, veredictos y replays.
**Verde solo con los cinco criterios, nunca por el control humano.**

[Instrumento](ECHO45-S6-TRANSITION-RESULTS.md) · [CPU Q8](ECHO45-S6-B8-CPUQ8-DESIGN.md).
