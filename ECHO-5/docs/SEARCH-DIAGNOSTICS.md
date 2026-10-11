# Autopsia de la búsqueda

`search_diagnostics.diagnose(task, witness, synthesis=...)` llama al sintetizador
con demostraciones y entradas de consulta. Excluye propuestas del investigador,
respuestas de consulta y programa testigo. Sólo después comprueba el testigo y
lo compara con eventos `synthesis_candidate` y `synthesis_selection`.

El indicador `diagnostic=True` es una observación pasiva: no cambia candidatos,
orden, respuestas ni trabajo lógico del buscador. Sí añade tiempo y tamaño de
registro; se declara como instrumentación de desarrollo. Su coste de análisis
se contabiliza en un presupuesto propio, separado del presupuesto del actor.

Se distinguen programa fuera de gramática/profundidad, testigo inválido,
ejecución inválida, prefijo podado, sustitución semántica y agotamiento de
recursos. Una sustitución por un estado equivalente exige seguir ese linaje:
no se interpreta automáticamente como pérdida de capacidad. Tampoco la poda
de un testigo prueba ausencia de otra solución. Si se encontró consenso por
otra ruta se informa expresamente; el evaluador contrasta después la predicción.

El primer piloto usa cuatro familias de desarrollo de `transfer.py` para
diagnosticar el buscador vigente. No cambia la gramática ni promete solucionar
esos casos. Cualquier reparación posterior deberá tener su propio contraste
con la revisión congelada y casos distintos de los utilizados en la autopsia.
