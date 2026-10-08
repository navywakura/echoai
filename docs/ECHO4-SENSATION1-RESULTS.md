# E4-SENSATION-1 — ventana y auditoría temporal

> Archivo del primer entregable. La fase se cerró después en predicción
> sensorial: [cierre, resultados y límites](ECHO4-SENSATION1-CLOSURE.md).
> Los números y pendientes de este corte histórico se conservan.

2026-09-21. Primer entregable de [SENSATION](ECHO4-SENSATION1-DESIGN.md).

[Informe JSON reproducible](../lab/echo4/sensation1-temporal-audit.json).
Digest del informe (sin el propio campo de digest):
`92b982b57744d39c8744ea4060bcd9c53b3919df8c2ff8ca63a67ba485c4eb5d`.

## Implementado

- `echo4/sensation.py`: ventana local de WSP y acciones ejecutadas, acotada
  a 0, 2 o 4 transiciones pasadas. Payload 16/50/84 bytes, sin cambiar WSP.
- `echo4/sensation_audit.py`: enumeración exhaustiva externa, grupos de
  estados compatibles, ambigüedad y conjuntos de acciones viables.
- `python -m echoai.echo4 sensation-audit`: JSON determinista en stdout,
  con hashes de fuentes y del informe. Sin archivos implícitos ni servicios.

**SENSATION-1 sigue abierta.** No se ha conectado un predictor temporal
aprendido a la política, no hay examen reservado y no se acredita control
ni conciencia. BOUNDARY-1 no se ha iniciado. WORLD-1 y NEXUS-0 no cambian.

## Resultado exhaustivo

Desde todos los 16.002 estados vivos hay 1.296.162 secuencias potenciales
de cuatro acciones. 947.496 permanecen vivas durante los cuatro pasos.
Prefijos terminales a profundidad 1/2/3/4: 5.024 / 9.396 / 23.146 / 59.016.
Su peso como secuencias completas más las supervivientes reproduce el total.

Los tres brazos comparan **los mismos 947.496 prefijos supervivientes**.
Las columnas cuentan prefijos cuyas historias dejan consecuencias distintas
compatibles, no errores de un predictor aprendido.

| Pasos recordados | Payload local | Historias distintas | Ambigüedad de observación o terminalidad | Ambigüedad de terminalidad |
|---:|---:|---:|---:|---:|
| 0 | 16 bytes | 32 | 947.496 | 360.186 |
| 2 | 50 bytes | 1.020 | 926.518 | 233.928 |
| 4 | 84 bytes | 17.628 | 874.554 | 173.498 |

Cuatro pasos dejan 72.942 prefijos adicionales sin ambigüedad en la siguiente
consecuencia para las tres acciones. Pero **874.554 siguen ambiguos**. La
historia aporta información; no hace plenamente observable este mundo.
El aumento del número absoluto de grupos ambiguos no es un empeoramiento:
hay muchas más historias distintas. Se compara con el denominador común.

Esto es una población enumerada condicionada a sobrevivir cuatro pasos,
no la distribución de experiencias de un agente ni una tasa de supervivencia.
No se extrapola a horizontes más largos o a perturbaciones no implementadas.

## Corrección conceptual importante

En el dominio instantáneo completo hay 32 clases con ambigüedad dinámica y
14 con conjuntos de acciones viables diferentes. **No son 32 clases con
decisiones necesariamente incompatibles.** Entre los grupos compuestos solo
por estados individualmente viables, ninguno carece de alguna acción viable
común. Hay además dos grupos que mezclan estados viables y condenados.

Los tres brazos temporales tampoco encuentran grupos totalmente viables
sin acción viable común. Esto no demuestra una política de mantenimiento:
la elección segura de una acción y el control indefinido bajo observación
parcial son preguntas distintas.

## Pruebas y reproducción

26 pruebas nuevas: ventana, presupuesto constante, entradas inválidas sin
mutación, reinicio explícito, delta sensorial, invisibilidad del estado
exacto, replay de una vida real del agente, referencia independiente por
producto cartesiano, contabilidad terminal, testigos alcanzables, fuentes,
CLI y reproducción completa en un proceso nuevo.

93 pruebas seleccionadas de WORLD-1, Q, HEAT, ECHO-2 y NEXUS-0 también pasan.
No se ha ejecutado toda la suite histórica ni reabierto campañas selladas.
La vida del agente original conserva 37 acciones hasta muerte por calor y
0 hechos falsos / 0 ranuras destruidas / 0 llamadas al córtex.

Desde `echoai/`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 sensation-audit
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_sensation1 -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest \
  echoai.tests.test_echo4_world1 echoai.tests.test_qtable \
  echoai.tests.test_heat1 echoai.tests.test_echo2 \
  echoai.tests.test_nexus0.TestWorld echoai.tests.test_nexus0.TestEncoder \
  echoai.tests.test_nexus0.TestGate echoai.tests.test_nexus0.TestBench -q
```

## Siguiente trabajo dentro de SENSATION

Fijar el contrato del predictor aprendido: representación temporal compatible
con CAM/T, memoria total presupuestada, error separado de incertidumbre,
predicción anterior a la consecuencia, baseline instantánea y escenarios
reservados. No alimentar el agente con los conjuntos de estados compatibles
del auditor ni convertir el error en una etiqueta de causa externa.
Solo después procede evaluar BOUNDARY-1 con intervenciones explícitas.
