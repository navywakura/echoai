# SHIELD-2 · reparación de control y diagnóstico de coste

22/10/2026. Encargo autorizado por Nav: «haz SHIELD-2 y luego continua
con reparación de E». Este protocolo numérico lo concreta el implementador
antes de medir; sus parámetros son decisiones técnicas, no citas de Nav.
Solo desarrollo y validación de desarrollo; ningún examen histórico o nuevo.

## Pregunta y alcance

En SafetyCarGoal2-v0, ¿añadir velocidad al control reduce la cola de coste
sin obtener seguridad dejando de alcanzar metas? SHIELD-1 conserva fuentes
y resultados. Se importan Gate/HurtTable y funciones de frontera existentes.
Nada en NEXUS, WSP16, hardware, LLM, PPO ni pesos entrenados se modifica.
La reparación se escribe en `echo58/shield2`; control rápido entero, frontera
física con floats. Entorno existente `~/.venvs/safe1`, sin instalaciones.

La autopsia histórica no identifica la causa de cada choque. El código
original no entrega magnitud de velocidad ni presupuesto restante a Gate.
Eso motiva esta hipótesis; no constituye una causa demostrada.

## Fases y semillas nuevas

1. Aprendizaje original ECHO-L:40episodios, semillas31000…31039,1000pasos
   como máximo cada uno. Una misma HurtTable se acumula, después se congela
   y se comparte idéntica por todos los brazos. Su coste se publica aparte.
2. Diagnóstico:10episodios legacy, semillas32000…32009, con trazas completas.
   Sirven para describir costes, velocidad y vetos, no para elegir parámetros.
3. Validación de desarrollo:50semillas33000…33049, cuatro brazos pareados,
  1000pasos cada episodio, máximo4procesos CPU. Orden y parámetros fijados
   antes del diagnóstico; no ajuste ni repetición según los resultados.

No se usan semillas0…39,100…109,4000…4049 ni gridworlds históricos. Los
250episodios máximos de este protocolo no son un examen ciego general.

## Cuatro brazos

- `legacy`: Gate aprendido congelado + actuación original de SHIELD-1.
- `slow`: mismo gate/margen3; regulador con velocidad objetivo fija300mm/s.
- `adaptive`: reparación propuesta. Margen3 más `min(2,max(0,(speed_mm-1)//500))`
  para frenar antes a velocidades≥501 y≥1001mm/s. Velocidad objetivo300mm/s
  si la cercanía en el rumbo elegido de un canal aprendido costoso es≥65;
  en otro caso700mm/s. Solo usa LiDAR, movimiento y velocidad observables.
- `budget_stop`: gate/margen original y regulador fijo300mm/s; al acumular
  coste20 frena recto el resto del episodio. Control fuerte que sí recibe
  coste acumulado; se declara su información adicional y pérdida de progreso.

El regulador compartido por los tres brazos nuevos conserva la dirección
y el giro del actuador original. Usa su acción normal; si velocidad hacia
delante supera objetivo+100mm/s, solicita la misma actuación con freno.
Si no, limita la componente de avance a `min(avance_original,
max(0,(objetivo-vf_mm)//2))` en escala1000, conservando el giro antes del
clip final de ambas ruedas. El freno del gate siempre tiene precedencia.
En budget_stop el freno recto usa heading12, sin añadir giro.
Los detalles de normalización pertenecen a la frontera, nunca al core entero.

Canales costosos son exactamente las claves de `Gate.danger_tiers()` aprendido.
Cercanía es el máximo `shield1.gate.heading_closeness` para esos canales y
rumbo elegido, o cero sin canales. Velocidad total es la norma XY de
`env.task.agent.vel`; longitudinal es `shield1.run.forward_speed`. Conversión
mm/s: `int(round(1000*x))`, empates al par, sin saturación. No finitos son
fallos instrumentales. `lidar_ints` se hereda sin alterar. Se registran por
separado el veredicto/freno del gate y los frenos extra por velocidad/presupuesto.
Adaptive evalúa conjuntamente velocidad y margen; no aísla el efecto del margen.

No hay «presupuesto garantizado»: el freno tiene inercia y un objeto ya
empujado puede seguir costando. No se termina un episodio al llegar a20.

## Trazas y medidas

Cada paso guarda estado previo y posterior: LiDAR entero completo, velocidad
total y longitudinal en mm/s, bin de movimiento, propuesta, rumbo/freno/
veredicto/margen/objetivo elegidos, acción de las ruedas, recompensa, coste
crudo, coste binario `int(c>0)`, acumulado, meta y term/trunc. Se guardan
los componentes `cost_*` que devuelve **ese mismo env.step**, sin llamar
otra vez a la función de coste ni consultar posiciones ocultas para decidir.

El presupuesto25 cuenta pasos con coste, igual que SHIELD-1. El coste crudo
y sus componentes se publican además; no se sustituyen sus denominadores.
Recibos por episodio exclusivos y trazas comprimidas con SHA256; progresos
reales por bloques de pasos. Fallos conservados, sin replay automático.

Puerta de utilidad de desarrollo para adaptive, todos simultáneos:
- legacy tiene al menos un episodio >25; si no, cola inconclusa;
- menos episodios >25 y menor coste binario total que legacy;
- metas adaptive≥80% de legacy y adaptive alcanza alguna meta;
- frente al control slow: coste no mayor y metas no menores, con una
  desigualdad estricta. Si slow gana, no se atribuye valor al margen adaptativo.

Retornos, peores episodios, costes por canal, velocidad de pasos con coste,
OK/MODIFY/BLOCK y comparaciones con budget_stop son descriptivos. Esta puerta
no certifica seguridad universal ni transfiere a Point u otras tareas.

## Custodia

Tests de core entero, regulador, prioridad de freno, equivalencia legacy y
auditor que recalcula decisiones/coste desde trazas. Builder check antes
de implementar y revisión de código antes de congelar/aprender. Fuentes,
versiones del simulador, contrato, agenda y tabla aprendida archivados antes
de validar. No cambiar código una vez iniciada la medición; cualquier defecto
instrumental conserva sus recibos y exige revisión prospectiva.

Term/trunc del entorno completan un episodio con sus pasos reales. Excepción,
traza incompleta o condición ausente son fallos instrumentales, nunca coste
cero ni abstención válida: dejan la puerta inconclusa y conservan recibos.
Un fallo de aprendizaje impide validar una tabla parcial. Sin reintento automático.

Al acabar, informar aunque salga rojo y continuar con la reparación del
buscador de E. No abrir exámenes ni publicar en Hugging Face.
