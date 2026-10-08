# Validación general NEXUS-0 · 30 septiembre

**Validación de regresión aprobada:** 488 pruebas en 332,369 segundos,
`OK (expected failures=1)` con Python de sistema 3.14. Ningún cambio de código
del núcleo fue necesario.

El primer intento reprodujo `PermissionError: [Errno 1] Operation not
permitted` al crear el socket del servidor HTTP local de `TestGui2`. Es una
restricción del sandbox de ejecución. El mismo comando, con permiso para abrir
el servidor local y ejecutado una sola vez, completó la batería general.

El fallo esperado es `TestWalk1.test_goal_hits_positive`: conserva una
limitación histórica de navegación que la prueba documenta explícitamente.
No se ha corregido esa capacidad ni convertido el caso en aprobado. La batería
de regresión pasa con esa expectativa previa; esto no acredita todos los
objetivos científicos de todas las extensiones de NEXUS.

Comando: `PYTHONPATH=..:. python3 -m unittest -v -f echoai.tests.test_nexus0`
desde el directorio `echoai`. No se usaron el entorno ni las herramientas de
`echo-discord`, ningún LLM ni hardware externo.

[Log completo](../lab/validation/nexus0-20260930/complete.log) ·
[Fallo reproducido del sandbox](../lab/validation/nexus0-20260930/sandbox-failure.log).

Las siete pruebas del nuevo banco y la comparación ARC también pasan, y las
190 fuentes protegidas de S6, memoria y evaluación siguen coincidiendo con
sus perfiles. La comparación ARC-1 sigue un contrato y artefactos propios.
