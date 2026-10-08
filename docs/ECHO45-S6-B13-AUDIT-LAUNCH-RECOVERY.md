# S6-B13-R1: recuperación del lanzamiento de auditoría

4 de octubre de 2026. El piloto terminó a las 04:23 de Madrid, con 54
propuestas medidas (36 del modelo, 18 del control aleatorio). ECHO sumó
1113 niveles frente a 1125 de FIJO y perdió los tres pares. Sus tres mejoras
aceptadas no bastan para promocionar. Es un resultado provisional hasta la
auditoría; el examen continúa sin abrir.

El lanzamiento de auditoría falló antes de jugar su primera partida porque
el proxy de transporte de R1 exponía `run` pero omitía `subprocess.STDOUT`.
Las pruebas anteriores cubrían el redireccionamiento del comando, pero no
el acceso a esa constante en la llamada completa. Se conserva el estado
BLOCKED original dentro del recibo de recuperación, junto con su presupuesto.

`seed/s6b13_audit_recovery1.py` añade esa constante únicamente al objeto de
transporte del proceso de recuperación. Las 159 fuentes científicas congeladas
permanecen intactas. La recuperación tiene su propio recibo, hashes y copia
de fuentes; fija también los hashes del perfil, piloto y registro de llamadas.
Una prueba nueva ejecuta un subproceso real y comprueba stdout/stderr juntos.

Se retoma `follow` original. Reutiliza el piloto terminado, no pide propuestas
nuevas, y arranca `seed.s6b13_runtime1 audit pilot` en otro proceso y con caché
separada. Reconstruye las 54 peticiones y sus veredictos, vuelve a ejecutar
las mediciones y replays y contrasta los tokens originales. Solo una auditoría
válida permitirá cerrar esta condición como `PILOT_NO_PROMOTION`. No se
habilitan campaña ni examen para un piloto que no cumple la promoción.

El tope original de 64.000 partidas sigue vigente. El fallo de lanzamiento
no cambia las puntuaciones ni convierte la derrota del piloto en un error
de capacidad del instrumento. Son dos hechos separados que deben conservarse.
