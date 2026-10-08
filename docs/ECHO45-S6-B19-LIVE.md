# S6-B19 — seguimiento privado

**Cerrado y auditado el 5 de octubre a las 16:59 Madrid, sin promoción.**
36 propuestas, 1188 ejecuciones; ningún pase del cribado. Las fases de 160
y 80 casos no se abrieron. No queda B19 corriendo. [Resultado final](ECHO45-S6-B19-RESULTS.md).

El texto siguiente conserva la previsión y configuración del lanzamiento.

Enviado el 5 de octubre de 2026 a las 13:57, hora de Madrid. Kaggle confirma
privacidad y coincidencia exacta del código subido. La base del cribado y su
replay ya coinciden con el registro local. La primera propuesta CUDA ya se
está midiendo; todavía no hay veredicto de conservación nuevo.

Los primeros lotes de doce partidas tardan alrededor de 1 minuto y 45 segundos.
Con doce oportunidades máximas por brazo, replay y auditoría, el orden de
magnitud inicial es **1,5–4 horas desde el lanzamiento**, aproximadamente
15:30–18:00 de Madrid si no hay interrupciones. Es una proyección de carga,
no una promesa de resultado ni el tiempo hasta S6 verde; depende del número
de candidatos que se ejecuten y de las puertas que lleguen a abrirse.

El servicio remoto ejecuta `seed.s6b19 follow`: cribado de tres brazos,
auditoría independiente, desarrollo completo de 160 casos, auditoría y, solo
si cumple, 80 casos protegidos nuevos con replay y otra auditoría.

Los servicios locales `echoai-s6b19-kaggle-live` y
`echoai-s6b19-kaggle-follow` recogen el progreso y descargan los recibos.
Después, `review.py` recalcula puntuaciones, pérdidas, pases y presupuesto,
compara las filas primarias/replay/auditoría y actualiza los documentos de
estado. Estos servicios no vuelven a enviar el experimento ni cambian sus
fuentes. La ejecución remota continúa aunque se cierre el chat; una caída de
red local retrasa el seguimiento y la descarga.

[Estado remoto recogido](../lab/seed/s6b19-20261005/transport-status.json) ·
[Último evento en directo](../lab/kaggle/s6b19-20261005/micro/live.json) ·
[Contrato congelado](ECHO45-S6-B19-DESIGN.md) ·
[Investigación](ECHO45-S6-B18-COST-FORENSICS.md).
