# ECHO-5: integración y evaluación, 10 de octubre de 2026

Se implementa la dirección autorizada: objetos y relaciones (GROUND-1),
programas compuestos (HIER-1), conceptos adquiridos de demostraciones
(CONCEPT-1), interacción informativa y planificación (ADAPT-1/RETRO-1),
integración de robótica previa y un ensayo de contraejemplos. Este documento
fija el alcance antes de medir. ECHO-5.1, 5.5 y RSI siguen siendo etapas
posteriores; S6 no se reabre ni cambia de resultado.

## Arquitectura

El código nuevo vive en `src/echo5/`. Los módulos históricos se importan
mediante `legacy.py`, sin copiar sus algoritmos ni modificar fuentes de 4.5.
`budget.py` contabiliza trabajo lógico entero antes de ejecutarlo.
`trace.py` adapta el diario JSONL existente de `echo_arc.observe`; es un
observador, nunca una entrada para la política ni un segundo bus cognitivo.

`grounding.py` reutiliza la segmentación de `seed.relational_dsl` y añade
relaciones espaciales y papeles independientes del color absoluto.
`programs.py` valida un lenguaje cerrado y expande subprogramas acotados.
`concepts.py` guarda programas comprobados sobre demostraciones, procedencia
y contraejemplos. Una demostración satisfecha no certifica su salida de test.
`solver.py` busca con esas representaciones, vuelve a comprobar cada recuerdo
y se abstiene ante hipótesis válidas con predicciones incompatibles.

`robotics.py` conecta la línea anterior de percepción/control WSP con una
interfaz explícita de observaciones y acciones. El simulador y sus secretos
permanecen fuera del actor. Los ensayos discretos no se anuncian como vuelos
PX4/Gazebo nuevos; el informe distingue disponibilidad y ejecución reales.

`interaction.py` mantiene hipótesis sobre consecuencias de acciones, selecciona
intervenciones discriminantes y planifica desde metas sobre transiciones
observadas. Los controles reciben las mismas observaciones y acciones.
`adversarial.py` selecciona contraejemplos válidos con testigo comprobado por
el evaluador; no entrega el testigo al solver. `evaluation.py` y el auditor
recalculan resultados sin confiar en los indicadores que devuelva el actor.

## Interfaces y límites

- `Budget(limit)` expone `consume(kind, amount=1)`, `add`, `used`, `counts`;
  el desbordamiento lanza `BudgetExceeded` antes de hacer el trabajo.
- `legacy.module(name)` importa módulos históricos bajo una identidad
  canónica. No ejecuta campañas, modelos ni pruebas durante la importación.
- `solve(task, *, budget, library=None, relational=True, hierarchical=True,
  learn=False, journal=None)` recibe demostraciones y consultas sin etiquetas;
  devuelve `status`, `predictions`, `program`, `metrics`, `test_verified=False`.
- Los conceptos se serializan como JSON con versiones y hashes. Recuerdos
  no comprobados, ciclos de expansión, desbordamientos y conflictos fallan
  de forma explícita. El identificador de tarea no es una feature.
- El neocórtex es opcional y apagado en este primer banco. No se entrenan
  pesos, no se descargan modelos y no se gastan créditos de nube.
- Python 3.12.13 y biblioteca estándar. Dependencias pesadas solo en los
  adaptadores históricos que las requieran; nunca necesarias para el núcleo.

## Secuencia verificable

1. Adaptadores, presupuestos y trazas; pruebas de identidad y límites.
2. Objetos, programas y conceptos; pruebas de colores/posiciones nuevas,
   composición, ambigüedad, persistencia y etiquetas inaccesibles.
3. Integración robótica y aprendizaje interactivo; pruebas de consecuencias,
   cambio de dinámica, planificación, veto y observaciones caducadas.
4. Evaluación por módulos, tres brazos de currículo y auditoría independiente.
5. CLI reproducible, documentación de resultados y comprobación de que los
   archivos históricos conservaron sus hashes.

## Contrato del primer banco

El banco es sintético y de desarrollo, no una puntuación oficial ARC ni un
examen sellado de S6. Antes de ejecutar la confirmación se congelarán hashes
de fuentes, configuración, semillas y estado aprendido. La evaluación no
realimenta aprendizaje. No se ajustan los umbrales después de ver resultados.

Se comparan representación anterior/nueva, biblioteca vacía/adquirida,
búsqueda plana/jerárquica e interacción pasiva/activa. El ensayo adversarial
compara referencia, desafíos aleatorios y desafíos adaptativos con el mismo
límite total; generación, simulación, descartes y evaluación cuestan trabajo.
Cada brazo tiene su propia memoria. Se publican denominadores, aciertos
exactos, desacuerdos, regresiones por caso, costes reales y límites agotados.

Una implementación correcta requiere que pase la suite, no filtre respuestas
reservadas ni permita que una propuesta modifique el juez. Una ventaja exige
aciertos nuevos sin regresiones o igual acierto con menor coste total,
incluyendo adquisición; se informa su magnitud y su incertidumbre. Un empate
es un empate. Los informes separan funcionamiento, mejora medida, transferencia
dentro del generador y generalización aún no acreditada.

Riesgos que las pruebas deben cubrir: importar dos veces el mismo estado,
confundir empate de roles con un objeto único, aceptar recuerdos corruptos,
contar operaciones fallidas como gratuitas, filtrar las etiquetas de consulta,
premiar mundos imposibles y utilizar resultados del padre como evidencia de
un descendiente. La reparación es acotada al lenguaje; no hay ejecución de
código propuesto ni escritura del verificador por el actor.

Calibración previa a confirmación: el caso sintético de desarrollo
`make_case(13, 'extract_rotate', split='development')` agotó 2.000.000 unidades
tras 3.325 candidatos, antes de cerrar la búsqueda. El contrato fija ahora
8.000.000 por tarea en todos los brazos de rejillas para cubrir la composición
y las entradas mayores; se conserva el agotamiento como resultado si ocurre.
Esta modificación se hizo antes de ejecutar las semillas de adquisición o
confirmación del contrato. No altera programas, jueces ni resultados previos.
