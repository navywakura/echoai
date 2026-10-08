# RSI1-R1: recuperación declarada del transporte CPU

2 de octubre de 2026. El experimento RSI1 original arrancó tras el cierre válido
de PROBE2 y quedó **BLOCKED a las 04:17:52 Madrid**. Su primera llamada a
`llama-cli` terminó con SIGABRT (-6) durante warmup: `ROCm error: invalid device function`.
No produjo respuesta del modelo ni abrió el examen. Se conserva su directorio,
status, presupuesto, stderr, fuentes y diez generaciones de controles sin LLM.

Aunque el comando tenía `-ngl 0`, el backend usó ROCm para operaciones sobre
tensores del host. La documentación distingue esa descarga de las capas del modelo.
[Opciones oficiales de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md).
La ayuda del binario instalado confirma las opciones utilizadas aquí.

La nueva condición **RSI1-R1** se guarda en
`lab/research/echo-rsi1-recovery1-20261002/` y utiliza un launcher separado:
`--device none --no-op-offload --no-kv-offload`, con dispositivos HIP/ROCr ocultos.
No reemplaza ni actualiza el binario o los pesos. Cambia únicamente la selección
del backend para ejecutar el perfil CPU que se pretendía medir.

Conserva semillas, datos, gramática, cinco brazos, generaciones, profundidad,
expansiones, prompts, sampling, límites de tokens y timeout, criterios de
aceptación y los tres requisitos de verde del [contrato original](ECHO-RSI1-DESIGN.md).
La recuperación no modifica ninguna fuente original congelada ni usa respuestas
de PROBE/S6 en solicitudes al modelo. El resultado seguirá indicando S6_green=false.

Antes de iniciar se exige un recibo válido de PROBE2 y una prueba de transporte
con el mismo GGUF, contexto 4096 y cuatro hilos, sobre un prompt artificial ajeno
a las cohortes: devuelve un JSON artificial, con semilla 311 y tope de 16 tokens
de salida. La prueba debe terminar correctamente y registrar buffers de
cómputo CPU sin buffers de cómputo GPU. Se declara como una llamada adicional;
su salida no es evidencia de capacidad ni se incorpora a la biblioteca.

Presupuesto de la condición: hasta **57 llamadas del nuevo banco**, más **una
fallida original y una de calibración**, máximo agregado **59**. Cero API,
alquiler o gasto externo. Las llamadas fallidas se conservan y cuentan; no hay
reintentos automáticos. El tiempo y trabajo de los diez controles anteriores
son coste adicional conservado, no resultados reutilizados. La nueva condición
empieza desde cero y se compara bajo su propio manifiesto.

`total-budget.json` enlaza esos costes de llamadas. El recibo de recuperación
guarda hashes de todos los archivos originales y de la calibración. Cada control
de integridad comprueba esas referencias, los archivos brutos de calibración,
el cierre de PROBE2 y el binario real detrás del launcher. La contabilidad se
actualiza después de cada llamada, incluso si falla.
La condición congela sus propias fuentes, launcher, tests y esta adenda.

Se inicia como servicio de usuario, sin reinicio automático. Un límite externo
de ocho horas de ejecución conserva el límite declarado; una interrupción se
registra BLOCKED y no se interpreta como resultado científico negativo.
La instrumentación muestra etapas, promociones y resultados reales en el log
del servicio; no crea otro bus de pensamiento.

Los tests específicos comprueban custodia del fallo, prohibición de reiniciar
después de una respuesta o examen abierto, conservación de llamadas previas y
contabilidad agregada. La calibración real verifica el transporte; sus tiempos
solo orientan la duración, que dependerá de los prompts del banco.
