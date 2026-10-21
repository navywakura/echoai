# E4-ROLES-1 · Anexo L v2 «¿y si la tengo yo?» — contrato (aprobado 2026-09-24)

**Declarado posterior al rojo** de L v1 (`c77b31cd…`, L4 21/24). Diagnóstico:
la deducción «B miente, luego C» ya existía y acertaba. Los 3 fallos eran temas
cuya respuesta tenía **el propio ECHO**, que no sabe qué sabe hasta intentarlo.

## Único cambio: metaconocimiento

ECHO recibe, por tema, una señal propia de **«¿me la sé?»** (sensación de saber):

- Acierta el **90 % en ambos sentidos**, con ruido sembrado. Valor fijado antes de ejecutar.
- Es una **hipótesis propia** (sin hecho ni extracto, procedencia «metaconocimiento»).
  Solo se convierte en hecho si ECHO se prueba a sí mismo y la respuesta abre.
- La deducción ordena las fuentes por fiabilidad: **1)** hecho verificado de quién
  sabe; **2)** su propia señal, si él sigue siendo candidato; **3)** rango derivado
  entre los demás candidatos. Si la señal dice «no me la sé», ECHO no se propone a
  sí mismo.

B y C no reciben la señal. Todo lo demás, incluida la mentira de B y la llave, es igual que en L v1.

## Criterios (por cohorte, todos)

L1–L3, L5 y L6 **idénticos a v1**. L6: con metaconocimiento apagado y tasa 0,
la sesión reproduce v5 bit a bit. **L4 con el mismo umbral: ≥90 %.**
Nuevo **L7:** la señal de metaconocimiento nunca es hecho, y cada vez que falla
queda refutada por un recibo `self_fail` (sin hecho falso).
Se publica sin ser criterio: L4 del control sin metaconocimiento en los mismos
recibos, y el neto con y sin mentiras.

## Semillas

Desarrollo **611, 623, 639**. Examen, si el desarrollo pasa (encargo de Nav de
dejarlo verde si es legítimo): **268001..268008** y **268101..268108**.
Auditoría en proceso nuevo; su recibo acredita `liar_annex_green`.
