# S6-B11 · adenda de transporte sin cambiar la inferencia

29 septiembre 2026. Antes de cualquier respuesta B11 o apertura de examen.

El preflight terminó: 365/400 A, paridad original y del observador correctas.
El primer envío de p0 devolvió error; su programa preparado ocupa 30318150
bytes, principalmente condiciones repetidas de las gramáticas. El error
interno del primer transporte no quedó capturado, así que no se atribuye con
certeza a un límite concreto de Kaggle. La consulta del trabajo dio 403;
eso solo no demuestra ausencia. Una consulta autenticada del inventario
completo devolvió **43 trabajos propios y ninguno B11**. El intento original,
su payload y su programa se conservan. No hay respuestas que seleccionar.

## Extensión

El transporte empaqueta con zlib/base64 el programa original completo. El
wrapper exterior verifica SHA-256 y tamaño al descomprimir, escribe un recibo
de procedencia y ejecuta exactamente esos bytes. No modifica peticiones,
gramáticas, condiciones, semillas, orden, pesos, backend, temperatura,
tokens, prefill ni algoritmo de muestreo. No hay llamadas LLM adicionales.
Los ensayos y fuentes experimentales B11 originales permanecen congelados.

La extensión tiene fuentes y perfil propios bajo
`lab/seed/s6b11-20260929/transport-recovery`. El `source_digest` de las respuestas
sigue identificando B11 original. El recibo remoto `transport-receipt.json`
identifica además la extensión y los bytes realmente ejecutados.

`submission.json` original conserva el hash del programa preparado antes del
envío fallido. `transport/package.json` y `transport/submitted.json` registran
por separado el hash del wrapper comprimido realmente enviado; no se presenta
ese hash como si fuera el del programa descomprimido. `submitted.json` enlaza
ambos. Las dos representaciones se conservan y auditan.

El transporte consulta el inventario propio antes de un envío y se niega a
sobrescribir un trabajo existente. Registra intención antes de la llamada;
si el resultado es ambiguo, se detiene y no reenvía automáticamente. Solo
la ausencia comprobada del p0 inicial permite su recuperación explícita.
No se repiten inferencias ni se cambian respuestas por su rendimiento.

## Auditoría adicional obligatoria

Se comprueba la identidad exacta al descomprimir, los metadatos privados CPU,
el recibo de envío y el recibo remoto de ejecución. Cada lote debe pasar esto
antes de entrar al verificador. La auditoría adicional se repite en proceso
independiente y exige los doce lotes antes de permitir el examen, además de
las auditorías originales de peticiones/veredictos/replays. Los criterios
V1–V4 y B1–B5 permanecen intactos.

Cuatro pruebas de transporte comprueban round-trip byte a byte, ejecución y
recibo, compresión del paquete real sin pérdida y rechazo de procedencia
alterada. La extensión no cambia las 13 pruebas del experimento original.

[Implementación](ECHO45-S6-B11-IMPLEMENTATION.md) ·
[Perfil adicional](../lab/seed/s6b11-20260929/transport-recovery/profile.json).
