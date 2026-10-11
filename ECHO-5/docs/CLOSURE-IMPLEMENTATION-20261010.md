# ECHO-5: implementación del cierre experimental

Alcance autorizado el 10 de octubre de 2026: ampliar representación, memoria,
composición, interacción y aprendizaje por contraejemplos; integrar MissionAgent
y ejecutar SITL nuevo; proporcionar un sandbox MiniGrid/BabyAI y un panel local
de decisiones y actividad real. S6 se retoma después de ECHO-5.5.

La evaluación distinguirá implementación, corrección, transferencia medida y
superioridad. Un resultado negativo no se convierte en verde cambiando su
denominador. Cada ensayo guarda contrato, fuentes, costes, casos y auditoría.
Los casos de desarrollo y confirmación tendrán semillas separadas. Los límites
y criterios se escriben antes de medir confirmación. Cualquier revisión tras
ver resultados necesita otra versión y conservar la anterior.

## Distribución de implementación

- Representación: extender `solver.py`, `programs.py`, `grounding.py` y añadir
  `transfer.py`; probar nuevos generadores, composición profunda, recuerdos
  adquiridos frente a biblioteca vacía, fija y de control del mismo tamaño.
- Interacción: añadir `sandbox.py` y `sandbox_eval.py` para MiniGrid/BabyAI,
  observación parcial y comparación de estrategias. El actor no recibe el
  estado secreto, la semilla ni la respuesta del evaluador.
- Robótica: añadir `mission.py` y `sitl.py` importando MissionAgent y gateways
  existentes. Distinguir simulación discreta de ejecución PX4/Gazebo real.
- Evidencia: añadir evaluación ampliada de contraejemplos, runner de cierre,
  auditoría, manifiestos y checklist calculado desde recibos.
- Panel: servidor HTTP local y assets propios. Usa el diario existente;
  muestra hipótesis, evidencia, predicciones, acciones, consecuencias, memoria
  y presupuesto. Las vistas neuronales identifican el módulo medido y su
  papel; una actividad auxiliar no se atribuye al selector de acciones.

## Interfaces compartidas

Cada banco nuevo expone `run_benchmark(config, journal=None)` y devuelve un
JSON con `schema`, `config`, `rows`, `summary` y `gates`. Cada fila conserva
identidad de caso, condición, éxito adjudicado externamente, costes y resultado.
El diario admite `write(kind=..., **facts)`, mediante `echo5.trace.Recorder`.
La auditoría recalcula los criterios; los indicadores del actor no adjudican.
La API de sandbox ofrece episodios paso a paso para el panel, además del banco.

## Orden de ejecución

1. [x] Programar los subsistemas y sus pruebas, sin iniciar campañas.
2. [x] Completar contratos numéricos y separar desarrollo de confirmación.
3. [x] Programar el panel, límites de ejecución y observación real.
4. [x] Revisar las interfaces y las fronteras del evaluador.
5. [x] Lanzar comprobaciones y pruebas en segundo plano, tras programación.
6. [x] Corregir fallos de instrumentación conservando sus recibos.
7. [ ] Congelar fuentes y ejecutar confirmación en segundo plano.
8. [ ] Auditar resultados desde otro proceso y revisar el panel en navegador.
9. [ ] Actualizar checklist con resultados, límites y enlaces reproducibles.

## Restricciones

Python 3.12.13 en entorno ECHO-5; dependencias externas explícitas y aisladas.
No editar fuentes históricas congeladas. No usar echo-discord. No activar
LLM en NEXUS-0, ni entrenar pesos, ni gastar créditos de nube. No volar hardware.
El servidor escucha sólo en loopback; `echoai.internal` será alias local si
puede configurarse sin cambiar DNS público. El panel no inventa pensamientos.

Riesgos a comprobar: filtración de etiquetas/estado oculto; memoria incorrecta
que obtiene autoridad por hash; costes omitidos; episodios no terminados;
coincidencia de trazas confundida con corrección; prompts/datos convertidos en
código; conflictos de puertos o procesos SITL ajenos; UI que dibuja actividad
aleatoria; cambio de fuentes durante una medición.

Por petición del usuario, las pruebas CPU se ejecutan en segundo plano cuando
todos los componentes estén programados. Este orden sustituye la ejecución
intercalada de tests; las pruebas se escriben junto con las interfaces.
