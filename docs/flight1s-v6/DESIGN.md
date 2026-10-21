# FLIGHT-1S v6 — una cadena que un solo fallo no detiene

Estado: **prerregistro aprobado** (2026-09-11), anterior a cualquier
vuelo v6. V1–v5 permanecen intactos y rojos.

## Por qué v6

V5 voló 64/64 vuelos A y quedó roja sin veredicto de etapa:

1. `nominal-02083ef67737f6d9-r1`: PX4 arrancó, pero su módulo MAVLink dejó de
   publicar `telemetry_status` ~2 s tras el arranque (1 muestra por instancia;
   un vuelo sano tiene una por segundo) y nunca emitió heartbeat. La misma
   firma aparece en `perturbed-02083ef67737f6d9-r2` de v3. 2 de 343 vuelos
   con ULog. Los 341 restantes enlazan en 14540 ≤1.8 s tras el inicio del log.
2. El agregador de repetición heredado de v2 leyó una medida inexistente de
   ese episodio y lanzó `KeyError`: sin negativos ni `report.json`.
3. El auditor exigía cinco etapas a un vuelo que nunca despegó: un fallo
   legítimo invalidaba la evidencia.

No es carga del host: en los dos fallos el reloj de simulación avanzó a 976
muestras/s, por encima de todo vuelo sano (mediana 944). Un contenedor en
lugar de dos no está justificado por los datos.

## Cambios prerregistrados

**Reinicio pre-tratamiento.** Si no llega el primer heartbeat MAVLink en 30 s,
el runner termina y el coordinador vuela el mismo trabajo en un contenedor
nuevo (Gazebo y PX4 desde cero, misma imagen, misma configuración), una sola
vez. Criterio, recalculable desde la traza: causa `mavlink_no_heartbeat`, cero
eventos del driver, cero muestras, cero wrench. Antes del heartbeat no se ha
enviado ningún parámetro, comando, armado ni fuerza: el reinicio no puede
seleccionar por resultado. El intento colgado se conserva (`boots/`, traza y
ULog con hash), el auditor lo valida y el informe publica el recuento. Un
segundo cuelgue del mismo trabajo cuenta rojo. Nada después del heartbeat se
reintenta. 30 s: la cota superior observada de arranque sano, contenedor y
teardown incluidos, es 21.2 s en 341 vuelos (mediana 6.1 s).

Esto relaja la regla «cero reintentos» de v4/v5 sólo en ese punto. Con la tasa
observada (~0,6 % por vuelo), sin la regla, una A de 68 vuelos saldría roja
por este fallo ~33 % de las veces y la cadena completa ~50 %.

**Agregación sin excepciones.** Cada grupo se calcula por separado con el
código congelado. Con todos los vuelos medidos el veredicto es idéntico a v4
(comprobado sobre los 44 vuelos reales de v4). Una medida ausente es un caso
rojo; un error inesperado pone rojo su grupo. Un trabajo que lanza excepción
se registra como fila fallida y cuenta en el denominador. La etapa siempre
vuela sus negativos y escribe `report.json`.

**Auditor.** Un vuelo que no despegó no necesita plan de etapas; uno completado
sigue exigiendo las cinco con su duración. Se añade la mutación
`forged_boot_restart`.

**Lanzamiento.** `campaign start` desacopla la cadena en su propia sesión con
log en `lab/flight1s-v6-run.log`. V4 murió con la shell que la lanzó.

## Lo que no cambia

Configuración v5 (`gpsaccuracy_7n`, imagen `v1.15.4-gpsaccuracy`, 7 N/600 ms),
criterios v4 completos (200 mm, 3 s, ventana 10 s, desafío >250 mm, impulso
500–1500 ppk, envolvente 1000 mm, contraste por mundo, controles, mutantes),
tamaños (A 64+4, banco 48+3), dos contenedores, órdenes nuevos 20260925 (A) y
20260926 (banco). Ningún cambio en Q/T/CAM/WSP ni en kernel.

## Repetición del candidato y regla de parada

V6 vuelve a volar el candidato de v5 tras un rojo. El contrato v4 dice que una
etapa roja «no autoriza repetir hasta conseguir un pase». Nav acepta esta
repetición, una vez, porque v5 no falló por la física medida sino por
infraestructura y agregación, y v6 fija sus reglas antes de volar. V5 sigue
roja; v6 no la reescribe.

Regla de parada, fijada antes del lock: si v6 queda roja por un grupo físico
(estímulo, desafío, recuperación, envolvente física, separación, repetición,
seguridad observada o controles), `gpsaccuracy_7n` queda cerrado y no habrá
v7 con esta configuración. Un rojo sólo de infraestructura se publica rojo
igualmente y no autoriza por sí mismo otra cadena.

Un verde v6 significaría estabilidad SITL bajo esta configuración; no
autonomía echoAI, hardware real ni sim-to-real.
