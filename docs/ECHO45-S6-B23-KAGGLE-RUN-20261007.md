# B23 en Kaggle: ejecución privada

Fecha: 7 de octubre de 2026. El contrato experimental sigue siendo
`ECHO45-S6-B23-MICRO-DESIGN.md`; este documento solo registra el transporte.

La cuenta `navywakura` respondió por la API. Se creó el dataset privado
`echo45-s6b23-private-20261007` con el paquete previamente preparado,
SHA-256 `575bdc3212c7cfc1e663a6a28615a20e4ef993622e9a2376f0d190f36e5904b1`.
Kaggle descomprimió el ZIP al montar el dataset: aparecieron 86 archivos.
El notebook exige comprobar los hashes de las fuentes y entradas declaradas
en `b23-input/intent.json` antes de preparar el experimento.

Dos notebooks privados se detuvieron durante el arranque técnico, antes de
congelar un manifiesto o jugar una partida:

- `echo45-s6b23-micro-20261007`: asumía una ruta fija para el dataset montado.
- `echo45-s6b23-micro-r1-20261007`: encontró el dataset, instaló el Python
  fijado, pero `ldconfig` no listó el driver CUDA. La calibración B18 ya había
  registrado que en Kaggle se obtiene cargando `libcuda.so.1` y leyendo
  `/proc/self/maps`.

`echo45-s6b23-micro-r2-20261007` incorpora ambas correcciones de transporte
y está enviado como notebook privado con GPU e internet. La fuente remota
coincide por SHA-256 con `lab/kaggle/s6b23-20261007/r2/notebook/run.py`; sus
metadatos remotos confirman `is_private=true`, GPU activa y el dataset privado.
Los dos arranques anteriores tienen cero propuestas científicas, cero llamadas
de modelo y cero partidas. No se modificó el investigador ni el juez B23.

El monitor local de solo lectura `echoai-s6b23-monitor.service` guarda
`lab/kaggle/s6b23-20261007/r2-status.json` y el log remoto. Kaggle ejecuta
el notebook independientemente de ese monitor. Solo un `closed.json` con
auditoría válida permitirá describir un resultado B23; el estado `RUNNING`
por sí solo indica únicamente que el contenedor sigue activo.

El notebook R2 comprueba dos T4, fija las revisiones públicas de Qwen2.5-Coder
7B/14B Q4_K_M, verifica sus SHA-256 LFS, compila llama.cpp en el commit
`79e0b68c178656bb0632cb8602d2940b755077f8`, instala Python 3.12.13 con
numpy 2.3.2 y arcengine 0.9.3, registra hashes de pesos y binarios, ejecuta
los tests del paquete y solo entonces congela el perfil y corre B23. Un fallo
en cualquiera de esos pasos bloquea el instrumento, sin interpretarse como
fracaso de una hipótesis científica.

## Recuperación R3 — 8 de octubre

R2 terminó en `ERROR` al segundo 949,94, durante `s6b23_build models`:
`ValueError: chat templates differ`. La compilación CUDA y las descargas
habían terminado. No llegó a `s6b23_cloud prepare`, no congeló un manifiesto
experimental y no generó propuestas ni jugó partidas del micro.

El error era exigir igualdad de las plantillas Jinja embebidas aunque el
ejecutor usa `chat()` con `--no-conversation --no-escape`. R3 conserva la
integridad individual de esas plantillas y valida el protocolo efectivo con
ambos tokenizadores: delimitadores, mensaje renderizado y comportamiento BOS.
El recibo queda en `models.json` y se vuelve a comprobar antes de ejecutar.
La enmienda está declarada en el contrato antes de cualquier resultado.
Los 48 tests de B23 pasan con Python 3.12.13; incluyen diferencias de
plantilla embebida, manipulación de metadatos, delimitadores inválidos y BOS.

Nuevo notebook privado: `navywakura/echo45-s6b23-micro-r3-20261008`.
Nuevo dataset privado: `navywakura/echo45-s6b23-private-r3-20261008`.
Paquete SHA-256:
`46208bd294c7d34190c343c67879662cd2f8aa93c22f5dc13611e48a4d002a23`.
La fuente recuperada de Kaggle coincide con la local. Kaggle confirma
`is_private=true`, GPU activa y el dataset R3. Los artefactos previos se
conservan; R3 usa su propio directorio y manifiesto.

Seguimiento local: `lab/kaggle/s6b23-20261008/r3/r3-status.json` y
`r3-remote.log`, servicio `echoai-s6b23-r3-monitor.service`. El estado
`RUNNING` se confirmó durante el arranque técnico; los marcadores
`B23_R3_EFFECTIVE_CHATML_VERIFIED` y `B23_PREPARED_PROFILE_FROZEN`
identifican la superación de la comprobación real y la entrada al micro.
No hay cierre de S6 implícito en ninguno de esos marcadores.

Comprobación adicional local del protocolo con los tokenizadores oficiales
de ambas revisiones y el ejecutor fijado: PASS, misma secuencia de 38 tokens,
`im_start=151644`, `im_end=151645`, sin BOS adicional. Se usaron únicamente
los primeros 8 MiB de cada GGUF y relleno disperso para satisfacer la
comprobación de límites del cargador `vocab_only`; no son pesos válidos y
no hubo inferencia. El recibo declara esta limitación en
`lab/kaggle/s6b23-20261008/r3/local-real-tokenizer-check.json`.
Kaggle comprueba por separado los hashes de los archivos completos y vuelve
a ejecutar el mismo diagnóstico antes del micro.
