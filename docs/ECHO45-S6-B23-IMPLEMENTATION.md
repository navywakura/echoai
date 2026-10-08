# Implementación privada de B23

7 de octubre de 2026. **42/42 pruebas B23 y 102/102 de regresión pasan.** El
paquete se comprueba también extraído en un directorio aislado. El
instrumento real se valida en un registro separado, con 61 niveles esperados
y 42 partidas entre medición, replay y auditoría. No propone candidatos ni
llama al modelo. El micro
compara R22, M22, M23, N7 y N14 siguiendo
el [contrato B23](ECHO45-S6-B23-MICRO-DESIGN.md). Su ejecución experimental
espera los pesos 7B/14B y sus hashes. S6 continúa abierto.

`echo_arc/s6b23_search.py` contiene el investigador puro. R22 y M22 llaman
al selector B22 original. M23 conserva ramas con ganancia positiva, limita
los hijos y reparaciones por linaje, reconsidera el mejor descendiente y
filtra propuestas inactivas sobre las lecturas reales de la base. Los
ordenamientos usan asociaciones observadas, sin certificar efectos futuros.
Los cinco brazos tienen dieciocho plazas como máximo.

`seed/s6b23_model.py` ejecuta GGUF locales con llama.cpp, sin APIs ni cambios
automáticos de modelo. Comprueba archivos, metadatos y número de parámetros.
Guarda prompts exactos, tokens de entrada de ambos modelos, salida original,
errores y presupuestos. La inferencia no puede cambiar el juez. No se pide
un monólogo interno: el diario contiene propuestas y resultados observables.

`seed/s6b23.py` reutiliza el ejecutor auditado de B22 con directorios propios.
La medición, el replay y la auditoría independiente usan cachés distintas.
La reserva de trabajo precede a la ejecución; una partida iniciada sin
recibo completo bloquea la reanudación automática. Una llamada de modelo
interrumpida también conserva su gasto y requiere una recuperación declarada.
Un fallo del instrumento queda como `INSTRUMENT_BLOCKED`, nunca como rechazo
científico de una hipótesis.

Los finalistas se congelan juntos antes de medir desarrollo amplio. La
retención de 80 casos exige un pase amplio auditado, identidad de política,
revisión de exposición y permiso ligado al manifiesto. No se sustituye un
finalista después de conocer su resultado amplio. No hay código que abra
la campaña desde SEMILLA ni el examen S6 desde este micro.

`seed/s6b23_review.py` revisa aritmética, contabilidad, prompts, resultados
y enlaces entre recibos sin importar investigador ni simulador. Los
presupuestos máximos son 3.990 partidas para el micro, 2.880 para desarrollo
amplio y 1.440 para conservación: 8.310 en total, con fases posteriores
condicionadas. Hay hasta 36 inferencias. Una sola semilla de búsqueda no
permite afirmar superioridad estadística del algoritmo ni del modelo.

Preparación local con el entorno ya gestionado del proyecto:

```bash
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m unittest tests.test_s6b23 -v
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b23_build stage
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b23_build readiness
```

`stage` comprueba el cierre B22 y copia solo su política base y las
trayectorias base necesarias para paridad. No incorpora sus propuestas ni
los controles humanos. `readiness` escribe los bloqueos concretos. El
manifiesto experimental se congela únicamente con `prepare`, después de
identificar los pesos y pasar las pruebas.

Para registrar modelos ya descargados y fusionados en un GGUF por tamaño:

```bash
python -m seed.s6b23_build models \
  --n7 /models/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  --n14 /models/qwen2.5-coder-14b-instruct-q4_k_m.gguf \
  --revision7 COMMIT_HF_7B --revision14 COMMIT_HF_14B \
  --cli /usr/local/bin/llama-cli \
  --tokenizer /usr/local/bin/llama-tokenize \
  --backend cuda --tensor-split 1,1 --output models.json
```

Los `COMMIT_HF_*` deben ser hashes reales de 40 caracteres, nunca `main`.
El comando calcula los hashes de pesos y binarios; rechaza sustituciones
4B→7B y cuantizaciones distintas. Para una única GPU se fija `--tensor-split 1`
antes de congelar. No se cambia hardware o perfil a mitad de una campaña.
Las dos T4 pueden repartirse las capas; este reparto no convierte su memoria
en una única GPU ni demuestra que el modelo mayor resulte más eficiente.

La descarga debe fijar la revisión con `hf download`, conservar la
procedencia y descargar únicamente Q4_K_M. Los repositorios oficiales son
[Qwen 7B GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) y
[Qwen 14B GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF).
Si vienen divididos en shards, se fusionan antes de registrar su hash final;
no se hace inferencia con un único fragmento.

Para Kaggle o Colab, el paquete privado se crea así:

```bash
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b23_build package /tmp/echo-b23-private.zip
```

Contiene código necesario, contrato, pruebas y observaciones base; no
incluye pesos, credenciales, políticas ganadoras ni diarios históricos de
propuestas. No se sube automáticamente a ningún servicio. En el entorno
remoto se usa Python **3.12.13**, numpy **2.3.2** y arcengine **0.9.3**, más
el mismo ejecutor llama.cpp para los dos modelos. Con el ZIP extraído y
`models.json` creado en ese entorno:

```bash
python -m seed.s6b23_cloud prepare \
  --input b23-input --models models.json --root /kaggle/working/b23-run
python -m seed.s6b23_cloud run --root /kaggle/working/b23-run
```

En Colab, se sustituye el directorio de salida por uno persistente que se
haya montado previamente. El código no monta cuentas ni copia credenciales.
`prepare` vuelve a comprobar el paquete y ejecuta las pruebas antes de
congelar; `run` comprueba los hashes y continúa desde recibos completos.
No borra ejecuciones interrumpidas para repetirlas silenciosamente.

En local, tras generar el registro de modelos y guardar la salida de las
pruebas en un archivo:

```bash
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b23_build prepare \
  --models models.json --tests-log lab/seed/s6b23-20261007/tests-final.log
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b23_build launch
python3 observe.py --launch lab/seed/s6b23-20261007/live/journal.jsonl
```

El estado está en `status.json`; los prompts y respuestas, en `calls/`;
cada propuesta y efecto, en `steps/`; el cierre, en `closed.json` y
`arithmetic-review.json`. La primera base de catorce partidas, repetida y
auditada, genera `estimate.json`. Su estimación separa el coste de juegos
del coste de inferencia todavía no medido.

Para un resumen sin ejecutar nada:

```bash
python -m seed.s6b23_report --root lab/seed/s6b23-20261007
```

La prueba de formato con diecisiete resultados sintéticos pasó de 14.159
a 7.311 tokens con el tokenizador 4B local. Conserva deltas de nivel y flags
exactos de pérdida; solo redondea el score mostrado. Este dato diagnostica
el formato, no valida los tokenizadores 7B/14B ni mide inferencia. El
transporte comprueba ambos tokenizadores reales antes de cada llamada.

La primera prueba del instrumento reprodujo las trayectorias, pero la
comprobación final descubrió 28 recibos de workers guardados en el directorio
por defecto. El método de arranque `spawn` no hereda cambios en globals del
padre. Esa prueba queda supersedida, con incidente y bytes originales
conservados. Cada tarea ahora lleva directorio de ejecución y de entradas
explícitos; el worker rechaza cachés fuera de su directorio. R1 repite la
medición y comprueba también la ubicación e identidad de todos los recibos.
El monitor no cuenta recibos sin reserva como progreso experimental.

La prueba corregida del instrumento se registra aparte en
`lab/seed/s6b23-instrument-r1-20261007/`; la primera y su incidente se
conservan en `lab/seed/s6b23-instrument-20261007/`. Son 84 partidas físicas
de comprobación entre ambos intentos. Reproducen únicamente la base con su
replay y auditoría; no investiga candidatos y no se suma como evidencia de
ventaja M23 o del neocórtex. Los tests con transportes simulados tampoco
demuestran funcionamiento real de los pesos 7B/14B.
