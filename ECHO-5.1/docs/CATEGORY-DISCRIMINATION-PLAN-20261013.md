# Discriminación de categorías · piloto de desarrollo 0.7

Objetivo: medir si priorizar riesgos del código mejora frente a una secuencia
fija con el mismo catálogo, no construir un control destinado a perder. El
3/3 frente a 2/3 anterior es una observación favorable, no confirmación de H1.
E y F empataron: ese resultado permanece inalterado.

## Diseño fijado antes de inferencia

- `repair-v2`, doce variantes, semilla 47: dos de cada familia Intervalos,
  Registros, Rutas, CSV, Paginación y Dependencias; S/I2/F/E, 48 episodios.
- Las seis familias ya son conocidas. Las variantes cambian valores, no
  constituyen familias independientes ni un examen nuevo de generalización.
- `expanded-v1`: tres categorías anteriores más dos válidas por familia.
  Las nuevas no se declaran universalmente inocuas: podrían detectar otros
  defectos. Entradas fuera de dominio nunca cuentan como sondeos válidos.
- F: orden por SHA-256 de `[20261013, task_id, category]` con JSON compacto.
  Semilla elegida aquí antes de inspeccionar órdenes o resultados. No se busca
  un orden favorable a E. Orden completo archivado en cada definición de tarea.
- E: las mismas categorías y orden de respaldo; prioriza una señal AST
  explícita si existe, y omite categorías registradas en su memoria del episodio.
  Es una política escrita por humanos, no aprendizaje automático del router.
- Corrección previa al lanzamiento: E recupera observaciones y rechazos en una
  sola consulta CAM contabilizada. Antes olvidaba las categorías cuyos tres
  intentos fallaban y podía repetirlas; una prueba del episodio completo lo
  reproduce. La auditoría ampliada comprueba etiquetas, evidencia, orden y
  reintentos. Este cambio adicional tampoco quedará aislado de los demás en la comparación.
- Conserva la parada tras dos categorías soportadas, cuotas y política de
  reparación. Esto limita la búsqueda de errores en ambos brazos; se reportará
  como una condición del experimento, no como verificación exhaustiva.
- 25.000 tokens, 50 herramientas, 12 llamadas LLM, seis críticas, 128 fuel,
  300 s CPU y 900 s de plazo por episodio. Máximo dos reparaciones guardadas.
- Mismo 14B Q4_K_M fijado, llama.cpp b11577, contexto 4096, salida máxima768,
  temperatura0,2 y política compartida de semillas. Misma imagen Python local,
  Bubblewrap/cgroups y oráculos. Orden de brazos contrabalanceado existente.
- Kaggle privado, solo inferencia; ejecución de candidatos y oráculos locales.
  Una campaña, sin reintentos automáticos. Worker con techo total de90min,
  servicio activo de80min tras carga; supervisor y túnel con límites mayores
  solo para terminar y guardar recibos. No es una previsión de duración.

## Categorías añadidas

| Familia | Categorías |
|---|---|
| Intervalos | Intervalos disjuntos; extremos del rango permitido |
| Registros | Claves únicas; valores extremos permitidos |
| Rutas | Componentes ordinarios; raíz sola |
| CSV | Campo único; campos vacíos |
| Paginación | Ventana dentro de la lista; elementos extremos permitidos |
| Dependencias | Cadena dirigida; grafo sin aristas |

Los validadores de etiqueta y dominio son externos al modelo. El router solo
lee código candidato y evidencia previa; no recibe casos finales ni aciertos
del oráculo reservado. Las señales AST no prueban que exista un defecto.

## Lectura de resultados y criterios

Se publicarán localmente todos los episodios, incluso errores y presupuestos
agotados: aceptación final común, casos comunes por familia, contraejemplos,
reparaciones, categorías solicitadas/soportadas, duplicados, tokens observados
y cobrados sin uso conocido, trabajo, tiempo y coste de memoria. Se distinguirán
fallos públicos de descubrimientos del crítico.

Contrastes descriptivos E−S y E−F emparejados sobre las mismas tareas; también
I2 y F completos. Informar victorias/empates/derrotas y coste, sin seleccionar
familias después. Dos variantes correlacionadas no equivalen a doce familias
independientes. No se prometerá significación ni cierre por un marcador alto.

E/F aún difieren en memoria y política de coordinación además del orden; esta
tanda no aísla causalmente CAM ni el router por sí solo. Harán falta ablaciones
y repetición de órdenes/semillas para atribuir una diferencia. El nuevo catálogo
y AST cambian conjuntamente: tampoco se atribuirá la diferencia respecto al
piloto0.6 a un único cambio.

Puerta de lanzamiento: suite PCWorld completa verde, revisión de validadores y
controles, hashes de código/contrato/plan congelados y notebook privado verificado.
Puerta de ejecución válida:48 episodios conservados, auditoría de recibos válida,
sin cambios de fuentes; errores del modelo se conservan como resultados. Si se
agota el techo de campaña, se publica parcial y no se descartan episodios.

No se hace push ni se publica el notebook. S6 permanece aplazado. El resultado,
positivo o negativo, se añade al checklist sin reescribir pilotos anteriores.
