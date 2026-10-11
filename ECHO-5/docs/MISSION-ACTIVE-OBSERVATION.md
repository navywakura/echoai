# Observación activa ante caminos sin evidencia suficiente

El ensayo `artifacts/sitl-calibration-20261010-r2` terminó con un recibo válido
y auditoría independiente concordante. El capturador privado mantuvo un hueco
máximo de 27 ms. No hubo colisión, infracción de reserva ni comando inseguro.
La misión falló: tras siete movimientos, el agente aterrizó fuera de casa sin
observar la meta. Ese resultado se conserva.

En la octava decisión, la posición pública era `[0,-1,0]`. El frame admitía
dos celdas lejanas, pero ninguna vecina permitía alcanzarlas. El planificador
devolvió una lista vacía. MissionAgent inició retorno por
`compose_access_not_found`; el paso hacia casa tampoco estaba admitido y
emitió `return_not_admitted`. Había 861 unidades de reserva simulada: el motivo
inmediato fue falta de evidencia local, no agotamiento de batería o cómputo.

La hipótesis nueva es que obtener otra vista puede distinguir una interrupción
perceptiva de un camino cerrado. La política utiliza las cuatro inspecciones
de orientación ya permitidas por el gateway, sin desplazarse a una celda
desconocida. Limita cada celda a cuatro propuestas y el episodio a doce.
Cada propuesta conserva su motivo y contador. El verificador comprueba acción,
posición, presupuesto y condiciones públicas; el evaluador físico conserva
la autoridad sobre éxito, colisión y llegada.

La adaptación se aplica antes de enviar el WSP. Sólo puede aplazar un abandono
recién propuesto por ausencia de camino. No elimina una parada anterior, un
retorno exigido por energía ni un veto. Si ya se está regresando, la inspección
conserva ese estado. El coste de una inspección más el retorno y aterrizaje debe
caber en la reserva, comprobado otra vez por el supervisor independiente.
Al consumir el límite sin información útil se conserva la retirada o parada.

ECHO y el control de horizonte uno usan esta misma posibilidad de observación;
el controlador convencional queda como referencia anterior. El nuevo cambio
debe medirse con fuentes congeladas en desarrollo y después en confirmación.
No demuestra que una inspección siempre encuentre un camino ni convierte
una celda recordada en permiso para mover el cuerpo.
