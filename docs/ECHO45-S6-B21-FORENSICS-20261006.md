# B21-A: cierre, descubrimiento y límites de promoción

Revisión privada posterior al cierre del 6 de octubre de 2026. Se leen resultados
y se reconstruye la selección usando las entradas exactas conservadas. No se
ejecutan partidas, no se llama al modelo y no se abren cohortes protegidas.

B21-A terminó como `CLOSED_NO_PROMOTION`, con auditoría y revisión aritmética
válidas: 110 propuestas, 4.212 partidas físicas y cero generaciones LLM.
Las 70 fuentes del manifiesto conservan sus hashes. La reproducción de esta
investigación está en [analyze.py](../lab/seed/s6b21-forensics-20261006/analyze.py)
y sus resultados en [analysis.json](../lab/seed/s6b21-forensics-20261006/analysis.json).

La comprobación recalcula los efectos por partida de los 110 intentos, compara
sus mediciones con replay y auditoría independiente, verifica las entradas
comprimidas utilizadas para reconstruir las oportunidades HOLD=2 y compara
las 18 propuestas del control con C1 de B20: propuestas y efectos coinciden.

## Qué encontró realmente

El segundo intento de `random-821117` generó esta regla:

```text
HOLD = 2
si level <= 1 y pred_error == 0 y world_events <= 8
```

Sobre las 12 partidas de desarrollo del micro subió de 52 a 56 niveles,
sin pérdidas individuales de niveles ni score. El incremento agregado de
score fue 5,064425708100558. Replay y auditoría independiente lo reprodujeron.
Esto constituye un pase del umbral del micro; no una promoción final S6.

| Caso | Niveles base → candidato | Acciones del agente base → candidato |
|---|---:|---:|
| v2 / semilla 18 | 4 → 5 | 2.000 → 1.240 |
| v3 / semilla 28031 | 2 → 5 | 2.000 → 1.821 |
| v3 / semilla 28027 | 5 → 5 | 765 → 765 |
| v3 / semilla 28039 | 5 → 5 | 577 → 577 |

Los dos últimos son los casos donde B18 perdió score. Aquí conservan también
las acciones y el score exactamente. Ya eran desarrollo conocido; no son
prueba de transferencia nueva. El caso A53 (v3/13) no cambia: el +4 no procede
de recuperar su antigua ganancia. Otras tres partidas reducen acciones y
mejoran score conservando sus niveles. Estos niveles pertenecen a mundos
procedurales S6; no son aciertos exactos ni porcentajes oficiales ARC.

La reconstrucción muestra que la guarda ganadora estaba en la biblioteca
ampliada de B20, entre 675 clases observacionales retenidas, sin truncamiento.
No procede de las 64 muestras generales adicionales. Su clase contiene
solo esa guarda en el conjunto reconstruido. Por tanto, este hallazgo no
necesitó ampliar otra vez el lenguaje ni rescatar un representante eliminado.

Una búsqueda aleatoria programada puede ser autónoma. B21 demuestra aquí
descubrimiento automático acotado, sin que se le entregue esa regla ganadora.
No demuestra ventaja del investigador balanceado, del neocórtex, ni el ciclo
de automejora asistida desde SEMILLA que exige S6. La ausencia de LLM no
invalida por sí misma la autonomía de una búsqueda.

## Por qué no se abrió la siguiente fase

El contrato exigía que al menos un recorrido `balanced-*` pasara para abrir
el desarrollo amplio de 160 casos. Solo uno aleatorio pasó. `qualify` y
`follow` aplicaron esa condición, tal como se había prerregistrado.

La regla aleatoria no fue rechazada en las 160 partidas ni en la conservación
nueva de 80: esas fases no se ejecutaron. Su transferencia sigue desconocida.
La condición protegía la atribución de éxito a la intervención balanceada,
pero dejó sin confirmar una mejora útil hallada por un control. Fue una
limitación del diseño del laboratorio. Debe corregirse mediante un contrato
complementario posterior al resultado, sin modificar retroactivamente B21.

## Qué limitó al investigador balanceado

**Cobertura incompleta de las combinaciones.** Las tres semillas balanceadas
ensayaron las diez duraciones, pero la cobertura de duraciones no garantiza
la de parejas duración/guarda. En las cuatro oportunidades balanceadas de
HOLD=2, la guarda ganadora estaba en la biblioteca y ninguna propuesta anterior
había consumido su misma firma observacional. Se eligieron otras guardas:
tres dieron ganancia cero sin pérdidas y una dio −1 con cinco pérdidas.
Esto localiza el fallo en la exploración/selección bajo un presupuesto corto;
no prueba que una selección alternativa vaya a ganar en cualquier semilla.

**La puntuación de reparación no modela la nueva duración.** `repair_score`
cuenta ganancias del padre donde la guarda coincide con consumos efectivos.
No estima la respuesta a cambiar HOLD. Para las pérdidas consulta evidencias
del mismo valor y linaje; un valor no ensayado suele tener carga asociada cero.
Ese cero significa falta de evidencia, no ausencia demostrada de riesgo.
El código lo advierte, pero el ordenamiento aún puede favorecer esa ausencia.

En los seis intentos de reparación de duración, los ocho candidatos de cada
shortlist empatan en ganancia prevista y carga de pérdidas. El desempate
sembrado decide entre ellos. El resultado real fue cuatro ganancias cero,
una −1 y una +1; ninguno pasó. Es evidencia concreta de una señal de ranking
poco informativa para modificar duración, no de un error del juez.

**Una rama cercana no recibió reparación de condiciones.** En
`balanced-821117`, el intento 11 produjo HOLD=4 con +4 y una pérdida de score
en v3/28027. Su único descendiente medido, el intento 13, mantuvo la guarda
y cambió HOLD a 32: desapareció la ganancia. No se probó un descendiente que
conservara HOLD=4 y reparase sus condiciones. La agenda alternada y el reparto
entre familias consumieron las cuatro plazas de reparación de ese recorrido.
No sabemos si tal descendiente habría eliminado la pérdida; no se midió.

La reparación sí tuvo un efecto útil en otra rama del mismo recorrido: el
intento 15 eliminó las cinco pérdidas del intento 1 conservando su +1. Quedó
por debajo del umbral +2. Conservar ramas rechazadas funcionó como soporte de
investigación; aún no produjo una mejora aceptable en los brazos balanceados.

## Comparación con los ensayos anteriores

| Ensayo | Evidencia positiva | Límite observado |
|---|---|---|
| B18 | Híbrido y síntesis: 378 → 383 sin pérdidas en 80 A; auditoría válida | En 40 casos nuevos: 173 → 176, pero pérdidas de score en dos casos |
| B19 | Síntesis alcanza +1 conservador en el micro | 36 propuestas; ningún pase; híbrido +4 con pérdida |
| B20 | El control dirigido confirma capacidad del lenguaje; un control humano conserva +6 en 160 A | Micro de 144 propuestas: ningún pase; no acredita hallazgo autónomo del control humano |
| B21-A | Control aleatorio encuentra +4 conservador; conserva los dos casos conflictivos conocidos; auditado | Balanceado 0/3; ganador sin medir en 160 A ni en 80 nuevos |

B21 tuvo 54 propuestas balanceadas, 38 aleatorias y 18 del control B20.
Un recorrido aleatorio se detuvo tras su segundo intento por primer pase;
los otros completaron 18. Un éxito en tres semillas frente a cero en tres
no establece superioridad estadística del muestreo aleatorio. Los intentos
adaptativos tampoco son 110 observaciones independientes. Los tamaños y
cohortes distintos impiden comparar tasas brutas entre B18–B21.

B21 aporta una mejora conservadora automática en el micro y una localización
más precisa del problema de selección. B18 llegó más lejos en transferencia,
aunque falló conservación. B21 no confirma haber resuelto aquella etapa.

## Qué queda por demostrar y siguiente investigación

Primero conviene congelar el primer ganador aleatorio y someterlo, con recibos
y auditoría independiente, a las 160 partidas amplias y después a conservación
en casos nuevos. Las cohortes anteriores que orientaron este diagnóstico ya
son desarrollo: no deben presentarse como examen ciego. Ese control debe
medirse aunque no gane el balanceado, sin atribuirle éxito a este último.

Para investigar la selección: representar conjuntamente duración y guarda;
distinguir explícitamente evidencia ausente de pérdidas observadas; dar una
reserva limitada de reparación a la mejor rama con ganancia y pérdidas antes
de cambiar de familia. Son hipótesis posteriores a B21, pendientes de otro
contrato y comparación con el control aleatorio a igual presupuesto.

S6 continúa requiriendo descubrimiento y aceptación desde SEMILLA, piloto,
campaña, conservación y examen nuevo de cuatro brazos. B1 exige ≥105 % de
niveles respecto a SEMILLA y score medio no inferior; B2 superar FIJO;
B3 superar SIN FILTRO; B4 retención oficial; B5 auditorías y procedencia.
La auditoría válida del micro no sustituye esas puertas ni prueba conservación
universal. T/C/R/N/P y la ablación del neocórtex siguen sin ejecutar en B21-A.

Fuentes: [contrato B21-A](ECHO45-S6-B21-A-DESIGN.md),
[resultados B21-A](ECHO45-S6-B21-A-RESULTS.md),
[archivo investigador](../echo_arc/s6b21_archive.py),
[pipeline](../seed/s6b21.py), [B18](ECHO45-S6-B18-RESULTS.md),
[B19](ECHO45-S6-B19-RESULTS.md), [B20](ECHO45-S6-B20-RESULTS.md)
y [puertas S6](ECHO45-S6-B14-DESIGN.md).
