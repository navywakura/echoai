# S6-B13-R1: por qué ECHO obtuvo 1113 y FIJO 1125

Análisis privado del 4 de octubre de 2026, sobre el piloto terminado a las
04:23 de Madrid. La auditoría independiente terminó válida a las 08:32:03:
reconstruyó los 54 veredictos en 7720 partidas independientes y confirmó el
cierre sin promoción. [Recibo](../lab/seed/s6b13-native-20261003/pilot-audit.json).
Se han revisado
las 36 peticiones realmente enviadas, sus respuestas, los 54 veredictos y las
mediciones de desarrollo A. Este análisis no juega partidas ni llama al modelo.
Las 159 fuentes congeladas conservan sus hashes. El cálculo reproducible está
en [analyze.py](../lab/seed/s6b13-forensics-20261004/analyze.py) y el recibo con
hashes de las entradas en [analysis.json](../lab/seed/s6b13-forensics-20261004/analysis.json).

La expectativa de que ECHO eligiera mejores preguntas era la hipótesis del
experimento. Este piloto no la confirma. Los números son niveles de 80 partidas
gym, repetidas bajo tres semillas de generación del modelo; no son 1113 tareas
ARC diferentes ni una puntuación oficial ARC. Cada brazo podía sumar 1200.

| Semilla del modelo | SEMILLA | ECHO | FIJO | Diferencia ECHO−FIJO |
|---|---:|---:|---:|---:|
| 697001 | 365 | 373 | 375 | −2 |
| 697017 | 365 | 367 | 375 | −8 |
| 697029 | 365 | 373 | 375 | −2 |
| Total | 1095 | 1113 | 1125 | −12 |

ECHO mejora un 1,64 % respecto a SEMILLA y FIJO un 2,74 %, según niveles
agregados. Ambos aceptaron una modificación por semilla. ECHO consiguió
sus tres aceptaciones en la primera ronda y ninguna adicional en las cinco
siguientes. Por tanto, la segunda parte del presupuesto no produjo mejora
acumulativa aceptada. La mayoría de las 18 propuestas de cada brazo fueron
REVALIDATE_NOOP: 16 en ECHO y 17 en FIJO. No hubo COOLDOWN_CAP en esos brazos.

**La diferencia de niveles está localizada en las reglas aceptadas.** Las tres
ejecuciones de FIJO terminaron con `REVALIDATE_NOOP=1` condicionado a
`stagnation>=20`: revisar una predicción de movimiento cuando el estado lleva
al menos veinte decisiones consecutivas sin cambiar. Ganó cinco niveles en
la partida A51, tres en A59 y uno en A76 y A77. A51 estaba bloqueada sin
completar un nivel; sus 2000 decisiones base registran `level=0`.

ECHO aceptó valores 8/8/1 condicionados a `level>=2`, `level>=4` y `level>=2`,
respectivamente. Esas reglas no podían activarse en A51. La primera y tercera
semilla ganan tres niveles en A59 y A68, y uno en A76 y A77: +8. La segunda
solo gana uno en A76 y A77: +2. FIJO no gana los tres de A68, pero sí los cinco
de A51: de ahí las diferencias −2, −8 y −2. Las gramáticas iniciales de ambos
brazos eran idénticas y permitían la regla que encontró FIJO. No había una
restricción sintáctica que impidiera a ECHO proponerla.

**La compactación suprimió parte esencial de la realimentación.** El límite
era de 3072 tokens de entrada. `seed/s6b13_prompt.py` ofrece variantes con
cuatro antecedentes, dos y después cero, antes de compactar las features.
En 12 de las 15 llamadas ECHO posteriores a la inicial de cada semilla, la
petición enviada tiene `Own recent feedback: []`. También ocurre en las
15 llamadas posteriores de FIJO: el problema de representación es compartido,
aunque perjudica directamente el mecanismo de refinamiento que ECHO pretende
aprovechar. El selector y la gramática sí conservan historia internamente;
esa historia no llega completa al modelo.

Las seis llamadas REFINE usan la última variante. Conservan el objetivo
rechazado original y sus contrastes, pero borran todos los resultados recientes.
Las rondas 3–5 de la semilla 697001 tienen exactamente el mismo texto de
entrada; sucede lo mismo con las rondas 4–6 de la semilla 697017. Las semillas
de muestreo y las exclusiones de gramática sí cambian. No son tres repeticiones
idénticas de toda la inferencia, pero el modelo no recibe qué falló en la
reparación que acaba de proponer.

En 697017, la ronda 4 llegó a 378 niveles A, pero V4 la rechazó por pérdidas
de score en dos partidas protegidas, sin pérdida de niveles. Las rondas 5 y 6
proponen variantes con el mismo comportamiento y vuelven a ser rechazadas.
Sus prompts aún muestran como objetivo el rechazo V3 de la ronda 3 y no
contienen el indicador del rechazo V4 más reciente. No se usan los casos
protegidos ni sus features para diseñar la corrección: basta comprobar que
incluso el bit permitido de aceptación/rechazo se eliminó del mensaje.

**La variedad sintáctica no produjo suficiente variedad de comportamiento.**
Ocho de las 18 propuestas ECHO repiten un digest de comportamiento que el
mismo brazo ya había medido. En FIJO no hubo repeticiones dentro de una
semilla según ese indicador. La gramática evita el parche textual exacto y
algunos valores inertes, pero distintas guardas pueden producir la misma
ejecución. Añadir `reset_known=1`, por ejemplo, no garantiza un nuevo efecto.
La equivalencia observada tiene alcance sobre estas partidas; no demuestra
equivalencia de programas en todos los entornos.

**El selector pierde correspondencia entre foco y evidencia.** ECHO eligió
CONTRADICTION diez veces, REFINE seis y WAIT dos; GENERALIZE ninguna.
En cuatro peticiones CONTRADICTION, los tres casos mostrados registraban cero
contradicciones. Una petición WAIT no mostraba ninguna lectura de HOLD.
`contrastive_requests.select` rota toda la lista ordenada por el índice de
ronda, y puede desplazar los casos con señal fuera de los tres elegidos.

El planificador calcula `(ganancia_aceptada + 2) / (intentos + 1)`. Aunque su
comentario dice que prueba primero mecanismos nuevos, la fórmula no lo
garantiza: una primera ganancia +8 deja CONTRADICTION con prioridad 5 frente
a 2 para mecanismos sin probar. Además, el adaptador B13 filtra del historial
los rechazos con ganancia positiva para que no reactiven un objetivo vencido;
ese mismo historial filtrado se usa para contar intentos. Se mezclan así dos
responsabilidades: decidir qué objetivo sigue disponible y contabilizar todos
los intentos del planificador.

Estos hechos identifican defectos de selección y comunicación. No cuantifican
cuánto subiría ECHO si se corrigieran. Que una petición incluya más evidencia
no garantiza que el modelo la utilice mejor. El mayor contexto inicial de
ECHO y la selección de tareas casi resueltas tampoco son, por sí solos, una
prueba causal de la derrota. Hace falta una comparación posterior con cambios
aislados, presupuestos iguales y validación protegida nueva.

La siguiente condición debería conservar obligatoriamente un recibo compacto
del último intento (propuesta, veredicto, ganancia, pérdidas en A, rechazo
protegido booleano y equivalencias), incluso en la variante más corta. El
objetivo original y el resultado de su última reparación deben coexistir.
Las pruebas de contexto deben cubrir historias reales largas y confirmar que
el mensaje cambia tras cada veredicto. Esto se aplicaría a ECHO y FIJO.

El selector debería escoger primero casos con señal del mecanismo elegido
y rotar dentro de ese grupo; la exploración de mecanismos y su contabilidad
deben separarse de la caducidad de objetivos. Las equivalencias observadas
pueden penalizar intentos redundantes y devolver diversidad a la búsqueda,
sin afirmar que una coincidencia de trazas demuestra equivalencia universal.
No se copiará al agente la regla ganadora de FIJO como si la hubiera descubierto
autónomamente. No se reducen V3/V4 ni se abre el examen con este piloto.

El error `subprocess.STDOUT` apareció después de calcular y guardar todo el
piloto. Impidió lanzar su auditoría, pero no explica los doce niveles de
diferencia. La recuperación arrancó a las 04:44:17 y está documentada
[por separado](ECHO45-S6-B13-AUDIT-LAUNCH-RECOVERY.md). El plan de auditoría
reconstruido requiere 7720 partidas únicas, con cuatro procesos, sin nuevas
llamadas al modelo. La previsión inicial de terminar entre las 08:00 y las
09:00 sigue siendo orientativa. Si reproduce el piloto, cerrará B13-R1 sin
promoción. Campaña y examen quedan sin fecha en esta condición.
