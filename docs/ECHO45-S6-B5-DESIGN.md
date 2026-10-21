# S6-B5: cambios precisos, piloto y continuación — contrato

2026-09-28. Orden de Nav: mejorar desarrollo sin regresión, obtener una
mejora propuesta/verificada por ECHO con ayuda LLM y ejecutar cuatro brazos
en un examen nuevo. Condiciones fijadas antes de la primera llamada B5.
S6-A/B0/B2/B3/B4 y los controles anteriores conservan fuentes y resultados.

Base v5.8; doce parámetros, incluyendo `COOLDOWN_CAP`, y parches de una a
tres guardas observables/un parámetro entero. Hasta 32 parches acumulados;
fuera de sus guardas se mantienen controles nativos. Los operadores nuevos
son humanos y están igualmente disponibles a FIJO/ECHO. No se acepta Python,
IDs, familia, semilla, coordenada absoluta, acceso al verificador o respuesta
reservada. La gramática finita define guardas disponibles; V1 además valida
JSON cerrado y límites. El parche vacío/inactivo y el observador ya tienen
pruebas de paridad; el control previo exige también paridad completa.

A: v2/v3, semillas 0–19; B nueva protegida 24120–24139; 40 partidas cada
cohorte y 2000 decisiones. Se conserva la convención de score S6-B4 y se
registran reinicios automáticos. V2: ejecución y replay completo A/B cuando
corresponde; V3: +2 niveles A, sin pérdida individual de niveles ni score A;
V4: ninguna pérdida individual B. Tolerancia de puntuación 1e-10. Solo A
alimenta prompts: episodios reales, alias locales y contraejemplos medidos.
B solo puede comunicar rechazo protegido; nunca detalles o índices.

Tres condiciones sucesivas:

1. Control humano preciso cerrado positivo con perfil intacto. La solución
   humana no entra en los prompts ni en el código subido al modelo.
2. Piloto emparejado: tres semillas 612001/612017/612029, dos respuestas por
   brazo y semilla. FIJO petición genérica con tres fallos; ECHO elige P1/P2/P4
   con el selector histórico. Prompts precomputados, sin adaptación dentro
   del piloto. Verificación compone parches aceptados secuencialmente. Se
   promueve solo si ECHO acepta al menos uno y la suma A ECHO supera FIJO.
3. Campaña nueva: ambos parten otra vez del mismo parche vacío, seis rondas
   de cinco respuestas por brazo (30 cada uno). La evidencia, estadísticas
   de tipos y feedback se actualizan entre rondas; P3 usa un parche ya
   aceptado. El muestreo se empareja por ronda. Nada se selecciona por examen.

Qwen2.5-Coder-7B, revisión `c03e6d358207e414f1eca0bb1891e29f1db0e242`,
FP16, dos T4 gratis, temperatura 0.7, top-p 0.95, máximo 900 tokens;
prefill 512/caché dinámica explícita según recuperación auditada B4.
Máximo siete trabajos de 900 s: piloto 12+2 calibraciones; campaña 60+2
calibraciones en r0: **76 llamadas**. Solo trabajos privados y cuota gratis,
pago prohibido; espera automática si falta cuota. Un fallo de inferencia
se conserva y detiene, sin duplicar ni reintentar trabajos automáticamente.
No se permite truncar prompts. Respuestas, payloads, fuentes y wrappers
de ejecución se auditan contra sus hashes. Cota conservadora de 32000 partidas
CPU incluyendo control, piloto, verificación, brazo raw, examen y auditoría
completa; la caché compartida reduce repeticiones de políticas idénticas.
Cuatro procesos por pool.

SEMILLA conserva v5.8. FIJO/ECHO mantienen solo propuestas que pasan V1–V4.
**SIN FILTRO acumula todas las propuestas de ECHO que pasan V1/V2**, incluso
las rechazadas por utilidad/regresión; omite V3/V4 y no necesita llamadas
nuevas. Cada composición tiene replay de A para verificar ejecutabilidad.
Esta definición restaura literalmente la propuesta original de Nav;
B4 usaba la última política completa, que se conserva como condición anterior.

Examen nuevo 24200–24259, versiones 2/3, reps 0/1/2: 360 partidas y 1800
niveles por brazo. Fuentes y políticas finales congeladas antes de abrir.
Sin observador ni LLM. El solucionador debe validar 300 niveles por versión.
Repetir todas las 120 partidas rep0 por política distinta en caché/pool nuevos.
Políticas idénticas pueden compartir medición, declarando sus hashes.
No reabrir tras conocer resultados. Ocho juegos oficiales de desarrollo,
tres reps, después de congelar. Auditoría independiente reconstruye prompts,
respuestas, wrappers, todos los 60 veredictos y la composición raw.

**VERDE solo si todos pasan:** B1 ECHO ≥105 % de niveles de SEMILLA y score
medio ≥SEMILLA; B2 ECHO >FIJO; B3 ECHO >SIN FILTRO; B4 sin caída de niveles
o score agregado oficial; B5 fuentes/procedencia, decisiones, solucionador
y todos los replays válidos. Piloto/control positivos no hacen S6 verde.
Si falla una promoción, cerrar sin abrir examen; si falla un criterio final,
publicar ROJO; si falta evidencia por error, PENDIENTE. Sin rebajar umbrales.

El bucle nuevo de rejillas y sus relaciones se evalúa aparte en ARC-2;
no se atribuye una mejora del solver de rejillas a esta campaña de juegos.
