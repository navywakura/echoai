# B21 — implementación de la investigación recibida

6 de octubre de 2026. B21-A implementado y prerregistrado; medición en cola
hasta que B20 cierre con auditoría y revisión aritmética válidas. S6 sigue
abierto. El estado vivo y los resultados posteriores están en
[B21-A-RESULTS](ECHO45-S6-B21-A-RESULTS.md).

Se leyó el PDF local de 13 páginas. Su SHA-256 es
`0ad4ef6145fe3dbaa99ecac133ed5be4302e314e4c1ac86c508453062b42d784`.
Se conservó una copia privada y un recibo de procedencia en
`lab/seed/s6b21-research-20261006/`. El ZIP enlazado en la respuesta externa
no estaba disponible en Descargas; los hashes y recuentos de aquel paquete
se tratan como afirmaciones del informe, diferenciadas de las verificaciones
ejecutadas aquí sobre el repositorio. El PDF no entra al buscador.

El primer problema intervenido es la cobertura conjunta de duración y
condiciones. Cuando no había padre, B20 tendía a iniciar con HOLD=0; tener
otra duración legal en la gramática no le daba una oportunidad efectiva.
B21-A obliga a repartir diez oportunidades entre las diez duraciones, en
orden sembrado. No favorece una pareja conocida de duración/guarda.
Después alterna cuatro reparaciones y cuatro exploraciones. Puede aumentar
o reducir duración y sustituir una guarda sin heredar su anclaje.

| Pieza | Implementación y prueba relevante |
|---|---|
| Cobertura | `echo_arc/s6b21_search.py`: diez duraciones, mezcla general/diversidad, soporte para guardas inactivas; control aleatorio y B20 congelado |
| Archivo investigador | `echo_arc/s6b21_archive.py`: conserva hasta 32 hipótesis, pérdidas por caso y linaje; dos hijos por padre; ningún rechazo modifica la política estable |
| Reparación | Usa lecturas propias y contraejemplos medidos; separa duración y linaje; la asociación de una lectura con una pérdida sigue siendo una estimación |
| Datos observables | Entrada JSON exacta guardada por hash; solicitud, respuesta, candidato, padre, consumo, firma y conducta registradas por separado |
| Ejecución | `seed/s6b21.py`: doce casos de cribado, replay completo, auditoría con caché separada, desarrollo amplio y conservación condicionados |
| Revisión independiente | `seed/s6b21_review.py`: extiende el revisor aritmético congelado de B20; reconstruye entradas, primer pase, agenda y hashes sin importar el solver |
| Paquete privado | `seed/s6b21_build.py`: copia de 70 fuentes, excluye documentos/tests/PROBE/controles humanos B20, comprueba fuentes anteriores y espera el cierre válido |
| Observación y documentación | Diario existente `live/journal.jsonl` y `observe.py`; `seed/s6b21_report.py` actualiza el informe privado automáticamente |

El ranking puede aprender de una ganancia rechazada, pero la aceptación
sigue exigiendo al menos dos niveles nuevos y ninguna pérdida individual
de nivel o score. No se presupone que una condición prometedora prediga
todas las consecuencias de cambiar HOLD. Se simula cada política; la
coincidencia de lecturas anteriores solo orienta búsqueda.

La comparación consta de siete recorridos de hasta 18 intentos: un control
B20, tres aleatorios y tres balanceados. Usa cuatro procesos CPU y cero
llamadas al LLM. Esta elección sigue la recomendación de aislar B21-A antes
de cambiar memoria temporal, crédito o neocórtex. Una mejora aquí acreditaría
capacidad de búsqueda; su atribución al LLM necesita la ablación N posterior.

Tras los primeros pases se ejecutan 160 casos de desarrollo amplio y, si
conservan los requisitos, 80 casos protegidos nuevos, siempre con replay y
auditoría independiente. No se sustituye un ganador tras observar un fracaso
en conservación. El techo físico es 16.000 partidas, con cota de implementación
10.548 antes de reutilizaciones exactas y paradas tempranas. La reserva queda
fuera de observación y feedback; no abre el examen final S6.

Se revisaron 191 perfiles históricos de partición, sin coincidencias en las
tuplas de la reserva B21. El recibo conserva la lista y los hashes. La revisión
de declaraciones en fuentes encontró referencias anteriores a 64000 como
presupuesto de partidas, no como el intervalo de semillas 64000–64039.
El alcance de esta comprobación es el inventario registrado, no todos los
datos posibles fuera del laboratorio.

Pasan **69 pruebas**: 29 B21, 22 B20 y 18 B18. Se verifican cobertura sin
padre, reparaciones en ambas direcciones, rechazo de datos protegidos o de
otra base, límite de hijos, ausencia de herramientas de archivos/red en el
buscador, entrada exacta persistente, detección de alteraciones por el auditor,
consumo de presupuesto tras fallos, permiso de reserva ligado a la política
y congelación del primer pase. Una prueba inicial del protocolo falló porque
su doble de medición no había creado el fichero basal que debe leer el
auditor. Se corrigió el fixture, se conservó el log y la batería pasó completa.
No se jugaron partidas para esas pruebas.

Se comprobó además la importación del runtime aislado en un directorio
temporal, con el Python congelado y sin jugar. Las fuentes B18, B19 y B20
conservan sus hashes. El seguimiento y el PDF están fuera del manifiesto
científico; no afectan las decisiones ni permiten reescribir fuentes congeladas.

El prerregistro previo a cualquier partida es
`a4f4c2a21ef6549b6398c09a8aa84e3ab182e8712b32b0d705b4675bda697898`.
Enlaza contrato, configuración, semillas, fuentes, tests, base y revisión de
particiones. Al llegar el cierre B20 se añade su recibo al manifiesto de
ejecución, manteniendo esos hashes intactos.

Los servicios locales son `echoai-s6b21-run` y `echoai-s6b21-report`.
El primero espera B20 y luego encadena las fases autorizadas, deteniéndose
ante una discrepancia o falta de pase. El segundo solo actualiza documentación.
El proceso y sus resultados están en `lab/seed/s6b21-20261006/`; estado en
`status.json`, log en `process.log` y contabilidad en `budget.json` cuando
empiecen las partidas. Son servicios independientes de esta conversación;
la CPU local tiene que estar disponible para que avancen.

Quedan deliberadamente separadas las etapas T/C/R/N/P del informe: memoria
temporal del investigador, crédito diferido, restauración parcial comprobada,
crítica del neocórtex frente a muestreo adicional y nuevas features del actor.
La variante A ya incluye archivo, contraejemplos y replay desde el inicio;
no implementa e-prop ni garantiza restaurar snapshots completos. El decaimiento
entero hacia cero y conservar historia ante RESET interno son requisitos
para las etapas temporales posteriores.

Si B21-A pasa, todavía habrá que demostrar contribución del neocórtex y
descubrimiento desde SEMILLA, completar piloto y campaña y superar B1–B5.
No se marcará S6 verde a partir de un micro de desarrollo.

[Contrato](ECHO45-S6-B21-A-DESIGN.md) ·
[Resultados vivos](ECHO45-S6-B21-A-RESULTS.md) ·
[Pruebas](../lab/kaggle/s6b21-20261006/tests-final.log) ·
[Prerregistro](../lab/kaggle/s6b21-20261006/intent.json).
