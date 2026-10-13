# ECHO-5.1 · co-learning A → B, desarrollo 0.9

**La persistencia y reutilización funcionan en este piloto.** Los tres receptores
con la receta de A resolvieron Registros01 con su primera propuesta y sin reparar.
El control con memoria vacía resolvió 1/3, tras reparar. Esto no cierra H2 ni T20
en general: solo se ensaya una familia conocida, y dos controles fallaron por
copiar un texto de formato. El código heredado se reprodujo literalmente.

Plan previo: [COLEARNING-PLAN-20261013.md](COLEARNING-PLAN-20261013.md).
Implementación congelada: `9ef31b0`, rama local `research/echo-5.1-pcworld1`.
Sin push, publicación ni cambio de las campañas anteriores.

## Implementación comprobada

- `pcworld/shared.py`: `SharedConceptLibrary` persistente sobre recibos autenticados.
  Guarda código real del snapshot reparado, AST normalizado, contraejemplo observado,
  ámbito público y procedencia: autor atestiguado por el supervisor, tarea, familia,
  snapshot y recibos. La firma corresponde a la custodia del supervisor, no al LLM.
- Solo publica donantes aceptados tras reparación, con auditoría válida, refutación
  no final y reproducción posterior del caso y de los ejemplos públicos. La tarjeta
  no contiene entradas ni salidas de evaluación final. El registro conserva el AST;
  la tarjeta del proponente omite AST y contrato redundantes y está limitada a 6 kB.
- La consulta devuelve como máximo una receta compatible. Exige conservar y auditar
  los artefactos del donante; alterarlos invalida la recuperación. La receta sigue
  siendo candidata y no concede autoridad para aceptar la tarea nueva.
- `pcworld/pilot.py`: consulta cobrada antes de la propuesta inicial, entrega de la
  tarjeta una sola vez y trazabilidad en el `thought.jsonl` existente. La CAM episódica
  sigue siendo nueva en cada episodio; la biblioteca persiste entre ellos.
- `pcworld/transfer.py` y `scripts/run_transfer_pilot.py`: adquisición nueva, biblioteca
  congelada, receptores con y sin memoria y apagado del worker. Auditoría de donante
  exacto, tarjeta, fuentes, orden, modelo, runtime y límites comunes.
- Una sola generación de transferencia. Los receptores no publican nuevas lecciones;
  no se afirma aprendizaje de pesos, abstracción parametrizada ni evolución recursiva.

## Diseño ejecutado

Qwen2.5-Coder-14B-Instruct Q4_K_M, revisión y GGUF fijados, llama.cpp b11577,
contexto 4096, salida máxima 768, temperatura 0,2. 49/49 capas en T4.
Kaggle solo hizo inferencia. Los candidatos y oráculos quedaron en Linux con
Bubblewrap/cgroup y el rootfs Python fijado, sin `/usr` del host.

A: E sobre Registros00, semilla de tareas 47 y del modelo 73. B: Registros01,
semillas del modelo 73, 74 y 75; orden aislado/cooperativo, cooperativo/aislado,
aislado/cooperativo. Mismo protocolo E, catálogo expanded-v2, 25.000 tokens,
50 herramientas y dos reparaciones como máximo. Los límites restantes se conservan.
No se eliminaron llamadas al crítico para producir un ahorro.

Se ejecutaron **7/7 episodios**. Cinco fueron aceptados: A, tres B cooperativos
y un B aislado. No se confundió completar la ejecución con resolver la tarea.
No hubo reintentos de campaña ni selección posterior de semillas.

## Resultado por receptor

| Semilla | Memoria | Pasa evaluación final | Reparaciones | Llamadas LLM | Críticas | Tokens | Herramientas |
|---|---|---:|---:|---:|---:|---:|---:|
| 73 | Vacía | Sí, 5/5 | 1 | 4 | 2 | 4.426 | 39 |
| 73 | Lección de A | Sí, 4/4 | 0 | 3 | 2 | 3.896 | 26 |
| 74 | Vacía | No, 0/4 | 0 | 1 | 0 | 285 | 14 |
| 74 | Lección de A | Sí, 4/4 | 0 | 3 | 2 | 3.844 | 26 |
| 75 | Vacía | No, 0/4 | 0 | 1 | 0 | 285 | 14 |
| 75 | Lección de A | Sí, 4/4 | 0 | 3 | 2 | 3.866 | 26 |

Los cuatro casos comunes son los mismos. El quinto caso del aislado 73 es su
contraejemplo retenido, añadido por el protocolo común de reparación. Las tres
soluciones cooperativas pasaron las dos críticas y la evaluación final sin cambios.
Cero destrucciones de CAM en los siete episodios.

### Qué se transfirió realmente

A propuso inicialmente `list({p['id']: p for p in x}.values())`, que conserva el
último valor de cada clave en lugar del primero. Su crítico encontró una repetición
con valores diferentes. A reparó usando `seen_ids` y pasó 5/5 casos finales.
La biblioteca publicó ese programa y un testigo no final de sobrescritura.

El aislado 73 repitió **el mismo código defectuoso** y necesitó una reparación;
su contraejemplo tiene la misma estructura, con otros valores. Los tres receptores
cooperativos propusieron un programa idéntico, byte a byte, al parche de A.
La observación acredita recuperación y reutilización de una solución válida para
el mismo contrato con nuevos valores; no síntesis de una abstracción nueva.

### Fallo de los controles 74 y 75

Ambos devolvieron literalmente:

```text
complete solution.py reading JSON from stdin and writing one JSON value
```

Ese texto procede del campo ilustrativo `format.content` del proveedor. Ejecutarlo
produce `SyntaxError`. El verificador clasifica la ejecución como `unknown`, nunca
como un contraejemplo de valor ni como éxito. El protocolo actual termina antes del
crítico cuando el ejemplo público no produce una salida verificable; no reintenta
ese error de formato. No hubo timeout ni excepción del proveedor.

Por tanto, las dos victorias adicionales tienen este factor de confusión: recibir
código ejecutable también evita copiar el ejemplo de formato. No basta el 3/3 frente
a 1/3 para atribuir toda la diferencia al contenido causal del contraejemplo o a CAM.
No se modificó el prompt ni se descartaron episodios después de observarlo.

## Coste completo

| Magnitud, solo receptores B | Vacía | Compartida |
|---|---:|---:|
| Aceptados | 1/3 | 3/3 |
| Aceptados sin reparación | 0/3 | 3/3 |
| Tokens | 4.996 | 11.606 |
| Llamadas LLM | 6 | 9 |
| Críticas | 2 | 6 |
| Herramientas, incluida consulta | 67 | 78 |
| Tiempo de episodios | 51,134 s | 111,953 s |
| CPU host de episodios | 2,866 s | 3,494 s |

**No hay ahorro agregado de tokens:** los dos fallos tempranos del control son baratos.
En la pareja 73, donde ambos resuelven, compartir ahorra 530 tokens (**11,97%**),
una llamada LLM y 13 herramientas (**33,33%**). Es una comparación descriptiva
individual, no el efecto promedio confirmado del sistema.

Adquisición A: 4.419 tokens, 4 llamadas LLM, 2 críticas, 38 herramientas, una reparación,
81,965 s de episodio. Se ejecutó una vez como prefijo común y se atribuye a ambos
recorridos comparados, no se supone entrenamiento gratuito.

Publicar costó una operación supervisora adicional: 225,926 ms de pared y 221,266 ms
CPU. Cada consulta cooperativa, incluida reauditoría del donante, costó aproximadamente
203–205 ms y una herramienta; las vacías aproximadamente 0,58 ms y una herramienta.
La CPU de consulta también se cargó al presupuesto del episodio. No es una consulta
total O(1). Las auditorías finales son trabajo de evaluación separado, no tokens del agente.

Con el prefijo A una vez más los tres B: aislado 9.415 tokens y 105 herramientas;
cooperativo 16.025 tokens y 117 herramientas, incluyendo publicación. Para la pareja
73 sola, A→B usa 8.845 frente a 8.315 tokens: ahorro 5,99% contando adquisición.

Coste físico total de la campaña: **21.021 tokens, 19 llamadas LLM y 184 operaciones
contadas**, incluida publicación. La publicación no consume tokens. No se suma dos
veces el prefijo común a este total físico.

## Validación y recursos

- **240 tests** PCWorld pasan en 88,191 s; nuevas pruebas de persistencia, custodia,
  incompatibilidad, exposición inicial, contabilidad y auditoría de pares.
- Auditoría inicial y repetida en otro proceso: `valid: true`, cero errores.
  347 recibos de episodios; además se comprueba custodia de ejecuciones, estudio y
  bibliotecas. Los diarios de toda esta tanda contienen 373 recibos.
- 30 archivos congelados: sin cambios. Modelo, snapshots y procedencia registrados.
- 57 solicitudes de inferencia/preflight: todas HTTP 200. Sin timeout ni desbordamiento.
  Los dos `SyntaxError` son resultados fallidos del candidato y permanecen contabilizados.
- Worker: 486,791 s (**8 min 07 s**), incluyendo 226,341 s de preparación. GPU 49/49;
  aproximadamente 9.161 MiB en la T4 principal, 105 MiB de contexto en la segunda.
- Cuota GPU: 24,12 → **23,98 horas**, consumo aproximado 0,14 h según el contador.
- Kaggle `COMPLETE`; worker detenido, supervisor/broker/túnel apagados. Sin publicación.

Artefactos locales:
`ECHO-5.1/artifacts/colearning14b-pilot-20261013`,
`ECHO-5.1/artifacts/colearning-control-20261013` y
`ECHO-5.1/artifacts/kaggle-colearning14b-output`.
Las autoridades y paquetes privados contienen credenciales/custodia; no se publican.

SHA-256:
- Resultado: `20e25132ef36520e38612471404e4b8be7a4a4fd44723f3bf60d204def0afdbe`.
- Auditoría: `21a919b51ff7d61bccbc03f458165300d79783115aa8cb46a34d8cd9135b5561`.
- Contrato del estudio: `625accf8e8d2e3b944edaa861ba3b62f6ca1162a54af7a47f4f9b9feaaa883f3`.

## Checklist de ECHO-5.1 tras este ensayo

| Estado | Obligación | Evidencia o siguiente comprobación |
|---|---|---|
| [x] Comprobado localmente | T01–T04: ejecución y frontera de archivos | Bubblewrap/cgroup obligatorio, sin fallback ni acceso a autoridad. Límites históricos de host/kernel siguen vigentes. |
| [x] Comprobado localmente | T05–T07: recibos, observaciones y snapshots | HMAC/ancla, separación proceso/propiedad, identidad de bytes; memoria nueva enlazada a evidencia real. |
| [x] Acotado | T08 y T10: runtime y caché pura | Rootfs fijado sin `/usr` host; ejecuciones siempre frescas. No empaqueta kernel/hardware ni acredita otra máquina. |
| [x] Comprobado | T09 y T11: recuerdo no autoritativo y crítico validado | La receta heredada no veta ni acepta la propuesta; incompatibilidad no se reutiliza. |
| [x] Acotado | T12: contraejemplo y reparación | A y aislado 73 reparan; cooperativos pasan con la receta. No incluye minimización automática del testigo. |
| [x] Comprobado localmente | T13–T14 y T17: recursos, reintentos y aislamiento | Cuotas y preflight conservados; consulta/publicación registradas. Falta recuperación simétrica de propuesta no ejecutable. |
| [x] Acotado | T15–T16 y T19: persistencia, orden y núcleo | Recetas restaurables, auditoría en otro proceso y replay WSP. No scheduler distribuido, aprendizaje de Q ni recuperación a mitad de episodio. |
| [x] Acotado | T18: comparación con condiciones comunes | Tres parejas, mismo E/modelo/cuotas/runtime; solo cambia biblioteca. Una familia de desarrollo, no prueba general. |
| [x] Implementado y ensayado | T20: almacenamiento y recuperación de recetas | Publicación tras reparación, AST, procedencia, restauración y reutilización A→B comprobadas. |
| [ ] Parcial | T20: conceptos y transferencia general | Falta extracción parametrizada, tareas que requieran adaptar la receta, promoción/cuarentena integrada y varias generaciones. La biblioteca antigua de cuarentena solo tiene pruebas unitarias. |
| [ ] Parcial | H2: ventaja de memoria compartida | Señal positiva 3/3 frente a 1/3; una pareja evita reparación con menor coste. Falta controlar formato, código de ejemplo/biblioteca fija, transferencia negativa, familias nuevas y repeticiones de adquisición. |
| [ ] Pendiente | H1: especialistas frente a agente único fuerte | 8/12 frente a 6/12 es desarrollo; falta confirmación independiente preregistrada. Este ensayo no compara S/I2/F/E. |
| [ ] Pendiente | H3: utilidad neta del crítico | No se ablaciona aquí; las críticas se mantienen iguales cuando el episodio llega a ellas. |
| [ ] Pendiente | H4: aporte del router | No se desempata E/F con este contraste; reparar ambigüedad de categoría de grafos antes de atribuirle ahorro. |
| [ ] Pendiente | CSV y Dependencias | Detección mejorada en 0.8; reparación general sigue sin pasar. |
| [ ] Pendiente | Confirmación y release | Nuevas familias/casos reservados, muestra dimensionada, controles fuertes e instalación reproducida fuera del host. |
| Aplazado | S6 | Permanece fuera hasta después de ECHO-5.5. |

Siguiente experimento justificado: corregir para **ambas condiciones** el ejemplo de
salida del proponente y el manejo de errores sintácticos, fijar otro contrato y
repetir con adquisición y tareas nuevas. Añadir controles que separen «tener código
útil en el contexto» de «seleccionar una lección pertinente con procedencia» y medir
coste total y transferencia negativa. Este piloto queda cerrado e inmutable;
**ECHO-5.1 continúa abierto científicamente**.
