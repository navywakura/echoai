# EGO-MEMORIA-3E · valor de conservar una prueba

2026-09-29, antes de medir esta revisión. Diagnóstico de desarrollo 3D:
en semilla 21 el agente escribe también casi todas las pistas verdaderas.
La muestra de reclamaciones sin verificar/escribir tiene media de coste
11,11 (27 retornos), frente a 8,94 al escribir sin verificar (1237).
Ambas acciones carecen de prueba verificable: atribuir la diferencia muestral
a escribir provoca una superstición costosa. M1 lo rechaza correctamente.

Revisión: conservar las estimaciones de navegación y escritura, y agrupar
el coste posterior por **existencia de prueba verificada conservada**. Durante
la experiencia se registra ese atributo mirando la entrada realmente escrita;
se aprende su coste posterior desde la acción original. No se almacena la
prueba en crédito ni se permite responder reclamaciones desde este registro.
Solo el diario conserva la prueba. Sigue sin haber recompensas por escribir.

Hipótesis estructural humana explícita: en este mundo las acciones verificar
y escribir juntas permiten conservar el recibo; sin ambas no existe recibo
persistente. Se comparten las muestras de reclamaciones entre acciones sin
recibo. No se afirma que el agente haya descubierto solo esta factorización.
Su utilidad se aprende de costes reales: puede valer cero en el control sin
deudas o no compensar su coste en un mundo honesto. No usa etiquetas de mentira.

Se conservan horizonte 64 y exploración por experiencia de 3D. Desarrollo
1–24 completo, M1–M5 24/24 y coste agregado ≤base para promover. 3D es ablación
del agrupamiento por prueba; sus recibos y fallo quedan conservados. Ninguna
selección por semilla. Reserva 43000–43015 solo si nadie la abrió antes;
congelación previa y reconstrucción completa en proceso independiente M6.
VERDE = M1–M5 en 16/16 y M6, con los umbrales originales sin cambios.
Alcance: memoria y prueba en esta aldea, no transferencia general ni ARC.
