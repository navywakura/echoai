# E4-ROLES-1 — contrato C/D v1 (PLAN, pendiente de aprobación)

2026-09-24. Contrato anterior a implementar C y a abrir D. El desarrollo A/B
(`36b9cab3…`, enmienda 1) queda sellado. Física, pagos, deriva, brazos y la
fila del tratamiento **no cambian**. Las semillas 211/223/241 no son examen.

Motivos del relato: «poder no es deber» (C1), «¿podrías hacer de intermediario?»
(C2), «creer no es poder» (C5). Nombran las pruebas; no son evidencia.

## C: límites y casos adversos

C añade escenarios en un módulo nuevo sin tocar las fuentes selladas. Los
criterios hay que cumplirlos; los límites solo se publican, salgan como salgan.

| # | Escenario | Qué se exige | Tipo |
|---|---|---|---|
| C1 | **Negarse.** Tras la primera deriva, la contraparte competente en un tipo rechaza (gate real) todas las asignaciones durante 48 rondas. | Publicar las rondas perdidas. La fila solo mira intentos **ejecutados**, así que un rechazo no cambia la fila y el agente puede seguir asignándole. El rechazo no se convierte en fallo de competencia. | límite |
| C2 | **Intermediario.** El aprendiz no ve el resultado de lo que ejecuta la contraparte 2; la contraparte 1 se lo retransmite. | El recibo retransmitido se guarda como **hipótesis con procedencia** (quién lo retransmite), nunca como hecho, y no entra en la fila. Se publica el coste frente al caso nominal. | criterio (nunca hecho) + coste publicado |
| C3 | **Miembro nuevo con el mismo identificador.** En la ronda 240 una contraparte se sustituye por un cuerpo nativo nuevo con otra competencia. | Recupera 6 aciertos seguidos en ≤48 rondas. En desarrollo, la peor recuperación tras una deriva fue 38. | criterio |
| C4 | **Deriva durante una ausencia.** Una contraparte no está disponible 48 rondas (sus asignaciones no llegan: no hay coste ni recibo) y la deriva ocurre en ese intervalo. | Sin recibos inventados durante la ausencia; publicar la recuperación al volver. | criterio (sin invento) + publicado |
| C5 | **El rango coincide por azar con la competencia.** Se cambia quién afirma el rango (1 o 2). | La trayectoria de `competence` es **idéntica bit a bit** con cualquier afirmante: la afirmación no influye en la decisión. Publicar cuánto gana `rank_follow` en el régimen en que acierta por azar. | criterio |
| C6 | **Límites.** 512 rondas; CAM llena. | Cierre limpio al límite; CAM llena para la sesión sin borrar ni sobrescribir. | criterio |
| C7 | **Veto y parada del operador** en la ronda 200. | El gate y la parada mandan sobre la competencia. | criterio |
| C8 | **Recibo corrupto.** | Un recibo imposible o no canónico para la sesión sin asignar. Un recibo falsificado pero canónico y posible no se detecta: se publica como límite. | criterio + límite |

C cierra cuando todas sus pruebas pasan y los criterios se cumplen en las semillas de desarrollo.

## D: examen preregistrado

Solo se abre si A/B y C pasan y **Nav aprueba la congelación**. Antes:
lock de código, contratos, pruebas, brazos, semillas, umbrales y custodia de
RELATION y del desarrollo de ROLES. Nada se ajusta tras ver D. Un rojo se
publica y exige una v2.

Dos cohortes nuevas de 8 vidas: **264001..264008** y **264101..264108**.
Misma configuración que el desarrollo: 384 rondas, 4 regímenes, 6 brazos,
sin escenarios C.

Cada cohorte debe cumplir **todos**:

1. **Neto del aprendiz:** `competence` supera a **cada** otro brazo por
   ≥256 por vida en media (≥2048 por cohorte). En desarrollo el margen mínimo
   fue +706 (frente a `static_role`, semilla 241).
2. **Recuperación:** total de las tres derivas ≤96 rondas por vida en media
   (≤768 por cohorte), y menor que la de `cumulative`. En desarrollo: 32–57.
3. **Último régimen:** ≥72 aciertos de 96 por vida en media. En desarrollo: 84–93.
4. **Ninguna vida** con `competence` por debajo de `static_role` en neto.
5. Invariantes, replay desde recibos, determinismo, afirmaciones nunca hechos,
   deriva real; cero hechos falsos, borrados y llamadas LLM.

Se publica, sin ser criterio: coste del primer régimen (en desarrollo, 32–37
frente a 68–72); neto conjunto; incentivo privado excluido; asignaciones al
afirmante.

## Auditoría y cierre

Una auditoría en proceso nuevo reconstruye C y D y comprueba toda la custodia.
**Solo su recibo puede acreditar `roles1_green=true`.** Tras el cierre: 11/13
hitos software. Siguiente: INTEGRATE.

Coste estimado: 1,5 s por vida y brazo; D ≈ 16 × 7 ejecuciones, unos minutos.

## Qué no afirma

No jerarquía emergente, liderazgo, obediencia, justicia ni conciencia. La
competencia es una variable del simulador. Sin Discord, web, hardware, commit,
push ni HF.
