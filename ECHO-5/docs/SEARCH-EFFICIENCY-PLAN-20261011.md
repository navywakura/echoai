# Correcciones de coste y búsqueda — plan de implementación

Objetivo: reducir trabajo repetido y asignarlo a comprobaciones útiles, manteniendo
el lenguaje público completo, los presupuestos y la abstención ante un consenso
incompleto. Intervenciones autorizadas por el usuario; S6 queda fuera de alcance.

## Búsqueda

- [x] Caché acotada por resolución de análisis de rejillas inmutables, papeles y
  relaciones; cobrar lecturas, escrituras y construcción. Control sin caché.
- [x] Firmas calculadas a partir de demostraciones, con coste explícito. Orientan
  prioridades; no se eliminan operadores intermedios por dimensiones finales.
- [x] Después del primer ajuste, verificar las alternativas restantes del mismo
  nivel por contraejemplos tempranos. No aceptar por mayoría ni por el primer ajuste.
- [x] Mantener candidatos que difieran en consultas y abstenerse cuando falte
  trabajo para cerrar el nivel. Registrar el alcance limitado por beam search.
- [x] Pruebas de composiciones que cambian y restauran dimensiones, de desacuerdo
  tardío, consultas indefinidas, límites y ausencia de lectura de respuestas test.

## Exploración

- [x] Modo híbrido opcional: frontera cercana normalmente, información bajo un
  bloqueo observable. Mismas habilidades, percepción, memoria y acciones.
- [x] Registrar fase y disparador, contando el trabajo de selección y navegación.
  No se atribuye complejidad O(1) a la construcción del mapa o búsqueda de rutas.

## Currículo

- [x] Reducir selección pesada cuando queda exactamente una hipótesis y detener
  puntuaciones cuando se alcanza una cota demostrable de discriminación.
- [x] Conservar hipótesis minoritarias compatibles; 90 % de una familia no implica
  certeza. Contabilizar adquisición, selección, actualización y evaluación.

## Validación

- [x] Tests pertinentes y suite completa antes del ensayo en segundo plano.
- [x] Congelar fuentes y plan; comparar mecanismos por separado, a igual límite.
  Los casos examinados son desarrollo, no confirmación nueva.
- [x] Evaluación adicional con semillas registradas antes de observar resultados,
  todos los casos y familias publicados; reproducción en proceso independiente.
- [x] Actualizar informe y checklist con resultados, incluidos empates y fallos.

Se añadió una cuarta condición de búsqueda, con cota segura de pérdida parcial,
tras medir el piloto r2. La ejecución final r3 está
[terminada y auditada](SEARCH-EFFICIENCY-RESULTS-20261012.md): 12/18 independientes,
9/9 plantillas, híbrido 28/28 y currículo eficiente 64/64. Estas casillas
acreditan implementación y medición, no resolución de todos los problemas:
persisten seis tareas con presupuesto agotado y conclusiones científicas abiertas.

El cociente 326²/32² describe enumeración sin poda: el solver real usa frontera
limitada a 24 estados. Un ajuste en train no demuestra exactitud en test; las
94 comparaciones semánticas sin discrepancias tampoco prueban ausencia universal
de fugas o errores compartidos. Los ahorros prometidos son hipótesis a medir.
