# Investigación del resultado de S6 B22

B22 terminó el 7 de octubre de 2026 a las 14:31 de Madrid con instrumento
válido, 11.976 partidas físicas y ninguna promoción. La investigación separa
el fallo del buscador y la conservación del candidato B21. Ambos están
medidos; la superioridad del neocórtex y el examen desde SEMILLA siguen
pendientes. B22 hizo cero llamadas a un modelo.

La revisión independiente de los artefactos reproduce las 288 decisiones y
las 924 mediciones guardadas, incluidas sus repeticiones y las ejecuciones
en otra caché. Coinciden los hashes de las 70 fuentes congeladas y las cinco
entradas. Las comprobaciones aritméticas recomputan el score por nivel,
la ganancia, las pérdidas y la correspondencia entre propuesta y solicitud.
Este análisis no juega partidas ni modifica recibos originales.

**El resultado del ganador B21 conserva niveles, pero pierde eficiencia en
dos partidas.** En el micro reproduce 52 → 56 sin pérdidas; en las 160
partidas de desarrollo amplio pasa de 740 a 748. Ninguna partida baja de
nivel. Las dos regresiones son de score y bastan para rechazarlo con el
criterio vigente, que exige conservar ambos indicadores por partida.

| Caso de desarrollo | Niveles antes → después | Score antes → después | Cambio relativo |
|---|---:|---:|---:|
| 144, mundo v3, semilla 62004 | 5 → 5 | 9,525842 → 9,035931 | −5,143 % |
| 154, mundo v3, semilla 62014 | 4 → 4 | 0,156655 → 0,048212 | −69,224 % |

El score de este ejecutor es

\[
S=100\frac{\sum_{i=1}^{L} i\,\min(b_i/a_i,1)^2}{\sum_{i=1}^{L}i},
\]

donde `b_i` es la referencia del entorno y `a_i` las acciones usadas al
resolver el nivel; un nivel sin resolver aporta cero. Las acciones por nivel
del caso 144 cambian de `[333,359,164,112,21]` a `[337,108,153,82,22]`.
Aunque el total se reduce de 989 a 702, el primer y el último nivel empeoran.
El último pesa más y su contribución al score cae lo suficiente para reducir
el total. En 154, las acciones cambian de `[75,702,402,396]` a
`[263,699,404,575]`: empeoran especialmente el primer y cuarto nivel.
Las diferencias son muy superiores a la tolerancia `1e-10`.

Los ocho casos con acciones distintas son 18, 42, 76, 77, 111, 117, 144 y 154.
Las ganancias de niveles vienen de 18 (+1), 111 (+3) y 117 (+4). La suma
agregada de score también mejora, +10,366188, pero el juez controla pérdidas
individuales. Las trayectorias amplias permiten localizar la primera acción
distinta y las consecuencias finales. No registran el consumo exacto de
HOLD; con ellas no se identifica una intervención única como causa de cada
pérdida ni se sabe qué habría sucedido con una guarda alternativa.

Estas 160 partidas son desarrollo ya conocido. Los casos 144 y 154 ya
figuraban como pérdidas del control ampliado de B20. Las cohortes nuevas de
B22 permanecieron cerradas. Por tanto, B22-V demuestra un fallo de
conservación al ampliar desarrollo; no mide todavía transferencia a sus
casos nuevos.

**La búsqueda se atasca por cómo usa los intentos y el feedback.**

| Resultado de cada intento | R22 aleatorio | M22 con reparaciones | Total |
|---|---:|---:|---:|
| Alguna pérdida individual | 66 | 72 | 138 |
| Sin pérdidas, +1 nivel | 7 | 14 | 21 |
| Sin pérdidas, sin ganancia de niveles | 71 | 58 | 129 |
| Pasa: al menos +2 y ninguna pérdida | 0 | 0 | 0 |
| Acciones idénticas a la base, subconjunto de los anteriores | 60 | 47 | 107 |

Hay 182 propuestas distintas entre los 288 intentos. Los brazos comparten
104 propuestas de su corriente global por diseño; eso es emparejamiento
experimental y no debe contarse como 288 oportunidades independientes.
Cada brazo tiene 142 propuestas distintas. Se probaron las diez duraciones
permitidas: 0, 1, 2, 4, 8, 12, 16, 20, 24 y 32. B22 no volvió a restringir
toda la campaña a un único valor, como ocurrió en versiones anteriores.

De las 107 propuestas sin cambios de acciones, 79 no coinciden con ninguna
lectura de HOLD de la trayectoria base. Las 79 dejaron efectivamente las
acciones iguales. El resto, 28, sí podía cambiar un consumo y aun así no
cambió acciones. Deben distinguirse ambos casos: activación de una regla y
cambio de conducta son medidas diferentes. En el muestreo general hay 73
propuestas inactivas de 124 intentos; se admitían intencionalmente para
conservar el soporte de la distribución. Esto consume plazas sin aportar
información sobre mejores trayectorias.

El argumento de inactividad es acotado: la única intervención es el valor
HOLD y solo puede causar una primera divergencia cuando se lee ese valor.
Si la guarda no coincide con ninguna lectura de la base completa, no puede
aparecer esa primera divergencia bajo este ejecutor determinista. No permite
equiparar entre sí dos reglas activas ni extender el resultado a otros casos.

**La segunda reparación impone diversidad por encima de los fallos medidos.**
M22 efectuó 40 reparaciones, en veinte bloques de dos. El primer hijo ordena
por menor solapamiento con contextos de pérdidas y después mayor cobertura
de contextos de ganancias. El segundo antepone la máxima distancia respecto
al primero, medida sobre contextos observados de toda su historia. Los
resultados son consistentes con ese orden de prioridades:

| Reparación | Regresiones | +1 sin pérdidas | Sin ganancia y sin pérdidas |
|---|---:|---:|---:|
| Primer hijo, 20 intentos | 3 | 8 | 9 |
| Segundo hijo, 20 intentos | 20 | 0 | 0 |

Las veinte primeras reparaciones tenían `loss_context_overlap=0`;
las veinte segundas tenían `loss_context_overlap=1`. El segundo hijo volvía
a cubrir todos los contextos efectivos del padre asociados a sus partidas
con pérdida. Las veinte primeras redujeron el número de casos con pérdidas;
solo dos segundas lo redujeron. Esto identifica un mecanismo del selector
que desperdició presupuesto en esta campaña. Todavía no mide el resultado
de reemplazarlo por otro orden.

El indicador tampoco es un certificado causal: tres primeros hijos
empeoraron alguna partida aunque su solapamiento calculado fuera cero.
Cambiar la guarda produce trayectorias nuevas y consumos nuevos. El resumen
no contiene un modelo contrafactual que permita garantizar su resultado.

Un ejemplo completo está en `M22-822117`. El primer intento, HOLD=2 con
`level<=1` y `world_events<=20`, ganaba ocho niveles y perdía en tres casos.
El hijo 2 cambió el umbral a `<=4`: conservó todas las partidas, pero solo
ganó un nivel. El hijo 3 cambió a `>=4`: obtuvo cero niveles extra y perdió
en cinco casos. La reparación eligió un contraste muy amplio que también
reintroducía las situaciones conflictivas.

**El buscador cierra ramas que el juez aún no puede aceptar.** Su función
`eligible` requiere simultáneamente ganancia neta ≥2 y alguna pérdida.
Por eso una mejora de +1 sin pérdidas no recibe descendientes, aunque sea
útil como punto de partida. El requisito del juez se ha convertido en parte
de la política de investigación. Mantener la aceptación en +2 y permitir
investigar una rama de +1 son decisiones compatibles.

También obliga a completar el segundo hijo del padre original antes de
seguir un descendiente más prometedor. En `M22-822143`, el intento 15 dio
+5 con cuatro casos de pérdidas; el 16 redujo eso a +4 y una pérdida. El 17
volvió al padre 15 y obtuvo −3 con siete pérdidas. El descendiente 16 quedó
sin reparar al agotarse las ocho plazas reservadas para reparaciones.

El vecindario solo admite una edición de literal. Desde el primer padre
de `M22-822117`, la guarda exacta ganadora B21 necesita dos ediciones, por
lo que no está entre sus vecinos inmediatos. La variante de dos condiciones
`level<=1, world_events<=8` ocupa el puesto 160, con solapamientos 1/9 y 2/3
para pérdidas y ganancias. Esa variante no fue medida aquí y no se presume
equivalente a B21. La comparación con la regla conocida es retrospectiva;
sirve para explicar la distancia de búsqueda, nunca como descubrimiento
autónomo ni como respuesta que debamos entregar al siguiente LLM.

**El lenguaje conserva capacidad demostrada en desarrollo.** El control
humano de B20 obtuvo +6 niveles y cero pérdidas en las mismas 160 partidas.
Su política base coincide con B22 y su propuesta sigue siendo legal bajo
la gramática B22. El recibo de auditoría y la diferencia del control se
recalculan en el análisis complementario. Por tanto, no está justificado
atribuir estos 288 rechazos al agotamiento completo del lenguaje. Sigue
pendiente que el investigador encuentre por sí mismo una solución que
conserve esa ventaja en casos nuevos. El control permanece excluido de sus
entradas.

La mejora parcial de M22 —catorce propuestas de +1 conservador frente a
siete de R22— merece investigarse, pero los ocho pares no producen ningún
pase y no demuestran superioridad en el objetivo registrado. Las propuestas
están relacionadas por linaje y emparejamiento: no procede tratar 14/144 y
7/144 como ensayos independientes para declarar significación.

**El siguiente experimento debe separar la reparación y la aportación del
modelo.** El [contrato del micro B23](ECHO45-S6-B23-MICRO-DESIGN.md) conserva
R22 y M22 como controles, añade un selector corregido y dos brazos con
neocórtex de 7B y 14B. Las correcciones propuestas son detectar inactividad
demostrable antes de asignar una simulación, mantener ramas conservadoras,
refinar el mejor descendiente y distribuir intentos entre distintos
compromisos de cobertura y riesgo observado. Las observaciones seguirán
siendo asociaciones; el juez conserva el criterio de cero pérdidas.

Los dos casos de pérdida amplia pasan a formar parte explícita del desarrollo
del siguiente micro, con la misma información para todos los brazos. Esto
declara su exposición y evita repetir la misma comprobación demasiado tarde.
Los candidatos nuevos necesitarán validación amplia y conservación reservada
después de congelarse. No se abren campaña ni examen por una mejora aislada.

Los artefactos B20 fijaban Qwen3-4B-Instruct-2507 Q4_K_M; B21 y B22 no hicieron
llamadas LLM. La comparación propuesta de 7B y 14B será una condición nueva.
En este entorno solo se ha localizado el GGUF 4B bajo `/home/user/models`;
la resolución de DNS hacia Kaggle y Hugging Face falla. El micro con modelos
quedó inicialmente como borrador. La [implementación posterior](ECHO45-S6-B23-IMPLEMENTATION.md)
ya completa selector y ejecutor; faltan los pesos verificados y el acceso operativo. No se ha reservado
GPU ni gastado presupuesto de API.

Reproducción y artefactos:

```bash
python3 -m seed.s6b22_forensics
PYTHONDONTWRITEBYTECODE=1 lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b22_forensics_neighbors
python3 -m unittest tests.test_s6b22_forensics -v
```

- [Resultados recalculados](../lab/seed/s6b22-forensics-20261007/analysis.json).
- [Las 288 propuestas, sus guardas y sus efectos](../lab/seed/s6b22-forensics-20261007/proposals.csv).
- [Efectos completos por caso](../lab/seed/s6b22-forensics-20261007/proposals.json).
- [Reconstrucción de reparaciones y control de capacidad](../lab/seed/s6b22-forensics-20261007/repair-reconstruction.json).
- [Hashes de entradas leídas](../lab/seed/s6b22-forensics-20261007/input-hashes.json).
- [Cierre original B22](../lab/seed/s6b22-20261006/closed.json).

Las cinco pruebas del instrumento pasan. Durante su desarrollo se corrigió
una comprobación auxiliar: `base_sha256` del plan de capacidad B20 identifica
una medición B19, no los bytes de la política. La comparación ahora usa las
políticas serializadas y las mediciones amplias completas. Ese error del
análisis no alteró B22 ni sus resultados.
