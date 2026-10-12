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

## Conector LLM opcional, todavía sin ensayo real

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
No se ha validado contra un servidor real en esta entrega. El identificador del
proveedor es una declaración que debe verificarse al preparar el despliegue.

## Lo siguiente

1. Fijar un runtime reproducible y completar el alcance de T08/T10.
2. Ejecutar el ciclo completo con un modelo identificado y presupuestado.
3. Incorporar tareas independientes de reparación, datos y archivos, con
   referencias externas al candidato y separación por familias.
4. Añadir las ablaciones de memoria, crítico y roles homogéneos.
5. Dimensionar la confirmación con los pares discordantes del piloto y congelar
   el contrato antes de abrir casos reservados.

S6, publicación y promoción automática no son acciones de esta interfaz.
