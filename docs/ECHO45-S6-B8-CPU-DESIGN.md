# S6-B8-CPU · continuación declarada, sin cuota GPU

2026-09-29. Fijado antes de inferencia CPU. La autorización vigente pide
continuar S6 y corregir los bloqueos. B8 original queda PENDIENTE con doce
propuestas auditadas. Sus dos intentos p2 no generaron ninguna respuesta.

La caché privada de CPU contiene la revisión exacta
`Qwen/Qwen2.5-Coder-7B-Instruct@c03e6d358207e414f1eca0bb1891e29f1db0e242`,
cuatro shards y 15242805878 bytes en total. Todos los hashes LFS de pesos
coinciden. Esta continuación tiene directorio, perfil y fuentes propios.

Se heredan las dos rondas completas de B8 y sus veredictos; se reutiliza
la caché de ejecución y la de auditoría, copiadas por separado. El actor,
el lenguaje, datos A/B, filtros V1–V4 y B1–B5 no cambian. Las seis peticiones
restantes son exactamente las ya escritas, con sus semillas previstas. El
diagnóstico nuevo de consumo real NO se introduce en estos prompts.

**Cambio explícito:** inferencia en CPU, float16, sin cuantizar, cuatro hilos,
pesos locales verificados y sin descargas del Hub durante la inferencia.
El muestreo CPU no es bit-equivalente a CUDA. Ambos brazos usan el mismo
backend en cada ronda: las dos rondas heredadas usaron GPU; la tercera usa CPU.
Se publica esta mezcla y se conserva B8 original por separado. No se presenta
la continuación como una repetición exacta del experimento íntegramente GPU.

Un trabajo CPU de hasta 3600 segundos completa la tercera ronda. Si promueve
ECHO (acepta ≥1 y suma A >FIJO), campaña nueva desde parche vacío, seis trabajos
CPU de hasta 3600 segundos y cinco propuestas por brazo/ronda. Total lógico
del piloto+campaña: 78 propuestas y cuatro calibraciones =82 llamadas, incluyendo
las heredadas. Ningún trabajo tiene acelerador ni pago. Fallo de inferencia se
conserva y detiene; no hay duplicado automático ni búsqueda ilimitada de respuestas.

Prompts, wrapper, manifiesto de pesos, respuestas, backend y todos los
veredictos se auditan. El examen 24500–24559 solo puede abrirse si el piloto
promueve y se completa/audita la campaña. Se conserva la comparación de cuatro
brazos, SIN FILTRO acumulativo, conservación oficial y replay del contrato B8.
Este conjunto sigue sin abrir; ni B8 ni esta continuación pueden evaluarlo dos
veces o elegir políticas con sus resultados. Verde solo con B1–B5 completos.

[B8 original](ECHO45-S6-B8-RESULTS.md) ·
[Caché verificada](../lab/kaggle/s6-model-cache-20260929/output/manifest.json).

## Corrección de infraestructura antes de la primera respuesta CPU

El primer trabajo CPU verificó y cargó los pesos, pero falló al registrar
`model.hf_device_map`: Transformers 5 no expuso ese atributo en este caso.
Archivo de respuestas: cero calibraciones, cero propuestas, `complete=false`.
No se midió ninguna propuesta ni se abrió la reserva. Se conserva todo el
perfil, fuentes y salida en `infrastructure-attempt-1/`; el trabajo remoto
original tampoco se sobrescribe.

Se registra una única recuperación v2: inventariar los dispositivos reales
de `model.named_parameters()` y exigir que todos sean CPU. No cambia pesos,
dtype, muestreo, prompts, semillas, gramática ni criterios. La prueba del
wrapper exige el nuevo registro. Los trabajos v2 usan identificadores
distintos y conservan el límite de 3600 segundos; no hay reintento automático
si fallan. Perfil corregido congelado antes de enviar v2; coste extra GPU cero.
