# E4-BENCH-1 A · contrato D del examen (APROBADO por Roger el 2026-09-25)

Contrato de origen: `ECHO4-BENCH1-A-DESIGN.md`. Desarrollo: `lab/echo4/bench1-a-dev-v1`. Datos
congelados: `lab/echo4/bench1-data/samples.json` (sha256 `a068c4f5…`). Examen: 200 de SimpleQA,
100 de MMLU-Pro y 50 de GSM8K, que **nadie ha mirado**.

## Enmienda de modelos (orden de Roger del 2026-09-25: «máximo 2 dólares»)

- **Gemini 3.5 Flash sale del examen.** En el desarrollo costó 0,85 de 1,12 $, porque razona y
  no se puede desactivar. En el examen serían ≈3,7 $.
- **Quedan 4 modelos:** Qwen3-30B-A3B-2507, GPT-5.4 mini, DeepSeek-V4.1-Flash y Claude
  Sonnet 5. Se ejecutan en ese orden, del más barato al más caro.
- **Coste esperado:** ≈1,2 $.
- **Topes duros:** `--budget-usd 2.0`, y `--floor-usd` con el saldo actual menos 2 $. Si un
  tope se alcanza antes de un modelo, ese modelo no se ejecuta y se publica lo que haya.

## Desarrollo (SimpleQA, 50 preguntas): incorrectas M → M+R → M+R+ECHO

| Modelo | M | M+R | M+R+ECHO | Precisión M+R → ECHO |
|---|---|---|---|---|
| Sonnet 5 | 19 | 3 | 2 | 82 % → 87 % |
| DeepSeek | 18 | 9 | 3 | 74 % → 82 % |
| GPT-5.4 mini | 36 | 13 | 9 | 54 % → 57 % |
| Qwen3-30B | 31 | 9 | 6 | 65 % → 70 % |

En el desarrollo, ECHO **baja las incorrectas y sube la precisión** en los 4 modelos. A cambio
responde menos: su F-score queda por debajo del de M+R en 3 de los 4.

## Umbrales (se fijan antes del examen)

| Id | Condición (SimpleQA, 200 preguntas) | Tipo |
|---|---|---|
| D1 | % de incorrectas de M+R+ECHO < % de M+R en **al menos 3 de los 4** modelos | principal |
| D2 | precisión de M+R+ECHO ≥ precisión de M+R en al menos 3 de los 4 | principal |
| D3 | ECHO **nunca** convierte una respuesta en correcta: en cada pregunta, correcta con ECHO ⇒ correcta en M+R. 0 violaciones en todos los modelos y bancos | estructural |
| D4 | la auditoría reconstruye el informe desde los recibos con el mismo sha256 | custodia |

**Verde = D1 ∧ D2 ∧ D3 ∧ D4.**

**Se publica sin umbral:**
- el F-score, que probablemente **empeora** con ECHO: es el coste de abstenerse;
- la cobertura;
- la comparación con M (libro cerrado);
- MMLU-Pro (control negativo: se espera que ECHO se abstenga casi siempre);
- GSM8K (límite: ECHO no puede verificar cálculos).

## Qué no afirma

- Que ECHO haga más listo al modelo. Solo puede **quitar** respuestas, nunca crear una
  correcta.
- Nada sobre Gemini en el examen: solo tiene resultados de desarrollo.
- El corrector es determinista (coincidencia normalizada), más estricto que el corrector
  oficial de SimpleQA basado en un modelo. Se declara.

## Ejecución

- Herramienta: `echo4/bench1.py`, sha256 `b533c3e1ea5c308d2d6038111724c79e8421fe8fa72edf78e5f060c3f6f03458`.
- Saldo al empezar: 5,608 $. Topes: `--budget-usd 2.0 --floor-usd 3.61`.
- Salida: `lab/echo4/bench1-a-exam-v1`.
