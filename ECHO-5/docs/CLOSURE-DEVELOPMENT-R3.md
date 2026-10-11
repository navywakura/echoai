# Desarrollo de ECHO-5 con MissionAgent integrado

10 de octubre de 2026. Fuentes propias: `f6fdf885be552cf519667a63bfcd63d1c5f2028d5b7bec2880307509c8fab98c`.
Los resultados de desarrollo no cierran confirmación. Se conservan r1 y r2.

El cambio activa por defecto `MissionReasoner`, que construye objetos y
relaciones a partir del frame público ya proyectado y llama al planificador
de hipótesis de ECHO-5. El plan sólo puede recorrer celdas admitidas por la
evidencia actual. Los efectos nominales se declaran como priors; no son
efectos aprendidos ni datos de vuelo. MissionAgent conserva POWER, vuelta,
inspección de objetivo y el acceso al gateway supervisado por SAFE.

Cada consecuencia se vincula a secuencia, observación, propuesta, ACK y
muestras de llegada. Una propuesta caducada queda como no ejecutada. El
auditor reconstruye el recorrido desde evidencia y consecuencias; la cadena
no se valida porque el actor escriba una etiqueta de éxito.

| Condición de simulación discreta | ECHO, horizonte 4 | Horizonte 1 | Convencional |
|---|---:|---:|---:|
| Misiones completadas | 4/12 | 4/12 | 3/12 |
| Colisiones | 0 | 0 | 0 |
| Violaciones de reserva | 0 | 0 | 0 |
| Trabajo lógico total | 2.434.343 | 2.428.832 | 1.886.575 |

Frente al convencional hay una ganancia y ninguna pérdida por caso. El coste
sube en 547.768 operaciones. Frente a horizonte 1 se empata en los doce
casos y se gastan 5.511 operaciones adicionales; esta muestra no demuestra
ventaja de ampliar el horizonte. El denominador incluye fallos provocados,
mundos cerrados y misiones que deben detenerse por seguridad.

El recibo está en `artifacts/closure-development-20261010-r3/mission/result.json`.
La auditoría de la campaña se lanza por separado y su resultado se consulta
en `artifacts/closure-development-20261010-r3/audit.json`; este documento no
anticipa su veredicto. La prueba Gazebo/PX4 correspondiente es
`artifacts/sitl-development-20261010-r2/`. Conserva los parámetros previos;
no mezcla el cambio de razonador con una presunta reparación barométrica.

Las pruebas de corrección r4 terminaron: 260 pruebas del núcleo, con 12
omitidas por dependencias opcionales, y 32 del entorno MiniGrid/BabyAI que
cubren esas doce. El panel pasó 14 comprobaciones de navegador y una misión
nativa en 20 acciones. `artifacts/validation-reconciliation-20261010-r4/`
reconcilia desde otro proceso las fuentes completas, comandos/logs, identidad
del servidor, recibo nativo, diario y frames neuronales reproducidos.

El diagnóstico neuronal es opcional y no dirige la política. El servidor
detiene acciones cuando detecta cambios en fuentes; ningún recibo antiguo
puede certificar una versión nueva. Los dos mecanismos tienen pruebas de
fallo específicas. Se mantiene S6 fuera del alcance hasta después de 5.5.
