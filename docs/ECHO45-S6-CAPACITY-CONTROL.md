# S6: control manual de capacidad, sin LLM

2026-09-28. Contrato de desarrollo. Se congela antes de la primera medición.
No constituye una campaña de automejora ni permite marcar S6 en verde.

Se prueban exactamente 20 candidatos en el orden de `seed/s6_capacity.py`.
Todos son una reparación de un parámetro, legal y expresable por la gramática
local congelada de B4. No contienen IDs, semillas, familias, coordenadas ni
datos del examen. Se elige el primero que pasa en el orden congelado; se
publican también los demás resultados. No se añaden candidatos tras medir.

Las hipótesis son: cambiar la evidencia antes de identificar el cuerpo;
orientar la acción después de un efecto observado; cambiar el orden de
exploración, límite de entradas o soporte requerido; y ajustar la espera
tras identificar una tecla de reinicio. No se añade ninguna habilidad al
agente ni se modifica el ejecutor o los agentes congelados.

A: versiones 2/3, semillas 0–19; B: versiones 2/3, semillas 20–39.
Son desarrollo ya utilizado, no una cohorte ciega. Una repetición por juego,
2000 decisiones por partida, cuatro procesos CPU, cero llamadas LLM/pago.
Presupuesto máximo 2640 partidas: dos de paridad del observador, 40 inertes,
160 de base/replay, 1600 A/replay de candidatos y hasta 800 B/replay; quedan
38 de margen técnico que no autorizan nuevas propuestas ni cohortes.

Se mantienen los filtros de B4:

- V1: JSON cerrado, condiciones observables y parámetros acotados.
- V2: replay de cada candidato en procesos nuevos; comparación exacta del
  registro completo serializado a JSON, sin redondeo ni exclusiones.
- V3: al menos +2 niveles A y ninguna pérdida individual de niveles ni
  puntuación oficial, con tolerancia numérica original de 1e-10.
- V4: ninguna pérdida individual B. Para los candidatos que llegan a B se
  repiten también todas sus partidas, bajo V2.

El control inerte se compara con la base por acciones, frames, métricas,
reinicios y modelo completo. Se excluyen únicamente del cotejo de paridad
los identificadores del parche; no se excluye el modelo ni ningún resultado.
La base nueva debe reproducir las 40 partidas A de B4 y su replay A/B.

Se registran activaciones reales por partida, acciones y frames cambiados,
ganancia y regresiones. Una partida completa v3/semilla0 por medición queda
visible en el diario ARC existente y la mini terminal. El resto conserva
el registro completo de ejecución; el observador pasivo se verifica antes.
No se generan pensamientos ficticios ni se instrumentan exámenes.

Los archivos, configuración, runtime y fuentes SDK quedan congelados en
`lab/seed/s6-capacity-20260928/profile.json`. Los resultados se escriben en
otra ruta documental para no alterar el contrato durante la ejecución.
Las campañas anteriores quedan intactas. La diagnosis histórica lee solo A.

Si un control pasa, la siguiente etapa es contrastar repetición y evidencia
del prompt en un piloto LLM nuevo, con presupuesto igual, varias semillas y
contrato previo. El control humano no puede pasar como propuesta del modelo.
Si ninguno pasa, se documenta el alcance finito y se estudian operaciones
nuevas en tareas sintéticas; no se concluye imposibilidad de todo el DSL.

Ejecución en el entorno ARC gestionado:

```
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6_capacity prepare
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6_capacity run
```
