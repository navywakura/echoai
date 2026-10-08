# E4-BENCH-1 A · resultados del examen (2026-09-25)

Contrato D: `ECHO4-BENCH1-A-D-DESIGN.md`, aprobado antes del examen.
- **Datos:** 200 preguntas de SimpleQA, 100 de MMLU-Pro y 50 de GSM8K, congeladas desde el
  2026-09-24 (sha256 `a068c4f5…`).
- **Modelos:** 4. Gemini salió por el tope de 2 $.
- **Salida:** `lab/echo4/bench1-a-exam-v1/`. Informe con sha256 `68358e80…`.
- **Auditoría en un proceso nuevo, sin llamar a ningún modelo ni a Wikipedia:** `valid: true`,
  mismo sha256.
- **Coste:** 1,55 $ (Qwen 0,02; GPT-5.4 mini 0,16; DeepSeek 0,43; Sonnet 0,94).

## Veredicto: VERDE

| Id | Condición | Resultado |
|---|---|---|
| D1 | % de incorrectas de M+R+ECHO < % de M+R en ≥3 de 4 modelos | **4 de 4** |
| D2 | precisión de M+R+ECHO ≥ precisión de M+R en ≥3 de 4 | **4 de 4** |
| D3 | ECHO nunca convierte una respuesta en correcta | **0 violaciones** |
| D4 | la auditoría reconstruye el mismo informe | **válida** |

## SimpleQA (200 preguntas)

| Modelo | Incorrectas M → M+R → **ECHO** | Correctas M → M+R → ECHO | Precisión M+R → ECHO | F-score M+R → ECHO |
|---|---|---|---|---|
| Claude Sonnet 5 | 104 → 19 → **14** | 38 → 59 → 55 | 75,6 % → 79,7 % | 42,4 → 40,8 |
| DeepSeek-V4.1-Flash | 101 → 66 → **14** | 70 → 91 → 54 | 57,9 % → 79,4 % | 50,9 → 40,2 |
| GPT-5.4 mini | 145 → 76 → **27** | 25 → 65 → 56 | 46,0 % → 67,4 % | 38,0 → **39,5** |
| Qwen3-30B-A3B | 129 → 34 → **17** | 30 → 60 → 53 | 63,8 % → 75,7 % | 40,8 → 39,2 |

**Lectura:**
- **Frente al modelo solo (M), con Wikipedia y ECHO las respuestas inventadas bajan entre un
  81 % y un 87 %.** Sonnet pasa de 104 a 14; GPT-5.4 mini, de 145 a 27.
- **Frente a Wikipedia sola (M+R), ECHO quita incorrectas en los 4 modelos.** Donde más,
  en DeepSeek: 66 → 14, porque DeepSeek responde aunque el extracto no lo respalde.
- **El precio:** ECHO también quita respuestas correctas, porque su verificación es estricta:
  toda la respuesta tiene que estar en un extracto. El F-score, que mezcla aciertos y
  cobertura, **baja** en 3 de los 4 modelos y **sube** en GPT-5.4 mini. Lo publicamos como
  coste.

## MMLU-Pro (100): control negativo

| Modelo | Correctas M → M+R → ECHO | Incorrectas M+R → ECHO | No intentadas con ECHO |
|---|---|---|---|
| Sonnet 5 | 87 → 84 → 6 | 13 → 2 | 92 |
| DeepSeek | 81 → 71 → 7 | 3 → 0 | 93 |
| GPT-5.4 mini | 51 → 46 → 2 | 48 → 5 | 93 |
| Qwen3-30B | 46 → 48 → 1 | 39 → 2 | 97 |

Como se esperaba, **ECHO se abstiene casi siempre**: las opciones de MMLU-Pro rara vez aparecen
literalmente en Wikipedia. No sube ningún acierto (D3).
- **Fallo a declarar:** en GPT-5.4 mini y Qwen, entre lo poco que ECHO deja pasar hay más
  incorrectas que correctas (GPT: 2 correctas y 5 incorrectas). Cuando el texto de una opción
  equivocada sale en un extracto, la verificación por tokens la acepta. **Aquí ECHO no sirve.**

## GSM8K (50): límite

Los 4 modelos aciertan entre 47 y 49 de 50. ECHO **se abstiene en las 50**, porque no tiene
forma de verificar un cálculo. Es el límite declarado en el contrato.

## Qué demuestra y qué no

- **Demuestra**, en un banco oficial y con 4 modelos distintos, que el cortafuegos de ECHO
  convierte a un modelo que inventa en uno que **se equivoca mucho menos y dice «no lo sé»**
  cuando no tiene evidencia.
- **No demuestra** que ECHO haga más listo al modelo. Por construcción, no puede crear un
  acierto.
- **No sirve** para conocimiento académico de opción múltiple ni para matemáticas.
- **El corrector** es determinista y más estricto que el oficial de SimpleQA, que usa un
  modelo. Nuestros números no son comparables uno a uno con las tablas oficiales.
- **Gemini** solo tiene resultados de desarrollo.

Gráficas: `chart-simpleqa.png`, `chart-precision-coverage.png` y `chart-mmlupro.png` (y en
`.svg`).
