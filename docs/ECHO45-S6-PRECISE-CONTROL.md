# S6: control de cambios precisos — contrato previo

2026-09-28. Autorizado por Roger: permitir cambios precisos, demostrar primero
una mejora de desarrollo sin regresiones y después intentar automejora LLM.
Este contrato solo mide la capacidad del instrumento; no certifica S6 verde.

Extensión aditiva sobre v5.8: una a tres condiciones observables por parche,
un parámetro y nueva operación `COOLDOWN_CAP` (0–100), que reduce la espera
restante. Vacío devuelve la clase nativa. No se modifican perfiles anteriores,
NEXUS-0, fuentes congeladas ni el bus de observación. El observador captura
estado, decisión y resultado reales mediante el diario ARC existente.

A: versiones 2/3, semillas 0–19. B nueva protegida: 24120–24139; no se usa
la B anterior 20–39 para ajustar nuevas condiciones. 2000 decisiones por
partida, réplica cero, cuatro procesos CPU. Doce candidatos y orden fijados
en `configuration()` antes de medir. Solo guardas disponibles en la gramática
del modelo. Preflight: igualdad nativa, parches inactivos, observación pasiva
y reproducción completa A/B en procesos nuevos.

Control positivo: al menos dos niveles adicionales A, cero pérdida individual
de niveles o puntuación A/B (tolerancia de puntuación 1e-10), reproducción
exacta de cada partida. Se elige el primer candidato que pase en el orden
congelado. Se publican también todos los rechazos. Máximo 2280 partidas,
cero llamadas LLM/GPU y cero acceso a examen reservado. Se conserva la
contabilidad de decisiones/reinicios y puntuación de S6-B4, igual para ambos
agentes. No se confunde con la fórmula distinta del examen final R3.

Un control positivo permitiría un piloto nuevo: la solución humana no entra
en los prompts ni se presenta como propuesta de ECHO. Una búsqueda negativa
solo descarta estos doce candidatos. Los criterios S6 B1–B5 siguen intactos;
una campaña posterior exige contrato propio y examen nuevo.
