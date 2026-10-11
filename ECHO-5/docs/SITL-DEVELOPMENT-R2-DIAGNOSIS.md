# Diagnóstico de desarrollo: regreso interrumpido en SITL r2

10 de octubre de 2026. Se conserva el resultado negativo de
`artifacts/sitl-development-20261010-r2/0000-echo32/`.

ECHO llegó al objetivo y el juez observó su marcador. El regreso se interrumpió
al intentar llegar de [2,-2] a [1,-2]. El supervisor pasó a `execution_fault`
tras el plazo de ejecución vigente, cortó órdenes y el simulador terminó
aterrizando y desarmando. No volvió a casa. `success=false`, con recibos
válidos, cero colisiones horizontales y reserva final 497 unidades simuladas.
La latencia lógica p95 fue 123,28 ms; esta fila no indica un timeout del LLM
o del razonador. No hay llamadas a LLM.

En los datos anteriores al veto, el vehículo estaba cerca de la posición
horizontal solicitada, pero la velocidad estimada no bajaba del límite de
150 mm/s durante las tres muestras requeridas. Hay además una discrepancia
creciente entre altura estimada y altura de la verdad física de Gazebo:

| Tiempo simulado | Altura estimada | Altura Gazebo | Velocidad estimada |
|---|---:|---:|---:|
| 175,626 s | 2,403 m | 1,229 m | 126 mm/s |
| 181,994 s | 2,345 m | 0,988 m | 203 mm/s |
| 185,000 s | 2,328 m | 0,956 m | 182 mm/s |
| 190,580 s | 2,280 m | 0,776 m | 208 mm/s |

El veto ocurrió a 190,652 s. Estos valores provienen de `out/trace.jsonl` y
`out/private.jsonl`; la verdad privada sólo llega al juez. El resultado
demuestra una estimación inadecuada en esa trayectoria, pero todavía no
identifica un único parámetro como causa.

Se propone un ensayo de calibración de desarrollo con el mismo actor, semilla,
imagen y criterios, cambiando exclusivamente `EKF2_BARO_NOISE` de 0,01 a 3,5 m.
3,5 m es el valor predeterminado documentado en
[PX4 v1.15](https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_BARO_NOISE).
Se mantiene `EKF2_HGT_REF=0`, los controles horizontales, el plazo y las
tolerancias de llegada; no se fuerza el desarmado. El recibo debe comprobar
el parámetro leído del simulador antes de armar. No se modifica la fila r2.

El primer ensayo será sólo la condición nominal ECHO de desarrollo. Un éxito
habilitará comprobar cobertura y repeticiones; no demostrará por sí solo
robustez o causalidad universal. La confirmación reservada permanece cerrada.
Las correcciones pendientes de integridad de recibos se programan aparte para
evitar atribuir a la calibración cambios simultáneos en la política.
