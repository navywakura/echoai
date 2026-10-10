# B23-R4 · recuperación de la interfaz del neocórtex

Condición nueva, 8 de octubre de 2026. El resultado R3 se conserva íntegro:
36/36 respuestas inválidas, sin finalistas. R4 se declara antes de inferir
con los modelos o medir partidas. S6 continúa abierto.

R3 presentaba una lista de valores HOLD como si fuera una respuesta y describía
`when` con texto. El CLI generaba texto libre; la comprobación previa solo
tokenizaba ChatML. Eliminar Markdown no convierte ninguna de las 36 respuestas
en una propuesta legal. Este fallo impide atribuir el resultado a la capacidad
de razonamiento de 7B o 14B.

R4 separa las opciones permitidas de un ejemplo ejecutable sin resultados de
juego. Una gramática GBNF limita la salida a un parche HOLD, un entero del
conjunto ya permitido y una a tres condiciones legales distintas. Las claves
se serializan en orden alfabético: el lenguaje de políticas conserva todas sus
combinaciones. El decodificador garantiza estructura; el verificador original
sigue comprobando la propuesta. No se reparan condiciones ni valores después
de generarlos. El juez y los criterios de aceptación permanecen iguales.

Antes de cualquier partida se exigen cuatro pruebas sintéticas de formato por
modelo: copiar una propuesta de una condición, construir dos condiciones,
construir tres y corregir un valor expresado erróneamente como lista. Son ocho
llamadas reales al mismo CLI, pesos, gramática y límites que el experimento.
No contienen observaciones de partidas, reglas ganadoras ni resultados de
PROBE. Se conserva solicitud, salida, comando, tokens y hashes. Cada respuesta
debe coincidir con la solución de formato prerregistrada. Un fallo detiene R4;
no se consume la campaña como 36 intentos científicos inválidos. La prueba no
entrena ni modifica los pesos y su historial no pasa al investigador.

El micro repite solo N14 y N7, en ese orden, con la semilla 823101, 18 plazas
por brazo, la misma base de 61 niveles en 14 partidas, contexto de 9216,
8192 tokens de entrada y 768 de salida. Mantiene Qwen2.5-Coder-Instruct Q4_K_M
7B/14B, revisiones y llama.cpp de R3, dos T4 y cuatro procesos de simulación.
Las propuestas repetidas consumen plaza. Un error de transporte o una salida
inválida bajo la gramática detiene el instrumento; se preserva la llamada.
No hay reintentos automáticos ni sustitución del modelo.

Los tres controles sin LLM ya medidos y auditados en R3 se conservan como
referencia histórica. No se repiten sus 2268 partidas. Esta recuperación de
una semilla es diagnóstica; no demuestra superioridad estadística de un modelo
ni equivale a una réplica contemporánea de cinco brazos.

Presupuesto máximo: 1596 partidas del micro (798 por brazo), 1440 de desarrollo
amplio (base y hasta dos candidatos, 160 casos, ejecución/replay/auditoría),
720 de retención (base y hasta dos candidatos, 80 casos, triple). Total 3756.
Hasta 36 llamadas científicas más ocho de formato: 44, con libros separados.
Todas las llamadas y partidas se reservan antes de ejecutarse; un trabajo
interrumpido exige recuperación explícita. El preflight no juega partidas.

Cada candidato necesita ≥2 niveles adicionales y cero pérdidas individuales
de nivel o score. Se detiene cada brazo al primer éxito del micro. Solo
entonces se valida ampliamente; solo si supera desarrollo amplio se abre
retención para la política exacta congelada. R3 no abrió esos 80 casos.
La retención no alimenta el prompt ni selecciona nuevas propuestas. Replay y
auditoría independiente deben coincidir exactamente. Una discrepancia es un
fallo del instrumento y nunca un resultado científico negativo.

Los módulos R4, contrato, tests y recibo del cierre R3 se congelan por hash junto
con los bytes originales reutilizados. El investigador recibe únicamente base,
política e historial propio. El contrato y los recibos de custodia son del
arnés; no forman parte de los bytes enviados al modelo.

Se considera arreglada la interfaz cuando pasan las ocho inferencias de
formato y se ejecutan propuestas científicas válidas. Una mejora científica
necesita sus mediciones y auditorías posteriores. R4 no abre campaña ni examen
S6, no implica descubrimiento desde SEMILLA y no autoriza declarar S6 verde.
