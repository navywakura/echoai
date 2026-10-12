# Ejecutar PCWORLD-1 de desarrollo

Trabajar desde la raíz del checkout aislado de echoai. Python del sistema;
no usar entornos del proyecto legacy. Requisitos: Linux, Bubblewrap en
`/usr/bin/bwrap`, systemd con gestor de usuario, cgroup v2 y namespaces de usuario
habilitados. La ausencia de requisitos causa un error explícito. El comando no
instala dependencias ni altera la red del host.

## Infraestructura

```sh
python3 -I -B ECHO-5.1/scripts/run.py test
```

Pruebas reales de proceso acotadas más pruebas de contabilidad, snapshots,
recibos, adaptación WSP, propiedades y protocolo de proveedor simulado. Una
máquina sin el backend no puede declarar estos tests pasados omitiéndolos.

Regresiones seleccionadas, independientes del examen de investigación:

```sh
python3 -I -B ECHO-5.1/scripts/run.py test \
  echoai.tests.test_localdev \
  echoai.tests.test_echo4_code1_memory \
  echoai.tests.test_echo4_code1 \
  echoai.tests.test_nexus0.TestWorld \
  echoai.tests.test_nexus0.TestEncoder \
  echoai.tests.test_nexus0.TestLex \
  echoai.tests.test_nexus0.TestFallback
```

La suite histórica completa tiene un error de rutas en el generador del léxico
del checkout público plano. Se reproduce también en el checkout base intacto;
no se arregló cambiando el núcleo congelado. Ver RESULTS.md. No confundir esta
selección de regresiones con la totalidad de los tests de ECHO.

## Desarrollo y observabilidad

```sh
python3 -I -B ECHO-5.1/scripts/run.py pilot --dry-run --tasks 60 --repetitions 2
python3 -I -B ECHO-5.1/scripts/run.py pilot --provider fixture --tasks 4 \
  --output ECHO-5.1/artifacts/mi-desarrollo > /tmp/pcworld-desarrollo.log 2>&1 &
tail -f /tmp/pcworld-desarrollo.log
```

El directorio de salida debe ser nuevo. Cada episodio conserva `thought.jsonl`
con eventos reales, snapshots inmutables, recibos y costes. No hay monólogo
inventado. Las fuentes no deben cambiar durante la tanda: se comprueban antes
de cada episodio y al final; un cambio invalida la combinación de resultados.
Las cuatro propiedades programadas no equivalen a 60 problemas independientes.

```sh
python3 -I -B ECHO-5.1/scripts/run.py audit ECHO-5.1/artifacts/mi-desarrollo
```

La auditoría requiere conservar la autoridad de recibos y exactamente las
fuentes usadas. `artifacts/` está excluido de Git; contiene claves de custodia
que no deben publicarse como parte de una prueba autónoma. No edites fuentes,
tareas o resúmenes de una tanda para que su auditoría vuelva a pasar.

## Conector LLM y primer piloto local

La continuación del 13 de octubre incorpora llama.cpp. La configuración usada
está en `QWEN-LOCAL.example.json`: Qwen2.5-Coder-7B-Instruct Q4_K_M,
512 tokens máximos de salida por llamada, contexto 4096, temperatura 0,2 y
semilla 73 + índice de llamada. Primero se aplica la plantilla del servidor,
después se tokeniza y se pasan esos mismos IDs a `/completion`. El cómputo de
tokens de entrada incluye toda la plantilla, incluso cuando el servidor pudiera
reutilizar prefijos; la caché de prompt se desactiva para la comparación.

El GGUF oficial usado está fijado en la revisión
`13fb94bfda8c8cf22497dc57b78f391a9acb426a`, archivo
`qwen2.5-coder-7b-instruct-q4_k_m.gguf`, SHA-256
`509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`.
Se guarda fuera del repositorio. El ejecutable y sus bibliotecas también se
identifican en el recibo de despliegue local; un alias HTTP por sí solo no
acredita qué modelo sirve un proveedor remoto.

```sh
python3 -I -B ECHO-5.1/scripts/run.py runtime build ECHO-5.1/artifacts/runtime
python3 -I -B ECHO-5.1/scripts/run.py runtime export ECHO-5.1/artifacts/runtime \
  --archive ECHO-5.1/artifacts/runtime.tar
python3 -I -B ECHO-5.1/scripts/run.py runtime verify ECHO-5.1/artifacts/runtime
```

Para restaurarlo en otra máquina Linux compatible, usar `runtime import` con
un directorio nuevo, `--archive` y `--expected-id` igual al hash obtenido.
Construir otra imagen desde otro `/usr` puede producir bytes distintos; la
reproducción se hace restaurando el archivo exportado. El rootfs contiene
Python, stdlib y dependencias ELF; no instala pip, paquetes externos ni GUI.
No se promete identidad de kernel, hardware, reloj o aleatoriedad.

Arrancar un servidor llama.cpp compatible, sólo en loopback. Ejemplo CPU:

```sh
llama-server --model /ruta/qwen2.5-coder-7b-instruct-q4_k_m.gguf \
  --alias pcworld-qwen25-coder7b --host 127.0.0.1 --port 8785 \
  --ctx-size 4096 --parallel 1 --threads 4 --threads-batch 4 \
  --n-gpu-layers 0 --device none --no-op-offload
```

Comprobar su build, hashes y velocidad antes de congelar la tanda. El binario
del sistema tardó 93,95 s en una consulta de 201 tokens; el build CPU nativo
`d230ddd` tardó 20,52 s en la calibración equivalente. Son dos mediciones de
preparación, no un benchmark de servidores.

```sh
python3 -I -B ECHO-5.1/scripts/run.py pilot --provider http --suite repair-v1 \
  --config ECHO-5.1/docs/QWEN-LOCAL.example.json --tasks 6 \
  --runtime ECHO-5.1/artifacts/runtime \
  --output ECHO-5.1/artifacts/repair-pilot > /tmp/repair-pilot.log 2>&1 &
```

Son 24 episodios, seis familias por cuatro brazos, máximo 600.000 tokens en
conjunto y 25.000 por episodio. Los casos de evaluación de cada familia no se
entregan a los roles. No son tareas de un benchmark oficial ni una confirmación
sellada; no se tratará esta muestra pequeña como demostración de superioridad.

Un diagnóstico separado con `--arms F --seeded-diagnostic` entrega al crítico
el programa defectuoso inicial y exige que produzca un contraejemplo ejecutable
antes de reparar. Ese defecto fue sembrado por el experimento: nunca se cuenta
como primera propuesta fallida del LLM ni se mezcla con S/I2/F/E.

`--cache-properties` permite la caché persistente autenticada de comprobaciones
puras. Está desactivada en el piloto principal. La ejecución del candidato
siempre se repite: fijar el rootfs no elimina acceso al reloj ni aleatoriedad.
El coste de consulta se registra incluso en los aciertos de caché.

### Protocolo vLLM anterior

Sólo se admite un servicio explícito que tenga tokenización previa del mismo
prompt y plantilla, y el endpoint de completions compatible. Ejemplo de
configuración que debe rellenarse con identidades reales antes de usar:

```json
{
  "endpoint": "http://127.0.0.1:8000/v1/chat/completions",
  "tokenize_endpoint": "http://127.0.0.1:8000/tokenize",
  "model": "IDENTIDAD_REAL_DEL_MODELO",
  "revision": "REVISION_INMUTABLE",
  "quantization": "CUANTIZACION_REAL",
  "tokenizer": "IDENTIDAD_Y_REVISION_DEL_TOKENIZER",
  "max_output_tokens": 2048,
  "timeout_seconds": 60
}
```

`key_env`, opcional, acepta únicamente el nombre de una variable de entorno.
No pegues tokens secretos en el JSON; la configuración queda en el manifiesto.
No hay modelo, credencial, servidor ni descarga predeterminados.

```sh
python3 -I -B ECHO-5.1/scripts/run.py pilot --provider http \
  --config /ruta/proveedor.json --tasks 1 \
  --output ECHO-5.1/artifacts/primer-modelo
```

Este comando inicia **un ensayo de desarrollo con cuatro brazos**, no la campaña
científica. El contrato global y los costes deben quedar fijados antes de una
campaña. El conector exige tokenización previa y contabilidad de entrada/salida;
una API compatible sólo en formato de chat puede no cumplir ese protocolo.
El protocolo vLLM conserva sus tests simulados; la validación local nueva usa
llama.cpp. El identificador del proveedor es una declaración que debe verificarse
al preparar el despliegue.

## Lo siguiente

1. Revisar los resultados locales y ampliar tareas independientes por familias,
   incluyendo repositorios reales y otras dependencias con contratos propios.
2. Añadir las ablaciones de memoria, crítico y roles homogéneos.
3. Dimensionar la confirmación con los pares discordantes del piloto y congelar
   el contrato antes de abrir casos reservados.

S6, publicación y promoción automática no son acciones de esta interfaz.
