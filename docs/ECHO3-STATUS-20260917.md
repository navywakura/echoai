# ECHO-3 — estado del 17 de septiembre de 2026

Actualizado el 18 de septiembre tras cerrar HOST-1.

**13/15 hitos con certificado verde en su alcance software; dos pendientes.**
ECHO-1 y ECHO-2 permanecen cerrados. El recuento no es porcentaje de esfuerzo.
La [revisión del 14 de septiembre](ECHO3-STATUS-20260914.md) se conserva como
historial; los cambios desde entonces son los cierres de CAUSE-1, PX4-1, POWER-1, SAFE-1 v2 y HOST-1.

| ID | Hito | Referencia vigente | Alcance |
|---:|---|---|---|
| 1 | SIM-3 | Verde | Infraestructura y aislamiento en host |
| 2 | FLIGHT-1S | v6 verde | Vuelo PX4 simulado |
| 3 | SENSOR-1S | v3 verde | Sensores simulados con procedencia y tiempos |
| 4 | GROUND-1 | v2 verde | Traducción física → WSP |
| 5 | PATTERN-1R | v4 verde | Dos familias LiDAR; examen por replay |
| 6 | FUSION-1 | Verde | Evidencia, caducidad y conflicto; funcional/replay |
| 7 | DYNAMIC-1 | v2 verde | Normal de una cara observada desde hover |
| 8 | COMPOSE-1 | v4 verde | Composición y ejecución PX4 en salas extruidas |
| 9 | CAUSE-1 | Verde SITL | Atribución propia/externa en movimiento normal a una pared |
| 10 | PX4-1 | Verde SITL | Objetivos norte/sur acotados y failsafe por pérdida GCS |
| 11 | POWER-1 | Verde funcional | Coste previsto, retorno, aterrizaje y reserva en energía simulada |
| 12 | SAFE-1 | v2 verde SITL | Contención acotada de fallos y aterrizaje nativo PX4 |
| 13 | HOST-1 | Verde funcional/replay | Autoridad fuente/signo/contexto por consecuencias; comunicación acotada |
| 14 | TRANSFER-3 | Pendiente | Transferencia A→B/C congelada frente a scratch |
| 15 | DRONE-3 | Pendiente | Misión integrada; SITL y después HIL/jaula |

CAUSE-1 completó 16 vuelos de desarrollo y 32 reservados: B 16/16 y C 16/16
correctos frente a 8/16 del control temporal por etapa; cero falsas
atribuciones propias. Evidencia válida y segunda auditoría en proceso nuevo,
exit 0, certificado `a469abab…`. Error máximo externo 122 mm en B y 93 mm en C.
60 tests, cuatro mutantes y siete manipulaciones de trazas detectadas;
siete alteraciones de informe rechazadas. [Resultados](CAUSE1-RESULTS.md).

La intención del banco es experimental, la predicción es nominal de la
habilidad, y la atribución permanece como hipótesis sin escribir CAM/T/Q.
No prueba causalidad general ni movimiento motor frente a fuerzas externas
no medidas sobre el dron. Ese banco no integra todavía la navegación.
Los ocho certificados previos y las versiones rojas se conservan.

PX4-1 cerró por separado: 4 vuelos de desarrollo y 8 reservados; B 4/4 y
C 4/4, 48/48 intentos inválidos bloqueados y cuatro aterrizajes de failsafe
PX4 sin orden externa de aterrizaje. Error máximo B/C 172/354 mm; 48 tests
de cierre y 521 de regresión ampliada (un fallo esperado). Seis mutantes,
cuatro corrupciones de traza y una de informe detectadas. Auditoría en
proceso nuevo válida: `342ca3aa…`. [Resultados y límites](PX41-RESULTS.md).
Una transacción supervisada, altura fija y movimientos norte/sur de 1 m;
sin integración permanente de navegación ni validación hardware.

POWER-1 cerró funcionalmente: B/C, 320/320 episodios con reserva por etapa;
128/128 metas factibles frente a 64/128 del umbral fijo e igual al oráculo.
2.160 episodios, 78 tests, seis mutantes, cuatro episodios manipulados y
tres alteraciones de informe rechazados; certificado `6a05ad4c…`.
Son unidades de energía simulada, no consumo físico ni nuevos vuelos.
El replay de batería PX4-1 se abstiene en 2.197 muestras no instrumentadas.
Integración con batería instrumentada y vuelo continuo aún pendiente.
[Resultados y reproducción](POWER1-RESULTS.md).

SAFE-1 v2 cerró B/C con 6/6 vuelos y 512/512 episodios funcionales por etapa.
Diez fallos contenidos con aterrizaje nativo PX4, sin objetivos nuevos ni
NAV_LAND externo. Veto máximo 288 ms y desarmado ≤27.723 ms desde veto.
108 tests; seis mutantes, cuatro corrupciones y tres alteraciones de informe
detectados. Auditoría en proceso nuevo reproduce `eecb77b8…`, exit 0.
V1 rojo conservado: v2 corrige exclusivamente la comprobación de reintentos
normales de armado, con B/C nuevos y runtime intacto. Fallos antes del
objetivo desde hover; no seguridad general, hardware ni batería física.
[Resultados](SAFE1-V2-RESULTS.md).

HOST-1 cerró funcionalmente: B/C, 1.536/1.536 decisiones útiles frente a
768/1.536 del control recompensa-botón por etapa. 1.024 pérdidas y 1.024
recuperaciones de autoridad por etapa; 14/14 casos de comunicación/arbitraje.
127 tests, seis mutantes, cinco corrupciones y tres alteraciones de informe
detectados. Auditoría en proceso nuevo reproduce `18d4a4fa…`, exit 0.
Calibración supervisada y decisiones leídas sobre cinta cinemática de máquina,
no nuevas metas voladas ni confianza humana general. Replay de tres vuelos
previos con tres observaciones por fuente; ninguna aún alcanza confianza.
[Resultados y límites](HOST1-RESULTS.md).

Orden pendiente:

```
TRANSFER-3 → DRONE-3
```

HIL y jaula física siguen pendientes de hardware. La validación software
puede continuar en el PC; el cierre físico completo no se obtiene por
acumular vuelos simulados. El C sellado de TRANSFER-3 permanece sin consumir.
