# S6 · control de revisión de transiciones obsoletas

29 septiembre 2026. Contrato fijado antes de medir candidatos. Solo desarrollo;
no LLM, no inferencia pagada, no reserva final ni modificación de B8.

En A conocida v3/11 se observaron más de 1800 decisiones con el mismo estado,
alternando acciones y rutas. La implementación nativa actualiza T/adyacencias
si cambia el estado, pero ignora una contradicción donde predijo cambio y
observó el mismo estado. Hipótesis a comprobar: esa arista obsoleta mantiene
una ruta ficticia. El nuevo observador registra predicción previa y resultado
real; los identificadores de estado son observaciones, no estado privado.

Operación candidata `REVALIDATE_NOOP` en 0–8: 0 desactivada. Tras N observaciones
sin cambio que contradicen una transición aprendida, escribe esa transición
como bucle sobre el estado observado y vacía el plan pendiente. Una observación
posterior con movimiento puede corregirla otra vez. No marca la acción peligrosa,
no borra hechos del diario y no consulta el simulador. No aplica en GAME OVER
o cambio de nivel. Usa las guardas observables de B5; mismas 32 reglas máximas.

Cuatro controles humanos en orden fijado, todos desde SEMILLA:

1. reinicio conocido y estancamiento ≥8; umbral 1;
2. cuerpo conocido y estancamiento ≥8; umbral 1;
3. estancamiento ≥8; umbral 2;
4. estancamiento ≥16; umbral 4.

A: las mismas 40 partidas conocidas, versiones 2/3 y semillas 0–19, 2000
decisiones. B de desarrollo protegida nueva: 24620–24639, ambas versiones.
Sin observador en B. El control desactivado debe conservar tres partidas A
exactas; la base debe reproducir A nativa. Cada candidato se ejecuta y repite
en A; para continuar exige +2 niveles y ninguna pérdida individual de nivel
o puntuación. Después B y replay B, también sin pérdidas individuales.
Primer control que pasa en el orden fijado es el ganador instrumental; se
terminan/documentan los cuatro controles. Hasta 760 partidas, cuatro workers.

Un positivo solo demuestra que existe una reparación útil expresable. Todavía
harían falta una gramática que la incluya, propuestas reales del modelo con
datos permitidos, piloto emparejado, campaña, auditoría independiente y examen
nuevo de cuatro brazos bajo B1–B5. Nunca se pasa al modelo el control ganador
ni se contabiliza como una mejora que ECHO haya descubierto.
