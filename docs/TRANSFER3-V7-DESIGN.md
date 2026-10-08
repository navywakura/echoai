# TRANSFER-3 v7 — cobertura y conflicto en función del presupuesto

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Diagnóstico, no
selección de candidato. No se genera ni se abre B/C. No se modifica ninguna
fuente congelada.

## Por qué

V6 refutó que el convenio de signo sobre acciones no muestreadas fuera la
restricción activa: el suelo mejora la navegación entre acciones conocidas
(+22 movimientos netos) y pierde dos metas por no explorar. V5 había medido
los dos problemas por separado —244/372 decisiones sensibles sobre acciones
sin muestra, 14 pares con órdenes opuestos— pero a un único presupuesto.

Tiran en direcciones contrarias: enriquecer el feature reduce el conflicto y
empeora la cobertura; ampliar el presupuesto mejora la cobertura y no toca el
conflicto. **Elegir un lado por argumento sería adivinar.** Este experimento
mide la curva.

## Qué se mide, por presupuesto

Presupuestos de escuela: **128, 256, 512, 1024** movimientos ejecutados, mismas
cuatro semillas de escuela, misma recompensa de progreso, misma escuela
reparada de v5.

- **Cobertura**: features alcanzadas, pares `(feature, acción)` con al menos
  una muestra, y la fracción sobre los cuatro planares de cada feature.
- **Conflicto de representación**: pares `(feature, acción)` que reciben a la
  vez un retorno de avance (≥ +7) y uno de retroceso (≤ −9). El mismo par,
  la misma feature, consecuencias opuestas: la representación no determina el
  resultado. Se mide dentro de la escuela, sin oráculo ni geometría privada.
- **Cribado** de ambas exportaciones —estándar y con suelo— contra `scratch`
  sobre las 64 salas de examen de v4, con `rehearsal_v4.screen` sin modificar.
- **Coste amortizado**: presupuesto de escuela más movimientos de examen.

## Predicciones registradas

1. A 128 movimientos, la escuela trazada debe producir un payload idéntico al
   de `school_v6.train`. Si no, la corrida queda anulada.
2. Si la restricción activa es la cobertura, la fracción muestreada crece con
   el presupuesto, el cribado de `pessimistic` mejora de forma monótona y
   cruza en algún presupuesto.
3. Si la restricción activa es el conflicto, los pares en conflicto crecen con
   el presupuesto y el cribado se estanca por debajo del criterio aunque la
   cobertura sature.

Los tres resultados son informativos. Ninguno promueve un candidato.

## Qué no es

Ocho cribados contra el mismo banco público de 64 salas **no son ocho pruebas
independientes**. Es una curva de diagnóstico sobre datos ya usados. Si algún
presupuesto cruzara el criterio, eso **no** constituiría un candidato: exigiría
confirmación prospectiva en salas nuevas, con presupuesto y tamaño de muestra
fijados de antemano. Se declara aquí para que no se lea después como hallazgo.

Tampoco prueba amortización: ampliar el presupuesto aleja el punto de
equilibrio mientras el examen siga siendo 64 salas, como registró v6.
