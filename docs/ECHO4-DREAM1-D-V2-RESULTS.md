# DREAM-D v2 — feedback y generalización diagnóstica

2026-09-22. **Implementación y campaña completadas; v2 roja, DREAM-1 abierto.**
Los criterios se fijaron en el [contrato v2](ECHO4-DREAM1-D-V2-DESIGN.md)
antes del examen. V1 se conserva roja y su auditoría ha vuelto a pasar sin
hallazgos; no se editan sus fuentes ni sus artefactos.

## Implementación

`dream_v2.py` reutiliza el intérprete y el replay sellados de v1. Añade
feedback de estrategias completas, selección por peor margen histórico y
promoción comparada tanto con el incumbente como con el fijo original.
El adaptador cortical conserva el backend local y permite hasta nueve
llamadas con recibos verificables. No altera pesos ni ejecuta código generado.

`dream_v2_bench.py` congela fuentes/particiones/modelo, realiza tres ciclos,
publica nueve brazos y conserva selecciones, decisiones y versiones antes
de incorporar nuevos casos al historial. El auditor reconstruye el banco
completo sin volver a inferir con Qwen.

En desarrollo, solo sobre los 320 casos ya abiertos de v1, el orden
`[2,4,0,1,3,5]` resuelve 255 casos frente a 210 del fijo. No se introduce ese
orden como candidato ganador manual: las estrategias evaluadas como DREAM
deben proceder de las respuestas reales de Qwen o del incumbente. Las seis
rotaciones históricas aportan un resumen inicial explícito, también disponible
para el control sin Qwen. No se atribuye ese catálogo escrito al modelo.

## Resultado de los tres ciclos

Las celdas son **aciertos / pasos de entorno**; 320 casos por ciclo y brazo.

| Brazo | Ciclo 1 | Ciclo 2 | Ciclo 3 | Aciertos / 960 |
|---|---:|---:|---:|---:|
| DREAM | 245 / 3040 | 245 / 3056 | 240 / 3048 | 730 |
| Incumbente | 205 / 2560 | 245 / 3056 | 240 / 3048 | 690 |
| Fijo | 180 / 3840 | 210 / 3840 | 200 / 3840 | 590 |
| Aleatorio | 206 / 3148 | 230 / 3140 | 238 / 3148 | 674 |
| Sin Qwen | 245 / 3040 | 245 / 3056 | 240 / 3048 | 730 |
| Sin feedback | 180 / 2912 | 245 / 3056 | 240 / 3048 | 665 |
| Sin historial en prompt | 180 / 2912 | 245 / 3056 | 240 / 3048 | 665 |
| Sin selección replay | 0 / 2560 | 0 / 2560 | 0 / 2560 | 0 |
| SELF activo existente | 210 / 3020 | 230 / 2912 | 250 / 2920 | 690 |

**Cero atribuciones erróneas, cero terminalidades, invariantes conservados y
paridad online/replay exacta** en los nueve brazos. Los demás casos son
desconocidos, no éxitos. Los candidatos se aceptan en el primer ciclo y se
conservan en los dos siguientes, sin regresión frente a incumbente o fijo.

| Criterio por ciclo | Ciclo 1 | Ciclo 2 | Ciclo 3 |
|---|---:|---:|---:|
| Ganancia vs fijo, mínimo +32 | +65, pasa | +35, pasa | +40, pasa |
| Ganancia vs aleatorio, mínimo +16 | +39, pasa | +15, falla | +2, falla |

**`criteria_passed=false`, `dream1_green=false`.** El agregado +140 frente al
fijo y +56 frente al aleatorio no sustituye la exigencia por ciclo. No se
redondea +15 a +16 ni se cambia el umbral. Se usan 9.144 pasos frente a los
11.520 del fijo, pero eso no compensa un criterio obligatorio fallido.

El feedback del primer ciclo contiene una propuesta real
`order=[4,5,0,1,2,3], step_budget=12`; se selecciona y permanece activa.
La primera ronda, sin feedback, seleccionaba una política de menor rendimiento.
No se observa una sucesión de mejoras ilimitadas: hay una promoción inicial
y dos conservaciones. El selector sin Qwen empata exactamente; no se ha
demostrado una ventaja exclusiva del LLM. SELF activo supera a DREAM en el
tercer ciclo, aunque queda por debajo en el agregado.

## Nuevo examen

Tres ciclos, 320 casos por brazo y ciclo: 16 cuerpos × 20 condiciones.
Dominio H65..96, theta40..60, cuatro cuerpos por banda H de ocho unidades,
seleccionados antes de ejecutar el examen y sin filtrar por resultados.
Se conserva la exigencia +10 puntos frente a fijo y +5 frente a aleatorio
en cada ciclo: +32/+16 aciertos. Es un muestreo estratificado nuevo, no una
réplica de las particiones v1, que tenían distinta banda corporal por ciclo.

Historial inicial: cuatro lotes v1, 320 casos, físicamente reconstruidos
desde sus recibos. Cada ciclo añade 320 casos después de evaluarlos.
Se prueban Qwen + feedback + replay, incumbente, fijo, aleatorio, sin Qwen,
sin feedback, sin historial en el prompt, sin selección y SELF activo.

Las ablaciones con cuatro frente a ocho propuestas confunden feedback con
número de candidatos; se reportan como diagnósticas, no como aislamiento
causal perfecto. Ganar al fijo y aleatorio tampoco implica ganar al control
sin Qwen. Una igualdad con este último limita cualquier atribución al LLM.

## Costes e identidad

- Qwen3-4B-Instruct-2507 Q4_K_M, 2.497.280.736 bytes; SHA-256
  `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
- llama.cpp `0.3.0-dev`, commit `d230ddd`, CPU con cuatro hilos, cero capas
  GPU, contexto8192, temperatura0 y pesos sin modificar.
- Nueve llamadas reales, 36 propuestas válidas (no todas distintas):
  11.623 tokens de entrada y 2.391 generados. Petición/respuesta acumulada:
  916.997 ms, más 4.011 ms de arranque. Servidor propio cerrado al terminar.
- Reutilizar v1 conserva su coste hundido. Además, `load_history` reconstruye
  sus 320 contextos: 14.080 pasos de colección y 1.152 nominales; esta
  comprobación física no se presenta como replay gratuito.
- Cada ampliación nueva: 320 contextos, 14.080 pasos de colección y 1.152
  nominales. Tres ampliaciones: 42.240 + 3.456 pasos. La referencia nominal
  se comparte con la evaluación online del mismo ciclo, no se cuenta dos veces.
- Nueve brazos online: 82.472 pasos. DREAM representa 9.144 de ellos.
- Selección/resúmenes replay: 38.514 consultas y 252.600 pasos representados,
  cero pasos físicos nuevos o llamadas al LLM durante esas consultas.
  Son 19/14/14 evaluaciones distintas de política por ciclo, incluidas
  ablaciones y controles; no son 47 estrategias globalmente distintas.

Auditorías, regresiones y diagnóstico posterior añaden cómputo aparte. Los
costes se reportan como vector, sin equiparar tokens a pasos o julios ni
afirmar ahorro total de energía/latencia frente a los controles sin modelo.

## Reproducción

[Informe de campaña](../lab/echo4/dream1-d-v2/report.json), con digest
`f5d36371c330c8d3ee439f3710391c744789a9026927b995aa1ae450fd4585ee`.
[Recibo reconstructivo](../lab/echo4/dream1-d-v2/audit-receipt.json):
**`valid=true`, cero hallazgos, `dream1_green=false`**. Reproduce las tres
etapas, selecciones, decisiones, versiones y trazas en proceso nuevo; audita
los recibos Qwen sin reinferir. Las 76 fuentes congeladas y todos los archivos
v1 vinculados siguen intactos, comprobados después de actualizar los docs.
El informe no concede verde; los hashes dan integridad local, no atestación
externa de un tercero. `git diff --check` pasa.

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_dream1_v2 -q
PYTHONPATH=.. python3 -m echoai.echo4.dream_v2_bench verify lab/echo4/dream1-d-v2
```

La campaña local opt-in usa `campaign` y exige un directorio inexistente:

```bash
PYTHONPATH=.. python3 -m echoai.echo4.dream_v2_bench campaign lab/echo4/dream1-d-v2-reproduction \
  --server /home/roger/src/llama.cpp/build/bin/llama-server \
  --model /home/roger/models/qwen3-4b-instruct-2507/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
  --threads 4
```

Repetirlo reproduce un protocolo conocido, no crea un holdout independiente.
Los recibos registran la inferencia observada, sin prometer que otra versión
de backend produzca exactamente los mismos tokens o tiempos.

## Diagnóstico posterior del segundo ciclo (no criterio de aceptación)

Tras abrir el segundo examen, DREAM obtiene 245/320 y el aleatorio 230/320.
Hacían falta 246 para satisfacer +16. Se enumeraron por replay las seis
pruebas individuales y las diez secuencias de dos pruebas que caben en
12 pasos. Los 320 contextos tienen registradas las seis ramas del catálogo.

| Secuencia | Aciertos / 320 |
|---|---:|
| 0 | 0 |
| 1 | 136 |
| 2 | 146 |
| 3 | 180 |
| 4 | 196 |
| 5 | 210 |
| 0→2 o 2→0 | 210 |
| 1→2 o 2→1 | 230 |
| 3→2 o 2→3 | 230 |
| 4→2 o 2→4 | 245 |
| 5→2 o 2→5 | 230 |

Máximo de un programa fijo: **245**. Unión de los casos resueltos por
cualquiera de los 16 programas, permitiendo elegir retrospectivamente el
mejor con acceso a la verdad: **245**, no 246. Ese selector retrospectivo
es una cota diagnóstica, no un controlador permitido ni un nuevo resultado
de Qwen. Todos estos replays tienen cero atribuciones erróneas/terminalidades.

Dentro del contrato hay cinco ensayos de ocho pasos y uno de cuatro; no
se permiten repeticiones. Con 12 pasos solo cabe uno de los ensayos largos
y el corto, en cualquier orden, o un subconjunto. La lista cubre esas
trayectorias posibles en este banco con restauración. Incluso una elección
adaptativa entre ellas no supera su unión. **Otro prompt u otra permutación
del catálogo no puede aportar aquí el acierto que falta.** No es una cota
para otros catálogos, presupuestos, sensores o mundos.

Para reproducir la cota sin inferencia (incluye recalibración de las
referencias de los cuerpos ya examinados, además del replay):

```python
import json
from itertools import permutations
from pathlib import Path
from echoai.echo4.dream_bench import evaluate
from echoai.echo4.dream_policy import Policy
from echoai.echo4.dream_probe import ProbeArchive, prepare
from echoai.echo4.self_attribution import CATALOG
from echoai.echo4.world import Body

path = Path("lab/echo4/dream1-d-v2/history-online-1.json")
rows, prepared = [], {}
for item in json.loads(path.read_text()):
    body = Body(**item["private_context"]["body"])
    if body not in prepared:
        prepared[body] = prepare(body)
    rows.append((body, tuple(item["private_context"]["condition"]),
                 prepared[body], ProbeArchive(item["archive"])))
covered = set()
for size in (1, 2):
    for seq in permutations(range(6), size):
        if sum(len(CATALOG[i]) for i in seq) > 12:
            continue
        order = seq + tuple(i for i in range(6) if i not in seq)
        policy = Policy(order, tuple(int(i in seq) for i in range(6)))
        outcomes = evaluate(policy, rows, replay=True)
        found = {i for i, row in enumerate(outcomes) if row["correct"]}
        covered.update(found)
        print(seq, len(found))
print("Cota retrospectiva:", len(covered))  # 245, no un controlador
```

Esto orienta el siguiente incremento hacia ensayos más informativos con
seguridad/observabilidad verificadas, no hacia mover semillas o rebajar el
umbral. Hará falta un contrato nuevo y un examen nuevo; v2 no cambia de color
por este análisis posterior.

## Verificación de código

891 pruebas distintas: **890 aprobadas y un fallo esperado histórico**.
20 nuevas de v2, 30 de DREAM-B/C/D v1, 583 de DREAM-A/SELF-B/CONT-A/NEXUS-0/Q,
y 258 de CONT-B/C/D, SELF final, WORLD, SENSATION y BOUNDARY. Las pruebas GUI
se ejecutaron con permiso de loopback y no tuvieron errores de sandbox.
V1 se volvió a auditar en proceso nuevo: válida, cero hallazgos y roja.
No se afirma que estos grupos sean toda la suite histórica del repositorio.

## Siguiente: DREAM-D v3 (PLAN, no implementado)

Antes de otro examen, desarrollar ensayos más informativos que separen las
hipótesis todavía indistinguibles, manteniendo seguridad bajo todo el prior
y el presupuesto declarado. Contrastarlos con un selector adaptativo y con
el control sin Qwen. Si es necesario cambiar catálogo, horizonte o protocolo
de recibos, hacerlo en una versión nueva; no modificar SELF ni la evidencia
sellada para acomodar el resultado. Congelar entonces otro contrato y casos
nuevos. Los casos v2 abiertos ya son desarrollo, no nueva confirmación.

## Límites que no cambian

Ensayos restaurados con física/prior SELF conocidos; el laboratorio realiza
calibración y restauración. No es reparación autónoma ni una vida continua.
No hay evidencia de conciencia subjetiva, entrenamiento de pesos ni mejora
general en problemas arbitrarios. El núcleo sigue sin LLM, WSP sigue midiendo
16 bytes y las propuestas no crean hechos CAM. La integración de producto
sigue perteneciendo a INTEGRATE; hardware posterior y METAVERSE-1 último.
Los veinte casos por cuerpo comparten estado inicial y no son muestras
independientes para inferencia estadística. Los umbrales son de un banco
finito preregistrado, no estimaciones universales con intervalos de confianza.
Sin Discord, publicación web, commit ni push en esta entrega.
