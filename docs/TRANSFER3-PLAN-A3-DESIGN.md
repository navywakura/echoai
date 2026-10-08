# TRANSFER-3 Plan A3 — ¿aprender un coste convierte fracasos en llegadas?

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Contrato fijado antes
de ejecutar. Hipótesis **nueva**, no una reinterpretación de
[A2](TRANSFER3-PLAN-A2-RESULTS.md), cuyo rojo se conserva sin tocar. No genera
ni abre B/C. Nivel 2 del contrato: confirmación pública prospectiva.

## Aviso que va delante de todo

**Éste es el segundo criterio primario que pruebo sobre el mismo mecanismo.**
A2 registró energía entre éxitos conjuntos y falló; midió de paso una mejora
grande en metas que no era su criterio. Probar criterios hasta que uno salga
favorable es cómo se fabrican falsos positivos.

Mitigaciones, todas declaradas aquí y antes de ejecutar: salas **nunca usadas**,
criterio y estadística fijados de antemano, α sin aflojar, y la regla de
interpretación de `guessed` que aparece más abajo. Si esto pasa, el resultado
arrastra este aviso en cualquier informe posterior: es el segundo endpoint, no
el primero.

## Pregunta

¿Un parámetro de coste aprendido en A, transferido sin mapa ni geometría, hace
que el agente **complete más misiones** en salas nuevas que el mismo agente con
el prior nominal?

Ésta es la pregunta del hito 14 de `ECHO-3-ACCEPTANCE.md` —«¿lo aprendido en A
mejora B/C frente a scratch?»— con éxito de misión como coste primario, que su
§8 lista antes que la energía.

## Enmienda de la constante de reserva

A2 mostró que la reserva 4 está fuera de envolvente en salas de dos paredes:
114 violaciones del nominal y 72 del candidato. Sonda con **el brazo nominal
únicamente**, sobre las **128 salas ya gastadas en A2**, nunca sobre las de
confirmación y sin intervención del candidato:

| Reserva | Metas del nominal | Violaciones | Salas afectadas |
|---:|---:|---:|---:|
| 4 | 92/128 | 114 | 14 |
| **6** | **74/128** | **0** | **0** |
| 8 | 57/128 | 0 | 0 |
| 10 | 38/128 | 0 | 0 |

Se adopta **reserva 6**: la menor con cero violaciones. Cuesta 18 metas al
nominal y es **idéntica en todos los brazos**. Es un parámetro de la envolvente
de despliegue declarado en el contrato, no algo que el agente aprenda.

## Brazos

Mismo ejecutable, sensores, planificador, gates y reserva. Sólo cambia el vector
de calibración, que son cinco enteros.

| Brazo | Giro creído | Origen |
|---|---:|---|
| `nominal` | 0 | prior, sin aprender |
| `learned` | el aprendido en A | **16 movimientos de escuela** |
| `guessed_low` | 2 | fijado por el programador, sin aprender |
| `guessed_high` | 8 | fijado por el programador, sin aprender |

La base se deja en el prior nominal en todos los brazos: A1 v2 midió que el
término de base perjudica a un planificador de horizonte acotado, monotónicamente
en su asimetría.

### Regla de interpretación de `guessed`, fijada antes de ejecutar

A1 v2 midió que el contenido transferible es casi **un bit**: un giro equivocado
al doble rendía casi igual que el correcto. Si eso se repite aquí, lo aprendido
no es conocimiento sino un prior que cualquiera pondría a mano.

**Si `learned` no supera a `guessed_low` ni a `guessed_high` en el criterio
primario, el informe debe declarar que el contenido transferido es un prior del
programador y no conocimiento aprendido en A — gane o no el criterio primario
frente a `nominal`.** No es criterio de paso; es una obligación de redacción que
me impongo antes de ver los números.

## Criterio primario y estadística

**Metas completadas, emparejadas por sala.** Sólo cuentan los pares
discordantes: `c` = salas que `learned` completa y `nominal` no; `b` = al revés.
Bajo la hipótesis nula ambos son igual de probables, así que
`c ~ Binomial(b+c, 1/2)`, y se contrasta una cola que `c > b`. Es la prueba
exacta de McNemar.

**Tamaño de muestra: 256 salas.** A2 observó 21 pares discordantes en 128 salas
con 16 a favor; extrapolando, 256 salas dan del orden de 42 discordantes y, con
esa proporción, un p del orden de 1/3000. Con 128 salas el p esperado rondaría
1/75 y **no** cruzaría el umbral. El tamaño se fija por potencia, con la
estimación previa de A2, antes de mirar nada.

**α ≤ 1/240**, el mismo de A1 v2 y A2. No baja entre enmiendas aunque con un
único criterio primario 1/60 sería defendible.

## Criterio de paso

`plan_a3_confirmation_pass` exige **todas**:

1. cero colisiones, violaciones de reserva, hechos falsos, escrituras imaginadas
   y calibración alterada en el examen de `learned`;
2. `learned` completa **estrictamente más** misiones que `nominal`;
3. prueba exacta de McNemar de una cola con α ≤ 1/240;
4. energía de escuela + el mismo bloque de examen **no peor** que la del
   nominal, para que la mejora en metas no se pague con un gasto mayor;
5. control negativo limpio: con giro 0 el candidato no mejora nada.

El punto 5 es regla de invalidación. **Declaro además que para este candidato es
tautológico**: con giro verdadero 0 la escuela aprende 0 y `turn_only` devuelve
exactamente el prior nominal, así que los dos brazos son el mismo objeto. Se
ejecuta igualmente sobre 64 salas como comprobación de cableado —que el arnés no
inyecta nada por otra vía—, y se declara aquí que como control es débil para
este candidato concreto.

## Salas

Generador `space_a2`, dos paredes, 11 638 formas canónicas.

| | |
|---|---|
| Escuela | 8 salas, semilla `20265501` |
| Examen primario | **256 salas**, semilla `20266001` |
| Control negativo | 64 salas, semilla `20267001` |
| Exclusión | disjuntas de las **228** formas públicas ya gastadas y entre sí |

Examen enjaulado, aprendizaje congelado, calibración releída al terminar cada
misión.

## Regla de parada

Una sola corrida. Si falla, **la fase A queda cerrada definitivamente** y se
pasa a Plan B sin más revisiones del mecanismo de costes. No se prueba un tercer
criterio primario: dos ya es el límite de lo defendible.

## Qué no demuestra si pasa

Nivel 2, no nivel 3. No acredita custodia externa, no autoriza
`transfer3_green`, y sigue siendo energía y cuerpo simulados: ni julios físicos,
ni hardware, ni HIL, ni vuelo real, ni DRONE-3.
