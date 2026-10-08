# CONT-B — continuidad de diagnóstico y control SELF activo

2026-09-22. Contrato de desarrollo previo a implementación y banco.
Extiende CONT-A sin modificar sus fuentes ni las selladas por SELF final.
No concede `continuity1_green`; linaje y examen conjunto quedan para CONT-C/D.

## Perfil

Guardar los agentes originales `SelfRecoveryAgent` y `SelfReuseAgent`,
`SelfSession`/`SelfAttributor`, creencias de recuperación, permisos de
aprendizaje y estado de ensayo de reutilización. Una única CAM/T/Q por agente.
Sin LLM, reloj de pared, callbacks externos ni nuevo bus. WSP sigue en 16 B.

El ejecutor CONT-B mantiene una sesión diagnóstica, hasta seis recibos de
sonda y su orden de consumo, un buzón de un recibo, reloj global de turnos y
origen del reloj de la vida actual. El historial de recibos es custodia del
ejecutor, no memoria adicional que recibe la política. Reconstruir la sesión
desde sus entradas públicas permite detectar estado diagnóstico incoherente.

Puntos de pausa: antes de elegir sonda, plan pendiente antes de ejecutarlo,
recibo recibido pero aún no consumido, entre sondas, confirmación completada,
cancelación, recuperación entre turnos y ensayo de reutilización armado o
completado. No se guarda dentro de una sonda física ni a mitad de un turno.
Un fallo inesperado en una operación envenena la sesión y prohíbe guardarla.
Una parada normal de RecoveryStop no autoriza nuevas acciones ni resucita.

Solo WORLD-1 nominal y RecoveryEnv de acoplamientos binarios/pulso inicial.
Los cuerpos y las perturbaciones privados se guardan en custodia, nunca se
entregan al diagnóstico. No se implementan cambios de cuerpo, rearmado de
vidas ni herencia. Una restauración previa de laboratorio puede dejar
`metrics.turns` mayor que `life_turns`: se conservan ambos, no se igualan.

## Persistencia

Formato CONT-B separado, JSON cerrado, digest externo obligatorio, fuentes
fijadas, límites estructurales y de bytes, publicación sin sobreescritura.
Rechazo de tipos/campos desconocidos, alias de contenedores mutables,
referencias rotas, clocks incoherentes, permiso desligado del agente, sesión
no confirmada que pretende autorizar recuperación y predicciones pendientes
del turno físico. CONT-A no se migra ni reetiqueta silenciosamente.

## Pruebas prospectivas

1. Canonicalización completa y conservación de referencias compartidas,
   incluyendo el ciclo permiso → agente; guardar no cambia el origen.
2. Reanudación en procesos nuevos con igualdad de planes, diagnósticos,
   acciones, recompensas, veto, aprendizaje/retención y hashes posteriores.
3. Diagnóstico pendiente/recibido/confirmado/cancelado/inválido; protección
   contra doble consumo, token repetido y acción antes de confirmar.
4. Recuperación selectiva, control sin protección, veto, parada y terminal;
   reutilización con T y ablación sin T, sin duplicar una acción de ensayo.
   El testigo terminal introduce un pulso -127 fuera del prior tras el
   diagnóstico y ejecuta la física: no simula morir editando un booleano.
   Su aceptación es conservar la terminalidad, no prevenir ese daño.
5. Preservar origen global de turnos tras escuela previa y todos los relojes
   de vida, estados térmicos y balances de recursos.
6. Corrupciones con digest antiguo y mutantes re-hasheados de esquema,
   referencias, sesión, pendientes, costes, clocks, campos y código.
7. Banco de desarrollo reconstruido desde sus recetas en otra ejecución;
   no confiar solo en `equal=true` del informe. Registrar fallos y costes.
8. Regresiones de CONT-A, SELF y núcleo; verificar hashes previos y replay
   CONT-A sin atribuir a este trabajo una nueva campaña completa de SELF.

El éxito de este componente demuestra continuidad computacional en ese
perfil, no identidad subjetiva, reparación autónoma, captura concurrente o
recuperación tras caída eléctrica. DREAM permanece en PLAN.
