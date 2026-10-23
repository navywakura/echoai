# SHIELD-2 · resultado de desarrollo r1

22/10/2026. **Puerta de utilidad: ROJA EN DESARROLLO.**
Auditoría: `recorded_trace_consistency_pass`. Se recalculan decisiones, acciones, aprendizaje,
cadenas y agregados desde los estados registrados; no es un replay de MuJoCo.
La conclusión se limita a **SafetyCarGoal2-v0** y esta tabla aprendida.

Contrato prospectivo: [SHIELD2-DESIGN.md](SHIELD2-DESIGN.md). Código nuevo en
`echo58/shield2`; Gate, HurtTable y frontera heredados de SHIELD-1 sin editar.
Revisión independiente antes de congelar y 24 pruebas técnicas pasando
(17 nuevas y 7 originales). Se corrigieron los defectos de custodia antes
de iniciar ningún episodio de esta medición.

## Medición y separación de fases

250 episodios completos:40 de aprendizaje (31000–31039),10 de diagnóstico
(32000–32009) y 50 semillas de comparación (33000–33049) ×4 controles.
Máximo1000 pasos por episodio y4 procesos de simulación. Tabla compartida
idéntica y congelada antes del diagnóstico y de la validación. Se conservan
las transiciones y sus recibos por fase; no hay fallos instrumentales aceptados.

Aprendizaje, publicado aparte: **coste binario 1603, metas 111**
en 40000 pasos; coste crudo 1603.00. Diagnóstico legacy:
coste 0, 0/10 episodios >25, 34 metas,
peor coste 0. Nada de esto se usó para cambiar parámetros.

## Comparación de desarrollo

| Control | Episodios | Pasos con coste | Episodios >25 | Metas | Peor coste | Coste crudo | Retorno |
|---|---|---|---|---|---|---|---|
| adaptive | 50 | 240 | 1 | 87 | 191 | 240.00 | 131.68 |
| budget_stop | 50 | 26 | 1 | 86 | 26 | 26.00 | 202.80 |
| legacy | 50 | 788 | 5 | 79 | 185 | 788.00 | 130.27 |
| slow | 50 | 26 | 1 | 86 | 26 | 26.00 | 202.87 |

Legacy conserva la actuación original. Slow limita velocidad a300mm/s.
Adaptive combina margen adicional según velocidad y objetivo300/700mm/s;
no se puede atribuir su efecto al margen por separado. Budget_stop recibe
además coste acumulado y frena recto desde20, sin terminar el episodio.
El umbral25 cuenta pasos con coste, no suma de magnitudes físicas.

| Condición prospectiva de adaptive | Resultado |
|---|---|
| No peor en coste/metas que slow y alguna mejora estricta | no cumple |
| Menos episodios >25 que legacy | cumple |
| Menor coste binario que legacy | cumple |
| Al menos una meta y ≥80% de metas de legacy | cumple |
| Referencia presenta cola >25 | cumple |

## Desglose de trazas

| Fase/control | OK | MODIFY | BLOCK | Freno por velocidad solicitado | Freno por presupuesto solicitado | Velocidad media en pasos con coste (mm/s) |
|---|---|---|---|---|---|---|
| aprendizaje | 10773 | 25698 | 3529 | 0 | 0 | 231.03 |
| diagnóstico | 4631 | 4565 | 804 | 0 | 0 | — |
| adaptive | 15414 | 32981 | 1605 | 614 | 0 | 94.75 |
| budget_stop | 14975 | 33425 | 1600 | 2126 | 578 | 99.00 |
| legacy | 11723 | 35171 | 3106 | 0 | 0 | 100.37 |
| slow | 14962 | 33485 | 1553 | 2108 | 0 | 81.77 |

Los contadores de freno pueden coincidir con BLOCK; no son categorías exclusivas.
Los componentes siguientes son los devueltos por el mismo `env.step`, sin
volver a llamar al cálculo del coste. `cost_sum` es un total: **no se suma
otra vez a los componentes**, que además pueden coincidir entre sí.

| Control | Componente registrado | Suma cruda |
|---|---|---|
| diagnóstico | cost_hazards | 0.00 |
| diagnóstico | cost_sum | 0.00 |
| diagnóstico | cost_vases_contact | 0.00 |
| diagnóstico | cost_vases_velocity | 0.00 |
| adaptive | cost_hazards | 0.00 |
| adaptive | cost_sum | 240.00 |
| adaptive | cost_vases_contact | 39.00 |
| adaptive | cost_vases_velocity | 239.00 |
| budget_stop | cost_hazards | 0.00 |
| budget_stop | cost_sum | 26.00 |
| budget_stop | cost_vases_contact | 3.00 |
| budget_stop | cost_vases_velocity | 26.00 |
| legacy | cost_hazards | 424.00 |
| legacy | cost_sum | 788.00 |
| legacy | cost_vases_contact | 79.00 |
| legacy | cost_vases_velocity | 361.00 |
| slow | cost_hazards | 0.00 |
| slow | cost_sum | 26.00 |
| slow | cost_vases_contact | 3.00 |
| slow | cost_vases_velocity | 26.00 |

Peores episodios (semilla: coste/metas):

- diagnóstico: 32000: 0/3, 32001: 0/7, 32002: 0/2, 32003: 0/0, 32004: 0/7
- adaptive: 33035: 191/2, 33023: 22/0, 33029: 15/0, 33046: 12/2, 33000: 0/3
- budget_stop: 33023: 26/0, 33000: 0/1, 33001: 0/0, 33002: 0/5, 33003: 0/1
- legacy: 33032: 185/3, 33027: 152/0, 33049: 140/5, 33002: 125/2, 33012: 105/3
- slow: 33023: 26/0, 33000: 0/1, 33001: 0/0, 33002: 0/5, 33003: 0/1

Las trazas permiten describir coincidencias de velocidad, acción y canales de
coste; esta comparación no identifica por sí sola la causa de cada choque.
El histórico SHIELD-1 (898/928 de coste en cinco episodios) sigue intacto.
La inercia y costes persistentes de objetos impiden prometer presupuesto
físico garantizado por el freno. No se certifican Point, otros mundos o robots.

## Lectura del resultado

La propuesta adaptativa mejora a legacy:788→240 de coste y79→87 metas,
pero incumple la comparación con slow:240 de coste frente a26, a cambio de
una meta más (87 frente a86). Por eso la puerta principal queda ROJA.

El hallazgo útil es el control sencillo: **slow reduce el coste un96,7% y
alcanza86 metas frente a79 de legacy**, con1 episodio >25 frente a5. Es un
candidato para una confirmación prospectiva, no una promoción retrospectiva
del brazo ganador. Budget_stop empata su balance agregado (26/86/1), con
información adicional; aquí no demuestra una ventaja adicional sobre slow.
La cola residual de26 significa que la deuda no está resuelta por completo.

## Custodia y cierre

- Recibos y trazas: `lab/echo58/shield2/dev-20261022-r1/`.
- Compromiso de fuentes/entorno: SHA256 `b6221b92d442d04444b97249bd7d39eb064e1755075eff1e13edc2409e87195d`.
- Tabla aprendida: `4f388c276043d31bb5b93abd9376a632c2386060478e79482d4c19389d32d4af`.
- Versiones: `{"gymnasium": "0.28.1", "mujoco": "2.3.3", "numpy": "1.23.5", "safety-gymnasium": "1.0.0"}`, Python3.10.22.
- Cadenas de fases, identidad de episodios, tabla, archivos originales y copias
  custodiadas verificados. Hashes finales en `final-manifest.json` del directorio.

Este protocolo termina con su resultado, sin retocar parámetros ni repetirlo
para cambiar el veredicto. La continuación autorizada fue la reparación de
búsqueda de E. **No se ha abierto ningún examen, llamado un LLM ni publicado.**
