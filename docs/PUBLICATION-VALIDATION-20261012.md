# Publicación de ECHO-5 5.0.0 — validación

La copia pública adaptada a `core/` pasó sus comprobaciones propias:
502 pruebas del core (26 omisiones opcionales), 32 externas, sintaxis JavaScript
y conservación de fuentes. Cinco pruebas adicionales del verificador de fuentes
pasaron. El recibo identifica esta distribución, no el snapshot original.

[Recibo y logs](../research-archive/20261012/publication-checks/result.json) ·
[Manifiesto del expediente](../research-archive/20261012/MANIFEST.json).

No se incluyeron entornos, credenciales ni configuración personal de agentes.
El manifiesto de distribución identifica todas las fuentes distribuidas; el
manifiesto de investigación distingue bytes originales y exportados.
El release declara verde solo dentro del alcance definido, con seis tareas
independientes pendientes y S6 abierto hasta después de ECHO-5.5.

La repetición completa pasó sus cuatro auditorías y reprodujo los resultados del
laboratorio. Tres hashes coinciden; en exploración solo difieren tiempos de reloj,
no resultados, acciones ni trabajo lógico. Duró 147,49 segundos en CPU en segundo
plano. [Comparación](../research-archive/20261012/publication-reproduction/parity.json).
Son casos ya medidos, no una confirmación científica nueva.
