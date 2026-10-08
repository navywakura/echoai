# FLIGHT-1S v3 — resultados medidos

**Estado: sin certificado. Bloqueo técnico caracterizado y cuantificado.**
Fecha: 2026-09-10. Diseño: [FLIGHT1S-V3-DESIGN.md](FLIGHT1S-V3-DESIGN.md).
Historias v1 y v2 intactas y auditables.

Cuatro candidatos preregistrados, ocho campañas A, 176 vuelos frescos. Ninguno
cierra. El obstáculo ya no es el controlador ni la dosis: es la **deriva de la
estimación** de EKF2, y está medida.

---

## 1. Qué se ejecutó

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign development pd_7n        # pass 8/8
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign validation  pd_7n        # FAIL 28/64
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign development noaid_7n     # error de lista blanca
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign development noaid_7n --attempt 2   # pass 8/8
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign validation  noaid_7n     # not_run 36/64 (flake)
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign validation  noaid_7n --attempt 2   # PASS 64/64 + 4 controles
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v3.campaign validation  noaid_7n --attempt 3   # FAIL 28/64
```

Todas las campañas se conservan enteras, incluidas las rojas y la interrumpida.
Ningún directorio se sobrescribe: el arnés lo impide.

---

## 2. El candidato nuevo de esta sesión: `noaid_7n`

Declarado en el diseño **antes** de medirlo, tras diagnosticar el rojo de
`pd_7n` contra la pose real de Gazebo:

```text
pose real, excursión máxima            255,1 mm
setpoint local de PX4, recorrido        24,6 / 13,9 mm
estimación local de PX4, recorrido     176,5 / 198,7 mm
error de seguimiento al setpoint       p50 59,4 mm, máx 86,4 mm
```

PX4 sostiene su setpoint con 86 mm en el peor caso. **El controlador no falla.**
Lo que se mueve es la estimación, y el cuerpo la sigue. Por eso ni `damped_8n`
ni `settled` podían corregirlo: ninguno toca la estimación, y la dosis no
interviene en un vuelo nominal.

Causa, por inspección de fuentes en la imagen congelada:

```text
SensorGpsSim.cpp:118  inyecta ruido horizontal de sigma 0,2 m
SensorGpsSim.cpp:137  pero declara eph = 0,9 m
gps_control.cpp:203   pos_noise = max(hacc, EKF2_GPS_P_NOISE)
gps_control.cpp:205   con GNSS como única ayuda: pos_noise = min(pos_noise, EKF2_NOAID_NOISE)
```

Es el mismo defecto que el retardo, en el mismo archivo: el sensor simulado se
describe peor de lo que es. EKF2 usa 0,9 m de sigma donde hay 0,2 m —varianza
sobreestimada por 20— infrapondera el GNSS y se apoya en integración inercial,
que deriva. `EKF2_GPS_P_NOISE` no sirve porque `hacc` domina el máximo; el único
parámetro capaz de bajar ese suelo es `EKF2_NOAID_NOISE`, con mínimo documentado
**0,5** — todavía 2,5 veces el sigma real.

`noaid_7n` = `pd_7n` + `EKF2_NOAID_NOISE=0,5`. No se reduce el ruido inyectado,
no se suministra groundtruth, no se tocan las bandas.

### Funcionó, y no lo suficiente

```text
validación A intento 2   64/64 vuelos + 4 controles negativos   PASS
validación A intento 3   falla en el vuelo 28: nominal 280,5 mm  FAIL
```

El mismo mundo, la misma repetición que ya había fallado con `pd_7n`.

---

## 3. El número que decide

Excursión de los vuelos **nominales** —sin wrench— de toda la familia
`noaid_7n`, agregando desarrollo y las tres validaciones:

```text
n = 68 vuelos nominales
min 88,0 mm   p50 ~160 mm   max 280,5 mm
por encima de 250 mm: 1 de 68  ->  1,5 % por vuelo
```

De ahí, con las bandas congeladas:

```text
P(al menos un nominal > 250 mm en el brazo de 24 del banco)        30 %
P(al menos un nominal > 250 mm en el brazo de 32 de la validación) 38 %
P(una cadena validación + banco completa en verde)                ~43 %
```

**El pase 64/64 del intento 2 fue suerte, no robustez.** Autorizar el banco con
esa campaña mientras el intento 3 existe y falló sería escoger la corrida, que
es exactamente lo que el diseño prohíbe. Por eso no se ha abierto el banco.

Para contraste, la separación entre poblaciones es total y nunca ha fallado:

```text
nominales   n=68    88,0 .. 280,5 mm
perturbados n=84   413,3 .. 677,0 mm
```

Los dos conjuntos no se solapan en ningún vuelo. Lo que falla es un **techo
duro por episodio** en el brazo de control, no la distinción entre condiciones.

---

## 4. Un fallo de infraestructura, no de vuelo

`validation-noaid_7n` (intento 1) se detuvo en el vuelo 36 con
`mavlink_no_heartbeat`: PX4 arrancó, Gazebo entregó 121.489 muestras de reloj y
7.064 poses, y el ULog de 26 MB muestra al autopiloto vivo durante 114 s con
avisos de deriva GPS en preflight. No hubo evidencia de vuelo.

Frecuencia medida del aviso: 1 de 36 ULogs con `noaid_7n` frente a 3 de 28 con
`pd_7n`, así que no es efecto del parámetro nuevo. Se trató como episodio sin
evidencia y **se repitió la campaña entera**, nunca sólo el vuelo fallido.

---

## 5. Lo que sí quedó demostrado en v3

- `EKF2_GPS_DELAY=0` corrige un desajuste real entre el sensor simulado y el
  filtro, verificado en MAVLink y en ULog en cada episodio.
- El controlador amortiguado (`P=3`, `D=0,4`, `I=0`) sostiene su setpoint con
  ≤86 mm de error incluso cuando el cuerpo deriva 255 mm.
- Con 7 N durante 600 ms el desafío es holgado: 84 vuelos perturbados, mínimo
  413,3 mm frente a un umbral de 250 mm; ninguno se quedó dentro.
- La recuperación pasó en todos los perturbados de `noaid_7n`.
- Los controles negativos separan limpiamente: sin wrench, `stimulus` suspende.
- El watchdog de reloj real cierra contenedores con reloj congelado; se
  encontraron y detuvieron dos abandonados por bancos históricos.

---

## 6. La vía elegida: corregir la etiqueta del sensor

Roger autorizó atacar la causa raíz. Se construyó
`echoai-flight1s-px4:v1.15.4-gpseph`, la imagen congelada con **una línea**
cambiada:

```diff
-			sensor_gps.eph = 0.9f;
+			sensor_gps.eph = 0.2f; // FLIGHT1S-v3: match the injected sigma
```

Verificado dentro de la imagen: el ruido inyectado sigue siendo
`generate_wgn() * 0.2` en los dos ejes, `epv = 1.78f` sin tocar, commit PX4
`99c40407…` sin tocar, binario nuevo `3a83b5cc…`. La imagen de v1/v2 conserva su
etiqueta y su lock.

Candidato `gpsfix_7n`: retardo 0, `P=3`, `D=0,4`, `I=0`, `EKF2_GPS_P_NOISE=0,2`
—necesario porque `max(hacc, gps_pos_noise)` dejaría el suelo en el 0,5 por
defecto— y 7 N. Con eso el filtro usa por fin la sigma real de 0,2 m.

**Falló el desarrollo A en el vuelo 6 de 8**, con un nominal de 286,8 mm:
peor que el candidato anterior, que había pasado 8/8.

Por qué, medido en el ULog del mismo mundo y la misma repetición:

| candidato | jitter por muestra | deriva lenta | dispersión de la estimación |
|---|---:|---:|---:|
| `pd_7n` (eph 0,9, por defecto) | 0,86 mm | 417,3 mm | 554,5 mm |
| `noaid_7n` (eph 0,9, NOAID 0,5) | 0,82 mm | 233,2 mm | 254,3 mm |
| `gpsfix_7n` (eph 0,2, P 0,2) | **1,66 mm** | 330,0 mm | 452,3 mm |

Al decirle al filtro la verdad, la estimación deja de suavizar y **sigue el
ruido blanco del sensor**: el jitter se duplica. El cuerpo sigue la estimación,
así que la excursión real no baja. La etiqueta de 0,9 m era incorrecta, pero
estaba actuando como suavizado.

El problema queda acotado por los dos lados:

```text
filtro demasiado conservador (0,9)  -> deriva lenta, excursión > 250 mm
filtro con la sigma correcta (0,2)  -> sigue el ruido, excursión > 250 mm
```

### El suelo físico

El X500 no tiene más sentido de posición horizontal que un GNSS que inyecta
sigma 0,2 m por eje, sin ninguna otra ayuda. El criterio exige que el
**máximo** de la desviación radial sobre una ventana de 10,6 s se quede por
debajo de 250 mm en **cada** vuelo. Un máximo sobre ~500 muestras alcanza
rutinariamente 2,5–3 sigma del error residual del estimador; con 250 mm, eso
sitúa el techo justo en el 3 sigma de lo mejor que este estimador puede hacer.
No es un fallo de sintonía: es el suelo de ruido del sensor.

## 7. Bloqueo

No queda ningún parámetro de PX4 que ataque la deriva sin tocar la imagen
congelada: el suelo de la varianza de observación es el `eph` que el propio
sensor declara, y `EKF2_NOAID_NOISE` ya está en su mínimo.

De las dos salidas que se plantearon, la primera ya se probó y está medida
arriba: corregir la etiqueta del sensor no cierra el tajo, y ahora se sabe por
qué. Queda una:

- **Convertir el brazo de control en un criterio distribucional.** El techo
   nominal existe para mostrar que el umbral significa algo, y eso es una
   afirmación sobre poblaciones, no sobre cada vuelo. Los datos ya la sostienen
   sin solape. Pero cambiar el criterio después de cuatro campañas rojas es
   exactamente el patrón post-hoc que v1 y v2 se negaron a hacer, y exigiría un
   protocolo v4 declarado antes de medir.

Mientras no se elija, los rojos se conservan y FLIGHT-1S no se declara cerrado.
