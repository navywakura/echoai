# POWER-1 — verde funcional, no consumo físico certificado

2026-09-17. Implementación, banco reservado y auditoría independiente
completados. [Contrato prospectivo](POWER1-DESIGN.md).

## Resultado

Cada etapa reservada tiene 64 semillas ×5 condiciones ×3 políticas:
960 episodios, 320 por política. Desarrollo añade 240; total 2.160.

| Medida del completo | B | C |
|---|---:|---:|
| Finaliza en home con reserva ≥40 sim_u | 320/320 | 320/320 |
| Metas factibles completadas | 128/128 | 128/128 |
| Metas completadas por umbral fijo | 64/128 | 64/128 |
| Coincidencia inicial con oráculo | 320/320 | 320/320 |
| Abortos correctos / falsos | 192 / 0 | 192 / 0 |
| Muertes / violaciones de reserva | 0 / 0 | 0 / 0 |
| Permisos para metas globalmente inviables | 0 | 0 |
| Reserva mínima final, sim_u | 79 | 75 |
| Consumo total completo / fijo, sim_u | 19.283 / 24.129 | 18.948 / 23.432 |
| Latencia P99 del consumidor aislado | 0,208 ms | 0,158 ms |

El oráculo también completa 128 metas por etapa; el completo alcanza ese
techo **en este dominio construido**. Contraste por semilla: 64 victorias,
cero derrotas en B y en C, p unilateral = 5,4210×10⁻²⁰.
Wilson 95% descriptivo: 128/128 factibles [0,9709, 1]; 320/320 con reserva
[0,9881, 1]. El JSON publica además el denominador de todas las misiones:
128/320 metas (40%; intervalo [0,3478, 0,4546]), pues 192 eran inviables.
Los cinco casos de cada semilla no se cuentan como muestras independientes
en el contraste principal.

**El umbral fijo también acaba 320/320 episodios sin muerte ni violación de
reserva.** La ventaja demostrada es completar más metas factibles, evitar
abortos falsos y gasto innecesario, no reducir muertes. Sus 295/285 permisos
para metas globalmente inviables son inicios/continuaciones que luego
abandona, no 295/285 accidentes ni violaciones efectivas de reserva.

## Qué se implementó

`nexus0/power1/core.py`: tabla aprendida de recibos de consumo, media nominal,
cota conservadora y gate entero que suma ejecución, retorno desde la meta,
aterrizaje y reserva. Retorno enclavado; sin reintentos tras cerrar sesión.
Caducidad, reloj, aumentos de batería, cambios de capacidad, rutas desconocidas
y unidades incompatibles impiden afirmar viabilidad.

Calibración A: 96 recibos (32 por habilidad). Costes nominales norte/sur/
aterrizaje: 10/14/21; cotas: 15/20/29 sim_u. No se ajustan en B/C.
Las misiones empiezan ya en vuelo; la batería indicada es el presupuesto
restante en ese instante, no incluye una certificación de coste de despegue.
Las rutas son conocidas y vienen del exterior del gate: no hay otro
planificador, descubrimiento de mapas ni integración nueva con COMPOSE.

El consumidor de coste y el control fijo se ejecutan en la jaula SIM-3,
sin mundo, etiquetas, semilla ni costes futuros. El supervisor privado sólo
ejecuta el WSP canónico (16 bytes) y descuenta el consumo simulado.
Stop termina la misión y el supervisor funcional aterriza; **no es evidencia
de que PX4 haya ejecutado ese aterrizaje en este banco**. Sin segundo bus,
LLM, nuevos CAM/Q/T, cambios de pesos por muerte ni hardware Akida.

## Evidencia, controles y límites

78 tests aprobados, incluidos 30 nuevos de POWER-1. Seis mutantes detectados
(retorno, aterrizaje, incertidumbre, reserva, caducidad, enclavamiento),
cuatro manipulaciones de episodios rechazadas (sensor, WSP, coste privado,
resultado), pruebas de unión modelo/recibos y tres alteraciones de informe
rechazadas aun recalculando su hash. Auditoría repetible sin sobrescrituras.

Replay de los **doce vuelos ya existentes de PX4-1**, no vuelos nuevos:
2.197/2.197 muestras de batería se rechazan para estimar energía utilizable
porque el SITL publica corriente desconocida (-1), capacidad cero y tiempo
restante no válido. No se inventan amperios, capacidad ni julios. El adaptador
externo distingue carga estimada `mC` de las unidades simuladas `sim_u`.
La tabla simulada no acepta datos físicos de otra unidad como si fueran
equivalentes. El certificado y las fuentes congeladas de PX4-1 se preservan.

No demuestra consumo real, autonomía temporal física, comportamiento bajo
viento/carga fuera del dominio de costes, navegación integrada, descarga
electroquímica, HIL ni jaula. Falta calibrar con batería instrumentada y
validar la cadena en vuelo continuo; los failsafes PX4 siguen siendo la
última autoridad y no se modificaron. SAFE-1 e integración DRONE-3 permanecen
pendientes. El C sellado de TRANSFER-3 no se ha utilizado.

## Certificado y reproducción

Lock: `7e59dfee77e278c507a93aea6b41e9e590ff3467601e70e20515f579c43285fb`.
Certificado: `6a05ad4c8be2d2cbbeec720b786a426a20db265fa9b9297654bbca617ba6d7d6`.
Informe: `lab/echo3_power1_report.json`; recibo: `lab/power1/audit-receipt.json`.
Trazas: `lab/power1/{development,validation,confirmation}/episodes.jsonl`.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_power1 -v
PYTHONPATH=.. python3 -m echoai.nexus0.power1.bench audit
PYTHONPATH=.. python3 -m echoai.nexus0.px41.audit
```

Secuencia original: `development`, `freeze`, `accept`, `audit`.
El ejecutor se niega a sobrescribir etapas existentes; B rojo impide abrir C.
La auditoría reconstruye desde semillas, recibos y trazas y compara el
informe completo; no basta con rehashar un JSON manipulado.
