# S6-B11 · recuperación de carpeta de auditoría

29 septiembre 2026, 23:52 Madrid. El piloto terminó con **ECHO 1129 frente a
FIJO 1108**, tres mejoras ECHO aceptadas, dos pares ganados y ninguno perdido.
Cumple la promoción del piloto; **no acredita aún S6 B1–B5**.

El primer auditor fresco falló antes de medir: `shutil.disk_usage()` recibió
una ruta `pilot-audit` todavía inexistente. Se crearon las carpetas vacías
`pilot-audit` y `campaign-audit` y se reanudó el supervisor original. No se
modificaron código, prompts, modelo, propuestas, semillas ni criterios. No se
añadieron llamadas al modelo. El registro del primer fallo y el hash del piloto
se conservan en el recibo operativo.

La auditoría vuelve a ejecutar desde cachés independientes. La campaña sólo
puede empezar si reconstruye las 36 propuestas y los veredictos completos.
Después exige promoción propia y auditoría antes de abrir el examen reservado
de cuatro brazos. S6 verde sólo cuando todos los B1–B5 pasan.

[Recibo operativo](../lab/seed/s6b11-20260929/audit-directory-recovery/receipt.json) ·
[Contrato congelado](ECHO45-S6-B11-DESIGN.md) ·
[Resultado automático](ECHO45-S6-B11-RESULTS.md).
