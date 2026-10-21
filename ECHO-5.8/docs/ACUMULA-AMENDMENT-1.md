# ACUMULA · enmienda 1 (desarrollo, antes de congelar)

20 de octubre de 2026. Escrita antes de `preflight` y antes de jugar ninguna
familia de la sonda de examen (LavaCrossingS11N5, Dynamic-Obstacles-Random-6x6,
BlockedUnlockPickup, ObstructedMaze-1Dl) y ninguna semilla de examen
(3 000 000+). Q1–Q5, la métrica, α = 0,01, Holm y la puerta verde **no
cambian**. Datos de desarrollo: `lab/echo58/acumula/dev-*.json` (macros 1–3,
semillas 2 000 000+, sonda de desarrollo LavaGapS6, Dynamic-Obstacles-Random-5x5,
Unlock, KeyCorridorS3R3).

## 1. Cambio de menú: dos bits de rango en la firma (fuera de lo que permitía §6)

**Hallazgo.** En DistShift2 A2 la lava tiene la firma 8 (5–15 casillas, sin
borde); en el entrenamiento esa firma era suelo transitable 175 veces frente a
17 NOOP. La memoria cree «con razón» que se puede pisar. Ningún bit del menú
aprobado (tamaño, borde) separa esa lava del suelo: `silence` o `verify` solo
dejan al agente tanteando, y muere igual.

**Cambio.** La firma lleva dos bits más que el agente ya puede ver: 32 = el
identificador interior más común, 64 = el segundo. `refine(k, b)` puede usar
también esos bits. **La configuración base los oculta**: comprobado que la
memoria de partida reconstruida da exactamente las mismas tablas que la
memoria congelada de A (macro 1: 539 observaciones, capas 1 y 2 idénticas) y
un test lo fija. Es un cambio del contrato aprobado: **aprobado el 20/10/2026**
(«apruebo los bits de rango»). El revisor comprobó la identidad con A en
las 10 macros (516–572 observaciones cada una), no solo en la macro 1.

## 2. Diagnóstico (permitido por §6)

- **Las sorpresas cuentan como fallo medido.** Además de «la memoria respondió
  y el agente sufrió daño o perdió la acción», cuenta toda observación que
  contradice la regla vigente de su clave (el δ del núcleo). Motivo: en
  desarrollo, una puerta abierta y una tira corta de lava compartían clase
  morfológica; tras la ronda 4 la regla de esa clase quedaba muda y la lava de
  la sonda mataba, sin que la regla hubiera fallado nunca en la ronda.
- **Por clave, solo el bit que mejor separa.** Para cada clave culpada se
  prueba el bit que más aumenta la pureza de sus resultados observados (suma
  de la moda de cada mitad, enteros), no todos los bits.
- **Orden por niveles:** `order` (si falló la capa 1) → partir cada clave
  culpada por su mejor bit → `verify` → `silence` → `merge` de un bit común a
  ≥ 2 claves. Antes `merge` se puntuaba con todos los fallos y ocupaba todos
  los huecos. **`bound` ya no lo propone el diagnóstico** (el contrato §3 decía
  «`merge` o `bound`»); solo azar y LLM pueden elegirlo del menú.
- Las candidatas se calculan una vez por ronda: si se acepta `refine(k)`, las
  `verify(k)`/`silence(k)` que venían detrás actúan sobre una clave que ya no
  existe, entran por la puerta y no hacen nada. Gasta presupuesto de la propia
  `recursiva` (no la favorece); el informe Q5 lo señalará.

## 3. K y puerta de aceptación (permitido por §6)

- **K = 6** candidatas por ronda (antes 4), para todos los brazos.
- **Puerta lexicográfica de no inferioridad**, para todos los brazos: entra si
  el daño no sube y el éxito no baja **y** (baja el daño, o sube el éxito, o,
  si ambos empatan, el desperdicio no crece un 10 % o más; 0 → 0 cuenta como
  no crecer). Antes exigía mejora
  estricta y rechazaba ediciones que solo protegen otros mundos (p. ej.
  separar puerta y lava en la ronda 4).
- Validación: 10 mundos por familia de la ronda (20 por ronda), sin aprender.

## 4. Brazo LLM

`openai/gpt-oss-120b` en Groq, temperatura 0, respuesta JSON. Ve el mismo
diagnóstico (claves como números) y el menú completo de ediciones válidas;
elige hasta K; pasa la misma puerta. Respuestas guardadas por SHA-256 de la
petición en `lab/echo58/acumula/llm-cache/`. Se informa, no decide. En
desarrollo: 15 llamadas, 0 errores.

## 5. Desarrollo tras los cambios (`dev-20261020T164733.json`, 3 macros)

Sonda de desarrollo, suma de las 3 macros, éxitos / daño por ronda 0…5:

| Brazo | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| recursiva | 278/6 | 284/3 | 279/0 | 278/0 | 289/0 | 282/0 |
| azar | 278/6 | 270/13 | 267/12 | 254/36 | 232/76 | 221/80 |
| sin_acumular | 278/6 | 284/3 | 282/0 | 266/7 | 276/3 | 195/79 |
| fija | 278/6 | 270/13 | 265/10 | 259/15 | 196/83 | 193/79 |
| llm | 278/6 | 260/13 | 237/35 | 242/34 | 182/80 | 167/104 |

Q3 en desarrollo (configuración final frente a base, misma memoria final,
familias de examen de A en A2): daño 84,3 → 0, éxito 111 → 196. Q4: DistShift2
A2 50 daños → 0, 0 éxitos → 50.

## 6. Riesgo que se declara antes del examen: Q1

En desarrollo **Q1 falla**: la sonda empieza casi sin daño (6), y la
automejora lo que hace es **impedir que el daño suba** mientras los demás
brazos se degradan; no puede bajar tres rondas seguidas desde casi cero. Q1
no se cambia: es el criterio de automejora sucesiva del roadmap. Si en el
examen sale rojo y Q2/Q3 verdes, el resultado se leerá como «automejora que
protege y corrige, sin curva sucesiva», y B quedará **roja**.

## 7. Segunda revisión independiente (20/10)

Veredicto: congelar, con dos condiciones, cumplidas: la Aprobado: de
§1, y que el examen no se pueda perder por un fallo de red. Ahora un trabajo
que falla queda escrito como `crash` con su traza en vez de abortar el
examen. La llamada al LLM captura cualquier excepción, y las respuestas con
error no se guardan en la caché. Comprobado también: equidad entre brazos
(misma puerta, mismas semillas de validación, misma memoria de partida, `fija`
es un control válido), aislamiento de la sonda, bloques de semillas
disjuntos, informe sin errores que cambien una predicción, invariantes.
Aviso de potencia: Q2 necesita ~9 macros a favor y ninguna empatada.

## 8. Congelación

`preflight` congela el estado de A (código y entorno), los ficheros de
`echo58/acumula/`, el registro de familias, rondas, sonda, K, tamaños y
semillas de examen. `exam` se niega si algo cambió o si `exam/` no está vacío.
