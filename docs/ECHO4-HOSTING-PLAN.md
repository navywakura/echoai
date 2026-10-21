# Plan de alojamiento: echoai-4-cognitive-agentic en servidor con GPU (PLAN, pedido 2026-09-24)

No es contrato. Va **después de RELEASE**. Cifras aproximadas, a confirmar con
precios actuales y una **prueba de carga** antes de contratar nada.

## Objetivo

- **Público:** `rxlabs.org/chat`, al menos **100 usuarios ajenos a la vez**, con
  respuestas rápidas.
- **Canal propio:** una API solo para nosotros, sin límite de uso contractual.
- **Componentes:** el núcleo ECHO-4 (CPU, una instancia con memoria propia por usuario)
  y el córtex con el modelo de referencia (Qwen3-4B-Instruct-2507).

## Dimensionado

- **Carga estimada:** 100 usuarios de chat ≈ 3–5 peticiones/s en total, con unas 10–30
  generaciones simultáneas.
- **Modelo:** Qwen3-4B ocupa unos 8 GB en FP16 y unos 2,5–3 GB en AWQ. Cabe en una GPU de
  24 GB con mucho espacio para la caché de contexto.
- **Servidor de inferencia:** vLLM o SGLang, con agrupación continua de peticiones. En el
  laboratorio se usa GGUF Q4_K_M con llama.cpp; en producción se sirve **el mismo modelo**
  en su formato oficial (FP16 o AWQ). La diferencia de cuantización se documenta y se
  verifica que las pruebas de SITUATE-2 (cortafuegos) siguen pasando.
- **Latencia esperada:** primer token en 1–2 s y respuesta en pocos segundos, a verificar.
- **Núcleo ECHO:** CPU; muy barato.

## Arquitectura

- **Mínimo viable:** 1 servidor con **1 GPU de 24 GB**. Cola con prioridad: público primero y
  API propia en cola separada con tope.
- **Recomendado:** **2 GPU** (un servidor con dos, o dos servidores): una para el público y
  otra para la API propia. Da aislamiento y redundancia.
- **«Canal infinito»:** no existe capacidad infinita. Nuestro canal es ilimitado en uso,
  pero limitado físicamente en tokens por segundo; por eso va en su propia GPU.

## Coste aproximado (24/7)

| Opción | GPU | Mensual aprox. |
|---|---|---|
| Dedicado económico (tipo Hetzner GPU) | RTX 4000 Ada 20 GB | ~200 € |
| Mercado de GPU (RunPod, Vast.ai) | RTX 4090 24 GB | ~250–500 $ |
| Nube grande (AWS, GCP) | L4 / A10G | ~550–750 $ |
| Sobredimensionado | A100 | ~900–1.800 $ (innecesario) |

- **Mínimo:** ~200–500 €/mes.
- **Recomendado, con 2 GPU:** ~400–1.000 €/mes.
- **Además:** dominio y CDN (≈0), copias de seguridad y tiempo de operación (moderación,
  seguridad, actualizaciones).

## Requisitos antes de abrir al público

1. **Prueba de carga** con 100 usuarios simulados: latencia, errores y consumo reales.
2. **Seguridad:** autenticación de la API propia, límites por usuario, protección contra
   abusos, registro de actividad y moderación de contenido.
3. **Cortafuegos de ECHO activo:** lo que escriben los usuarios es testimonio, nunca hecho.
   Se avisa siempre de que se habla con una IA.
4. **Privacidad y normas:** RGPD si se guardan conversaciones (minimizar y anonimizar);
   términos de uso y aviso de IA. Consulta legal antes de abrir.
5. **Modelo híbrido:** el núcleo corre solo en el servidor; no se distribuye su código.
6. **Plan de caída:** si el córtex falla, ECHO responde desde sus hechos o avisa;
   reinicio automático.

## Qué no promete

Qwen3-4B es un modelo modesto: la fuerza del sistema es el núcleo verificador, no la
elocuencia del modelo. Alojarlo no certifica conciencia ni capacidades más allá de lo medido.

## Proveedores concretos (consultado 2026-09-24; confirmar al contratar)

- **Principal, para el público:** **Hetzner GEX45**. NVIDIA RTX PRO 4000 Blackwell de
  24 GB, i5-13500, 64 GB de RAM y 2× 512 GB NVMe, en Helsinki (UE). **214 €/mes sin IVA
  más 209 € de alta**; con IVA español del 21 % como particular, unos 259 €/mes. Precio fijo.
- **Segunda GPU, para la API propia:** **RunPod Secure Cloud**. RTX A5000 24 GB a 0,27 $/h
  (~200 $/mes 24/7) o L4 24 GB a 0,49 $/h (~360 $/mes). Se factura por segundo, así que
  puede apagarse cuando no se use. Community Cloud es más barato (RTX 4090 a 0,34 $/h),
  pero menos fiable: no se usa en producción.
- **Presupuesto:** mínimo ~214 € + IVA al mes (solo Hetzner); recomendado ~400 € + IVA
  al mes (Hetzner + RunPod 24/7), o ~250–320 € con la API de RunPod bajo demanda.
- **Orden:** primero una prueba de carga en RunPod durante unas horas; si una GPU basta,
  contratar la GEX45.

Fuentes: [Hetzner GEX45](https://www.hetzner.com/dedicated-rootserver/gex45/),
[noticia del precio de la GEX45](https://dohohub.com/news/hetzner-gex45-entry-level-gpu-server),
[precios de RunPod](https://www.runpod.io/pricing).
