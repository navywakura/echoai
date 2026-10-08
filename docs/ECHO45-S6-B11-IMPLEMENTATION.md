# S6-B11 · implementación y arranque

29 septiembre 2026. [Contrato congelado](ECHO45-S6-B11-DESIGN.md).

## Qué se ha implementado

- Comparación de las acciones y resultados antes/después de cada reparación,
  exclusivamente en desarrollo. Conserva ejemplos positivos y negativos
  cuando existen. Registra la primera divergencia, sin inventar su causa.
- Medición de propuestas distintas que producen el mismo comportamiento.
  Esa señal vuelve al modelo como feedback de su propio historial. Todos
  los intentos siguen contando y pasan el mismo verificador.
- Selector ECHO que alterna contradicciones, esperas, generalización y
  refinamiento según sus resultados. FIJO mantiene la petición genérica y
  recibe las mismas herramientas y formato de feedback.
- Oportunidades observadas para revisar transiciones y modificar esperas.
  No introduce un algoritmo nuevo en el actor ni una solución humana en
  sus peticiones. Las políticas se construyen con respuestas reales de Qwen.
- Desarrollo ampliado a 80 partidas; validación y examen nuevos. Conservación
  individual estricta de niveles y puntuación sin cambiar umbrales.
- Piloto de seis rondas, auditoría independiente, campaña nueva, segunda
  auditoría y examen de cuatro brazos condicionado a las promociones.
- Checkpoints con fsync y supervisor de usuario independiente del chat.
  No reenvía solicitudes ambiguas ni repite trabajos fallidos automáticamente.

## Verificación realizada

Comando: `lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m unittest tests.test_s6b11 -v`.
**13 pruebas pasan**, incluyendo exclusión de datos protegidos, novedad de
comportamiento, ejemplos de ambos signos, gramática de controles aplicables,
conservación del veto por pérdida de eficiencia y paridad del observador
con la base y con una reparación activa. El paquete que se sube a Kaggle
se importa en un proceso limpio, sin depender del repositorio local.

Durante esta verificación se corrigió una desalineación del nuevo observador:
el runner inserta reinicios automáticos que no son decisiones del agente.
Ahora se alinean con el contador existente y no se les inventan rasgos ni
decisiones. La corrección precede a la congelación y medición B11.

Preflight completo a las **16:33:26 Madrid**: base **365/400 niveles A**,
comportamiento original conservado en las 40 partidas anteriores y cuatro
pares completos con/sin observador idénticos. Es una medida de desarrollo
del simulador, no una puntuación ARC oficial ni una mejora de S6.

[Recibo del preflight](../lab/seed/s6b11-20260929/preflight.json) ·
[Perfil congelado](../lab/seed/s6b11-20260929/profile.json).

## Ejecución y alcance de la autonomía

Supervisor iniciado a las **16:30:19 Madrid**, unidad `echoai-s6b11.service`.
Visor `echoai-observe.service` activo y mini terminal de decisiones abierta.
Inferencia privada CPU en Kaggle; partidas, verificación y coordinación en
el PC. Cerrar el chat no detiene el servicio. Apagar el PC interrumpe la parte
local; la recuperación debe comprobar el estado de cualquier envío previo.

La autonomía que se evalúa es el bucle de elegir evidencia, solicitar una
reparación, comprobarla, aceptarla/rechazarla y volver a elegir sin intervención
por propuesta. El diseño de operadores, el selector y el protocolo son humanos.
El modelo tiene pesos congelados. Una trayectoria registrada no es acceso a
un pensamiento privado. La auditoría reconstruye peticiones y decisiones.

No se ha acreditado todavía el verde. Piloto exige al menos dos de tres
parejas de semillas de muestreo ganadoras, ninguna perdedora, aceptación y
ventaja total ECHO. Son tres muestreos de propuestas medidos en el mismo A,
no tres conjuntos independientes de tareas. Campaña debe volver a ganar.
Solo el examen final puede acreditar conjuntamente B1–B5.

[Resultado actualizado automáticamente](ECHO45-S6-B11-RESULTS.md) ·
[Estado del proceso](../lab/seed/s6b11-20260929/status.json) ·
[Registro de lanzamiento](../lab/seed/s6b11-20260929/launch.json).

## Recuperación del envío y primer lote activo

El programa de inferencia preparado ocupaba 30 MB por las gramáticas. El envío
original y una primera compresión zlib fueron rechazados antes de confirmarse
un trabajo. Se inspeccionó el inventario propio antes de recuperarlos. Todos
los archivos e intentos quedan conservados; no se descartó ninguna respuesta.

La [segunda adenda de transporte](ECHO45-S6-B11-TRANSPORT-RECOVERY2.md) usa LZMA:
**72655 bytes**, con descompresión idéntica byte a byte al programa congelado.
Sus cuatro pruebas pasan. El supervisor reanudó a las **16:45:40 Madrid** y
Kaggle confirmó **RUNNING a las 16:46:17** para el primer lote privado CPU
`rogeernavarro/echo45-s6b11-p0-20260929`. Este es un estado de arranque fechado;
el resultado actual está en los enlaces de seguimiento anteriores.

La auditoría adicional comprobará también el recibo remoto de los bytes
ejecutados; los doce lotes deben superarla antes del examen. No se ha cambiado
el hash del experimento B11 ni de B10. Las 13 pruebas del experimento y las
cuatro del transporte activo pasan; todavía no son los criterios científicos
de cierre B1–B5.

Para reanudar esta versión tras comprobar envíos pendientes:
`lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m seed.s6b11_background2 start`.
