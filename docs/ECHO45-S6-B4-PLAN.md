# S6-B4 · reparación localizada y feedback de verificación

Propuesta inicial del 2026-09-27, conservada abajo. **Actualización 2026-09-28:
implementación y preflight terminados; piloto en desarrollo desde las 00:49.**
El [contrato final](ECHO45-S6-B4-DESIGN.md) fija un cambio por parche, cuatro
brazos de piloto (24 propuestas), continuación condicional y examen nuevo.
[Estado del servicio](../lab/kaggle/s6b4-20260928/README.md). Este plan inicial
no certifica mejoras; sus cifras tentativas no sustituyen el contrato final.

## Qué sabemos de B3

B3 cerró auditado ROJO a las 23:04 Madrid: SEMILLA/FIJO/ECHO 1668/1800;
SIN FILTRO 1586/1800. B1/B2 fallan, B3/B4/B5 pasan. Los tres primeros brazos
conservaron exactamente la misma política. El desarrollo oficial se mantuvo
intacto y todos los replays pasaron. El filtrado protege en esta comparación;
no hay evidencia de automejora ni ventaja de preguntar adaptativamente.

Diagnóstico separado, reconstruido **solo con entrenamiento A y sus caches**:

- 60 respuestas válidas y ejecutables, ninguna aceptada; todas rechazadas por V3.
- 51/60 modifican ocho o más defaults globales de los once disponibles.
- 55/60 pierden niveles en alguna partida y 55/60 pierden puntuación individual.
- Cinco respuestas ganan niveles agregados; todas pierden también puntuación
  agregada y contienen regresiones individuales. Las cinco restantes sin
  regresiones individuales conservan el resultado base y no aportan ganancia.
- ECHO usa P1/P2/P4 diez veces cada uno. P3 no se activa sin aceptación.
  El selector nunca obtiene una recompensa positiva en esta campaña.
- Las peticiones contienen resúmenes de niveles, acciones finales y soporte de
  memorias. P2 elige los cinco peores resultados, sin agrupar realmente por
  similitud de episodios. Los rechazos se guardan, pero no se devuelven como
  contraejemplos individuales en los prompts siguientes.

La distribución de cambios y las pérdidas son observaciones. Que los cambios
globales y la evidencia insuficiente expliquen el fracaso es una hipótesis:
se comprobará por ablación, no se da por demostrada.

## Cambio propuesto

1. **Parches pequeños que heredan la base.** Sustituir la reescritura completa
   de once defaults por una reparación localizada con condición observable y
   uno o dos cambios acotados. Fuera de la condición se conserva el controlador
   nativo; comprobar paridad con un parche inerte antes de usar el modelo.
   Persisten parser cerrado, límites enteros y determinismo. El modelo propone
   datos/una composición de operaciones disponibles, no ejecuta prosa.
2. **Episodios observables.** Dar secuencias cortas antes/acción/después, progreso,
   predicción incumplida y memoria relevante; objetos renombrados por aparición
   y relaciones observadas. P2 agrupa por esos patrones, sin etiquetas de
   familia. Nunca recibir seeds, solucionador, estado oculto o mundos de examen.
3. **Feedback concreto.** Devolver por qué se rechazó el parche y la transición
   donde dañó una habilidad previa. ECHO puede elegir reparar ese contraejemplo;
   FIJO conserva su instrucción genérica. Ambos tienen el mismo modelo, base,
   operaciones, historial disponible y presupuesto; cambia la selección y
   composición de la petición. No ocultar las regresiones por un total mayor.

Esto mide selección/composición de estrategias acotadas. No se atribuyen al
modelo los módulos H1/H3 ni una operación que escribamos nosotros. Cualquier
ampliación programada del espacio de operaciones estará disponible para todos
los brazos y se declarará antes de medir.

## Piloto antes de otra campaña larga

- Propuesta inicial: seis respuestas por brazo, doce en total, solo desarrollo
  A/B 0–39, con el mismo modelo gratuito y datos observables.
- Comprobar formato, paridad del parche inerte, ejecución, replay y utilidad
  contra la base en las once familias, conservando niveles y puntuación por
  partida. Comparar también contra el formato de defaults completos para
  identificar qué cambio ayuda, con presupuesto equivalente.
- Exigir una mejora verificable retenida en A y sin regresión en B para avanzar
  del piloto. Ese mínimo verifica funcionamiento; no es S6 VERDE ni asegura
  alcanzar la ganancia del examen. Analizar si las ganancias de desarrollo
  permiten acercarse al umbral del 5 % antes de gastar otra campaña completa.
- Si no hay avance, usar los contraejemplos para decidir si falta información,
  una operación expresable o capacidad del modelo. No aumentar llamadas sin
  evidencia de que el espacio puede producir una reparación útil.

Solo después: contrato B4, fuentes congeladas, cuatro brazos con igual
presupuesto, políticas finales congeladas, examen nuevo no consumido y auditoría.
Conservar B1–B5: ECHO ≥105 % de SEMILLA sin perder puntuación, ECHO > FIJO,
ECHO > SIN FILTRO, desarrollo oficial intacto e integridad/replays.
No reutilizar 16000, 17000 ni 18000–18059. La cohorte nueva todavía no se fija.

En B3 el umbral del 5 % habría exigido al menos 1752 niveles, 84 más que la
base. Es una ilustración de la magnitud, no un objetivo para reoptimizar ese
examen consumido. El próximo umbral dependerá de su nueva SEMILLA medida.

[Resultados B3](ECHO45-S6-B3-RESULTS.md) ·
[Diagnóstico reproducible](../lab/seed/s6b3-20260927/diagnose_training.py) ·
[Evidencia solo de entrenamiento](../lab/seed/s6b3-20260927/training-diagnosis.json).
