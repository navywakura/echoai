# CONT-B — sesiones SELF y recuperación reanudables

2026-09-22. **Implementado; banco y verificación reconstructiva aprobados.**
37 tests nuevos y 805 regresiones: 842 pruebas, 841 aprobadas y un fallo
esperado histórico. No concede `continuity1_green` ni reabre los certificados SELF.
[Contrato previo](ECHO4-CONTINUITY1-B-DESIGN.md).

## Qué se conserva

`echo4/continuity_active.py` añade `ActiveRun`, custodia del ejecutor para
los `SelfRecoveryAgent`, `SelfReuseAgent`, `SelfSession`, `SelfAttributor`
y `RecoveryBelief` originales. No cambia su inferencia, política o física.
Conserva CAM/Q/restos/T/PATTERN, contexto sensorial, BOUNDARY/SELF, cuerpo,
referencias compartidas y el ciclo permiso de aprendizaje → mismo agente.

El diario diagnóstico contiene hasta seis recibos y catorce eventos de
elección/consumo/cancelación, más un buzón de un recibo. Se reconstruye la
inferencia con las entradas públicas y la referencia sellada para contrastar
el estado guardado, sin volver a ejecutar la física al cargar. Este diario
es evidencia del ejecutor, no un segundo almacén cognitivo del agente.

El reloj global se conserva separado del comienzo de la vida experimental:
en reutilización, la escuela deja 24 turnos previos, la vida empieza en 0 y
su única acción lleva los contadores a 25 globales/1 local. Ni guardar ni
cargar restauran recursos o vuelven a armar un ensayo completado.

CONT-A y sus fuentes permanecen intactos. El nuevo formato CONT-B usa una
lista cerrada de tipos, límites, hash de custodia externo y publicación sin
sobreescritura. `continuity_graph.py` versiona la serialización ampliada,
no copia una política ni crea otra CAM/T/Q. No hay migración silenciosa.

## Evidencia de desarrollo

**37 tests nuevos pasan.** Cubren roundtrip completo, referencias, planes
y previsiones pendientes, buzón, consumo único, confirmación, cancelación,
recibos inválidos, protección de T/PATTERN, controles sin protección y sin T,
veto, parada, terminalidad, procesos nuevos, clocks global/local, archivos
existentes, corrupción y esquema/código incompatible. Un turno interrumpido,
incluido KeyboardInterrupt, no se puede presentar después como checkpoint
limpio. El lint de los cuatro archivos nuevos pasa.

La batería amplia termina con **805 pruebas, 804 aprobadas y un fallo
esperado histórico**, sin fallos inesperados. Incluye WORLD, SENSATION,
BOUNDARY, SELF A/B/C/v2/final, CONT-A, NEXUS-0 y QTable. Se ejecutó con
permiso fuera del sandbox para que los tests GUI pudieran abrir sockets
locales; no se deshabilitaron. Sumando CONT-B: 842 pruebas.

Las 50 fuentes del informe SELF final y las 37 de CONT-A conservan sus
hashes. Además se ha repetido el verificador reconstructivo de CONT-A:
válido, sin hallazgos. Esta comprobación de integridad no se presenta como
una nueva ejecución completa de la campaña final SELF.

El banco ejecuta 18 escenarios y compara continuación original con otro
proceso: **18/18 iguales, 142/142 eventos posteriores y 67/67 turnos físicos
posteriores idénticos**, además de las instantáneas iniciales y finales.
Los hashes completos incluyen el aprendizaje; no se comparan solo etiquetas.

| Punto de pausa | Escenarios | Eventos posteriores | Turnos posteriores |
|---|---:|---:|---:|
| Inicial, plan pendiente, recibo en buzón, recibo consumido, confirmado | 5 | 115 | 40 |
| Cancelación y recibo inválido consumido | 2 | 0 | 0 |
| Recuperación inicial, aprendida y control sin protección | 3 | 24 | 24 |
| Veto, parada sin acción segura y terminal | 3 | 0 | 0 |
| Exposición armada/completada | 2 | 1 | 1 |
| Reutilización armada/completada y ablación sin T | 3 | 2 | 2 |

Los casos sin eventos posteriores no se cuentan como vidas completadas.
El veto conserva `gate_veto`, y el testigo de parada conserva
`no_safe_action` tras 59 turnos sin declarar una muerte. El caso terminal
introduce un pulso térmico -127 **fuera del prior después del diagnóstico**:
la física termina la vida en un paso y el modelo registra contradicción.
La prueba es que restaurarlo no lo resucita; no demuestra prevención de daño.

Todos los escenarios conservan balances y cero llamadas corticales, hechos
falsos y ranuras destruidas. Las decisiones originales se conservan tanto
cuando permiten aprender como cuando retienen una actualización.

## Costes y límites

Los 18 checkpoints ocupan **29.442.535 bytes** en total, aproximadamente
1,63–1,64 MB cada uno. Los 16 bytes WSP son el cable de representación, no
el tamaño del estado persistente completo.

Cada receta incluye preparación supervisada: 72 transiciones físicas para
la escuela de recuperación, o 96 para la de reutilización; no se incluyen
gratuitamente en los 67 turnos posteriores. Las sondas diagnósticas también
tienen coste: un diagnóstico completo registra 44 pasos y seis recibos,
además de la sonda nominal de ocho pasos. El checkpoint registra el contador
de pasos declarados por recibos, no lo presenta como medida física
independiente si un recibo es inválido.

Perfil: una sesión y una vida o ensayo, monohilo, entre operaciones completas.
No captura durante una sonda/turno, restauración de un nuevo cuerpo,
descendencia, bifurcaciones, rearmado de múltiples vidas, concurrencia ni
garantía de ejecución exactamente una vez en hardware tras un apagón.
Digest suministrado por custodio confiable; no es firma ni prueba de verdad
de entradas entregadas por un custodio comprometido. Los checkpoints
contienen física privada: no se exportan al córtex o a la política.

## Artefactos y reproducción

[Informe](../lab/echo4/continuity1-b-v1/report.json), con
`development_passed=true` y **`continuity1_green=false`**.
SHA-256 del informe:

```text
e36113d375f220d7d1b7f390b13818d7f1a2de480f51315d033aa5557697d3db
```

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_continuity1b -v
PYTHONPATH=.. python3 -m echoai.echo4.continuity_active_bench verify lab/echo4/continuity1-b-v1
PYTHONPATH=.. python3 -m echoai.echo4.continuity_bench verify lab/echo4/continuity1-a-v1
```

Regresiones amplias:

```bash
PYTHONPATH=.. python3 -m unittest \
  echoai.tests.test_echo4_world1 \
  echoai.tests.test_echo4_sensation1 \
  echoai.tests.test_echo4_sensation_predictor \
  echoai.tests.test_echo4_boundary1 \
  echoai.tests.test_echo4_self1 \
  echoai.tests.test_echo4_self1b \
  echoai.tests.test_echo4_self1c \
  echoai.tests.test_echo4_self1c_v2 \
  echoai.tests.test_echo4_self1_final \
  echoai.tests.test_echo4_continuity1 \
  echoai.tests.test_nexus0 \
  echoai.tests.test_qtable -q
```

`campaign` exige otro directorio: no sobrescribir esta evidencia. El
verificador reconstruye cada checkpoint desde la receta y compara todos
los eventos con un proceso restaurado; no confía en `equal=true` del informe.
La verificación independiente de los 18 casos devuelve `valid=true`, sin
hallazgos. Como control negativo, cambiar en memoria un hash de continuación
del primer caso produce `valid=false` y `initial: continuation differs`;
no se modifica el informe original.

## Siguiente

CONT-C: reanudación frente a cuerpo nuevo, descendiente y bifurcación,
con herencia y revocación explícitas. Después CONT-D: nuevo examen A/B/C,
controles y auditoría de cierre. DREAM permanece en PLAN; hardware después
del software y METAVERSE-1 último. Sin commit, push ni despliegue web aquí.
