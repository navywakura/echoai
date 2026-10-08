# S6-B12 · contexto comprobado y campaña nueva

30 septiembre 2026. Contrato previo a la nueva inferencia. B11 permanece
detenido en c1 y sus artefactos se conservan. Esta condición prueba si el
aprendizaje contrastivo puede completar su campaña con contexto acotado.
Solo B1–B5 juntos permiten declarar S6 verde. El verde global de ECHO-4.5
requiere además las otras puertas de su roadmap.

## Cambio y presupuesto de contexto

Se conservan selección de casos, gramática, controles, verificador, solver,
modelo, sampling y umbrales de B11. Ambos brazos tienen un máximo de **6000
tokens de entrada** incluyendo chat template. Se cuentan con los archivos
del tokenizer de la misma revisión Qwen, cotejados con el manifiesto privado
ya usado en Kaggle. Solo se instala el contador en un entorno separado.

Una petición que cabe se conserva byte por byte. Si no cabe, el algoritmo
prueba estos formatos en orden, eligiendo el primero que cabe:

1. Sustituir nombres de features repetidos por vectores y una leyenda de
   orden fijo. Se verifica reconstrucción exacta: todavía no se omite evidencia.
2. Conservar solo el paso de primera divergencia de cada secuencia comparada.
3. Conservar secuencias solo del intento más reciente.
4. Omitir secuencias; conservar todas las propuestas, veredictos, pérdidas,
   ganancias y resultados agregados de los contrastes de los seis intentos.
5. Además, una observación de oportunidad por control y caso.

Los tres casos, programa aceptado, instrucciones y veredictos conservados
no se cortan a mitad. La gramática sigue derivándose de las observaciones
originales permitidas. Los detalles omitidos se identifican como desconocidos.
No se usa puntuación reservada para elegir formato. Si ni la representación
mínima cabe, se detiene **antes** de enviar: no hay truncamiento silencioso.
Cada petición incluye hashes, número de tokens y formato usado. El trabajo
remoto verifica los token IDs exactos antes de cargar el modelo o generar
el primer brazo; el auditor coteja su recibo y el uso real declarado.

## Piloto previo y campaña

Se hereda como calificación previa el piloto B11: ECHO 1129, FIJO 1108,
tres aceptaciones ECHO, dos parejas ganadoras y ninguna perdedora. No se
presenta como una replicación nueva. La auditoría B11 ya reconstruyó sus
36 veredictos. Un proceso B12 independiente verifica fuentes, recibos y las
36 peticiones originales: todas caben y serían idénticas bajo la regla B12.
Si esa identidad falla, la campaña no comienza. Se conservan hashes del
piloto, auditoría y transporte originales. Ninguna política del piloto se
traslada a la campaña.

Campaña nueva desde programas vacíos, semilla emparejada **705001**, +1000
por ronda: seis rondas, cinco propuestas por brazo, 60 propuestas y dos
calibraciones. Los 38 intentos del piloto heredado se atribuyen explícitamente;
los 17 intentos de la campaña B11 interrumpida son coste anterior adicional,
no evidencia ni respuestas reutilizadas en B12. No se elige entre varias
campañas posteriores según el resultado reservado.

A conserva 80 partidas, gym v2/v3, semillas 0–39, 2000 decisiones. B conserva
las 40 partidas protegidas B11, semillas 24920–24939: se declara reutilizado;
solo su aceptación/rechazo se devuelve al modelo. No se muestra su trayectoria.
Examen nuevo: semillas **25100–25159**, v2/v3, tres repeticiones, 360 partidas
y 1800 niveles por brazo. No se abre antes de promoción, auditoría y freeze.

## Aceptación, auditoría y cierre

V1 formato/seguridad; V2 ejecución y reproducción; V3 al menos dos niveles
nuevos A sin pérdidas individuales de niveles o score; V4 conserva cada
nivel y score B, tolerancia 1e-10. Promoción: aceptación ECHO y suma A
estrictamente mayor que FIJO. SIN FILTRO acumula todas las propuestas ECHO
seguras y ejecutables en su orden, sin V3/V4 ni selección retrospectiva.

La campaña se reconstruye en otro proceso con caché propia, incluyendo
prompts, formato de contexto, gramática, propuestas, decisiones y SIN FILTRO.
Antes del examen se congelan SEMILLA, FIJO, ECHO y SIN FILTRO. El examen usa
las funciones B11 y los criterios originales de `s6_precise_exam.checks`:

| Criterio | Verde solamente cuando |
|---|---|
| B1 | ECHO ≥105% de niveles SEMILLA y score medio no menor |
| B2 | ECHO supera niveles FIJO |
| B3 | ECHO supera niveles SIN FILTRO |
| B4 | Conserva niveles y score agregados en ocho juegos oficiales de desarrollo, tres repeticiones |
| B5 | Fuentes, modelo, tokenización, peticiones, veredictos, solver y replays auditables |

El examen no recibe observador. Sus resultados nunca vuelven al prompt.
Una campaña sin promoción o un examen fallido se cierran negativos.
S6-B12 no es una puntuación oficial ARC-AGI-1, 2 o 3.

## Recursos y continuidad

Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, Transformers 5.0.0,
CPU int8 fbgemm, resto float32, cuatro hilos, temperatura 0,7, top_p 0,95,
900 tokens de salida, prefill 512. Seis trabajos privados CPU de 3600 s;
sin GPU ni gasto de API. Máximo 64000 partidas locales incluidas auditorías,
examen e intentos interrumpidos, cuatro procesos y al menos 12 GiB libres.

Transporte LZMA con bytes y hashes verificados; no se duplica una inferencia
ambigua. Si se perdió la respuesta al envío, solo se recupera un trabajo
existente cuyo código remoto tenga el hash esperado. Dos recuperaciones de
transporte como máximo; ningún trabajo remoto fallido se vuelve a muestrear.
El servicio de usuario continúa sin chat, inhibe suspensión automática durante
su ejecución, conserva checkpoints y emite un aviso local al terminar.
Un error queda visible y se documenta; no se sustituye por un éxito.

[Fallo B11](ECHO45-S6-B11-C1-CONTEXT-DIAGNOSIS.md) ·
[Resultados B12](ECHO45-S6-B12-RESULTS.md).
