# E4-CONTINUITY-1 — contrato de continuidad computacional

2026-09-22. **En desarrollo; no cerrado.** Primer entregable: CONT-A,
pausa/reanudación de `SelfAgent` en WORLD-1 nominal, entre turnos completos.
No modifica fuentes ni certificados de SELF-1.

## Pregunta y primer dominio

¿Produce una ejecución restaurada las mismas acciones, observaciones,
recursos y cambios de memoria que una ejecución ininterrumpida, con la misma
secuencia de entradas? Guardar un identificador o únicamente CAM no basta.

CONT-A admite exactamente `SelfAgent` + `DockEnv` nominal, profundidad
sensorial 0/2/4, sin córtex, oracle, planner, recuperación activa ni hooks
externos. Conserva CAM, Q y sus restos enteros, T e inverso, PATTERN,
ventana sensorial, BOUNDARY y referencia SELF, métricas, cuerpo, balances y
relojes. Este perfil no usa RNG, reloj de pared ni colas externas: se
rechazan extensiones desconocidas, no se presupone haberlas guardado.

El guardado es del **ejecutor**, no una observación del agente: contener
el cuerpo exacto no permite entregárselo a la política o a Qwen. No es un
segundo bus cognitivo. La política continúa recibiendo WSP de 16 bytes.

## Formato y procedencia

- JSON versionado con tipos permitidos explícitos, campos exactos, límites
  de tamaño/profundidad y referencias que conservan la única CAM/T/Q.
- Sin pickle, imports indicados por el archivo, eval ni código ejecutable.
- Huella de fuentes y hash esperado suministrado por el custodio fuera del
  archivo. Un hash autocontenido no prueba autenticidad; este contrato no
  sustituye una firma ni protege a un custodio comprometido.
- Escritura completa antes de publicar, sin sobreescribir instantáneas.
- Rechazo de captura a mitad de predicción, campos desconocidos, código
  cambiado, cuerpo/relojes incompatibles y configuración fuera del perfil.
- Restaurar terminalidad no resucita. Reiniciar cuerpo o individuo no es
  una reanudación autorizada por esta API.

## Pruebas fijadas antes de ejecutar CONT-A

1. Igualdad del estado canónico completo al cargar, incluyendo restos de Q
   y contexto temporal; referencias compartidas conservadas.
2. Igualdad paso a paso de acciones, recompensas, WSP, recursos y hash de
   estado bajo entradas iguales; al menos un caso en proceso nuevo.
3. Casos iniciales, memoria aprendida, referencia calibrada y estado terminal.
4. Rechazo sin mutar el origen: corrupción, hash/procedencia incorrectos,
   versión desconocida, tipos/campos inesperados y operación pendiente.
5. Regresiones seleccionadas de SELF/SENSATION/BOUNDARY y núcleo; cero
   cortex_calls, false_facts y destroyed en el perfil nominal.

Estos tests acreditan únicamente el primer componente. **No conceden
`continuity1_green`** ni trasladan automáticamente el verde de SELF-1.

## Lo que falta para cerrar la fase completa

- CONT-B: ampliar el serializador a sesiones SELF confirmadas y recuperación
  activa, con pendientes/recibos y reloj experimental explícitos; no fingir
  que el primer perfil cubre SelfRecoveryAgent o SelfReuseAgent.
- CONT-C: distinguir reanudación, nuevo cuerpo, descendiente y bifurcación;
  contrato de herencia y revocación de diagnósticos dependientes del cuerpo.
- CONT-D: examen nuevo A/B/C con fuentes congeladas, controles de pérdida
  de historia/restos, mutantes y replay independiente de las trayectorias.
  Publicar diferencias y costes, sin convertir paradas en vidas completadas.

## Relación con DREAM

La continuidad verificable prepara un historial con procedencia para
[E4-DREAM-1](ECHO4-DREAM1-PLAN.md). Un checkpoint aislado **no** es un árbol
contrafactual: ramas nunca ejecutadas siguen sin resultado. DREAM es una
rama cortical opt-in; no enciende Qwen en CONTINUITY ni en NEXUS-0.
