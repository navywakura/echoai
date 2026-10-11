# Síntesis con trabajo reutilizado y verificación prioritaria

La estrategia es opcional. La búsqueda histórica conserva su comportamiento por
defecto y los recibos anteriores requieren sus fuentes archivadas.

El [piloto final y sus cuatro auditorías](SEARCH-EFFICIENCY-RESULTS-20261012.md)
terminaron: la variante con cota logra 12/18 independientes y 9/9 plantillas,
frente a 0/18 y 0/9 del control. Hay seis agotamientos pendientes.

```sh
.venv/bin/python -I scripts/run.py solve tarea.json --budget 2000000 \
  --synthesis-strategy certified --trace artifacts/mi-busqueda.jsonl
```

`--ranking-bound` activa adicionalmente la poda por pérdida parcial. En el
ensayo se compara explícitamente activada (`certified_bound`) y desactivada
(`certified`), con los mismos casos, alfabeto y presupuesto.

`baseline` usa la síntesis anterior. `memoized` añade análisis compartido de
rejillas, transiciones y pérdidas sobre rejillas exactamente iguales. `certified`
añade orden por firmas, poda de pérdida irreversible de colores y comprobación
prioritaria del resto del nivel, además de poda de enlaces imposibles y alias
demostrados antes de expandir. El nombre describe la comprobación del nivel
retenido, no una certificación universal de respuestas. Los tres usan el mismo
alfabeto público de 326 átomos, profundidad 4, beam 24 y límite de 12.000 candidatos.
El límite cuenta programas efectivamente expandidos: en `certified` se cuentan
por separado todas las consultas a operadores previas a la expansión, incluidos
los descartados. Sus costes sí consumen el mismo presupuesto de 2.000.000.
No se comparan los contadores de expansiones como si fueran cantidades de
cómputo equivalentes entre estrategias; se publica también el trabajo total.

## Qué puede podarse y qué no

Construir una firma cuesta trabajo proporcional a los datos leídos; no es O(1).
Las dimensiones orientan el orden, conservando operaciones que cambien el tamaño
intermedio. Que entrada y salida midan lo mismo no permite eliminar escalados:
`down2; up2` es un contraejemplo implementado en las pruebas.

La poda irreversible se apoya en una propiedad del DSL actual: cada primitiva
expandida utiliza únicamente colores presentes en su entrada. Si un estado ya
perdió un color exigido por una demostración, ninguna continuación puede producir
esa demostración. Una futura primitiva que introduzca colores invalidaría esta
propiedad y deberá desactivar o ampliar la regla; no se extiende a otros lenguajes.

Por cada prefijo se resuelven los papeles y relaciones de los 326 operadores en
los estados públicos actuales. Si una primitiva resulta indefinida en una
demostración, no se construye ese hijo. Dos primitivas sólo comparten un
representante si coinciden fuente, destinos y efecto en **todas las demostraciones
y todas las entradas de consulta**. Coincidir sólo en entrenamiento no basta.
Los fragmentos de varios pasos conservan su tratamiento anterior. Se cobra esta
resolución de enlaces; no es un filtro gratuito ni una selección por el generador.

La poda por pérdida parcial mantiene una cota a partir de una frontera ya llena
de estados distintos y completamente evaluados, incluidas sus consultas. La
pérdida sobre demostraciones es una suma no negativa: una rama que ya supera
al peor de esos estados no puede entrar en la frontera ni ajustar los ejemplos.
Las dimensiones conocidas aportan otra cota inferior antes de ejecutar una
operación. Se incluyen longitud y orden en los desempates. Nunca se descarta
por esta regla una rama que todavía podría lograr pérdida cero; todas ellas
continúan participando en el consenso. Las pruebas contrastan las fronteras
retenidas con la poda activada y desactivada.

## Cuándo se acepta

Al encontrar el primer ajuste completo se registra un ticket y el presupuesto
restante se dedica a verificar las alternativas pendientes de **todo el nivel
retenido**. Se rechaza una alternativa al primer contraejemplo; no se calcula su
ranking ni se ejecuta en consultas si ya contradice una demostración. Las
dimensiones conocidas pueden rechazar un ajuste final, nunca una continuación
intermedia necesaria. Al alcanzar la profundidad máxima también se evitan
rankings de prefijos que ya no podrán expandirse.

Sólo se acepta tras cerrar el nivel. Desacuerdo entre consultas o una ejecución
indefinida impiden aceptar; un límite de trabajo o candidatos deja abstención.
`test_verified` continúa siendo falso: el juez externo compara las respuestas.
No se usa una mayoría de candidatos ni se promete reservar un porcentaje fijo
suficiente para cualquier tarea.

## Memoria y coste

Las cachés viven dentro de una resolución, tienen límites y cobran las claves,
lecturas, escrituras y resultados retenidos. La identidad de rejilla se comparte
tras igualdad completa, nunca por coincidencia de hash. Las consultas aportan
sólo entradas públicas; el evaluador conserva respuestas y testigos.

El límite de celdas del caché de búsqueda se reparte entre éste y su análisis
anidado; con límite cero ambos operan sin retención. Guardar una referencia a
un resultado cuesta una escritura, como en el caché de prefijos del control:
no se cobra una copia de todas las celdas cuando tal copia no se ejecuta. El
hash y la comparación completa de rejillas sí se cobran por celdas; la retención
de memoria se contabiliza y limita por separado. Ningún ahorro se obtiene
dejando de cobrar una ejecución que realmente se haya realizado.

La comparación controlada está en `SEARCH-EFFICIENCY-PILOT.json`, ejecutada por
`scripts/efficiency.py`. Fuentes congeladas, casos por familia y auditoría en otro
proceso preceden a cualquier conclusión científica. Los casos de desarrollo ya
vistos se distinguen de semillas nuevas de los mismos generadores.
