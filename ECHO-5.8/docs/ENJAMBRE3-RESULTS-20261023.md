# C v3 · ENJAMBRE-3 · resultados, 23/10/2026

**ROJO científico: no cumple todas las puertas fijadas.** Auditoría técnica y recuperación VERDES.

Estudio nuevo y separado: tres candidatos de desarrollo, selección automática única y validación nueva congelada. C v2 desfavorable y todos los exámenes anteriores permanecen intactos. Sin LLM, API, publicaciones, GitHub/Hugging Face ni instalaciones. No se presenta como examen antiguo ni como defensa general ante emisores arbitrarios.

La versión reduce daño frente a C2 prudente en los tres ataques, pero resuelve 75/80 mundos en cada uno. La pérdida se concentra en m10: 3/8 resueltos y 168 puntos en cada ataque, frente a 8/8 y 53 puntos sin memoria global. La falsa alarma mantiene más daño que ingenuo (64 frente a 57). Ninguno de los tres contrastes pasa Holm. No se cambia una puerta para conceder verde.

## Contrato y selección

Contrato anterior a medidas: [diseño](ENJAMBRE3-DESIGN-20261023.md) y [plan](ENJAMBRE3-PLAN-20261023.md). Se conserva provisionalmente HURT unilateral para buscar otra vía; solo la pasada verify de agotamiento permite contrastarlo. Evidencia local/privada/notas y avisos de dos autores mantienen precedencia/veto.

Desarrollo: 63 trabajos, tres macros nuevas × tres ataques × siete brazos. Selección fija por violaciones, daño, puntuación y n mínimo. Menos daño y puntuación son mejores; un mundo sin resolver vale 31.

| Candidato | n mínimo | Puertas incumplidas en dev | Daño total | Puntuación total |
|---|---:|---:|---:|---:|
| v3_n1 | 1 | 1 | 54 | 333 |
| v3_n2 | 2 | 2 | 69 | 390 |
| v3_n3 | 3 | 4 | 74 | 426 |

Seleccionado: **v3_n1**. En desarrollo la falsa alarma ya incumplía daño≤ingenuo: 18 frente a 16, aunque resolvía 24/24 frente a 15/24. Esa puerta no se cambió. La validación permaneció sin resultados hasta guardar la selección y su hash.

## Validación nueva y controles

Diez macros nuevas × tres ataques × siete brazos = **210 trabajos**. Cada celda de resueltos tiene máximo 80 mundos. Cuatro agentes, ocho mundos por macro, 30 rondas y 300 pasos por episodio/agente; mismos mundos, turnos y ayuda para todos los brazos. Controles C2 exactos; instrumentación de acciones común.

| Ataque | Brazo | Puntuación ↓ | Daño ↓ | Resueltos /80 | Daño de sonda física ↓ |
|---|---|---:|---:|---:|---:|
| false_safe | v3_n1 | 465 | 72 | 75 | 35 |
| false_safe | prudente | 485 | 104 | 80 | 64 |
| false_safe | ingenuo | 392 | 76 | 80 | 29 |
| false_safe | por_autor | 424 | 90 | 80 | 36 |
| false_safe | sin_global | 462 | 101 | 80 | 99 |
| false_alarm | v3_n1 | 452 | 64 | 75 | 37 |
| false_alarm | prudente | 484 | 104 | 80 | 75 |
| false_alarm | ingenuo | 1342 | 57 | 45 | 34 |
| false_alarm | por_autor | 741 | 72 | 73 | 51 |
| false_alarm | sin_global | 462 | 101 | 80 | 99 |
| false_remote | v3_n1 | 445 | 50 | 75 | 28 |
| false_remote | prudente | 553 | 103 | 76 | 70 |
| false_remote | ingenuo | 355 | 59 | 80 | 37 |
| false_remote | por_autor | 407 | 81 | 80 | 45 |
| false_remote | sin_global | 462 | 101 | 80 | 99 |

Una sonda física para la puerta es una acción con prior desconocido **o** ejecutada bajo aviso provisional liberable. Se conserva aparte harm_probe legacy: cambiar un prior a HURT no hace desaparecer su daño. Las consultas/liberaciones no son decisiones independientes ni sustituyen al daño real.

| Ataque | Consultas expuestas | Respuestas afectadas | Acciones bajo aviso provisional | Daño al contrastar aviso | Sondas físicas | Daño de sonda legacy |
|---|---:|---:|---:|---:|---:|---:|
| false_safe | 164616 | 1137 | 166 | 6 | 732 | 29 |
| false_alarm | 6089 | 97 | 164 | 4 | 751 | 33 |
| false_remote | 5946 | 0 | 181 | 6 | 697 | 22 |

## Ablaciones del mecanismo

Ambas usan el n mínimo seleccionado. No fueron candidatos alternativos tras ver validación. sin_alarma devuelve desconocido ante aviso provisional; sin_liberacion mantiene el aviso sin contrastarlo en la pasada verify.

| Falsa alarma | Puntuación ↓ | Daño ↓ | Resueltos /80 | Daño de sonda física ↓ |
|---|---:|---:|---:|---:|
| v3_n1 | 452 | 64 | 75 | 37 |
| sin_alarma_n1 | 503 | 76 | 75 | 47 |
| sin_liberacion_n1 | 744 | 52 | 64 | 28 |

Se exige mejora de daño de sonda frente a sin_alarma, conservar sus resueltos y mejorar progreso frente a sin_liberacion. Si no se discrimina el mecanismo, no se atribuye causalidad ni se concede verde. Las tres puertas de ablación pasan en esta validación: el canal provisional reduce daño de sonda 47→37 y la liberación conserva 75 resueltos frente a 64 sin liberación. El daño total de no liberar es menor (52 frente a 64); ese compromiso permanece visible. Estas comparaciones no eliminan la pérdida de progreso frente a controles ni la puerta de daño frente a ingenuo.

## Puertas y contrastes fijados

| Contraste por macro, agregando ataques | p unilateral exacto | Pasa Holm |
|---|---:|---|
| harm_ingenuo | 0.21875 | no |
| score_por_autor | 0.052734375 | no |
| score_sin_global | 0.0419921875 | no |

Wilcoxon unilateral exacto de signos sobre rangos medios, ceros excluidos; Holm α=0,05 para los tres contrastes. Las diferencias por macro, todas las puertas booleanas y el desglose por tipo/macro están en result.json. No se usan estas pruebas para anular una puerta física o de progreso.

**Puertas incumplidas:**

- `false_safe:solved_geq_ingenuo`
- `false_safe:solved_geq_prudente`
- `false_alarm:harm_leq_ingenuo`
- `false_alarm:solved_geq_prudente`
- `false_remote:solved_geq_ingenuo`
- `false_remote:solved_geq_prudente`
- `holm:score_sin_global`
- `holm:score_por_autor`
- `holm:harm_ingenuo`

## Incidente y recuperación: no fue una corrida ininterrumpida

El PC se reinició; el coordinador comunicó OOM de RAM del kernel. [Enmienda instrumental](ENJAMBRE3-INCIDENT-20261023.md), anterior a reanudar: **158 recibos completos conservados sin repetir**, 52 trabajos pendientes, incluidos dos parciales. Se archivaron originales y hashes de los parciales prudente-false_remote-m8 (15 rondas) y v3_n1-false_safe-m8 (5).

**20/20 rondas de prefijo coinciden byte a byte** con sus nuevas versiones. Los dos trabajos parciales se reiniciaron con sus mismas semillas; esos 20 prefijos se reprodujeron, sin elegir resultados. Lo que se perdió en RAM y no estaba publicado no se inventa. Los otros trabajos ya completos no se repitieron. Se informa una **validación recuperada determinista**, condicionada a integridad y prefijos exactos, con el incidente visible.

Recuperador separado del código congelado, un proceso fresco por trabajo y un único worker. systemd user, CPUQuota=100%, MemoryMax=2G, MemoryHigh=1536M, MemorySwapMax=0, TasksMax=96, Nice=10, OOMPolicy=stop; threads OMP/OpenBLAS/MKL/NumExpr=1 y flock global. Tras el incidente, auditoría serial bajo iguales límites; ningún auditor pesado vuelve a ejecutarse fuera del cgroup. CPython 3.14.6 coincide con el preflight. Recursos y controles están guardados en recovery/. La auditoría final terminó con status 0, 318,48972 s de CPU y MemoryPeak retenido de 1.611.628.544 bytes. El pico observado de recuperación fue 1.611.558.912 bytes; su total final se perdió por GC de la unidad y no se inventa.

## Reparación instrumental del informe

La primera auditoría offline completó la reconstrucción pero el compositor de estadística falló con KeyError: aggregate guarda m1…m10 y report.result buscaba 1…10. No se publicó resultado ni falso verde. Se conservan fuentes y traceback originales. [Reparación declarada](ENJAMBRE3-REPORT-FIX-20261023.md): adaptador nuevo separado con única corrección de clave f'm{m}', y argumentos opcionales para recibir auditoría/preflight ya verificados. Las funciones originales de gates, aggregate, Wilcoxon y Holm permanecen intactas.

Un test de regresión sintético cubre las diez macros, los tres vectores pareados y sus p-valores; pasa. El coordinador revisó el diff y aprobó la corrección. Se volvió a ejecutar únicamente la auditoría offline bajo iguales límites; audit.json quedó guardado ANTES de componer el informe. No hubo nuevos mundos, candidato, métricas o umbrales. El programa de informe congelado conserva su defecto como antecedente; este dictamen usa recovery/report_adapter.py explícitamente.

## Auditoría y límites

La auditoría offline reconstruye observaciones privadas, postales originales/enviadas, ataques, confianza, consultas, notas, resoluciones y métricas, además de hashes y diarios exclusivos. Las acciones se alinean con sus consecuencias. El auditor de recuperación vuelve a verificar los 158 recibos previos, los 20 prefijos y los 52 nuevos en orden. No vuelve a ejecutar física. Auditoría técnica verde no sustituye a las puertas científicas.

Los campos prior/provisional se registran por el código de política congelado; se recuentan y contrastan acciones/consecuencias, pero no se reconstruyen de forma independiente todos los estados internos/bans de la política. El campo step es el contador de decisiones de PAgent, que excluye su primer turno de observación. No se usa como medida de tiempo físico.

Pruebas: 16 C3 + 18 C2 = 34 verdes con Python de sistema. La suite ampliada original dio 44/45 y un error por falta de gymnasium en sistema. El coordinador ejecutó independientemente las 45/45 en el entorno MiniGrid existente ECHO-5/.venv-sandbox/bin/python: 73,389 s, cero errores, sin instalar ni cambiar fuentes. Dos pruebas adicionales del recuperador y una regresión del adaptador de informe pasan sin mundos. La suite original no había cubierto el acoplamiento de nombres de macro que causó el fallo de informe, ahora declarado y comprobado.

Alcance: reglas programadas de lectura/acción y confianza en cuatro autores autenticados; no colusión, suplantación ni sabotaje físico. Misma familia sintética de C1/C2. Una excepción local puede desacreditar una generalización honesta; RM no entrena confianza. No se demuestra invención autónoma de la defensa ni seguridad universal. No se añade candidato, semilla, intento o puerta tras estos resultados.

## Custodia y reproducción offline

- Dev preflight: `e40e394e8a4a163b9aaefbbaa2fc31ac556c2bed2d11d0f0b3800b34fad17915`.
- Dev completed: `b3db9faebeb6a879c92d2d53bac27ef53ff79b3bdcaa0bf4a7c6e01b8089ff8e`.
- Selección: `1b4ac42bc8e74f0c37d2f7f4cb093a5f5b1376b4ca2d01c57347ac66e44f2dd9`.
- Validación preflight: `00c8bdd232f7eadec9c051e45c5efbfc42fab44f40560d08b5ea2cfccc1b4987`.
- Validación completed: `dc74c666dc5a823f7e423be12c969adb60bca24923997d888ef9b5c895e96693`.
- Inventario del incidente: `e7dd6a342ca0dc8b4bb6bc39fc5292425d08289a4f61c93af444c1a6b53f0920`.
- Enmienda: `9437fc44cff3a81b012d9b6888ed5938de6a024d5c01e853f610a618356a4991`.
- Recuperador: `23c680c7ac3b725b5dc8ff9e3e5c1f6930722d23d53026e042702a6cdf9addf0`.
- Auditor de recuperación: `f9c3ac81b5823c02ec1ff94aa48124654aa4104d988732d9e9306312d912f4f2`.
- Adaptador de informe: `7fad955fb49ab356d9ed42d3e75f8689e82fb48328960d123d6b1b0974199033`.
- Plan de reparación de informe: `e771d56026086f09f4d95421955c378d70d2e45a34e49ba555f88618d4211a6b`.

Artefactos: `lab/echo58/enjambre3/dev-20261023-r1/` (development/, validation/, recovery/). Fuentes/contrato congelados antes de medidas: 35 entradas dev, 36 validación incluida selección. Los 273 recibos canónicos del estudio se conservan; se declaran aparte las dos interrupciones/prefijos reproducidos.

La auditoría offline requiere un turno pesado exclusivo con los límites anteriores, incluso aunque no ejecute mundos. Para reproducirla de lectura sin sobrescribir artefactos:

```python
from echoai.echo58.enjambre3.verify import verify
report = verify('lab/echo58/enjambre3/dev-20261023-r1/validation')
print(report['audit_green'], report['jobs'])
```

El programa recovery/audit_recovery.py original publica recibos exclusivos y no debe relanzarse sobre estas raíces. Sus comprobaciones de lectura están en el código archivado; los pares de prefijos se conservan bajo validation/incident/oom-20261023/partial-rounds/ y validation/rounds/. No volver a jugar mundos ni ejecutar bench run sobre estas raíces.
