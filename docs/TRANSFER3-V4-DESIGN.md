# TRANSFER-3 v4 — presupuesto comparable y cribado público

2026-09-18. Diseño fijado antes de ejecutar. No es confirmación B/C.

Tres variantes v3 sin cambios: corrected, reward_only y coverage_only.
Todas parten de Q vacía, la misma cinemática y las mismas cuatro salas A,
en orden cíclico. **Exactamente 128 movimientos ejecutados y observados**
por variante (512 sim_u), máximo 64 por episodio. El corte global puede
ocurrir a mitad de episodio; queda rotulado, no como llegada o retorno.
Es un límite del banco cinemático, no un procedimiento de parada de vuelo.
No ejecutar una cola y excluir luego su coste. Sin observaciones inventadas.

64 salas públicas nuevas del generador v2, comenzando en seed 20264601.
Excluir las 4 geometrías A y las 16 examinadas anteriormente, además de
duplicados internos, con ledger y máximo 100 intentos por caso. Generar
antes de ejecutar políticas. 4 brazos incluyendo scratch = 256 exámenes
aislados. No aprender en examen. Publicar todos los casos y fallos.

El cribado de desarrollo (no criterio final del hito) exige por candidato:

- cero colisiones, hechos falsos, violaciones de reserva y escrituras
  imaginadas observadas; parámetros congelados;
- ningún fallo nuevo en una sala que scratch completa;
- más victorias que derrotas por llegada primero y movimientos sólo entre
  llegadas conjuntas; fallos conjuntos son empate;
- ahorro positivo de movimientos entre éxitos conjuntos;
- prueba de signo unilateral exacta sobre pares discordantes, p ≤ 1/60
  (0,05/3 para las tres variantes). Empates no son muestras discordantes.

Se publican separadamente coste de escuela, examen, coste combinado y ahorro
entre éxitos conjuntos. Ahorrar por abandonar antes no cuenta como victoria.
Una ventaja operacional no equivale a amortizar el entrenamiento. Los modelos
fueron seleccionados usando desarrollo previo: este cribado no acredita
custodia, generalización física ni cierre final. Si ninguno pasa, se conserva
el rojo y no se abre C ni se congela una política por obligación.

Limitación conocida: esta familia finita tiene poca diversidad de topología
(una pared y abertura). Antes de una campaña final hay que verificar su
capacidad sin reemplazo y decidir el alcance del generador y del auditor
geométrico; no basta solicitar semillas adicionales.
