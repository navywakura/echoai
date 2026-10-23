# W · JSON compacto · resultado descriptivo, 23/10/2026

WSP mantiene una ventaja de tamaño pequeña frente a estos controles en la suma de los cuatro Archives: **0,803 % sin comprimir frente al JSON columnar base85** y **0,544 % con zlib e integridad**. JSON gana en varias medidas del Archive de memoria. El ~18 % previo corresponde al JSON posicional hex32 de sesiones y no representa superar al mejor JSON. No se modifica W/R2 ni ninguna puerta.

Este add-on es **post hoc y descriptivo**: los cuatro Archives ya se habían visto. El plan se fijó antes de las nuevas codificaciones; el coordinador revisó el código y autorizó el freeze antes de medir. No hay muestra nueva, examen, inferencia cognitiva, latencia medida ni afirmación universal sobre JSON. Se ejecutó una medición del corpus fijo y una auditoría en proceso nuevo.

## Información y denominadores

Cada representación conserva perfil, provenance, metadata de archivo, los 16 bytes originales de cada paquete y todos los metadatos de cada registro, incluidos tipos JSON e historial. No se elimina ni resume información. Los tres layouts son b64-rows, b64-columns y b85-columns fijados en el plan; no se eligió un ganador tras medir.

Payload excluye únicamente el SHA256 binario final de 32 bytes. Full añade esos mismos 32 bytes a cada representación; detectan corrupción, no autentican al emisor. Las dos columnas zlib comprimen su respectivo payload/full con nivel9 y el mismo runtime. Ventaja WSP = `100 × (JSON − WSP) / JSON`: el denominador es siempre el tamaño del JSON correspondiente; negativo significa que gana JSON. Las sumas son sumas de bytes de los cuatro casos, sin seleccionar casos ni promediar porcentajes.

## Todos los tamaños, bytes

| Archive (registros) | Formato | Payload | Full + SHA32 | zlib(payload) | zlib(full) |
|---|---|---:|---:|---:|---:|
| honesto-none-m1 (104) | wsp | 9572 | 9604 | 921 | 980 |
| honesto-none-m1 (104) | b64-rows | 10869 | 10901 | 938 | 1001 |
| honesto-none-m1 (104) | b64-columns | 10076 | 10108 | 1142 | 1212 |
| honesto-none-m1 (104) | b85-columns | 9936 | 9968 | 974 | 1035 |
| memory-training-m01 (12) | wsp | 104684 | 104716 | 26623 | 26693 |
| memory-training-m01 (12) | b64-rows | 104785 | 104817 | 26594 | 26671 |
| memory-training-m01 (12) | b64-columns | 104696 | 104728 | 26614 | 26693 |
| memory-training-m01 (12) | b85-columns | 104680 | 104712 | 26606 | 26688 |
| oraculo-false_remote-m3 (102) | wsp | 9402 | 9434 | 894 | 952 |
| oraculo-false_remote-m3 (102) | b64-rows | 10673 | 10705 | 897 | 955 |
| oraculo-false_remote-m3 (102) | b64-columns | 9894 | 9926 | 1106 | 1164 |
| oraculo-false_remote-m3 (102) | b85-columns | 9758 | 9790 | 937 | 1003 |
| prudente-false_safe-m1 (104) | wsp | 9575 | 9607 | 952 | 999 |
| prudente-false_safe-m1 (104) | b64-rows | 10872 | 10904 | 962 | 1032 |
| prudente-false_safe-m1 (104) | b64-columns | 10079 | 10111 | 1165 | 1232 |
| prudente-false_safe-m1 (104) | b85-columns | 9939 | 9971 | 1003 | 1060 |
| **Suma cuatro** | **wsp** | **133233** | **133361** | **29390** | **29624** |
| **Suma cuatro** | **b64-rows** | **137199** | **137327** | **29391** | **29659** |
| **Suma cuatro** | **b64-columns** | **134745** | **134873** | **30027** | **30301** |
| **Suma cuatro** | **b85-columns** | **134313** | **134441** | **29520** | **29786** |

Los zlib(full) WSP son exactamente iguales, byte a byte, a los cuatro `.wsp.zlib` originales (980, 26693, 952, 999 bytes). No se sustituyó el control histórico por una recomprensión más favorable.

## Ventaja WSP frente a cada control, %

| Archive | JSON | Payload | Full | zlib(payload) | zlib(full) |
|---|---|---:|---:|---:|---:|
| honesto-none-m1 | b64-rows | 11.933021 | 11.897991 | 1.812367 | 2.097902 |
| honesto-none-m1 | b64-columns | 5.001985 | 4.986150 | 19.352014 | 19.141914 |
| honesto-none-m1 | b85-columns | 3.663446 | 3.651685 | 5.441478 | 5.314010 |
| memory-training-m01 | b64-rows | 0.096388 | 0.096358 | -0.109047 | -0.082487 |
| memory-training-m01 | b64-columns | 0.011462 | 0.011458 | -0.033817 | 0.000000 |
| memory-training-m01 | b85-columns | -0.003821 | -0.003820 | -0.063895 | -0.018735 |
| oraculo-false_remote-m3 | b64-rows | 11.908554 | 11.872957 | 0.334448 | 0.314136 |
| oraculo-false_remote-m3 | b64-columns | 4.972711 | 4.956679 | 19.168174 | 18.213058 |
| oraculo-false_remote-m3 | b85-columns | 3.648289 | 3.636364 | 4.589114 | 5.084746 |
| prudente-false_safe-m1 | b64-rows | 11.929728 | 11.894718 | 1.039501 | 3.197674 |
| prudente-false_safe-m1 | b64-columns | 5.000496 | 4.984670 | 18.283262 | 18.912338 |
| prudente-false_safe-m1 | b85-columns | 3.662340 | 3.650587 | 5.084746 | 5.754717 |
| **Suma cuatro** | **b64-rows** | **2.890692** | **2.887997** | **0.003402** | **0.118008** |
| **Suma cuatro** | **b64-columns** | **1.122120** | **1.121055** | **2.121424** | **2.234250** |
| **Suma cuatro** | **b85-columns** | **0.804092** | **0.803326** | **0.440379** | **0.543880** |

En las tres sesiones, frente a base85 columnar, WSP ahorra aproximadamente 3,64–3,65 % sin comprimir y 5,08–5,75 % en full+zlib. La ventaja sin comprimir frente a base64 columnar ronda el 4,96–4,99 %, bastante menor que frente al hex32 previo. Estos son resultados de estas tres sesiones, sin extrapolación.

La memoria concentra 104716 de los 133361 bytes WSP completos. Allí base85 columnar gana por 4 bytes full y 5 bytes full+zlib; base64 por registro gana por 22 bytes full+zlib, y base64 columnar empata full+zlib. En zlib(payload) los tres JSON ganan a WSP: por 29, 9 y 17 bytes respectivamente (rows64, columns64, columns85). La suma zlib(payload) frente a b64-rows difiere únicamente en **1 byte** (29390 frente a 29391); no sostiene una ventaja práctica general.

## Verificación, recursos y custodia

Puerta técnica satisfecha: 9 pruebas pasan con fixtures, incluyendo archivos vacíos, preservación de bool/int/float/Unicode, SHA alterado en cada byte de fixtures pequeños, todos los truncamientos, sobrantes, esquemas y perfiles incorrectos, JSON ambiguo/no finito, UTF-8, base64/base85 no canónico, metadatos/longitudes, expansión zlib, sobrescritura y manipulación de artefactos/resultado/freeze. Se conservan los siete fallos iniciales por codec todavía inexistente y las ejecuciones posteriores; no se oculta una ejecución fallida.

La auditoría nueva reconstruye los 64 artefactos y los resultados desde los ocho controles congelados: **4 Archives, 64 artefactos, 0 diferencias**. Cada una de las 12 variantes JSON de cada Archive decodifica y vuelve a generar exactamente el `.wsp` original; esto comprueba la información completa más allá de la igualdad Python de valores. La auditoría usa el codec y el cálculo congelados; es una reconstrucción en proceso nuevo, no una segunda implementación independiente.

Solo stdlib, sin modelos, dependencias nuevas, red, mundos ni agentes. Unidades `echo58-wspstrongjson-{freeze,measure,audit}.service`, CPUQuota25 %, MemoryHigh192MiB, MemoryMax256MiB, Swap0, TasksMax16 y cuatro variables threads1. La suite final tuvo CPU0,576s y pico17657856 bytes; medición CPU0,996s/pico16908288 bytes; auditoría CPU1,038s/pico14475264 bytes. Son consumos de recursos de la ejecución, **no un benchmark de latencia**. Los recibos exactos quedan en resources/ y technical/.

Ruta de artefactos: `lab/echo58/wspstrongjson/20261023-r1/`; `freeze.json` incluye fuentes, tests, plan y los ocho controles, junto al manifiesto original. `events.jsonl` conserva preparación, freeze, medición y auditoría. No se han editado los originales WSPFILES, sus artefactos, los históricos, el roadmap ni el handoff global.

Comandos de reproducción (siempre en un directorio nuevo y con los límites anteriores):

```text
PYTHONPATH=.. python3 -m unittest tests.test_echo58_wspstrongjson
PYTHONPATH=.. python3 -m echoai.echo58.wspstrongjson.bench prepare <nuevo-directorio>
PYTHONPATH=.. python3 -m echoai.echo58.wspstrongjson.bench measure <nuevo-directorio>
PYTHONPATH=.. python3 -m echoai.echo58.wspstrongjson.audit <nuevo-directorio>
```

Hashes SHA256:

- Plan: `5f98b1108e7e1cffa9b62be240e32c7a0cd059be4337442edd9e1af91def649c`.
- Freeze: `69238adcea06efddffe58f0c1d4319e8a8cf6a405fc5a05ab6d4cdb5912310bf`.
- Resultado: `075d9796d63f26c0ddd34287ccaf2a8b54d46ff02b1c69f97cda04d61c98e92a`.
- Auditoría: `1213e8b4e8af3b0a99577916f986f113d433d9151874609adca138c904bf79c8`.
