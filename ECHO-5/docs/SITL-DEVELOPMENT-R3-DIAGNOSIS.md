# SITL desarrollo r3: fallo previo a la primera decisión

Investigación del 10 de octubre de 2026. La batería r3 conserva todos sus
episodios y terminó con auditoría independiente: 17 de 18 registros válidos,
sin discrepancias de recálculo y con resultado global negativo. La confirmación
permanece cerrada mientras se valida la nueva configuración en desarrollo.

En `artifacts/sitl-development-20261010-r3/0002-conventional/`, el ejecutor
terminó con `TimeoutError('settled sensor observation')`. Hubo cero respuestas
del agente y coste del actor cero. El contenedor salió con código 1, sin OOM;
el capturador de poses conservó 21.322 registros, sin pérdidas ni regresiones
temporales. No es una derrota del planificador convencional ni una victoria
cognitiva de ECHO: es una preparación del episodio que no produjo evidencia
válida para medir al actor.

La entrega con poca energía ocurrió a los 347,9 segundos simulados, tras
esperar al umbral de 150 unidades. La observación inicial exigía altura
estimada a menos de 300 mm de 2.500 mm. Al iniciar la entrega, el ejecutor
informaba 2.146 mm. Veinte segundos después seguía alrededor de 2.184 mm y
agotó el plazo. La posición horizontal, la velocidad y la frescura de los
sensores del último diagnóstico estaban dentro de sus límites; la altura
explica el rechazo observado. El error genérico no imprimía ese componente
en `observation_failure`; aparece en las muestras de telemetría.

El origen vertical se había capturado antes de armar, a los 7,6 segundos:
`origin[2] = 0.3672452569 m`. El ejecutor calcula
`z_mision = -LOCAL_POSITION_NED.z - origin[2]`. Durante la espera, la referencia
de altura configurada era barométrica (`EKF2_HGT_REF=0`). En una ventana de
dos segundos alrededor de la entrega se observan estas medianas:

| Brazo de poca energía | Origen z (m) | z estimada de misión (m) | z real de Gazebo (m) |
|---|---:|---:|---:|
| ECHO | -0,42658 | 2,595 | 3,07991 |
| Horizonte 1 | -0,68717 | 2,305 | 1,35185 |
| Convencional | 0,36725 | 2,154 | 1,35148 |

Las alturas usan referencias diferentes; no se restan como si fueran el
mismo marco. Sus diferencias y el origen previo al despegue muestran que
hay que revisar referencia y deriva de altura. No se atribuye todo el efecto
a un único parámetro sin medir una intervención. Las poses privadas se usan
para diagnosticar y juzgar; nunca pasan al actor.

PX4 1.15 describe GNSS (`EKF2_HGT_REF=1`) como referencia habitual cuando
está disponible y explica que la estimación converge hacia la fuente de
referencia. La imagen arranca con ese valor; el perfil histórico lo estaba
cambiando a 0. Fuentes primarias: [configuración de altura](https://docs.px4.io/v1.15/en/advanced_config/tuning_the_ecl_ekf#height),
[parámetro](https://docs.px4.io/v1.15/en/advanced_config/parameter_reference#EKF2_HGT_REF)
y [marcos y altitud MAVLink](https://mavlink.io/en/messages/common.html#GLOBAL_POSITION_INT).

Intervención aplicada después de cerrar y auditar r3:
restaurar `EKF2_HGT_REF=1`, conservando `EKF2_BARO_NOISE=3.5`, el resto del
perfil, código de los agentes, mundos, reservas, límites de espera y criterios
del verificador. Medir primero el caso convencional de poca energía en un
directorio nuevo; si resulta válido, realizar otra batería completa antes de
abrir confirmación. La intervención será común a todos los brazos. No se
reemplaza el fallo de r3 ni se convierten sus recibos en positivos.

La calibración nueva terminó a las 23:28 (Madrid), con auditoría independiente
válida en `artifacts/sitl-height-calibration-20261010-r1/audit.json`. El mismo
caso convencional de poca energía produjo un registro válido, aterrizaje en
origen, desarmado y reserva final 129, sin colisiones ni órdenes inseguras.
La captura conservó 20.731 poses con separación máxima de 27 ms. El criterio
de esta prueba es la respuesta segura a falta de energía; no alcanzar la meta.
La evidencia justifica repetir la batería completa con la configuración nueva;
un episodio no demuestra la robustez general de la corrección. El coordinador
`artifacts/closure-pipeline-20261010-r2/` arrancó después de esa auditoría.

La salida por excepción tampoco observó un aterrizaje antes de destruir el
contenedor. El recibo lo considera inválido. Ese comportamiento no se
presenta como parada física certificada; cualquier mejora futura del cierre
de errores debe conservar el fallo original y medir el aterrizaje real.
