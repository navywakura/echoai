# Reproducir la entrega pública 5.8.2

Python 3.12 o posterior. Estos controles son locales, sin llamadas a modelos,
sin simulación de vuelo y sin examen. Desde la raíz del checkout `echoai`:

```bash
python3 tools/source_setup.py verify
PYTHONPATH=..:. python3 -m unittest tests.test_echo58_wspfiles tests.test_echo58_wspstrongjson tests.test_echo58_llmstudy -v
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles verify ECHO-5.8/results-5.8.2/wspfiles/artifacts/memory-training-m01.wsp
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles use-memory ECHO-5.8/results-5.8.2/wspfiles/artifacts/memory-training-m01.wsp
```

El repositorio debe llamarse `echoai` para esos imports. Los módulos `navi10_*`
están en la raíz; `PYTHONPATH=..:.` añade tanto el paquete como esos módulos.
No usar `unittest discover`: el archivo incluye campañas históricas selladas.

La CLI también permite `inspect`, `export-json` e `import-json`; los destinos
han de ser nuevos. Los cuatro ejemplos incluyen memoria y sesiones: no todos
se pueden cargar como memoria. `.wsp` conserva paquetes de 16 bytes y metadatos;
el hash detecta corrupción, no autentica al emisor ni convierte prosa en verdad.

Para jugar un mundo de desarrollo nuevo cargando la memoria:

```bash
python3 -m venv .venv-public
.venv-public/bin/pip install gymnasium 'minigrid==3.0.0' numpy
PYTHONPATH=..:. .venv-public/bin/python -m echoai.echo58.wspfiles.play ECHO-5.8/results-5.8.2/wspfiles/artifacts/memory-training-m01.wsp --family DynObs6 --seed 202610232 --regime A2 --output /tmp/echo-wsp-example.json
```

Ese ejemplo opcional es otra ejecución de desarrollo, no una repetición del
examen. Los resultados históricos están en `results/` y `results-5.8.2/`.
Los auditores de campañas que buscan `lab/echo58/` requieren los datos completos
no incluidos: copiar los agregados allí no permite una auditoría profunda.
La comprobación SOURCE-MANIFEST acredita integridad de esta entrega pública,
no validez científica por sí sola. Véanse los límites de RELEASE-5.8.2.md.
