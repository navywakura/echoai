# CONT-A — primer componente de E4-CONTINUITY-1

2026-09-22. **Implementado y validado en desarrollo; fase completa abierta.**
[Contrato](ECHO4-CONTINUITY1-DESIGN.md). No se concede `continuity1_green`.

## Implementación

`echo4/continuity.py` guarda y reconstruye el estado del `SelfAgent` existente,
sin clonarlo ni modificar su política. JSON con clases/campos permitidos,
referencias compartidas, fuente versionada y hash esperado externo. Conserva
CAM/Q/restos/T/inverso/PATTERN, historia sensorial, BOUNDARY, referencia SELF,
métricas, cuerpo, balance de recursos y reloj de turnos. Rechaza captura
pendiente, extensiones desconocidas y perfiles no soportados. No carga pickle.

Los checkpoints pertenecen al ejecutor: contienen datos físicos privados y
no se entregan a la política ni al córtex. Un hash de custodia no es una
firma ni garantiza la veracidad de una historia aportada por un tercero.
Se asume un ejecutor confiable, monohilo y detenido entre turnos completos.
No se ha validado captura concurrente ni recuperación ante pérdida de energía.

## Pruebas y evidencia

**29 tests nuevos pasan**, incluyendo proceso nuevo, igualdad de decisiones
y aprendizaje, restos enteros de Q no nulos, profundidad 0/2/4, veto nativo,
aislamiento de copias, fuente/esquema/campos corruptos, límites, archivos
existentes, captura interrumpida y rechazo de recuperación activa no soportada.

También se ejecutó la batería amplia de **805 pruebas**: los diez módulos
ECHO-4 seleccionados, `test_nexus0` y `test_qtable`. En el primer intento
hubo ocho errores de permisos al abrir sockets localhost de las GUI bajo el
sandbox, sin fallos de aserción nuevos; se mantuvo un `expectedFailure`
histórico (`test_goal_hits_positive`). Tras autorización se repitieron
`TestGui2`, `TestGui3` y `TestGui35`: **29/29 pasan**, incluidos los ocho
casos afectados. Resultado combinado: **804 aprobadas y un fallo esperado
histórico**, sin errores pendientes. No se presenta el primer intento como
una ejecución íntegramente verde ni se ha borrado el fallo esperado.

El banco de desarrollo ejecuta cinco escenarios; guarda, continúa como
referencia y restaura en otro proceso bajo el mismo calendario `greedy`.
Cada paso compara acción, recompensa, WSP, gate, cuerpo, recursos y hash
canónico completo. La verificación posterior vuelve a construir los estados
desde el inicio y a ejecutar todas las continuaciones, no acepta simplemente
el booleano que publicó el banco.

| Caso | Turno de guardado | Pasos posteriores comparados | Igualdad | Tamaño del checkpoint |
|---|---:|---:|---|---:|
| Inicial tras calibración | 0 | 12 | Sí | 1.627.602 B |
| Memoria aprendida | 5 | 16 | Sí | 1.629.300 B |
| Historia 0 | 1 | 12 | Sí | 1.628.174 B |
| Historia 4 | 9 | 12 | Sí | 1.630.070 B |
| Terminal | 37 | 0 | Sí; no resucita | 1.631.509 B |

**52/52 pasos idénticos**, más igualdad de las cinco instantáneas iniciales
y sus estados finales. Cero llamadas corticales, hechos falsos o slots
destruidos; balances de recursos conservados. El terminal no se contabiliza
como vida completada ni como supervivencia mejorada.

Antes de cada escenario se calibra la referencia con 16 pares de ensayos
virtuales supervisados, cuatro transiciones físicas por par: 64 por caso,
320 en total, además de las vidas y continuaciones. Esta calibración no es
actividad autónoma de mantenimiento y no se oculta dentro del reloj de vida.

[Informe](../lab/echo4/continuity1-a-v1/report.json):
`development_passed=true`, `continuity1_green=false`.
Verificación posterior: `valid=true`, `findings=[]`, `continuity1_green=false`.
Los cinco checkpoints se conservan en el mismo directorio; no se sobrescriben.

Las **50 fuentes selladas por SELF-1 final** conservan sus hashes. Esto es
una comprobación de integridad de fuentes, no una nueva ejecución de su
campaña ni una extensión de aquel certificado a CONTINUITY.

## Reproducción

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_continuity1 -v
PYTHONPATH=.. python3 -m echoai.echo4.continuity_bench verify lab/echo4/continuity1-a-v1
```

Para otra campaña, `campaign` exige un directorio nuevo. El cambio de código
requiere una nueva versión/migración explícita; no reetiquetar estos datos.

## Siguiente trabajo

CONT-B: conservar sesiones diagnósticas y recuperación activa de SELF.
Después CONT-C: nuevo cuerpo/individuo, bifurcación y contrato de herencia;
CONT-D: examen nuevo con controles y auditoría de cierre. No afirmar que
CONT-A ya cubre esos dominios. E4-DREAM-1 queda en
[PLAN](ECHO4-DREAM1-PLAN.md), sin activar Qwen ni modificar sus pesos.
