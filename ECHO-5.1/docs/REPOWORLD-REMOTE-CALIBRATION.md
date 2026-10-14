# Gate 3: una instancia, inferencia remota y parada

Este procedimiento está preparado, **no ejecutado**. No lanzar Kaggle hasta que
`offline-preflight`, `mock-smoke` y `official-controls` (36/36) sean válidos y
correspondan a las fuentes actuales. El contrato continúa en `design`.
`calibrate-remote` es un alias de `calibrate`, con las mismas comprobaciones.

**Bloqueo verificado el 14 de octubre:** Requests-2674 no supera el control
negativo. No utilizar los informes `controls-r4` o su recuperación como gate
aprobado. Una invocación local de `calibrate-remote` con proveedor deshabilitado
fue rechazada con `official-controls has not passed`, sin crear el directorio
de calibración. Véase el [diagnóstico](REPOWORLD-CURATOR-ALL-20261014.md).

## Preparación local (sin GPU)

Desde la raíz del worktree, elegir un directorio privado nuevo `RUN` bajo
`ECHO-5.1/artifacts/`. Crear `relay-secrets.json` con dos valores aleatorios
independientes, claves `client_token` y `worker_token`, y permisos 0600.
No publicar secretos, cuadernos que los incluyan ni resultados privados.

El relay se inicia **cuando se vaya a calibrar**, con diario persistente:

```bash
python3 ECHO-5.1/scripts/inference_relay.py "$RUN/relay-secrets.json" \
  --port 8786 --journal "$RUN/relay-journal" --log "$RUN/relay.jsonl"
cloudflared tunnel --url http://127.0.0.1:8786
```

Conservar ambos PID propios. Usar el origen HTTPS que devuelve el túnel para el
worker. El proveedor local puede usar `http://127.0.0.1:8786`; no necesita salir
por el túnel. Su JSON debe incluir los campos de
`QWEN-LOCAL-REPAIR.example.json`, sustituyendo:

- `endpoint`, `tokenize_endpoint`, `template_endpoint`: puerto 8786.
- `model`: `pcworld-qwen25-coder32b`.
- `revision`: `9d3053fce650fe1cdbdb75998c2a87add9d178ef`.
- `tokenizer`: `embedded GGUF 4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`.
- `timeout_seconds`: 240; `key_env`: `REPOWORLD_RELAY_TOKEN`.

Exportar `REPOWORLD_RELAY_TOKEN` leyendo `client_token` sin imprimirlo.
Mantener Q4_K_M, contexto 4096, salida 768, semilla 73 y temperatura 200 milésimas.

## Worker privado en Kaggle

Reutilizar `write_bundle()` de `scripts/prepare_kaggle_repair.py` mediante
`runpy.run_path`, **sin llamar a su función prepare() de reparación 14B**.
El objeto de entrada debe contener:

```python
bundle = {
    "schema": "pcworld.gpu-repair-input.v1", "scientific_claim": False,
    "gpu_model": "qwen25-coder32b", "jobs": [],
    "config": worker_provider_config,
    "relay": {"broker_url": tunnel_https_origin,
              "worker_token": credentials["worker_token"], "max_seconds": 600},
}
write_bundle(bundle, output, private_kernel_slug,
    extra_sources={"inference_relay.py": relay_source}, timeout_seconds=1800)
```

`worker_provider_config` usa las mismas identidades del modelo, pero endpoints
locales de Kaggle en `127.0.0.1:8785` y sin `key_env`. `relay_source` es el texto
del script local `inference_relay.py`. El preparador escribe el cuaderno privado,
pero no lo sube. Revisar que `jobs` siga vacío antes de lanzar ese único cuaderno
con 2×T4. No incluir repositorios, pruebas reservadas ni parches de referencia.

El worker comprueba hashes del modelo/binarios y las 65 capas en GPU. Los 600 s
limitan la espera/inferencia del relay **después de descargar y cargar el modelo**;
no garantizan diez minutos de cuota total. La envoltura limita el proceso completo
a 1800 s. Una calibración cortada por ese límite queda fallida, no verde.

## Único comando de calibración

Sustituir las rutas por los gates actuales; no reutilizar informes cuyo manifiesto
de código difiera. El comando comprueba esa identidad antes de consultar al modelo.

```bash
python3 ECHO-5.1/scripts/run_repoworld.py calibrate-remote \
  --registry "$REGISTRY" \
  --contract ECHO-5.1/docs/SWE-CONTRACT.json \
  --sample ECHO-5.1/docs/swebench/SWE-SAMPLE.json \
  --preflight "$PREFLIGHT" --curator "$CURATOR" --smoke "$SMOKE" \
  --provider "$RUN/provider-config.json" \
  --instance sympy__sympy-19007 --output "$RUN/calibration"
```

## Parada y comprobación

El supervisor solicita `/stop` en un `finally`, incluso si falla el episodio.
`worker-stop.json` acredita una solicitud, **no confirma la terminación remota**.
Comprobar en Kaggle que el worker finalizó y que `gpu-proposer-results.json`
contiene `relay_result.stopped: true` (o documentar timeout/error). El worker
termina `llama-server` en su propio `finally`; detener además la sesión/cuaderno
GPU en Kaggle y comprobar su estado final. Cerrar solo los procesos propios del
relay y túnel. Si el supervisor muere abruptamente, el plazo del worker limita
la espera; detener igualmente la sesión de Kaggle.

Auditar el episodio con `run_repoworld.py audit-episode`. Registrar latencia,
contabilidad y cierre del worker. Este gate comprueba el pipeline, no demuestra
resolución oficial de SWE-bench ni autoriza por sí solo la campaña completa.

## Gates locales de esta entrega y restauración

Los gates autenticados locales están en:

```bash
REGISTRY=ECHO-5.1/artifacts/repoworld-option-b-20261014/registry.json
PREFLIGHT=/tmp/echo-curator-preflight-r2
SMOKE=/tmp/echo-curator-smoke-r2
```

La autoridad HMAC vincula cada diario a su ruta absoluta: no usar una copia
movida como gate ni editar `authority.json`. Se conservan archivos completos
`preflight-full-evidence.tar.gz`, `smoke-full-evidence.tar.gz` y
`software-full-evidence.tar.gz` en la carpeta de evidencia de esta entrega.
Si `/tmp` se ha limpiado, comprobar primero los hashes del manifiesto y restaurar
cada archivo en `/tmp`, únicamente cuando su directorio de destino no exista.
Así se recupera la misma ruta y autoridad. Las copias de consulta en la carpeta
de evidencia no son gates trasladables. `require_gate` vuelve a autenticar el
contenido y a comparar las fuentes antes de iniciar inferencia.

## Curador local: perfil de Podman de esta entrega

Tras recuperar el espacio de metadatos de Btrfs, el curador usa un servicio
rootless propio, iniciado con esta opción explícita de extracción:

```bash
podman --storage-opt overlay.ignore_chown_errors=true system service \
  --time=0 unix:///tmp/repoworld-docker-api/api.sock
```

La opción evita que los propietarios de archivos de qhull, fuera del rango
subordinado disponible, impidan descargar las imágenes oficiales de Matplotlib.
Puede modificar propietarios durante la extracción; los contenidos y los
identificadores de imagen siguen fijados. Los controles vacío/referencia deben
validarse con este mismo perfil antes de usarlo en la evaluación final.
No se modifica `~/.config/containers/storage.conf`.

El perfil operativo, la orden de arranque y las identidades de las imágenes se
conservan en `curator-runtime-r4.json` y `rootless-unpack-policy.json` dentro de
la carpeta de evidencia. Para repetir los controles usar el `curator-config.json`
de esa carpeta y exportar `REPOWORLD_CURATOR_SERVICES` con la ruta absoluta de
`services.json`, junto con su SHA-256 en `REPOWORLD_CURATOR_SERVICES_SHA256`.
Detener solo este servicio propio después de la ejecución. Gate 3 ejecuta el
repositorio con Bubblewrap; el servicio del curador no necesita estar activo
para inferencia/calibración.
