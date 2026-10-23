# S6-B12 · implementación y arranque

Actualización, **30 septiembre, 12:48 CEST**: B12 quedó detenido a las
09:28 CEST con dos de seis rondas completas. ECHO y FIJO aceptaron una
mejora cada uno: 365 → 378 niveles A, sin regresiones detectadas por V3/V4.
El empate mantiene pendiente la promoción. c2 terminó cancelado tras unos
61 minutos, con un límite configurado de 60 y siete respuestas guardadas;
Kaggle no facilitó una causa más detallada. La auditoría final y el examen
reservado siguen sin completar; el examen no se ha abierto.

La continuación **B12-R1** arrancó como servicio a las 12:48 CEST. Declara
7200 segundos por trabajo, conserva los originales y exige reproducir las
siete respuestas exactamente. Perfil adicional:
`8bf075108e5c5dff238131daac73c2b66f0da62253d28c0266cd76f7d1e40ff4`.
Pasaron 35 pruebas: once R1, once B12 y trece B11. Las once R1 incluyen
rechazar cambios en respuestas, tokens, perfil, fuente y payload, impedir
otro intento de inferencia fallido y no duplicar un envío ambiguo.
Este arranque todavía no acredita que la reproducción remota haya pasado.
[Condición, coste y diagnóstico](ECHO45-S6-B12-RECOVERY1.md).

Kaggle confirmó **RUNNING a las 12:52 CEST** para
`navywakura/echo45-s6b12-r1-c2-20260930`, privado, CPU y tope 7200 s.
La fuente ejecutada conserva el SHA-256 original c2
`f72fee76a7d8ec076d3a115035aaf0497e9d97908624fa654a4bef38dca42baa`.
La reproducción de las siete respuestas y los tres resultados restantes
se comprobarán al recibir el trabajo completo.

Registro del arranque original:

30 septiembre 2026. Perfil congelado
`9192295d75b0c2cd419258478b578689bbb2350ada2dc5ad17de0c0a388ebf77`.

Se corrigió la construcción de contexto: el mensaje B11 que tenía 6372
tokens queda en 4180 con la primera compresión, sin pérdida de evidencia.
La nueva condición conserva los mensajes que ya caben y aplica la misma
regla de presupuesto a ambos brazos. Qwen verifica los token IDs antes de
inferir; la auditoría reconstruye las peticiones y el formato elegido.

Validación: once pruebas nuevas y trece pruebas B11 aprobadas. Incluyen el
mensaje que falló, conservación de ganancias/pérdidas y veredictos, un
programa de 32 parches con seis historiales detallados, rechazo previo a
inferencia si el contexto mínimo no cabe, discrepancias entre tokenizers,
serialización del worker y bloqueo de examen sin promoción. Se comprobó
la creación del directorio de auditoría antes de su replay. Las fuentes
congeladas B11 y la comparación ARC-1 permanecen verificadas e intactas.

El servicio `echoai-s6b12.service` arrancó a las **05:42 CEST**. El sistema
confirmó la inhibición `sleep:idle`. La verificación independiente del piloto
heredado pasó: 36 peticiones sin cambios y auditoría previa válida. La campaña
se ejecuta desde programas vacíos, con semilla emparejada nueva; no reutiliza
las respuestas de la campaña B11 interrumpida. Ni una finalización del
proceso ni este arranque certifican una mejora o un cierre S6.

El servicio encadena campaña, auditoría, congelación y examen. Conserva
trabajos fallidos y solo recupera cortes de transporte sin repetir inferencia.
Al terminar escribe `closed.json` si hay resultado científico completo,
actualiza la documentación y guarda el aviso de escritorio en
`lab/seed/s6b12-20260930/notification.json`. Un error deja su causa visible.

El monitor independiente publica [seguimiento](ECHO45-S6-B12-LIVE.md) y
`lab/seed/s6b12-20260930/progress.json` cada 30 segundos a partir de artefactos
existentes. No ejecuta el agente ni lee trayectorias protegidas. La mini
terminal existente se abrió mediante `python3 observe.py --launch`.

Primera inferencia real: `navywakura/echo45-s6b12-c0-20260930`, privada y
sin GPU. Kaggle confirmó `S6_CPU_WEIGHT_HASHES_VERIFIED`, la comprobación
de arquitectura Q8 y `S6_B12_CONTEXT_PREFLIGHT_OK`. El trabajo comenzó a
generar el brazo FIJO; todavía no hay un veredicto de campaña. Los snapshots
de lectura remota están en `lab/seed/s6b12-20260930/monitoring/`.

ECHO-4.5 no se marca globalmente verde por aprobar S6: aún requieren evidencia
sus otras puertas ARC y de publicación. [Roadmap](ECHO45-ECHO5-ROADMAP.md).
