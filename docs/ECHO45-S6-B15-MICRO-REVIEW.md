# S6-B15 — microensayo cerrado y revisión del 4 de octubre

El microensayo terminó a las **18:11:58, hora de Madrid**, después de unos
42 minutos y medio. Se cerró con `MICRO_NO_PROMOTION`. No sigue activo, y no
arrancaron piloto, auditoría del piloto, campaña ni examen. S6 permanece abierto.

Se reconstruyeron las doce solicitudes y respuestas, la tokenización, las
métricas por partida, las guardas, los hashes y el presupuesto. Las 174 fuentes
congeladas permanecen intactas. El recibo está en
`lab/seed/s6b15-micro-audit-20261004/audit.json`; su script reproducible es
`python -m seed.s6b15_micro_audit`, ejecutado antes de configurar la condición
siguiente. Fue una revisión de registros existentes, con cero partidas nuevas
y cero inferencias; no se presenta como una repetición independiente de juegos.

La base y su replay coinciden exactamente: 378 niveles, digest `4458a4c2…`.
Se comprobaron las 12 propuestas y sus replays, además del replay de la base.
Las 1280 partidas físicas están en la caché y en el presupuesto, todas de A;
la reutilización de políticas idénticas redujo el máximo de 2080 previsto.
No hubo respuestas inválidas, errores de transporte, timeouts registrados ni
tracebacks. B y examen no se abrieron. El cierre negativo fue el comportamiento
correcto del coordinador, no una avería ni una auditoría pendiente.

| Vínculo operador/casos | Resumen | Niveles en las tres semillas | Pasa V3 en A |
| --- | --- | --- | --- |
| Desactivado | Antiguo | 374, 378, 378 | 0/3 |
| Activado | Antiguo | 374, 374, 374 | 0/3 |
| Desactivado | Numérico | 378, 374, 379 | 0/3 |
| Activado | Numérico | 374, 374, 381 | 0/3 |

Las seis propuestas restringidas usaron HOLD. Las seis no restringidas usaron
REVALIDATE_NOOP (tres) o COOLDOWN_CAP (tres), aunque se pidió HOLD. El enlace
funcionó en este ensayo. Con tres semillas por celda no se puede atribuir una
ventaja general al resumen numérico ni al paquete de cambios.

El mejor candidato ganó +4 niveles en A53 y +1 en A18; perdió dos niveles en
A51 y también score en A76 y A77. El agregado es +3, pero V3 exige cero pérdidas
individuales. La regla seguía siendo amplia: coincidía con 127 de 140 lecturas
HOLD distintas observadas en la base. Otra regla de HOLD, con `body_known`,
`reset_known` y `reset_useful`, coincidía con 136 de 140. Cambiar el operador
no resolvió por sí solo el alcance de las condiciones.

La revisión detectó dos problemas de representación para el refinamiento:

1. `contrastive_evidence.comparison` ordena las ganancias por índice y mezcla
   ganancias de score y niveles. En las propuestas HOLD revisadas elegía A4,
   que ya tenía todos sus niveles resueltos, como ejemplo positivo. A18 y A53
   no aparecían en el resumen de tres contrastes. El modelo habría visto una
   ganancia de score y pérdidas, ocultando la ganancia local principal de niveles.
2. `repair_experiments.target_for` solo considera propuestas con ganancia
   agregada positiva. Las reglas HOLD de 374 niveles habían ganado +5 niveles
   locales y perdido nueve en otras partidas. Se rechazan correctamente, pero
   el selector no las consideraba oportunidades para restringir la guarda.

Estos problemas no causaron una mala reconstrucción del microensayo: el diseño
factorial hacía una propuesta independiente por celda/semilla y no realimentaba
sus rechazos. Por tanto, B15 no midió el ciclo secuencial de refinamiento. Se
corrigen como hipótesis nueva, sin reescribir el resultado anterior ni atribuir
a esas correcciones una mejora ya demostrada.

El siguiente ensayo es [S6-B16](ECHO45-S6-B16-DESIGN.md). Compara controlador
previo y corregido en cuatro intentos secuenciales por semilla; comparten la
primera petición, el modelo, el presupuesto por llamada y la base. Conserva en
el feedback la mayor ganancia de niveles y una pérdida, muestra las observaciones
con nombres de features y permite refinar ganancias locales propias. El objetivo
no se acepta hasta superar todos los filtros. No se suministra el parche ganador
de PROBE2 ni se relajan V3/V4 o B1–B5.

Solo si el micro B16 obtiene ≥2 niveles nuevos sin pérdidas individuales y
replay idéntico, arrancará un piloto nuevo desde SEMILLA sin respuestas del
micro. Le seguirán auditoría, campaña y examen según las puertas existentes.
