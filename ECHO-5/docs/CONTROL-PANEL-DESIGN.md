# Panel local de ECHO-5

El panel permite iniciar una misión, detener el avance, ejecutar un paso,
inspeccionar evidencia y descargar el diario. El mapa representa exclusivamente
observaciones del actor. Las consecuencias verificadas y las hipótesis se
distinguen. El texto del visor nunca entra en la política.

Se reutiliza `echo5.trace.Recorder`, que adapta el diario histórico. La vista
de módulos corresponde a eventos emitidos; no supone acceso a razonamientos
ocultos. La segunda vista mide el módulo histórico `navi10_qn.Layer256` con una
entrada derivada del hash de la observación pública. Guarda potenciales y
spikes reales por tick, identifica la fuente y declara `drives_policy=false`.
Es diagnóstico del componente, no evidencia de que la política de MiniGrid
sea neuronal, ni representación de 500.000 neuronas.

Diseño: lienzo de mapa y evidencia a la izquierda, proyección de topología Q8
a la derecha, decisiones inspeccionables debajo. Fondo hielo #eff3f8, tinta
#13223a, superficie blanca, estado observado #126e82, disparo #db7039, error
#b44456. Tipografía Noto Sans disponible localmente; cifras monoespaciadas. Sin recursos
CDN, sin publicidad y sin animación aleatoria. La rotación del grafo es una
proyección visual; su color y actividad proceden de las mediciones.

El servidor escucha en 127.0.0.1. URL estable: http://127.0.0.1:8765.
Alias de navegador previsto: http://echoai.localhost:8765. No se modifica DNS
público ni /etc/hosts. `echoai.internal` necesitaría una entrada local explícita;
el servicio funciona sin privilegios de administrador con las URLs anteriores.

Se validan Host, Origin y token de sesión en operaciones que inician trabajo;
las entradas son JSON acotado, nunca órdenes de shell. Una sola misión avanza
a la vez. El historial se conserva en artifacts/control, separado de los bancos
congelados. Reiniciar una misión crea un diario nuevo.
