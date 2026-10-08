# E4-SELF-1 / SELF-B — atribución condicionada y ensayos discriminantes

2026-09-21. **Entregable diagnóstico implementado; E4-SELF-1 sigue abierta.**
El [contrato previo](ECHO4-SELF1-B-DESIGN.md) pasa su censo de desarrollo:
7.920/7.920 atribuciones correctas, cero errores, cero desconocidos y cero
terminalidades con el selector activo. No es un examen B/C reservado ni
una demostración de conciencia, causalidad general o recuperación autónoma.

## Qué cambia respecto a SELF-A

[SELF-A](ECHO4-SELF1-A-RESULTS.md) encontró causas indistinguibles con sus
dos pares cortos de intervención/espera. Ese resultado se conserva intacto.
SELF-B añade una referencia nominal de ocho esperas, medida antes del fallo,
y elige entre seis secuencias de diagnóstico. Predice cada secuencia antes
de ejecutarla y descarta las hipótesis incompatibles con los WSP posteriores.

Solo emite `nominal`, `own`, `external` o `mixed` cuando todos los candidatos
restantes coinciden. Con evidencia insuficiente, contradictoria o recibos
inválidos devuelve `unknown`. No recibe la causa ni el cuerpo exacto del juez.

**Supuesto material:** conoce la transición nominal WORLD-1 y su encoder,
la independencia de los canales, los dos estados posibles de cada
acoplamiento y un pulso externo en {-16, -4, 0, 4, 16} al primer tick.
La calibración nominal y la restauración del mismo estado oculto son
garantías del ejecutor. La solución es inferencia dentro de ese modelo
declarado, no descubrimiento autónomo de sus leyes. La nueva observación
y ese prior son parte de la explicación del resultado.

## Censo y controles ejecutados

396 cuerpos iniciales: H=29..40 y temperatura=40..72. Cada uno se evalúa
con cuatro configuraciones de acoplamiento y cinco pulsos: 7.920 condiciones
por controlador. Se conserva el mismo censo público de desarrollo de SELF-A.

| Controlador | Correctas | Desconocidas | Erróneas | Pasos de diagnóstico | Ensayos | Máximo pasos/ensayos por condición |
|---|---:|---:|---:|---:|---:|---:|
| Activo | 7.920 | 0 | 0 | 66.660 | 8.745 | 12 / 2 |
| Orden fijo seguro | 7.920 | 0 | 0 | 133.320 | 17.490 | 20 / 3 |
| Activo sin referencia larga | 6.288 | 1.632 | 0 | 130.360 | 17.338 | 44 / 6 |
| Solo esperar ocho ticks | 0 | 7.920 | 0 | 63.360 | 7.920 | 8 / 1 |

El activo empata en precisión con el orden fijo y usa **50% menos pasos y
ensayos de diagnóstico** en este censo. No se afirma mayor precisión ni
optimalidad global: el selector solo compara el catálogo fijado.
La referencia larga elimina aquí 1.632 abstenciones respecto a su ablación.
Esperar no identifica por sí solo la capacidad de ejecutar carga/enfriamiento.

Los costes de la tabla excluyen la calibración compartida: 64 transiciones
nominales de los pares cortos más ocho de la referencia larga por cuerpo,
72 en total. La ablación utiliza solo los pares cortos; no recibe la
referencia larga. Cada ensayo implica una restauración experimental explícita,
no una reanimación gratis en una vida autónoma. No se ha medido una ventaja
de latencia, consumo eléctrico ni memoria total del proceso Python.

Desglose del activo:

| Causa privada del evaluador | Correctas / total |
|---|---:|
| Nominal | 396 / 396 |
| Propia | 1.188 / 1.188 |
| Externa | 1.584 / 1.584 |
| Mixta | 4.752 / 4.752 |

El testigo anterior H=37/temperatura=65 se resuelve para las cuatro causas
en un ensayo de ocho pasos (`22122222`). El agente no recibe esos valores
exactos. La referencia nominal acota las posiciones compatibles dentro de
las bandas sensoriales; la intervención posterior separa las causas.

## Integración y límites de memoria

- `self_attribution.py`: hipótesis factorizadas y selección entera por peor
  ambigüedad restante; sin acceso al ejecutor ni etiquetas del evaluador.
- `self_probe_agent.py`: integración opt-in sobre `SelfAgent`, con su misma
  CAM/BOUNDARY/referencia. No cambia la política ordinaria ni el loop T.
- `self_probe_world.py`: ejecutor experimental separado; acciones originales,
  gate original, parada ante veto o terminalidad y recibos de ejecución.
- `self_probe_audit.py`: censo, controles, manifiesto, trazas y replay completo.

Límites: 64 candidatos H, 160 térmicos y hasta 1.792 códigos de previsión
pendiente. El producto de estados no se materializa; no se acumula historia
en el consumidor. En el censo, incluyendo la ablación, se observaron máximos
de 46 y 80 candidatos respectivamente. Se examinan hasta seis planes al
seleccionar; las cotas anteriores no son una medición de bytes/RSS total.

Referencia nominal y CAM conservadas en 396/396 calibraciones; cero hechos
añadidos y cero slots destruidos. Las hipótesis verdaderas sobreviven en
las 7.920 condiciones de cada controlador. No se modifica WSP16, Q/T,
kernel, certificados anteriores ni se añade un LLM o un segundo bus.
Esta conservación de lectura **no** demuestra aún protección selectiva de
T mientras el agente aprende y actúa: eso sigue pendiente.

## Verificación y reproducción

28 pruebas nuevas; **236 pruebas seleccionadas pasan** con las regresiones
de SELF-A, BOUNDARY, SENSATION, WORLD, Q, HEAT, ECHO-2 y partes de NEXUS-0.
Se prueban, entre otros, predicción previa, ambigüedad, contradicción,
recibos incompletos/repetidos/vetados, safety durante todo el horizonte,
integración compartiendo CAM, no sobrescritura y alteración de evidencia.

Artefactos: [informe](../lab/echo4/self1-b-v1/report.json),
[trazas](../lab/echo4/self1-b-v1/traces.jsonl) y
[recibo de auditoría](../lab/echo4/self1-b-v1/audit-receipt.json).
El replay en proceso nuevo reproduce el informe y todas las trazas sin
hallazgos. Identidad de reproducción:

```text
06fae2d4da1513243d64fb33b14c8c945d3be0f9a450363e1c109798f4ffd0a3
```

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_self1b -v
PYTHONPATH=.. python3 -m echoai.echo4.self_probe_audit verify lab/echo4/self1-b-v1
```

Para repetir el censo guardando nuevos artefactos, `census` exige una ruta
nueva. No reutilizar ni sobrescribir `self1-b-v1`.

También se han reproducido sin hallazgos SELF-A (`eeb52994…`), BOUNDARY
(`48789bd5…`) y SENSATION (`96f2deae…`) con sus fuentes selladas intactas.
`diagnostic_checks_passed=true`; **`self1_green=false`**.

## Qué falta y siguiente paso

**SELF-C:** conectar el diagnóstico a decisiones y aprendizaje comprobables,
preservando conocimiento no refutado. Primero fijar su contrato: tareas
viables bajo la alteración, controles sin atribución y con atribución
indiscriminada, coste de diagnóstico, política/gate y métricas de recuperación.
No exigir recuperación imposible ni atribuir reparación física a una etiqueta.

Después quedan exámenes nuevos B/C, negativos y ablaciones para el cierre
completo de E4-SELF-1. Este censo ya visto no se convertirá en evidencia
reservada mediante un cambio de nombre.

Fuera del prior puede haber anomalías detectables, pero una causa externa
que imite exactamente un fallo corporal puede seguir siendo indistinguible.
No se garantiza reconocer toda perturbación desconocida. Tampoco se ha
demostrado aprendizaje autónomo de física, experimentación sin restauración,
supervivencia mejorada, continuidad, contraparte ni conciencia.

El [roadmap](ROADMAP.md) mantiene hardware después del software y METAVERSE-1
al final.
