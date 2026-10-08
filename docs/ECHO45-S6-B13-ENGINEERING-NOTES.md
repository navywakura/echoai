# Reanudación privada de S6, 3 de octubre de 2026

Al revisar los procesos no había una campaña científica activa. Las mediciones
V3 de los módulos habían terminado. Permanecían un publicador antiguo de
S6-B11 y el visor automático, que consumía aproximadamente un núcleo al recorrer
los históricos. Se detuvo el publicador para mantener la investigación privada
y se cambió el visor a un archivo explícito de la ejecución vigente.

Se completó una reejecución independiente de PROBE2 en una caché nueva: 240
partidas A, cuatro procesos, cero llamadas al modelo. La base reproduce 378
niveles y el digest `4458a4c2…`; el candidato 28 reproduce 383 y `c6bbb046…`,
el 33 reproduce 383 y `1b0f15fa…`. Los tres digests completos coinciden con los
originales. Se recalculó V3 sin pérdidas individuales. El recibo está en
`lab/seed/s6probe2-independent-20261003/audit.json`, con `valid:true`.
No se midió B ni se abrió la reserva. Es confirmación de capacidad de la
gramática; sus soluciones dirigidas permanecen fuera de los prompts autónomos.

B13 implementa selección de objetivo con memoria entre llamadas, devolución
inmediata de cada veredicto, exclusión de valores ya vigentes en las lecturas
observadas y un control auxiliar aleatorio. El objetivo expira al cambiar la
base o agotar tres intentos. Una propuesta que cambia otro operador durante
REFINE se rechaza y consume su llamada. El piloto y la campaña empiezan de
SEMILLA vacía. El código no importa resultados de los supervivientes dentro
de la función que construye las peticiones.

Se reutilizan el ejecutor, la DSL, los registros y los criterios anteriores.
El modelo cambia a Qwen3-4B-Instruct local Q4_K_M, declarado en el contrato;
las comparaciones se realizan dentro de esta condición. Una calibración sin
datos del experimento devolvió JSON correcto en 12,95 s y 36 tokens de entrada.
Ese tiempo corto no estima una llamada con un contexto de desarrollo completo.

Se midió el tamaño de las peticiones con el tokenizador del GGUF. Las dos
peticiones iniciales de ensayo tenían 2633 y 1372 tokens. El caso de prueba
de refinamiento con tres contrastes y todas sus features usa 1711 tokens tras
la compactación numérica sin pérdida. El límite es 3072; no hay corte de texto
ni desplazamiento automático del contexto. Cada llamada conserva entrada,
tokens, gramática, comando, salida y logs. La auditoría vuelve a tokenizar la
entrada y reconstruye peticiones/veredictos usando una caché distinta.

Validación: 17 pruebas nuevas pasan, incluida reconstrucción de una fase con
dobles de prueba y detección de una alteración del recibo. Una ejecución de
regresión de B13/B11/PROBE2 pasó 39 pruebas; la versión final de las 17 nuevas
se verificó tras las últimas correcciones funcionales. La auditoría PROBE2
jugó las 240 partidas reales; los dobles de prueba no cuentan como resultados
científicos. Una comprobación administrativa inicial comparó tuplas en memoria
con listas de JSON y dio un falso fallo; la comparación canónica pasó antes
de iniciar B13. Queda anotado en `validation.json`.

El perfil B13 congela 155 fuentes/datos y el modelo, SHA-256
`e6d3280cc9f82e0d13cb6db969145dca09cc5e5a03a8633da9e8bf7662f477fa`.
El servicio `echoai-s6b13` se inició a las **23:10:08 de Madrid**. Ejecuta
paridad → piloto → auditoría → campaña → auditoría → examen, deteniéndose
si no es elegible o falla el instrumento. Se preservan 36 llamadas de piloto,
60 de campaña, 18 propuestas aleatorias auxiliares y un tope de 64.000 partidas
contando auditorías, repeticiones y reserva. Todos los recibos quedan locales.

El preflight terminó válido a las 23:16:11: SEMILLA reproduce 365 niveles A,
el observador conserva el comportamiento y A/B tienen replay idéntico.
La primera llamada real tardó 444,33 s, con 1372 tokens de entrada. Su propuesta
en el brazo **FIJO** pasó V1–V4: A 365→373 (+8), B 175→176 (+1), sin ninguna
pérdida individual de nivel ni score en ambas particiones. Es un resultado
provisional de una propuesta genérica; no se atribuye a ECHO, no constituye
victoria del piloto y todavía necesita su auditoría independiente. A las 23:31
el brazo ECHO estaba generando su primera propuesta. El neocórtex CPU es un
coste importante: no extrapolar la calibración sintética de 12,95 s al piloto.

S6 continúa abierto. Un proceso iniciado, una prueba unitaria aprobada o un
control dirigido de +5 no acreditan B1–B5. La única condición de cierre sigue
siendo superar simultáneamente esas cinco puertas con auditoría válida.
La duración depende de los programas generados y de la CPU disponible; el
servicio requiere el portátil encendido y sin suspensión para avanzar.

[Contrato](ECHO45-S6-B13-DESIGN.md) · [Resultado actualizado automáticamente](ECHO45-S6-B13-RESULTS.md) ·
[Estado](../lab/seed/s6b13-20261003/status.json).

Actualización del 4 de octubre, 00:05 de Madrid. La primera llamada ECHO del
runtime del sistema agotó los 900 s sin una propuesta completa. Se conservan
el estado BLOCKED, los dos intentos reservados y las 484 partidas programadas;
la condición se cerró como `INCOMPLETE_RUNTIME_REPLACED`. Su resultado FIJO
parcial no se agrega al reinicio ni acredita una victoria de ECHO.

Se compiló una herramienta privada desde llama.cpp b5904, commit
`79e0b68c178656bb0632cb8602d2940b755077f8`, sin reemplazar los binarios del
sistema. El paquete anterior no activaba AVX2/FMA; el nuevo sí. Una entrada
sintética de 1372 tokens obtuvo 22,18 tokens/s de prefill frente a 3,19 en la
entrada real anterior de igual longitud. Cambian los textos y la salida de
calibración está forzada: esa comparación mide rendimiento del instrumento,
no calidad de propuestas. Los 1372 IDs de la petición real anterior coinciden
con el tokenizador nuevo. Pasaron las 22 pruebas de B13 y del reinicio.

La adenda B13-R1 conserva el modelo, las semillas, las peticiones, los límites
de tokens y las puertas científicas. Declara el nuevo runtime y la guardia
temporal de 1800 s; reinicia todos los brazos, las propuestas y las cachés.
El perfil congela 159 fuentes/datos, SHA-256
`806910820323d60c8cd4b821b5a87cec396f90ec967921381403f44b494530b4`.
El servicio `echoai-s6b13-native` arrancó el 3 de octubre a las 23:59:31.
A las 00:05 había completado la base A y su replay y seguía en el preflight.
El observador lee únicamente su diario explícito. S6 continúa pendiente;
la cadena posterior sigue condicionada a los resultados y las auditorías.

[Adenda del reinicio](ECHO45-S6-B13-RUNTIME1.md) ·
[Informe automático vigente](ECHO45-S6-B13-RUNTIME1-RESULTS.md) ·
[Estado vigente](../lab/seed/s6b13-native-20261003/status.json).

El preflight R1 terminó válido a las 00:07:12 del 4 de octubre: 244 partidas
programadas, SEMILLA 365 niveles A, replays A/B exactos y paridad del observador.
La primera llamada del piloto comenzó a las 00:07:46. No hay resultados nuevos
del piloto en este punto; el examen permanece cerrado.

La primera llamada FIJO R1 terminó en 73,74 s, con 1372 tokens y una propuesta
`HOLD=10` bajo `level>=2`. Se comprobó igualdad byte a byte de su petición con
la del runtime anterior, que tardó 444,33 s; las propuestas generadas difieren,
como permite el cambio declarado de motor numérico. El prefill real nuevo
fue 21,94 tokens/s. A las 00:10 se estaba midiendo su efecto en A, todavía sin
veredicto de utilidad. Las 159 fuentes del reinicio seguían intactas.

El piloto terminó el 4 de octubre a las 04:23:03, con las 54 propuestas y las
36 llamadas previstas. ECHO obtuvo 1113 niveles agregados frente a 1125 de
FIJO, con tres mejoras ECHO aceptadas. Perdió los tres pares (373/375,
367/375 y 373/375). `promote:false`; estos resultados son provisionales hasta
la auditoría. Se reservaron y midieron 7844 partidas en el piloto/preflight.

En el paso siguiente apareció un error del lanzador que implementé:
el proxy de subprocess tenía `run`, pero carecía de `STDOUT`. La auditoría
no había jugado ninguna partida. La recuperación se declaró por separado,
conservando las fuentes científicas y el estado BLOCKED original. Las tres
pruebas nuevas pasan, incluido stdout/stderr de un subproceso real.
El recibo `audit-launch-recovery1/prepared.json` tiene SHA-256
`e157c58753ec89f63872be915d8be1ba888c739287e0ce7a027f778f0e03ecdc`.

La auditoría se reanudó como `echoai-s6b13-native-audit` a las 04:44:17.
A las 04:44:45 ya había reejecutado 18 partidas en la caché independiente;
el registro de llamadas sigue en 36. Estimación inicial: tres o cuatro horas,
aproximadamente entre las 08:00 y las 09:00, sujeta al rendimiento de CPU.
Si reproduce el piloto, la condición cerrará `PILOT_NO_PROMOTION`; no se
ejecutarán campaña ni examen con un piloto no elegible. La estimación anterior
de finalizar toda la cadena el 5 de octubre queda retirada para esta condición.
[Recuperación del lanzador](ECHO45-S6-B13-AUDIT-LAUNCH-RECOVERY.md).

El análisis de las peticiones realmente enviadas localizó problemas adicionales:
12/15 llamadas posteriores ECHO y 15/15 FIJO pierden todo el feedback reciente
en la compactación; las seis REFINE forman dos grupos de tres textos idénticos.
Ocho propuestas ECHO repiten comportamientos ya observados. El selector mostró
tres casos sin señal en cuatro peticiones CONTRADICTION y una WAIT. Los niveles
que explican la diferencia se reconciliaron por partida A. El análisis usó
solo archivos existentes y no altera la auditoría; sus hipótesis de reparación
todavía requieren un nuevo experimento.
[Informe forense y cálculo reproducible](ECHO45-S6-B13-PILOT-FORENSICS.md).
