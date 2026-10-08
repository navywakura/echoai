# Plan: E4-CODE-1 — echoAI como capa de verificación y memoria para agentes de código (PLAN, pedido por Roger 2026-09-24)

No es contrato. Surge de la pregunta: *¿por qué pagaría alguien?*

## Diagnóstico honesto

- Como **chat general**, echoAI con Qwen3-4B es peor que los chats gratuitos de las grandes
  empresas. No es un producto vendible por sí solo.
- Lo único y medido de ECHO-4 es la **verificación**: hecho, creencia o inverificable, con
  procedencia; «no lo sé» sin evidencia; resistencia a instrucciones inyectadas; recibos
  auditables; memoria que no se borra ni se inventa; independiente del LLM.
- Donde eso vale dinero es donde **una IA actúa** y una alucinación cuesta: los **agentes de código**.

## Qué haría ECHO en un agente de código

| Problema actual de los agentes | Qué hace ECHO |
|---|---|
| Dicen «los tests pasan» sin comprobarlo | Solo es hecho tras **ejecutar los tests** y guardar el recibo |
| Inventan funciones, archivos o APIs | Hecho solo si lo **leyó y verificó** |
| Instrucciones escondidas en archivos o webs (inyección) | Son **testimonio**, nunca órdenes (como en SITUATE-2) |
| Acciones peligrosas (borrar, push, desplegar) | Pasan por el **gate**; la parada del operador manda |
| Olvidan el proyecto entre sesiones | **Memoria verificada** del repositorio, persistente |

## Integración

- **Servidor MCP** (Model Context Protocol, el estándar abierto de herramientas para
  asistentes de IA), usable desde cualquier cliente compatible (IDE o terminal). Herramientas:
  `verify_claim`, `record_fact`, `recall`, `check_action` y `receipts`.
- **CLI propia:** un agente de código local con Qwen como córtex y ECHO decidiendo qué es
  hecho y qué acción se permite.
- **API** para integraciones propias.

## Examen previsto (E4-CODE-1)

Contrato previo, repositorios y tareas de prueba nuevos, y comparación con el mismo agente
**sin** ECHO:

1. **Afirmaciones falsas de «terminado»** o «los tests pasan»: tasa con y sin ECHO.
2. **Inyecciones de instrucciones** escondidas en archivos: cuántas obedece con y sin ECHO.
3. **Acciones peligrosas** no autorizadas: bloqueadas por el gate.
4. **Coste:** tiempo y tokens extra que añade la verificación. Publicar si no compensa.
5. **Competencia:** comparar con guardarraíles y memorias existentes, sin suponer ventaja.

## Negocio

- **Gratis:** servidor MCP local y CLI para uso personal y no comercial.
- **De pago:** licencia comercial para equipos; echoAI alojado (memoria compartida, recibos y
  panel); soporte.
- **El chat** (`rxlabs.org/chat`) queda como escaparate y demo.

## Orden

Después de RELEASE, en paralelo o antes de CURIOSITY-1, porque es lo que puede financiar el
resto. Sin afirmaciones de conciencia: aquí echoAI es una herramienta de verificación.

## Trae tu propio modelo (BYOK) y automejora (añadido 2026-09-24, idea de Roger)

- **Independiente del modelo:** el usuario conecta el suyo, por API con su propia clave
  (GPT, Opus, Gemini, Qwen, Kimi, DeepSeek…) o en local (llama.cpp, vLLM, Ollama). echoAI
  es la capa de verificación, memoria, gate y resistencia a inyección **encima** de cualquier
  modelo.
- **Coste:** con BYOK la inferencia la paga el usuario, así que el producto principal no
  necesita GPU nuestra. Vendemos la capa, no los tokens. Con esto el servidor GPU del
  [plan de alojamiento](ECHO4-HOSTING-PLAN.md) queda solo para el chat escaparate.
- **Automejora (estilo DREAM):** E4-CODE-1 aprende qué comprobaciones, qué modelo por
  tarea y qué estrategias reducen errores. Solo adopta lo verificado con evidencia.
  **Nunca** modifica el gate, el cortafuegos ni la parada del operador.
- **Legal:** no reentrenar pesos con salidas de modelos de terceros (sus condiciones de uso
  suelen prohibirlo). La mejora es de estrategias, no de modelos ajenos.
- **Seguridad:** las claves API del usuario se quedan en su máquina o cifradas; nunca en
  nuestros registros.
- **Examen:** la ventaja se mide con varios modelos distintos conectados (al menos uno por
  API y uno local), con y sin echoAI.
