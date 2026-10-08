# Familia Echo Alpha, Beta, Theta y Gamma: investigación y viabilidad

7 de octubre de 2026. Documento privado de propuestas para noviembre–diciembre de 2026 y Q1 de 2027. Registra las ideas del propietario, fuentes comprobadas y decisiones recomendadas. No hay modelos entrenados, infraestructura contratada ni nuevas métricas obtenidas por este informe. Complementa la [investigación de RSI-2](ECHO-RSI-2-FUTURE-REVIEW-20261007.md) y la [visión de ECHO-5/5.1/5.5](ECHO5-51-55-RESEARCH-VISION.md).

**La propuesta es integrar el núcleo de ECHO-5.5 con un neocórtex entrenable e intercambiable.** El núcleo conservaría estado, memoria causal, control y verificación; el modelo de lenguaje propondría programas y reparaciones, interpretaría solicitudes y explicaría resultados. «Cerebro reptiliano» y «neocórtex» describen funciones por analogía. La arquitectura de software conserva interfaces explícitas y pruebas de integración.

Se registran estos nombres como nombres de trabajo de la familia. Todavía no designan publicaciones ni capacidades acreditadas; tampoco se ha comprobado disponibilidad de marca.

| Nombre propuesto | Producto que se quiere investigar | Ventana deseada | Evidencia necesaria |
|---|---|---|---|
| **Echo-Alpha-7B** | Neocórtex abierto de aproximadamente 7B, adaptado al protocolo de ECHO, con ejecución local y `dream` en el runtime | Piloto noviembre–diciembre de 2026 | Mejores propuestas útiles o menor coste frente a su propia base, conservación y utilidad de ECHO frente al mismo LLM aislado |
| **Echo-Beta-14B** | Neocórtex intermedio para problemas donde Alpha no alcanza el criterio previsto | Q1 de 2027 | Ventaja frente a Alpha en casos nuevos, incluyendo tiempo y coste; ajuste completo sujeto a perfil previo |
| **Echo-Theta-32B** | Neocórtex de mayor tamaño para síntesis y planificación exigentes | Investigación Q1 de 2027 | Ganancia propia frente a su base y frente a Beta, transferencia, retención y coste sostenible |
| **Echo-Gamma-Images** | Generador visual existente integrado con especificaciones, selección de candidatos y comprobaciones de ECHO; adaptación propia si aporta utilidad | Piloto separado noviembre–diciembre de 2026 | Mejor seguimiento de restricciones o menor coste frente al mismo generador sin ECHO; evaluación visual independiente |

7B, 14B y 32B indican parámetros del modelo lingüístico, no tamaño del núcleo ni duración admisible de las tareas. El enrutador elegiría por competencia y coste medidos. Una tarea breve puede exigir razonamiento difícil; una larga puede consistir en operaciones rutinarias. No se fija todavía una base ganadora: se compararán modelos abiertos con pesos y licencia adecuados. La comparación B23 de 7B/14B de una misma familia permitiría aislar tamaño antes de introducir entrenamiento propio.

**La entrega necesita distinguir pesos y sistema completo.** Un ajuste puede enseñar al modelo el DSL, los formatos de herramienta y cuándo solicitar comprobación. La memoria persistente, las transiciones del mundo y el verificador siguen siendo componentes ejecutables del runtime. Un archivo GGUF por sí solo no incorpora todas esas funciones. Cada publicación identificaría modelo base y revisión, método de ajuste, dataset, licencia, cuantización, versión del núcleo y resultados del sistema integrado. Fusionar LoRA con la base genera un checkpoint completo, pero el método sigue siendo ajuste con adaptador; la descripción del producto debe conservar esa distinción.

El objetivo de ajuste completo de las tres escalas queda registrado. Para decidir su conveniencia, la primera comparación sería base sin ajustar, SFT con adaptador y ajuste de todos los pesos, usando datos equivalentes cuando el perfil lo permita. No hay evidencia de que cambiar todos los pesos vaya a superar al adaptador en nuestras tareas. La cantidad, calidad y diversidad de los ejemplos propios, y el funcionamiento del controlador, forman parte del experimento.

**`dream` sería una operación acotada de búsqueda y ejecución.** El usuario podría seleccionar presupuesto de tiempo, hipótesis y gasto; una solicitud normal usaría un presupuesto pequeño. El recorrido propuesto es:

```text
solicitud y evidencia permitida
  → recuperar recuerdos con procedencia
  → generar varias hipótesis o programas
  → ejecutar candidatos en el entorno disponible
  → registrar fallos y refinar dentro del presupuesto
  → verificar y seleccionar con el criterio declarado
  → entregar resultado, alcance de la comprobación y coste
```

El modo no actualizaría pesos en cada consulta. La incorporación de experiencias a un dataset sería un proceso separado; el entrenamiento posterior produciría un candidato versionado antes de sustituir al activo. Los trabajos abiertos conservarían su versión hasta terminar. Dream puede mejorar una respuesta mediante más búsqueda sin haber demostrado aprendizaje acumulativo ni RSI.

La selección depende del problema. Para código se comprobarían compilación y tests; para ARC, las demostraciones permitidas y los límites del contrato; para juegos, las transiciones ejecutadas; para imágenes, las restricciones medibles y una evaluación perceptual. No se consultan respuestas reservadas para escoger candidato. Si ninguno satisface el criterio, el resultado conserva incertidumbre o abstención. Una buena puntuación en simulación no garantiza corrección fuera de su dominio.

Para explorar una acción distinta de la histórica se requiere restaurar el estado completo y continuar con un simulador, o reiniciar la partida. Las trazas anteriores solo contienen consecuencias realmente observadas. Un modelo aprendido del mundo devuelve predicciones que deben contrastarse. El modo debe medir utilidad frente a una sola muestra, varias muestras independientes y refinamiento con feedback, igualando presupuesto. El panel mostraría observaciones, hipótesis explícitas, acciones, comprobaciones y resultados registrados, usando la observabilidad existente.

**El alcance actual de «cero alucinaciones» es el banco que comprueba `false_facts == 0`.** El [contrato NEXUS-0](05-NEXUS-0-SPEC.md) exige evidencia para marcar un hecho como verificado y mantiene el córtex apagado. No mide la verdad de cada frase que podría generar un LLM sobre cualquier tema. La garantía de producto propuesta es que una afirmación no se etiquete como verificada sin evidencia admisible. Hay que medir también errores de la evidencia, del parser y del evaluador. Para respuestas abiertas se informarían afirmaciones respaldadas, falsas afirmaciones aceptadas y abstenciones; reducir cobertura para abstenerse de todo no acredita utilidad.

**El ajuste completo exige un perfil distinto al de inferencia.** Estos cálculos usan GB decimales y cantidades nominales de parámetros:

| Escala | Solo pesos ideales a 4 bits | Solo pesos BF16 | Estados de ajuste completo convencional, antes de activaciones |
|---|---:|---:|---:|
| 7B | 3,5 GB | 14 GB | 112–126 GB |
| 14B | 7 GB | 28 GB | 224–252 GB |
| 32B | 16 GB | 64 GB | 512–576 GB |

El último intervalo supone 2 bytes de pesos, 4 de copia maestra, 8 de momentos Adam y 2–4 de gradientes: `M_estados ≈ P × (16–18)` bytes. Activaciones, buffers y comunicación aumentan el pico. Optimización cuantizada, offload y particionado cambian esos supuestos; una cifra menor requiere medir la configuración concreta. La [documentación de memoria de Transformers](https://huggingface.co/docs/transformers/main/en/model_memory_anatomy) describe 18 bytes con gradientes FP32. Inferencia añade metadatos y KV cache; los pesos cuantizados no son una estimación completa de VRAM.

El primer trabajo de Alpha puede usar QLoRA para evaluar si existen datos y ganancias suficientes. [QLoRA](https://arxiv.org/abs/2305.14314) demuestra un método de adaptación de base cuantizada; su resultado no garantiza que cualquier configuración quepa. Un ajuste completo corto de 7B podría ser viable con una configuración optimizada y RAM/offload suficiente. Para 14B/32B se presupuestaría particionado o estados reducidos y se mediría rendimiento antes de alquilar. El alquiler de una GPU para inferencia no proporciona automáticamente memoria ni interconexión adecuadas para entrenamiento distribuido.

El coste se obtiene de tokens totales —incluidas épocas—, tokens por segundo medidos, número de GPU y tarifa. Una aproximación de orden de magnitud al cálculo del entrenamiento denso es `F ≈ 6 × P × T`; no se convierte en horas sin rendimiento efectivo del stack. El perfil inicial debe medir pico de VRAM/RAM, checkpoint, restauración, throughput y estimación de coste de la corrida más evaluación. Si excede el techo de la etapa, se conserva el resultado del perfil y se aplaza ese entrenamiento. Ajustar una base existente con pocos tokens especializados tiene un presupuesto muy distinto al de preentrenar desde cero.

**Los recursos incluidos permiten preparar y comparar antes de pagar.** El propietario declara AI Pro activo con 200 unidades mensuales de Colab y acceso a Kaggle T4 ×2. Sus equivalencias de 26 horas A100 u 100 horas L4 son supuestos para planificación. Octubre–diciembre sumaría tres asignaciones, 600 unidades: aproximadamente 78 horas A100 o 300 L4 a esas tasas. Son alternativas y no se presupone acumulación de saldo. Se registrarán consumo real y GPU asignada; Google no garantiza un acelerador concreto ni recursos continuos. [Beneficio AI Pro](https://support.google.com/googleone/answer/14534406?hl=en), [FAQ Colab](https://research.google.com/colaboratory/intl/es/faq.html).

La CPU local prepararía datasets y evaluadores. Kaggle puede realizar comparaciones de inferencia o adaptadores que quepan; dos T4 mantienen dos memorias separadas. Colab serviría para perfiles y entrenamientos reanudables en el acelerador disponible. Las sesiones de ambos se tratarían como ejecutores temporales, con checkpoints privados fuera de la máquina. No se presupone un clúster unificado entre Kaggle y Colab. [Kaggle](https://www.kaggle.com/docs/notebooks), [T4 de NVIDIA](https://www.nvidia.com/en-us/data-center/tesla-t4/).

**Gamma es una línea adicional con un primer alcance pequeño.** La opción propuesta es medir un generador abierto existente y después comprobar si el control de ECHO añade seguimiento de objetos, cantidades, relaciones o texto. FLUX.1-schnell es un candidato verificable: transformer de flujo rectificado de 12B, destilación en espacio latente, 1–4 pasos y licencia Apache-2.0. Su pipeline incorpora otros componentes; no se deduce su VRAM total solo de esos 12B. La ficha consultada exige aceptar condiciones de acceso antes de descargar. [Ficha original de FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell).

SD3.5 Large Turbo ofrece otra comparación de cuatro pasos, con licencia propia de Stability. La API oficial también enumera SD3.5 Flash; eso no confirma el nombre «SD3.5 Medium Turbo» ni disponibilidad de pesos de Flash para ajustar. El coste, licencia y acceso deben corresponder al modelo exacto. [API oficial](https://platform.stability.ai/docs/api-reference), [licencia de Large Turbo](https://huggingface.co/stabilityai/stable-diffusion-3.5-large-turbo/blob/main/LICENSE.md).

La descripción recibida de las arquitecturas visuales necesita estas correcciones: Parti genera tokens de imagen autoregresivamente; Muse usa tokens enmascarados y decodificación paralela. Los pasos de muestreo no permiten ordenar todos los modelos por latencia o calidad. Los intervalos de 0,3–0,8 segundos necesitan GPU, resolución, lote y pipeline definidos. No se ha encontrado documentación oficial que respalde el nombre exacto «Gemini-4 Image Flash» en las fuentes consultadas; queda fuera de la selección técnica. «Zero-step» necesitaría definir qué cómputo realiza realmente. [Parti](https://arxiv.org/abs/2206.10789), [Muse](https://muse-model.github.io/).

Para Gamma se fijarían resolución, precisión, pasos y lote; se medirían latencias p50/p95 de arranque y ejecución, VRAM y coste por imagen aceptada. Se compararían generación única, varias imágenes del mismo modelo y selección/refinamiento con ECHO, contando todos los candidatos. [GenEval](https://arxiv.org/abs/2310.11513) proporciona pruebas de objetos, número, color y posición. El evaluador visual usa modelos que también pueden equivocarse; una muestra humana ciega debe comprobar su fiabilidad. El primer Gamma puede ser una integración experimental; llamarlo modelo entrenado de RxLabs exige una adaptación real, linaje y mejora propia. Se recomienda aplazar el ajuste completo del generador hasta medir una necesidad concreta.

**Un SaaS pequeño puede separar web, control CPU y GPU por demanda.** Un VPS mantendría API, sesiones, cola, presupuestos y recibos; un worker GPU ejecutaría el modelo cuando hubiera trabajos. Para el arranque basta una región y pocos trabajos simultáneos. El modelo y sus checkpoints se guardarían en un registro de artefactos; la memoria de cada sesión permanecería separada. La API común permitiría navegador, Echo Nexus y clientes propios, además de un servidor local con el mismo contrato.

| Acceso previsto | Primer alcance recomendado | Coste principal |
|---|---|---|
| Web | Demo limitada, envío de una tarea y recibo verificable; `dream` como trabajo con progreso y cancelación | Hosting ligero y ejecución solicitada |
| API alojada | Trabajos normales/dream con techo explícito y versión fijada | GPU/API externa y evaluación por uso |
| API local + GGUF | Núcleo y neocórtex en el equipo del usuario; exportación de memoria y recibos | Hardware del usuario, mantenimiento del paquete |
| Echo Nexus CLI | Reutilizar el arnés oficial para conectar a API local o alojada | Desarrollo y soporte del arnés existente |

La preferencia por navegador es una hipótesis comercial que conviene contrastar con usuarios. Recomiendo empezar por web y API sobre un único ejecutor, conservando Echo Nexus como cliente. La distribución de pesos y su licencia se decidirían por producto; el carácter abierto del arnés no cambia automáticamente el del núcleo. La primera oferta puede resolver un problema de desarrollo delimitado: probar una reparación, comprobar un programa o comparar hipótesis con un recibo. El cliente pagaría por utilidad y ejecución comprobadas. Gamma competiría en otro mercado y debe justificar su coste por separado.

Los precios consultados el 7 de octubre de 2026 muestran por qué conviene evitar GPU ociosa al arrancar. Los importes en USD no se convierten aquí a EUR; impuestos, almacenamiento y divisa requieren una cotización final.

| Servicio consultado | Memoria GPU | Tarifa publicada | Cálculo para 730 h encendido |
|---|---:|---:|---:|
| Runpod Pod RTX A5000 | 24 GB | 0,27 USD/h | 197,10 USD |
| Runpod Pod A40 | 48 GB | 0,49 USD/h | 357,70 USD |
| Runpod Pod A100 PCIe | 80 GB | 1,59 USD/h | 1.160,70 USD |
| Runpod Serverless grupo L4/A5000/3090 | 24 GB | 0,69 USD/h equivalente | 503,70 USD si se mantuviera activo |
| Runpod Serverless grupo A40/A6000 | 48 GB | 1,22 USD/h equivalente | 890,60 USD si se mantuviera activo |

Son productos y perfiles diferentes; no se comparan solo por tarifa. [Precios oficiales Runpod](https://www.runpod.io/pricing). Los workers flex escalan a cero y facturan arranque del worker, ejecución y espera antes de apagarse; el almacenamiento sigue teniendo coste. Con 0,69 USD/h, 60 segundos totales facturados equivalen a 0,0115 USD y 600 a 0,115 USD, solo cómputo. Son ejemplos aritméticos de tiempo facturado, no latencias medidas de Alpha o Gamma. Más hipótesis o workers aumentan el consumo. [Facturación Serverless](https://docs.runpod.io/serverless/pricing).

OVHcloud España publica VPS-1 desde 3,81 €/mes más IVA —4,61 € con el IVA mostrado—, 2 vCores y 4 GB RAM, y VPS-2 desde 7,21 €/mes más IVA —8,72 € mostrado—, 4 vCores y 8 GB. Si se mantuvieran esas tarifas serían 55,32 y 104,64 € por doce meses. Deben confirmarse plazo, localización y precio final; el VPS alojaría el control, no Theta en GPU. [Oferta consultada](https://www.ovhcloud.com/es-es/vps/).

Hetzner publica un precio actualizado de CX23 de 5,49 €/mes sin IVA/IPv4, pero su catálogo consultado marca la categoría Cost-Optimized como no disponible. Queda como alternativa a comprobar; esa cifra no demuestra stock contratatable. [Precios](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/), [disponibilidad del catálogo](https://www.hetzner.com/cloud/).

El coste directo por tarea se estimaría con `C = Σ(t_facturado_worker × tarifa_worker) + API + evaluación + almacenamiento asignado`. Se medirían colas, reintentos y tasa de éxito. Un plan comercial tendría cuotas de trabajos/cómputo y una modalidad con API propia del cliente; `dream` ilimitado comprometería el presupuesto. Solo se justificaría una GPU permanente cuando tráfico y margen previstos cubran su utilización y soporte. Colab/Kaggle se reservan al laboratorio y no son la infraestructura asumida para un servicio continuo a clientes.

**El nuevo techo del propietario es 1.300 € para cómputo e infraestructura.** Sustituye el reparto exploratorio anterior de 2.000 €. La beca se espera en 2027 y no se trata como saldo disponible. Este reparto es un máximo de planificación por hitos, con IVA/divisa dentro de cada techo; usa primero recursos incluidos y deja al menos 700 € fuera si la beca fuera exactamente 2.000 €.

| Etapa propuesta | Máximo reservado en el plan |
|---|---:|
| Alpha/Gamma: perfiles, primer ajuste y pilotos | 200 € |
| Beta: perfil y ajuste viable | 250 € |
| Theta: perfil y entrenamiento que quepa en la cotización | 350 € |
| Evaluación independiente, retención y reproducción | 200 € |
| VPS y almacenamiento | 150 € |
| Reserva técnica, divisa e incidencias | 150 € |
| **Total máximo** | **1.300 €** |

No garantiza entrenar y validar completamente los cuatro productos. Para dimensionar Theta, Runpod publica A100 SXM de clúster a 1,79 USD/GPU-h: ocho GPU durante 20 horas serían 286,40 USD y durante 50 horas, 716 USD, antes de adicionales. El segundo caso excedería el techo Theta salvo reasignación explícita. Ni ocho GPU aseguran que quepa una configuración ni 20 horas bastan para demostrar mejora; hay que comprobar interconexión, estados y throughput. Un adaptador evaluado puede conservarse si el ajuste completo no resulta rentable. [Tarifa de clúster consultada](https://www.runpod.io/pricing).

**La secuencia propuesta protege tanto los resultados como el dinero.** Octubre prepara datos privados, perfiles, controles de neocórtex y el contrato de `dream`. Noviembre intenta Alpha experimental, con adaptación pequeña y dos interfaces que comparten ejecutor; un ajuste completo solo después del perfil. Diciembre puede abrir Gamma si aparece utilidad frente al generador original. Q1 de 2027 estudia Beta, Theta y los primeros ciclos de pesos de RSI-2, condicionado a retención, transferencia y coste. Las fechas son objetivos del propietario; el bloqueo de S6 y el cierre de 4.5 siguen teniendo sus pruebas propias.

Cada candidato se compararía con su base, con el mismo modelo sin núcleo, con ECHO sin ajuste y con un control de igual presupuesto de búsqueda. Código, ARC y herramientas necesitan contratos distintos; los benchmarks públicos se identifican por versión y split, y una puntuación local no se presenta como puntuación oficial privada. Se buscaría rendimiento por tarea, coste, regresiones, uso correcto de herramientas, procedencia y abstención. Tamaño de parámetros y ausencia de errores observados no permiten predecir porcentajes de ARC ni equivalencia frontier.

Para código se propone [LiveCodeBench](https://livecodebench.github.io/), fijando su versión y ventana temporal, y después [SWE-bench Verified](https://www.swebench.com/) para reparación de repositorios con herramientas. Los pilotos usarían una muestra declarada y no se anunciarían como una evaluación completa. ARC-1/2 medirían transformaciones de rejillas; ARC-3 requeriría su actor interactivo y contrato propios. Gamma usaría GenEval y revisión perceptual. Los datos usados para entrenar o elegir arquitectura quedarían separados de la confirmación; una comparación base/ajustado permite medir mejora incluso cuando no pueda asegurarse ausencia de contaminación en la base original.

La prueba de RSI-2 empieza después de una actualización útil: el sistema resultante debe producir mejores mejoras posteriores frente a un sistema reiniciado o congelado, con presupuesto comparable y oportunidades nuevas. Reentrenar una vez o seleccionar el mejor de muchos candidatos acredita una operación distinta. El lanzamiento comercial inicial puede centrarse en una capacidad delimitada y medida mientras esa investigación sigue abierta. Este informe conserva las propuestas de futuro y no modifica contratos, fuentes ni resultados de B22.
