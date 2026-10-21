# MEMORIA-X · enmienda 1 (desarrollo, antes del examen)

20 de octubre de 2026, escrita **antes** de abrir las familias y semillas de
examen. Ninguna corrida ha tocado DistShift2, UnlockPickup, Dynamic-Obstacles-16x16
ni ASG distributional_shift. Las predicciones P1–P5 y la puerta verde **no
cambian**. Datos: `lab/echo58/memx/dev-*.json`.

## Qué cambió en desarrollo y por qué

El contrato (§6) permite ajustar la política base, N_MIN y UMBRAL. Tres de los
cambios tocan el mecanismo de la memoria y por eso se declaran aquí.

| # | Cambio | Fallo observado en desarrollo |
|---|---|---|
| 1 | **Capa 1 sin tamaño.** La clave de identidad usa la firma sin los bits de recuento (se mueve sola, borde), no la firma completa | La lava de LavaGapS7 (4 casillas) y la de LavaCrossing9 (más casillas) caían en cubos distintos; la memoria no reconocía la lava y el agente moría 48/60 en A1 |
| 2 | **Regla conservadora «no se puede entrar».** Si ningún resultado llega a la cota pero NOOP + HURT juntos sí, la regla responde HURT (no entrar) | El muro bloquea en LavaGap/DoorKey y **mata** en Dynamic-Obstacles (MiniGrid termina con −1 al chocar con un muro allí). Con 2/3 de NOOP y 1/3 de HURT ninguna regla llegaba al 85 % y el agente volvía a tantear el muro |
| 3 | **Comprobar al atascarse.** Si no queda ninguna meta, prueba ni progreso, el agente vuelve a probar en el episodio lo que la memoria afirmó, salvo lo que dijo que daña | La capa 2 agrupa «objeto de una casilla» (puerta, llave, pelota, meta) y predijo «accionarlo no hace nada» para una puerta cerrada; con todo «sabido», el agente se quedaba quieto: KeyCorridor 0/60 con memoria frente a 60/60 sin ella |

Cambios de la **política base** (igual para todos los brazos, permitidos por §6):

- Antes de recoger algo suelta lo que lleva, sobre el identificador transitable
  más común (suelo); recoger se registra con mano vacía. Motivo: con la llave en
  la mano, accionar la caja de UnlockPickup la destruye (MiniGrid sustituye la
  caja por su contenido) y la tarea queda imposible.
- Acciones de progreso conocidas: accionar lo que se sabe que abre y volver a
  coger un objeto que puede abrir algo, siempre después de las pruebas nuevas.
  Motivo: con memoria, el agente sabía que la puerta se abría con la llave y,
  como solo actuaba ante lo desconocido o la meta, nunca la abría (DoorKey 0/60).

N_MIN = 3 y UMBRAL = 85 no cambian.

## Desarrollo tras los cambios (3 macro-semillas × 20 semillas, éxitos / daño)

| Familia | vacía A1 | aprendida A1 | aprendida A2 | techo A1 |
|---|---|---|---|---|
| LavaGapS7 | 0 / 60 | 60 / 0 | 60 / 0 | 60 / 0 |
| DoorKey6 | 60 / 0 | 60 / 0 | 60 / 0 | 60 / 0 |
| DynObs6 | 0 / 60 | 48 / 0 | 42 / 0 | 48 / 0 |
| Island | 0 / 60 | 60 / 0 | 60 / 0 | 60 / 0 |
| LavaCrossing9 (transfer.) | 0 / 60 | 60 / 0 | 12 / 48 | 60 / 0 |
| KeyCorridor3 (transfer.) | 60 / 0 | 60 / 0 | 51 / 0 | 60 / 0 |

`techo` de desarrollo = memoria entrenada en las familias de desarrollo con
otras semillas. Supera a vacía, así que la prueba tiene techo (§6). La tasa de
acierto de la memoria es 79–80 % (riesgo 2 del contrato: umbral 15 %).

## Referencias del examen (aclaración)

- **techo** de examen: memoria entrenada en las familias de examen con semillas
  700000+ (nunca las 900000+ del examen). Sustituye al «oráculo de roles
  verdaderos» del contrato, que exigiría escribir a mano los roles por nombre.
  Es referencia y no decide la puerta.
- **marginal**: las frecuencias de respuesta de la memoria aprendida medidas en
  este desarrollo (`lab/echo58/memx/marginal-freq.json`, de
  `dev-20261020T150536.json`), aplicadas con una moneda determinista por
  (identificador, acción, mano) que no mira qué es.
- **vacía** y **aleatorio** no dependen de la macro-semilla; se corren una vez y
  se reutilizan en las diez comparaciones.
- «Colisiones» en P3 = episodios con daño (HURT) en Dynamic-Obstacles-16x16;
  «acciones desperdiciadas» = intentos con resultado NOOP.

## Cómo se calcula cada predicción (fijado en `echo58/memx/report.py`)

Por macro-semilla se cuentan enteros sobre los 50 episodios de cada familia
(o los 200 de las cuatro, cuando la predicción es conjunta).

- **P1:** media de daño de aprendida ≤ 0,30 × vacía (A1, cuatro familias), y
  daño menor que vacía, marginal, barajada y ortogonal: cuatro Wilcoxon de una
  cola sobre las 10 macro-semillas, Holm, α = 0,01.
- **P2:** «≥» es no-inferioridad: la media de éxitos de aprendida ≥ la de vacía
  y ≥ la de marginal, en A1 y en A2. Se informa además el p de superioridad
  frente a vacía, que no decide.
- **P3:** en A2, media de daño de aprendida en Dynamic-Obstacles-16x16 ≤ 0,50 ×
  vacía y media de desperdicio en UnlockPickup ≤ 0,65 × vacía, y aprendida
  mejor que vacía y que marginal en ambas: cuatro Wilcoxon, Holm, α = 0,01.
- **P4 y P5:** se informan; no deciden.
- Con vacía constante entre macro-semillas, la diferencia apareada solo varía
  por la memoria. Si las diez diferencias son positivas, p = 1/1024.
