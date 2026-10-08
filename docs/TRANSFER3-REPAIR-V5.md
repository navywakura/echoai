# TRANSFER-3 — reparaciones y diagnóstico público v5

2026-09-18. No es una campaña ni un candidato promovido. V1–v4 y sus
inventarios se conservan. Se corrige la redacción del informe v3, que no
pertenece a su inventario congelado. No se genera ni abre B/C real.

## Contrato previo al diagnóstico

Se reutilizan exclusivamente las trazas y salas públicas de v3/v4, los tres
brazos completos y sus políticas congeladas. Para cada decisión ejecutada:

1. Reproducir exactamente la decisión registrada con la historia original.
2. Desde una copia del mismo estado anterior, poner la consulta Q a cero.
3. Desde otras cuatro copias, favorecer cada acción horizontal con +127 y
   las restantes con −127. No cambiar búsqueda, visitas, observación ni gate.
4. Medir acciones distintas accesibles a través de Q, decisiones cambiadas
   frente a cero y pares elegidos sin muestra escolar. No ejecutar esos
   contrafactuales ni alimentar sus resultados al agente.
5. Fuera del agente, comparar distancias reales al objetivo y detectar
   features que exigen ordenaciones opuestas para el mismo par de acciones
   disponibles simultáneamente. Distintas mejores acciones con distintos
   conjuntos candidatos no bastan para declarar ese conflicto.

El oráculo sólo adjudica. Sus preferencias no son una política aprendida ni
garantizan retorno, seguridad o mejor misión completa. Las cuatro filas
extremas son suficientes para favorecer cada primer movimiento entre los
empates de score/profundidad de este controlador; no son una búsqueda de
hiperparámetros. No se estima significación de estas observaciones correlacionadas.

## Reparaciones nuevas, sin reescribir fuentes congeladas

`repair_v5.py` reutiliza el controlador y Q originales:

- Asignación CAM comprobada antes de escrituras Q/T. Con CAM llena, las
  filas existentes pueden aprender; una asignación nueva se rechaza.
- `terminal=True` en llegada y desenlace de fallo, sin bootstrap. Una
  transición física produce una sola actualización. Fallo inicial sin
  movimiento no fabrica un predecesor.
- Corte de presupuesto de entrenamiento distinto de fin de misión:
  truncamiento mantiene bootstrap; el límite de misión del controlador sí
  es terminal. Se conserva la prioridad de llegada en el último movimiento.
- Un único `scan` por timestamp; se reutiliza la captura para la decisión
  siguiente. La guarda de capturas conflictivas permanece activa.
- Reserva adjudicada con transición real, mediante la misma función en
  escuela y diagnóstico sin aprendizaje; no depende de `predict`.

Recompensas explícitas: progreso = `8*(L1_before-L1_after)-1+32*arrival`;
paso/llegada = `-1+32*arrival`. **Bonus de fallo nuevo: −32**, separado de
esas fórmulas. Es un parámetro experimental no optimizado, probado en una
sala pública cerrada; no se afirma que mejore la transferencia. Las escuelas
históricas de 12 éxitos no se convierten retrospectivamente en escuelas con fallos.
El resultado v5 local no sustituye al consumidor aislado del examen.

`custody_v2.py` reutiliza el pestillo SIM-3, con bloqueo también al crearlo:
sellar → abrir bajo lock → llamar al loader → comprobar compromiso publicado,
hash de inventario y vínculo del aviso completo → entregar inventario.
Error o excepción consume el intento. **Campañas reales rechazadas**, incluso
con cadenas de custodio convincentes. Una API en el mismo usuario del SO no
impide leer secretos disponibles a ese usuario: la custodia externa sigue pendiente.

## Alcance corregido de v3/v4

- Sólo escuelas estáticas en los informes históricos. V5 prueba captura
  dinámica, pero no demuestra transferencia dinámica ni vuelo físico.
- Meta en coordenadas globales conocida desde el inicio, igual entre brazos;
  no se estudia descubrimiento de meta ni se oculta toda información geométrica.
- Formas disjuntas dentro de una única topología de pared con hueco:
  450 configuraciones, 126 formas canónicas; 84 públicas usadas, 42 restantes.
- Esquema de features: 1728 códigos; cota planar utilizable 144
  (9 signos XY × 16 máscaras horizontales, z igual y bits verticales puestos).
- Q entra como tercer desempate. Es un canal limitado, no influencia nula.
  La identidad Q v2/corrected y del consumidor explica sus exámenes idénticos.
- El metadato `rooms.reward` de v3 describe sólo recompensa de progreso;
  reward_only usa paso/llegada. Se preserva el JSON histórico y se denuncia
  esa inconsistencia; el protocolo nuevo distingue ambas fórmulas.
- Un abandono histórico sí aprende el paso anterior, pero no su terminalidad
  ni penalización de desenlace. La afirmación contraria de la revisión se matiza.
- Restauración válida histórica usa CAM fresca y menos de 4096 entradas:
  el caso −1 es un fallo defensivo, no corrupción demostrada de esos resultados.

## Reproducción

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_v5 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.diagnostic_v5 run lab/transfer3/diagnostic-v5.json
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.diagnostic_v5 audit lab/transfer3/diagnostic-v5.json
```

`run` rechaza sobrescribir. `audit` repite y compara todos los resultados.
Ambos comprueban cada ruta de los inventarios históricos guardados. No
vuelven a ejecutar campañas ni seleccionan salas nuevas.

## Disposición de los 16 hallazgos de la revisión

| Hallazgo | Tratamiento |
|---|---|
| 1. Control omitido | Corregido en el informe v3: 3/3/10 y scratch=25 en 20264511. |
| 2. Tercer desempate | Se mantiene el controlador; se mide su sensibilidad, no se presume nula. |
| 3. Terminalidad | Corregida en la escuela v5; prueba con Q del sucesor no nula. |
| 4. Escuela sin fallos | Fallo y penalización explícitos probados en fixture cerrado; aún no nueva escuela representativa ni candidato. |
| 5. Captura dinámica | Reutilizar frame; prueba que rechaza cualquier segundo scan en el mismo paso. |
| 6–7. Orden y vínculo de custodia | API nueva bajo pestillo con callback y doble verificación; sólo fixture público. |
| 8. CAM llena | Rechazo previo a Q/T; pruebas con CAM realmente llena y restauración fallida. |
| 9. Reserva | Juez común independiente de predict en escuela y diagnóstico local v5. |
| 10. Selección supuestamente intacta | Corregida la afirmación estructural; identidad empírica conservada. |
| 11. Geometría | Topología y cardinalidad declaradas; ampliar generador queda pendiente. |
| 12. Meta conocida | Declarada explícitamente; no se cambia la tarea a descubrimiento de meta. |
| 13. Custodio de relleno | Campañas rechazadas por la API nueva; aún falta integración externa real. |
| 14. Fórmula del protocolo | Dos fórmulas explícitas nuevas; inconsistencia histórica documentada sin retocar JSON. |
| 15. Features | 1728 es capacidad de esquema, 144 cota planar; cobertura efectiva medida aparte. |
| 16. n=16 | V4 ya usa 64 pares y prueba exacta; repetir semillas deterministas no aporta muestras independientes. |

No se reetiquetan los rojos como verdes ni se parchean resultados históricos.

## Resultados del diagnóstico

Artefacto: `lab/transfer3/diagnostic-v5.json`, hash canónico
`bc8d31432dbfac59767a0fd321b88a11fa614acd9b7ebf756053d713a9e71f60`.
Auditoría completa en un proceso nuevo: mismo hash y contenido, exit 0.
Inventarios históricos comprobados también por separado: v1 322 rutas,
v2 324, v3 328 y v4 330; cero rutas con hash cambiado en los cuatro.
Reproduce exactamente las decisiones históricas antes de intervenir. Las
intervenciones son locales sobre esa historia, **no trayectorias alternativas**.

| Trazas | Decisiones ejecutadas | Sensibles a Q extrema | Cambian con Q aprendida vs cero | Mejor/peor/igual distancia local al cambiar | Pares feature–acciones con orden opuesto |
|---|---:|---:|---:|---|---:|
| v3 corrected | 260 | 67 | 31 | 7 / 6 / 18 | 3 |
| v3 reward_only | 245 | 62 | 17 | 3 / 7 / 7 | 1 |
| v3 coverage_only | 248 | 63 | 38 | 8 / 8 / 22 | 1 |
| v4 corrected | 1130 | 372 | 93 | 26 / 17 / 50 | 14 |
| v4 reward_only | 1048 | 324 | 51 | 13 / 26 / 12 | 13 |
| v4 coverage_only | 1152 | 378 | 163 | 33 / 31 / 99 | 15 |

No existe sensibilidad cero: incluso el desempate restringido altera acciones.
Tampoco se debe convertir «mejor distancia local» en «mejor misión»: no mide
retorno a casa, coste de aprendizaje ni resultado contrafactual completo.
Las historias difieren entre brazos, así que sus contadores no son pares
independientes ni una estimación causal entre recompensas.

Cobertura en los estados donde Q **sí** puede influir, a igual presupuesto v4:

| Brazo | Decisiones sensibles con todas las acciones ofrecidas muestreadas | Elegida sin muestra, entre sensibles | Cambios frente a cero que eligen acción sin muestra |
|---|---:|---:|---:|
| corrected | 59 / 372 | 244 / 372 | 22 / 93 |
| reward_only | 101 / 324 | 203 / 324 | 35 / 51 |
| coverage_only | 130 / 378 | 160 / 378 | 28 / 163 |

Estos son conteos de decisiones, no de pares distintos; una feature repetida
puede aportar muchas filas. El último grupo separa valor aprendido de
optimismo por cero: la acción seleccionada nunca se entrenó en esa feature,
aunque otras acciones sí pudieron aprender valores negativos.

Los conflictos de orden son sobre un mismo par ofrecido en distintos estados
con la misma feature; el JSON guarda cada estado y distancias. Demuestran
ambigüedad respecto a ese criterio local, no imposibilidad de toda política
útil: puede haber terceras acciones y el criterio de misión es más amplio.

## Verificación de las reparaciones

28 tests v5 pasan. Regresión dirigida final: **138 tests, todos pasan**.
Una ejecución más amplia anterior terminó con **605 tests, OK, un fallo
esperado preexistente**; después se añadieron los dos tests del diagnóstico
(copia optimizada vs completa y conflicto de pares), incluidos en los 28/138.

Fixtures con semilla pública 20264401, recompensa paso/llegada:

| Fixture | Desenlace | Movimientos/capturas | Última recompensa | Terminal |
|---|---|---|---:|---|
| Estático | reached | 6 / 7 | 31 | sí |
| Cerrado | abandoned_at_home | 50 / 51 | −33 | sí |
| Dinámico | reached | 6 / 7 | 31 | sí |

Adicionalmente, sala cerrada con energía inicial 1000: `budget_exhausted`
tras 64 movimientos, última recompensa −33 y terminalidad verdadera.
No confundir ese límite de misión con el corte de presupuesto de escuela.

Cero colisiones y violaciones de reserva en estos tres fixtures. No son
un nuevo benchmark de generalización. Se prueba aparte corte tras un paso
sin terminalidad, fallo inicial sin actualización, sucesor con Q=100 sin
bootstrap terminal, CAM realmente llena, crash/concurrencia y rechazo de
aviso, inventario, sal o split incorrectos antes de entregar datos.

## Decisión siguiente

No aumentar el peso de Q ni abrir B/C. El siguiente experimento, aún no
ejecutado, debe distinguir cobertura de aliasing de representación con datos
de entrenamiento públicos que incluyan fallos, manteniendo el mismo presupuesto
y el planificador fijo. Primero contrastar preferencias de un mismo par en
contextos distintos; sólo después proponer un feature observable que los
distinga, sin introducir geometría oracle. Más episodios con los mismos
features no resuelven por sí solos un conflicto de representación.

Custodia externa, generador final, protocolo final y ventaja amortizada siguen
pendientes. No hace falta ningún secreto ni intervención de Roger en esta fase.
