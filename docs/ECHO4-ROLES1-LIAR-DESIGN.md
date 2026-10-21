# E4-ROLES-1 · Anexo L «B miente diciendo que sabe» — contrato (encargado por Nav 2026-09-24)

ROLES-1 v5 es verde (`c98c7ab6…`) y no se modifica. Este anexo, pedido por
Nav, prueba la mentira **afirmativa**. En v5 C1, B decía «no la sé» cuando
sí la sabía. Aquí B dice **«sí, la sé»** cuando **no** la sabe y entrega una
respuesta falsa.

## Escena

ECHO pregunta a B. En un **porcentaje aleatorio de los casos**, B contesta con
seguridad aunque no sabe (la tasa de cada vida se sortea con semilla entre el
20 % y el 50 %). Si ECHO se fiara, «ya tengo respuesta» y no pensaría en C. ECHO
tiene dos vías para darse cuenta:

1. **Conocimiento previo verificado:** ECHO ya comprobó antes que ese tema lo
   responde C. Entonces el «sí» de B choca con un hecho, y ECHO marca la respuesta
   como sospechosa **antes de verificarla**.
2. **La llave:** la respuesta se comprueba contra el mundo. Solo la de quien sabe
   de verdad (C) abre. La de B falla, y eso queda como hecho: «B dio una respuesta
   que no abrió». Nunca «B sabe» ni «la respuesta es X».

Después de detectar la mentira, B queda eliminado en esa ronda, la deducción
apunta de nuevo a quien sabe (C) y la fiabilidad derivada de B baja: es una
consulta sobre los recibos, no una etiqueta.

## Criterios (fijados antes de ejecutar; por cohorte y todos)

| # | Exige |
|---|---|
| L1 | **Cero hechos falsos:** ninguna respuesta de B se convierte en hecho. En paralelo, un predictor *crédulo* (que acepta cualquier «sí» como saber) se mide en los mismos recibos para mostrar cuántos habría creado |
| L2 | **Toda mentira queda detectada** por la llave: 100 % de las respuestas falsas registradas como «no abrió» |
| L3 | **Detección previa:** cuando ECHO tenía un hecho verificado de que el tema es de otro, marca la respuesta de B como sospechosa antes de verificar en **≥95 %** de esos casos, con **0 falsas alarmas** sobre respuestas honestas |
| L4 | **Tras la mentira, apunta a la llave:** la deducción de ECHO señala al que sabe de verdad en **≥90 %** de las rondas con mentira detectada |
| L5 | **Fiabilidad derivada:** B acumula respuestas fallidas y C y ECHO ninguna. **Cero acusaciones** a agentes honestos |
| L6 | Integridad: invariantes, determinismo, cero borrados y LLM; con tasa 0, el mundo reproduce v5 bit a bit |

Se publica sin ser criterio: neto de ECHO con y sin mentiras, y cuántas rondas
con mentira acaba resolviendo la Q con C.

## Semillas

Desarrollo **511, 523, 539**. Examen: cohortes nuevas **267001..267008** y
**267101..267108**, abiertas por encargo explícito de Nav de terminar ROLES
aquí. Auditoría en proceso nuevo. Su recibo acredita `liar_annex_green`; no
cambia el verde de v5.
