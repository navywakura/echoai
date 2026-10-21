# S6-B8 · recuperación única de infraestructura

2026-09-29, después del fallo p2 y antes de su recuperación. La orden vigente
de Nav autoriza continuar y corregir S6. No es un reintento automático ni
una nueva selección de propuestas tras ver sus resultados.

Los trabajos p0 y p1 completaron seis propuestas cada uno. p1 repitió las
seis anteriores, con prompts/semillas distintos y procedencia verificada.
p2 terminó ERROR; su archivo de respuestas tiene `complete=false`, seis
listas vacías y ningún perfil de modelo completo. El último registro está
en la descarga de cuatro archivos, 0/4. Se había configurado un máximo de
300 segundos; no hubo ninguna propuesta que pudiera seleccionarse o descartarse.

Se permite **un** trabajo privado adicional, hasta 600 segundos gratuitos,
para el mismo payload p2 y el mismo ejecutable exacto. No cambian prompts,
semillas de muestreo, modelo, pesos/revisión, librerías solicitadas, temperatura,
límites de tokens, gramática, criterios ni políticas. El hash del wrapper
debe coincidir byte por byte con el intento original. No se reenvían p0/p1.
Si vuelve a fallar o falta cuota, queda PENDIENTE con ambos intentos conservados.
No se activa pago. Cuota observada antes: 626,703 segundos disponibles.

Los archivos originales de p2 permanecen en su carpeta; la recuperación tiene
carpeta, referencia Kaggle, perfil y recibo propios. Solo se consumen respuestas
completas de ese trabajo, validadas contra su payload. El auditor reconstruye
los 18 veredictos y valida las tres rondas, incluida esta procedencia separada.
La ejecución anticipada de seis veredictos usa exclusivamente la caché de
auditoría, separada de la medición; el auditor final comprueba todos los registros.

Extensión explícita del límite de infraestructura: como máximo diez trabajos
en total y 3300 segundos de GPU configurados (nueve ×300 y uno ×600), siempre
sujetos a cuota gratuita real. Las llamadas planificadas siguen siendo 82:
el intento fallido no generó respuestas. Su coste/tiempo sí se conserva y cuenta.
Todo lo demás sigue el [contrato B8](ECHO45-S6-B8-DESIGN.md).

Preflight de la recuperación: el primer controlador falló antes de enviar
ningún trabajo porque su enlace privado de `run_phase` omitía el valor por
defecto de `audit`. Se conserva el perfil y archivo fuente iniciales; se
corrige solo ese enlace, se añade una prueba y se congela el perfil revisado
antes de inferir. El wrapper original p2 no cambia. Recibo separado:
`preflight-correction.json` en la carpeta de recuperación.
