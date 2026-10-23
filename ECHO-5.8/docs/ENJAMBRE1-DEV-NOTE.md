# C v1 · ENJAMBRE-1 — nota de desarrollo (21/10/2026)

Solo familias y semillas de desarrollo (9 100 000+), macros 1–6, sin tocar el
examen. Datos: `lab/echo58/enjambre/dev-20261021T000956.json`; variantes con
`lab/echo58/enjambre/dev-variant-script.py` (copia del script de scratch).

Suma sobre 6 macros (puntuación = suma de rondas por mundo, menos es mejor;
mínimo 48, máximo 1488):

| Brazo | Contrato (A2) | A1 (ids iguales en todos los mundos) | A1 + identidades en la global |
|---|---|---|---|
| enjambre | 217 | 215 | **198** |
| sin_global | 220 | 218 | 218 |
| sin_ayuda | 217 | 216 | 199 |
| sin_privada | 244 | 193 | 193 |
| global_barajada | 213 | 206 | 203 |
| aislados | 221 | 222 | 222 |

Episodios fallidos del equipo (contrato): enjambre 381, sin_ayuda 135,
aislados 139. Mundos resueltos: 45 de 48 en todos los brazos.

Lectura:

1. **Con el contrato tal como está, ningún brazo se distingue.** En A2 los ids
   cambian de mundo a mundo y la global solo lleva roles; MEMORIA-X ya mostró
   que en A2 transfieren pocos roles. No hay casi nada útil que compartir.
2. **Cuando los ids significan lo mismo en todos los mundos (A1) y la global
   comparte identidades**, el equipo mejora: 198 frente a 222 de los aislados
   (~10 %). Es lo único que se ha visto ayudar.
3. **Ir a ayudar no adelanta ningún mundo** y triplica los episodios
   fallidos (381 frente a 135): quien ayuda falla en los mismos mundos
   difíciles. El cuello de botella es la política, como en B.
4. **La memoria privada no aporta** en esta tarea: solo global iguala o gana
   (193). E3 saldría rojo.

Sin examen. Decisión de Nav pendiente.
