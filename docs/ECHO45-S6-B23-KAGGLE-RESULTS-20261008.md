# S6-B23 R3: resultado del micro en Kaggle

8 de octubre de 2026. Notebook privado
`rogeernavarro/echo45-s6b23-micro-r3-20261008`. El cierre remoto se produjo
a las 06:31, hora de Madrid. Estado de Kaggle: `COMPLETE`.

El recibo `b23-closed.json` declara `DIAGNOSTIC_COMPLETE`, `valid=true`,
`s6_green=false`, 2.478 partidas físicas y 36 llamadas a los modelos. La
revisión aritmética independiente declara `valid=true`, 90 intentos lógicos
y 177 mediciones. El micro contiene 18 plazas por cada uno de los cinco
brazos y ningún ganador. `transfer={}`: desarrollo amplio y conservación
no se abrieron. Confirmación, campaña y examen B1–B5 no se ejecutaron.

| Brazo | Intentos | Ejecutados como políticas | Resultado relevante |
|---|---:|---:|---|
| M23, selector nuevo sin LLM | 18 | 18 | Cero pases. Máximo +9 niveles, con pérdidas individuales en cinco casos. |
| M22, buscador anterior | 18 | 18 | Cero pases. Máximo +8 niveles, con pérdidas individuales. |
| R22, control aleatorio | 18 | 18 | Cero pases. Máximo +8 niveles, con pérdidas individuales. |
| N7, Qwen2.5-Coder 7B | 18 | 0 | 18 propuestas inválidas antes del simulador. |
| N14, Qwen2.5-Coder 14B | 18 | 0 | 18 propuestas inválidas antes del simulador. |

La base del micro son 61 niveles en 14 partidas conocidas. Ganancia global
de niveles no autoriza promoción cuando otra partida pierde niveles o score.
Hubo algunas mejoras de +1 sin pérdidas; el umbral de aceptación exige al
menos +2 y ninguna pérdida individual. El micro utiliza un único recorrido
por brazo, así que incluso un ganador habría requerido confirmación posterior.

## Diagnóstico de las llamadas al neocórtex

Los 36 procesos de inferencia devolvieron código de salida correcto y su
contabilidad figura en `b23-model-budget.json`. En los `result.json` de la
evidencia completa, 33/36 salidas empezaban con un bloque de código Markdown
etiquetado como JSON; el parser del contrato exigía JSON puro. Las otras tres tenían
una estructura inválida. Un análisis retrospectivo que retiró solo las
cercas y el marcador final encontró **0/36 propuestas legales**: también
había listas de valores permitidos donde se pedía un escalar, guardas con
texto de ejemplo o claves fuera del esquema. Ese análisis no altera los
veredictos congelados ni ejecuta candidatos.

El prompt contenía un objeto `response_schema` que representaba la lista de
valores permitidos para `HOLD` y una cadena descriptiva para `when`. Varios
outputs copiaron esa plantilla como si fuera una propuesta. Es un indicio
concreto de ambigüedad de la interfaz; la evidencia no permite atribuir
cuánto corresponde al modelo y cuánto al prompt. En este R3, 7B y 14B no
recibieron feedback de pérdidas reales porque ninguna salida pasó el parseo.
No se ha demostrado que 14B razone mejor o peor que 7B sobre estas reglas.

El siguiente contraste de neocórtex requiere una condición nueva declarada:
un ejemplo **sintáctico** legal y neutral, diagnóstico de formato separado
de los casos científicos, y verificación de que las propuestas pasan el
validador antes de gastar otra batería completa. Ese ejemplo no debe
contener ninguna solución ni control humano. La prueba congelada R3 seguirá
siendo el resultado original. La decisión sobre B24 debe considerar primero
esta limitación; aumentar investigadores que producen cero políticas legales
no mide cooperación.

Recibos locales: [cierre](../lab/kaggle/s6b23-20261008/r3/r3-output/b23-closed.json),
[micro](../lab/kaggle/s6b23-20261008/r3/r3-output/b23-micro.json),
[auditoría aritmética](../lab/kaggle/s6b23-20261008/r3/r3-output/b23-arithmetic-review.json),
[evidencia íntegra](../lab/kaggle/s6b23-20261008/r3/r3-output/b23-evidence.tar.gz).
