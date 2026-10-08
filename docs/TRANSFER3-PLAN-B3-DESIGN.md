# B3 — última revisión acotada: ganancia más frenado observable

Contrato anterior a ejecución. B2 safe termina rojo: 51/72 metas vs 52/72,
sin violaciones, 6 fallos nuevos y coste total 7044 vs 6936. Se conserva.

Discrepancia comprobada en código: GainRoom.step frena delante de un obstáculo,
pero GainPlanner rechaza toda acción cuya ráfaga nominal no quepa entera.
Su "oracle" sólo conoce ganancia, no representa todas las transiciones reales.
Diagnóstico sobre las trazas públicas B2 safe: 149 estados de 21 salas con
ganancia 2, y 226 de 22 con ganancia 3, presentan un prefijo libre seguido de
pared observada antes de agotar la ráfaga. No son pruebas de ventaja.

Único cambio de B3: componer la ganancia aprendida en T con el frenado, regla
pública del cuerpo compartida por todos los brazos. Un prefijo de al menos una
celda libre seguido de pared explícitamente observada es una transición válida;
desconocido/conflicto/caducado no lo es. Predicción, expansión de búsqueda,
comprobación de siguiente acción y ruta de regreso usan la misma transición.
No se cambia la ganancia ni el payload después de la escuela, no se consulta
el mundo desde el agente. No se toca el cuerpo, recompensa, horizonte o margen.

Se conserva gate conservador de B2 (reserva 6 sin descuento por ganancia), todas
las condiciones y priors, las 24 salas públicas B1, todos los criterios B2 y
N=256/alpha=1/240 para eventual confirmación. B3 no reinterpreta B2 como verde.
El consumidor B3 está aislado con la misma lista permitida más su controlador.
El adaptador del arnés sustituye explícitamente las dos factorías de agente y
el manifiesto dentro de un proceso, y las restaura; no altera archivos B2.

Si este cribado falla, no se ejecuta confirmación ni se abre otra revisión en
esta sesión: se entrega el resultado para cuidar la cuota solicitada. Si pasa,
auditoría íntegra antes de confirmar; la confirmación usa formas frescas del
generador ya validado y no puede ejecutarse con un piloto falsificado/local.
No hay campaña B/C ni certificado TRANSFER-3.
