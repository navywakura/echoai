# CAPACITY-500K · continuidad del ejecutor

30 septiembre, 02:13 Madrid. El ejecutor se trasladó de la sesión del chat a
`echoai-capacity-s6-completion.service`, servicio de usuario con `Restart=no`.
Se conservaron los 79 resultados completos. Dos búsquedas incompletas fueron
interrumpidas y sus diarios archivados antes de repetir esos casos bajo el
mismo perfil. El conjunto, entrenamiento, solver, pesos, orden de movimientos,
presupuesto y criterios permanecen idénticos. Las 190 fuentes protegidas
coinciden con sus perfiles.

El coste de CPU de esas dos búsquedas incompletas no se pudo recuperar. Cada
una tenía un techo de 400 expansiones. Es trabajo adicional declarado y no se
incluye como si fuera una respuesta completa ni se oculta en la comparación
de coste de los resultados terminados.

El servicio encadena medición y auditoría. Solo genera un paquete del siguiente
candidato si la comparación auditada cumple la puerta de promoción. Observa
el cierre de S6-B11 desde sus artefactos; su supervisor propio sigue gestionando
los envíos, promociones, auditorías y examen. No reinicia ni reenvía inferencias
S6 desde este servicio.

Al terminar guarda el resultado conjunto y envía un aviso local de escritorio.
Un aviso VERDE exige que la validación, CAPACITY-500K y S6 pasen juntos; también
se comunica el cierre con pendientes si algún criterio falla. No se envían
mensajes a terceros. El servicio necesita que el equipo esté encendido.

[Recibo del traslado](../lab/validation/echo45-completion-20260930/handoff.json) ·
[Seguimiento conjunto](ECHO45-VALIDATION-CAPACITY-S6-RESULTS.md).
