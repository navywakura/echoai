# E · reparación acotada del agotamiento de búsqueda

22/10/2026. Sigue a SHIELD-2, por encargo de Nav. Desarrollo nuevo con
protocolo fijado antes de generar tareas; resultados históricos12/18 y sus
seis agotamientos se conservan. No se vuelve a jugar la campaña histórica.

## Hipótesis y mecanismo mínimo

La búsqueda agota trabajo antes de cerrar el nivel retenido. Se prueba si
retener ocho prefijos en vez de24 permite llegar/cerrar niveles útiles bajo
el mismo presupuesto, a costa de una frontera menos amplia. No promete
resolver toda tarea ni es una nueva capacidad de aprendizaje.

Se reutiliza `echo5.solver.solve` por su interfaz pública. Sin modificar el
motor, las fuentes congeladas ni sus contadores. Nueva orquestación en
`echo58/searchrepair`, import explícito del ECHO-5 local. Sin LLM, propuestas,
testigos entregados al actor, biblioteca adquirida ni respuestas de consulta.

## Contraste fijo

Cuatro brazos: beam24 (referencia), beam8 (reparación propuesta), beam4 y
beam48 (controles que pueden ganar). Todos:326átomos del DSL completo,
profundidad4,12000candidatos,2.000.000unidades de trabajo, estrategia certified
con ranking_bound, caché interned, misma semántica de cierre y consenso.
Una frontera más estrecha no se vende como búsqueda exhaustiva.

Generador independiente existente, ocho familias: sus seis soportadas y
ambiguous_reflection/unsupported_new_color como controles. Cuatro casos por
familia:32tareas,128solves. Semillas mediante `_seed(37_000_000,
'independent',familia,índice,ledger)` del generador original. Congelar agenda
y hashes de tareas antes de resolver, sin examinar soluciones para ordenar.
Ledger de preparación inicial: `Budget(20_000_000)`, usado0 y counts vacío.
Se guardan snapshots inicial/final, sus hashes y mapa familia/índice/semilla.

Solo el evaluador genera y conserva expected/category/witness. El actor
recibe exclusivamente public_task con demostraciones y entradas de consulta.
Cada brazo recibe el mismo hash público. No selección por nombre de familia,
semilla, testigo, forma de la respuesta ni éxito previo. Aprendizaje apagado.

## Medidas y puerta

Exactitud externa, respuestas erróneas, falsas afirmaciones, abstenciones,
trabajo total/desglosado, candidatos, profundidad, cierre de nivel y poda;
tiempo CPU/pared descriptivo, coste de generación/evaluación separado.
Diario con observaciones, fronteras y resultados reales, nunca monólogo.

Utilidad de desarrollo de beam8 frente a24: más exactos totales, no menos
exactos en ninguna familia soportada, al menos una mejora en alguna de las
dos familias de los agotamientos históricos, cero wrong/false_commitments
en todos los casos y trabajo total no mayor. Los controles4/48 se reportan;
si alguno gana, no se cambia retrospectivamente el brazo principal.
Las dos familias objetivo fijadas son `inside_erase_crop` y
`right_erase_crop_rotate`.

No se relaja consenso ni se acepta el primer programa compatible al agotar
presupuesto. `test_verified` sigueFalse; juez externo verifica respuestas.
El auditor comprueba agenda/identidad, contabilidad, programas/predicciones
y puntuación externa con ejecución de programas, sin repetir la búsqueda.
Se declara que ese audit no es un replay del razonador completo.

## Entrega

Contrato, fuentes/dependencias y casos congelados; resultados/diarios por
condición exclusivos, auditoría e informe incluso si sale rojo. Sin cambiar
límites para buscar verde; toda continuación distinta exige versión prospectiva.
No examen, HF, nueva campaña ARC ni edición de SHIELD-1/W/C v1/CRECE.
`budget_exhausted` y `search_exhausted` son abstenciones válidas del actor;
excepciones, instrumentos incompletos o condiciones ausentes dejan la puerta
inconclusa. Se conservan recibos y no hay reintentos automáticos.
