# COMPOSE-1 v2 — registro de desarrollo y resultados

Estado: **rojo en validación B; fase sin cerrar**. No sustituye el rojo de v1.
C funcional y la aceptación SITL no se abrieron. La continuación es v3.

## Intentos conservados

Todos están en `lab/compose1-v2/`; ninguna corrida fallida se elimina.

| Intento | Resultado / hallazgo |
|---|---|
| `development/terminal-1` | Exploración A de la puntuación terminal en la geometría antigua; no aceptación. |
| `development/extruded-1` | 192 misiones A: completo 16/16 alcanzables, Q 0/16; el coste favorece al horizonte largo, muestra pequeña. |
| `sitl-development/live-1` | 56 movimientos reales, retorno y aterrizaje; sin llegada. El clasificador redondeaba una pared a la celda libre próxima. Sus 56 consecuencias observadas alimentan la escuela física. |
| `sitl-development/live-2` | Llega a la coordenada pero no verifica el marcador. Las solicitudes de giro no se ejecutaban con orientación todavía no válida para el control. |
| `sitl-development/live-3` | Supera 1,5 m y alinea orientación; falla la condición de altura al confundir altura local absoluta con relativa al origen. Aterriza. |
| `sitl-development/live-4` | Primera misión completa auditada: 8 movimientos, inspección, llegada y aterrizaje. Distancia mínima observada a obstáculos 1.321 mm, envolvente 400 mm. |
| `sitl-development/round-1` | Estática: completo 8 movimientos frente a Q 50 y abandono en origen. Dinámica: completo vuelve sin resolver tras 50 movimientos; conserva una secuencia antigua aunque ve el nuevo acceso. Horizonte uno sí llega en 12 movimientos. Se detiene la campaña durante el posterior control Q para corregir ese defecto; todas las trazas, incluidos episodios parciales, quedan conservadas. |
| `development/replan-1` | Repite A con replanteamiento después de cada consecuencia, manteniendo horizonte/control y mapa. |
| `sitl-development/round-2` | 10/10 vuelos válidos y sin violaciones. Estática: completo 8, horizonte uno 10, convencional 8 movimientos; Q abandona tras 50. Dinámica: completo 8, horizonte uno 12, convencional 8; Q abandona tras 56. Cerrado: retorno tras 50; reserva insuficiente: aborto en origen con 0 movimientos. |

Las copias de código por sesión permiten distinguir revisiones de desarrollo.
En round-2 se añadió al ejecutor la comprobación de caducidad inmediatamente
antes de ejecutar. Los tres primeros casos, anteriores a esa guarda,
mostraban máximos medidos de 215, 201 y 214 ms al publicar el comando, por
debajo de 250 ms. Los casos posteriores ejercitan también la guarda activa.
Las primeras exploraciones no tienen el mismo inventario que el futuro lock.
`controls/round-1` conserva un fallo del copiador por enlaces internos del
contenedor; `controls/round-2` conserva 13 controles negativos aprobados sobre
la revisión anterior al replanteamiento. Se repetirán sobre la revisión final.

`controls/round-3` repitió los 13 controles sobre la revisión con replanteamiento:
todos detectados. Regresión de congelación: 34 tests aprobados.

## Examen congelado

Lock: `1c6e06506f4c2dc2cece33d76e7fcd0c1e28a5988a687dec2080b78a00564505`.
La cadena `python3 -m echoai.nexus0.compose1_v2.bench finish` congela y ejecuta
validación/confirmación funcional, validación/confirmación SITL, certificado y
auditoría en otro proceso. No reutilizarla para sobrescribir el lock ni repetir
el examen: una carpeta ya existente provoca rechazo.

La cadena se detuvo tras B: 768 misiones, 64/64 metas alcanzables tanto para
completo como para horizonte uno; Q 0/64. El completo ahorra 108 movimientos,
IC 97,5 % del ahorro medio [0,375; 3,03125]. Test de signos: 31 ventajas,
17 desventajas, 16 empates; p=0,0297316876. **No supera p<0,025**. No se cambia
ese límite ni se añaden observaciones. La reconstrucción de B produce evidencia
válida, sin hallazgos. `early-stop.json` documenta este cierre parcial rojo;
no representa una auditoría de etapas que no llegaron a ejecutarse.

La revisión [v3](COMPOSE1-V3-DESIGN.md) compara prefijos con el mismo horizonte,
tras medir dos candidatos en A. Usa B/C nuevos y conserva N y umbrales.

## Alcance que no cambia con un resultado verde

La composición usa T/Q/CAM y WSP, sin LLM ni hardware. Las transiciones
imaginadas no se escriben como experiencias. La cámara y LiDAR generan
evidencia de ocupación y PX4 ejecuta movimientos solicitados mediante WSP.
La pose verdadera es privada del juez. La estación es un marcador visual,
la energía es un presupuesto abstracto y la geometría está extruida: no
demuestra recarga, autonomía energética real, manipulación ni un metaverso.

Después del cierre verificable, el siguiente contrato es **CAUSE-1**.
