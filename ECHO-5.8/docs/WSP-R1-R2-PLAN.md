# W R1/R2 · plan de implementación y ejecución

> Ejecución nativa en esta sesión mediante superpowers:executing-plans,
> pruebas primero y una revisión final independiente.

**Objetivo:** ejecutar el contrato aprobado `WSP-R1-R2-DESIGN.md` sin inferencia,
sin nuevas partidas, sin tocar fuentes congeladas y sin publicar.
**Arquitectura:** adaptador lossless separado, corpus público fijo, benchmark
de tokens local y auditor de mensajes guardados. Stdlib más tokenizers 0.23.3
ya instalado; no se instalan dependencias ni pesos.

## Límites globales

WSP16 e IDs legacy intactos; ±100 para E, uint8 para los demás campos de
postal. Hasta 64 capas 128×128 (enmienda técnica previa a medir; límite inicial
de ocho insuficiente para el corpus fijo) y colores 0…255. Límite 4 MiB por mensaje.
El contrato manda; los dominios opacos de postal se preservan, sin conceder
autoridad ni registrar namespaces nuevos. Solo W1 es versión de contenedor.
Los tres archivos públicos se fijan por hash antes del benchmark. BP35 es
calibración; S5I5/SP80 evaluación, 64 registros iniciales cada uno.

## Tareas

1. **Codec y fixtures.** Crear `echo58/wspstudy/codec.py` y pruebas en
   `tests/test_echo58_wspstudy.py`. Funciones: validate_record(record),
   encode/decode con base opcional, encode_json/decode_json para named,
   positional y wrapped. Roundtrip de píxeles/feedback/postal, ausencia vs
   null/false/0, multicapa, JSON con `|`, límites y rechazo de corrupción.
   Geometría raw/RLE/delta idéntica para todos; delta exige contexto,
   secuencia siguiente y digest exacto. Primero tests fallidos, después
   implementación mínima y suite verde.
2. **Corpus.** Crear `corpus.py`: normalizar primeras 64 filas de las tres
   grabaciones a campos públicos del contrato; preservar presencia de
   action_input.id/data, excluir reasoning de todos los brazos. Manifiesto
   con hashes del origen, línea/índice y registro normalizado. Fixtures
   sintéticas para pérdida de campos/multicapa, sin medir todavía evaluación.
3. **Benchmark y puerta.** Crear `bench.py`: count_tokens sin chat template,
   elegir raw/RLE/delta de menor coste para cada formato; leyenda por juego,
   control JSON elegido por mínimo total del juego. Guardar mensajes y
   métricas por registro; medir encode/decode cinco veces de forma descriptiva.
   Probar la puerta con Fraction exactas, frontera 15 %, datos donde mediana
   de cocientes difiere de cociente de medianas y regresión de un juego.
4. **Revisión/congelación/ejecución.** Pruebas técnicas verdes y revisión
   independiente. Archivar fuentes/contrato/dependencias, fijar corpus,
   ejecutar calibración y evaluación una vez sin ajustar formatos entre
   ellas. Cualquier fallo técnico conserva recibos y no se convierte en pase.
5. **Auditoría e informe.** Crear `verify.py`: reconstruir todos los mensajes,
   contarlos otra vez con el tokenizador fijado y recalcular la puerta.
   Probar alteración de base/mensaje/digest. Publicar informe local y figura,
   conservar rojo si no alcanza el 15 %, continuar después con C v2.

## Verificación

En workspace aislado, usando el entorno local de tokenización existente:
`PYTHONPATH=<workspace>:<RXos> <tokenizer-env>/bin/python -m unittest
echoai.tests.test_echo58_wspstudy`. No tests ni imports de echo-discord.
Los comandos concretos, logs y hashes quedan en el registro de ejecución.

## Registro

- Aprobación recibida antes de implementar. Se preservan fuentes históricas.
- Builder check independiente: una duda material sobre fórmula de mediana;
  resuelta en el contrato como mediana exacta de 128 ahorros relativos con
  leyenda amortizada. No se cambia por un cociente de medianas.
