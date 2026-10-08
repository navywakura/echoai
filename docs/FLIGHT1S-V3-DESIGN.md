# FLIGHT-1S v3 — corregir la respuesta conservando las bandas v2

Estado: desarrollo; ninguna afirmación de cierre. Fecha: 2026-09-10.

Se conservan íntegros código, protocolos y evidencias v1/v2. Esta revisión
prueba configuración de PX4 en un subpaquete nuevo; no reetiqueta sus rojos.
La autorización para reparar procede del usuario. No hay hardware ni LLM.

## Diagnóstico y candidatos prefijados

El ULog del nominal rojo muestra un error local respecto al setpoint de sólo
87 mm durante recuperación, mientras el error de estimación cambia unos
248 mm en un eje. Por tanto, aumentar únicamente las ganancias no garantiza
corregir la deriva. El vuelo perturbado muestra además sobreoscilación real.
Las diferencias absolutas de origen entre groundtruth y EKF no se interpretan
como error; interesa su variación temporal.

La imagen fijada PX4 v1.15.4 implementa SensorGpsSim con ruido y timestamp de
muestra, sin una línea de retardo de 110 ms. El ULog registra unos 17 ms entre
timestamp_sample y publicación; EKF2_GPS_DELAY vale 110 ms. Primera hipótesis:
ajustar el retardo configurado al sensor simulado evita compensación temporal
incorrecta. Verificar su efecto sólo en A; no extrapolar a un GNSS físico.

Fuentes primarias inspeccionadas dentro de la imagen congelada:
`src/modules/simulation/sensor_gps_sim/SensorGpsSim.cpp`,
`src/modules/simulation/gz_bridge/GZBridge.cpp`.
Referencia de parámetros: https://docs.px4.io/v1.15/en/advanced_config/parameter_reference

Candidatos de desarrollo, en orden, antes de nuevas corridas:

1. `delay`: EKF2_GPS_DELAY=0 ms, demás parámetros originales.
2. `damped`: retardo 0; MPC_XY_VEL_P_ACC=3.0,
   MPC_XY_VEL_D_ACC=0.4. Mayor amortiguación del controlador de velocidad.
3. `settled`: configuración damped, estabilización previa de 20 s en lugar
   de 5 s. La preparación más larga se declara como coste del protocolo.

No se reduce ruido, modifica masa, suministra groundtruth al controlador,
añaden sensores ni cambia el modelo. PX4 estabiliza y mezcla actuadores.
Parámetros enviados y confirmados deben quedar tanto en eventos como en ULog.

## Regla de selección y cierre

Exploración de candidatos: cuatro mundos A, una pareja fresca nominal/perturbada
por mundo, por candidato. Se conservan todos los intentos. Se elige el primero
que cumpla todas las bandas originales. Luego validación A con 8 parejas por
mundo (64 episodios) y 4 controles sin wrench. Si falla, no se abre B/C:
el candidato se descarta y se prueba el siguiente, conservando el rojo.
Si ninguno pasa, se publica bloqueo técnico y se requiere otra hipótesis.

### Extensión de calibración tras probar damped a 5 N (antes de B/C)

El candidato damped frenó un empujón en 216,784 mm: recuperación válida pero
sin salir de 250 mm. Su nominal quedó en 191,354 mm. Se conserva el descarte
en development-damped-r2; no es prueba de desafío suficiente. Antes de abrir
B/C se añade la hipótesis de dosis: el controlador más amortiguado necesita
una fuerza mayor para probar recuperación desde fuera de la banda.

Candidatos nuevos, orden fijo: damped_7n y, sólo si falla, damped_8n, con los
mismos P=3 y D=0,4, retardo 0, y fuerzas de 7 N / 8 N durante 600 ms.
Se conserva el radio 200, margen 50, timeout 10 s, permanencia 3 s y techo
25°. Impulsos mandados: 4200 / 4800 mN·s. Se calcula el cociente respecto a
esa nueva dosis; su banda sigue siendo 500–1500 ppk. No se reduce el ruido.
Se selecciona la primera dosis que complete desarrollo y validación A.
El candidato settled queda aplazado: aumentar preparación no aborda la
insuficiencia de desafío que acaba de medirse. No se declara probado.

Esto cambia fuerza y configuración de vuelo, explícitamente. Un eventual
verde v3 no vuelve verdes las dos campañas históricas a 5 N. El banco sigue
siendo rehearsal ya conocido; no se vende como examen ciego.

### Hipótesis siguiente tras el rojo A de damped_7n

La segunda pareja de validación a 7 N suspendió la permanencia. Entre t+3 y
t+9 s el controlador mantuvo errores de posición estimada de unos 36–102 mm
en el eje principal, y la estimación también derivó. La implementación PX4
integra el error de velocidad con I=0,4; ese término puede persistir tras
eliminar una perturbación corta. No se atribuye todo el fallo al integrador.

Se prueba `pd_7n`: mismos P=3, D=0,4, retardo 0 y dosis 7 N, con
MPC_XY_VEL_I_ACC=0. Se conserva el lazo exterior de posición y los integradores
de altura/actitud; PX4 sigue estabilizando. Hipótesis limitada a la wrench
corta: eliminar la memoria integral horizontal puede reducir el desplazamiento
residual. Puede empeorar rechazo de viento constante; este banco no lo prueba.
El valor 0 está admitido por los parámetros de PX4 v1.15.4. Fuente inspeccionada:
mc_pos_control/PositionControl/PositionControl.cpp y
mc_pos_control/multicopter_position_control_gain_params.c.

Se aplaza aumentar a 8 N porque el último fallo fue recuperación, no falta de
desafío. `pd_7n` exige nuevamente desarrollo A, 64 vuelos/4 controles de
validación A y, sólo si pasa, banco completo. No hay cambios en las bandas.

Regla de descarte explícita antes del candidato damped: un fallo duro en A
permite terminar anticipadamente una candidatura que ya no puede pasar.
Se publica el denominador previsto, el completado y todos los pendientes como
not_run/interrumpidos. No se permite aprobación anticipada: un candidato
aceptado sigue necesitando los 64 vuelos y cuatro controles. El candidato
delay se descartó con 25/64 vuelos completos por un nominal de 266,481 mm;
su archivo discarded.json y sus trazas se conservan. B/C no se ha abierto.

### Hipótesis siguiente tras el rojo A de pd_7n

`pd_7n` completó desarrollo A 8/8 y cayó en validación A en el vuelo 28 de 64:
el nominal `nominal-eddc87870377f61b-r6` derivó 255,101 mm sobre el límite de
250 mm. Es el tercer candidato que cae por deriva del **nominal**, nunca por
recuperación ni por estímulo. Se conserva el descarte y los 28 vuelos
completos; los 36 restantes son not_run.

Medición del mecanismo en ese ULog, contra la pose real de Gazebo:

```text
pose real, excursión máxima            255,1 mm   (253,5 mm en el eje y)
setpoint local de PX4, recorrido        24,6 / 13,9 mm
estimación local de PX4, recorrido     176,5 / 198,7 mm
error de seguimiento al setpoint       p50 59,4 mm, máx 86,4 mm
```

PX4 sostiene su setpoint con 86 mm en el peor caso: el controlador no falla.
Lo que se mueve es la **estimación**, y el cuerpo la sigue. Aumentar ganancias
no puede corregir esto, y por eso `damped_8n` y `settled` tampoco lo harían:
ninguno toca la estimación y la dosis no interviene en un vuelo nominal.

Causa en la imagen congelada, por inspección de fuentes:

```text
SensorGpsSim.cpp   inyecta ruido horizontal de sigma 0,2 m
                   (generate_wgn() * 0.2, líneas 118-119)
SensorGpsSim.cpp   pero declara eph = 0,9 m  (línea 137)
gps_control.cpp    pos_noise = max(hacc, EKF2_GPS_P_NOISE)          (línea 203)
gps_control.cpp    con GNSS como única ayuda horizontal, además
                   pos_noise = min(pos_noise, EKF2_NOAID_NOISE)     (líneas 205-211)
```

Es el mismo defecto que el retardo, en el mismo archivo: el sensor simulado se
describe peor de lo que es. EKF2 usa 0,9 m de sigma donde hay 0,2 m —
sobreestima la varianza en un factor 20— infrapondera el GNSS y se apoya en la
integración inercial, que deriva. `EKF2_GPS_P_NOISE` no sirve aquí porque
`hacc` domina el máximo; el único parámetro que puede bajar ese suelo es
`EKF2_NOAID_NOISE`, cuyo mínimo documentado es 0,5.

Candidato nuevo `noaid_7n`, declarado antes de medirlo: `pd_7n` más
`EKF2_NOAID_NOISE=0,5`, con las mismas ganancias, retardo 0 y dosis 7 N. El
valor no se barre: es el mínimo que el parámetro admite, es decir lo más cerca
del sigma real de 0,2 m que la configuración permite. No se reduce el ruido del
sensor: sigue inyectando exactamente el mismo. No se suministra groundtruth.

**Tensión que este cambio no resuelve y hay que medir.** Ponderar más el GNSS
reduce la deriva de baja frecuencia del nominal, pero también rigidiza el
mantenimiento de posición y puede meter más jitter de alta frecuencia. Lo
primero ayuda al brazo de control; lo segundo puede **reducir la excursión
perturbada** y dificultar el desafío, que exige salir de 250 mm. No es un pase
gratis y puede fallar por el otro extremo. Si falla, el rojo se conserva y se
publica bloqueo técnico: no queda ningún parámetro que ataque la deriva sin
tocar la imagen congelada.

Bandas sin cambios. Si `noaid_7n` pasa desarrollo A y validación A, se congela
y se corre el banco de 48. Si no, no se abre B/C.

### Corrección de la etiqueta del sensor: candidato `gpsfix_7n`

Autorizada explícitamente por Roger tras publicar el bloqueo de `noaid_7n`.
Se declara aquí antes de construir la imagen y antes de volar.

`noaid_7n` midió 68 vuelos nominales con 1 por encima de 250 mm: 1,5 % por
vuelo, es decir ~43 % de que una cadena validación+banco salga verde por suerte.
Su intento 2 pasó 64/64 y el intento 3 falló en el mismo mundo con 280,5 mm.
Autorizar el banco con el intento 2 sería escoger la corrida. No se hizo.

La causa está en la fuente y es una etiqueta equivocada, no ruido:

```text
SensorGpsSim.cpp   latitud/longitud += generate_wgn() * 0.2      -> sigma real 0,2 m por eje
SensorGpsSim.cpp   sensor_gps.eph = 0.9f                          -> declara 0,9 m
gps_control.cpp    pos_noise = max(hacc, EKF2_GPS_P_NOISE)
                   pos_var   = sq(pos_noise), aplicada a cada eje
```

EKF2 consume `hacc` como sigma **por eje**, exactamente la cantidad que el
simulador inyecta por eje. Declararla 0,9 sobreestima la varianza en un factor
20 y obliga al filtro a apoyarse en integración inercial.

Se corrige la etiqueta a `eph = 0.2f`, el valor que el propio archivo inyecta
tres líneas más arriba. **No se reduce el ruido**: el sensor sigue sumando
exactamente el mismo `generate_wgn() * 0.2`. No se suministra groundtruth, no
se cambia masa, modelo ni sensores.

Se deja deliberadamente sin tocar `epv = 1.78f`, que está mal por la misma
razón (inyecta 0,5 m): el fallo medido es horizontal y ampliar el parche
añadiría una variable al brazo vertical sin necesidad. Queda registrado como
defecto conocido y no corregido.

Corregir `eph` por sí solo no basta: `max(hacc, EKF2_GPS_P_NOISE)` dejaría el
suelo en el 0,5 por defecto del parámetro. El candidato fija además
`EKF2_GPS_P_NOISE=0.2`, dentro de su rango documentado (0,01–10), de modo que
el filtro use la sigma real. Con eso `EKF2_NOAID_NOISE` deja de hacer falta y se
devuelve a su valor original.

```text
gpsfix_7n = EKF2_GPS_DELAY 0, MPC_XY_VEL_P_ACC 3.0, MPC_XY_VEL_D_ACC 0.4,
            MPC_XY_VEL_I_ACC 0, EKF2_GPS_P_NOISE 0.2, dosis 7 N / 600 ms
            sobre imagen echoai-flight1s-px4:v1.15.4-gpseph
```

**Qué cambia esto en el significado del resultado.** La imagen deja de ser la
de v1/v2: el binario PX4 es otro y su SHA-256 lo dirá. Un verde de `gpsfix_7n`
sería sobre un PX4 con una línea corregida en su sensor GNSS simulado, no sobre
el binario histórico, y no vuelve verdes v1 ni v2. El commit de PX4 sigue siendo
`99c40407…`; el parche se aplica sobre el árbol y se publica su diff y su hash.
Las imágenes y locks de v1/v2 no se tocan: la nueva lleva etiqueta propia.

Bandas sin cambios: mismo radio, margen, permanencia, timeout, banda de impulso
y techo de actitud. Si `gpsfix_7n` falla desarrollo o validación A, se conserva
el rojo y no se abre el banco.

*Resultado, medido:* `gpsfix_7n` falló el desarrollo A en el vuelo 6 de 8 con un
nominal de 286,8 mm. La corrección es real —el filtro usa por fin la sigma que
el sensor inyecta— pero al dejar de sobreestimar la varianza la estimación pasa
a seguir el ruido blanco del GNSS: el jitter por muestra se duplica (1,66 frente
a 0,82 mm) y la excursión real no baja. El problema queda acotado por los dos
lados y el techo de 250 mm por episodio queda en el suelo de ruido del sensor.
Se conserva el rojo. Ver [FLIGHT1S-V3-RESULTS.md](FLIGHT1S-V3-RESULTS.md) §6.

Bandas v2 conservadas: estímulo 500–1500 ppk, wrench única y retirada,
nominal <=250 mm, perturbado >250 mm, retorno <=200 mm y 3 s continuos dentro
de los 10 s originales, actitud <=25°, repetición <=5 s. No se amplía ventana
de recuperación ni radio. Hover vertical/horizontal se sigue publicando.

Tras validar A se congela configuración, código, protocolo y lock. Examen:
12 mundos rehearsal, 2 condiciones, 2 repeticiones, 48 episodios frescos.
Seed de orden 20260915; desarrollo/validación A usan 20260913/20260914.
Los mundos son públicos ya vistos, no examen independiente de generalización.
Un fallo permanece rojo; no se repiten sólo fallidos ni se escoge la corrida.

La ejecución puede usar dos contenedores aislados simultáneos; cada episodio
tiene reloj simulado y directorio propios. Se publica el paralelismo y el
tiempo real; no se interpreta su RTF como mejora del vehículo. Orden de
asignación fijado antes de ejecutar; finalización asíncrona no cambia el orden.

## Evidencia

Rutas nuevas: nexus0/flight1s/v3, lab/flight1s-v3 y
lab/echo3_flight1s_v3_report.json. Guardar trazas y ULog también en validación A.
Auditor: hashes de ambas historias, protocolo, código, imagen, configuración
real de PX4, denominadores exactos, métricas recalculadas desde muestras,
casos/grupos coherentes y controles de manipulación del informe.
Una evidencia válida roja sigue siendo válida y roja. Ninguna mediana oculta
una violación. Cero cambios en SIM-3, WSP, Q/T/CAM ni kernel; sin commit/push.
