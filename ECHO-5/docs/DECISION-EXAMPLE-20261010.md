# Una decisión observada en ECHO-5

Ejemplo de desarrollo, 10 de octubre de 2026. Procede del primer vuelo de
`artifacts/sitl-development-20261010-r3/0000-echo32/`. La batería completa y
su auditoría aún estaban en curso al escribir esta nota. No es una prueba
reservada ni una demostración de superioridad estadística.

ECHO ya había observado la meta y estaba regresando. En la celda relativa
`[1, -2]`, el siguiente movimiento hacia `[1, -1]` carecía de admisión con
evidencia sensorial actual. El controlador registró `return_not_admitted`.
La falta de admisión no significa que hubiera una pared: significa que los
datos disponibles no autorizaban ese desplazamiento.

En las decisiones 27–30, el puente de observación activa emitió cuatro
inspecciones de orientación. Sus predicciones conservaron la posición:

```json
{
  "status": "inspect_information",
  "prediction": [1, -2, 0],
  "information": {
    "reason": "return_step_not_admitted",
    "blocked_return_cell": [1, -1],
    "index": 0,
    "total": 1
  }
}
```

El registro anterior muestra la primera de las cuatro inspecciones. Los
índices siguientes fueron 1, 2 y 3; se agotó el límite local de cuatro. El
motor no recibió permiso para avanzar a una celda desconocida por el mero
hecho de insistir. En la decisión 31, una observación posterior sí permitió
la admisión del siguiente paso. POWER comprobó 555 unidades de carga
simulada disponibles frente a 131 requeridas, incluido regreso, aterrizaje
y reserva. El controlador de regreso heredado ejecutó los pasos restantes
y propuso `land_home` en la decisión 34.

El evaluador del episodio registró meta, regreso y desarmado; cero colisiones
y cero violaciones de reserva. La reserva final fue 476 unidades simuladas.
La cadena de ejecución conservó 34 recibos de consecuencias entregados al
actor y 22 acciones ejecutadas del razonador nuevo. Los movimientos de
regreso se atribuyen al controlador heredado, no al nuevo planificador.

Esto permite inspeccionar una secuencia real: evidencia insuficiente,
inspección acotada, nueva evidencia y acción autorizada. El registro no
contiene un monólogo privado. Tampoco permite afirmar cuánto habría mejorado
este mismo vuelo sin las inspecciones: esa comparación necesita su control.
Las unidades de carga no son julios y la simulación no certifica un dron real.

Los hechos pueden comprobarse en `transport.jsonl`, `public-outcomes.json`,
`row.json` y las trazas de `out/`. La auditoría del conjunto debe reconciliar
estos archivos antes de contar el episodio para el cierre.

Otra decisión del mismo ensayo aparece en `0002-echo32/transport.jsonl`.
El ejecutor esperó a entregar el control con poca energía. POWER registró
`remaining: 150`, `mission_required: 226` y `landing_required: 74`; propuso
`land_home`. El evaluador observó desarmado en casa, reserva final de 129 y
ninguna violación. Se cuenta como respuesta segura ante poca energía, no como
una misión completada: el agente no alcanzó la meta en ese episodio.
