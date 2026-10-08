# S6-B11 · transporte compacto, revisión 2

29 septiembre 2026. Adenda antes de inferencia y de abrir el examen.

El primer paquete de 30 MB falló al enviarse; la recuperación zlib de 1,6 MB
recibió HTTP 400 de `SaveKernel`. Se conservaron ambas representaciones,
intenciones, perfiles y errores. La nueva consulta completa de la cuenta
volvió a mostrar que no existe el identificador del trabajo B11. No hay
respuestas generadas ni decisiones experimentales que se hayan seleccionado.
El límite exacto que motivó el error no se infiere de un HTTP 400 genérico.

Esta revisión sustituye únicamente la compresión zlib del wrapper exterior
por **LZMA**, biblioteca estándar. El mismo programa original pasa a ocupar
aproximadamente **72 KB**. Al descomprimir se verifican exactamente sus bytes,
tamaño y SHA-256 antes de ejecutarlo. Conserva prompts, gramáticas, fuentes,
modelo, semillas y parámetros. No consume llamadas adicionales al modelo.

Los archivos y perfil de la revisión 1 permanecen intactos. Esta revisión
añade sus propias fuentes, contrato, cuatro pruebas y perfil en
`lab/seed/s6b11-20260929/transport-recovery2`. Incluye el hash del perfil previo.
Los paquetes y recibos por lote viven en `transport2/`, separados de
`transport/` de la primera recuperación. Se conserva también el inventario
anterior al nuevo intento. Los errores HTTP siguientes conservarán su cuerpo
de respuesta para permitir diagnóstico sin repetir el envío.

Se mantienen todas las obligaciones de la [primera adenda](ECHO45-S6-B11-TRANSPORT-RECOVERY.md):
no duplicar trabajos, recibo remoto de los bytes ejecutados, auditoría de
transporte antes de cada veredicto y auditoría independiente de los doce lotes
antes de abrir el examen. No cambia V1–V4 ni B1–B5 ni ninguna cohorte.

[Implementación](ECHO45-S6-B11-IMPLEMENTATION.md) ·
[Perfil adicional](../lab/seed/s6b11-20260929/transport-recovery2/profile.json).
