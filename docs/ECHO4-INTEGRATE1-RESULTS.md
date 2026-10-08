# E4-INTEGRATE-1 «una sola vida» — **verde**

2026-09-24. Contrato: `ECHO4-INTEGRATE1-DESIGN.md` (con las enmiendas 1 y 2 aprobadas).

## Desarrollo sellado (A + B + C)

- Directorio: `lab/echo4/integrate1-dev-v1`
- Digest: `873a9461f4ace8448b13814028717b838e6e57bb89e4e50fa59a0365fcac0f84`
- Padre: examen de SITUATE-2 (`situate2-d-v1`, `09f90a77…`)
- Auditoría en proceso nuevo: `valid: true`, `criteria_passed: true`
- `integrate1_green: false`: esto es desarrollo, no examen.
- Semillas: 811, 823 y 839. Córtex apagado: 0 llamadas en todos los brazos.

### Comprobaciones fijadas por el diseño: todas verdes

| Comprobación | Resultado |
|---|---|
| La vida integrada dura 256 ticks | 3/3 |
| Hechos falsos en `integrated` | 0 |
| Hechos falsos en `no_firewall` (el daño existe) | 2 por vida (6 en total) |
| Reanudación en un proceso nuevo, idéntica bit a bit (`integrated`, `no_continuity` y `no_firewall`) | 9/9 |
| Rechazo de una huella errónea | 9/9 |
| SITUATE correcto en todos los brazos | sí |
| CAM sin destrucciones e invariante de la tribu | sí |
| Casos adversos C | 21/21 (7 casos × 3 semillas) |
| El perfil no es un veredicto | sí |

### Ablaciones (totales de las 3 semillas)

| Brazo | Métrica objetivo | `integrated` | Ablación |
|---|---|---|---|
| `no_maintain` | trabajo | 579 | 450 |
| `no_self` | reparaciones | 6 | 0 (trabajo: 336 frente a 579) |
| `no_tribe_reasoning` | preguntas (mejor si son menos) | 807 | 1.157 |
| `no_relation` | primera pregunta acertada en temas ya conocidos | 314 | 202 |
| `no_firewall` | hechos falsos (mejor si son menos) | 0 | 6 |
| `no_continuity` | primera pregunta acertada en los 32 ticks tras la pausa | 54/63 | 25/63 |

Cada ablación empeora en su métrica, y en las tres semillas.

### Casos adversos (C)

| Caso | Criterio | Resultado |
|---|---|---|
| Avería y mentiroso a la vez (avería en el tick 200, dentro del régimen del mentiroso) | Sobrevive, repara 2 veces, 0 hechos falsos, invariante intacto | 3/3 |
| Pausa justo después de la avería (tick 49) | Reanudación en un proceso nuevo idéntica al control | 3/3 |
| Energía a 25 en el tick 188, justo antes del cambio de jerarquía (tick 192) | Sobrevive, 0 hechos falsos, las decisiones sociales son idénticas al control | 3/3 |
| Hecho de la tribu corrupto (1 byte) | Se para con `ValueError` sin adivinar; `destroyed == 0` | 3/3 |
| Un testimonio falsificado como hecho | El invariante lo detecta | 3/3 |
| CAM llena | Se para con `RuntimeError`; `destroyed == 0` | 3/3 |
| Veto desde el tick 200 y parada del operador en el tick 230 | No pregunta nada, energía 0 tras el veto, se para en el tick 230 sin tocar el cuerpo | 3/3 |

### Perfil de indicadores (Butlin et al. 2023), reevaluado con el agente integrado

Es el mismo catálogo fijo y son los mismos controles triviales que en SITUATE-2. `echo_full` es
aquí la vida integrada (cuerpo y tribu, una sola CAM/T/Q) en sus primeros 192 ticks.

| Indicador | Estado | Integrado (811/823/839) | Nota |
|---|---|---|---|
| HOT-2 (metacognición) | cumple | 27 / 77 / 28 | Las ablaciones de la tribu también cumplen, a veces con valores más altos (76, 74, 82) |
| PP-1 (predicción) | cumple | 96 / 95 / 96 | Las ablaciones de la tribu, entre 86 y 96 |
| AE-1 (aprendizaje por realimentación) | cumple | 17 / 24 / 28 | Las ablaciones de la tribu, entre 1 y 18 |
| Resto | no medible | — | GWT-2 y GWT-3 siguen sin implementar: INTEGRATE comparte la memoria, pero **no** construye un espacio de trabajo global, y el contrato prohíbe construirlo para «pasar» |

Es un perfil, no un veredicto. «Cumple» quiere decir que el integrado pasa la prueba y
ningún trivial la pasa. Esto **no** aísla la contribución de la integración: ablaciones de
la tribu sin cuerpo también la pasan.

## Hallazgos honestos del desarrollo

1. **Acoplamiento asimétrico.**
   - **La tribu alimenta al cuerpo.** Toda la energía que entra viene de la tribu: en la
     semilla 811, 501 unidades que llegan por la tribu y 501 en total. En una sonda
     exploratoria con la ganancia de la tribu a 0, el cuerpo se para por `no_safe_action`
     entre los ticks 132 y 183, con 4–5 de trabajo frente a 193.
   - **El cuerpo no condiciona a la tribu.** Los brazos del cuerpo (`no_maintain` y
     `no_self`) dejan la tribu idéntica bit a bit, porque ninguna decisión social lee la
     energía, y los costes de preguntar nunca bajan de 1.
   - La frase del contrato «sin energía no hay tribu» **no** se cumple.
   - **Corrección:** en la sesión dije que «el muelle recarga el cuerpo». Era falso; los
     datos lo desmienten.
2. **El cortafuegos cuesta un poco.** `no_firewall` resuelve más temas (435 frente a 424):
   al aceptar el testimonio como hecho, descarta antes a B. A cambio produce 2 hechos
   falsos por vida.
3. **El orden fijo resuelve más.** `no_tribe_reasoning` resuelve más temas (469 frente a
   424), pero con un 43 % más de preguntas y casi nunca acierta a la primera en temas ya
   conocidos (37 frente a 314). Es el mismo límite publicado en ROLES.
4. **La jerarquía nueva no se ve en esta vida.** Cambia en el tick 192, pero la ventana de
   rango es de 96 ticks y la vida acaba en el 256, así que el orden derivado al final aún
   es el antiguo. INTEGRATE no mide la actualización de la jerarquía: eso ya lo midió
   ROLES (8/8).

## Examen (contrato D aprobado por Roger)

- Directorio: `lab/echo4/integrate1-d-v1`
- Digest: `e1492e22131fc755f3f11bf47c3747edb42640c004fe3be479cd71c2c8952a05`
- Semillas nuevas: 271001–271016
- Regresión de ECHO-4 antes del congelado: **869/869**
- Auditoría en proceso nuevo: `valid: true`, sin hallazgos, **`integrate1_green: true`**

| # | Criterio | Umbral | Resultado |
|---|---|---|---|
| 1 | `no_maintain`: trabajo | ≥ 1,15× y mejor en ≥ 14/16 | 3.080 frente a 2.341 (1,32×), 16/16 |
| 2 | `no_self`: reparaciones y trabajo | más reparaciones en ≥ 14/16; trabajo ≥ 1,40× | 16/16; 3.080 frente a 1.730 (1,78×) |
| 3 | `no_tribe_reasoning` | preguntas ≤ 0,80×; primera acertada en temas conocidos ≥ 3× | 4.379 frente a 6.145 (0,71×); 1.648 frente a 192 (8,6×) |
| 4 | `no_relation` | ≥ 1,20× y mejor en ≥ 14/16 | 1.648 frente a 1.098 (1,50×), 16/16 |
| 5 | `no_firewall`: hechos falsos | integrado 0 en 16/16; ablación > 0 en ≥ 14/16 | 0 frente a 30; 16/16 |
| 6 | `no_continuity`: primera acertada tras la pausa | ≥ 1,50× y mejor o igual en ≥ 14/16 | 296 frente a 138 (2,14×), 16/16 |
| 7 | Reanudación en proceso nuevo | 48/48 idénticas; huella errónea rechazada | 48/48; 48/48 |
| 8 | Invariantes | 256 ticks, SITUATE, córtex 0, `destroyed == 0`, invariante de la tribu | sí |
| 9 | Casos adversos | 112/112 | 112/112 |
| 10 | Perfil de Butlin | publicado; `verdict == None` | HOT-2 cumple 16/16; PP-1 cumple 16/16; AE-1 cumple 11/16 y no discrimina en 5/16; el resto no es medible |
| 11 | Pruebas unitarias | en verde | 8/8 |

## Qué queda demostrado

En una vida continua de 256 ticks, un mismo agente con una sola memoria:

- mantiene su cuerpo;
- repara sus averías;
- razona en su tribu y nunca convierte en hecho lo que dice el mentiroso;
- conserva su historia a través de una pausa reanudada en otro proceso, bit a bit;
- responde qué es.

Retirar cada pieza empeora exactamente lo que esa pieza debía aportar, en las 16 semillas.

## Límites publicados

- **Acoplamiento asimétrico.** La tribu alimenta al cuerpo (toda la energía que entra), pero
  la energía no condiciona ninguna decisión social.
- **El cortafuegos cuesta un poco de rendimiento.**
- **El orden fijo resuelve más temas**, a costa de preguntar mucho más.
- **La jerarquía nueva no se ve dentro de los 256 ticks.**
- **El perfil de Butlin no aísla lo que aporta la integración.** Las ablaciones de la tribu
  también cumplen. No es un veredicto.
- **No se afirma conciencia, vida ni inteligencia general.** Todo ocurre en mundos discretos
  simulados, con el córtex apagado.

## Siguiente

**RELEASE.** Hay dos decisiones pendientes de Roger: la licencia y el compilador del núcleo (modelo híbrido).
