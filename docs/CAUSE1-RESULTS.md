# CAUSE-1 — atribución propia y externa, verde SITL

2026-09-17. **`cause1_green=true`, `evidence_valid=true`.** La segunda
auditoría, ejecutada en un proceso nuevo, reconstruye el mismo certificado
y termina con `exit 0`. ECHO-3 pasa a **9/15** hitos verdes software;
siguiente: **PX4-1**.

Certificado: `a469ababf7ac40c3ccf737aaa156793d8f98761faf35df7fe6c5058cfab26954`.
Lock: `c48fd0d067a235d9c53af4bee9a7fa9a29704a16781e5da2b4c1e87266040ca9`.
Contrato congelado: [CAUSE1-DESIGN.md](CAUSE1-DESIGN.md).

## Resultado

| Medida | Desarrollo | B, validación | C, confirmación |
|---|---:|---:|---:|
| Vuelos nuevos del banco | 16 | 16 | 16 |
| Atribuciones correctas | 16/16 | 16/16 | 16/16 |
| Control de coincidencia temporal | 8/16 | 8/16 | 8/16 |
| Acierto por condición | 4/4 en las cuatro | 4/4 en las cuatro | 4/4 en las cuatro |
| Falsas atribuciones propias | 0 | 0 | 0 |
| Error máximo de cambio externo | 131 mm | 122 mm | 93 mm |
| Vuelos con error de residuo ≤300 mm | 16/16 | 16/16 | 16/16 |
| Evidencia y ejecución válidas | 16/16 | 16/16 | 16/16 |

En B y C, por separado: ocho ventajas, cero desventajas y ocho empates frente
al control; test de signos unilateral exacto **p=0,00390625**, frente al umbral
preregistrado p<0,025. IC Wilson 95% de acierto por etapa: **80,64–100 %**.
Son bancos pequeños de un dominio finito; los ticks y rayos no cuentan como
experimentos independientes. Las semillas nuevas varían ruido y geometría
dentro de la familia declarada; no son nuevos tipos de mundo.

Las cuatro condiciones son esperar con pared quieta, mover sólo el dron,
mover sólo la pared y mover ambos. El sentido se invierte entre bloques.
La variación LiDAR de los dos casos individuales es aproximadamente igual;
la odometría permite separar su origen. El caso combinado conserva ambas
contribuciones. Ejemplo reservado B: pared −1.000 mm, dron esperando;
estimación externa **−999 mm**, sin atribución propia.

Los 32 vuelos reservados tuvieron cero muestras de invasión de la envolvente
de pared observadas y todos aterrizaron/desarmaron. El error máximo de la
variación de odometría respecto a la pose privada fue 132 mm en B y 101 mm en C.
Las 32 llamadas al consumidor de cada etapa midieron P99 de ida y vuelta
de **0,889 ms en B** y **0,746 ms en C**, con reloj monótono del host. Esto
no es latencia sensor-motor, plazo garantizado ni consumo energético.

## Qué se implementó y verificó

`nexus0/cause1/` añade un consumidor aislado y opt-in. Recibe intención WSP,
LiDAR y estimador PX4 públicos. Publica una predicción nominal de la habilidad
de 1 m antes del envío del WSP; registra aceptación y contrasta desplazamiento
observado con el esperado. Descuenta el movimiento propio de la variación de
distancia para estimar el cambio de pared. Rechazo de orden, datos caducados,
movimiento sin confirmar o cambios de marco producen desconocido.

La atribución usa enteros; la proyección geométrica se realiza en el adaptador
sensorial. WSP sigue en 16 B. La salida es una hipótesis con evidencia:
`has_fact=false`, sin escrituras en CAM/T/Q ni llamadas a córtex. La predicción
de 1 m es el nominal de una habilidad acotada, no un modelo T aprendido en
este banco. El arnés asigna las intenciones experimentales; no se demuestra
elección autónoma de una misión ni integración con el planificador COMPOSE.

Antes de B se congelaron 305 archivos, semillas y criterios. La puerta corrió
**60 tests**, incluidos 13 de CAUSE-1 y los candados de anillo/gate/ATTEND.
Se comprobó la jaula SIM-3, sin repositorio, procesos vecinos ni red utilizable.
Los 119 archivos del inventario COMPOSE-1 v4 conservaron sus hashes.

Cuatro mutantes funcionales detectados: sin ACK, sin confirmación de movimiento,
sin odometría y sin caducidad. Siete manipulaciones de trazas rechazadas:
ACK, publicación tardía, consecuencia, residuo, orden omitida, semilla y
escritura de pose del cuerpo. Siete manipulaciones adicionales del informe
también se rechazan: falso verde, vuelo omitido, semilla duplicada, ejecución,
etiqueta, residuo y denominador alterados.

El auditor reconstruye desde observaciones, contrasta transporte y cronología,
vincula posición/comandos/ACK al ULog, verifica setpoint frente a intención,
comprueba las poses privadas de dron/pared y conserva los denominadores.
La auditoría final volvió a realizar esas comprobaciones en un proceso nuevo.

## Límites y evidencia conservada

Dominio: vuelo a 2,5 m, una pared plana ancha al norte, traslaciones sobre su
normal y condiciones sin fuerzas externas no medidas sobre el cuerpo. Un
empuje que imitase exactamente un acto motor queda fuera de este banco.
No demuestra causalidad general, seguimiento de objetos arbitrarios,
aprendizaje causal, navegación integrada, superioridad sobre un estimador
convencional, hardware, HIL o jaula física.

Hay **48 vuelos del banco** más un vuelo piloto de desarrollo separado.
El primer intento previo no pudo arrancar Podman por restricciones de archivos;
su resultado fallido está conservado y no se cuenta como vuelo. No se
sustituyeron vuelos de B/C ni se ajustó código tras abrirlos. Los primeros
vuelos de desarrollo conservan revisiones de instrumentación anteriores al
lock; B/C usan las copias exactas de la implementación congelada. C pertenece
a CAUSE-1 y no consume el C sellado de TRANSFER-3.

Artefactos: `lab/echo3_cause1_report.json`, `lab/cause1/lock.json`,
`development/`, `validation/`, `confirmation/`, `regression.json`,
`mutations.json`, `report-mutations.json` y `audit-receipt.json` bajo
`lab/cause1/`.

Reproducción de la auditoría, desde `echoai/`, sin vuelos nuevos:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.cause1.bench audit
```

Resultado observado: `cause1_green=true`, hash `a469abab…`, `exit 0`.
El ejecutor preserva el certificado existente; no relanza ni reemplaza el banco.
