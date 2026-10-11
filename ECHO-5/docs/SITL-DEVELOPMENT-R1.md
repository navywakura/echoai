# Primera integración Gazebo/PX4 de ECHO-5

Ensayo de desarrollo del 10 de octubre de 2026, conservado en
`artifacts/sitl-development-20261010-r1/`. Ejecutó un mundo nominal nuevo en
tres procesos independientes, usando la imagen fijada, PX4 y Gazebo reales.
La auditoría posterior reconstruyó los resultados sin discrepancias entre
productor y auditor (`independent_audit=true`, `findings=[]`). La campaña
no supera cierre: falta cobertura de condiciones y un control no desarmó.

| Modo | Meta, regreso y desarme | Recibo completo válido | Decisiones | Duración de episodio | p95 de lógica |
|---|---|---|---:|---:|---:|
| ECHO heredado mediante puente nuevo | Sí | Sí | 33 | 253,84 s | 160,94 ms |
| Horizonte de un paso | No | No | 34 | 285,71 s | 127,77 ms |
| Convencional | Sí | Sí | 34 | 258,27 s | 142,45 ms |

Se midieron cero infracciones de envolvente de colisión y reserva en los
tres registros. Eso no convierte el episodio fallido en seguro conforme al
contrato: también exige observar el desarme. Las reservas mínimas fueron
543, 464 y 529 unidades de carga simulada, respectivamente. No son julios.
La diferencia de una decisión entre ECHO y convencional en un mundo y una
realización de física no demuestra una ventaja general.

En el control de un paso, el agente volvió a casa después de no confirmar el
marcador. El operador de simulación pidió aterrizar; PX4 no confirmó el
desarme dentro del plazo. El protocolo devuelve `TimeoutError('disarm')` y
el auditor señala `process_exit`, `ulog_armed_then_landed` y
`observed_disarm`. Estos errores permanecen registrados.

La pose privada final de Gazebo permanece aproximadamente en
(-0,1931; 0,0426; -0,0130) metros. Entretanto, `vehicle_land_detected.landed`
oscila entre cero y uno, y la altura/velocidad estimadas varían. Es una
discrepancia que debe investigarse entre estimación y estado físico simulado;
todavía no prueba cuál es su causa. El envoltorio actual configura referencia
barométrica y ruido de altura de 0,01 m. La documentación de PX4 1.15 define
referencia GPS con valor 1 y un ruido barométrico predeterminado de 3,5 m.
[Referencia oficial de parámetros](https://docs.px4.io/v1.15/en/advanced_config/parameter_reference).
Una corrección necesita otra calibración de desarrollo, con parámetros
declarados e iguales para los controles, conservando los criterios del juez.

Este ensayo valida parcialmente el transporte y la cadena heredada. No
evalúa todavía el razonador nuevo: todas las propuestas proceden de COMPOSE.
La siguiente revisión conectará el planificador de ECHO-5 a observaciones
públicas y añadirá recibos de ejecución efectiva; no atribuirá aprendizaje
a una propuesta que nunca llegó a ejecutarse.

No se ha accedido a la confirmación reservada, no se han editado las fuentes
históricas y no hubo conexión a hardware de vuelo.
