# E · último intento total · contrato prospectivo · 23/10/2026

Desarrollo autorizado por Nav el 23/10. Este documento se fija antes del primer
paso nuevo. Es el **único intento adicional de E en conjunto**. Si falla cualquier
puerta, E se cierra definitivamente como **«deuda residual, autopsiada»**.
Sin examen, API, LLM, publicación o cambios en estudios históricos/NEXUS.

## Evidencia previa y pregunta

Se verificaron contra el manifiesto histórico las tres trazas slow con coste y
`tail-diagnostics.json`, sin ejecutar el simulador. Los 136 pasos con coste tienen
señal de vasos y cero de hazards. En los 136, el máximo de vasos en los 16 bins es
≥75 mientras que `decision.close` del rumbo elegido es <75. Hay 109 pasos con
ruedas opuestas, 102 con diferencial absoluto ≥1,99; en cada uno de los tres
mundos los diez pasos anteriores al primer daño ya tienen vasos ≥75.
Esto identifica una observación disponible antes del daño que el actuador no
protege. No demuestra causalidad física ni que una reparación preserve progreso.
Detalle reproducible: `lab/echo58/shieldrepair/final-20261023-r1/prior-inspection.json`.

Hipótesis única: añadir margen de contorno a los canales aprendidos como costosos
y limitar el giro cuando cualquiera de sus bins se aproxima a 75 reduce las
colas que el regulador de avance deja al barrer el coche. El XML original tiene
parachoques hasta 0,175 m y ruedas hasta 0,155 m desde el centro; el margen elegido
es una aproximación discreta, no cálculo exacto del volumen barrido.

## Candidato único y controles

Importar Controller/Gate/aprendizaje y sensado heredados. Nuevo módulo aislado
`echo58/shieldrepair`; no modificar originales. `repair` parte de slow (objetivo
300 mm/s, freno400, margen3). Solo para canales que la tabla ya reconoce como
costosos, sumar **5 puntos** a cada bin no nulo (saturación100) antes de la decisión
del gate; equivale nominalmente a150mm con LiDAR lineal de3m. El aprendizaje usa
lecturas originales. La propuesta de goal y el coste real no cambian.
Si el máximo **original** de cualquier canal aprendido costoso es≥75, limitar
el término diferencial de ruedas a **±0,25**, conservando el término común de
avance/freno; después saturar cada rueda a[-1,1]. Fuera de esa zona, actuación
slow original. Estos números quedan fijos; ninguna variante o selección posterior.
El criterio de giro usa todos los bins, también objetos fuera del rumbo elegido.

Controles fuertes: `legacy` y `slow` originales y congelados por réplica, mismos
mundos/tabla/presupuesto. `repair` debe ganar por coste conservando progreso
frente a ambos. Un agente inmóvil pierde la puerta de progreso. No hay parada
por presupuesto ni acceso a coste acumulado para seleccionar la política.

## Agenda y puertas fijadas

Dos tablas aprendidas nuevas e independientes, inicialmente vacías:40 episodios
legacy r0 semillas61000–61039 y r1 62000–62039. Barrera y compromiso de ambas
tablas antes de validación.50 semillas nuevas por réplica: r0 71000–71049 y r1
72000–72049, cada una con legacy/slow/repair. **380 episodios**,1000 pasos máximo;
máximo4 procesos. Sin reintentos, sustituciones, omisiones, terminación temprana
o ajustes. Semillas históricas y exámenes no se abren. Aprendizaje se informa aparte.

**U (conjunción por réplica):** legacy y slow deben tener coste positivo (si no,
resultado inconcluso en comparación correspondiente, nunca verde); legacy debe
tener al menos una cola>25. En cada réplica, repair debe tener coste≤50% legacy,
estrictamente menos coste que slow, menos colas>25 que legacy y no más que slow.
Debe lograr alguna meta y **≥80% metas de cada control** (comparación entera, sin
redondeo). Además prueba de signos unilateral pareada de coste repair frente a
slow en100 pares: p exacta≤0,05, empates solo excluidos de esa prueba. Única prueba
inferencial primaria; las puertas conjuntas son obligatorias.

**B:** cero episodios repair>25 en100 validaciones. Un solo exceso es rojo.
**Verde completo:** U+B+auditoría técnica. No sensibilidad no es verde. Cualquier
no-verde termina este único intento; no se relanza ni se abre otro frente de E.

## Custodia y límites

Congelar fuentes, contrato, plan, pruebas, agenda y recursos/versiones del entorno
existente `~/.venvs/safe1` antes de aprender. Trazas encadenadas de cada paso real,
identidad de corrida/réplica/fase/semilla/brazo/tabla, lecturas, decisión y acción,
componentes devueltos por env.step, costes, metas, cierres y errores persistentes.
`live.jsonl` registra observaciones/acciones/resultados reales; no se realimenta.

Auditoría offline: decisiones y actuador desde estados grabados; aprendizaje,
continuidad y hashes, conjunto exacto de recibos/trazas, barrera de tablas, fases,
igualdad del estado inicial de cada triple pareado, agregados y puertas enteras.
No es replay físico de MuJoCo. Cualquier fallo instrumental bloquea verde;
conservar parciales, sin contar fallos como coste cero. Informe aunque rojo.
Revisión independiente del contrato/código antes de medir si el coordinador puede
realizarla; su ausencia se declara y prohíbe afirmar revisión independiente.
Alcance: dos aprendizajes y100 mundos nuevos de desarrollo SafetyCarGoal2-v0;
no certifica seguridad universal, otros robots o tareas. Los rojos previos quedan rojos.
