# HEAT-1b — temperatura observable bajo carga ambiental

Fecha: 2026-09-09. Contrato cerrado antes de derivar o ejecutar semillas
HEAT-1b. HEAT-1 queda rojo: su ciclo plano de exploración equilibraba por
casualidad carga y frío, y el control sin Q sobrevivía más.

HEAT-1b conserva los dos registros enteros H/temperatura, muerte en sus límites,
memoria entre vidas, examen congelado y cuatro controles. Cambia dos elementos
justificados por aquel diagnóstico:

1. temperatura usa ocho bandas de 16 unidades en el mismo `E[B]`, porque un
   salto térmico de 24 mezclaba dentro de una banda estados seguros y letales;
2. `wait` absorbe +16 de calor ambiental. El robot está en un recinto caliente:
   quedarse quieto no refrigera y la refrigeración activa es necesaria.

Física: cargar `(+3 H,+24 temp,+8 r)`, refrigerar
`(-4 H,-24 temp,0 r)`, esperar `(-1 H,+16 temp,0 r)`. Un límite reemplaza r
por −16. No hay recompensa por vivir ni regla de acción basada en temperatura.

Se ejecutan 60 vidas desde H=32/temp=64. Doce semillas nuevas proceden de los
primeros cuatro bytes SHA-256 de
`ECHO-AI/HEAT-1b/2026-09-09/<índice>`. Joint, blind, reset y no_q comparten
fases. El auditor reproduce cada acción, recompensa, banda y muerte.

## Verde fijado

- Joint supera en turnos totales a blind, reset y no_q en cada semilla y su
  suma agregada es al menos el doble de cada control.
- La mediana de las últimas 20 vidas de joint supera a cada control en al menos
  8/12 semillas; las comparaciones y empates se publican.
- Agregado joint: `approach > avoid` en 65..96 y `avoid > approach` en
  97..126. En cada semilla, el examen congelado elige approach a temp=80 y
  avoid a temp=112.
- Blind produce WSP, Q y acción idénticos en ambas temperaturas.
- Todas las vidas terminan por H, frío o calor y son reproducibles desde sus
  acciones. No_q conserva Q/restos a cero. Respawn conserva las memorias salvo
  el reset Q/T declarado.
- WSP sigue midiendo 16 bytes; `false_facts=destroyed=cortex_calls=0`.

No se cambian estas condiciones después de abrir las doce semillas.

## Resultado medido

**Verde.** Joint acumuló 20.786 turnos frente a 7.221 blind, 5.293 reset y
7.186 no_q. Superó individualmente a los tres controles en 12/12 semillas y
su suma fue más del doble en los tres casos. La mediana de las últimas 20 vidas
ganó 12/12 frente a blind/reset y 11/12 frente a no_q.

La política congelada eligió cargar a 80 y refrigerar a 112 en todas las
semillas; blind produjo la misma observación, fila y acción en ambas. En bandas
65..96 joint ejecutó 8.272 cargas frente a 1.326 refrigeraciones; en 97..126,
491 frente a 7.870. Murió 641 veces por calor y 79 por energía: enfriar evitó
calor a cambio de consumir H, por lo que el segundo límite tuvo coste real.

Las 2.880 vidas y todas sus acciones fueron reproducidas por el auditor.
Nacimientos vacíos, 59 resets Q/T declarados por brazo reset, Q/restos no_q a
cero y `false_facts=destroyed=cortex_calls=0`. Certificado:
`lab/echo2_heat1b_report.json`.

El banco prueba control conjunto de batería/temperatura en un cargador térmico
sintético. No mide todavía sensores físicos, latencia térmica real ni un dron.
