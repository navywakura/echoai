# COMPOSE-1 v3 — resultados

Estado: **rojo en B funcional; fase sin cerrar**. C y aceptación SITL sin abrir.
[Contrato v3](COMPOSE1-V3-DESIGN.md).

V1 conserva su rojo. V2 conserva B válido pero rojo en el test de signos:
`lab/compose1-v2/early-stop.json`, SHA canónico
`8e1afded545d2d3b6fe8a86e616ecba5208a46566c24c9e459652c014655446c`.
C funcional y aceptación física v2 no se abrieron.

## Desarrollo

`lab/compose1-v3/development/algorithms-1/` conserva los dos candidatos,
sus 384 misiones A en total y el código utilizado. Orden por coste acumulado:
8 ventajas, 2 desventajas y 6 empates frente a horizonte uno en 16 metas
alcanzables; prefijos comparables: 8 ventajas, 1 desventaja y 7 empates.
Se seleccionó el segundo. Es selección sobre A, no confirmación independiente.

La escuela física conserva el modelo idéntico a v2, refinado con 56
consecuencias observadas del primer vuelo A de v2. La referencia de origen
cambia de carpeta; los valores aprendidos no cambian.

`sitl-development/round-1/`: 10/10 vuelos aprobados y auditados. Estática:
completo, horizonte uno y convencional llegaron en ocho movimientos; Q
abandonó en origen tras 50. Dinámica: completo y horizonte uno llegaron en
12, convencional en 8; Q retornó tras 56. Cerrado: retorno tras 52 movimientos;
reserva insuficiente: aborto en origen sin desplazarse. No hubo violaciones
observadas de envolvente ni reserva. No se afirma superioridad física sobre
el planificador convencional.

`controls/round-1/` detectó los 13 controles negativos sobre el primer vuelo
válido. Regresión conjunta de congelación: 34 tests aprobados.

## Aceptación

Lock: `e6f01380100936298cbab3186cd8f341aafaf92e7d81ade4a496ce6ab978f46a`.

B terminó con 768 misiones. Completo y horizonte uno alcanzaron las 64 metas
factibles; Q no alcanzó ninguna. Ahorro del completo: 100 movimientos, IC
97,5 % de la media [0,46875; 2,6875]. Test de signos: 22 ventajas, 10 desventajas,
32 empates, p=0,025051229866221547. **No cumple p<0,025.** Se conserva sin
redondear el p, ampliar esta muestra ni abrir C.

[V4](COMPOSE1-V4-DESIGN.md) conserva el agente v3 íntegro y fija prospectivamente
un examen mayor con semillas nuevas, basado en una estimación explícita de
potencia. Reutiliza por hash el desarrollo porque no cambia la implementación;
no cuenta esos vuelos como vuelos nuevos ni cambia el rojo de v3.

La cadena `PYTHONPATH=.. python3 -m echoai.nexus0.compose1_v3.bench finish`
requiere desarrollo completo aprobado. Congela código/protocolo/modelo y
ejecuta B/C funcional, B/C SITL, certificado y auditoría nueva. Rechaza carpetas
existentes y no elige reintentos favorables. Informe final previsto:
`lab/echo3_compose1_v3_report.json`.

El siguiente hito después de un cierre verificable es **CAUSE-1**. Este banco
no cierra PX4-1, POWER-1 ni SAFE-1: usa energía abstracta, salas extruidas,
vuelo a altura fija y un marcador visual proporcionado. No hay hardware,
recarga eléctrica, manipulación de herramientas ni un LLM en el agente.
