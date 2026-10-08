# Contexto actual de PRISMA, echoAI y echOS para revisar NEURO-DRON

**Corte de evidencia: 18 de septiembre de 2026.** Este documento es autocontenido y se puede enviar a otra IA antes de pedir una opinión. Describe software y resultados existentes, diferenciándolos de la integración pendiente.

## Punto de partida

**Ya tenemos una arquitectura híbrida con componentes spiking y un LLM opcional en echoAI, capacidades robóticas ensayadas con PX4 SITL y un runtime robótico propio en echOS 3.0.** Proponer «añadir una SNN y un LLM pequeño» como primer paso desconoce ese trabajo. La revisión útil debe partir de las interfaces, resultados y límites siguientes.

Todavía no hemos validado la cadena completa desde una persona hasta un dron físico y su retorno perceptivo. Tampoco hemos certificado el LLM como parte de una misión continua: su aportación de lenguaje se ha probado en host y las campañas robóticas ECHO-3 citadas funcionan con el córtex apagado.

## 1. PRISMA: señal y análisis

PRISMA Engine es un motor Rust por eventos: modulación delta → LIF → STDP → predicción/telemetría, con AVX2 y alternativa escalar. PRISMA 5 añade análisis EEG en Python sobre MNE: importación de formatos, limpieza, ICA, épocas, ERP, espectro, tiempo-frecuencia, conectividad, fuentes, pipelines YAML, estadística de grupo e integridad de resultados.

Ya existe entrada en vivo por TCP y un puente LSL. El protocolo inspeccionado no preserva el tiempo original del sensor en cada muestra; asigna un tiempo al recibirla. Conservar origen temporal y marcadores es una necesidad concreta de NEURO-DRON, no hace falta empezar desde cero toda la adquisición.

El informe técnico registra **1,81 µs de media y 43,9 µs de máximo observado** en el camino caliente, para 32 canales y 200.000 muestras. Es un microbenchmark del motor; no mide cuánto tarda una persona en emitir una intención ni cuánto tarda el dron en responder. Existen análisis sobre datos EEG reales y 135 tests documentados. **Aún no hay un decoder de intenciones de vuelo validado.**

## 2. echoAI / ECHO-3: el híbrido ya construido

echoAI tiene dos escalas temporales. El núcleo rápido representa, recuerda, predice, aprende de consecuencias y decide con un gate; funciona sin el modelo de lenguaje. ATTEND solicita ayuda al córtex opcional cuando se cumplen sus condiciones. El LLM devuelve una propuesta restringida, no un hecho verificado ni una orden de motor.

Las piezas incluyen WSP, memoria episódica CAM, modelo de transición T, política Q, patrones temporales, composición, atención y consolidación. Existen componentes spiking LIF/Adaptive-LIF: CAPACITY-1 evaluó **512 LIF + 128 Adaptive-LIF**. En la GUI neuronal esa rama es un monitor perceptivo; no debe describirse como una red de 640 neuronas que sustituya por sí sola a CAM/Q/gate o pilote los motores.

El adaptador de **Qwen3-4B-Instruct-2507 Q4_K_M** ya se probó. El informe Qwen-0 conserva **8/8 letreros resueltos, 6/6 paráfrasis frente a 0/6 del control por reglas, ROI canónico 16 y 1,6178 segundos de media por consulta**. Es evidencia pequeña y concreta de interpretación útil de lenguaje, no inteligencia general ni latencia de vuelo. No usamos SIGN-C como segunda confirmación: su JSON actual no tiene modelo configurado y no acredita el resultado positivo citado en el historial.

La ruta host de `cortex.complete()` espera un subproceso. Tener dos relojes en la arquitectura o un hilo aparte para el render no demuestra todavía que una misión continua mantenga sus plazos durante una consulta. **Desacoplar, fechar y descartar propuestas lentas sigue siendo una pregunta de integración pertinente.** No se debe encender el LLM en los bancos NEXUS-0 para resolver esta documentación.

ECHO-1 y ECHO-2 cerraron sus bancos. **ECHO-3 tiene 13 de 15 hitos verdes en su alcance software:** simulación, vuelo PX4, sensores con procedencia, conversión a WSP, patrones, fusión de evidencia, dinámica acotada, composición, atribución causal acotada, enlace con PX4, reserva energética simulada, contención de fallos y autoridad de fuentes por consecuencias.

Ejemplos: COMPOSE-1 v4 registra **6.144 misiones funcionales y 32 vuelos nuevos Gazebo/PX4**; SAFE-1 v2, **diez fallos contenidos**; HOST-1, **1.536/1.536 decisiones útiles frente a 768/1.536 por etapa**. Cada cifra pertenece a su banco. COMPOSE no demostró superioridad frente al comparador convencional competente. HOST no mide confianza psicológica humana.

**TRANSFER-3 sigue rojo, sin candidato útil confirmado; DRONE-3 sigue pendiente de integrar la misión completa.** Trece certificados parciales no equivalen a un robot integral terminado.

## 3. echOS 3.0: ejecución y límites

echOS es un unikernel robótico con arranque x86_64 BIOS/UEFI y ARM64 directo/UEFI en QEMU. Implementa registros de sensor, colas fijas, intenciones con causa y caducidad, safety gate, watchdog, diagnóstico, persistencia y puente MAVLink 2 hacia PX4 SITL. El cierre de versión suma **441 comprobaciones en seis certificados**; no es una certificación aeronáutica.

El gate puede aceptar, modificar o bloquear y conserva separados esos resultados. Comprueba rangos, antigüedad, caducidad y condiciones representadas de batería, enlace, geofence y límites. El camino sensor → intención registró cero asignaciones dinámicas en los escenarios documentados.

**El productor actual de echOS es una política simple, no el agente echoAI.** No hay Qwen ni otro LLM en la ISO. echoAI y echOS tienen conexiones con PX4 probadas por separado; falta acreditar su unión. PX4 conserva el control de estabilización y motores, y se ejecuta fuera de la ISO en estas pruebas.

## 4. NEURO-DRON: la conexión humana propuesta

El reparto previsto es PRISMA → propuesta de intención → echoAI y su gate → Intent ABI → safety gate de echOS → PX4 → retorno observado a la persona. No es una cadena completa ya ejecutada.

Las primeras rutas propuestas son torso/IMU y EMG de superficie, comparadas por tarea; EEG puede estudiarse para selecciones o metas. Inclinar el torso, activar un músculo, intentar un movimiento, imaginarlo y pensar una palabra no son tareas intercambiables. No existe un traductor general de palabras mentales.

La fase inicial puede usar datos abiertos, incluidos datos de implantes para evaluación offline, sin cirugía ni compra inicial de sensores. Después vendrían comparación no invasiva y retorno sensorial; cualquier trabajo clínico con personas corresponde a una colaboración específica. No hay dron físico, sensores EEG/EMG ni acelerador Akida operativos y validados en esta campaña. AKD1500 M.2 es un candidato previsto; **no hay AKD1000 en el laboratorio**.

## Correcciones al resumen que originó la conversación

| Formulación que induce a error | Formulación que corresponde al estado actual |
|---|---|
| «Intent ABI enviado en WSP de 16 bytes» | **WSP = 16 bytes; Intent ABI v1 = 72 bytes.** Son contratos distintos. WSP permanece como único bus cognitivo |
| «Torso 98 ms, EMG 163 ms, EEG 1.245 ms medidos» | Son **escenarios aritméticos propuestos**, no resultados de la interfaz ni límites universales de esas modalidades |
| «P95 ≤150 ms desde impulso nervioso hasta reacción» | Objetivo todavía no alcanzado: **señal detectable → retorno físico**, conservando ambos gates. Percepción e inicio subjetivo son medidas diferentes |
| «La SNN ya extrae intenciones humanas de vuelo» | Hay procesamiento spiking; aún falta validar el decoder, la abstención y su generalización entre días |
| «El filtro detecta perder la atención y siempre hace hover» | No hay detector neural validado de atención. La respuesta segura depende del estado y de los mecanismos de recuperación disponibles |
| «PX4 o ArduPilot ya integrados» | La evidencia citada corresponde a **PX4 SITL** |
| «La háptica hará sentir el dron como una extremidad» | Es una hipótesis por medir. Debe comunicar estado observado, distinguir recepción/aceptación/movimiento y evaluar control percibido y pertenencia corporal |
| «El cerebro da órdenes gruesas y esto funciona exactamente igual» | Es una analogía funcional para explicar responsabilidades, no equivalencia neuroanatómica demostrada |

Un modelo que estime confianza necesita un objetivo definido: calidad de señal, probabilidad calibrada del decoder, autoridad de una fuente y seguridad de una acción son variables distintas. Ninguna equivale por sí sola a «cuánta confianza tiene la persona». HOST-1 es un antecedente para autoridad por consecuencias; no autoriza relajar automáticamente límites de seguridad durante entrenamiento humano.

## Qué feedback necesitamos ahora

1. Cómo aprovechar el híbrido existente sin poner el modelo de lenguaje en el lazo rápido, y cómo rechazar respuestas antiguas.
2. Cómo conservar causa, tiempo de origen y cancelación entre PRISMA, WSP, Intent ABI y retorno, con pruebas de la cadena completa.
3. Cómo comparar el futuro decoder con métodos sencillos y medir falsas activaciones en reposo, cambios entre días y abstención.
4. Qué prueba falta para unir las dos rutas PX4 ya existentes y qué debe demostrar DRONE-3.
5. Cómo diseñar feedback que exprese tanto movimiento real como veto, intervención autónoma o pérdida de estado.

Pedimos propuestas que indiquen qué componente existente reutilizan, qué carencia concreta resuelven y cómo se comprobaría el beneficio. Un entrenamiento humano progresivo o un nuevo modelo de secuencias son posibilidades de investigación; no se presentan como capacidades ya terminadas.

## Documentación para contrastar

- [PRISMA / NEURO-DRON: guía y fuentes](NEURODRON_PRISMA_PARA_USUARIOS.md).
- [echoAI / ECHO-3: guía, resultados y límites](ECHOAI_ECHO3_PARA_USUARIOS.md).
- [echOS 3.0: guía, contratos y certificados](ECHOS_3_PARA_USUARIOS.md).
- [Estado ECHO-3](../ECHO3-STATUS-20260917.md), [Qwen-0](../../lab/nexus0_qwen4b_report.json), [informe echOS 3.0](../../../docs/ECHOS_3.0_REPORT.md).

Las cifras proceden de artefactos existentes inspeccionados para redactar estas guías. No se han vuelto a ejecutar los bancos ni activado modelos. Este documento informa del estado; no cierra fases de investigación ni anuncia una publicación web.
