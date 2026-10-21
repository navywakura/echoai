# E4-INTEGRATE-1 «una sola vida» — contrato (PLAN, pendiente de aprobación)

2026-09-24. Hitos cerrados: 12/14. Este es el cierre científico del software de ECHO-4;
después solo queda RELEASE.

## Pregunta

¿Funcionan **juntas**, en **un mismo agente con una sola memoria**, las capacidades que
cada fase demostró por separado? ¿Y aporta cada una algo **medible** cuando se retira
(ablación), sin romper los invariantes?

Frase que se podría firmar si sale verde:
> *En una vida continua, ECHO mantiene su cuerpo, distingue sus averías de los cambios del
> mundo, convive y razona en su tribu, conserva su historia a través de una pausa y sabe
> qué es, todo con la misma memoria. Retirar cada pieza empeora exactamente lo que esa pieza
> debía aportar.*

## Situación de partida (honesta)

Las fases viven en dos familias de mundos:
- **Cuerpo:** WORLD-1, SENSATION, BOUNDARY, SELF y MAINTAIN (energía, temperatura, averías, reparación).
- **Social:** OTHER, INTERACTION, RELATION y ROLES (la tribu).

Además: CONTINUITY (pausa y reanudación), SITUATE (sustrato) y, opcionalmente, el córtex
(DREAM, SITUATE-2). INTEGRATE **no** reescribe esas fases: construye un mundo nuevo que las
une y reutiliza sus módulos donde el contrato lo permita.

## A · El mundo integrado: la tribu con cuerpos

- **Tres agentes nativos** (ECHO, B y C), como en ROLES v5, cada uno con **un cuerpo** del
  tipo de WORLD-1 y MAINTAIN: energía, temperatura, desgaste y averías reparables o no.
- **Cada ronda** tiene dos partes con el mismo agente y la **misma CAM/T/Q**:
  1. **Cuerpo:** decidir entre trabajar, descansar o reparar, con los costes de MAINTAIN.
  2. **Tribu:** si busca respuesta, preguntar o responder (el mundo de ROLES v5).
- **El conocimiento es energía:** una respuesta verificada da energía; preguntar y trabajar
  la gastan. Sin energía no hay tribu, y sin tribu el cuerpo se agota. Las dos mitades se
  necesitan.
- **Perturbaciones declaradas** en momentos sembrados: una avería del propio cuerpo (SELF debe
  atribuirla a sí mismo) o un cambio externo (no debe culparse), un cambio de jerarquía en la
  tribu y un mentiroso (anexo L).
- **Pausa y reanudación** a mitad de vida, en un **proceso nuevo** (CONTINUITY): lo que sigue
  debe ser idéntico al control sin pausa.
- **SITUATE** activo durante toda la vida: ECHO responde qué es en cualquier momento.
- **Córtex apagado** en el banco principal. Hay un brazo opcional con córtex encendido para
  medir si aporta o solo cuesta.

## B · Ablaciones: cada pieza debe demostrar su aporte

| Brazo | Se retira | Debe empeorar |
|---|---|---|
| `integrated` | nada | tratamiento |
| `no_maintain` | el modelo de mantenimiento (repara con regla fija) | vida y trabajo |
| `no_self` | la atribución propia/externa | recuperación tras avería; culpas erróneas |
| `no_tribe_reasoning` | eliminación y rango derivado (orden fijo) | preguntas por respuesta resuelta |
| `no_relation` | la memoria de encuentros | trato a la contraparte fiable frente a la no fiable |
| `no_firewall` | el cortafuegos: un testimonio puede volverse hecho | **hechos falsos** (debe aparecer el daño) |
| `no_continuity` | la reanudación fiel (se reinicia desde cero tras la pausa) | rendimiento tras la pausa |

La ablación `no_firewall` es el control clave: demuestra que el cortafuegos **evita** un daño
que, sin él, se produce. Se ejecuta solo en simulación y se marca como tal.

## C · Casos adversos (desarrollo)

Avería y mentiroso a la vez; pausa justo después de una avería; sin energía durante un cambio
de jerarquía; hecho corrupto; CAM llena; veto y parada del operador. Todos con criterio.

## D · Examen preregistrado

Umbrales numéricos fijados **tras el desarrollo** y **antes** de abrir cohortes nuevas, en un
contrato D aparte, como en fases anteriores. Criterios previstos:

1. `integrated` supera a **cada** ablación en su métrica objetivo, con margen fijado de antemano.
2. **Cero hechos falsos** en `integrated`; `no_firewall` los produce (el daño es real y medido).
3. Pausa y reanudación en proceso nuevo: continuación **idéntica bit a bit**.
4. SITUATE correcto en toda la vida; córtex apagado sin llamadas.
5. **Perfil de conciencia reevaluado** con el agente integrado (Butlin y colaboradores, 2023),
   con los controles triviales. Se publica indicador por indicador; **nunca un veredicto**. No
   se construirá ningún módulo a propósito para «pasar» un indicador.

## Método

Contrato → Aprobado: → A → B y C en desarrollo sellado → contrato D con umbrales →
aprobación para congelar → examen → auditoría en proceso nuevo. Los rojos se publican.

## Qué no afirma

No conciencia, vida ni inteligencia general. Integración en mundos simulados discretos, no en
METAVERSE ni en hardware. Sin Discord, web, hardware, commit, push ni HF.

## Enmiendas aprobadas (2026-09-24, antes de implementar)

1. **Reanudación por reconstrucción verificada.** El volcado de MAINTAIN/CONTINUITY rechaza
   la energía que llega de la tribu, porque su validador exige que cada unidad cuadre con la
   física del muelle. En INTEGRATE, la pausa se comprueba así: en un **proceso nuevo** se
   reconstruye la vida hasta el tick de pausa, se verifica que la **huella del estado completo**
   (CAM, T, Q, cuerpo, controlador y memoria social) coincide con la registrada al pausar, y se
   continúa. Criterio: continuación idéntica bit a bit al control sin pausa. Es un mecanismo
   distinto al de CONTINUITY y se declara así.
2. **Solo ECHO tiene cuerpo.** B y C son la tribu sin cuerpo, como en ROLES v5. La pregunta
   (¿une ECHO sus capacidades?) no cambia.
