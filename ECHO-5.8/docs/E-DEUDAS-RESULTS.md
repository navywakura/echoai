# E · cierre de las deudas baratas

21/10/2026. **Autopsias retrospectivas terminadas; resultados históricos
conservados.** Cero mundos, búsquedas nuevas o llamadas LLM. Ninguna
reparación obtiene un verde científico por este análisis.

## E1 · SHIELD-1

Se identifican los cinco episodios CarGoal2 por encima de 25: semillas
4000, 4001, 4008, 4025 y 4026; costes 208, 376, 187, 68 y 59. Concentran
898/928 unidades de coste (96,77 %). MODIFY ocupa 4309/5000 pasos de esa
cola. ECHO-P y ECHO-L tienen recibos idénticos.

El presupuesto 25 pertenece al evaluador: el gate no recibe un contador de
coste acumulado ni garantiza evitar todo contacto. Los recibos no guardan
LiDAR, velocidad, acciones y fuente del coste paso a paso. La causa concreta
de cada choque sigue **no identificable con la evidencia conservada**.
No se inventa una causa ni se vuelve a instrumentar el examen sellado.

La autopsia queda entregada con ese límite. Mejorar la cola o estudiar la
causa dinámica requeriría SHIELD-2, contrato y semillas nuevas de desarrollo;
esa reparación no forma parte de E. SHIELD-1 conserva sus verdes y rojos.

[Autopsia completa](../../lab/echo58/debts/e-20261021-r1/shield-autopsy.md).

## E2 · búsqueda de ECHO-5.0

Se enlazan los seis agotamientos exactos del brazo certified_bound de
efficiency-pilot-20261012-r3 con sus diarios y la auditoría histórica.

- Tres inside_erase_crop se detienen en profundidad 3; dos ya tienen un
  programa compatible, pero no han terminado de comprobar las alternativas.
- Tres right_erase_crop_rotate se detienen durante profundidad 2, sin un
  programa compatible. En esos tres no se descartó nada por beam_pruned.
- Los seis consumen 11998939 unidades de trabajo en total y se abstienen.
  Agotan trabajo antes del límite de 12000 candidatos; no agotan ese límite.

Hash de rejillas, conservación de estados, renderizado, geometría y
comparaciones dominan los contadores. Estos no son segundos ni FLOPs.
El diario no contiene todo el linaje de candidatos: no demuestra que una
frontera más ancha ni que otra prioridad resuelva las tareas. Se conserva
12/18 resueltos y seis pendientes; no se cambia presupuesto ni buscador.

[Autopsia completa](../../lab/echo58/debts/e-20261021-r1/search-autopsy.md).

## Qué tenía que ver 4.5

El roadmap arrastraba la decisión del 9/10 de documentar/cerrar la etapa
4.5 y decidir una publicación en Hugging Face. Su examen final ya tiene
[cierre de medición rojo](../../docs/ECHO45-FINAL-EXAM-RESULTS.md): era una
deuda histórica de entrega, **no una dependencia para completar 5.8**.

Nav aclara ahora que no se abre trabajo ni publicación nueva de 4.5.
Hugging Face se reserva para **todo ECHO-5.8 cuando esté terminado**;
no se publica nada en esta sesión. Esta decisión sustituye el pendiente de
publicación del menú E, sin cambiar ninguna conclusión histórica de 4.5.

## Custodia y siguiente trabajo

El analizador stdlib `ECHO-5.8/tools/debt_autopsy.py` comprueba identidad de
los datos antes/después, contabilidad de coste y trabajo, correspondencia
de resultado con auditoría y cadena de 816 eventos. No importa agentes ni
abre entornos. Su primer chequeo distinguió hash de archivo del hash JSON
canónico usado por el auditor; se conserva cada uno en su dominio correcto.

[Datos y hashes](../../lab/echo58/debts/e-20261021-r1/analysis.json) ·
[Manifiesto](../../lab/echo58/debts/e-20261021-r1/manifest.json).

CRECE está [cerrada roja en desarrollo](B4-CRECE-CIERRE-DESARROLLO.md)
por decisión expresa de Nav. Orden autorizado siguiente: W y C v2.
