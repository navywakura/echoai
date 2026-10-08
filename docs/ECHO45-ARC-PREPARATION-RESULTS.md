# Comparación ARC preparada · diagnóstico de capacidades

29 de septiembre de 2026, 19:43 Madrid. **Preparación técnica completada.**
S6-B11 sigue en ejecución y no está verde. No hay nuevas puntuaciones ARC ni
un examen reservado nuevo abierto por este trabajo.

## Qué está implementado

- Comparador de referencia, presupuestos, cohortes, ganancias y pérdidas por
  tarea/juego, porcentajes relativos y puntos porcentuales. Base cero produce
  `null` en el porcentaje relativo.
- Comprobación de **190 fuentes protegidas**, seis manifiestos, datos de
  evaluación y código de los juegos; reconstrucción de la referencia desde
  sus 536 registros auditados, sin reabrir el examen antiguo.
- Bloqueo de políticas provisionales: ARC3 solo podrá utilizar la política
  ECHO final si S6-B11 cierra B1–B5 en verde, con todas sus auditorías.
- Adaptador al ejecutor nativo B11 y repetición independiente de las futuras
  partidas. Un control con política vacía conserva exactamente acciones,
  frames, niveles, modelo, score y contadores del actor anterior en un juego
  de desarrollo, con 40 decisiones.
- Doce tareas sintéticas etiquetadas por capacidad, tres condiciones,
  observación pasiva en la mini terminal y auditoría desde otro proceso.

[Código del comparador](../seed/arc_comparison.py) ·
[Diagnóstico](../seed/arc_capabilities.py) ·
[Contrato y comandos](ECHO45-ARC-COMPARISON-DESIGN.md).

## Referencia que se conserva

| Prueba | Resultado anterior auditado | Nueva medición |
|---|---:|---|
| ARC-1 | 31/400 tareas exactas, 7,75 % | Pendiente de un candidato de rejillas diferente; B11 no lo cambia |
| ARC-2 | 0/120 tareas exactas | Mismo límite: S6-B11 no añade operaciones de rejillas |
| ARC-3 | 11/112 niveles; score local del contrato 0,6436787896/100 | Preparada y bloqueada hasta candidato final S6 verde |

No se atribuye una mejora ARC-1/2 al controlador de juegos. Los alias se
declaran expresamente. Los conjuntos de seguimiento ya son conocidos: un
resultado posterior no se presentará como una nueva evaluación ciega.

## Diagnóstico sintético, ya medido y reproducido

Cada casilla contiene tres tareas, cada una con tres demostraciones y dos
tests. Todos los brazos usan el mismo refinador y un límite global de 2000
programas por tarea. Se puntúa la primera solución elegida, exigiendo que
acierte todos los tests.

| Capacidad del generador | Completo | Sin relaciones nuevas | Sin composición |
|---|---:|---:|---:|
| Aislar objetos | 3/3 | 3/3 | 3/3 |
| Relación con marcador | 3/3 | 0/3 | 3/3 |
| Ordenar objetos por área | 3/3 | 0/3 | 3/3 |
| Aislar y después rotar | 3/3 | 3/3 | 0/3 |
| **Total** | **12/12** | **6/12** | **9/12** |

Las relaciones aportan seis aciertos en estas familias frente a su ablación;
la composición aporta tres frente a la suya. La prueba de objetos conserva
aciertos en todos los brazos. Es un **control diagnóstico construido para
estos mecanismos**, con una muestra pequeña; no estima una puntuación ARC,
una mejora de versión ni inteligencia general. El código de esos mecanismos
ya existía: este trabajo prepara y prueba la medición, no los presenta como
capacidades recién aprendidas.

Completo y sin relaciones consumen 24000 programas cada uno; sin composición
consume 3865 porque agota su espacio de búsqueda antes del límite. La igualdad
es del techo permitido, no del gasto real ni del tiempo. El registro conserva
también pasos primitivos, ambigüedad y tiempos. En una tarea de objetos hubo
varias predicciones compatibles con las demostraciones; la elegida acertó,
pero la ambigüedad permanece documentada.

**36/36 resultados reproducidos exactamente en otro proceso.** Los outputs
de test se mantienen fuera del solver. El visor muestra hipótesis ajustadas
a las demostraciones, no pensamientos inventados ni certeza sobre tests.

[Resumen completo](../lab/final/echo45-comparison-prep-20260929/v2/development/summary.json) ·
[Auditoría](../lab/final/echo45-comparison-prep-20260929/v2/development/audit.json) ·
[Perfil](../lab/final/echo45-comparison-prep-20260929/v2/profile.json).

## Verificación técnica y conservación

27 comprobaciones distintas pasan: 26 con Python del sistema y una de
integración en el entorno ARC gestionado. Cubren pérdidas que se ocultan en
el agregado, cohortes incompletas/duplicadas, presupuestos diferentes, outputs
ocultos, contabilidad de reinicios, puntuación ponderada, fuentes modificadas,
políticas no promocionadas, macros en la ablación y autenticidad del visor.

La primera preparación y sus resultados se conservan en el directorio padre.
La versión activa v2 añade comprobación explícita del corpus y del intérprete
de evaluación. Se repitió el diagnóstico: los 36 resultados del solver son
idénticos a los anteriores, sin cambiar familias, presupuestos o criterios.
Perfil activo: `ab58be03144ff7d82b8ac970181d0c4e4302818701905ab1e4ddc710a522267d`.

Las 190 fuentes protegidas permanecen idénticas, incluida la ejecución S6
actual. La documentación nueva y el visor están fuera de esos manifiestos.
Solo se recargó el visor; no se reinició S6. No hubo llamadas adicionales al
modelo, envíos a Kaggle ni entrenamiento con datos reservados.

## S6: captura provisional del avance

A las **19:42 Madrid**, S6-B11 verificaba localmente su tercera ronda. Las dos
rondas completas contienen doce propuestas: once rechazadas en V3 y una
aceptada de ECHO, en la repetición 675017. Esta mejora pasó de **365 a 373**
niveles A y de **168 a 171** niveles B, sin pérdidas individuales medidas.
FIJO todavía tenía cero aceptaciones en esas rondas. Se trata de niveles
del banco S6, no de tareas ARC-AGI.

Una propuesta posterior alcanzó 378 niveles A pero perdió una medida
individual y fue rechazada. La política conservada sigue en 373. Es la
diferencia entre medir un total mayor y aceptar una mejora sin regresiones.

ECHO gana una de tres repeticiones; necesita al menos dos y ninguna perdedora
al cerrar el piloto. Falta su auditoría independiente y, si promociona, la
campaña nueva y el examen de cuatro brazos. La captura es histórica, no un
indicador de actividad permanente.

[Captura con hashes de rondas](../lab/final/echo45-comparison-prep-20260929/v2/monitoring/s6-20260929T174225Z.json) ·
[Estado vivo de S6](../lab/seed/s6b11-20260929/status.json).

## Lo que queda

1. Terminar S6 bajo sus condiciones vigentes; conservar y explicar cualquier negativo.
2. Congelar el candidato elegible y ejecutar el seguimiento ARC3, con auditoría.
3. Registrar mejoras del solver de rejillas y comprobarlas en desarrollo real
   ARC-1/2; este diagnóstico por sí solo no resuelve su transferencia.
4. Implementar el adaptador de memoria y medir sus ablaciones según el
   [protocolo memoria→ARC](ECHO45-MEMORY-ARC-TRANSFER-PLAN.md). EGO-MEMORIA-3E
   conserva su verde en aldea; su transferencia sigue pendiente.

[Orden actualizado después de S6](ECHO45-POST-S6-PLAN-20260929.md).
