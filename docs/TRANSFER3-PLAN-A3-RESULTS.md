# TRANSFER-3 Plan A3 — lo transferido era un prior del programador; fase A cerrada

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Confirmación en rojo.**
Contrato: [A3](TRANSFER3-PLAN-A3-DESIGN.md), fijado antes de ejecutar, incluido
el aviso de que éste era el **segundo criterio primario** probado sobre el mismo
mecanismo. Una sola corrida. No se generó ni abrió B/C.

## Veredicto

| Criterio | | Valor |
|---|---|---|
| Restricciones duras | sí | reserva 6: **cero** violaciones, colisiones, hechos falsos |
| Más misiones que `nominal` | sí | 159 vs 156 |
| McNemar de una cola α ≤ 1/240 | **no** | 18 ganadas / 15 perdidas · **p = 0,36** |
| Energía no peor | **no** | 32 048 vs 30 984 |
| Control negativo limpio | sí | 0/0, 52/52 |

`plan_a3_confirmation_pass = false`.

La mejora en metas es de tres salas sobre 256, con 18 ganadas y 15 perdidas:
**ruido**, no efecto. El tamaño de muestra se fijó por potencia antes de mirar y
era suficiente para detectar el efecto que A2 sugería; no apareció.

## El resultado que importa

| Brazo | Giro creído | Origen | Metas | Energía | Giros |
|---|---:|---|---:|---:|---:|
| `nominal` | 0 | prior | 156/256 | 30 984 | 2112 |
| `guessed_low` | 2 | **puesto a mano** | 159/256 | 31 976 | 1620 |
| `learned` | 4 | **aprendido en A** | 159/256 | 31 976 | 1620 |
| `guessed_high` | 8 | **puesto a mano** | **161/256** | 31 892 | 1608 |

El brazo que aprendió el valor verdadero es **idéntico misión a misión** al que
lleva un número puesto a mano:

| Comparación | Salas con misión idéntica |
|---|---:|
| `learned` (4, aprendido) vs `guessed_low` (2, a mano) | **256 / 256** |
| `learned` vs `guessed_high` (8, a mano) | 241 / 256 |
| `learned` vs `nominal` (0) | 69 / 256 |

No es que se parezcan: son la misma conducta en **todas** las salas. Y el prior
equivocado al doble —giro 8 donde el verdadero es 4— completa **más** misiones
que el aprendido, 161 contra 159, ganándole 3 pares discordantes a 1.

## La obligación que me impuse antes de ejecutar

El contrato decía: *«si `learned` no supera a `guessed_low` ni a `guessed_high`
en el criterio primario, el informe debe declarar que el contenido transferido
es un prior del programador y no conocimiento aprendido en A — gane o no el
criterio primario».*

No supera a ninguno. **Se declara: lo que Plan A transfiere no es conocimiento
aprendido, es un prior del programador.**

El parámetro se comporta como un **binario**: importa que el giro se crea
distinto de cero, y dentro de eso su valor es casi irrelevante, porque el
desempate del planificador sólo usa el **orden** que induce el coste, no su
magnitud. Cualquier valor de una banda ancha produce el mismo plan. A1 v2 ya lo
había insinuado —un giro equivocado al doble rendía casi igual—; A3 lo mide
sobre 256 salas nuevas y enjauladas, y lo confirma en su forma extrema.

## Lo que no falló

Conviene separarlo, porque el fallo no está donde podría parecer:

- **El aprendizaje funciona.** La calibración se recupera exacta —giro 4— con 16
  movimientos, con cobertura parcial (la acción 2 no se observa ni recta ni
  girando) porque el término es compartido.
- **El transporte funciona.** Cinco enteros, sin mapa, sin geometría, sin Q.
- **El aislamiento funciona.** Jaula real, 17 módulos, cero simulador, grafo de
  importación verificado por AST, calibración releída tras cada misión.
- **El gate funciona**, con la reserva corregida a 6: cero violaciones en las
  1.152 misiones, frente a las 114 y 72 de A2 con reserva 4.

Lo que falla es la **utilidad**: el planificador no puede aprovechar la
precisión que el agente es capaz de adquirir. Aprender bien algo que no cambia
la decisión no es transferencia.

## Razonamiento auditable

- **Hipótesis.** Un parámetro de coste aprendido en A hace completar más
  misiones en salas nuevas.
- **Evidencia.** 159 vs 156 con p = 0,36: nada. Y `learned` ≡ `guessed_low` en
  256/256 salas.
- **Explicación rival.** Que el efecto exista pero la muestra sea corta.
  **Descartada por diseño**: 256 salas se fijaron por potencia sobre el efecto
  que A2 sugería, y una prueba del banco verifica que 32/10 cruzaría el umbral
  mientras 16/5 no.
- **Explicación rival 2.** Que la reserva 6 haya enmascarado el efecto al bajar
  las metas de todos. Posible en magnitud, **no en dirección**: la igualdad
  exacta con un prior a mano no depende de cuántas misiones se completen.
- **Autorrevisión.** Éste fue el segundo criterio primario sobre el mismo
  mecanismo, y lo declaré en la primera línea del contrato. Si hubiera salido
  favorable, ese aviso habría tenido que acompañarlo. Salió desfavorable, así
  que la cuestión es discutible: lo relevante es que la regla estaba escrita
  antes. El control negativo es tautológico para este candidato y lo dije en el
  contrato, así que no aporta la garantía que aporta en A1/A2.
- **Actualización.** Abandono Plan A entero, no una variante. La calibración de
  costes es aprendible, transferible y **inútil** en este dominio, y ahora sé
  por qué: el canal de influencia es un desempate por orden, que no distingue
  magnitudes.
- **Decisión.** Regla de parada aplicada. **Fase A cerrada definitivamente**, sin
  un tercer criterio primario. Siguiente: **Plan B**, calibración del modelo de
  ejecución, con contrato propio.

## Qué hereda Plan B

No se tira nada de la infraestructura: generador de dos paredes con 11 638
formas —quedan más de 11 000 sin usar—, jaula aislada y verificada, adjudicador
externo de reserva, arnés de escuela y examen, y la lección de diseño más
importante de la sesión: **antes de medir un parámetro, comprobar que el
planificador puede usar su precisión y no sólo su signo.** Plan B debe pasar ese
filtro antes de gastar una campaña.

> **Nota posterior (ARCH-1).** La generalización que este informe insinúa
> —que la replanificación paso a paso sea la causa común— fue puesta a
> prueba y **refutada**: el compromiso de plan resultó conductualmente
> inerte. Lo que sigue en pie de Plan A es lo medido aquí, que el canal es
> un desempate por orden y no transmite magnitud. Ver
> [ARCH-1](TRANSFER3-ARCH1-RESULTS.md).

## Verificación

Artefacto: `lab/transfer3/plan-a3-confirmation.json`, hash canónico
`b7a71a077bbd92bd4a8b58e84947f802ee64db2e310a2bed7679332e50c8d988`.
Auditoría completa en proceso nuevo, repitiendo las 1.152 misiones enjauladas:
`replay_valid=true`, exit 0, mismo hash. 19 tests A3 nuevos, todos en verde.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_a3 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.confirm_a3 audit lab/transfer3/plan-a3-confirmation.json
```

TRANSFER-3 sigue en rojo. No hay candidato. Custodia externa intacta y sin
secretos pedidos. ECHO-3 permanece en 13/15.
