# B · ACUMULA — contrato (APROBADO por Roger el 20/10/2026, con brazo LLM)

20 de octubre de 2026. Pista B del [roadmap](ROADMAP.md). Requisito cumplido:
A · MEMORIA-X verde ([resultados](MEMORIAX-RESULTS.md)). Nada de esto está
implementado ni medido.

## 1. Pregunta

¿Puede ECHO **mejorar sus propias reglas de memoria** a partir de sus fallos
medidos, de forma que cada ronda aprenda **más rápido en un mundo nuevo** que la
anterior, y mejor que cambiar las reglas al azar?

Es exactamente donde cayó RSI-1 (recursivo 99 = sin acumular 99, azar 101,
base 96; la curva se quedó plana). Lo que cambia aquí:

- RSI-1 proponía cambios a ciegas sobre una biblioteca DSL. Aquí cada propuesta
  sale de un **fallo localizado**: qué clave de memoria dio la creencia que
  precedió al daño o a la acción inútil. El azar recibe el mismo menú y el
  mismo número de intentos, pero no sabe dónde falló.
- Hay huecos medidos que atacar: en A, la lava con identificadores nuevos
  recibió una **creencia equivocada** (DistShift2 A2: 49,4 daños de 50, peor
  que barajada) y ShiftTest se quedó en la mitad.

## 2. Qué puede cambiar ECHO de sí mismo (menú cerrado, todo entero)

Una **configuración** C acompaña a la memoria. La memoria (append-only, con su
cadena SHA-256) nunca se borra: las ediciones cambian cómo se **lee**, no lo
observado. `destroyed == 0`.

| Edición | Qué hace | Alcance |
|---|---|---|
| `silence(k)` | la regla de la clave de capa 2 `k` no responde | una clave |
| `verify(k)` | la creencia de `k` se comprueba en el episodio antes de fiarse | una clave |
| `refine(k, b)` | la clave `k` se parte por el bit de firma `b` (tamaño o borde) | una clave |
| `merge(b)` | la capa 2 ignora el bit `b` para lo estático | global |
| `bound(l, n, p)` | N_MIN ∈ {2, 3, 5} y UMBRAL ∈ {70, 85, 95} de la capa `l` | global |
| `order` | en A2, preguntar primero la capa 2 en vez de la 1 | global |

## 3. Cómo propone ECHO (sin LLM, córtex apagado)

Al final de cada ronda, por cada episodio con daño o con acciones NOOP, el
diagnóstico busca la **clave que respondió** justo antes del fallo (capa y
firma). Con eso genera candidatas del menú que tocan esa clave o su bit
(`silence`, `verify`, `refine`) y, si el mismo bit aparece en ≥ 2 claves
fallidas, `merge` o `bound`. Ordena por número de fallos explicados. Sin
fallos no propone nada.

**Puerta de aceptación (igual para todos los brazos):** cada candidata se
prueba en 20 mundos de validación de la ronda (semillas propias). Entra si el
daño no sube, el éxito no baja y mejora al menos una de las dos, o el
desperdicio baja ≥ 10 %. Hasta **K = 4 candidatas por ronda**.

## 4. Rondas, mundos y brazos

Cinco rondas. En cada ronda el agente juega 40 episodios de dos familias
(régimen A2, ids nuevos por episodio) aprendiendo en línea, y luego propone.

| Ronda | Familias de la ronda |
|---|---|
| 1 | DistShift1 · LavaGapS5 |
| 2 | LavaCrossingS9N2 · Dynamic-Obstacles-5x5 |
| 3 | DistShift2 · SimpleCrossingS9N1 |
| 4 | LavaCrossingS9N3 · KeyCorridorS3R2 |
| 5 | ShiftTest (ASG) · DoorKey-8x8 |

**Sonda (mundos nuevos, nunca usados para proponer ni aceptar):**
LavaCrossingS11N5 · Dynamic-Obstacles-Random-6x6 · BlockedUnlockPickup ·
ObstructedMaze-1Dl. Tras cada ronda, la configuración y la memoria de ese
momento juegan 30 episodios por familia de sonda **aprendiendo en línea sobre
una copia** que se tira después. Eso es «velocidad de aprendizaje en un mundo
nuevo».

Punto de partida de todos los brazos: la memoria aprendida de A (de la misma
macro) y la configuración base de A.

| Brazo | Configuración | Memoria |
|---|---|---|
| **recursiva** | acumula ediciones aceptadas | acumula |
| **azar** | mismo menú, mismas K candidatas por ronda, elegidas al azar entre las ediciones válidas, misma puerta | acumula |
| **sin_acumular** | cada ronda vuelve a la base y propone solo desde esa ronda | acumula |
| **fija** | base siempre (solo «más datos», sin automejora) | acumula |

`fija` es el control clave: separa «mejorar las reglas» de «haber visto más
mundos».

10 macro-semillas; cada una con sus propias semillas de ronda, de validación y
de sonda (bloques disjuntos, fijados en `preflight`).

## 5. Predicciones (escritas antes de medir)

Métrica principal por ronda: **daño acumulado en la sonda** (4 familias × 30
episodios, A2), media por macro. Secundaria: éxitos en la sonda.

- **Q1 · mejora sucesiva:** la media de daño en sonda de `recursiva` baja
  estrictamente en **≥ 3 transiciones seguidas** de las 5 (ronda 0 = antes de
  la ronda 1), sin que el éxito medio baje en esas transiciones.
- **Q2 · mejor que los controles:** tras la ronda 5, daño en sonda de
  `recursiva` < `azar`, < `sin_acumular` y < `fija`: tres Wilcoxon de una cola
  sobre las 10 macros, Holm, α = 0,01.
- **Q3 · sin regresión:** con la configuración final de `recursiva`, en el
  banco de examen de A (régimen A2, sus cuatro familias, semillas nuevas) el
  daño medio no sube y el éxito medio no baja frente a la configuración base.
- **Q4 (se informa):** ¿se cierra el hueco de la lava? Daño en DistShift2 A2
  con la configuración final frente a la base.
- **Q5 (se informa):** qué ediciones se aceptaron, en qué ronda y cuántos
  fallos explicaba cada una.

**Verde = Q1 ∧ Q2 ∧ Q3.** Si `recursiva` empata con `azar` o con `fija`, B es
roja, igual que RSI-1, y se publica así.

## 6. Qué se puede ajustar en desarrollo (antes de congelar)

El diagnóstico, K, el tamaño de validación y la puerta de aceptación, con
semillas de desarrollo propias y **sin mirar la sonda**. Las predicciones,
las familias de sonda y la métrica no cambian.

## 7. Riesgos conocidos

1. La sonda puede no beneficiarse de lo que se arregla en las rondas
   (ediciones demasiado locales). Entonces Q2 sale rojo: es un resultado.
2. Con las ediciones `silence`/`verify` el agente puede volverse más prudente
   y ganar daño a costa de éxito; por eso Q1 y Q3 exigen que el éxito no baje.
3. La puerta de aceptación es ruidosa con 20 mundos; puede aceptar ediciones
   malas. Afecta igual a todos los brazos.
4. Diez macros comparten la memoria de partida de A, que era casi idéntica
   entre macros. La variación entre macros viene de los mundos de cada ronda.

## 8. Decisiones de Roger

1. Aprobar este contrato (familias de ronda y de sonda incluidas).
2. **Brazo LLM — APROBADO (se informa, no decide):** el mismo diagnóstico se le
   da a un LLM (`openai/gpt-oss-120b` en Groq) para que elija las K
   candidatas del mismo menú; pasa la misma puerta. Mediría si el córtex
   propone mejor que ECHO o que el azar. Coste estimado: unas 500 llamadas en
   total, dentro del cupo gratuito diario. Temperatura 0; cada respuesta se
   guarda por hash del mensaje, así que repetir la corrida no vuelve a llamar.
   El LLM ve claves como números opacos, nunca nombres. Si la API falla o
   responde fuera del menú, esa ronda no propone nada (se registra).

Invariantes: memoria entera y append-only, 0 coma flotante en el agente y la
memoria, el córtex no escribe hechos (sus propuestas solo entran si pasan la
puerta), nada nuevo bajo `nexus0/`, campaña ARC intacta.
