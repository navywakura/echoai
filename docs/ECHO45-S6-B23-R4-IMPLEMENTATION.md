# B23-R4 · corrección y comprobaciones

8 de octubre de 2026. Se ha creado una recuperación con archivos propios,
conservando los 74 archivos de ejecución congelados de R3 y su ZIP original.
El paquete R4 congela 88 archivos por hash, incluido su contrato y sus tests.

El cambio afecta a la interfaz del investigador LLM. `s6b23r4_search.py`
conserva la política, observaciones y feedback seleccionados por R3; sustituye
la plantilla ambigua por instrucciones tipadas, valores permitidos separados
y un ejemplo neutral. No recibe parches ganadores ni artefactos de PROBE.

`s6b23r4_model.py` reutiliza el transporte y contabilidad de R3 y añade GBNF al
comando real de llama.cpp. Conserva todos los átomos legales y valores HOLD;
admite cualquiera de los dos órdenes de `set`/`when`, pero ordena las claves
de las condiciones para impedir duplicados. No convierte una salida inválida
en una política mediante heurísticas. Un fallo de transporte o parseo para el
instrumento, con la llamada ya contabilizada y sus bytes conservados.

`s6b23r4_preflight.py` ejecuta cuatro comprobaciones sintéticas por modelo en
un libro separado. La entrada no contiene partidas. Exige seguimiento de la
instrucción y resultado exacto, no solo JSON válido. El arnés y la reserva de
partidas verifican el recibo, cada comando y los hashes de las ocho llamadas.
No puede arrancar el micro sin ese recibo válido.

El runner y la revisión R4 conservan las verificaciones de R3 en archivos
versionados aparte. La auditoría de una partida reconstruye la petición y
política y ejecuta `seed.s6b23r4 audit-measure` en otro proceso. Las partidas
del micro conservan diarios; retención y exámenes no reciben instrumentación
nueva. El flujo no abre S6 ni cambia sus criterios.

Validación previa a Kaggle:

- 59 tests pasan con Python 3.12.13, numpy 2.3.2 y arcengine 0.9.3.
- El parser nativo de llama.cpp, commit
  `79e0b68c178656bb0632cb8602d2940b755077f8`, verifica 582 casos: todos los
  átomos, duraciones, combinaciones de una a tres condiciones y salidas
  ilegales, en ambos órdenes de las claves del parche.
- El test nativo inicialmente confundía el código de salida del ejecutable
  con su veredicto; ese ejecutable retorna 0 también ante entradas inválidas.
  La aserción se corrigió para comprobar su mensaje de validación. Todas las
  formas ilegales se rechazan en la comprobación final.
- El ZIP extraído en una carpeta independiente pasa los 58 tests Python;
  el test nativo se omite cuando no se proporciona su binario. Kaggle lo
  compila y ejecuta también.
- Una comprobación orientativa del prompt con 17 intentos medidos de R3 ocupa
  6519 tokens con el vocabulario Qwen2 de referencia, por debajo de 8192.
  Cada inferencia remota vuelve a comprobar ambos tokenizadores GGUF reales;
  no se trunca silenciosamente el contexto.

Notebook privado:
`navywakura/echo45-s6b23-micro-r4-20261008`, versión 1, enviado a las 14:08
Madrid. SHA-256 del paquete:
`9b9cf90d896ac8da4f49c848373050d9f1d00d6c3b8bcaa5868f47a15c5b3b94`.
Hasta confirmar las ocho inferencias remotas, la reparación está probada
localmente pero la interfaz real sigue pendiente de validación.

Seguimiento de solo lectura mediante `echoai-s6b23r4-live` y
`echoai-s6b23r4-monitor`. Los estados se conservan bajo
`lab/kaggle/s6b23-20261008/r4/`; el cálculo se ejecuta en Kaggle y no depende
de que sigan abiertos esos dos lectores locales.
