# E4-BENCH-ARC3 · ECHO juega ARC-AGI-3 — contrato

2026-09-24. Parte de E4-BENCH-GENERAL (ver `ECHO4-BENCH1-A-DESIGN.md`). Nav lo puso **primero**
en la cola, porque el brazo de ECHO solo no cuesta dinero.

## Pregunta

¿Puede el núcleo de ECHO, **sin modelo de lenguaje**, descubrir actuando las reglas de juegos
interactivos que no ha visto nunca, y completar más niveles que el agente aleatorio oficial?

## El entorno (comprobado el 2026-09-24)

- ARC-AGI-3: 25 juegos públicos, cada uno con 6–10 niveles. Se juegan **en local** con el
  paquete oficial `arc_agi` 0.9.1 y `arcengine` 0.9.3 (repositorio `arcprize/ARC-AGI-3-Agents`,
  MIT). La clave de ARC Prize se lee de `echoai/.arcprizekey` y nunca se imprime.
- Cada fotograma es una rejilla de 64×64 con 16 colores posibles. Las acciones son
  `ACTION1…5` (teclado), `ACTION6` (clic con coordenadas) y `ACTION7`; cada juego dice cuáles
  admite.
- **Puntuación oficial por nivel:** `min(100, acciones_humano / acciones_agente × 100)` si se
  completa, y 0 si no. Cada juego trae las acciones de un humano de referencia por nivel.

## Juegos congelados (antes de diseñar el agente)

`lab/arc3/split.json`, semilla 20260925, sha256 `91f23200c99619aa94ce4a9b897d015092f6d4d584e8b6df5f7f07652ac57e08`:
- **Desarrollo:** 8 juegos: bp35, g50t, lp85, m0r0, s5i5, sk48, su15 y wa30.
- **Examen:** 17 juegos. **LS20 se excluye** del examen porque se abrió en la prueba de
  viabilidad; se vieron su primer fotograma y el efecto de 4 acciones. El examen queda en
  **16 juegos**.

## El agente ECHO-ARC3 (con las piezas de ECHO)

Es un agente nuevo, construido con las **piezas** de ECHO (WSP, CAM, T, Q y gate). **No** es
el agente completo de MAINTAIN adaptado; se declara así.

1. **Percibe:** cada fotograma se reduce a un estado discreto (su huella) y a sus objetos
   (componentes conexos por color). El estado entra en la CAM como paquete WSP: **un hecho
   observado**.
2. **Qué depende de mí (BOUNDARY):** compara el fotograma antes y después de cada acción
   para descubrir qué objetos mueve él y cuáles se mueven solos.
3. **Predice (T):** guarda las transiciones (estado, acción) → estado siguiente que ha
   vivido. En estos juegos la misma acción desde el mismo estado da el mismo resultado; si
   no, T registra el conflicto.
4. **Curiosidad dirigida:** va al estado conocido más cercano que todavía tenga acciones sin
   probar y las prueba. En los juegos de clic, pulsa **sobre los objetos**, no en píxeles al
   azar.
5. **Aprende de las consecuencias (Q):**
   - completar un nivel refuerza el camino que llevó hasta ahí;
   - «fin de partida» castiga la última acción (δ negativo);
   - tras un «fin de partida», reinicia **conservando lo aprendido**.
6. **Gate:** nunca intenta una acción que el juego no admite.

## Brazos

| Brazo | Qué es | Coste |
|---|---|---|
| **RANDOM** | el agente aleatorio oficial, con el mismo presupuesto de acciones | 0 $ |
| **ECHO** | ECHO-ARC3 sin modelo de lenguaje | 0 $ |
| **ECHO sin BOUNDARY** | ablación: no distingue qué depende de él, y en los juegos de clic pulsa al azar | 0 $ |
| LLM | la plantilla oficial con un modelo barato (DeepSeek o Qwen) | de pago, bloque posterior, con orden de Nav |
| ECHO + córtex | el modelo propone reglas y ECHO las comprueba actuando | de pago, bloque posterior, con orden de Nav |

## Métricas

- **Niveles completados** por juego y en total.
- **Puntuación oficial** (la media por nivel de la fórmula de arriba).
- **Acciones usadas.**
- Mismo presupuesto de acciones por juego para todos los brazos; se fija en el contrato D.

## Qué esperamos, sin inflarlo

ARC-AGI-3 está hecho para que las IA actuales puntúen bajo. El agente aleatorio casi nunca
pasa de nivel. Si ECHO completa algunos niveles donde el aleatorio no, será evidencia de que
explorar con un modelo del mundo y saber qué depende de uno sirve fuera de nuestros propios
mundos. **Puede salir rojo** (ECHO empata con el aleatorio), y se publicará igual.

## Método

- Contrato → aprobación → desarrollo con los 8 juegos → contrato D con umbrales →
  aprobación → examen con los 16 juegos → auditoría.
- **Recibos:** cada partida guarda su secuencia de acciones y la huella de cada fotograma.
  La auditoría **vuelve a jugar** la misma secuencia en el entorno local y comprueba que los
  fotogramas y los niveles salen idénticos.

## Qué no afirma

- Nada sobre el conjunto privado de ARC-AGI-3 ni sobre el premio.
- Que ECHO sea «inteligente en general».
- Los brazos con modelo de lenguaje van en un bloque posterior.
