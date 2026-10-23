> Guía histórica del laboratorio. Para esta publicación use [REPRODUCE-5.8.2.md](REPRODUCE-5.8.2.md); los caminos lab/ no están incluidos completos.

# Uso local · herramientas nuevas de 5.8.2

No hay publicación en GitHub ni Hugging Face. Resultados y estado vigente:
[ROADMAP-ORDENADO.md](ROADMAP-ORDENADO.md). Tras el reinicio por falta de RAM,
el trabajo pesado se ejecuta por turnos con límites:
[RECOVERY-OOM-20261023.md](RECOVERY-OOM-20261023.md).

## Cargar y utilizar archivos .wsp

Desde `/home/user/REALRXOS/RXos/echoai`, inspeccionar el archivo y comprobar
su contenido sin llamar a un LLM:

```bash
PYTHONPATH=.. python3 -m echoai.echo58.wspfiles inspect \
  lab/echo58/wspfiles/20261023-r1/artifacts/honesto-none-m1.wsp
PYTHONPATH=.. python3 -m echoai.echo58.wspfiles verify \
  lab/echo58/wspfiles/20261023-r1/artifacts/memory-training-m01.wsp
```

Ejecutar la política original cargando su memoria desde el archivo, en un
mundo de desarrollo nuevo y con entorno MiniGrid existente:

```bash
PYTHONPATH=.. ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.wspfiles.play \
  lab/echo58/wspfiles/20261023-r1/artifacts/memory-training-m01.wsp \
  --family DynObs6 --seed 202610232 --regime A2 --output /tmp/echo-wsp-episode.json
```

El destino debe estar libre: las herramientas no sobreescriben resultados.
Los archivos preservan paquetes originales de16 bytes y metadatos; no son
una fuente de autoridad sobre lo que ocurrió. Sus hashes detectan corrupción,
no autentican al emisor. Hay exportación/importación JSON desde la misma CLI.
El perfil de memoria actual admite las claves/action/outcome del estudio;
el perfil de sesión conserva paquetes opacos y metadatos JSON.

## Auditorías sin volver a jugar ni gastar API

El índice de la entrega comprueba código, documentos y manifiestos de estudios
sin volver a importar simuladores ni usar modelos:

```bash
python3 lab/echo58/closure-20261023/verify-delivery.py
```

Es comprobación de integridad de las anclas, no una repetición de la física o
de los auditores profundos. Los informes conservan sus recibos y límites.

Ejecutar con Python normal (sin `-O`) y desde la misma carpeta:

```bash
PYTHONPATH=.. python3 -m echoai.echo58.wspfiles.integration audit \
  lab/echo58/wspfiles/agent-integration-20261023
PYTHONPATH=.. python3 -m echoai.echo58.llmstudy.audit \
  lab/echo58/llmstudy/20261023-r1
```

La auditoría del formato puede repetirse sin crear otro recibo inmutable:

```python
from echoai.echo58.wspfiles.audit import audit
print(audit('lab/echo58/wspfiles/20261023-r1'))
```

Los informes de E, C v3 y P incluyen sus comandos de auditoría y, cuando
corresponda, el anexo de recuperación. No lanzar sus comandos de campaña
históricos sobre una carpeta empezada: no son reanudadores automáticos.
El coste de Groq ya realizado está en los recibos de D. Las auditorías de
esta guía no leen claves ni hacen llamadas nuevas.

## Qué ventaja se ha medido

En los cuatro archivos medidos, WSP ocupa un 0,803 % menos que JSON columnar
base85 con la misma información e integridad; con zlib, un 0,544 % menos.
JSON gana por unos pocos bytes en el archivo de memoria. No hay una ventaja
general de compresión del 15 %. El ≈18 % de la comparación anterior solo
corresponde a sesiones frente a JSON con paquetes en hexadecimal. El
[informe de controles compactos](WSP-STRONGJSON-RESULTS-20261023.md) conserva
todos los tamaños y las victorias de JSON. La igualdad de las decisiones
tras cargar `.wsp` está comprobada en 12 mundos completos.

D2: los dos modelos logran24/24 con memoria,9/24 sin ella y0/24 con memoria
barajada en un banco simbólico propio. D1: contención técnica, sin ventaja
estadística demostrada y empate con autorización explícita. Estos resultados
no responden todavía a la pregunta de alucinaciones factuales en SimpleQA.

P: dos desarrollos y seis validaciones pasaron la integración estrecha en
Gazebo/PX4. Inspecciones congeladas: MEMORIA-X 3 / sin memoria 32 / caché 2.
Los 16 archivos WSP de los ocho vuelos conservan 98 experiencias y 13.737
paquetes de sesión. Para inspeccionar uno de los archivos de memoria:

```bash
PYTHONPATH=.. python3 -m echoai.echo58.wspfiles inspect \
  lab/echo58/percibex/20261023-r1/validation/val-w1-memx/memory.wsp
```

En este perfil, TOGGLE significa inspección yaw y PASS su éxito observado.
Cada vuelo comienza con memoria vacía: r1 no mide transferencia de ese archivo
a otro mundo ni superioridad frente a la caché simple.
