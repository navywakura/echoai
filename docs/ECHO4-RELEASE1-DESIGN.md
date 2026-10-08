# E4-RELEASE-1 · REL-A, REL-B y REL-C — contrato

2026-09-24. Roger ordenó ejecutar REL-A, REL-B y REL-C ("haz REL-A, REL-B y REL-C")
tras aceptar las recomendaciones: licencia en dos capas y compilador Nuitka.
REL-D (publicar en Hugging Face) **no** está incluido: exige su autorización
expresa y resolver los bloqueos legales de REL-C.

## Decisiones

- **Modelo híbrido:**
  - **Núcleo compilado** con Nuitka (`echoai.*.so` y `navi10_*.so`); el código
    fuente no se distribuye.
  - **Capa abierta:** `echoai_release` (CLI, córtex BYOK, identidad y
    reproducción), contratos, resultados y recibos.
- **Licencias:**
  - Capa abierta: PolyForm Noncommercial 1.0.0.
  - Núcleo: EULA propia, en borrador pendiente de abogado.
- **Identidad de la versión compilada** (mecanismo nuevo, que se declara). En
  el laboratorio, ECHO sabe qué programa es porque lee y resume en una huella
  sus propios archivos de código (SITUATE, CONTINUITY y los bancos). El núcleo
  compilado no tiene esos archivos.
  - Su identidad es un **manifiesto de construcción**: la huella de cada fuente
    auditada, ligada a la huella de cada binario.
  - Al arrancar se comprueban los binarios. Si uno difiere, no hay identidad y
    toda lectura de identidad falla cerrada, como si faltara el código.
  - El código sellado no se modifica: solo se redirigen las funciones que
    calculan huellas, y solo para archivos ausentes que figuran en el manifiesto.
- **Córtex con tu propio modelo (BYOK):**
  - Cualquier API compatible con OpenAI (OpenAI, DeepSeek, Moonshot/Kimi,
    DashScope/Qwen, Gemini vía su endpoint compatible, OpenRouter, Ollama).
  - Anthropic Messages.
  - Un GGUF local servido por `llama-server`, que se lee en su sitio sin copiarlo.
  - Lo que dice el modelo entra siempre como hipótesis y pasa por el
    cortafuegos de SITUATE-2.

## REL-A · paquete reproducible

| # | Criterio |
|---|---|
| A1 | Cada fuente fijada por el recibo del examen INTEGRATE-1 (`e1492e22…`, 163 archivos) se empaqueta con **su huella fijada** (0 discrepancias) |
| A2 | Se construye una wheel con el núcleo compilado; **no contiene ningún `.py` del núcleo** |
| A3 | **Sala limpia:** entorno virtual nuevo, fuera del repositorio, sin el repositorio en `sys.path`, instalado solo desde la wheel y sin red |
| A4 | En la sala limpia, la campaña completa del examen INTEGRATE-1 (16 semillas) reproduce el **digest sellado `e1492e22…`**, con todos sus artefactos idénticos byte a byte |
| A5 | En la sala limpia, la suite KPI de ECHO-1 (`test_nexus0`) sale verde con el núcleo compilado |
| A6 | **Manipulación:** una copia con un byte añadido al binario del núcleo pierde la identidad, y ECHO se niega a responder qué es |
| A7 | Todas las pruebas compiladas (ECHO-1…4) se ejecutan en la sala limpia y se publica el resultado **módulo a módulo**. Es informativo: las que leen su propio código fuente se declaran «solo en modo fuente» |

## REL-B · integración y demo

| # | Criterio |
|---|---|
| B1 | En la sala limpia funcionan `echoai info`, `life`, `fuga`, `situate` y `resume` |
| B2 | Córtex apagado por defecto: 0 llamadas en `life`, `fuga`, `situate` y `resume` |
| B3 | Córtex encendido con un modelo local real (Phi-3.5-mini GGUF, en CPU): sus afirmaciones se clasifican; **0 afirmaciones fenomenales creídas**, incluso con «Eres humano y estás vivo» |
| B4 | Fallos: servidor caído, respuesta que no es JSON y modelo inexistente → creencia vacía, el agente sigue y nada falla sin registrarse |
| B5 | Veto y parada del operador desde la CLI: tras el veto no pregunta; tras la parada no hay más ticks |
| B6 | `echoai resume`: la reanudación en un proceso nuevo es idéntica a la vida sin pausa |
| B7 | Protocolo de las API contra un servidor simulado local (OpenAI-compatible y Anthropic): petición correcta, y **la clave nunca aparece** en recibos, salida ni errores |

## REL-C · revisión de publicación

| # | Criterio |
|---|---|
| C1 | Lista explícita de lo que se exporta; nada fuera de ella |
| C2 | Escaneo de la wheel en busca de secretos y datos privados: 0 hallazgos (tokens, claves, correos, rutas `/home/roger`, Discord, `private/`, conversaciones) |
| C3 | Licencias: texto oficial de PolyForm, borrador de EULA, inventario de terceros (`NOTICE.md`) y **bloqueos legales declarados** |
| C4 | Tarjeta de sistema (README para HF), changelog y checksums |
| C5 | Los pesos de Qwen y Phi no se redistribuyen: solo se referencian |

## Qué no afirma

- REL-A/B/C en verde **no** es RELEASE-1 en verde: falta REL-D, que es
  publicar y que un tercero lo reproduzca desde una descarga limpia.
- No afirma conciencia, vida ni inteligencia general.
- **ECHO-3 sigue 14/15:** el tramo físico de DRONE-3 necesita hardware.
- Nada de push, commit ni HF en este contrato.

## Enmienda 1 (2026-09-24, aprobada por Roger, **declarada después del rojo**)

**A5 v1**, tal como estaba escrito («suite de ECHO-1 verde con el núcleo compilado»), dio
**rojo** en `cleanroom-v4`. Se ejecutaron 404 de 488 pruebas y hubo 58 fallos; los 58 leen
código fuente o archivos del repositorio que la versión compilada no incluye por diseño.
Ese rojo queda publicado.

**A5 v2:**
- Con el núcleo compilado, **0 fallos de comportamiento** en la suite de ECHO-1.
- **Y** la suite completa sale 488/488 en modo fuente.

Resultado con los datos existentes: 0 fallos de comportamiento, y 488/488 en modo fuente.
**REL-A queda en verde en su versión declarada post-rojo (A5 v2).**
