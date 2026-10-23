# B v3 · ACUMULA-3 — contrato (APROBADO por Nav el 20/10/2026)

20 de octubre de 2026. Pista B del [roadmap](ROADMAP.md). **Versión nueva tras
dos rojos**: B v1 roja en examen ([resultados](ACUMULA-RESULTS.md)), B v2
cerrada roja en desarrollo ([nota](ACUMULA2-DEV-NOTE.md)). Ninguno de los dos
se reetiqueta. Origen: [investigación B v3](B3-INVESTIGACION.md) (§6:
prototipo de desarrollo). Aprobación de Nav: «sí, apruebo, adelante con el
contrato B v3, puedes seguir hasta hacer el examen».

## 1. Afirmación (y lo que no afirma)

> ECHO **elige y encadena** ediciones de su memoria **y de su política** a
> partir de sus propios fallos medidos, ronda tras ronda, de forma que cada
> ronda falla menos en mundos nuevos que la anterior y mejor que los controles.

**No afirma** que ECHO invente conductas: las piezas de política (§2) las
diseñé yo (Claude) mirando trazas de familias de desarrollo. El control
`piezas_dadas` (todas las piezas desde el principio) lo mide y **se informa**.

## 2. Agente y menú

- **Agente base de todos los brazos:** el de A con los bits de rango de B v1
  (`acumula/agent.py`) **más el arreglo de la mano** (un intento fallido de
  coger con la mano llena cuenta, en ese episodio, contra coger ese id). Es un
  defecto de contabilidad del agente base, no un elemento del menú.
  `memx/` y `acumula/` no se tocan: el agente nuevo hereda
  (`b3/policy.py`).
- **Menú de memoria:** el de B v1 tras la enmienda 1 (`silence`, `verify`,
  `refine` con bits de rango, `merge`, `bound`, `order`).
- **Menú de política** (piezas genéricas, sin nombres; se encienden y no se
  apagan):

| Pieza | Regla | Señal que la propone |
|---|---|---|
| `commit` | no soltar lo que llevas para cambiarlo por algo ya cogido en este episodio, mientras lo que llevas pueda abrir algo alcanzable que no sea pared (id más común del borde) | `pickdrop`: un id cogido ≥ 3 veces en un episodio fallido |
| `no_repick` | si vuelves a coger lo que soltaste tú en esa casilla sin que nada haya cambiado (ninguna casilla abierta, nada nuevo cogido), no vuelvas a coger ese id, en ningún sitio, hasta que algo cambie | `pickdrop`, **solo junto con `commit`** |
| `no_retoggle` | si vas a accionar una casilla que ya cambiaste en este episodio, deja de accionar el id que tiene ahora, en todo el episodio (en la práctica: no volver a cerrar una puerta abierta de ese tipo) | `retoggle`: una casilla cambiada ≥ 3 veces |
| `clear` | soltar donde no te corte el paso (o andar ≤ 8 pasos hasta un sitio así) | `blockdrop`: una suelta redujo la zona alcanzable |
| `wander` | sin nada que probar, ir a la casilla alcanzable menos visitada | `idle`: ≥ 20 pasos quieto seguidos |

  La pareja `commit`+`no_repick` se ofrece también junta (misma señal).

## 3. Cómo propone ECHO y puerta

Al final de cada ronda: candidatas de memoria del diagnóstico de B v1
(enmienda 1, primeras K = 6) **más** las piezas propuestas por las señales de
los episodios fallidos de la ronda, por frecuencia de la señal. Sin LLM;
córtex apagado.

**Puerta estricta (B v2, igual para todos los brazos):** cada candidata, en
orden, se valida en 5 semillas × 4 familias de la mezcla, sin aprender; entra
si el daño no sube, el éxito no baja y mejora estrictamente daño, éxito o
desperdicio.

## 4. Rondas, sonda, brazos

- **Mezcla (todas las rondas, B v2):** DistShift1 · LavaCrossingS9N3 ·
  KeyCorridorS3R2 · BlockedUnlockPickup; 10 semillas por familia y ronda;
  5 rondas; el agente aprende en línea.
- **Sonda de examen** (30 episodios por familia, régimen A2, cada familia en
  una copia de la memoria que aprende en línea y se tira):
  **LavaCrossingS11N5 · DistShift2 · ObstructedMaze-2Dlh ·
  Dynamic-Obstacles-Random-5x5**. Respecto a B v2 se cambian
  ObstructedMaze-2Dl → **2Dlh** y Dynamic-Obstacles-Random-6x6 →
  **Random-5x5**, porque miré trazas de esas dos familias durante la
  investigación (semillas 7 000 000+). Decisión mía, declarada.
- **Semillas de examen: 8 000 000+** (nunca usadas: B v1 usó 3 000 000+, B v2
  reservó 6 000 000+ y no hizo examen; desarrollo 5 000 000+ y 7 000 000+).
  10 macros.

| Brazo | Qué hace |
|---|---|
| **recursiva** | acumula ediciones de memoria y piezas aceptadas |
| azar | mismo menú (memoria + piezas), tantas candidatas como `recursiva` habría propuesto esa ronda, elegidas al azar; misma puerta |
| sin_acumular | cada ronda vuelve a la base y propone solo desde esa ronda |
| fija | sin ediciones (solo más datos) |
| lote_final | sin ediciones hasta la ronda 5; entonces todo el presupuesto, desde todos los fallos vistos |
| vacia_online | memoria vacía aprendiendo en línea en la sonda (sin rondas) |
| piezas_dadas (**se informa**) | todas las piezas encendidas desde r0; ECHO solo edita la memoria |

## 5. Predicciones (escritas antes de medir)

Métrica: **episodios fallidos en la sonda** por macro (4 × 30); el daño se
informa al lado.

- **Q1 · mejora sucesiva:** la media sobre las 10 macros de fallos en sonda
  de `recursiva` baja estrictamente en **≥ 3 transiciones seguidas** de las 5
  (r0 = antes de la ronda 1), sin que el daño medio suba en esas transiciones.
- **Q2 · mejor que los controles:** en r5, fallos de `recursiva` < `azar`,
  `sin_acumular`, `fija`, `lote_final` y `vacia_online`: cinco Wilcoxon de una
  cola sobre las 10 macros, Holm, α = 0,01.
- **Q3 · sin regresión:** con la configuración final de `recursiva` (memoria
  + piezas) frente a la base (agente base con el arreglo de la mano), sobre la
  misma memoria final, en el banco de examen de A (DistShift2, UnlockPickup,
  Dynamic-Obstacles-16x16, ShiftTest; 50 semillas nuevas por familia): daño
  medio no sube y éxito medio no baja.
- **Q4 (se informa) · dependencia:** en cuántas macros hay al menos una
  edición aceptada en la ronda r ≥ 2 que ya se había probado y rechazado en
  una ronda anterior.
- **Q5 (se informa) · ¿mérito de ECHO o del menú?:** `recursiva` frente a
  `piezas_dadas` en r5 (medias y Wilcoxon en ambos sentidos).
- **Q6 (se informa):** ediciones y piezas aceptadas por ronda.

**Verde = Q1 ∧ Q2 ∧ Q3.** Si no, B v3 es roja y se publica así.

## 6. Desarrollo (cerrado; declarado)

Todo con semillas 5 000 000+ y 7 000 000+, sonda de desarrollo
LavaCrossingS9N1 · LavaCrossingS9N2 · ObstructedMaze-1Dlhb · KeyCorridorS3R3,
y trazas en BlockedUnlockPickup, ObstructedMaze-1Dlh, ObstructedMaze-2Dl,
KeyCorridorS3R2, Dynamic-Obstacles-Random-6x6. Ajustes de las piezas en esa
fase: ver [investigación](B3-INVESTIGACION.md) §6. Resultado de desarrollo
(3 macros): `recursiva` 267 → 118 → 84 → 63 → 38 → 39; `piezas_dadas` 43.
Ninguna familia de la sonda de examen ni semilla 8 000 000+ se jugó antes del
examen. Tras `preflight` no cambia nada; el examen corre una vez.

## 7. Riesgos

1. **La sonda de examen puede no tener los atascos que arreglan las piezas**
   (Lava y DistShift son de memoria; DynObs no tiene objetos). Entonces la
   curva puede quedarse en una sola mejora (como B v2) y Q1 sale rojo.
2. ObstructedMaze-2Dlh puede ser inalcanzable para la política (dos
   habitaciones, llave escondida): pesa igual en todos los brazos.
3. `piezas_dadas` probablemente empata o gana: no decide, pero limita lo que
   se puede afirmar (§1).
4. Puerta ruidosa con 20 mundos: igual para todos los brazos.

## 8. Enmienda 1 (20/10/2026, tras la revisión independiente, antes de `preflight`)

El revisor (sin ver la sonda de examen ni semillas de examen) no encontró
bloqueos. Cambios:

1. **Texto ajustado al código** (§2): `no_repick` solo se ofrece junto con
   `commit`; la regla real de `no_repick` y de `no_retoggle` es la de la tabla
   (prohíben por id, no por casilla).
2. **`idle` ya no cuenta los giros para encararse** a algo (antes cualquier
   giro a la izquierda sin intención contaba como «quieto»); y si el bucle de
   replanificación termina poniendo una prohibición, se decide una vez más con
   ella. Dos defectos del código; `wander` nunca se aceptó en desarrollo.
3. **`azar` estratificado:** saca tantas ediciones de memoria del menú de
   memoria y tantas piezas del menú de piezas como propone `recursiva` esa
   ronda (antes sacaba de la unión, ~0,7 piezas por ronda frente a 2–3:
   medía en parte «piezas sí o no»). Más justo con el control.
4. Q4 cuenta solo candidatas que llegaron a validarse; el informe exige
   `destroyed == 0` para el verde; la congelación añade la versión de numpy,
   el hash de este contrato y de los tests.

Declaraciones:

- **Q2 exige dominio casi total:** con 10 macros, el p exacto mínimo de
  Wilcoxon es 0,00098 (10 de 10 a favor), 0,00195 con 9; los umbrales de Holm
  son 0,002 · 0,0025 · 0,0033 · 0,005 · 0,01. Al menos dos controles tienen que
  perder en las 10 macros (o 9 con un empate).
- **LavaCrossingS11N5 y DistShift2** ya se usaron en exámenes anteriores
  (sonda de B v1; banco de A y Q4 de B v1) con otras semillas; sus resultados
  están publicados en los documentos. No se diseñó ninguna pieza con ellas.
- La memoria de partida la sigue entrenando el agente de B v1 (sin el arreglo
  de la mano), igual para todos los brazos.

Desarrollo tras la enmienda (`lab/echo58/acumula3/dev-20261020T213746.json`,
3 macros, sonda de desarrollo, suma fallidos/daño r0…r5):

| Brazo | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| recursiva | 267/173 | 118/14 | 84/0 | 63/0 | 38/0 | 39/0 |
| azar (estratificado) | 267/173 | 274/172 | 272/149 | 272/140 | 273/140 | 262/126 |
| sin_acumular | 267/173 | 118/14 | 113/17 | 120/21 | 157/29 | 153/33 |
| fija | 267/173 | | | | | 286/146 |
| lote_final | | | | | | 157/33 |
| vacia_online | 116/25 | | | | | 116/25 |
| piezas_dadas | 215/173 | 71/22 | 44/0 | 42/0 | 37/0 | 43/0 |

El código del informe sobre estos datos: Q1 pasa (4 transiciones seguidas),
Q3 pasa (daño 77,7 → 0; éxito 67,3 → 183,7), Q4 en 3 de 3 macros,
`destroyed` 0. Q2 no se puede evaluar con 3 macros.

Invariantes: memoria entera y append-only (`destroyed == 0`), 0 coma flotante
en agente y memoria, córtex apagado, nada nuevo bajo `nexus0/`, `memx/`,
`acumula/`, `acumula2/` sin tocar, campaña ARC intacta.
