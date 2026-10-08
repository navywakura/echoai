# CAPACITY-500K · comparación ARC-1 de desarrollo

30 septiembre 2026. Contrato previo a resultados de esta comparación.

**Hipótesis:** ampliar el banco disperso reduce colisiones de rasgos y mejora
la búsqueda de programas bajo el mismo presupuesto. Se exige mejora de
respuestas exactas; clasificar transformaciones sintéticas no acredita ARC.

Base común: estado `echo45-s2v`, tres conceptos y prior aprendido, DSL S2v,
solver `seed.learn.solve`, 400 expansiones, profundidad 4, una respuesta por
input de test, sin límite dependiente del tiempo y cero llamadas de modelo.
Los tres brazos son `base`, `guide640`, `guide500k`; solo las dos guías usan
el banco experimental, misma proyección y mismos programas de entrenamiento.
La guía modifica prioridad/coste mediante la interfaz existente `Library.guide`.
Los rasgos geométricos están diseñados manualmente; esta intervención no
equivale a descubrimiento autónomo de abstracciones.

Entrenamiento: los 60 programas ARC-1 ya verificados en el diario de S2v,
reproducidos de nuevo en todos sus ejemplos públicos. Los conceptos se
expanden para etiquetar las primitivas realmente ejecutadas. No se aprenden
de nuevo conceptos, ni se cambia prior, solver o DSL.

Desarrollo: las 250 tareas ARC-1 de **training** que pertenecen al pool de
entrenamiento del gimnasio y no a esos programas verificados. La elección
es exhaustiva por pertenencia al split, nunca por resultado. No se toca el
holdout del gimnasio ni la evaluación oficial. Los contributors de los
conceptos/prior se comprueban por procedencia antes de medir. El sandbox ya
pudo intentar tareas de este pool: es desarrollo conocido, no examen ciego.

El solver y la guía reciben únicamente demostraciones y inputs de test.
Solo el juez consulta outputs de test después de resolver. Los tres brazos
reciben los mismos datos. Se publica acierto exacto por tarea (todos sus
tests), ganancias, pérdidas, expansiones, aplicaciones DSL, pasos primitivos,
tiempo, memoria de pesos y número de unidades no cero. Contadores fuera del
actor y diario existente observable; ninguna traza se realimenta.

Se congelan fuentes, estado, programas, tareas y configuración antes de
ejecutar. Otro proceso reconstruye las guías y repite resultados completos
sin usar respuestas reservadas; se comparan decisiones/predicciones y
contadores deterministas. No se compara igualdad de tiempo de pared.

**Puerta de promoción de 500k:** más tareas exactas que base **y** guide640,
cero tareas perdidas respecto a base, presupuesto cumplido, procedencia,
verificación y replay completos. Una ventaja igual con 640 no justifica
ampliar a 500k. Resultado negativo permanece negativo; no se retocan rasgos
ni umbrales usando esta cohorte para llamarla después un examen nuevo.

S6-B11 conserva su contrato y fuentes. Cualquier integración futura del
banco en una condición S6 requerirá otro perfil; este ensayo ARC no puede
acreditar ni sustituir B1–B5.
