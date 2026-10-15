# RepoWorld V6 — lectura completa y transiciones verificables

Continuación local tras V5 (`66c2bec`, informe `e7fa597`). V5 se conserva como
fallo funcional: búsqueda arreglada, dos parches aplicados, reversión a diff
vacío, crítico agotado; 208 recibos válidos y 21,62 h GPU restantes al apagar.

## Corrección derivada de V5

`source_evidence` añade una comprobación estructural a las vistas autenticadas.
Para Python con funciones, un locus está listo solo si las líneas de una
función que intersecta la vista están completamente observadas bajo el mismo
hash. Las vistas se unen por número de línea; un cambio de contenido invalida
la evidencia anterior. Los rangos AST solo orientan la lectura: no demuestran
que esa función cause el bug. Fuentes sin funciones conservan un locus de
líneas observadas; no se describe como función completa.

Una vista parcial obtiene `locus.next_view` con el rango que falta. `finish`
no entrega al editor ese locus parcial; `finish(abandon=true)` permite abandonar.
Tampoco se permite que el localizador eluda el bloqueo enviando directamente
una edición. Al alcanzar los límites sin un locus completo se abandona.

Un parche retenido pasa al crítico aunque el cambio de hash invalide las vistas
anteriores. Restaurar el código base devuelve el control al editor con
`base_restored=true`, sin afirmar que exista una solución. Los cursores inventados
siguen rechazándose; el feedback y el prompt indican `cursor=null` para lecturas
nuevas. No cambian cuotas, tests ocultos, selección de issues ni comparadores.
El umbral de 8.000 tokens del localizador se comprueba entre llamadas, como en
la revisión anterior; no se presenta como un techo estricto por generación.

## Evidencia offline y custodia

Raíz: `ECHO-5.1/artifacts/repoworld-gates-v6-20261015/`.
Cinco pruebas nuevas reproducen lectura parcial, edición prematura, traspaso
tras retención, reversión y cobertura ligada al hash. Una sexta cubre feedback
de cursores inválidos. Las seis fallan antes de las correcciones; 49 pruebas
focalizadas pasan después. El primer intento verde tuvo un error en el recibo
del fixture (no en el runner); se corrigió el fixture para usar la propiedad
pública que exige `Workspace.retain`.

Verify completo: **455 pruebas pasadas, 3 omitidas**, sin fallos en esta ejecución.
Smoke válido, rollback y replay idéntico; preflight 36/36 y controles oficiales
36/36 reatestados con la misma comprobación de hashes/procedencia que V5,
sin reejecutar sus suites originales. Frontera offline y `operate.py check`
válidos, cero GPU/LLM durante esta renovación. El smoke usa `smoke-actions.json`, con
un `finish` explícito tras observar la función; sigue siendo una transacción
sintética que provoca regresión y rollback sobre tests públicos reales, no una
solución de SymPy. V5 no se reutiliza como pase funcional de este código.

## Criterio para continuar

Una calibración nueva debe leer `_entry` completo, entregar presupuesto suficiente,
aplicar y retener una edición del método y superar los checks públicos registrados.
El assessment usa solo recibos y fuente pública; no consulta el oráculo reservado.
Los 22 checks de `test_basic.py` no constituyen cobertura de BlockMatrix ni prueban
la solución del issue. Cualquier resultado oficial requiere el harness separado.
Sin ese pase funcional no se sella el contrato ni se inicia la campaña.
