# ECHO-4.5 · camino a la próxima campaña S6

2026-09-27. **B3 implementado y lanzado en segundo plano a las 19:18 Madrid.**
Contrato concreto: [S6-B3](ECHO45-S6-B3-DESIGN.md). Supervisor y seguimiento:
[procesos](../lab/kaggle/s6b3-20260927/README.md). El plan histórico siguiente
conserva el motivo de la campaña; ejecución y criterios se rigen por el contrato.
Nav prioriza obtener evidencia de S6 VERDE pronto. Los contratos y rojos
anteriores permanecen cerrados. Este documento no autoriza gasto de pago.

## Orden inmediato

1. **S5-F2:** examen reservado del paquete H1/H3 v5.8, en paralelo a B3, con
   fuentes congeladas y cohorte nueva. S5-F falló al registrar azar y queda
   incompleto; la corrección se comprueba antes en entrenamiento.
   [Contrato nuevo](ECHO45-H1-H3-EXAM2-DESIGN.md).
   Si sale rojo, publicar el fallo y corregir en entrenamiento; no reutilizar
   esa cohorte para certificar la corrección.
2. **Desarrollo de la siguiente campaña:** integrar los mecanismos temporales
   en un espacio de propuestas que pueda modificarlos de forma útil y acotada,
   con evidencia observable de los fallos. Fijar qué parte propone el modelo
   y qué capacidades vienen programadas por nosotros. No atribuir al modelo
   los módulos H1/H3 escritos por Codex.
3. **A/B y verificadores:** cubrir todas las familias, incluidas K4 y M1;
   presupuesto de validación acorde con el examen; proteger niveles y coste
   para detectar la regresión que B2 no vio. Rechazos y contrafactuales quedan
   registrados; no seleccionar propuestas usando el examen o etiquetas ocultas.
4. **Contrato nuevo y calibración:** fijar modelo, formato, límites, número
   de llamadas, selector, coste y criterios antes de generar las propuestas.
   Preferir recursos gratuitos disponibles; cualquier frontier de pago
   requiere autorización explícita. Un cambio de modelo se declara.
5. **Cuatro brazos:** misma base válida para SEMILLA/FIJO/ECHO/SIN FILTRO;
   comparar las propuestas verificadas de petición fija y petición elegida
   por ECHO. SIN FILTRO sigue una regla fijada antes, sin elegir su final por
   el examen. Congelar las cuatro versiones antes de evaluar.
6. **Examen nuevo, desarrollo y auditoría:** publicar las comparaciones aunque
   vuelvan a ser rojas. No reciclar 8000–8059, 10000–10059 ni 16000–16059.

El fallo de B2 no era solo de sintaxis: ECHO/FIJO acabaron con la misma
estrategia, ambos perdieron niveles frente a SEMILLA/SIN FILTRO y cayó la
puntuación de desarrollo oficial. H1/H3 mejora la base, pero no demuestra
ninguna de las tres ventajas de S6 por sí solo.

## Qué debe demostrar S6 VERDE

Se conservan los requisitos del cierre anterior: ECHO ≥5 % más niveles que
SEMILLA sin perder puntuación; más niveles que FIJO y SIN FILTRO; desarrollo
oficial sin regresión; integridad y replay exactos. La siguiente campaña
debe fijar además la nueva cobertura y filtros antes de abrir resultados.
No rebajar umbrales o cambiar la comparación para obtener una etiqueta verde.

## Duración y recursos

- B2 tardó aproximadamente **59 minutos** desde el inicio de su evaluación
  local hasta el cierre auditado, con cuatro trabajadores. No incluye construir
  el nuevo espacio de propuestas ni generar las respuestas del modelo.
- El último entrenamiento H1/H3, instrumentado, midió 480 partidas en **26,4
  minutos**; el examen nuevo añade azar, generación/validación y replay completo.
  Para planificar S5-F se reserva **1–2 horas**, estimación, no plazo garantizado.
- La duración de B3 se medirá con las primeras rondas del nuevo bucle.
  Todavía no existe una velocidad válida con la que fechar S6 VERDE.
- Kaggle consultado el 2026-09-27: GPU gratuita total 30 h; usadas
  28 h 35 min 19 s, reservadas 0; **quedan aproximadamente 1 h 25 min**.
  Renueva 2026-10-03 00:00 UTC; pago desactivado. Es una lectura puntual,
  no una reserva ni garantía de disponibilidad futura.

La forma de avanzar rápido es validar una base estable y un piloto con
propuestas capaces de añadir valor, antes de gastar la cuota en otra campaña
con el mismo espacio insuficiente. Una fecha de finalización del trabajo puede
estimarse; una fecha de resultado científico VERDE no se puede garantizar.

[Diagnóstico y cierre B2](ECHO45-S6-B-RESULTS.md) ·
[Roadmap consolidado](ECHO45-ECHO5-ROADMAP.md).
