# E · último intento total · cierre definitivo · 23/10/2026

**ROJA EN DESARROLLO. E queda cerrada como «deuda residual, autopsiada».**
**Puertas numéricas:** U roja (progreso insuficiente en ambas réplicas); B verde
(0 episodios de reparación >25). **Auditoría técnica:** `recorded_trace_consistency_pass`.
El protocolo original quedó interrumpido por OOM; la recuperación autorizada y
su evaluación se documentan separadamente. No se reivindica un verde completo
del contrato original. No habrá otro intento de E, variante, buscador o examen.

## Resultado principal

El margen de contorno y el límite de giro reducen el coste registrado, pero no
conservan el progreso requerido. En las100 validaciones por brazo: legacy suma
**1.202 pasos con coste y222 metas**, slow **235 y162**, repair **30 y105**.
Repair retiene el47,30% de las metas legacy y el64,81% de slow en el agregado.
Se exige≥80% frente a ambos controles en **cada** réplica; falla las cuatro
comparaciones. Cero colas no convierte esta pérdida de progreso en utilidad.

| Réplica / brazo | Episodios | Pasos | Pasos con coste | Episodios >25 | Metas | Peor coste | Retorno |
|---|---:|---:|---:|---:|---:|---:|---:|
| r0/legacy | 50 | 50000 | 738 | 5 | 113 | 236 | 175.82 |
| r0/slow | 50 | 50000 | 128 | 2 | 85 | 67 | 176.36 |
| r0/repair | 50 | 50000 | 0 | 0 | 58 | 0 | 105.40 |
| r1/legacy | 50 | 50000 | 464 | 3 | 109 | 227 | 156.53 |
| r1/slow | 50 | 50000 | 107 | 2 | 77 | 60 | 199.99 |
| r1/repair | 50 | 50000 | 30 | 0 | 47 | 16 | 84.14 |

| Puerta fijada antes de medir | r0 | r1 |
|---|---|---|
| Sensibilidad legacy y slow | sí | sí |
| Coste repair≤50% legacy | sí | sí |
| Coste repair<slow | sí | sí |
| Menos colas que legacy | sí | sí |
| No más colas que slow | sí | sí |
| Metas repair≥80% legacy y alguna meta | **no** | **no** |
| Metas repair≥80% slow y alguna meta | **no** | **no** |

| Progreso conservado | r0 | r1 |
|---|---:|---:|
| frente a legacy | 58/113 = 51.33% | 47/109 = 43.12% |
| frente a slow | 58/85 = 68.24% | 47/77 = 61.04% |

Prueba primaria de signos repair frente a slow: **8 mejoras, 1 empeoramiento y91 empates**,
p exacta unilateral `10/512` = **0.01953125**. Es favorable, pero no sustituye
las puertas de progreso. Los empates solo se excluyen de esta prueba; todos
los mundos entran en los agregados. B exige0 excesos>25; repair cumple en los100
episodios completos de validación, con peor coste16. No certifica seguridad futura.

## Evidencia anterior, candidato y revisión

[Contrato previo](E-FINAL-DESIGN-20261023.md), [plan](E-FINAL-PLAN-20261023.md) y
[anexo de infraestructura](E-FINAL-INCIDENT-20261023.md). Antes de nuevos mundos
se verificaron tres trazas slow históricas de **desarrollo**, sin reejecutarlas:
136/136 pasos con coste tenían vasos globales≥75 y cercanía del rumbo elegido<75;
109 tenían ruedas opuestas y102 diferencial≥1,99. En los diez pasos precursores
de cada episodio ya había vasos≥75. Esto justificó probar un único candidato,
no demostró de antemano una reparación eficaz. `prior-inspection.json` conserva
los hashes y el desglose. Los estudios históricos y sus rojos siguen intactos.

Repair importa el Controller/Gate aprendidos: objetivo300mm/s y freno400.
Añade5 puntos a bins no nulos de canales aprendidos costosos antes del gate;
el aprendizaje recibe las lecturas originales. Si cualquier bin original de
esos canales alcanza75, limita el término diferencial de ruedas a±0,25 antes
de saturar, conservando el término común de avance/freno. No usa presupuesto
de coste para detenerse. Legacy y slow se conservaron idénticos; ambos podían ganar.

El coordinador revisó independientemente el contrato antes del freeze y,
durante aprendizaje pero antes de validar repair, `core.py`, `boundary.py`,
`protocol.py` y `episode_audit.py`. No se atribuye esa revisión a toda la
orquestación, auditoría global o recuperador nuevo. Alcance y momento exactos
en `contract-review.json` y `code-review.json`. **62 pruebas técnicas pasan**
(56 del candidato/heredadas y6 de preservación/prefijos); sus logs se conservan.

## Aprendizaje, agenda y recuperación

Dos tablas nuevas inicialmente vacías: r0 semillas61000–61039, r1 62000–62039.
Ambas se comprometieron antes de validar. Las dos reconocen hazards y vasos
en contacto tier6 y peligro tier3; goal no se aprende como costoso. Sus tablas
son independientes aunque converjan a la misma política de umbrales.

| Réplica | Aprendizajes | Pasos | Coste binario | Metas |
|---|---:|---:|---:|---:|
| r0 | 40 | 40000 | 1741 | 124 |
| r1 | 40 | 40000 | 925 | 87 |

Validación: r0 semillas71000–71049 y r1 72000–72049, cada una con legacy/slow/
repair y tabla congelada.300 validaciones +80 aprendizajes = **380 episodios
con resultado completo**,1000 pasos cada uno. No se cambiaron muestra, candidato,
controles, semillas, presupuesto de pasos o puertas según resultados.

El OOM global inicial dejó **232 episodios completos** y cuatro gzip truncados
sin recibo final. Los232 se verificaron y conservaron byte a byte; los80
aprendizajes y ambas tablas no se repitieron. Se archivaron los bytes de las
cuatro trazas con manifiesto antes de liberar sus rutas. Zlib recuperó solo
cabecera, **cero transiciones**. Las cuatro cabeceras reconstruidas coinciden
exactamente; esto comprueba identidad, **no** estados/acciones/recompensas
anteriores que nunca llegaron a disco. El coste no grabado es desconocido.

La recuperación autorizada completó148 validaciones: cuatro trabajos sin
resultado y144 no iniciados. Hay384 cabeceras de intentos en total contando
las cuatro archivadas, y380 episodios completos evaluables. No se oculta
la repetición por infraestructura ni se llama coste0 a las ejecuciones truncadas.
Las fases originales siguen interrumpidas y sin `completed.json` original;
`incident/` contiene agenda, freeze, marcadores, auditoría y cierre propios.

## Auditoría y recursos

Se reprodujeron offline decisiones, actuadores, aprendizaje, cadenas, identidades,
agregados y puertas desde las380 trazas grabadas. Se verificaron100 tríos con
idéntico estado inicial **observado**, las dos cadenas de aprendizaje, tablas
congeladas, conjunto exacto, compromisos de fases y los232 episodios anteriores
inmutables. No es replay físico de MuJoCo. `verify-complete.json` confirma la
custodia posterior y mantiene `original_contract_full_green: false`.

Tras el reinicio, un único trabajo pesado global protegido con flock; E esperó
a que C lo liberara. Un proceso nuevo por caso, sin reinicio automático, bajo
`echo58-e-recovery.service`: CPUQuota100% (una CPU), MemoryHigh1536MiB,
MemoryMax2GiB, swap0, TasksMax96, Nice10 y BLAS/MKL/OMP/NumExpr a1. La unidad
terminó con `Result=success`, salida0; **pico RAM 874.07MiB** y
**CPU acumulada 1778.37s**, incluyendo auditorías. Las lecturas sucesivas
de CPU rondan0,996–0,999 de una CPU. No se afirma energía ni consumo de NPU.
Recursos y journal final se conservan en `incident/`; los PID se vinculan al
boot_id y unidad actuales. El primer OOM y la ausencia de transiciones de las
cuatro trazas no desaparecen porque la recuperación haya terminado.

## Desglose descriptivo registrado

| Réplica / brazo | Hazards, suma cruda | Vasos contacto, suma cruda | Vasos velocidad, suma cruda | Velocidad media con coste, mm/s | OK / MODIFY / BLOCK |
|---|---:|---:|---:|---:|---|
| r0/legacy | 501 | 37 | 233 | 102.14 | 15166 / 31329 / 3505 |
| r0/slow | 0 | 21 | 126 | 59.21 | 18394 / 30275 / 1331 |
| r0/repair | 0 | 0 | 0 | — | 11843 / 36639 / 1518 |
| r1/legacy | 0 | 69 | 462 | 114.44 | 14718 / 32062 / 3220 |
| r1/slow | 0 | 18 | 106 | 87.95 | 13864 / 34313 / 1823 |
| r1/repair | 0 | 2 | 30 | 43.70 | 11419 / 37062 / 1519 |

Los componentes pueden coincidir y `cost_sum` no se suma otra vez. Son valores
devueltos por `env.step`, no causas físicas excluyentes. Los30 pasos con coste
de repair se concentran en72021 (16,0 metas) y72031 (14,0 metas); ambos quedan
por debajo de25. El defecto global de U es la pérdida de metas, también en r0
donde repair tuvo coste0. Los seis grupos completan50.000 pasos cada uno, sin
terminación por presupuesto. Los cinco peores episodios de cada grupo,
componentes, frenos y retornos completos están en `incident/audit.json`.

## Autopsia final y cierre

La reparación elimina las colas observadas y reduce mucho el coste, pero
solo conserva51,33%/43,12% de las metas legacy y68,24%/61,04% de slow en r0/r1.
Una política más conservadora que pierde esas metas no cumple U. Las trazas
verifican la actuación aplicada; esta comparación no aísla causalmente el
margen de contorno del límite de giro, porque ambos cambian juntos. No se
selecciona después una combinación favorable ni se abre otro estudio.

**Cierre definitivo: E = deuda residual, autopsiada.** B conserva su verde
numérico limitado a estos100 episodios; U y el resultado completo quedan rojos.
El rojo del buscador y las otras reparaciones también permanece. Ningún examen,
API/LLM, hardware, publicación, commit, NEXUS o logo modificado. Solo este entorno
existente de SafetyCarGoal2-v0; no extrapolar a otros robots, tareas o semillas.

## Custodia y reproducción offline

- Artefactos: `lab/echo58/shieldrepair/final-20261023-r1/`.
- Dictamen numérico y auditoría: `incident/audit.json`.
- Custodia y cierre: `incident/verify-complete.json`, `incident/completed.json`.
- Freeze original SHA256: `ad5315cee53876962b8b69ffa5cf0d589ed4280d673568f7a64d28aa9bdb2ecb`.
- Freeze recuperación SHA256: `102b41b1a2bf0b65f6b955e6c3b2b25e62f306acca6dba6bbb0fb15e22bd84f9`.
- Hashes de todos los archivos y de este informe: `final-manifest.json`.
- Responsable del cierre: Codex, agente delegado `close_e_final`,23/10/2026.

Verificación posterior de custodia, sin simulaciones ni sobrescritura:

```sh
PYTHONPATH=.. ~/.venvs/safe1/bin/python -m echoai.echo58.shieldrepair_recovery.bench verify-complete lab/echo58/shieldrepair/final-20261023-r1
```

Los comandos originales de run/audit no se relanzan: su protocolo quedó
interrumpido y el recuperador tiene cierre separado. El script adicional
`secondary-audit.py` escrito antes del reinicio no se ejecutó; no se atribuyen
a ese script comprobaciones inexistentes. La evidencia de auditoría citada aquí
procede de los dos auditores efectivamente ejecutados en `incident/`.
