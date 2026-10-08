# S6-B16 — refinamiento secuencial y ganancias locales

Condición privada nueva, 4 de octubre de 2026. B15 concluyó a las 18:12 Madrid
con 12 propuestas y 1280 partidas ejecutadas: ninguna pasó V3 en A. El mejor
resultado agregado fue 381 frente a 378, con regresiones en tres partidas.
Se conserva su cierre MICRO_NO_PROMOTION. La reconstrucción independiente de
registros verificó los 174 archivos congelados, las respuestas del modelo,
la tokenización, los resultados por partida, el presupuesto y los replays.
No fue una nueva ejecución de juegos: así se declara en su recibo.

El enlace operador/gramática funcionó: seis propuestas restringidas de HOLD;
las seis no restringidas eligieron otros controles. El resumen numérico por
sí solo no produjo una mejora sin pérdidas. El microensayo factorial anterior
usó intentos independientes: no probó el refinamiento de un rechazo con feedback.

Se identificaron dos pérdidas de información. El comparador elegía por índice
una mejora de score en una partida ya resuelta y relegaba ganancias de niveles
de +4 y +1. El selector de refinamiento exigía ganancia agregada positiva; una
propuesta con +5 niveles locales y −9 en otros casos nunca se refinaba. La
hipótesis nueva es que conservar esas oportunidades y sus contraejemplos permite
acotar la regla. La ganancia local no es aceptación ni evidencia de conservación.

B16 introduce estos cambios:

1. El feedback calcula niveles ganados y perdidos por separado. Entre los dos
   primeros contrastes conserva la mayor ganancia local de niveles y una pérdida,
   si existen. Una mejora exclusiva de score no desplaza esa ganancia de niveles.
   El conjunto completo de 80 resultados sigue determinando V3 sin cambios.
2. ECHO puede refinar una propuesta propia V3/V4 de la base actual si ganó
   niveles en alguna partida, aunque el total sea negativo. Se prioriza la mayor
   ganancia local, después menos niveles perdidos y menos partidas perjudicadas.
   Mantiene el máximo de tres descendientes por objetivo y las pausas de familia.
   Una oportunidad local recibe una reparación acotada antes de explorar un
   operador aún no probado. FIJO conserva su calendario cíclico de B15.
3. Los contrastes muestran nombres de features y diferencias exactas entre
   observaciones emparejadas. El objetivo se muestra también como JSON explícito
   separado del programa aceptado. Las constantes compartidas entre casos se
   codifican una vez sin perder valores. Todas las variantes de contexto conservan
   los dos signos del objetivo, el último recibo y el objetivo completo. No se
   atribuye causalidad al primer punto en que difieren las acciones.
4. Se crea el diario antes de lanzar el visor, corrigiendo la carrera observada
   al arrancar B15. Esta corrección del visor no altera la decisión del agente.

No se añaden primitivas, guardas nuevas ni soluciones humanas. Las correcciones
B15 de operador, aplicabilidad, contabilidad, crédito por base y diversidad se
conservan. Se reutilizan ejecución, V1–V4, B1–B5 y presupuestos por petición.
NEXUS-0 y las fuentes de B15 permanecen intactos. No se publica en web ni GitHub.

Microensayo secuencial antes del piloto:

| Elemento | Condición congelada |
| --- | --- |
| Base | Política de 378 niveles aceptada en B14, con su recibo inicial propio |
| Datos | Las mismas 80 A; base y replay deben igualar íntegramente B14 |
| Brazos | `previous`: controlador/feedback B15; `updated`: B16 |
| Semillas emparejadas | 740101, 740117, 740129; semilla de llamada = semilla + ronda×1000 |
| Rondas | Cuatro intentos por brazo y semilla, 24 llamadas en total |
| Primer intento | Misma petición B15 en ambos brazos, mismo muestreo; no recibe ningún intento del micro B15 |
| Siguientes intentos | Solo el historial propio de cada brazo y sus contrastes medidos |
| Medición | Cada propuesta válida, 80 A + replay completo; inválidos V1 consumen llamada y no se remuestrean |
| Tope | 4000 partidas nuevas y 24 llamadas; la caché puede reducir las ejecuciones físicas |
| Política durante el micro | Base fija; una propuesta que pasa A se marca A_ONLY_PASS, nunca aceptada ni integrada sin B |
| Puerta | Al menos una propuesta `updated` con ≥2 niveles agregados nuevos, cero pérdidas individuales de niveles/score y replay idéntico |

No se detienen selectivamente los brazos tras su primer éxito: se conservan los
24 intentos y sus costes. No se exige que este pequeño micro pruebe superioridad
estadística: n=3 semillas y cuatro intentos no bastan para una afirmación general.
La ventaja frente a FIJO deberá demostrarse en el piloto y después en el examen.
Un resultado negativo del micro cierra la condición; no abre fases posteriores.
Un fallo de replay, origen o custodia detiene el instrumento y conserva artefactos.

Tras la puerta del micro, SEMILLA, FIJO, ECHO y RANDOM comienzan el piloto desde
la semilla original y sin historial de calibración. ECHO no recibe propuestas
del micro, resultados de PROBE2 ni guardas seleccionadas manualmente. La caché
primaria puede reutilizar políticas idénticas bajo este perfil; la auditoría
del piloto y de campaña usa otro proceso y caché independiente.

Piloto: seis propuestas por semilla, semillas 750101, 750117 y 750129. Dos brazos
con LLM, 36 llamadas, más 18 propuestas RANDOM uniformes dentro del operador
fijo. Para promover: ECHO > FIJO en total, al menos dos victorias pareadas de
tres, ninguna derrota y alguna mejora aceptada. A continuación se reconstruyen
los 54 veredictos incluso si el piloto es negativo.

Campaña: 30 propuestas por brazo, semilla 760101, 60 llamadas. Debe superar
FIJO, aceptar mejoras y pasar la reconstrucción independiente. SIN FILTRO
acumula las mismas propuestas ECHO seguras y ejecutables sin consultar V3/V4.

Particiones: A sigue con versiones 2/3 y semillas 0–39, 80 partidas. B usa semillas
29620–29639, versiones 2/3, 40 partidas. Examen nuevo 29700–29759, dos versiones
y tres repeticiones, 360 partidas por brazo más replays y conservación oficial
del protocolo. B y examen permanecen fuera de los prompts y cerrados durante
el microensayo. Ningún resultado de estas particiones se usa para diseñar B16.

V1 mantiene sintaxis y límites; la repetición exacta conserva V2; V3 exige ≥2
niveles agregados adicionales y ninguna pérdida individual en A; V4 conserva
individualmente B. La existencia de ganancias locales nunca reduce V3 ni V4.
B1 exige al menos +5% de niveles frente a SEMILLA y no menor score medio; B2
superar FIJO; B3 superar SIN FILTRO; B4 conservar habilidades; B5 auditoría válida.
Solo las cinco puertas del examen completas permiten declarar S6 verde.

Mismo Qwen3-4B-Instruct-2507 Q4_K_M local en CPU, binarios nativos y pesos
congelados de B15, 4 hilos y 4 procesos de juegos. Contexto 4096, entrada ≤3072,
salida ≤160, temperatura 0.6, top-k 40 y top-p 0.95. Presupuesto total: 120
llamadas (24+36+60), 64000 partidas, sin API de pago. Las etapas son secuenciales.

Preparación: tests → `python -m seed.s6b16_qualification` →
`python -m seed.s6b16 prepare` → `python -m seed.s6b16 follow`.
El último comando encadena micro → preflight → piloto → auditoría → campaña →
auditoría → examen. Sus fuentes quedan congeladas antes de medir o consultar al
modelo. La cualificación usa registros existentes y tokenización, sin inferencias
ni partidas nuevas. Las estimaciones temporales se documentan fuera del contrato.

Límites: el diseño se ha informado con A y resultados negativos B15. El micro
demuestra como máximo capacidad de reparación en ese desarrollo. Las semillas
de muestreo distintas no hacen nuevos los juegos A. Persisten restricciones
del lenguaje, sesgos del modelo y posibles regresiones protegidas; se miden,
no se dan por resueltos al implementar el controlador.
