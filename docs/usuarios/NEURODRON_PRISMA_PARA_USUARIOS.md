# PRISMA y NEURO-DRON: del análisis de señal a una intención de vuelo

**Guía para usuarios · estado contrastado el 18-09-2026.** PRISMA ya tiene un motor de procesamiento por eventos, entrada en vivo y una suite de análisis EEG. NEURO-DRON es la línea de investigación que propone conectar señales humanas a decisiones de vuelo y devolver información visual o táctil a la persona.

Esa línea aprovecha capacidades ya construidas en **echoAI** y **echOS 3.0**. Todavía no existe una validación del recorrido completo persona → decoder → ambos gates → dron físico → percepción. El trabajo pendiente consiste en construir y medir esa conexión sobre las piezas existentes.

## Qué ofrece PRISMA hoy

| Capa | Funciones implementadas | Utilidad para el usuario |
|---|---|---|
| **PRISMA Engine** | Motor Rust: modulación delta, neuronas LIF con AVX2 o ruta escalar, STDP, predicción y telemetría | Procesar una señal como flujo de eventos y observar su comportamiento |
| **PRISMA 5, análisis e interfaz** | Suite Python sobre MNE: importación, limpieza, eventos/épocas, ERP, espectro, tiempo-frecuencia, conectividad y fuentes | Trabajar con grabaciones EEG y ejecutar análisis reproducibles |
| **Pipelines y grupo** | Pasos declarados en YAML, ejecución por sujeto/lote, informes y estadística de grupo | Repetir un análisis conservando parámetros, versiones y resultados |
| **Integridad estadística** | Correcciones por familia, sensibilidad a extremos y confusores, potencia y resultados no computables | Identificar qué conclusiones soportan los datos |
| **Entrada en vivo** | Socket TCP de muestras y puente LSL | Alimentar el motor desde un productor externo, replay o generador sintético |

El motor y la suite de análisis pueden funcionar por separado. Los métodos clásicos proceden de MNE y sus bibliotecas asociadas; la aportación de PRISMA está en el flujo de trabajo, integración, procesamiento por eventos e integridad. No necesita una placa neuromórfica para ejecutar su ruta CPU.

Existen lectores para BrainVision, EDF/BDF, GDF, CNT, EEGLAB y FIF, con distintos tipos de comprobación documentada. Se ha procesado un dataset Flanker de 73 participantes y se ha comprobado la importación de épocas de imaginería motora BCI Competition IV 2a. **Leer y analizar esas épocas no equivale a haber validado un decoder de órdenes.** La documentación técnica recoge 135 tests automáticos; esta guía no los ha vuelto a ejecutar. [Documento técnico consultado](/home/roger/rxlabs.org_local/src/content/prisma/tecnico.md).

La capa de integridad también conserva resultados negativos: la hipótesis de que calibrar el umbral por sujeto predijera comportamiento no replicó en dos datasets públicos. Ese resultado limita la hipótesis, sin borrar las herramientas de análisis que sí funcionan.

## Rendimiento del motor y reloj de la señal

El informe técnico de Engine 0.1.0 registra un microbenchmark de **32 canales y 200.000 muestras**: **1,81 µs de media** y **43,9 µs como peor valor observado** en el camino caliente, con búferes fijos. Es rendimiento de una operación de software en una configuración concreta. No mide adquisición del sensor, evidencia necesaria para decidir, radio, movimiento ni percepción humana; tampoco establece un máximo garantizado.

La entrada TCP ya existe: cabecera con canales/frecuencia y muestras `float32` intercaladas. El puente LSL permite conectarle otros productores. La versión inspeccionada asigna el tiempo al recibir la muestra y no transporta en cada muestra el tiempo original del sensor ni marcadores de tarea. Por eso aún falta instrumentación para demostrar una latencia desde la adquisición física. Una marca de recepción no puede reconstruir por sí sola ese dato ausente. [Código de entrada](/home/roger/Escritorio/PRISMA-Engine-Workspace/prisma-engine-dev-full/src/live_source.rs), [puente LSL](/home/roger/Escritorio/PRISMA-Engine-Workspace/prisma-engine-dev-full/scripts/bridges/lsl_to_prisma.py).

## Qué quiere decir «subir» en este proyecto

Primero hay que definir una tarea observable y entrenable. El sistema podría asociar inclinar el torso, una activación muscular o un patrón de una tarea EEG a una propuesta acotada. Una vez seleccionada, la propuesta significa algo como «solicitar un desplazamiento permitido hacia arriba»; no contiene las revoluciones de cada motor.

Intentar un movimiento, imaginarlo, seleccionar un objetivo y pensar una palabra son tareas distintas. No existe en PRISMA un traductor general que entienda la palabra mental «subir». La investigación debe especificar señal, tarea, vocabulario, reposo, cancelación y criterio de abstención antes de hablar de precisión.

| Ruta propuesta | Qué entrada utiliza | Estado en NEURO-DRON |
|---|---|---|
| **Torso/IMU** | Movimiento e inclinación medidos mecánicamente | Primera comparación no invasiva propuesta; no es una señal eléctrica cerebral |
| **EMG de superficie** | Actividad eléctrica muscular | Ruta periférica propuesta; adquisición, calibración y decoder por validar |
| **EEG** | Actividad eléctrica registrada en el cuero cabelludo | Procesamiento ya disponible; decoder de intenciones y vuelo pendientes |
| **Datos de implantes abiertos** | Grabaciones publicadas para tareas definidas | Posibilidad de evaluar decodificadores offline sin realizar cirugía |

La revisión de investigación también compara otras modalidades. No convierte su existencia en equipos disponibles en el laboratorio ni en una integración ya implementada.

## Cómo se aprovecha el híbrido que ya existe

El reparto propuesto es:

1. **PRISMA:** adquirir y procesar señal; el futuro decoder propone una intención o se abstiene.
2. **echoAI:** incorporar la propuesta al contexto de observaciones, memoria, predicción y misión; aplicar su gate. Sus componentes spiking y su vía opcional hacia Qwen ya existen.
3. **echOS:** recibir una intención por su ABI, comprobar tiempo, límites y estado, y enviarla mediante su puente.
4. **PX4:** estabilizar y ejecutar la consigna admitida.
5. **Retorno:** informar a la persona de lo realmente observado y de las intervenciones del sistema.

WSP sigue siendo el único bus cognitivo de echoAI, con **16 bytes**. El Intent ABI v1 de echOS tiene **72 bytes** y cumple otra función. La conversión entre ambos debe preservar causa, secuencia, marco y caducidad; no se ha demostrado todavía como cadena conjunta con PRISMA.

La recomendación de otra IA de «añadir una SNN y un LLM pequeño» describe piezas que ya existen. La pregunta útil ahora es qué señal aporta el decoder, cómo se calibra y cómo se consume una propuesta lenta sin bloquear la acción. El LLM no debe interpretar cada muestra EEG ni ocupar el lazo de estabilización. [Guía de echoAI](ECHOAI_ECHO3_PARA_USUARIOS.md), [guía de echOS](ECHOS_3_PARA_USUARIOS.md).

## Qué significan las cifras de latencia del resumen anterior

**98, 163 y 1.245 ms son sumas de asignaciones propuestas, no medidas ni límites biológicos.** Incluyen evidencia, adquisición, inferencia, selección, gates, transporte, autopiloto, mecánica y retorno físico. El [presupuesto original](/home/roger/Escritorio/PRISMA-Engine-Workspace/docs/research/astra/neurodron/NEURODRON_PRESUPUESTO_LATENCIA.md) conserva cada término.

| Escenario de trabajo | Señal detectable → retorno físico | Añadiendo la reserva perceptiva hipotética de 80 ms |
|---|---:|---:|
| Torso/IMU | 98 ms | 178 ms |
| EMG | 163 ms | 243 ms |
| EEG de imaginería motora | 1.245 ms | 1.325 ms |

La reserva perceptiva es otra hipótesis, no una medición del instante de consciencia. La asignación EEG es deliberadamente conservadora; no demuestra que todo EEG necesite 1,2 segundos ni que cualquier EMG sea más rápido en cualquier tarea.

El objetivo propuesto para torso/EMG es **P95 ≤150 ms desde señal detectable hasta retorno físico**, con ambos gates. P95 indica el valor por debajo del cual queda el 95 % de las observaciones. No empieza en un «impulso mental» observable, no termina sólo en la recepción de una orden y todavía no se ha alcanzado experimentalmente. El escenario EMG nominal de 163 ms ya supera ese objetivo: habrá que medir y revisar sus términos. Sumar percentiles de etapas no produce el percentil del recorrido completo.

Reducir el tiempo no justifica eliminar filtros. Los 2 ms asignados conjuntamente a los gates son una hipótesis; el veto máximo de 288 ms en SAFE-1 v2 pertenece a otro recorrido de prueba e impide dar por resuelta la cancelación integral.

## El camino de vuelta

La propuesta incluye vídeo FPV y señalización háptica congruente con dirección, estado o proximidad. Recibir una intención, aceptarla y observar movimiento son tres eventos distintos: una vibración inmediata de recepción no debe presentarse como prueba de que el dron ya se movió.

El retorno tendría que proceder de una medida identificable, conservar su antigüedad y comunicar bloqueos o pérdida de estado. «Presión del viento» requeriría una medición o estimación explícitamente validada; no se deduce por poner un vibrador en un chaleco.

No existe todavía un ensayo propio de incorporación del dron al esquema corporal. La vibración sería una señal sensorial aprendida; hay que medir por separado utilidad, sensación de controlar la acción, sensación de pertenencia corporal y malestar. Ninguna se garantiza sólo por bajar la latencia.

## Próximos horizontes sobre las piezas existentes

| Horizonte | Trabajo propuesto | Qué resultado permitiría avanzar |
|---|---|---|
| **T0: 0–6 meses** | Datos abiertos, comparadores de decodificación, separación entre días, replay causal, reposo/abstención y trazas hasta SITL | Rendimiento reproducible sin fuga de datos, falsas activaciones y latencia caracterizadas; puede empezar sin comprar sensores |
| **T1: no invasivo** | Comparar torso, EMG y EEG por tarea, con retorno equivalente e instrumentación física | Beneficio útil, recuperación y tiempos medidos en un entorno contenido |
| **T2: colaboración clínica** | Reproducción offline ahora; trabajo con personas mediante un grupo clínico y su protocolo | Pregunta útil, responsabilidades y validación específica para esa población |
| **T3: largo plazo** | Interfaz bidireccional y estabilidad de uso | Beneficio reproducible frente a alternativas accesibles; sin fecha de producto prometida |

FALCON H1 es una de las posibilidades de datos intracorticales recogidas en la revisión. Estudiar grabaciones públicas no requiere implantar a nadie y tampoco valida automáticamente el control online de un dron. Para cada dataset hay que comprobar versión, tarea y licencia.

AKD1500 M.2 es un acelerador candidato previsto, no una pieza validada de este recorrido. Primero se necesita una referencia CPU y después una medida de compatibilidad, transferencias, tiempo y energía de la tarea completa. No hay AKD1000 en el laboratorio. La revisión NEURO-DRON tampoco cierra P0-R, TRANSFER-3 ni DRONE-3.

## Preguntas actuales

1. ¿Qué tarea concreta queremos facilitar y para qué usuario?
2. ¿Qué rendimiento entre días y cuántas falsas órdenes en reposo obtiene el decoder frente a comparadores sencillos?
3. ¿Cómo se enlaza el tiempo original de adquisición con el de decisión, vuelo y retorno?
4. ¿Qué comunica la interfaz cuando el gate modifica una orden o falta telemetría?
5. ¿Qué parte del beneficio procede del usuario y cuál de la autonomía del dron?

Fuentes de alcance: [revisión NEURO-DRON](/home/roger/Escritorio/PRISMA-Engine-Workspace/docs/research/astra/neurodron/NEURODRON_INFORME.md), [registro de evidencia](/home/roger/Escritorio/PRISMA-Engine-Workspace/docs/research/astra/neurodron/NEURODRON_LEDGER_EVIDENCIA.md), [decisión por horizonte](/home/roger/Escritorio/PRISMA-Engine-Workspace/docs/research/astra/neurodron/NEURODRON_DECISION.md). Lectura pública: [PRISMA técnico](https://www.rxlabs.org/docs/prisma/tecnico), [EEG y dron](https://www.rxlabs.org/docs/prisma/eeg-dron).
