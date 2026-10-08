# HEAT-1 — segunda variable homeostática

Fecha: 2026-09-09. Contrato cerrado antes de derivar y ejecutar las semillas
oficiales. Las semillas 17, 101, 907 y 20260903 se usaron sólo para desarrollo.

## Física y representación

HEAT-1 añade `temperature ∈ [0,127]` al `Agent`, junto a H. Ambos registros son
enteros. Una vida termina si `H=0`, `temperature=0` o `temperature=127`.
Respawn restaura H y temperatura, conservando CAM/Q/T.

La temperatura observada se reconstruye en cuatro bandas dentro de `E[B]` del
WSP existente de 16 bytes. El registro no se guarda en E, CAM ni un segundo
bus. H continúa reconstruyéndose en `E[U]`. El modo sin temperatura produce el
mismo WSP para dos temperaturas distintas y sirve como ablación de alias.

El mundo es un cargador térmico de una celda, relevante para batería/cómputo al
edge:

- `approach`: carga `H + 3`, genera `temperature + 24`, recompensa +8;
- `avoid`: refrigeración activa `H - 4`, elimina `temperature - 24`, recompensa 0;
- `wait`: consumo base `H - 1`, temperatura sin cambio, recompensa 0;
- cruzar cualquier límite vital reemplaza la recompensa por −16.

Todo se satura en 0..127. La carga prolonga energía pero calienta; refrigerar
protege del calor pero consume energía. No existe recompensa por seguir vivo,
`if temperature: action`, LLM, nueva acción ni memoria paralela.

## Banco fijado

H inicial 32, temperatura inicial 64, 60 vidas y máximo de seguridad 512 turnos
por vida. Las ocho semillas se derivan de SHA-256 sobre
`ECHO-AI/HEAT-1/2026-09-09/<índice>`; los primeros cuatro bytes big-endian son
la semilla. El informe guarda semillas y hash. Cada brazo comparte las mismas
fases:

1. **joint**: observa H y temperatura; Q/T persisten;
2. **blind**: misma física y temperatura terminal, pero el WSP sólo observa H;
3. **reset**: observa ambas, pero Q/T nacen de cero tras cada muerte;
4. **no_q**: observa ambas y conserva CAM/T, con `Q.update` desactivado.

Se guardan todas las secuencias ejecutadas. El auditor reproduce H, temperatura,
recompensas, causas de muerte, acciones por banda y duración desde la física.
El examen congelado lee Q en `(H=32,temp=80)` y `(H=32,temp=112)` sin escribir.

## Verde fijado

- En cada semilla, el doble de la mediana de duración joint de las últimas 20
  vidas es al menos tres veces la mediana blind, reset y no_q correspondiente.
- Joint supera también a los tres controles en suma total de turnos.
- En joint, `approach > avoid` desde la banda 65..96 y `avoid > approach` desde
  97..126. El examen elige approach a 80 y avoid a 112 en las ocho semillas.
- En blind, ambos exámenes tienen WSP, fila Q y acción idénticos.
- Todas las vidas terminan por un límite físico; acciones y recompensas
  reconstruyen exactamente cada fila; no hay recompensa +1 por vivir.
- Respawn conserva registros del individuo; no_q mantiene Q y restos a cero;
  `false_facts=destroyed=cortex_calls=0`; CAM ocupa 1..4096.
- El encoder sin opciones y VITA-1 sin temperatura mantienen su comportamiento.

Si falla cualquier condición, HEAT-1 queda rojo y no se cambian umbrales ni
semillas.

## Resultado medido

Rojo. Joint superó a blind y reset, pero no al control sin Q: 12.146 turnos
joint agregados frente a 22.220 sin Q. El ciclo plano 0–1–2 equilibraba carga
y refrigeración por casualidad. Las cuatro bandas también mezclaban estados
seguros y letales ante saltos térmicos de 24. Se conserva el informe
`lab/echo2_heat1_report.json`; no se rebajó el control.
