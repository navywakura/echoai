# CONT-D — límite observado durante la preparación de A

2026-09-22, antes del lock y antes de ejecutar B/C.

La receta inicial alternaba (52,44) y (68,58) también para recuperación.
Con H desacoplada, la escuela y seis sondas originales producen:

| Cuerpo A | Sondas / pasos | Resultado | Candidatos H / θ |
|---|---|---|---|
| (52,44) | 6 / 44 | `unknown`, posibles `nominal, own`, `ambiguous` | 30 / 4 |
| (68,58) | 6 / 44 | `own`, confirmado | 1 / 4 |

La primera preparación falla al exigir confirmación para adjuntar el
controlador. No es un error del serializador: el SELF original se abstiene
correctamente dentro de su resolución sensorial. No se modifica ese SELF,
su prior ni sus criterios. Tampoco se abre B/C para buscar parámetros.

Revisión prospectiva del examen **antes del lock**: conservar los cuerpos
previstos, asignar el segundo a los casos que requieren control confirmado
y añadir un caso explícito `ambiguous` con el primero. Quedan 23 casos por
etapa. Pendiente/buzón/cancelado también usan el primero y deben conservar
la eventual abstención. Nuevo cuerpo usa H del segundo y θ del primero,
con recibos/calibración propios. Nominal 0/2/4 conserva la alternancia.

El KPI sigue siendo continuidad exacta, nunca atribución correcta en todos
los cuerpos. Una abstención no es una vida recuperada. Este resultado de
preparación se conserva como límite; no existió campaña final ni lock antes
de este ajuste. Si B/C falla, no se vuelve a ajustar esta versión.
