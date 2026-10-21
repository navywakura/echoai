# Plan de negocio, comunidad y marketing de echoAI (PLAN, pedido 2026-09-24)

No es asesoramiento financiero, fiscal ni legal. Cifras orientativas.

## 1. El objetivo, con números

Mantener vivo `rxlabs.org/chat` y la API cuesta, según el
[plan de alojamiento](ECHO4-HOSTING-PLAN.md):

- **Mínimo:** ~260 €/mes (Hetzner GEX45 con IVA).
- **Recomendado:** ~400–480 €/mes (con una segunda GPU).
- **Colchón:** ~100 €/mes (dominio, copias de seguridad, pasarela de pago, imprevistos).

**Meta de ingresos: ~500 €/mes netos** para cubrir el recomendado con margen. Es una
cifra pequeña y alcanzable. Por ejemplo, sería suficiente cualquiera de estas
combinaciones:

- 100 suscriptores a 5 €/mes;
- 50 suscriptores a 10 €/mes;
- 2–3 licencias comerciales o patrocinios pequeños;
- una mezcla de todo lo anterior.

## 2. Lo que aprendemos de empresas actuales (estrategias públicas, no citas)

| Referencia | Estrategia conocida | Qué tomamos |
|---|---|---|
| **Midjourney** | Equipo pequeño, sin inversores, comunidad en Discord, **solo suscripción** y rentable pronto | Suscripción simple desde el principio; la comunidad como escaparate |
| **Hugging Face** | Lo abierto y gratuito atrae a la comunidad; cobra a empresas (servicios, alojamiento, soporte) | Abrir mundos, bancos y recibos; cobrar por el uso comercial y el servicio |
| **Mistral** | Modelos abiertos para reputación y una API y licencias de pago para ingresos | El modelo híbrido: ciencia abierta, núcleo con licencia comercial |
| **OpenAI y Anthropic** | Plan gratuito limitado, suscripción, y API por uso para desarrolladores | Plan gratuito con límites, plan de pago y API con cuota |
| **Anthropic** | Diferenciarse por seguridad y fiabilidad, publicando investigación | Nuestra marca es la **honestidad**: rojos publicados, «no se cree lo que no puede comprobar» |
| **NVIDIA** | Construir un ecosistema de desarrolladores alrededor de la plataforma | Que otros conecten su LLM al núcleo de ECHO: comunidad técnica |
| **Notion y Figma** | Crecimiento guiado por el producto: se prueba gratis y se comparte | Que cada conversación con ECHO sea compartible y enseñe algo |

## 3. Qué vendemos (de más fácil a más difícil)

1. **Suscripción al chat, «echoAI Plus»: 5–9 €/mes.**
   - **Gratis:** pocos mensajes al día. Usa sobre todo el núcleo, que es barato, y el
     modelo de lenguaje con límite.
   - **Plus:** más mensajes, memoria persistente propia (ECHO recuerda al usuario, como en
     RELATION), ver la «trastienda» (qué hechos verificó y qué afirmaciones bloqueó) y
     acceso anticipado a METAVERSE-1-CHAT.
2. **Patrocinio y mecenazgo:** GitHub Sponsors, Patreon o Ko-fi, «ayuda a mantener vivo a
   ECHO». Recompensas: nombre en los créditos, acceso a notas de laboratorio antes que
   nadie y votar el próximo experimento. Es el modelo de muchos proyectos abiertos.
3. **Licencia comercial del núcleo:** gratis para investigación y uso no comercial, de pago
   para empresas. Encaja con el modelo híbrido ya decidido. Pocas ventas cubren todo el mes.
4. **API para desarrolladores:** cuota gratuita pequeña y pago por uso o paquetes. Empezar
   solo cuando el chat funcione.
5. **Contenido e IP propia:** *La fuga* como obra (libro, audio o serie de notas), y cursos o
   talleres sobre «cómo construir un agente que no se cree a su LLM».
6. **Ayudas y colaboraciones:** convocatorias públicas de investigación e innovación, y
   colaboración con universidades (la metodología de contratos y auditorías es atractiva
   académicamente). Son lentas, pero pueden cubrir años.

## 4. Controlar el gasto antes de ingresar

Lección de los equipos pequeños rentables: **no pagar infraestructura antes de tener usuarios**.

- **Fase 0 (0 €/mes):** chat en lista de espera; demo grabada; todo en el PC local.
- **Fase 1 (unos pocos €/mes):** RunPod bajo demanda, encendido solo en ventanas anunciadas
  («ECHO está despierto de 19:00 a 23:00»). Es a la vez ahorro y narrativa.
- **Fase 2 (~260 €/mes):** Hetzner GEX45 cuando haya unos 50 suscriptores o patrocinios que lo paguen.
- **Fase 3 (~400–480 €/mes):** la segunda GPU cuando la demanda lo justifique.
- **Regla:** cada paso de gasto se desbloquea cuando los ingresos del mes anterior lo cubren.

## 5. Comunidad y marketing

**Mensaje central (la diferencia):**
> *«El agente que no se cree a su propia IA.»* echoAI escucha a un modelo de lenguaje, pero
> solo cree lo que puede comprobar, y publicamos cada experimento que falla.

**Canales, por orden:**

1. **Hacker News («Show HN») y r/LocalLLaMA:** público técnico y escéptico que valora
   justo lo nuestro (rojos publicados, reproducibilidad y modelo local).
2. **Hugging Face:** el repositorio con acceso condicionado y un Space de demo.
3. **X/Twitter y LinkedIn:** un hilo por fase con un número llamativo y honesto. Ejemplo:
   «El modelo dijo 5 veces que ECHO está vivo. ECHO no se lo creyó».
4. **YouTube y vídeos cortos:** cuando exista METAVERSE-1, clips de agentes curiosos
   construyendo, discutiendo o descubriendo algo que nadie programó. Es el contenido más
   compartible que tendremos.
5. **Discord oficial (bot declarado):** comunidad, votaciones de experimentos y acceso anticipado.
6. **La web y *La fuga*:** la historia como puerta de entrada emocional; los artículos como
   puerta técnica.

**Qué no hacemos:** prometer conciencia, AGI ni vida; vender humo. La honestidad es el
activo de marca; si se pierde, se pierde todo.

## 6. Hoja de ruta y métricas

| Plazo | Hito | Métrica objetivo |
|---|---|---|
| Mes 0–1 | Lista de espera, página de mecenazgo, «Show HN» con la historia de ROLES y SITUATE | 300–1.000 personas en lista |
| Mes 1–3 | RELEASE en Hugging Face; chat en ventanas horarias con RunPod | 10–30 mecenas o suscriptores |
| Mes 3–6 | Hetzner GEX45 24/7 cuando esté cubierto; echoAI Plus | ~260 €/mes cubiertos |
| Mes 6–12 | METAVERSE-1-CHAT y vídeos; licencias comerciales; ayudas | ~500 €/mes y segunda GPU |

Métricas semanales: visitas, lista de espera, conversión de gratis a pago (en productos así
suele ser baja, de unos pocos por ciento), coste por usuario activo y abandono.

## 7. Riesgos, con honestidad

- **Audiencia pequeña:** es un nicho técnico. Mitigación: gasto por fases, sin coste fijo antes de ingresos.
- **Qwen3-4B es modesto** para chat general: vender la **transparencia** y lo que el núcleo
  hace, no la elocuencia.
- **Abuso del chat público:** límites, moderación y registro.
- **Legal y fiscal:** darse de alta para facturar (por ejemplo como autónomo en España), IVA,
  RGPD, términos de uso y pasarela de pago (Stripe o similar). **Consulta con un gestor y un abogado.**
- **Dependencia de terceros:** precios de GPU y normas de plataformas. Mantener siempre la
  opción de volver al PC local.

## 8. Primeros pasos concretos

1. Crear la página de mecenazgo (GitHub Sponsors o Ko-fi) y la lista de espera en `rxlabs.org/chat`.
2. Preparar el «Show HN» con la historia honesta: rojos, 97 % en la tribu y «no se cree que está vivo».
3. Terminar SITUATE-2, INTEGRATE y RELEASE: sin producto no hay nada que vender.
4. Consultar gestor y abogado antes de cobrar.

## 9. Revisión de la propuesta de valor (2026-09-24)

Pregunta de Nav: *¿para qué pagaría la gente?* Respuesta honesta: **no por el chat**. Con
Qwen3-4B, echoAI conversa peor que los chats gratuitos de las grandes empresas. Lo único y
medido es la **verificación**: hecho, creencia o inverificable, «no lo sé», resistencia a la
inyección, recibos y memoria verificada, independiente del LLM.

**Nueva propuesta principal:** *la capa de verificación y memoria para tus agentes de IA*,
empezando por los **agentes de código**. Un servidor MCP y una CLI, detallados en
[ECHO4-CODE-AGENT-PLAN.md](ECHO4-CODE-AGENT-PLAN.md). El chat pasa a ser escaparate y demo;
la suscripción Plus se mantiene como ingreso secundario. La ventaja debe **medirse** en
E4-CODE-1 frente al mismo agente sin ECHO y frente a herramientas existentes.
