# PCWORLD-1 · primer modelo local y reparación independiente

Estado: **diagnóstico y comparación principal terminados, auditorías válidas**.
Fuentes congeladas en `2b68216`, sin cambios durante los experimentos. El piloto
principal termina en **2/6 tareas para cada brazo**: no demuestra ventaja del
crítico ni del coordinador ECHO. ECHO-5.1 continúa en investigación.

## Preparación comprobada

- 162 tests PCWorld, 59 regresiones seleccionadas, cinco hallazgos importantes
  de revisión reproducidos y corregidos. S6 y los exámenes previos no se reabren.
- Runtime de Python 3.14 con 597 archivos y 35.758.080 bytes de archivo TAR.
  Snapshot: `77b6e8fe4c5377fc517fdb4a7342bd4a1ee4c7ccdbc24db1fb93573f2a32eca3`.
  Exportación/importación exacta; se rechazan enlaces, metadatos extendidos,
  rutas inseguras e identidades distintas. No hay `/usr` host en `repair-v1`.
- Qwen2.5-Coder-7B-Instruct, Q4_K_M, GGUF oficial verificado; revisión y SHA
  documentados en RUNBOOK.md. El 4B existente se conserva, no participa.
- Servidor llama.cpp local `b1-d230ddd`, CPU con cuatro hilos y offload apagado,
  un slot, contexto 4096. Temperatura 0,2; semilla 73 + índice de llamada;
  salida máxima 512 tokens. Mismas reglas para todos los brazos.
- Cada episodio tiene techo de 25.000 tokens totales, 50 herramientas,
  300 segundos CPU del candidato, 300 segundos de pared y dos consultas al
  crítico. No confundir la cuota de CPU del candidato con el servidor LLM:
  la inferencia se mide por separado en su cgroup.

## Diagnóstico completo con un fallo sembrado

En la fixture histórica `sum_positive`, el código inicial sumaba también
números negativos. El crítico Qwen propuso `[1,-2,3,-4,5]`; el programa devolvió
3 y la referencia independiente exigía 9. La contradicción quedó en los
recibos y el diario WSP/CAM. La propuesta siguiente corrigió el programa;
la aceptación volvió a ejecutar el contraejemplo además del resto de casos.

Resultado: **1/1 diagnóstico aceptado**, 3 llamadas, 1.704 tokens,
109,213 segundos de episodio, 0,895407 segundos CPU de código candidato,
1,168959 segundos CPU del supervisor. El servidor de inferencia consumió
421,990414 segundos CPU acumulados durante los 110,502 segundos de ejecución
externa; tiene cuatro hilos. Son magnitudes distintas, no ahorro energético.
La auditoría valida 51 recibos, cero discrepancias y `destroyed == 0`.

Este defecto lo introdujo el experimento. No es un error de una primera
propuesta del modelo y no se suma a la comparación principal. El diagnóstico
anterior falló por un input envuelto incorrectamente y consumió 332 tokens;
se conserva. La gramática se corrigió usando sólo el esquema público.
En otra calibración de intervalos, un input elegible no refutó al programa;
también se conserva y no se presenta como contraejemplo.

## Comparación principal

Seis familias nuevas respecto a las fixtures anteriores: unión de intervalos,
deduplicación estable de registros, normalización de rutas, CSV, paginación y
dependencias. Los defectos son inducidos y ejecutables. No se afirma que sean
issues reales de proyectos externos ni tareas de un benchmark oficial.

Cada familia tiene un ejemplo público y casos de evaluación que no entran en
los prompts. Las referencias viven fuera del workspace candidato. El oráculo
de intervalos fusiona componentes por solapamiento; el de dependencias enumera
órdenes posibles en el dominio acotado. No se importa código del candidato.

S tiene autorrevisión; I2 genera dos propuestas independientes y selecciona con
el ejemplo público; F usa crítico fijo; E usa el coordinador basal existente.
La biblioteca permanece vacía y la caché de propiedades apagada. Los cuatro
brazos usan el mismo servidor, límites y tareas; se ejecutan secuencialmente.
El orden fijo puede afectar tiempos por temperatura/carga y no sustenta por sí
solo una conclusión de eficiencia. Los presupuestos son techos, no un consumo
forzado idéntico.

La muestra es descriptiva: seis familias, una repetición, sin potencia para
acreditar superioridad general. La capacidad de un modelo para reparar estos
programas tampoco acredita una ventaja del coordinador ECHO. Faltan ablaciones
y confirmación independiente para separar esos efectos.

### Resultados por familia

Cada celda corresponde a un episodio; «pasa» significa que todas las entradas
finitas exigidas por esa tarea fueron comprobadas. No certifica todo su dominio.

| Familia | S: autorrevisión | I2: dos propuestas | F: crítico fijo | E: control ECHO |
|---|---|---|---|---|
| Unión de intervalos | Pasa | Pasa | Pasa | Pasa |
| Registros, conservar primera aparición | Falla | Falla | Falla | Falla |
| Normalización de rutas | Falla | Falla | Falla | Falla |
| Lectura de CSV | Falla | Falla | Falla | Falla |
| Paginación | Pasa | Pasa | Pasa | Pasa |
| Dependencias | Falla | Falla | Falla | Falla |
| Total | **2/6** | **2/6** | **2/6** | **2/6** |

Son ocho episodios aceptados de 24, pero únicamente dos familias resueltas por
cada brazo. Repetir una misma familia en cuatro brazos no crea cuatro tareas
independientes. Las diferencias emparejadas E−S y E−F son cero en esta muestra.

### Coste observado

| Brazo | Tokens totales | Llamadas LLM | Herramientas | CPU candidato (s) | CPU supervisor (s) | Pared episodios (s) |
|---|---:|---:|---:|---:|---:|---:|
| S | 6.102 | 12 | 110 | 3,553222 | 4,641598 | 438,682 |
| I2 | 4.126 | 12 | 124 | 3,741400 | 4,936691 | 331,900 |
| F | 6.088 | 12 | 110 | 3,584282 | 4,643949 | 432,021 |
| E | 6.096 | 12 | 110 | 3,589431 | 4,675378 | 438,996 |

Total: **22.412 tokens, 48 llamadas LLM y 454 herramientas**. La ejecución
externa duró **1.643,379 s (27 min 23 s)**, incluyendo preparación y generación
del resultado, sin la auditoría posterior. El modelo consumió **6.333,516824 s
CPU acumulados** en su servicio de cuatro hilos; su PID fue el mismo antes y
después. No se atribuye esa CPU al código candidato ni se omite del coste.

El pico de memoria del cgroup del servidor al final fue 4.480.942.080 bytes
(4,17 GiB). Es el máximo de vida del servicio, incluye cargos distintos del RSS
y no constituye una medición energética. Coste de API de pago: 0 €; electricidad
no medida. I2 gastó menos tokens en esta realización, pero la muestra pequeña y
el orden fijo no permiten afirmar una ventaja general de eficiencia.

Todos los episodios cerraron sus reservas sin sobrepasar cuotas. Consumieron
entre 607 y 1.258 tokens de su techo individual de 25.000; el agotamiento del
presupuesto no explica estos fallos. Ninguno agotó su tiempo de ejecución.

### Autopsia del resultado nulo

- **Registros:** las soluciones conservan el último valor de un ID duplicado;
  el contrato pide el primero. Con `b:2, b:3`, el verificador observa `b:3` y
  exige `b:2`. El crítico probó IDs distintos, que no refutan esa solución.
- **Rutas:** las propuestas eliminan separadores vacíos y puntos, pero dejan
  `..` intacto. `/a/../b` produce `/a/../b` en vez de `/b`.
- **CSV:** dividir por comas no interpreta comillas ni escapes y el recorte
  elimina espacios significativos. `"a,b",c` debe dar dos campos, no tres.
- **Dependencias:** la búsqueda en profundidad no detecta ciclos y no asegura
  el orden topológico lexicográficamente mínimo. Un bucle `a → a` devuelve
  `["a"]` cuando el contrato exige `null`.

Hubo 18 llamadas de crítica/autorrevisión: **15 inputs elegibles sin refutación
y tres inputs fuera del dominio**, estos últimos en rutas. Allí el modelo
copió la descripción del problema en el campo `input`; cumplió la estructura
JSON, pero no el dominio de rutas. Las tres se descartaron. El ensayo principal
retuvo **cero contraejemplos** y no llegó a una segunda propuesta de reparación
en S/F/E. I2 hizo sus dos propuestas iniciales independientes previstas.

No hubo errores técnicos de proveedor, parsing JSON o ejecución de los
candidatos; esto no equivale a propuestas semánticamente válidas. Los defectos
quedaron expuestos en la evaluación final, que nunca devuelve esos casos al
modelo durante el episodio. En esta muestra las políticas F y E recorrieron
la misma secuencia de operaciones; el resultado no aísla utilidad del control
basal ni de la memoria. El diagnóstico separado sí ejercitó un ciclo de
contraejemplo y reparación; no demuestra que el crítico lo descubra en familias
independientes.

Una limitación concreta del protocolo es su parada: tras pasar el ejemplo
público y no obtener una refutación en la revisión, acaba la adaptación aunque
quede presupuesto. El prompt de roles es mínimo: especificación, código,
evidencia y esquema. Estas observaciones justifican investigar instrucciones
explícitas de reparación y generación de casos límite, y una política de
continuación ante crítica inválida. **No justifican atribuir el fracaso al
número de parámetros ni alterar retrospectivamente las métricas.** La próxima
comparación debe aislar estas intervenciones y usar otros casos reservados.

### Auditoría y alcance del verde

La auditoría final valida **860 recibos, 24 episodios y cero discrepancias**;
las 29 fuentes del manifiesto permanecen idénticas. `destroyed == 0`, cero
llamadas LLM desde NEXUS-0 y cero fixtures de propuestas en este piloto. El
diagnóstico separado valida 51 recibos adicionales. La auditoría comprueba
custodia y reproduce propiedades sobre salidas registradas; no vuelve a
ejecutar los candidatos ni garantiza corrección universal.

El verde corresponde a aislamiento, runtime, contabilidad, custodia, conector
y ejecución comprobada del ciclo diagnóstico. **La ventaja científica de
ECHO-5.1 permanece pendiente.** Los 162 tests PCWorld y las 59 regresiones
seleccionadas no sustituyen esa comparación.

Resultados numéricos, costes por episodio, validación de críticas y hashes de
los artefactos: [LOCAL-PILOT-SUMMARY.json](LOCAL-PILOT-SUMMARY.json).
Estado por obligación: [CLOSURE-CHECKLIST.md](CLOSURE-CHECKLIST.md).

## Artefactos locales

- `artifacts/diagnostic-qwen-20261013-r2/`, su `-audit.json` y `-resources.json`.
- `artifacts/repair-pilot-20261013/`: comparación principal completa; sus
  `-audit.json` y `-resources.json` conservan la auditoría y la medición externa.
- `artifacts/local-model-20261013.json`: hashes, build y comando del despliegue.
- `artifacts/runtime-python314-20261013/` y su TAR: entorno restaurable.

Los directorios de ejecución contienen autoridad privada de recibos y están
excluidos de Git. No publicar sus claves. Para auditar, usar las mismas fuentes
congeladas; no reescribir manifiestos de las calibraciones anteriores.

Tras guardar resultados, auditorías y mediciones se detuvo el servidor local
del 7B. No quedan unidades de este piloto ejecutándose. Los pesos y el runtime
siguen disponibles; el modelo 4B previo se conservó porque no faltaba espacio.
