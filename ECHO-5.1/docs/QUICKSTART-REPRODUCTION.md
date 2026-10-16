# Probar ECHO-5.1 y comprobar los resultados publicados

ECHO-5.1 se ejecuta desde el código fuente. `install.sh` instala el terminal
4.5; no instala automáticamente el laboratorio SWE-bench, sus entornos o modelos.

## 1. Descargar y comprobar integridad

```bash
git clone https://github.com/navywakura/echoai.git
cd echoai
python3 tools/source_setup.py verify
```

Python 3.12 o posterior para las herramientas de fuente. El laboratorio fue
probado con Python 3.14 en Linux; las pruebas de aislamiento necesitan Bubblewrap,
systemd de usuario, cgroup v2 y user namespaces. macOS/Windows no proporcionan
ese backend Linux por instalar el terminal.

## 2. Comprobar datos y regenerar las siete gráficas, sin GPU

```bash
python3 -m venv .venv-research
.venv-research/bin/python -m pip install matplotlib==3.10.9 jsonschema==4.23.0
.venv-research/bin/python ECHO-5.1/docs/swebench/results-v8-20261016/regenerate_figures.py --output /tmp/echo51-public-figures
```

El regenerador verifica el manifiesto público y el plotter antes de usar los
datos. Las figuras se escriben bajo `/tmp/echo51-public-figures/figures`.
Los resultados numéricos están en `full-results.csv`, `full-results.json` y
`analysis.json` del mismo directorio de datos publicado. Resultado principal:
S=2/17, I2/F/E=1/17; E gastó 34,14 % menos tokens totales que S. El panel
registró 24 issues por brazo y distingue las celdas no iniciadas.
La identidad byte a byte de imágenes depende también del entorno gráfico;
no se garantiza entre cualquier sistema operativo y sus fuentes/bibliotecas.

## 3. Probar la infraestructura local, sin modelo ni GPU

En Linux con los requisitos anteriores:

```bash
.venv-research/bin/python ECHO-5.1/scripts/run_repoworld.py verify --output /tmp/echo51-software-check
```

Usar un directorio de salida nuevo. Esta prueba ejecuta RepoWorld, PCWorld y
las pruebas de diseño; no reproduce inferencia. Puede tardar varios minutos.
La [verificación publicada](PUBLICATION-VERIFICATION-20261016.json) conserva
fallos intermitentes de arranque/metadatos y un fallo por longitud de ruta
temporal. No prometemos todos los tests verdes en cualquier máquina.

## 4. Repetir la inferencia SWE-bench es otro nivel

Regenerar tablas/figuras comprueba los resultados guardados; **no demuestra
que un modelo nuevo haya vuelto a resolver los mismos issues**. Una repetición
completa exige preparar repositorios, dependencias, rootfs y curador Podman,
obtener el GGUF y llama.cpp fijados, configurar un proveedor propio, superar
los gates y sellar un contrato nuevo. No se distribuyen modelos, imágenes
pesadas, credenciales ni autoridades HMAC privadas. No se deben reutilizar las
identidades de custodia ni presentar una nueva campaña como la original.

Consultar el [plan RepoWorld](SWE-BENCH-LITE-PLAN-20261013.md), el
[runbook PCWorld](RUNBOOK.md) y el
[informe final](REPOWORLD-SWE-RESULTS-20261016.md). El repositorio no es todavía
una instalación de un solo comando para replicar la campaña completa en otra
máquina; tampoco garantiza los mismos aciertos bajo otra GPU o ejecución.
