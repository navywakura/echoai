# ECHO-4.5 — integración de memoria y resolución de rejillas

2 de octubre de 2026. Roger aplaza S6 y prioriza memoria, refinamiento,
síntesis, vistas, consistencia y guía de capacidad. Se han implementado y
medido candidatos conjuntos en CPU. **ECHO-4.5 sigue sin estar listo para
cierre, incluso dejando S6 aparte.** Hay avances verificables y un resultado
de seguimiento que no confirma la ganancia general en ARC.

| Componente | Implementación y resultado | Alcance del verde |
|---|---|---|
| Diario 3E → programas de rejilla | Recibos, restauración, comprobación exacta, supresión y recuperación integrados | ✅ Ingeniería; ✅ reutilización causal en cuatro familias sintéticas |
| Política adaptativa completa de 3E → ARC | No se han trasladado las decisiones aprendidas de verificar/escribir en aldea | ❌ Pendiente; importar la clase no demuestra esta transferencia |
| Refinamiento y síntesis | Caché de prefijos, restricciones inversas, priorización de relaciones y presupuesto por profundidad | ✅ Composición sintética; mejora en desarrollo ARC conocido, sin confirmación en seguimiento |
| Multi-view | Ocho vistas posibles, con presupuesto y coste explícitos | ✅ Implementado; ❌ ventaja adicional no demostrada; desactivado por defecto |
| Consistencia | Agrupa predicciones de programas que cumplen todas las demostraciones; informa ambigüedad | ✅ Implementado; ❌ ventaja adicional no demostrada |
| Guías 640 / 65.536 / 500.000 | Ajuste con los mismos 84 programas históricos, exportación y carga | ✅ Integración; ❌ 500k no supera a los otros tamaños ni a ausencia de guía en este candidato |
| Persistencia de aprendizaje | Orden de adquisición: nuevo archivo con programa verificado, linaje y guías actualizadas cuando conocen sus primitivas | ✅ Caso completo entre procesos distintos; no acredita automejora S6 |
| S6 | Fuentes, contratos y artefactos anteriores conservados | Aplazado por el propietario, sigue pendiente |

La memoria tiene un efecto causal medido. El solver descubrió ocho programas
a partir de demostraciones de adquisición; el generador no le entregó el
programa solución. En 64 instancias posteriores de las mismas cuatro familias,
con colores, posiciones, tamaños y orientaciones diferentes, memoria y reinicio
acertaron 64/64. La memoria redujo las aplicaciones de primitivas de 81.168 a
23.504: **71,04 % menos trabajo de ese tipo**. La búsqueda de adquisición costó
otras 10.417 aplicaciones; incluyendo esa búsqueda el ahorro es 58,21 %.
Esta última cifra no incluye como primitivas las consultas al diario,
serialización ni extracción de características; el tiempo CPU se registra
separadamente. No se presenta como ahorro universal de coste.

En composición, retirar sus dos recuerdos eleva el trabajo de 5.936 a 28.292;
retirar dos recuerdos de objetos lo deja en 5.860. Las tres condiciones aciertan
16/16. El efecto observado es ahorrar búsqueda. Sin memoria, el refinamiento
resuelve 16/16 composiciones frente a 0/16 al desactivarlo, manteniendo las
48 tareas simples. Otro proceso reprodujo exactamente las ocho adquisiciones
y las 320 resoluciones. Son instancias nuevas de familias conocidas; no son
nuevas familias de abstracción ni resultados ARC oficiales.

La revisión V2 conserva 64/64 con esos recuerdos. Sin ellos baja a 63/64 en
la repetición diagnóstica de esos mismos casos. Esto también queda registrado:
no se atribuye conservación universal al orden nuevo de búsqueda.

| Muestra pública | V1 con vistas | V1 sin vistas | V2 sin vistas | V2 sin refinamiento |
|---|---:|---:|---:|---:|
| Calibración, 16 ARC-1 + 16 ARC-2 | 0/32 | 0/32 | No medida | No medida |
| Desarrollo ARC-1 | 1/64 | 2/64 | 4/64 | 1/64 |
| Desarrollo ARC-2 | 0/64 | 0/64 | 0/64 | 0/64 |
| Seguimiento disjunto ARC-1 | No medida | 0/64 | 0/64 | 0/64 |
| Seguimiento disjunto ARC-2 | No medida | 1/64 | 1/64 | 1/64 |

El desarrollo tiene 128 ocurrencias y 124 IDs únicos: hay cuatro coincidencias
entre pools, ninguna acertada. El seguimiento tiene 128 IDs únicos, sin
solapamiento con esos 124 ni con los 84 usados para ajustar memoria/guías. Se
excluyó siempre la reserva del gimnasio. Son datos públicos de entrenamiento
que pudieron utilizarse en investigaciones previas; el seguimiento no es una
reserva secreta. La calibración de 32 está incluida en desarrollo, no se suma
como otros 32 casos independientes.

V2 se diseñó después de observar el desarrollo y se fijó antes de seleccionar
el seguimiento. En desarrollo añade dos aciertos ARC-1 sin perder los de V1:
3,125 % → 6,25 %, +3,125 puntos porcentuales. En seguimiento ambos aciertan
1/128 y ninguna ablación aporta aciertos adicionales. **No pasa el criterio
de promoción**, que exigía añadir al menos un acierto sin pérdidas. Se conserva
como candidato experimental utilizable. Los resultados oficiales históricos
31/400, 0/120 y 11/112 permanecen intactos y no son comparables directamente con
estas muestras y presupuestos.

El límite común es 2.000 programas distintos, profundidad cuatro, beam doce y
96 comprobaciones tras el primer programa exacto. Igualar programas no iguala
CPU: sobre el desarrollo, V1 sin vistas consumió aproximadamente 58,6 segundos
CPU acumulados y V2 116,4. V2 ejecutó 932.598 primitivas frente a 841.950. Es un
intercambio de coste por aciertos en desarrollo, sin ventaja confirmada en el
seguimiento. Con vistas V2 ejecutó 1.398.128 primitivas y mantuvo cuatro aciertos.
Los tiempos excluyen adquisición; esta queda registrada por trabajador.

El cambio útil identificado consiste en dar turno a las relaciones. Por ejemplo,
en una tarea de desarrollo V2 sintetizó:

```python
[
    ("recolor", 5, 2),
    ("recolor_by_size", 0, 1, "largest"),
    ("recolor_by_size", 0, 3, "smallest"),
]
```

Todos los ejemplos de demostración se ejecutan simbólicamente antes de admitir
un programa. La crítica usa desacuerdo de dimensiones, fracción de celdas
erróneas y diferencia de paleta. La caché distingue también los resultados
sobre entradas de consulta; dos programas no se fusionan solamente por coincidir
en las demostraciones. La memoria ordena sus recibos por similitud de rasgos
`1000 * |F ∩ M| // |F ∪ M|`, reputación y longitud. Cada programa recuperado debe
volver a pasar los ejemplos actuales. Ningún programa obtiene aceptación por
su reputación o por la puntuación de la guía.

Se reutilizan `remember`, `evidence`, `trust` y la supresión del diario original
de 3E. En este adaptador los recibos almacenados son éxitos comprobados, y su
trabajo se registra. **No se utiliza `choose/begin/charge/mature` para aprender
una política ARC de coste diferido**. Ese trabajo es necesario para afirmar
transferencia completa de EGO-MEMORIA-3E; el banco sintético actual acredita la
utilidad del mecanismo de recuerdos verificables.

Los módulos nuevos son `seed/arc_memory.py`, `seed/integrated_grid.py` y su
revisión `seed/integrated_grid_v2.py`. Las campañas y el seguimiento viven en
`integration_campaign.py`, `integration_revision.py`, `integration_transfer.py`
e `integration_followup.py`. El exportador V2 guarda 84 recibos y las tres guías,
con hashes del código y del estado. El candidato declara `release_ready:false`.
La guía está apagada por defecto en esta revisión porque no añadió aciertos;
puede activarse explícitamente para investigar. La consistencia permanece
activada y las vistas opcionales.

Desde la raíz del repositorio:

```bash
python3 -m seed.echo45_grid_v2 solve mi_tarea.json \
  --candidate lab/seed/integration-v2-20261002/candidate.json

# Opciones experimentales: --guide 640 | 65536 | 500000, --views, --no-memory, --first

python3 -m seed.grid_memory_update demostraciones.json \
  --candidate lab/seed/integration-v2-20261002/candidate.json \
  --output mi-candidato-aprendido.json

python3 -m seed.echo45_grid_v2 solve otra_tarea.json \
  --candidate mi-candidato-aprendido.json
```

El JSON usa `train` con pares input/output y `test` con entradas. Si el archivo
trae salidas de test, el solver las descarta en la frontera. La adquisición
requiere un programa exacto en demostraciones, nunca sobrescribe el padre y
rechaza las rutas de evaluación selladas y los IDs de reserva conocidos. No
garantiza que las predicciones nuevas sean correctas. Una ejecución completa
adquirió `crop_largest_any → rot90`, abrió otro proceso y resolvió otra instancia
con `memory_verified:1`. No se efectuaron llamadas al LLM ni gasto en GPU.

Quedan por resolver la transferencia de la política adaptativa completa, la
ventaja independiente de vistas/consistencia/guía y la ganancia ARC fuera de la
muestra usada para revisar el solver. La siguiente hipótesis debe ampliar la
representación de relaciones y composición general, con casos diagnósticos
nuevos y controles; aumentar el banco de pesos no añadió operaciones al DSL.
Las puertas ARC-2/3 y la integración general de 4.5 siguen pendientes. S6 volverá
después, según el nuevo orden, sin rebajar B1–B5.

Artefactos reproducibles:

- [Contrato general](ECHO45-INTEGRATION-DESIGN.md), [transferencia sintética](ECHO45-INTEGRATION-TRANSFER-DESIGN.md), [V2](ECHO45-INTEGRATION-V2-DESIGN.md), [seguimiento](ECHO45-INTEGRATION-FOLLOWUP-DESIGN.md).
- [Resultados y auditorías consolidados](../lab/seed/integration-closure-20261002/result.json).
- [Desarrollo V2](../lab/seed/integration-v2-20261002/primary-summary.json), [seguimiento](../lab/seed/integration-followup-20261002/run/primary-summary.json), [memoria](../lab/seed/integration-transfer-20261002/primary-summary.json).
- [Prueba de persistencia entre procesos](../lab/seed/integration-v2-20261002/deployment-check/query-prediction.json).
- [Validación local aislada](../lab/localdev/arc-integration-closure-r1-20261002/result.json).
- [Gráfica PNG](../lab/seed/integration-closure-20261002/integration-results.png) · [SVG](../lab/seed/integration-closure-20261002/integration-results.svg).

Para regenerar el recibo y las gráficas: `python3 -m seed.integration_report`.
La auditoría consolidada exige que cada replay esté terminado y que las 217
fuentes protegidas registradas al comienzo sigan iguales. Los diarios de
desarrollo usan el visor existente; no se ha creado otro bus de pensamientos.

La primera validación de cierre pasó sus 22 pruebas, pero el arnés registró
`CUSTODY_FAILED` porque el generador del informe se editó mientras se comprobaba
la copia. Se conserva ese recibo. La validación R1 se realiza con las ediciones
detenidas; no cambia ninguna fuente congelada del agente ni del experimento.
