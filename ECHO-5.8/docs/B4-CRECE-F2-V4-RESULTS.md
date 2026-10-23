# CRECE F2 v4 · rojo de desarrollo con Groq 20b

21/10/2026. **Corrida completa, puerta de desarrollo ROJA; sin examen.**
Modelo único `openai/gpt-oss-20b`, 2048 tokens/low, temperatura 0. La falta
de crecimiento se conserva; no se presenta como un fallo de cuota ni se
atribuyen estos resultados a Gemini, Gemma o a otro modelo.

## Resultado

Dos macros, cinco generaciones y siete brazos. Fallos en 192 episodios de
sonda por generación, emparejados entre brazos y generaciones:

| Brazo | g0 | g1 | g2 | g3 | g4 | g5 |
|---|---:|---:|---:|---:|---:|---:|
| crece | 145 | 145 | 145 | 145 | 145 | 145 |
| sin_fichas | 145 | 145 | 145 | 145 | 145 | 145 |
| sin_relevo | 145 | 145 | 145 | 145 | 145 | 145 |
| azar_gramatica | 145 | 143 | 143 | 143 | 139 | 139 |
| acepta_azar | 145 | 145 | 145 | 145 | 145 | 145 |
| piezas_b3 | 110 | 110 | 110 | 110 | 110 | 110 |
| sin_piezas | 145 | 145 | 145 | 145 | 145 | 145 |

CRECE no mejora en ninguna transición; incumple las dos mejoras consecutivas
exigidas. Ninguno de los tres brazos con LLM promociona una pieza. La puerta
sí acepta dos candidatas del generador aleatorio en la macro 2, generaciones
1 y 4. Estas mejoras no cumplen tampoco la sucesión requerida a crece, ni se
usan para cambiar su veredicto. No se prueba aquí que el LLM sea útil para
inventar piezas o que sus fichas mejoren sus propuestas.

El daño agregado es 94 tanto en g0 como en g5 para todos los brazos, y no
hay errores del enchufe en las sondas. Las mejoras del generador aleatorio
y de la referencia B v3 corresponden a éxitos, con ese daño sin cambio.

## Propuestas y servicio

| Brazo generador | Propuestas | Mecánica válida | Promociones |
|---|---:|---:|---:|
| crece | 10 | 6 | 0 |
| sin_fichas | 10 | 10 | 0 |
| sin_relevo | 10 | 8 | 0 |
| azar_gramatica | 10 | 10 | 2 |

30 recibos: 28 llamadas HTTP nuevas y 2 respuestas de caché, todos 200 y
con `finish_reason=stop`; 127790 tokens sumados en los recibos, incluyendo
el uso histórico de las dos respuestas de caché. No hubo truncamiento ni agotamiento de cuota en esta
corrida. Se mantuvo la separación mínima de llamadas y no se cambió
facturación. Código mecánicamente válido no equivale a una pieza útil.
Los recibos de las 28 llamadas nuevas suman 125505 tokens; los dos cache
hits contienen 2285 tokens de uso histórico, sin consumo HTTP nuevo.

## Verificación y persistencia

- 44 pruebas técnicas pasaron antes del arranque. Fuente y protocolos
  se mantuvieron idénticos hasta el cierre; base B v3 congelada intacta.
- Un verificador separado recalculó las promociones, sucesión de campeones,
  sorteo, curvas y veredicto; comprobó 40 candidaturas, 30 solicitudes,
  84 snapshots, hashes y correspondencia entre propuestas y respuestas.
  También verificó el envío de rechazos previos y la ausencia de fichas
  en el control correspondiente. **Auditoría verde; experimento rojo.**
- La revisión posterior del auditor distingue reservas de envío y caché:
  los dos sin_fichas/g1 recuperan respuestas idénticas pedidas en V3.
  Esto corrige el recuento inicial de «30 intentos HTTP» a 28 nuevos y
  2 cache hits, sin cambiar propuestas, puntuaciones ni veredicto. El
  `audit.json` original permanece intacto como recibo histórico.
  La auditoría ampliada está en `audit-expanded.json`, con fuentes en
  `audit-source-expanded/` y siete pruebas contra alteraciones de artefactos.
- La biblioteca de dos piezas del control azar_gramatica, macro 2 g4,
  se recargó en dos procesos nuevos con red y lectura de claves denegadas.
  Ambos reprodujeron 76 pasos idénticos, éxito y cero errores en una semilla
  de desarrollo ajena a la sonda. Es verificación de persistencia, no una
  promoción del LLM ni un dato añadido a la puntuación.

Artefactos: `lab/echo58/crece/f2-v4-feedback/` contiene `results.json`,
`audit.json`, `source/`, `protocols/`, `audit-source/`, `reload-check/`,
solicitudes, candidaturas, snapshots y puntuaciones. Hash del resultado:
`4ed24bbde7b6bec866e444dd1ace89c9fdb3fe905a079984fddb00cc8c1b1e64`.

Figura exportable: [PNG](../../lab/echo58/crece/f2-v4-feedback/curves.png)
y [SVG](../../lab/echo58/crece/f2-v4-feedback/curves.svg).

## Siguiente versión, separada

El piloto [v5](B4-CRECE-F2-PROTOCOLO-V5-INTERFACE120B.md) prueba `120b`, ahora
accesible, y una presentación explícita de `DROP_ACTION` en las fichas. Se
fijó antes de sus datos, con nuevas semillas y los mismos umbrales. No borra
este rojo, no permite atribuir diferencias a un solo cambio y no abre examen
por sí mismo. F3/F4 siguen pendientes de una puerta de desarrollo superada.
