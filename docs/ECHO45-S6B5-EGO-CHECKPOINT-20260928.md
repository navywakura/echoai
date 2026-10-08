# Punto de continuidad: S6-B5 y EGO-MEMORIA

Corte del 28 de septiembre de 2026, actualizado tras el cierre de B5 a las
17:36:24 Madrid. Este
documento resume evidencia existente; no cambia contratos, fuentes congeladas,
políticas, cohortes ni umbrales. El estado vivo de S6-B5 está en su
[registro operativo](../lab/seed/s6b5-20260928/status.json).

## Lo desarrollado

| Área | Implementación y evidencia | Límite actual |
|---|---|---|
| ECHO-4 | Agente situado: percepción, mundo, límites propios, continuidad, memoria, sueño, mantenimiento, relaciones, roles e integración. Perfil científico software cerrado | Falta reproducción por tercero; no acredita consciencia |
| ECHO-4.5, S0–S2 | DSL, biblioteca, objetos, conceptos, exploración determinista y diario. Progreso 15→21→24/201 en el gimnasio reservado | El examen final ARC-2 quedó en 0/120; la transferencia sigue pendiente |
| ECHO-4.5, S3–S5 | Cuerpo, predicción y rutas; H1 aprende orden y H3 conteo de entradas reales. S5-F2: 1537 frente a 1239 niveles, sin regresiones individuales y con replay | El examen final ARC-3 no pasó su umbral: 11/112 frente a 13/112 de base |
| Cambios precisos | Parches de hasta tres condiciones observables, un parámetro entero y reducción de espera restante; comportamiento vacío/inactivo y observador conservan la base | Operadores implementados por humanos, disponibles por igual a FIJO/ECHO |
| Control previo B5 | Seis de doce reparaciones positivas; primera preregistrada: 178→181 niveles A, ninguna pérdida individual A/B y replay exacto | Demuestra que una reparación útil es expresable; todavía no es automejora |
| S6-B5 | Piloto, campaña adaptativa, cuatro brazos, filtros V1–V4, conservación, examen nuevo y auditoría implementados, probados y congelados | Piloto cerrado sin promoción: ninguna propuesta aceptada; campaña/examen no ejecutados; S6 sigue sin ser VERDE |
| Refinamiento ARC-2 | Hipótesis, crítica de errores medidos, reparación de programas DSL, ocho vistas y selección entre predicciones verificadas | Desarrollo S0: 0/12 en los cuatro brazos. S2v: 2/12 en todos, incluida la base. Ventaja adicional sin demostrar; no hay entrenamiento de pesos durante la prueba |
| Observabilidad | Mini terminal con decisiones, propuestas, errores y veredictos reales; diario existente y documentos automáticos | No inventa pensamientos ni observa el examen reservado |
| EGO-MEMORIA-2 | Aprendizaje entero de cuatro acciones, costes posteriores atribuidos a su acción de origen, diario con cadena de hashes, recibos verificados, confianza desde recuerdos, clones y ablaciones | Condición terminada y auditada ROJO: M5 falla en una de dieciséis semillas |

## S6-B5: dónde está y qué queda

Kaggle entregó las doce propuestas del piloto, seis de FIJO y seis de ECHO;
el trabajo de inferencia incluye dos calibraciones adicionales. El piloto
terminó a las 17:36:24: **PILOT_NO_PROMOTION**. Las doce propuestas fueron
rechazadas en V3. Todas conservaron 178 niveles A; ninguna cambió acciones
ni fotogramas frente a la política anterior, aunque sí activó sus guardas.
ECHO acepta cero; suma A ECHO 534, FIJO 534. Las setenta fuentes congeladas
conservan sus hashes. El informe automático ya refleja CLOSED.

No falta implementar una pieza del ejecutor de B5: esta condición ya quedó
cerrada con resultado negativo. La campaña de treinta propuestas por brazo
y el examen de cuatro brazos no se ejecutaron porque dependían de la
promoción. El examen nuevo queda sin abrir, tal como exige el contrato.

Para seguir hacia S6 VERDE queda:

1. Diagnosticar en desarrollo por qué las propuestas activadas no cambian
   conducta, y desarrollar una revisión que produzca reparaciones efectivas.
   El control humano positivo demuestra que existen reparaciones expresables;
   no se trasladará ese ganador como si lo hubiera descubierto ECHO.
2. Preregistrar una nueva condición y demostrar una mejora propuesta por el
   modelo, verificada sin regresiones, y ventaja ECHO frente a FIJO.
3. Solo tras esa promoción, ejecutar campaña adaptativa desde la misma base
   y congelar SEMILLA, FIJO, ECHO y SIN FILTRO. Este último acumula propuestas
   ECHO legales y ejecutables, aunque no pasen utilidad/conservación.
4. Ejecutar examen nuevo de cuatro brazos, conservación en juegos oficiales
   de desarrollo y auditoría independiente con reconstrucción y replays.
5. VERDE exige B1–B5 juntos: ECHO ≥105 % de niveles de SEMILLA con score no
   inferior, supera FIJO y SIN FILTRO, conserva las habilidades oficiales y
   pasa toda la auditoría.

No se modificará B5 para convertir su resultado en verde. GPU gratuita y
pago desactivado; la disponibilidad de cuota condiciona nuevas campañas.

[Contrato B5](ECHO45-S6-B5-DESIGN.md) ·
[Control positivo](ECHO45-S6-PRECISE-RESULTS.md).

## EGO-MEMORIA: qué demuestra y qué queda

M1: aprende cuándo escribir. M2: el diario reduce costes, reclamaciones falsas
pagadas y errores repetidos. M3: retirar recuerdos formativos cambia conducta
y retirar igual cantidad de otros recuerdos conserva el resultado. M4: clones
inicialmente iguales divergen por su historia y sostienen conductas/citas
comprobables. Los cuatro pasan en las dieciséis semillas. M6 reconstruye
exactamente las dieciséis condiciones completas.

M5 exige aprender a verificar por consecuencias: crecimiento ≥200/1000,
ventaja de crecimiento sobre el control ≥200/1000, control tardío ≤100/1000 y
verificación tardía de pistas falsas ≥800/1000. Pasa en quince semillas.
En la restante, crecimiento 195/1000 y ventaja sobre control 165/1000.
EGO-MEMORIA-2 queda cerrado ROJO, sin rebajar requisitos.

No falta el diario, la confianza ni el crédito de consecuencias posteriores:
ya existen. Falta diseñar y desarrollar una revisión que demuestre aprendizaje
robusto de verificación, estudiar su conducta en desarrollo con controles
emparejados y fijar una nueva condición antes de un examen nuevo. La causa
del fallo de M5 no está aislada; no hay una corrección de código validada.
El resultado de una semilla reservada no será un caso especial del controlador.
La revisión deberá conservar M1–M4, satisfacer M5 y repetir M6. No hay todavía
una EGO-MEMORIA-3 implementada ni una integración demostrada en NEXUS-0 o ARC.

[Contrato EGO-MEMORIA-2](ECHO45-EGO-MEMORIA2-DESIGN.md) ·
[Cierre auditado](ECHO45-EGO-MEMORIA2-RESULTS.md) ·
[Línea del tiempo completa](ECHO4-ECHO5-TIMELINE.md).
