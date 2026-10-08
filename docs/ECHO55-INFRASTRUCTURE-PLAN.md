# ECHO 5.5 plan de infraestructura y desarrollo

1 de octubre de 2026. Objetivo de planificación: un candidato medido y
utilizable **antes del 1 de diciembre**, condicionado a resultados, tiempo
y financiación. No se promete cerrar todos los módulos ni equivalencia
general con modelos frontier. ECHO-4.5 sigue sin S6 verde.

Ampliación del 1 de octubre: [ECHO-RSI-1, laboratorio y evaluación](ECHO-RSI-1-LAB-PLAN.md)
documenta la línea posterior a 5.5, las puertas propuestas R0–R9 y recursos
económicos comprobados. El primer piloto propone un techo de 20–30 € dentro
del presupuesto previsto, con CPU local y una GPU alquilada. Las tarifas
del nuevo documento son un corte de consulta; se comprueban al contratar.

## Producto que se puede construir

Un agente híbrido con control y memoria ECHO, neocórtex intercambiable,
propuestas verificadas y observación de decisiones reales. «Vivo
artificialmente» se convierte en una prueba operativa de continuidad:
conservar estado tras reiniciar, aprender de consecuencias, gestionar
presupuesto, actuar durante una sesión larga y trasladar habilidades a
mundos nuevos. No es una medición de experiencia subjetiva.

Reutilizar echo-nexus y sus conectores. El núcleo debe mantener comportamiento
útil cuando el neocórtex no responde. WSP y el firewall existentes conservan
su papel: no se crea otro bus ni una vía que permita a la prosa modificar
hechos, verificador o cohortes.

## Neocórtex y pesos propios

Recomendación inicial, **a comprobar con nuestro banco**: API equilibrada
para la condición fuerte y modelo local abierto para la condición económica.
Usar proveedores distintos como réplicas de dependencia, manteniendo fijo
el modelo dentro de cada campaña.

| Opción | Función propuesta | Evidencia de disponibilidad |
|---|---|---|
| GPT-6.1 Sol por API | Propuestas de código con coste menor que Astra; comparar utilidad verificada por euro | [Catálogo oficial](https://developers.openai.com/api/docs/models), consultado 1 oct: $2 entrada / $10 salida por millón en modo estándar corto |
| Claude Sonnet 5.5 por API | Segundo neocórtex para reproducir resultados con otra familia | [Precios oficiales](https://claude.com/pricing), consultado 1 oct: $2 entrada / $10 salida por millón |
| gpt-oss-20b | Candidato de pesos disponibles de OpenAI, sujeto a memoria y ajuste real | [Ficha oficial](https://developers.openai.com/api/docs/models/gpt-oss-20b) |
| Qwen3-Coder-30B-A3B-Instruct | Control abierto especializado en código; no descartarlo por el rendimiento de otro Qwen pequeño | [Ficha del fabricante](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct): Apache 2.0, 30,5B totales y 3,3B activos |
| Qwen3 4B Instruct local instalado | Primera condición gratuita RSI; no se presume rendimiento frontier | Archivo local ya guardado por echo-nexus |

API no significa disponer de los pesos de ese modelo. Una adaptación local
requiere una base de pesos disponibles y su licencia. Los 3,3B activos de
Qwen Coder no hacen desaparecer sus 30,5B pesos del requisito de memoria.
Una configuración capaz de inferir un GGUF no necesariamente permite entrenar.

El modelo propio empezaría como adaptador LoRA/QLoRA de una base pequeña,
usando exclusivamente propuestas con ejecución verificable y ejemplos
permitidos. Antes de recolectar datos de un proveedor para entrenar otro
modelo se comprueban sus condiciones; no se presupone permiso de destilación.
No ajustar con respuestas ARC de examen ni trazas PROBE dirigidas por humanos.

## Presupuesto previsto de 180 euros

Todavía no disponible: **no se ha alquilado GPU ni iniciado inferencia de pago**.
Asignación propuesta total, incluyendo margen para extras:

| Partida | Límite propuesto |
|---|---:|
| GPU para perfiles y adaptadores | 120 € |
| Comparación por API | 30 € |
| Disco persistente y exportación | 15 € |
| Reserva para cambios, IVA y divisa | 15 € |
| Total | 180 € |

Precios públicos en dólares consultados el 1 de octubre; no son cotizaciones
en euros ni garantizan stock o impuestos. Proveedores candidatos:

| Proveedor | GPU y VRAM | Tarifa publicada | Uso propuesto |
|---|---|---:|---|
| Runpod Pods | RTX A5000 24 GB | $0,27/h | Perfil inicial de adaptación pequeña |
| Runpod Pods | A40 48 GB | $0,49/h | Mayor margen de memoria para LoRA y lotes |
| Runpod Pods | RTX 4090 24 GB | $0,74/h | Comparar coste por experimento terminado |
| Lambda | A6000 48 GB | $1,09/h | Alternativa si hay mejor disponibilidad o rendimiento |

Fuentes: [Runpod](https://www.runpod.io/pricing),
[Lambda](https://lambda.ai/instances). Se comparan Pods e instancias,
no se mezclan sus precios con Serverless. Disco y disponibilidad se consultan
al reservar. Un perfil de una hora decide según tokens/s, VRAM máxima,
tiempo total y euros por mejora: no elegir solo por precio horario.

Con una **hipótesis de precio final** de 0,50–1,00 €/h, 120 € darían
120–240 horas; es aritmética de planificación, no oferta del proveedor.
Esto puede servir para ajustes acotados, no para preentrenar un frontier.
[Guía de memoria de Unsloth](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
explica que la memoria depende del método, tamaño y contexto. Se comienza
con una base 4–8B, contexto corto y perfil real antes de escalar.

## Infraestructura mínima

CPU local o VPS económico: núcleo, cola, verificador y pruebas deterministas.
GPU por horas: entrenamiento y perfiles de inferencia. API externa:
condición de neocórtex forte; el núcleo decide cuándo consultar.

Una cola persistente con un worker basta al principio; no hace falta
Kubernetes. Cada trabajo guarda manifiesto de fuentes/pesos/datos, presupuesto,
snapshot, respuestas estructuradas, recibos y motivo de parada. Un contenedor
fija dependencias del entrenamiento. Checkpoints y adaptadores se exportan
antes de terminar la instancia para evitar pagar GPU inactiva.

Tres modos de instalación propuestos: local GGUF; núcleo local con API HTTPS;
servicio remoto para sesiones de desarrollo. El harness sigue siendo el
artefacto público; el experimento RSI actual es privado. El MCP conecta
herramientas permitidas, no concede control irrestricto al modelo.

## Camino por semanas con condiciones de salida

| Fecha objetivo | Trabajo | Solo se declara terminado cuando |
|---|---|---|
| 1–7 oct | PROBE2 y RSI1 privado; decidir siguiente contrato S6 | Recibos completos, costes reales y resultado reproducible, incluso si es rojo |
| 8–18 oct | Candidato S6, transferencia de memoria y comparación ARC de ECHO-4.5 | Supera B1–B5 y los demás criterios existentes; si falla, se mantiene pendiente |
| 19–31 oct | ECHO-5: protección del evaluador, planificación hacia atrás y reparación acotada | Cada módulo supera sus controles y conserva habilidades |
| 1–10 nov | ECHO-5.1: colaboración, selección de cómputo y evolución de bibliotecas | Ventaja frente a un agente con el mismo presupuesto total |
| 11–20 nov | ECHO-5.5: candidato con API y adaptador local pequeño | Ventaja reproducida sobre base y sobre LLM solo, con costes declarados |
| 21–30 nov | Instalación, sesiones largas, auditoría y release candidato | Replays, reinstalación, restauración de estado y exámenes nuevos pasan |

Fechas son objetivos de gestión, no pronóstico de verdes científicos. Si S6
no cierra, puede entregarse un candidato experimental en noviembre con ese
límite visible; no se renombra el rojo. Los trabajos privados no sustituyen
el roadmap de ECHO-5 ni los módulos ya planificados.

## Ingresos sin depender de prometer inteligencia general

Hipótesis comercial inicial: **servicio de instalación y evaluación reproducible
de agentes de código**, apoyado en echo-nexus y sus informes. Es vendible
por trabajo entregado mientras continúa la investigación. Oferta piloto
propuesta: instalar en un entorno del cliente, evaluar 20–30 tareas permitidas,
comparar dos configuraciones y entregar informe de aciertos, fallos y coste.

Precio de validación sugerido: 150–300 € por proyecto pequeño, con alcance
cerrado y objetivo de coste externo menor de 20 €. Es una propuesta, no
ingreso previsto ni margen asegurado; medir también horas humanas. Primero
validar interés, luego suscripción o alojamiento si existe demanda.

Próximos entregables comerciales: demo reproducible, ejemplo de informe,
texto de oferta y plantilla de alcance. No se han enviado mensajes, creado
campañas ni cobrado a nadie. La conexión de apps puede ayudar a organizar
ese trabajo; las comunicaciones a clientes se autorizan aparte.
