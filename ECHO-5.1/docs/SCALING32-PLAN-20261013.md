# Qwen 32B + biblioteca compartida · plan 0.10

Plan previo a inferencia. Desarrollo conocido, no confirmación independiente.
Se conserva el protocolo de propuesta/crítica/reparación y aceptación de 0.9.
No se presupone que un modelo mayor resuelva CSV o grafos, ni que E supere a F.

## Modelo y memoria GPU

Qwen/Qwen2.5-Coder-32B-Instruct-GGUF, revisión
`9d3053fce650fe1cdbdb75998c2a87add9d178ef`, Q4_K_M monolítico de
19.851.335.872 bytes. SHA256
`4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`.
Metadatos oficiales y `hf download --dry-run` comprobados antes del lanzamiento.

llama.cpp b11577, `CUDA0,CUDA1`, reparto `layer`, proporción `1,1`, `fit off`,
contexto 4096, un slot, cuatro hilos CPU. Exigir 65/65 capas GPU y buffers de
modelo >1 GiB en cada dispositivo. Las VRAM no son un único espacio automático.
Pesos, KV y buffers deben caber; si no, detener antes de inferir, sin fallback CPU.

Referencias primarias:
[Qwen GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF),
[llama-server b11577](https://github.com/ggml-org/llama.cpp/blob/b11577/tools/server/README.md).

## Matriz fijada

- Donantes: seis familias, variante03 del generador `repair-v2`, semilla47,
  brazo E sin biblioteca. Crear los 24 valores de variante para seleccionarlos.
- Publicar solo donantes aceptados tras reparación con refutación observada y
  auditoría válida. Mismo filtro de SharedConceptLibrary 0.9; sin sembrar defectos,
  reintentos selectivos ni reutilización de victorias históricas.
- Receptores: las 12 tareas anteriores, variantes00/01. Comprobar que son idénticas
  a `repair_task_variants(12,seed=47)` antes de lanzar. Nunca evaluar variante03
  como receptor. Solo varían valores del mismo contrato; no son familias nuevas.
- Cinco condiciones por tarea: S, I2, F, E, E_shared. La última ejecuta el mismo E
  con biblioteca; las otras cuatro consultan una biblioteca vacía. Rotar orden por
  tarea para no situar siempre una condición al final.
- Total: 6 donantes + 12×5 receptores = 66 episodios. Una biblioteca congelada con
  cero a seis recetas; ninguna publicación de receptores ni cadenas transgeneracionales.
- Modelo base del proveedor: seed73 + índice de llamada, temperatura0,2, salida768,
  contexto4096. Catálogo expanded-v2 y semilla de orden20261013.
- Misma cuota por episodio: 25k tokens, 50 herramientas, 12 llamadas LLM,
  6 críticas, 128 fuel, 300 s CPU y 900 s de pared. Máximo dos reparaciones.
- Consulta cobrada en todos los receptores, incluso biblioteca vacía. Esta operación
  adicional respecto al piloto histórico 14B se declara; la comparación histórica
  es descriptiva, no un contraste emparejado puro de tamaño del modelo.
- Acquisition y publicación se contabilizan, además de mostrar coste de receptores
  solos. Registrar lecciones disponibles por familia, acierto sin reparar, errores
  de candidato/formato, críticas, reparaciones, tokens, herramientas y tiempos.

## Límites y contingencias

Los problemas heredados `format.content` y `disconnected-lex-order` no cambian
para este ensayo. Si aparecen, informar su efecto; no confundir ausencia de salida
válida con refutación de valor. La regla de exportación exige reparación: si el 32B
resuelve un donante a la primera, no hay receta exportable bajo esta versión.

Límite del worker: 9.000 s totales; relay hasta 7.800 s de inferencia; supervisor
espera hasta 1.200 s de preparación. No relanzamiento automático de episodios
fallidos, ni presupuestos ampliados después de observar una respuesta. Los logs y
resultados parciales se conservan ante agotamiento del límite de infraestructura.
Un problema de carga antes de comenzar tareas se podrá corregir documentándolo.

Se conserva Bubblewrap/rootfs/cgroup local para todos los candidatos; Kaggle solo
recibe inferencia. Fuentes congeladas, auditoría por ejecución y matriz completa,
apagado del worker al terminar. Sin push ni publicación. S6 permanece fuera.

## Interpretación prevista

Un salto del 32B sin memoria señala un efecto de modelo bajo este protocolo;
E_shared frente a E con el mismo 32B examina el aporte de la biblioteca.
Si todos empatan arriba, hay efecto techo, no superioridad de E demostrada.
Si CSV/grafos no generan lecciones válidas, esa ausencia es resultado del mecanismo.
El catálogo conocido, la única semilla y la posible copia literal de recetas
impiden cerrar H1–H4 o T20 de manera general con esta tanda.
