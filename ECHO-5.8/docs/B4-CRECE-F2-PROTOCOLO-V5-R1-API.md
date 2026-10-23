# CRECE F2 v5 r1 · descripción completa de la API existente

21/10/2026. Revisión previa a datos nuevos, sobre el piloto acotado
[v5](B4-CRECE-F2-PROTOCOLO-V5-INTERFACE120B.md). Su arranque r0 se conserva
interrumpido: cuatro candidaturas y cinco recibos, fuentes exactas y
`interrupted.json`. No tiene resultado científico ni examen. V4 sigue roja.

La revisión completa de `runtime.py`, `language.py` y F0-SPEC identifica
omisiones de documentación al LLM. Se corrige **la descripción**, manteniendo
runtime, lenguaje, efectos, límites, ejemplos y puerta empírica idénticos.

| Enganche | Campos de contexto que se suministran | Efectos admitidos |
|---|---|---|
| DECIDE | intent, drop_for; los otros tienen valores por defecto | BAN, NOTE |
| OUTCOME | intent, out, dropped_here anterior a la acción; los otros por defecto | BAN_UNTIL_PROGRESS, NOTE |
| DROP | solo avoid; intent está vacío | DROP_AT, GOTO, NOTE |
| IDLE | todos por defecto; intent está vacío | GOTO, NOTE |

Valores por defecto: intent/dropped_here/avoid `()`, drop_for `0`, out
`UNKNOWN`. DROP e IDLE solo se invocan en modo no absoluto. La vista OUTCOME
mantiene posición/mano/rejilla anteriores a la acción y contadores posteriores.
OUTCOME solo se invoca para intenciones no vacías distintas de DROP_ACTION:
no existe un resultado de ese enganche después de soltar ni de una acción
primitiva sin intención. Las observaciones de las fichas son posteriores a
la acción; no se confunden con la vista anterior usada por OUTCOME.

Se explicitan todas las condiciones del validador: los dos vetos admiten
solo ENTER/PICK/TOGGLE, nunca DROP_ACTION; id entero presente en la rejilla,
HAND con mano no vacía, NOTE suma uno y HAND también exige mano no vacía,
coordenadas tuplas de dos enteros con las restricciones ya descritas,
efectos como tupla de longitud 0…2 (máximo una acción y una nota). No hay
relajación de una comprobación porque una propuesta haya fallado.
BAN/ANY dura el episodio; BAN/HAND sigue asociado al identificador sostenido
y vuelve a aplicar si se recupera; BAN_UNTIL_PROGRESS dura mientras no cambie
el progreso registrado. NOTE pertenece a cada pieza, admite EPISODE/HAND y
sus contadores se reinician por episodio.

Se describen los valores de View: belief devuelve una consecuencia; picked,
opened, visits y note son contadores; progress suma en la primera recogida
de cada identificador y en cada OPEN. reach incluye la celda inicial y
blocked es una sola celda; ids_near reúne vecinos de toda la región alcanzable.

La serialización usa símbolos públicos en ambos dominios: intención histórica
DROP → DROP_ACTION, resultado histórico PICK → PICKED y falta de clasificación
→ UNKNOWN; una intención ausente se presenta como tupla vacía. Se explica que
los símbolos de acción y resultado pertenecen a dominios distintos. La traza
original y su hash no se alteran. No se convierte una observación en una
instrucción sobre qué estrategia debe inventar el modelo.

También se aclaran las particularidades del intérprete existente: listas y
generadores se materializan como tuplas, sin mutaciones; tuple/frozenset
requieren una colección (usar `()` para vacía), lambdas solo como key directa
de min/max/sorted. No se añade una pieza ni se modifica código del LLM.
Todos los identificadores tienen como máximo 48 caracteres y no empiezan
por `_`; no se reasignan v/c/moment, constantes, efectos ni builtins. Se
enumeran las firmas de los builtins, incluido int con un argumento y el
start posicional de sum. El límite de colecciones cuenta también la raíz.

La revisión se contrastó con los cinco campos de Context, los cuatro sitios
de invocación y todas las ramas de `_validate`, además del intérprete. La
prueba de ficha cubre ambos dominios de nombres, intención ausente y hash de
traza original; las pruebas negativas y la equivalencia de F0 siguen vigentes.

Modelo y presupuesto de v5 sin cambios: `openai/gpt-oss-120b`, 2048/low,
30 propuestas, máximo 90 intentos HTTP, 60 s entre llamadas. Semillas nuevas:
**b=500000000** en las fórmulas de v1. Directorio
`lab/echo58/crece/f2-v5-r1-interface120b/`. Mismas familias, tamaños y controles;
misma puerta de dos mejoras consecutivas. Se conserva la regla de cierre del
piloto adicional de v5. No se inicia ninguna medida de examen.
