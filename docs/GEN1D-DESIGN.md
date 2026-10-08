# GEN-1d — confirmación de cautela heredable

Fecha: 2026-09-09. Este contrato se cierra antes de generar sus condiciones o
ejecutar el banco. GEN-1, GEN-1b y GEN-1c conservan sus resultados rojos.

## Hipótesis y tarea

Un hijo que hereda cuántas observaciones locales exige por acción aprende una
política de actuador ruidoso con menos errores que un hijo nacido con el valor
predeterminado. Sólo se transmite `evidence_budget`; CAM, Q, T y sus restos
nacen vacíos. No hay LLM, segunda memoria ni segundo bus.

Cada vida presenta un contexto WSP, permite una orden y termina. `approach` o
`avoid` es correcto; `wait` siempre falla. La consecuencia se invierte con una
secuencia determinista del 30%. La perturbación depende exclusivamente de
semilla, contexto y número de vida, nunca de la acción: todos los brazos de una
pareja reciben el mismo entorno causal.

Después de entrenar una vida, el examen consulta `Q.best` y no ejecuta física
ni escribe memoria. El KPI primario es el número de errores de esa política
congelada desde la vida 13 hasta la 40. La vida 13 empieza después de que el
presupuesto mayor haya reunido cuatro observaciones de cada una de las tres
acciones. También se conserva `EpisodesToCriterion`: ocho aciertos seguidos.

## Condiciones que aún no se han abierto

Se generan con SHA-256 a partir del dominio ASCII
`ECHO-AI/GEN-1d/2026-09-09`, el nombre de la partición y el índice decimal.
Los primeros 24 pares pertenecen a selección y otros 64, bajo el nombre
`exam`, a confirmación. El byte 0 módulo 32 fija el contexto y los bytes 1..4
en big-endian fijan la semilla. El informe almacena todos los pares y su hash.

Selección compara presupuestos 1, 2 y 4 por suma de errores tardíos; un empate
favorece 2, después 1 y después 4. El hijo hereda el ganador. Examen compara:

- heredado frente a presupuesto predeterminado 2;
- heredado frente a selección histórica (`evidence_budget=0`);
- configuración directa del ganador frente al heredado;
- ablación del entero a 2 frente al naïf;
- heredado frente a un control con actualizaciones Q desactivadas.

Todos los brazos emparejados comparten contexto, semilla y fases. Se guardan
acciones, recompensas, secuencias de examen y memorias inicial/final.

## Verde fijado

El ganador de selección debe diferir de 2. En las 64 condiciones nuevas:

1. heredado y configuración directa son idénticos; ablación y naïf también;
2. el control sin Q no acierta ningún examen ni alcanza criterio;
3. el heredado alcanza criterio en al menos 58 condiciones;
4. su suma de errores tardíos es como máximo el 80% de la naïf y menor que la
   histórica;
5. en la comparación pareada tiene más victorias que derrotas y la prueba de
   signos unilateral exacta da `p <= 0.05` (los empates no cuentan);
6. no hay hechos falsos, destrucciones CAM ni llamadas a cortex.

El auditor reconstruye selección, KPI, criterio y controles desde las filas.
Si una condición falla, GEN-1d queda rojo y no se reajusta este contrato.

## Resultado medido

Rojo. Con ruido independiente de la acción, selección transmitió 4, pero el
examen produjo 265 errores heredados frente a 272 del naïf y 225 del histórico;
18 victorias, 18 derrotas y 28 empates. El resultado congelado está en
`lab/echo2_gen1d_report.json`. Una variante de desarrollo que entrega Q en
modo greedy tras cumplir el presupuesto se conserva separada como
`lab/echo2_gen1d_dev_greedy_report.json`; tampoco es un certificado.
