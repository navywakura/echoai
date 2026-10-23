# Qwen 32B y memoria compartida · resultados 0.10

Con el 32B se resolvieron CSV y Dependencias en este piloto. **S, F, E y E con
memoria compartida terminaron en 12/12; I2, en 10/12.** No se rompió el empate
E/F: el agente único con autorrevisión también alcanzó el máximo y gastó menos.
La biblioteca evitó cuatro reparaciones, pero su adquisición todavía no se
amortizó en estos doce receptores. ECHO-5.1 no queda cerrado científicamente.

## Ejecución comprobada

13 de octubre de 2026, rama local `research/echo-5.1-pcworld1`, código congelado
`c25c103792bf03d4197c6e159547482b15073e3e`. Sin push ni publicación.
[Plan previo](SCALING32-PLAN-20261013.md),
[orquestación](../../pcworld/scaling.py),
[perfil GPU](../scripts/kaggle_repair_worker.py).

- 255 tests PCWorld pasan en 97,446 s antes del lanzamiento.
- 66/66 episodios ejecutados: seis donantes y doce tareas por cinco condiciones.
  Donantes aceptados 6/6; receptores 58/60. Las puntuaciones de los brazos se
  calculan solo sobre sus doce receptores.
- Auditoría integral y repetición en un proceso nuevo: ambas `valid: true`,
  sin diferencias. El contador del auditor es 3.359 registros de episodios y
  estudio; incluyendo las cabeceras de custodia de ejecuciones y bibliotecas,
  hay 3.495 registros en 135 diarios autenticados.
- Las 32 fuentes del manifiesto de arranque permanecen intactas; cada ejecución
  también verifica su manifiesto de fuentes. Los seis archivos descargados de
  Kaggle coinciden con el manifiesto enviado, incluido el input privado.
- Cero errores de episodio, timeouts, excesos de presupuesto; `destroyed == 0` en
  memoria. Los dos fallos de I2 son contradicciones semánticas comprobadas.
  Las 630 solicitudes de inferencia/transporte registradas respondieron HTTP 200.
- Las ejecuciones de código candidato siguieron en Bubblewrap/cgroup/rootfs
  local. Kaggle ejecutó únicamente inferencia; no recibió autoridad de verificador.

Notebook **privado**: `navywakura/echo51-scaling32-20261013`, versión 1.
Kaggle terminó `COMPLETE`; worker `stopped: true`. Supervisor, relay, túnel y
observador de cola inactivos. El mini terminal solo conserva el diario visible.

## Modelo y recursos

[Qwen2.5-Coder-32B-Instruct-GGUF oficial](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF),
Q4_K_M, revisión `9d3053fce650fe1cdbdb75998c2a87add9d178ef`.
Archivo de 19.851.335.872 bytes; SHA256
`4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085`.
llama.cpp b11577, contexto 4096, salida máxima 768, temperatura 0,2, seed 73 más
índice de llamada, un slot. No se modificaron los pesos del modelo.

La carga real fue **65/65 capas GPU**, repartidas explícitamente entre dos T4.
Buffers de pesos: CUDA0=9.211,25 MiB; CUDA1=9.297,10 MiB. Uso observado tras cargar:
10.197 y 10.167 MiB respectivamente. Esto demuestra que esta configuración cabe;
no presupone que cualquier contexto, lote o cuantización tenga el mismo consumo.

- Preparación del worker: 391,855 s, unos 6 min 32 s.
- Worker completo: 3.711,017 s, unos 61 min 51 s, sin contar la cola previa.
- Suma de tiempos de los 66 episodios: 3.223,640 s. Preparación, auditorías y
  coordinación exterior se informan aparte; no son equivalentes a tiempo de GPU útil.
- Cuota reportada: 23,98 h antes, **22,94 h después**; consumo aproximado 1,04 h.
- Trabajo total ejecutado: 179.731 tokens, 210 llamadas LLM y 1.756 operaciones,
  incluidas las dos publicaciones. No son medidas de energía eléctrica.

Kaggle estuvo unos 16 minutos en cola. Antes de iniciar cualquier episodio se
separó esa espera del plazo de 1.200 s para cargar el modelo. Al reiniciar hubo
que recrear la unidad transitoria de systemd, ya descargada; se corrigió con el
mismo comando congelado. La consulta de logs de Kaggle también devolvió HTTP 500
mientras estaba en cola; el flujo de inferencia posterior no tuvo ese error.
No se reenvió el notebook ni se repitieron selectivamente episodios.
Estos eventos constan en `queue-adjustment.json` y `queue-release.json`.

## Resultado por brazo

La columna 14B procede del [piloto 0.8](PROBE-CONTENT-RESULTS-20261013.md).
Es una comparación histórica descriptiva: el 32B usa ambas GPU y todos sus
receptores pagan una consulta de biblioteca adicional. Cambió la versión de
orquestación, aunque se conservaron plantillas de prompts, aceptación, tareas objetivo,
catálogo, muestreo y límites de episodio. No aísla causalmente solo el tamaño
ni permite equiparar el coste físico de ambos modelos.

| Condición | 14B histórico | 32B actual | Tokens de receptores | Llamadas LLM | Reparaciones | Herramientas |
|---|---:|---:|---:|---:|---:|---:|
| S, único con autorrevisión | 6/12 | 12/12 | 20.074 | 28 | 4 | 246 |
| I2, dos propuestas independientes | 6/12 | 10/12 | 9.668 | 24 | 0 | 250 |
| F, especialistas con orden fijo | 8/12 | 12/12 | 44.621 | 47 | 4 | 356 |
| E, router adaptativo sin biblioteca | 8/12 | 12/12 | 42.795 | 46 | 4 | 380 |
| E_shared, mismo E con biblioteca | No comparable | 12/12 | 40.254 | 42 | 0 | 336 |

S sí realiza autorrevisión. Su contador de llamadas al rol separado `critic` es
cero; eso no significa ausencia de crítica. También encontró y reparó los cuatro
fallos de Registros/Dependencias. I2 falló ambas variantes de Registros: conservó
el último elemento de una clave duplicada en vez del primero, pasando 2/4 casos
finales en cada una. No fue un fallo de formato o infraestructura.

| Familia, dos variantes cada una | S | I2 | F | E | E_shared |
|---|---:|---:|---:|---:|---:|
| Intervalos | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| Registros | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 |
| Rutas | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| CSV | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| Paginación | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| Dependencias | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |

En el candidato E de CSV00, la solución usa `csv.reader`. En Dependencias00,
la reparación mantiene grados de entrada y ordena la frontera disponible antes
de cada extracción; devuelve `None` al detectar un ciclo. No usó `heapq` en ese
candidato. Se observó código que pasa los casos finitos del contrato, no una
prueba de que el modelo haya memorizado un algoritmo ni de corrección universal.

E/S, E/F y E_shared/E tienen doce empates de aceptación. E gasta 4,09% menos
tokens que F, pero 6,74% más herramientas. S alcanza el mismo 12/12 con 53,09% menos
tokens que E, menos llamadas y menos herramientas. Este resultado no demuestra
una ventaja específica del router ni de los especialistas sobre el agente único.

## Qué aportó la biblioteca

Los seis donantes fueron variantes 03; los receptores, variantes 00/01 de las
mismas seis familias. Se usó `repair-v2`, un corpus de bugs inducidos, sin forzar
manualmente la primera propuesta del LLM mediante `seeded_diagnostic`. Los
oráculos finales no se enviaron al proponente ni al crítico.

Registros03 y Dependencias03 pasaron después de una reparación: esas dos recetas
se publicaron con autor, contrato, fuente, AST y recibos de refutación/reparación.
Los otros cuatro donantes pasaron sin reparar y no cumplieron el filtro de
publicación de esta versión. No es evidencia de incapacidad en esas familias.
La biblioteca quedó congelada antes de evaluar receptores y no recibió sus resultados.

Cuatro receptores obtuvieron una receta compatible y los cuatro pasaron sin
reparar; E sin memoria necesitó una reparación en cada uno. Registros reutilizó
el código literalmente; Dependencias produjo el mismo AST, con diferencias de
formato. La procedencia y entrega están registradas, y los candidatos se
verificaron de nuevo. Es reutilización entre variantes del mismo contrato, no
extracción de una abstracción parametrizada. La coincidencia de código por sí
sola no prueba influencia; también puede aparecer sin una receta.

En las otras ocho tareas no hubo receta compatible. Sus diferencias pequeñas
no se atribuyen al contenido de una memoria: muestreo y contextos no garantizan
respuestas byte a byte idénticas aunque se declare la misma semilla.

Coste marginal de los doce receptores E_shared frente a E:

- Aceptación: 12/12 frente a 12/12; reparaciones: 0 frente a 4.
- Tokens: 40.254 frente a 42.795, **−5,94%**.
- Llamadas LLM: 42 frente a 46; herramientas: 336 frente a 380, **−11,58%**.
- Tiempo sumado de episodios: 590,752 frente a 661,327 s, −10,67% en esta ejecución.
- Las críticas se conservaron: 30 llamadas al rol crítico en cada condición.
  No se obtuvo el supuesto ahorro de «cero críticas».

Coste completo, sin ocultar adquisición:

| Componente de E_shared | Tokens | Llamadas LLM | Herramientas |
|---|---:|---:|---:|
| Seis donantes, incluidos los cuatro sin publicación | 22.319 | 23 | 186 |
| Dos publicaciones | 0 | 0 | 2 |
| Doce receptores | 40.254 | 42 | 336 |
| Total | **62.573** | **65** | **524** |

Las publicaciones sumaron 0,451377 s de pared y 0,401665 s de CPU. Las consultas
y los tokens de las recetas ya están dentro del coste de receptores: no se
suman otra vez. Frente a E sin adquisición, el total cuesta **46,22% más tokens**.
El ahorro marginal no amortiza aún la biblioteca; no se anuncia un ahorro global.
La cuota común se aplicó a cada receptor; la condición completa tuvo seis
episodios adicionales de adquisición, cuyo coste se muestra explícitamente.

## Checklist de ECHO-5.1 tras esta tanda

| Estado | Componente | Comprobado o pendiente |
|---|---|---|
| [x] Verde de implementación | Frontera Linux y contabilidad | Bubblewrap/cgroup, límites y recibos; sin fallback. Se mantiene la separación de NEXUS-0. |
| [x] Verde acotado | T08, entorno hermético | Rootfs Python fijado; no monta `/usr` host. Kernel/hardware y reproducción en otro equipo siguen fuera de esa identidad. |
| [x] Verde acotado | T10, caché pura | Implementada y ensayada previamente; desactivada en esta matriz. Los candidatos siempre se ejecutan. |
| [x] Verde | Proveedores 7B/14B y perfil 32B | 32B real, identidad comprobada y dos GPU usadas; mismos límites declarados. |
| [x] Verde acotado | T12, crítica y reparación | Catorce episodios de esta tanda completan una reparación verificada. Sin minimización automática de contraejemplos. |
| [x] Verde acotado | CSV y Dependencias con 32B | Ambos 2/2 en los cinco brazos. No reescribe los fracasos históricos del 14B. |
| [x] Verde de implementación | T20, publicación/recuperación persistente | Dos recetas con procedencia; cuatro receptores compatibles pasan sin reparar. |
| [x] Verde de ejecución | Matriz 0.10 y auditoría | 66 episodios, dos auditorías válidas, fuentes intactas y 255 tests. |
| [ ] Parcial | H2, utilidad neta de memoria | Evita cuatro reparaciones, con ahorro marginal; coste completo mayor. Falta confirmar amortización, transferencia negativa, controles de biblioteca fija y adquisiciones repetidas. |
| [ ] Parcial | T20, conceptos y transferencia general | Misma familia/contrato y AST; faltan adaptación de recetas, abstracción parametrizada, promoción/cuarentena integrada y varias generaciones. |
| [ ] Pendiente | H1, especialistas frente a único fuerte | Empate 12/12 con 32B; S resulta más barato. El resultado 14B anterior sigue siendo desarrollo, no confirmación independiente. |
| [ ] Pendiente | H3, utilidad neta del crítico | Esta matriz no aísla el crítico manteniendo todo lo demás idéntico; S también tiene autorrevisión. |
| [ ] Pendiente | H4, router E frente a F | Empate; menos tokens pero más herramientas. Falta controlar ambigüedad de categoría heredada y confirmar en tareas nuevas. |
| [ ] Pendiente | Defectos heredados del protocolo | Alinear guía/detector de `disconnected-lex-order` y corregir el atractivo de `format.content` en una tanda nueva, conservando estos resultados. |
| [ ] Pendiente | Confirmación independiente | Familias/bugs externos, varias semillas y donantes, controles fuertes, muestra y contrato fijados antes de medir. |
| [ ] Pendiente | Release reproducible | Instalación/restauración en otra máquina y preparación de artefactos publicables sin credenciales. |
| Aplazado | S6 | No se reabre; permanece fuera de esta etapa. |

Seis familias conocidas, dos variantes por familia y una semilla no equivalen a
sesenta problemas independientes. H1–H4 y el cierre general de ECHO-5.1 siguen
abiertos. No se alteraron presupuestos o aceptación para forzar una victoria.

## Evidencia conservada

Todo en `ECHO-5.1/artifacts/`, ignorado por Git:

- `scaling32-pilot-20261013/`: contrato, resultado, auditoría, ejecuciones y bibliotecas.
- `scaling32-control-20261013/`: manifiesto de arranque, tests, evidencia GPU,
  transporte, análisis final, auditoría repetida, verificación y cierre.
- `kaggle-scaling32-output/`: fuentes y logs remotos, reporte de GPU.

Los directorios de control y Kaggle son privados; contienen material de custodia
o credenciales de transporte y no se publican en bruto.

| Archivo del estudio | SHA256 |
|---|---|
| `contract.json` | `c3c4867060bbb37b8da5d927bae21a4b98b5db12941e0516750ba5b589da3244` |
| `result.json` | `c240adba5c318d60e5ef77856d7edd4edc57b784ed60bb4c2a95ac115c20f476` |
| `audit.json` | `065167a5d112aa2491feef3a5404d3884ff393b07f9c2fdf50ac3dc5493215a5` |

El reporte remoto de GPU tiene SHA256
`0018c0f3cc59848239a907b882e3c8d73b236c7263bb708ce2ffd17a0479dba3`.
