# CONT-D — examen conjunto de continuidad

2026-09-22. **CONT-D verde; E4-CONTINUITY-1 cerrada en el perfil software
síncrono WORLD-1 declarado.** Auditoría independiente válida, sin hallazgos.

## Qué se ha implementado

`continuity_final_cases.py` define las recetas y controles del examen.
`continuity_final_audit.py` registra la campaña, congela las fuentes antes de
B y reconstruye la evidencia en otro proceso. Reutilizan los ejecutores
CONT-A/B/C originales sin cambiar SELF, el núcleo, la política ni la física.
El manifiesto reúne 62 fuentes. El contrato y la revisión de desarrollo
están incluidos en ese manifiesto.

Pregunta: ¿continúa el mismo estado computacional bajo las mismas entradas,
incluidos aprendizaje, contexto, permisos, cuerpo y procedencia? Es una
prueba de continuidad funcional, no de identidad subjetiva.

## Resultados de campaña y auditoría

| Etapa del examen | Checkpoints exactos | Eventos posteriores idénticos | Turnos nativos posteriores | Mutantes rechazados | Bytes de checkpoints |
|---|---:|---:|---:|---:|---:|
| A, desarrollo | 23/23 | 90/90 | 52/52 | 10/10 | 37.678.973 |
| B, validación | 23/23 | 100/100 | 62/62 | 10/10 | 37.678.133 |
| C, confirmación | 23/23 | 110/110 | 72/72 | 10/10 | 37.680.196 |
| Total | 69/69 | 300/300 | 186/186 | 30/30 | 113.037.302 |

Los eventos incluyen operaciones de diagnóstico y bloqueos, no solo turnos
nativos; los totales no cuentan dos veces referencia y restauración. Las
etapas A/B/C de esta tabla son los exámenes nuevos, no los tres componentes
CONT-A/B/C. Cada etapa pasa los once grupos del contrato.

Rangos de checkpoint: A 1.628.397–1.654.545 B; B 1.628.634–1.654.406 B;
C 1.628.720–1.654.539 B. Es almacenamiento privado del ejecutor, no el tamaño
del WSP ni memoria visible por el agente. Cero llamadas corticales, hechos
falsos o slots destruidos; balances correctos. Terminales, vetos, paradas y
abstenciones se conservan; cuarentena bloquea; las ramas hermanas conservan
la misma trayectoria física con ámbitos de procedencia distintos.

El informe guarda `closure_eligible=true` y `continuity1_green=false`.
El [recibo de auditoría](../lab/echo4/continuity1-final-v1/audit-receipt.json)
concede `valid=true` y `continuity1_green=true`: reconstruye los 69 casos,
todos sus eventos, controles, checkpoints, diario e informe. También vuelve
a auditar CONT-A, CONT-B y CONT-C completos: los tres válidos, sin hallazgos.
Las fuentes y artefactos padres permanecen intactos. No basta con que un
informe se autodeclare verde.

- Reproducción: `69d57a0b03a468b3f2be7fedde5bce7edeaa2db5a2576ce9160726e2a90cec7c`.
- Lock anterior a B: `043ef85388aaa32368df28977cd1f6f3104504a0162afec8badc92417d8ede1e`.
- Diario: `e8e7039070af333ad7cdc70849d85513dbff5e99466267de1e7a6615d46cda0b`.
- [Informe](../lab/echo4/continuity1-final-v1/report.json) y
  [diario completo](../lab/echo4/continuity1-final-v1/traces.jsonl).

Costes de preparación de los **23 casos de referencia**, por etapa:

| Etapa | Pasos de escuela | Turnos nativos previos | Pasos de diagnóstico | Pasos de recalibración | Cuerpos asignados |
|---|---:|---:|---:|---:|---:|
| A | 1.672 | 147 | 844 | 216 | 5 |
| B | 1.672 | 156 | 844 | 216 | 5 |
| C | 1.672 | 168 | 844 | 216 | 5 |

No es el coste total de ejecución: excluye la repetición del auditor y de
los bancos padres, la preparación adicional de controles/mutantes y la
continuación posterior. El control de historia publica además su preparación
y tres turnos por brazo. No se cuantifican latencia o energía de hardware.

## Controles y lectura correcta

- Historia: borrar únicamente la ventana sensorial debe perder información
  y alterar el registro posterior de aprendizaje PATTERN. También se publican
  los empates de acciones y predicciones; no se exige ni se atribuye una
  ventaja de supervivencia.
- Restos de Q: se publica su ocupación nativa. El testigo de crédito unitario
  es una prueba aritmética separada sobre la tabla original, no una recompensa
  positiva inventada en WORLD-1. Se compara conservación, omisión y cálculo
  entero directo.
- Mutantes: diez por etapa; relojes, cuerpo, esquema, fuentes, digest,
  permiso, confirmación, época, asignación y ámbito de recibo. La mayoría
  recalcula el digest para probar rechazo semántico, además del rechazo de
  un digest inválido. Los originales deben permanecer intactos.
- Costes: escuela, turnos nativos previos, diagnóstico y recalibración se
  registran por separado. No son consumo eléctrico ni coste de hardware.
- Referencia y restauración: cada checkpoint se compara con el estado vivo
  original, no solo con otra copia cargada. Cada continuación restaurada
  corre en un proceso nuevo; el auditor repite esa comparación.

La [preparación A](ECHO4-CONTINUITY1-D-PREFLIGHT.md) encontró ambigüedad real
con el primer cuerpo. Se documentó antes de abrir B/C, se mantuvo SELF
intacto y se añadió el caso de abstención. No se elimina esa incertidumbre
ni se presenta abstenerse como una recuperación exitosa.

Resultado del control de historia, número acumulado de observaciones
PATTERN en sus tres turnos:

| Etapa | Ventana conservada | Ventana borrada | Diferencias de acción / predicción |
|---|---|---|---|
| A | 2, 3, 4 | 1, 1, 2 | 0 / 0 |
| B | 3, 4, 5 | 2, 2, 3 | 0 / 0 |
| C | 4, 5, 6 | 3, 3, 4 | 0 / 0 |

En las tres etapas, el control nominal tiene **cero restos Q no nulos**.
El testigo sintético sí pausa con resto: tras la tercera actualización
posterior, conservarlo da Q=1/resto=0 y omitirlo da Q=0/resto=3; al cuarto
paso vuelven a coincidir. La copia restaurada coincide siempre con el cálculo
entero directo. Esto demuestra pérdida de estado aritmético relevante, no
ventaja conductual en este mundo.

## Tests y verificaciones

33 pruebas nuevas pasan. Incluyen las 23 recetas de desarrollo A, proceso
nuevo real, checkpoint alterado, controles negativos, bloqueo antes de B,
cancelación de C si B falla y rechazo de aprobación falsificada. Las pruebas
unitarias del protocolo y del diario utilizan fixtures simulados pequeños:
no sustituyen la campaña física virtual completa ni cuentan como B/C.

Dos comprobaciones adicionales contra la evidencia final real inyectan
lecturas alteradas **solo en memoria**: un byte extra en `A-nominal0.json`
y el primer evento del diario sustituido. El auditor rechaza ambas con
`valid=false`, `continuity1_green=false` y sin certificado. Los hashes de
los originales permanecen intactos. No se han corrompido archivos del banco.

Regresiones ejecutadas en esta entrega: 805 generales y 67 CONT-B/C.
Total con las nuevas: **905 pruebas, 904 aprobadas y un fallo esperado
histórico**, sin fallos inesperados en las ejecuciones finales. Ruff pasa
en los tres archivos Python nuevos. No se modifican las fuentes selladas de
SELF final (50), CONT-A (37), CONT-B (50) ni CONT-C (54).

## Reproducción

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_continuity1d -q
PYTHONPATH=.. python3 -m echoai.echo4.continuity_final_audit verify lab/echo4/continuity1-final-v1
```

Para reproducir también la grabación, usar **otro directorio inexistente**:

```bash
PYTHONPATH=.. python3 -m echoai.echo4.continuity_final_audit campaign /tmp/echo4-continuity-final-reproduction-v1
PYTHONPATH=.. python3 -m echoai.echo4.continuity_final_audit verify /tmp/echo4-continuity-final-reproduction-v1
```

No sobrescribe evidencia previa. El informe solo concede elegibilidad;
únicamente el recibo de auditoría puede conceder `continuity1_green=true`.
La auditoría repite los tres antecedentes CONT-A/B/C. SELF queda vinculado
por su certificado existente y la integridad de fuentes y artefactos, no
por una nueva ejecución completa de SELF y sus seis antecesores.

## Límites y siguiente paso

Operaciones síncronas terminadas, WORLD-1 y custodio confiable. No cubre
captura concurrente, cortes eléctricos físicos, exclusividad distribuida,
autorreparación ni diagnóstico seguro fuera del modelo declarado. Un hash
no es una firma ni protege frente a un custodio comprometido. El checkpoint
es privado del ejecutor; no entrega al agente registros físicos ocultos y
no constituye un segundo bus. WSP sigue en 16 B, enteros y córtex apagado.

El historial con procedencia prepara **DREAM-A**, primera subfase del plan
DREAM-1, pero no es todavía un árbol de descubrimiento: ramas nunca ejecutadas
siguen sin resultado. DREAM continúa en PLAN, sin llamadas a Qwen ni cambios
de pesos. La vía basal mantiene pendiente MAINTAIN → OTHER → INTERACTION →
RELATION → ROLES → INTEGRATE. Hardware después; METAVERSE-1 último.
ECHO-4 completo no queda cerrado por este examen.

Sin commit, push ni publicación web en esta entrega local.

[Contrato final](ECHO4-CONTINUITY1-D-DESIGN.md) ·
[Preparación A y ambigüedad](ECHO4-CONTINUITY1-D-PREFLIGHT.md) ·
[Programa y roadmap](ECHO4-EGO-PROGRAMA.md) · [Roadmap canónico](ROADMAP.md).
