# W+ · archivos .wsp · resultados 23/10/2026

**Verde técnico; utilidad local acotada. W R1 verde/R2 tokens roja siguen cerradas.**

Contrato y fuentes fijados antes de medir. Python 3.14 del sistema, stdlib, zlib; sin API, modelos, instalaciones, juegos nuevos, exámenes, publicación ni cambios de módulos certificados.

Se generaron cuatro archivos `.wsp` reales y sus tres controles equivalentes (16 artefactos). El auditor offline reconstruyó exactamente 1288/1288 postales entre los cuatro brazos: 322 registros fuente, conservando bytes y metadatos. Las sesiones usan publicaciones de desarrollo de ronda 1; original y enviado son registros separados. La memoria conserva 539 observaciones de entrenamiento y 12 postales actuales de reglas; sus postales se generaron al exportar, sin inventar tiempos históricos.

| Fuente | Registros WSP | WSP B | JSON posicional + SHA B | WSP zlib B | JSON zlib + SHA B | Ahorro WSP sin comprimir |
|---|---:|---:|---:|---:|---:|---:|
| honesto-none-m1 | 104 | 9604 | 11733 | 980 | 981 | 18.145% |
| memory-training-m01 | 12 | 104716 | 104913 | 26693 | 26649 | 0.188% |
| oraculo-false_remote-m3 | 102 | 9434 | 11521 | 952 | 951 | 18.115% |
| prudente-false_safe-m1 | 104 | 9607 | 11736 | 999 | 1003 | 18.141% |

JSON usa arrays posicionales y hex de 32 caracteres por postal, más compacto que 16 enteros. Los metadatos y toda la información son idénticos. Ambos reciben un SHA-256 de 32 bytes; las cifras JSON sin recibo son, por orden de la tabla: 11701, 104881, 11489, 11704 B. Frente a JSON sin recibo el ahorro de las sesiones sigue siendo aproximadamente 17,9%.

La ventaja de tamaño >=10% se cumple en las tres sesiones frente a JSON sin comprimir. **No hay ventaja relevante frente a JSON comprimido:** WSP zlib gana 1 y 4 bytes en las dos primeras sesiones y pierde 1 byte en la tercera; la memoria pierde 44 bytes. Un `.wsp` bruto es mucho mayor que JSON zlib. El historial domina la memoria y su ahorro bruto es solo 0,19%. No se deducen tokens ni inteligencia.

## Tiempos descriptivos

Nueve réplicas por brazo/operación, orden rotado e invertido, warm-up previo, wall clock y CPU guardados íntegros. Medianas wall en microsegundos; p95, CPU y cada muestra están en `results.json`. Archivos en caché del SO, carga de máquina no aislada; no son tiempos de disco frío ni una prueba estadística.

| Fuente | Brazo | Escribir¹ µs | Decode µs | Leer + decode µs | Leer una postal² µs | Residente³ µs |
|---|---|---:|---:|---:|---:|---:|
| honesto-none-m1 | wsp | 2123.55 | 1147.09 | 1334.68 | 329.65 | 3.21 |
| honesto-none-m1 | json | 2238.02 | 2881.82 | 2774.62 | 608.12 | 3.28 |
| honesto-none-m1 | wsp-zlib | 2127.25 | 1128.58 | 1079.34 | 413.12 | 3.28 |
| honesto-none-m1 | json-zlib | 2407.80 | 2998.18 | 2645.41 | 869.32 | 2.86 |
| memory-training-m01 | wsp | 6901.51 | 15275.79 | 10754.77 | 21595.10 | 3.28 |
| memory-training-m01 | json | 18942.98 | 25703.35 | 24635.95 | 4525.21 | 3.35 |
| memory-training-m01 | wsp-zlib | 19642.87 | 11168.24 | 6593.65 | 9859.67 | 3.35 |
| memory-training-m01 | json-zlib | 25374.81 | 18634.77 | 24628.97 | 3107.97 | 3.35 |
| oraculo-false_remote-m3 | wsp | 1579.90 | 998.04 | 1145.97 | 201.98 | 3.35 |
| oraculo-false_remote-m3 | json | 1431.13 | 2217.84 | 2985.54 | 472.55 | 3.35 |
| oraculo-false_remote-m3 | wsp-zlib | 1499.58 | 884.90 | 1179.49 | 200.66 | 3.35 |
| oraculo-false_remote-m3 | json-zlib | 1952.30 | 2390.14 | 3245.35 | 447.27 | 3.35 |
| prudente-false_safe-m1 | wsp | 1401.45 | 910.60 | 945.38 | 124.95 | 19.21 |
| prudente-false_safe-m1 | json | 1926.73 | 2858.08 | 4429.10 | 332.24 | 18.86 |
| prudente-false_safe-m1 | wsp-zlib | 1791.59 | 1111.75 | 1560.76 | 137.03 | 19.14 |
| prudente-false_safe-m1 | json-zlib | 2151.55 | 2229.78 | 2741.16 | 358.01 | 19.07 |

¹ La operación medida es **codificar el archivo en memoria**, incluida compresión y hash; no mide fsync ni escritura de disco. La creación real de los artefactos se hace fuera del cronómetro.

² Incluye leer archivo, validar recibo y localizar la postal. JSON debe parsear su documento; WSP puede omitir los metadatos por registro. No se mide seek frío ni lectura parcial con hash previamente confiado. El historial de memoria está en el descriptor, que se valida al acceder: ahí **WSP pierde** frente al acceso selectivo JSON (21,6 ms frente a 4,5 ms sin compresión). Esto limita el interés del layout para memoria con mucho historial. Las sesiones favorecen WSP en esta operación, sin reclamar ventaja en todo acceso.

³ Objetos ya decodificados: el mismo acceso `records[index].packet` en los cuatro brazos. Diferencias pequeñas y ruido no son una ventaja de formato. WSP también pierde en codificación bruta de la sesión oráculo frente a JSON (1,58 ms frente a 1,43 ms).

## Uso real por ECHO

El wrapper nuevo exporta la `Memory` original de entrenamiento, la reconstruye desde `.wsp` mediante su `observe` original y comprueba cadena, head, l1/l2, umbrales y postales. `Agent(source=load_memory(path))` usa después esa memoria. En 15 claves observadas de entrenamiento, sondas declaradas de `Agent._decide`: **15/15 decisiones idénticas**, 45 consultas y 31 hits; **8/15 decisiones difieren del agente sin memoria**. Por tanto la memoria cargada afecta decisiones. Son sondas de política con escenarios explícitos, no episodios históricos, ni benchmark de score nuevo, ni examen.

Alcance del perfil `memx-replay-v1`: claves i/s/h enteras 0…255, acciones ENTER/PICK/TOGGLE y outcomes de MEMORIA-X, n_min 1…1000000 y pct 1…100. La clase Memory permite instancias más generales; este perfil no promete representar toda instancia arbitraria. El perfil genérico conserva cualquier secuencia original de 16 bytes y metadatos JSON válidos, sin validar semántica ni conceder autoridad.

La CLI `use-memory` se ejecutó también sobre el archivo generado. Exportación JSON e importación a `.wsp` dieron bytes idénticos (`cmp`, salida 0). `technical/` contiene esos recibos, JSON de inspección apto para integración web y la memoria reimportada. No se cambió la web existente; el visor entregado es la inspección JSON de CLI.

## Validación y límites

- 19 pruebas propias verdes, incluidas cada truncación y alteración byte a byte de una muestra, versiones/flags/hash, tamaños declarados, tipos/profundidad/UTF-8, expansión zlib, sobrescritura, CLI, cadena de memoria y alteración de auditoría/métricas/fuentes.
- La primera ejecución con Python del sistema carecía de `tokenizers` para el pipeline WSP antiguo. La comprobación final utilizó el entorno ya gestionado `/home/user/.local/share/echoai-tools/echo55-tokenizer-v3/bin/python`: **23/23 pruebas históricas completas pasan**. No se instaló nada ni se repitió un examen o benchmark cerrado; son fixtures sintéticos de codec/corpus/gate/pipeline. Recibo y journal en `lab/echo58/wspfiles/technical-final-20261023/`. Unidad limitada a una CPU, 1 GiB de RAM y sin swap; consumió 17,75 s de CPU y un pico de 113.168.384 bytes de RAM.
- Auditoría en proceso nuevo: 16 artefactos y 1288 postales exactas, métricas reconstruidas desde nueve muestras, 15 decisiones sin discrepancias. SHA detecta corrupción, no autentica a otros agentes.
- El acceso selectivo solo verifica envoltura, hash y descriptor; `verify` o `read` deben usarse para validar también todos los metadatos. No sustituir esa distinción por una garantía de mensaje válido.
- La corrección previa de corpus (r09 inexistente en dos fuentes → r01 común) figura en el contrato; no hubo selección por tamaños ni cambios tras ver tiempos.

## Artefactos y comandos

Raíz: `lab/echo58/wspfiles/20261023-r1/`. `preflight.json`, `manifest.json`, `results.json`, `audit.json`, fuentes en `sources/`, datos fuente en `corpus/`, formatos en `artifacts/`, diario factual `observations.jsonl` y recibos de CLI en `technical/`.

Desde RXos con `PYTHONPATH=.` y Python del sistema:

```sh
python3 -m echoai.echo58.wspfiles inspect echoai/lab/echo58/wspfiles/20261023-r1/artifacts/honesto-none-m1.wsp
python3 -m echoai.echo58.wspfiles verify echoai/lab/echo58/wspfiles/20261023-r1/artifacts/memory-training-m01.wsp
python3 -m echoai.echo58.wspfiles use-memory echoai/lab/echo58/wspfiles/20261023-r1/artifacts/memory-training-m01.wsp
python3 -m unittest echoai.tests.test_echo58_wspfiles
```

La auditoría puede repetirse sin escribir otro recibo inmutable:

```python
from echoai.echo58.wspfiles.audit import audit
print(audit("echoai/lab/echo58/wspfiles/20261023-r1"))
```

- Preflight SHA-256: `3178bbd80bc480eafe001d9b570931158b92f0e458525851fb16f42e8f51a5a0`
- Resultados SHA-256: `f433d585ec6a5dde2c33c802dd0565c9888e034212eb1978e7000b0d242965fe`
- Manifiesto SHA-256: `8bae0fbd8af0db432b3e5ee5159ffc116095dd3db153b0119faf18094596cc3a`

La revisión estática cruzada no encontró bloqueo importante; pidió acotar explícitamente el perfil Memory, reflejado arriba. No se modifica roadmap/handoff global desde este frente.
