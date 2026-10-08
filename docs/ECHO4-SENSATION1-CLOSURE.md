# E4-SENSATION-1 — cierre verde de predicción sensorial

2026-09-21. [Contrato predictivo v1](ECHO4-SENSATION1-PREDICTOR-V1.md).

**Cerrada en su alcance declarado:** aprender a predecir el siguiente WSP
del cuerpo virtual WORLD-1 usando historia observable, con incertidumbre
separada del error. No demuestra mantenimiento, causa propia/externa,
conciencia, eliminación del aliasing ni una mejora de la política Q.

## Implementación y encaje

`SensationPredictor` reutiliza CAM, World/T y PatternMemory originales.
El registro temporal identifica historias exactas; no añade un segundo bus,
otra CAM o un controlador. El primario recuerda dos transiciones (50 bytes
de ventana), aprende reglas tras ocho repeticiones y retira la respuesta
temporal ante contradicción. Si no hay regla, recurre a T con su confianza.

`SensationAgent` lo conecta a `_predict` del Agent existente. La predicción
se obtiene después del gate, para la acción ejecutada, y antes de la física.
Comparar contra la consecuencia precede al aprendizaje temporal. Se usan
las mismas CAM y T que el Agent; Q, gate y WORLD-1 no se modifican.

Las cuatro etiquetas (esperada, desviación pequeña, grande, incertidumbre)
resumen error de código sensorial y confianza. No identifican una causa ni
se han validado como detector general de fallos. En esta campaña nominal
no hubo errores de confianza alta clasificados como desviación grande;
esa rama se comprueba con pruebas unitarias, no con fallos físicos reales.

El examen congelado usa el predictor autónomo con los mismos componentes;
no se llama «congelado» al Agent, cuyo aprendizaje Q/T continúa. La conexión
real se verifica aparte durante cuatro vidas explícitas, 118 transiciones
y tres reinicios. La primera vida conserva las 37 acciones del baseline.

## Examen prospectivo

8.192 episodios de entrenamiento, 104.705 transiciones. Luego B y C,
2.048 episodios cada una, hasta 24 acciones y final al morir. Arranques
particionados y nuevas secuencias de acciones; ninguna selección por éxito.
Semillas públicas prospectivas, no custodia ciega. Se generaliza a otras
trayectorias del mismo mundo, no a leyes físicas nuevas.

| Medida | Validación B | Confirmación C |
|---|---:|---:|
| Transiciones evaluadas | 25.781 | 26.030 |
| Aciertos T instantánea | 21.834 | 22.215 |
| Aciertos historia 2 | 22.052 | 22.418 |
| Precisión T | 84,6903% | 85,3438% |
| Precisión historia 2 | 85,5359% | 86,1237% |
| Mejora absoluta | +0,8456 puntos | +0,7799 puntos |
| Victorias / pérdidas emparejadas | 218 / 0 | 203 / 0 |
| Episodios ganados / perdidos | 165 / 0 | 158 / 0 |
| Cobertura de predicción | 100% | 100% |
| Cobertura de confianza alta | 28,4085% | 29,1433% |
| Aciertos de confianza alta | 7.303 / 7.324 | 7.564 / 7.586 |
| Precisión de confianza alta | 99,7133% | 99,7100% |

Ambas etapas superan los umbrales prospectivos: al menos 10.000 muestras,
+0,5 puntos de acierto, cobertura 98%, confianza alta en 5% y precisión
95% en ese subconjunto. Incertidumbre no oculta errores: la precisión
global incluye todas las transiciones. Todavía hay 3.729 y 3.612 errores
del primario; un cierre predictivo no implica predicción perfecta.

**Historia 4 no es el ganador:** aporta solo dos aciertos adicionales en
cada etapa y descarta 46.049 altas de contexto al llenarse su registro.
No se seleccionó retrospectivamente entre dos y cuatro pasos: dos era
el brazo primario del contrato. La observabilidad potencial y la capacidad
de aprender con memoria limitada no son la misma cosa.

## Invariantes y presupuesto

- WSP intacto de 16 bytes; aritmética entera; sin LLM/córtex ni hardware.
- 45 paquetes observados en una CAM de 4.096 ranuras; cero destrucciones.
- T instantánea idéntica en los tres brazos: mismo aprendizaje base.
- CAM/T/PATTERN/registro idénticos antes/después de cada examen; solo avanza
  la ventana. Predicciones nunca se escriben como hechos.
- Primario: 1.007/2.048 contextos, 2.807/8.191 filas PATTERN, cero descartes.
- Claves del primario: 50.350 bytes; ventana: 50 bytes. La estimación de
  objetos Python del conjunto CAM/T/PATTERN/registro es 3.930.876 bytes en
  esta ejecución. **50 bytes no es el consumo total del modelo.** No es
  medida de RSS, implementación C Heap-0 o memoria de una NPU.
- Integración nativa: cero hechos falsos, ranuras destruidas y llamadas al
  córtex. Las paradas, terminalidad y gate mantienen su autoridad.

## Verificación

**145 pruebas pasan:** 26 nuevas del predictor/campaña, 26 de ventana/auditoría
temporal y 93 regresiones seleccionadas de WORLD-1, Q, HEAT, ECHO-2 y NEXUS-0.
Incluyen capacidad llena sin desalojo, entradas inválidas sin mutación,
predicción anterior a la consecuencia, uso de la acción tras veto,
congelación y rechazo de informe y traza manipulados en copias temporales.
No se ejecutó toda la suite histórica ni se reabrieron campañas selladas.

La auditoría completa en un proceso nuevo vuelve a entrenar desde cero,
repite B/C y compara todos los campos semánticos y hashes de las trazas.
Resultado: `valid=true`, sin hallazgos, `sensation_predictive_green=true`.
El tamaño de objetos dependiente del intérprete es diagnóstico y no entra
en el digest; los presupuestos y ocupaciones sí.

Certificado de contenido reproducible (no certificación externa):

`96f2deaeefdc40a38d45710dc732106f68295d7a81553bef4b6e554a8f8d1b88`

[Informe](../lab/echo4/sensation1-predictor-v1/report.json) ·
[Recibo de auditoría](../lab/echo4/sensation1-predictor-v1/audit-receipt.json).
Las trazas locales `train.jsonl`, `B.jsonl` y `C.jsonl` ocupan unos 72 MiB
en conjunto. Se conservan como evidencia, no se han publicado en la web.

## Reproducción

Desde `echoai/`, verificar evidencia existente sin sobrescribirla:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 sensation-verify lab/echo4/sensation1-predictor-v1
```

Otra ejecución completa, JSON en stdout y sin escritura implícita:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 sensation-campaign
```

`--output-dir` permite conservar evidencia en un directorio **nuevo** y
rechaza sobrescribir uno existente. `--development` utiliza otro corpus
y no concede cierre aunque sus números pasen un umbral.

Pruebas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest \
  echoai.tests.test_echo4_sensation_predictor echoai.tests.test_echo4_sensation1 \
  echoai.tests.test_echo4_world1 echoai.tests.test_qtable \
  echoai.tests.test_heat1 echoai.tests.test_echo2 \
  echoai.tests.test_nexus0.TestWorld echoai.tests.test_nexus0.TestEncoder \
  echoai.tests.test_nexus0.TestGate echoai.tests.test_nexus0.TestBench -q
```

## Siguiente fase

**E4-BOUNDARY-1**: contrato de intervenciones comparables, acciones vetadas,
retardos y perturbaciones para estimar influencia causal y abstenerse ante
ambigüedad. Un error de SENSATION no basta para clasificar un cambio como
externo, ni predictibilidad significa pertenencia corporal. BOUNDARY no
está implementado por este cierre; ECHO-4 completo sigue abierto.
