# ECHO-4.5 · S6-B: estrategias de juego · contrato B0

Autorizado por Nav el 2026-09-27: «hagamos S6-B». Esta orden abre la fase B
aunque S6-A salió rojo. El resultado de A no cambia. Este contrato se fija antes
de generar propuestas o abrir el examen de B.

## Alcance y base

La base es `Arc3EchoV57`, que **ya existía**: 494 niveles en gym-test v3 frente
a 369 de v5.6 (tres semillas). En los ocho juegos oficiales de desarrollo su
puntuación media baja de 1,033 a 1,000; no se declara mejora universal.

El modelo propone **estrategias de control de los mecanismos existentes**:
parámetros enteros y reglas condicionadas por observaciones e historia. Puede
cambiar cuánto explorar, qué evidencia exigir o cuánto esperar tras un reinicio.
No puede escribir Python, cambiar el agente, añadir un algoritmo, leer el estado
oculto del simulador ni identificar semillas, familias, colores o juegos. Es un
alcance menor que inventar operaciones nuevas en S6-A, y se publica como tal.

Formato, límites y sensores permitidos: `echo_arc/strategy.py`. Máximo ocho
reglas. Una propuesta sustituye la estrategia anterior completa; las reglas se
aplican en orden. SIN FILTRO incorpora sucesivamente las mismas propuestas de
ECHO válidas; su estrategia final es la última válida, sin escogerla por resultados.
Ningún brazo recibe el contenido del examen.

## Campaña gratuita B0

- Qwen/Qwen2.5-Coder-7B-Instruct, temperatura 0,7, top-p 0,95, máximo 400 tokens.
- **30 llamadas por brazo**, seis rondas de cinco. Misma fuente, semillas y
  configuración del modelo. Se publica esta diferencia respecto de las 300 de A.
- Cuatro brazos: SEMILLA, FIJO, ECHO y SIN FILTRO. Cero API de pago.
- A: semillas 0–7, versiones 2 y 3, rep 0, **600 acciones** (16 juegos).
- B: semillas 20–23, versiones 2 y 3, rep 0, 600 acciones (8 juegos).
- FIJO: petición genérica fija con tres fallos de A del estado actual.
- ECHO: P1 casi-acierto, P2 grupo de fallos, P3 generalizar una mejora aceptada
  (elegible tras la primera aceptación), P4 diario. Solo estadísticas y trazas de A, sin etiquetas
  del generador. Selector entero de A: aceptadas*1000//(intentos+1)+300//(intentos+1).
- V1: JSON acotado, sin nombres fuera de la lista permitida; no ejecutar código
  del modelo. V2: ejecutar A dos veces, acciones idénticas, en trabajadores con
  plazo y límites de recursos. V3: **al menos dos niveles más en A** que la
  estrategia vigente, con exactamente el mismo presupuesto. No exigir acertar
  primero el fallo de la petición: aprendizaje de la criba de S6-A.
- V4: niveles y puntuación total en B no disminuyen respecto de la estrategia
  vigente. Se registran regresiones individuales aunque el total pase.
- Cache de mediciones ligada a fuentes, estrategia, versión, semilla, rep y
  presupuesto; replay final en directorio vacío, sin cache de la campaña.
- Peticiones, respuestas, tokens, errores y veredictos en diario encadenado;
  respuestas guardadas antes de verificar; reanudar sin pedirlas de nuevo.

## Examen único después de congelar las cuatro estrategias

Semillas **8000–8059**, versiones 2 y 3, reps 0, 1 y 2, 2000 acciones.
120 juegos, 1800 niveles por brazo sumando reps. No son las semillas 5000–5099
de S5-D ni las 1000–1059 de gym-test. No ajustar nada después de abrirlos.
Repetir rep 0 de las cuatro estrategias en proceso nuevo, comparando acciones,
frames y métricas. Solucionador: 600/600 niveles y generación determinista.
Si dos brazos tienen estrategias idénticas, comparten la medición de esa
estrategia; el replay usa un almacén independiente del de la medición inicial.

| Id | Condición para verde |
|---|---|
| B1 | ECHO completa al menos un 5 % más niveles que SEMILLA y su puntuación no baja |
| B2 | ECHO completa más niveles que FIJO |
| B3 | ECHO completa más niveles que SIN FILTRO |
| B4 | En ocho juegos oficiales de desarrollo (reps 0–2, 2000 acciones), niveles y puntuación de ECHO no bajan frente a SEMILLA |
| B5 | fuentes protegidas intactas, diarios válidos, reconstrucción de las estrategias y replay exactos; ningún examen en los prompts |

**S6-B0 verde = B1 ∧ B2 ∧ B3 ∧ B4 ∧ B5**. La tasa de aceptación temprana/tardía
se informa como diagnóstico, sin condición adicional. Si falta una medida,
queda pendiente; no se llama verde. Si falla una condición, se publica rojo.
No se garantiza verde ni una fecha de mejora. Repetir exige contrato nuevo y
semillas nuevas; el examen B0 no se convierte en entrenamiento durante B0.

## Integridad y calendario

Congelar antes de la primera propuesta: agente, runner, gym, estrategia,
controlador, contrato y manifiesto de entornos oficiales de desarrollo.
Paquete Kaggle privado: fuentes y datos A/B únicamente; **sin entornos oficiales,
semillas de examen ni claves**. El examen y los ocho juegos se miden localmente.
No publicar un envío de competición desde esta campaña.

Cuota comprobada: 2 h 27 min de GPU gratis; reinicio 2026-10-03 00:00 UTC.
Generación y verificación tienen checkpoint; agotar cuota no autoriza pago.
La duración se estima con velocidad observada, y el cierre depende también
del examen CPU y la auditoría. S5-E sigue siendo un examen separado pendiente:
S6-B0 compara contra v5.7, no certifica por sí solo v5.7 frente a v5.6.
