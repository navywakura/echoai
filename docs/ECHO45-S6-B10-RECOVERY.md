# S6-B10 · recuperación tras desconexión

29 septiembre 2026. El seguimiento anterior quedó detenido a las 08:54:49 UTC
(10:54 Madrid). Ese estado local no demostraba que Kaggle siguiera ejecutándose.
Se consultó el envío existente antes de reanudarlo: **p0 COMPLETE**, seis
propuestas guardadas. La última respuesta remota figura a los 1488,5 segundos
de ejecución. No se volvió a enviar p0.

El trabajo recuperado es `rogeernavarro/echo45-s6b10-p0-20260929`. Sus respuestas,
modelo, pesos, perfil y pertenencia a las gramáticas por petición pasan las
comprobaciones congeladas. Esto acredita la inferencia, no la utilidad de las
propuestas. El perfil sigue siendo
`afc4da02cf2d7dd188c82e405617163a1e58e8152f88a8b0594b44afc231ac09`.

La continuación local se reanudó el **29 sep a las 11:20:20 UTC / 13:20 Madrid**.
Ahora `echoai-s6b10.service`, un servicio de usuario de systemd, ejecuta el mismo
`seed.s6b10 follow`. El servicio vive fuera de los procesos de herramientas del
chat. Conserva los logs anteriores y añade los nuevos; comprueba que no exista
otro verificador B10, mantiene un bloqueo y no reinicia automáticamente fallos.
No se modificó ninguna fuente del experimento congelado.

La secuencia permanece: medir las seis propuestas recuperadas, completar p1/p2,
auditar el piloto en otro proceso y caché, y continuar campaña/examen únicamente
si pasan las condiciones del contrato. Al terminar o detectar un error, el
supervisor ejecuta el publicador de resultados. Una desconexión del chat deja
el servicio trabajando; apagar el equipo o terminar la sesión de usuario puede
interrumpirlo y exige comprobar de nuevo los envíos antes de reanudar.

El visor se restauró mediante `echoai-observe.service`. Solo lee los diarios
existentes de desarrollo. No se instrumentan los exámenes ni se inventan
pensamientos. Cerrar la mini terminal no detiene la campaña.

Comprobaciones de recuperación: p0 descargado e íntegro; ningún proceso B10
previo activo; servicio del experimento activo con `Restart=no`; visor activo
y ventana visible; primeros resultados de medición escritos tras la reanudación;
`git diff --check` sin errores. Las seis pruebas experimentales y la paridad A/B
anteriores siguen referenciadas en `local-checks.json`; no se atribuyen al
supervisor ni se ejecutan de nuevo para alterar el ensayo.

Las dos primeras propuestas (FIJO/ECHO, pareja 655001) coinciden y suben
A 178→186. El verificador las rechaza por V4: B sube en agregado 181→189,
pero una partida empeora. Por tanto no se incorporan a la política. Es progreso
respecto a B9 en aplicabilidad y efecto, **no una mejora aceptada ni evidencia
de superioridad de ECHO**. El resto del piloto continúa; S6 depende de B1–B5.

La inspección visual encontró el visor inicialmente en blanco, ocupado
decodificando colas de miles de diarios archivados (21 GB de observabilidad).
Se corrigió únicamente el lector: se posiciona al final de los diarios antiguos
que no mostrará, conserva escrituras partidas y decodifica solo las entradas
históricas solicitadas. Diez pruebas del lector pasan. El visor se reinició
sin reiniciar la investigación; el perfil B10 sigue íntegro.

El publicador terminal añade automáticamente al informe los veredictos por
brazo/semilla, ganancias y pérdidas individuales, validez de la auditoría y,
si existe examen cerrado, B1–B5 y los cuatro totales. Conserva las comprobaciones
que impiden llamar verde a un empate o a un criterio fallido: tres pruebas pasan.
Se comprobó además el renderizado de los 18 veredictos negativos reales B9
sin publicar esa prueba como resultado B10. Esto no modifica ninguna decisión
del experimento.

- [Recibo de recuperación](../lab/seed/s6b10-20260929/recovery.json).
- [Comprobaciones y resultados parciales de la recuperación](../lab/seed/s6b10-20260929/recovery-checks.json).
- [Estado del supervisor](../lab/seed/s6b10-20260929/supervisor.json).
- [Estado del experimento](../lab/seed/s6b10-20260929/status.json).
- [Resultados](ECHO45-S6-B10-RESULTS.md) · [Contrato](ECHO45-S6-B10-DESIGN.md).

Consulta local, sin iniciar trabajos:

```sh
systemctl --user status echoai-s6b10.service --no-pager
cat lab/seed/s6b10-20260929/status.json
tail -n 12 lab/kaggle/s6b10-20260929/process-network.log
```

## Reanudación tras apagar el equipo · 29 sep, 15:10 Madrid

Los tres trabajos remotos p0/p1/p2 terminaron correctamente. Sus 18 respuestas,
pesos, perfil y gramáticas se comprobaron de nuevo. La medición del piloto
terminó a las 12:51:39 UTC: 18 propuestas con +8 niveles A, todas rechazadas V4
por regresiones individuales B. Las políticas conservadas siguen en ECHO/FIJO
534–534, cero aceptaciones. **Auditoría aún pendiente; reserva sin abrir.**

El apagado interrumpió la auditoría independiente a las 12:56 UTC. Tras volver
a encender aparecieron **37 archivos vacíos**, 36 entradas de caché de partidas
y un agregado de medición. La primera reanudación de las 13:06 UTC se detuvo
antes de certificar ningún resultado para recuperar esas entradas. No se
cambió un veredicto científico ni se hizo una llamada nueva al modelo.

Los archivos vacíos se trasladaron, conservando sus bytes y hashes, a
[un archivo de recuperación con recibo](../lab/seed/s6b10-20260929/recovery-history/20260929T130856Z/receipt.json).
Las partidas faltantes se vuelven a ejecutar con las fuentes congeladas; no se
copian resultados del piloto a la auditoría. No quedaron diarios A sin su
entrada de caché válida en el punto de reanudación.

El supervisor ahora comprueba también la integridad de las cachés de auditoría
antes de arrancar y conserva los recibos de recuperaciones anteriores. Dos
pruebas específicas pasan: rechazo de archivos vacíos sin borrarlos y rechazo
de registros con hash incorrecto. Se verificaron **290 entradas válidas** antes
del reinicio definitivo, a las **13:10:14 UTC / 15:10 Madrid**. Ambas funciones
son del supervisor externo; el perfil experimental sigue siendo `afc4da02…31ac09`.

`echoai-s6b10.service` vuelve a estar activo y el visor está abierto. La auditoría
debe reconstruir los 18 veredictos y coincidir exactamente con el piloto antes
del cierre. Con el resultado medido actual no habrá campaña ni examen B10.
El publicador documentará el cierre al terminar; S6 sigue sin acreditar B1–B5.

A las 13:11:56 UTC ya se habían reconstruido los **37 archivos afectados**;
las 375 entradas de caché presentes pasaban su comprobación y el primer agregado
B reconstruido coincidía exactamente con el del piloto. Queda terminar la
auditoría de los demás candidatos. [Recibo de esta comprobación](../lab/seed/s6b10-20260929/recovery-history/20260929T130856Z/verification.json).
