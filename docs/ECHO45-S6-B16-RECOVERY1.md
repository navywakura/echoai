# S6-B16 — recuperación del comparador de paridad

El primer servicio B16 se detuvo el 4 de octubre de 2026 a las 19:17:30 Madrid,
antes de realizar llamadas al modelo. Había ejecutado las 80 partidas A de la
base y sus 80 replays. El estado `BLOCKED_INSTRUMENT` y el log original se
conservan; este incidente no se cuenta como un resultado científico negativo.

La comparación Python del micro enfrentaba el informe recién ejecutado con
su representación leída de JSON. `agent.report()` convierte solo el nivel
exterior de algunas hipótesis; quedan coordenadas como tuplas. El informe
temporal también contiene una tupla en `decision.target`. JSON las guarda
como listas. Las dos representaciones tienen la misma huella canónica, pero
la igualdad Python devuelve falso. Los 80 registros guardados, sus replays y
la referencia B14 son exactamente iguales, incluidos score y todos los campos.

Se realizaron dos partidas de diagnóstico A, declaradas en el presupuesto:
A0 y A72. A0 no contiene esas diferencias. A72 reproduce las dos diferencias
de tipo en `/model/hypotheses/3/1/1` y `/model/temporal/decision/target`.
Normalizada a JSON coincide con B14; acciones, frames, niveles, score,
reinicios y acciones por nivel permanecen idénticos incluso antes de normalizar.
El presupuesto previo a reanudar suma **162** partidas: 160 de base/replay y
dos diagnósticos. Ninguna partida protegida ni de examen se ha abierto.

La recuperación se implementa en `seed/s6b16_recovery1.py`, fuera de las 183
fuentes congeladas de B16. Solo los resultados de las etiquetas
`micro/baseline/A` y `micro/baseline/A/replay` se convierten a su representación
JSON antes de compararse. Se exige que la huella coincida antes y después;
un cambio de comportamiento o una huella incorrecta detiene el instrumento.
Los demás resultados, los prompts, el selector, el modelo, las semillas,
los presupuestos y V1–V4/B1–B5 conservan su implementación original.

Las cuatro pruebas de recuperación cubren la conversión anidada, la
inmutabilidad del objeto original, el rechazo de diferencias reales y el
alcance exacto de la intervención. `recovery1/receipt.json` fija las nuevas
fuentes y esta adenda por hash, archiva sus bytes y liga el perfil original,
las pruebas, el fallo y los diagnósticos. Se declara antes de la primera
generación. Las 160 partidas de base/replay ya guardadas se reutilizan; no
se repite ninguna llamada ni se elige una nueva semilla.

Entrada de recuperación: `python -m seed.s6b16_recovery1 follow`, bajo el
servicio separado `echoai-s6b16-recovery1`. Su log se guarda en
`lab/seed/s6b16-20261004/recovery1/process.log`. El estado científico continúa
en el directorio B16 original. La cadena sigue siendo micro, piloto,
auditoría, campaña, auditoría y examen, con las mismas condiciones de paso.
