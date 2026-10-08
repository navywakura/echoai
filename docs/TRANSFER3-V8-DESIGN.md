# TRANSFER-3 v8 — diversidad de salas a presupuesto fijo

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** No se genera ni se
abre B/C. No se modifica ninguna fuente congelada.

## Por qué

V7 descartó tres explicaciones con datos: no es el convenio de signo, no es el
presupuesto y no es contradicción interna de la representación. Lo que se
saturó fue la **cobertura**: cuatro salas recorridas on-policy dan 27 features
y 38 pares de 108, y ocho veces más movimientos añaden dos de cada.

Si el techo lo pone el número de estados distintos que la escuela visita y no
el número de movimientos que gasta, entonces **a presupuesto constante, más
salas distintas debe subir la cobertura**. Ésta es la prueba directa.

## Factor único

Presupuesto de escuela fijo en **128 movimientos ejecutados** en los tres
brazos, misma escuela reparada de v5, misma recompensa de progreso, mismas 64
salas de examen de v4, criterio `rehearsal_v4.screen` sin modificar. Lo único
que varía es cuántas salas distintas recorre la escuela:

| Conjunto | Salas | Procedencia |
|---|---:|---|
| R4 | 4 | las de escuela de v3, sin cambios |
| R8 | 8 | R4 más 4 formas públicas nuevas |
| R12 | 12 | R8 más 4 formas públicas nuevas |

Los conjuntos son **anidados**: R4 ⊂ R8 ⊂ R12. Así el brazo de 4 salas es a la
vez el control de réplica, y el aumento de cobertura no se confunde con un
cambio de qué salas se usan.

Cada conjunto se exporta de las dos maneras ya definidas —estándar y con suelo
de v6— porque la exportación pesimista sólo puede ordenar lo que tiene
muestra: es la que más debería beneficiarse de una cobertura mayor.

## Coste declarado del banco público

Las formas nuevas salen de `suite(20264701, …)` excluyendo las 84 ya gastadas
(4+16 de v3, 64 de v4). **Este experimento consume 8 de las 42 formas
canónicas que quedaban en la familia y deja 34.** Se declara aquí porque no es
gratis: reduce el margen público antes de que exista el generador nuevo.

## Predicciones registradas

1. El brazo R4 con exportación estándar debe reproducir exactamente el
   `baseline` de v6 y el `corrected` de v4: 11/13/40 y 2 fallos nuevos. Si no,
   la corrida queda anulada.
2. Si v7 acertó, los pares muestreados crecen de forma monótona con el número
   de salas a presupuesto constante.
3. Si además la cobertura era la restricción activa del cribado, algún brazo
   se acerca al criterio o lo cruza.

La predicción 3 puede fallar aunque acierten 1 y 2: más cobertura con el mismo
presupuesto significa menos muestras por par, y eso puede empeorar el valor
aprendido antes de mejorarlo. Ese resultado también es informativo.

## Qué no es

Seis cribados más contra el mismo banco público de 64 salas. Siguen sin ser
pruebas independientes. **Cruzar el criterio aquí no produce un candidato**:
exigiría confirmación prospectiva en salas nuevas, con presupuesto, tamaño de
muestra y criterio fijados antes de mirarlas, y para eso hace falta el
generador ampliado. Se declara antes de ejecutar.
