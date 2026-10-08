# echo-nexus 1.5.1 · lectura de la meta en `dev-world`

El mundo de desarrollo tiene una única meta en `[6,5]`. El entorno notificó
victoria y el diario de ECHO registró `level_up=true` al llegar. En la sesión
del 29 de septiembre, las primeras 66 llegadas ocurrieron cada 56 pasos, sin
muertes. A las 23:32 UTC la misma sesión había acumulado 133 llegadas; estaba
activa, de modo que esa cifra es una observación parcial. No hubo mejora en
el número de pasos de las primeras 66 repeticiones.

La frase «objetivo sin identificar» venía de `DecisionView`: interpretaba
`target=None` como ausencia de conocimiento sobre la meta. En el actor,
`target` es el destino *actual* del plan y se limpia al ganar. El diario
también muestra `recent_hypotheses=[[1,["near",3],"proposed"]]`: una hipótesis
visual sobre el color 3 a partir de la victoria. La ruta ganadora permanece
en la memoria del actor durante esa sesión.

El arnés 1.5.1 muestra por separado el destino activo, la hipótesis visual y
el número acumulado de victorias. Cuenta únicamente los eventos recibidos con
`level_up=true`; un `false` del paso siguiente no borra el total. La hipótesis
sigue etiquetada como hipótesis; no se convierte en hecho ni se devuelve al
motor como instrucción. `/echo`, `/why`, `/ask` y el árbol usan este mismo
informe.

Verificación: 25 pruebas del arnés, incluida la secuencia victoria → paso
normal → reinicio de vista. La versión instalada desde el script público es
`1.5.1`; el SHA-256 del paquete es
`8ca50715f812e62c8711e4a1601c30892112c1b1374f0a1c7d4e38aaac0e5df0`.
Release [v1.5.1](https://github.com/navywakura/echo-nexus/releases/tag/v1.5.1),
commit del arnés `bad136f`; web y captura real desplegadas en `28f745e`.

No se cambió el mapa, el agente ni la campaña congelada S6. Una TUI ya abierta
debe reiniciarse cuando el operador quiera cargar la versión instalada; el
diario anterior permanece disponible, pero la memoria activa del actor no
persiste entre procesos. Esta corrección de lectura no acredita una mejora de
política, un resultado ARC ni el cierre de S6.
