# Referencia semántica independiente de misiones

Remediación de desarrollo del 11 de octubre de 2026. Módulo:
`src/echo5/mission_reference.py`; pruebas: `tests/test_mission_reference.py`.
No modifica la campaña r3 ni sus contratos, resultados o criterios de cierre.

## Qué comprueba

El evaluador personalizado de `sandbox_eval.py` construye instrucciones BabyAI
desde `parse_mission`, que también usa el actor. Un error compartido puede
producir un replay coherente y una interpretación incorrecta. Este banco
contrasta esa ruta con significados escritos explícitamente como datos.

`reference_cases()` contiene textos/entradas estructuradas, descriptores,
orden de ejecución, posiciones iniciales, conjuntos esperados de referentes
y trayectorias con resultado esperado. Sus helpers sólo construyen registros:
no llaman al parser, a su renderer ni al constructor de instrucciones de
producción para generar respuestas esperadas. Cada llamada devuelve datos
separados; tampoco se comparten objetos mutables entre entrada y significado.

El constructor de referencia convierte esos descriptores en `ObjDesc` e
instrucciones nativas. Para `after` usa `AfterInstr` directamente; para `then`,
`BeforeInstr`; para `and`, `AndInstr`. La otra rama usa el parser de producción
y `sandbox_eval._native_instruction`. Ambas ejecutan las mismas acciones en
instancias nuevas de `RoomGridLevel`, con objetos colocados a mano y sin
muestreo de misiones. La implementación nativa de `step` y su verificador
deciden éxito mediante terminación y recompensa positiva. No hay simulador
sustituto ni flags de finalización del actor.

Corpus fijo actual:

| Comprobación | Cobertura |
|---|---|
| Significados aceptados por el parser | 32 casos, incluidos tres rechazados al resolver referentes en el mundo |
| Sintaxis rechazada | 20 casos: pronombres, referencia «other», conectores mezclados, más de dos pasos, ubicaciones/colores no admitidos, verbos incompatibles y estructuras inválidas |
| Trayectorias nativas emparejadas | 94: 41 positivas y 53 negativas; una ejecución por rama |
| Rechazos nativos emparejados | 3: referente ausente, solapamiento de papeles en `putnext`, objetos ya adyacentes |
| Pasos nativos del corpus sin mutaciones | 288 por rama, 576 en total |
| Orden | `after`, `then` con/sin coma, `and`, primer paso incompleto y recuperación del orden |
| Localización | izquierda, derecha, delante, detrás; cuatro orientaciones iniciales y giros antes de recoger |
| Referentes | tipo, seis colores, color omitido, tipo `object` y varios referentes válidos |
| Relaciones | papeles móvil/fijo de `putnext`, tipo incorrecto, referencia incorrecta, diagonal, ausencia de depósito y localización de ambos papeles |
| Entradas alternativas | espacios/mayúsculas/punto final, `{"text": ...}`, secuencia/conjunción/`putnext` estructurados |

La ambigüedad de objetos no exige unicidad: BabyAI acepta cualquier miembro
del conjunto que satisface la descripción. Los IDs esperados y observados
quedan en el informe. Una referencia pronominal no soportada sí se rechaza.

La localización se fija respecto de la posición y orientación iniciales.
`BeforeInstr` y `AfterInstr` se usan sin `strict`: realizar el segundo paso
demasiado pronto no completa la misión, pero puede recuperarse realizando
después la secuencia correcta. «Negativa» significa que ese prefijo finito
no obtiene éxito; no significa rechazo terminal ni imposibilidad futura.
La adyacencia de `putnext` es ortogonal y requiere mover el objeto indicado;
mover el referente hasta una configuración geométricamente similar no basta.

## API, validez y replay

```python
from echo5.mission_reference import run_benchmark

report = run_benchmark()              # dependencias nativas requeridas
subset = run_benchmark(native=False)  # sólo parser, válido como subconjunto
```

El retorno es JSON serializable, sin tiempos, fechas, PID, rutas absolutas
ni identificadores de memoria en la evidencia normal. Las posiciones y
acciones son datos fijos. No escribe archivos ni lanza procesos, actores,
campañas, modelos o visores. Las importaciones opcionales son diferidas;
el módulo y el subconjunto del parser funcionan en `.venv` de stdlib.

- `instrument_valid`: se ejecutó toda la referencia prevista; sus resultados,
  conjuntos de referentes y rechazos coincidieron con los datos explícitos.
  Es falso si faltan dependencias, cambia `BABYAI_DONE_ACTIONS`, el corpus está
  vacío/incompleto, hay errores del motor o falla un testigo de referencia.
- `semantic_pass`: requiere `instrument_valid`, aceptación/rechazo correcto
  del parser, descriptores correctos y acuerdo del juez personalizado en todas
  las trayectorias y referentes. Un error semántico conserva un instrumento
  válido y produce `semantic_pass: false`.
- `valid` y `passed`: aliases de los dos campos anteriores, respectivamente.
- `parser`: resultado del subconjunto. Cada fila conserva `status`, `observed`
  o `error_type`/`error`/`stage`. Una excepción inesperada del parser se registra
  como error del candidato; no se convierte en rechazo correcto ni invalida
  por sí sola una referencia nativa que se ejecutó correctamente.
- `counters`: casos y errores de parseo, rechazos fallidos, trayectorias por
  signo, discrepancias, falsos éxitos/negativos, errores de referencia,
  errores del instrumento y pasos efectivamente ejecutados por rama.
- `coverage`: cantidades previstas y gramática cubierta, incluso si no pudo
  ejecutarse el entorno nativo. `native_trajectories` cuenta pares con referencia
  ejecutada; una rama candidata ausente queda explícitamente como `null`.
- `cases`: mundo inicial, significado esperado, binding nativo, acciones,
  estados reales, recompensas, terminación y resultados por trayectoria.
  Los rechazos semánticos del mundo se separan de los rechazos sintácticos.
- `corpus_sha256`, `source_sha256` y `native.versions`: identidad del corpus,
  fuentes relevantes y paquetes nativos. Un hash acredita identidad, no éxito.

`native=False` o dependencias ausentes dejan **ambos campos globales falsos**,
aunque pase el parser. No hay pase global por omitir pruebas opcionales.
El estado `native.status` distingue `not_requested`, `unavailable`, `complete`
e `invalid`. `complete` puede acompañar un resultado semántico negativo.

Dos procesos nuevos con las mismas fuentes y dependencias producen el mismo
informe completo, comprobado mediante igualdad exacta de JSON ordenado. No se
necesita eliminar tiempos para el replay. El runner padre puede llamar a
`run_benchmark()` desde `.venv-sandbox/bin/python -I scripts/remediation.py`
en procesos separados para medir y auditar, conservando su propia custodia
de resultados, fuentes congeladas y recibos de lanzamiento. No usar sólo el
hash del informe como auditoría: volver a ejecutar y comparar el contenido.
Esta tarea no registra el módulo en contratos, runners o campañas compartidos.

## Ejecución acotada

Desde `ECHO-5`, imprimir el informe nativo en stdout:

```sh
.venv-sandbox/bin/python -I -B src/echo5/mission_reference.py
```

La CLI devuelve 0 si pasa, 1 si la medición es válida y falla la semántica,
o 2 si la medición completa no es válida. El modo siguiente imprime el
subconjunto y devuelve 2 deliberadamente:

```sh
.venv/bin/python -I -B src/echo5/mission_reference.py --parser-only
```

Pruebas y comprobación de sintaxis:

```sh
.venv/bin/python -I -B tests/test_mission_reference.py
.venv-sandbox/bin/python -I -B tests/test_mission_reference.py
make check
```

Verificación de esta entrega: 17 pruebas pasan en `.venv-sandbox`; 6 pasan y
11 nativas se omiten explícitamente en `.venv`. También pasan 14 regresiones
existentes: cuatro de gramática en `MissionContractTests` y las diez de
`ObservationActorTests`. `make check` pasa. El corpus sin mutaciones devuelve
`instrument_valid: true`, `semantic_pass: true`, cero discrepancias y cero
falsos éxitos. La primera ejecución de las pruebas falló por ausencia del
módulo, antes de implementar el banco.

Las pruebas adversariales inyectan el mismo error en los dos consumidores
del parser: invertir `after`, convertir `and` en secuencia, cambiar izquierda
por derecha y permutar los papeles de `putnext`. Todas producen una medición
válida con fallo semántico; los significados y resultados de referencia se
conservan. Otra mutación altera sólo el constructor del juez. Los controles
del instrumento corrompen la referencia, simulan ausencia de dependencias,
corpus vacío y errores del motor; ninguno obtiene validez/pase ficticios.
Una excepción del parser queda como evidencia de fallo semántico. La prueba
de importación bloquea cualquier import de MiniGrid/Gymnasium/NumPy/Pygame.

## Límites e integración pendiente

Es una referencia finita de desarrollo, no una garantía universal de lenguaje
ni una medida de capacidad de la política. Los dos brazos comparten el motor
y verificador de BabyAI; la independencia corresponde a los significados,
fixtures y testigos frente al parser y constructor de producción. Los helpers
de referencia también pueden tener errores; los testigos y mutaciones reducen
ese riesgo sin demostrar ausencia universal de fallos.

No cubre alias `reach` de MiniGrid, el cableado completo de overrides en
`ExternalEnvironment`, varias habitaciones, objetos ocultos, exploración,
misiones generadas al azar o todas las combinaciones posibles de dos verbos.
No se ha ejecutado la suite general ni se han abierto tareas selladas o
artefactos de la campaña. El padre puede añadir una puerta independiente en
un protocolo nuevo usando `instrument_valid` y `semantic_pass` por separado;
no debe convertir el resultado de este corpus en un pase retroactivo de r3.
