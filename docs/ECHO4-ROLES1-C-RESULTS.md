# E4-ROLES-1 — C implementada, testigos de desarrollo válidos

2026-09-24. [Contrato C/D](ECHO4-ROLES1-CD-DESIGN.md), aprobado.
Auditoría en proceso nuevo válida, cero hallazgos. Digest
`ba7225c4217a99786b85a63070e554588cf27783819ba333ae0ed205bd41e863`.
`roles1_green=false`: D sin abrir. Custodia de ROLES A/B (`36b9cab3…`) y RELATION comprobada.

[Informe](../lab/echo4/roles1-c-dev-v1/report.json) ·
[Testigos](../lab/echo4/roles1-c-dev-v1/witnesses.json) ·
[Código](../echo4/roles_c.py) · [Banco](../echo4/roles_c_bench.py) ·
[Pruebas](../tests/test_echo4_roles1c.py).

## Defecto encontrado en A/B sellada, corregido en C

Cuando el gate bloquea al aprendiz, el Agent nativo devuelve la acción 2
(esperar). En ROLES la acción 2 significa «hacerlo él», así que **un veto hacía
que el aprendiz ejecutara la tarea y pagara 2**. La prueba A/B comprobaba el
BLOCK pero no el coste. No afecta a los números de A/B porque el banco nominal
no veta. `RolesCSession` corrige el caso: veto = ronda sin efecto ni coste.
D usa esta sesión; C0 demuestra que, sin vetos, reproduce bit a bit las 18
vidas-brazo selladas de A/B. La fuente A/B no se ha tocado.

## Testigos, semillas 211 / 223 / 241, brazo `competence`

| # | Escenario | Resultado | Tipo |
|---|---|---|---|
| C0 | Paridad nominal con A/B sellada | 18/18 digests idénticos | criterio, **cumple** |
| C1 | La competente rechaza (gate real) 48 rondas tras la primera deriva | 22/8/10 asignaciones rechazadas; neto 1928/1892/2081 frente a 2200/2186/2207. La fila no ve rechazos: sigue asignándole | límite publicado |
| C2 | La contraparte 1 retransmite lo que hace la 2 | 174/186/172 recibos retransmitidos, todos hipótesis con procedencia, ninguno en la fila. Neto 1756/1748/1640: **cuesta 440–570** no poder verificar | criterio (nunca hecho) **cumple** + coste |
| C3 | Cuerpo nuevo con otra competencia en la ronda 240 | 6 aciertos seguidos a las 5/4/2 rondas (≤48) | criterio, **cumple** |
| C4 | Contraparte ausente 72–119, con deriva en 96 | 16/9/37 asignaciones sin llegada, 0 recibos inventados; recupera en 20/7/19 al volver | criterio, **cumple** |
| C5 | Cambiar quién afirma el rango | Trayectoria de `competence` idéntica bit a bit. `rank_follow` da 32/96 en todos los regímenes: con una permutación, el afirmante siempre es competente en exactamente un tipo; el «acierto por azar» total no existe en este mundo | criterio, **cumple** |
| C6 | 510 rondas (la mayor longitud equilibrada ≤512) y CAM llena | Cierre limpio; CAM llena para la sesión; cero borrados | criterio, **cumple** |
| C7 | Veto del operador en 200 y parada | 40 rondas vetadas, coste 0; tras parar no continúa | criterio, **cumple** |
| C8 | Recibo no canónico | Para sin asignar; libros intactos. Un recibo falsificado pero canónico y posible no se detecta | criterio + límite |

7 pruebas nuevas de C.

## Lectura

«Poder no es deber» (C1): el agente solo aprende de lo que se ejecuta, así que
un rechazo lo deja insistiendo. «¿Podrías hacer de intermediario?» (C2): lo
retransmitido nunca pasa a hecho y eso tiene un coste medible. «Creer no es
poder» (C5): la afirmación de rango no toca la decisión.

Hubo ejecuciones exploratorias antes de sellar.
