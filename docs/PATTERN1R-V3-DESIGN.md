# PATTERN-1R v3 — incertidumbre barométrica coherente con el sensor

2026-09-14. Revisión separada; v2 sigue congelada y debe terminar su cadena.
No se permite congelar v3 antes de conservar el informe final auditable de v2.
El contrato sensorial y de reconocimiento de [v2](PATTERN1R-V2-DESIGN.md) sigue
vigente. No cambian firmas, familias, aprendizaje, umbrales, muestras ni mutantes.

## Causa observada y única hipótesis nueva

En A-v2, `clean-11b2f9bdbbccf260` sólo alcanzó 33/48 objetivos. La z real pasó
de aproximadamente 1,6 m a suelo, mientras la estimación global permaneció
cerca de 1,5 m. El barómetro observó la bajada. Tanto altura GPS como barómetro
seguían fusionados. Se conserva el diagnóstico con campos y tiempos del ULog
en `lab/pattern1r-v3/review/`. No se atribuye este fallo a identidad ni a PID.

El SDF fijado declara ruido gaussiano de presión de **0,01 Pa**, a 50 Hz. Cerca
del nivel del mar, la derivada de altura respecto a presión es aproximadamente
0,0833 m/Pa. Incluyendo la cuantización float32 de presión, la desviación de
altura declarada es aproximadamente 0,00085 m. PX4 conserva `EKF2_BARO_NOISE=3.5`
m: su configuración subestima mucho la precisión de este barómetro simulado.

El único candidato de esta revisión fija:

`EKF2_BARO_NOISE = max(0.01 m, sigma_altura_del_modelo)`

0,01 m es el mínimo publicado en `src/modules/ekf2/module.yaml` de la imagen
PX4 fijada; no un valor elegido mediante barrido de vuelos. El contrato calcula
sigma a partir del SDF, la derivada atmosférica y la cuantización, y publica
sus términos. La hipótesis es que dar el peso correspondiente a esta medición
evita la deriva vertical. Debe comprobarse en vuelos nuevos.

Se conserva `EKF2_HGT_REF=0`, GPS_CTRL=7, ruido GNSS, ruido barométrico físico,
geometría, imagen, PID y conversión inicial de altitud de v2. No se añade una
fuente de pose perfecta ni se corrige la altura con verdad durante el vuelo.
Cambian la configuración del estimador y la lista permitida del driver.

## Secuencia fijada antes de medir

1. Pruebas de configuración, fórmula, driver, igualdad del consumidor y
   preservación del código de v2. Desarrollo en los seis mundos 0–5 completos,
   semillas 20261521–20261526, etiqueta `baro-covariance`, sin reemplazos.
2. Sólo 6/6 verdes con el mismo candidato permiten congelar protocolo, código,
   historia completa de v2 y nuevas regresiones.
3. A: ocho vuelos y dos controles, semilla 20261511. Banco: doce vuelos y seis
   mutantes, semilla 20261512, únicamente tras A verde con auditoría válida.
4. Auditoría por recomputación, siete manipulaciones de informe y conservación
   de todos los episodios. Un rojo mantiene la fase abierta.

Criterios iguales a v2: acierto ≥75%, confusión ≤15%, pureza ≥60%, dos familias
distintas, cobertura por objeto, ≥90% de 48 objetivos, geometría, sensores,
aislamiento, memoria congelada e integridad de código/historia por separado.
En el primer candidato el evaluador se importa de v2 y el consumidor se conserva byte a byte.

## Límite

Esta configuración corresponde a un barómetro simulado especialmente preciso;
no es una recomendación para un dron real. No se afirma realismo aerodinámico,
transferencia a hardware, vuelo autónomo decidido por echoAI ni reconocimiento
semántico general. Se mantiene el alcance acotado del banco PATTERN-1R v2.

## Segunda hipótesis, declarada tras desarrollo completo

`baro-covariance` terminó: **6/6 recorridos con 48/48 objetivos**, todos los
grupos físicos/sensoriales verdes; **3/6 fallan identidad**. Su código, informes
y todas las trazas se conservan. No se abrió aceptación. La altura ya no explica
esos errores: w0 y w3 alcanzan sólo 59,37% y 53,55% de acierto.

El diagnóstico w0 muestra una familia de 9 bits y otra de 8 para la misma pared.
`InvariantPatternMemory.observe` crea familia cuando la observación empata entre
dos vecinas, aunque esté dentro del radio. Eso puede introducir un prototipo
intermedio que madura y fragmenta la identidad. `predict` ya abstiene ante empate.

La única regla nueva: **empate dentro del radio y con consecuencia compatible →
observación sin asignar, sin actualizar ni crear familia**. Se contabiliza en
`observations` y `dropped`, conserva el denominador escolar y no recibe etiquetas.
Fuera del radio se conserva la creación de familias, y no cambian mayoría,
madurez=32, radio=3, capacidad=64, consecuencias, firmas ni evaluación congelada.
Es una subclase optativa; `nexus0/pattern1.py` permanece intacto.

La hipótesis se escribió antes del replay de los seis vuelos. Resultado:
6/6 identidades verdes, acierto 88,67–96,32%, confusión 0–6,25%. El replay no
es confirmación independiente. El nuevo candidato `baro-abstain` volará los
seis mundos completos, semillas 20261531–20261536. Se añade `memory.py` a los
archivos fijados durante esa tanda. El evaluador se copia de v2 cambiando sólo
la importación de memoria; el consumidor conserva los mismos bytes.

Sólo 6/6 verdes permiten abrir A. No cambian semillas, muestras, mutantes ni
umbrales de aceptación v3. Los tres rojos previos y el replay quedan en la historia.

## Coste de auditoría

La auditoría mantiene una caché local al proceso, alimentada sólo por su propia
recomputación independiente, nunca por las evaluaciones declaradas del informe.
Cada llamada vuelve a verificar inventario, asignación, archivos de registro,
hashes de trazas, stream privado, transcript, ULog, canarios y reinicios.
Sólo si esas entradas están verificadas se reutiliza un cálculo anterior con
clave completa `(registro, protocolo, package_id)`. Cualquier diferencia de clave
o verificación fallida obliga a recalcular; no se almacena ese resultado no
verificado. Se devuelven copias y se publican conteos `evaluation_work` de
recomputaciones y reutilizaciones. La caché no persiste entre comandos.

Esto reduce las repeticiones durante los siete informes manipulados; no elimina
la primera recomputación de cada episodio ni ninguna comprobación de integridad.
Las pruebas comprueban cambios de firma, traza, protocolo, mundo, entradas sin
verificar y aislamiento de las copias. Se declara antes de abrir A-v3.

## Inicializar antes de estimar

`baro-abstain` termina **5/6 verde**, identidad verde en los seis, pero w5 falla
tiempo causal y respuesta al empujón: al comenzar el recorrido el cuerpo está
en suelo (z≈−0,013 m), mientras PX4 informa altitud global 2,287 m. El recorrido
posterior sí alcanza 48/48. No se abre A ni se elimina ese episodio.

Los parámetros nuevos se estaban aplicando tras conectar MAVLink, cuando EKF2
ya había comenzado a estimar y fijado referencias. La siguiente hipótesis es
inicializar la misma configuración antes del estimador. La imagen fijada ofrece
el hook `. px4-rc.params` después de cargar el airframe y antes del simulador,
`sensors start` y `ekf2 start`. El runner añade un hook privado al PATH, ejecuta
primero el hook original absoluto y aplica sólo los parámetros autorizados,
numéricos y finitos del protocolo. El hook y sus valores quedan registrados.

Tras conectar, el driver solicita lectura de cada parámetro y exige valor y
tipo correctos; no los vuelve a escribir. `MIS_TAKEOFF_ALT` se mantiene en el
mismo punto previo al armado. No cambian valores, sensores, ruido, PID, firmas,
memoria ni criterios. El ULog y la lectura posterior deben corroborar el arranque.

`baro-abstain-preinit`: seis mundos nuevos completos, semillas 20261541–20261546.
Se conserva el código de `baro-abstain` y todos sus resultados. Sólo 6/6 verde
permite abrir A-v3; semillas y denominadores de aceptación permanecen fijados.

Se descartó otra sospecha al revisar el bucle completo: MAVLink ya se drena
continuamente durante las etapas previas. No se cambia la lectura de posición
por una hipótesis de cola antigua que ese ULog no respalda.

## Aislamiento de una regresión histórica

El primer preflight de aceptación v3 se detuvo antes del lock y de cualquier
vuelo. Las pruebas v2 aíslan ROOT temporalmente pero no REPORT; al existir ya
su informe real, la prueba de la puerta de desarrollo recibía `FileExistsError`
antes del `RuntimeError` que intenta probar. Se conserva el intento en
`review/preflight-attempt1/`. El runner `regression_v2.py` ejecuta **las 22
pruebas originales**, con REPORT temporal y ausente; no cambia ni omite ninguna
aserción ni modifica el código v2 congelado. El candidato de seis mundos verdes
permanece intacto. Se vuelve a ejecutar el preflight completo antes de abrir A.
