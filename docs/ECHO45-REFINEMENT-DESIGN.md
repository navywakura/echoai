# Refinamiento y síntesis de programas: primera extensión

2026-09-28. Propuesta de Roger, incorporada como desarrollo independiente
de S6. Código aditivo `seed/refinement.py`; el solver histórico se conserva.

**Implementado:** varias hipótesis DSL; crítica de forma, celdas, colores y
número de objetos; refinamiento mediante añadir, sustituir o quitar operaciones;
ocho vistas geométricas intercaladas; ejecución simbólica exacta sobre todas
las demostraciones; hasta dos grupos de respuestas, con votación entre
programas canónicos distintos. Se eliminan rotaciones/reflejos equivalentes
para que repetir una vista no fabrique votos. Si programas válidos predicen
salidas diferentes, se publica `AMBIGUOUS`. `CONSISTENT` solo significa acuerdo
entre las hipótesis encontradas; nunca prueba que la salida reservada sea correcta.

Cuatro operaciones de relaciones entre objetos: ordenar objetos por tamaño
en una fila, usar el color de un marcador único para otros objetos, recolorear
los objetos mayores/menores y conectar marcas del mismo color en filas/columnas.
Son herramientas diseñadas por el implementador, no abstracciones aprendidas.
La biblioteca anterior de rotación, simetría, gravedad, recorte y conceptos
verificados se importa. No hay interpretación general de símbolos demostrada.

**Búsqueda acotada:** un límite global de programas, compartido entre vistas.
Sin parada dependiente del tiempo, sin Python del modelo, sin tocar pesos o
prioridades persistentes y sin LLM en NEXUS-0. Una propuesta externa debe ser
un programa del DSL cerrado y superar el mismo verificador. El diario ARC
existente puede guardar programas, errores y veredictos realmente calculados;
no se inventan pensamientos ni se crea otro bus.

**Desarrollo preregistrado:** doce tareas del split histórico de entrenamiento
ARC-2, seleccionadas por hash, sin leer evaluación. Cuatro ablaciones: una
pasada, refinamiento, varias vistas y relaciones nuevas. Límite común de
2000 programas, profundidad 4, beam 12, hasta 32 hipótesis; se publica consumo
real, que puede diferir entre brazos. Verificación independiente de todas las
demostraciones de los programas emitidos. Solo el juez, después de resolver,
recibe las respuestas de test de estas tareas de desarrollo. No es un examen
reservado y no obtiene un VERDE científico.

**Pendiente:** composición jerárquica con variables y relaciones, adquisición
de abstracciones nuevas con pocos ejemplos, transferencia con el modelo
apagado, experimentación interactiva y entrenamiento durante la prueba.
Este último requiere actualizaciones reales de parámetros y otro contrato;
explorar miles de programas se llama búsqueda con más cómputo.

El examen futuro comparará la base, el nuevo solver y ablaciones bajo un
presupuesto declarado, en una cohorte todavía no abierta. VERDE solo si
mejora las respuestas exactas, conserva la capacidad previa y pasa custodia
y replay según umbrales fijados antes. No se promete resolver ARC-2 ni el 100 %.

Fundamento: [Self-Refine](https://arxiv.org/abs/2303.17651),
[entrenamiento durante la prueba](https://arxiv.org/abs/2411.07279),
[informe oficial ARC-2](https://arcprize.org/blog/arc-agi-2-technical-report).

Actualización de contexto verificada el 28 sep: Astra tiene 95 % en ARC-2 a
esfuerzo Max y 99,95 % en ARC-3 con Provider Adapter a esfuerzo High, frente
a 62,71 % con arnés Standard a esfuerzo Max. Son resultados distintos con
configuraciones y costes distintos; no establecen un 100 % generalizable.
Por tanto, «nadie supera 99 % en ninguna versión» no es una premisa válida.
[Fuente oficial](https://arcprize.org/results/openai-gpt-6-astra).
