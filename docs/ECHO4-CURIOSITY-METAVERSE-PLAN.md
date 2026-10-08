# Plan: E4-CURIOSITY-1 y METAVERSE-1 «vida en un mundo de vóxeles» (PLAN, pedido por Roger 2026-09-24)

No es contrato. Orden previsto: SITUATE-2 → INTEGRATE → RELEASE → **CURIOSITY-1** →
**METAVERSE-1** (último, como siempre).

## E4-CURIOSITY-1 — curiosidad propia

Roger: *«que sean curiosos de por sí; no hace falta tener motivos, aunque también
pueden tenerlos; quizá les interese aprender para hacer algo nuevo».*

- **Motivación intrínseca:** recompensa interna por **progreso de aprendizaje** del
  modelo del mundo propio (T): «estoy mejorando al predecir esto», no la sorpresa
  bruta. Así evita quedarse atrapado en el ruido (el problema de la tele sin señal;
  Schmidhuber, Oudeyer).
- **«¿Qué pasa si…?»:** elegir acciones cuyo resultado aún no predice bien; simularlo
  antes con T cuando pueda (contrafactual) y probarlo después de verdad.
- **Metas propias (autotélicas):** inventarse objetivos («construir una torre»,
  «aprender a curar») y practicar hasta dominarlos, sin que nadie se los dé.
- **Curiosidad social:** «¿qué pasa si daño a otro?». Se permite en simulación. Las
  consecuencias las aprende por sí mismo a través de RELATION (el otro recuerda),
  ROLES (pierde rango) y MAINTAIN (le cuesta). Nada prohibido por regla fija. Todo es
  daño virtual, registrado y documentado.
- **Curiosidad sobre sí mismo:** puede probar modificaciones de **su cuerpo y sus
  estrategias** (parámetros de vuelo, energía, estrategias soñadas), verificadas antes
  con replay como en DREAM. **Nunca** puede modificar el gate, el cortafuegos entre
  hechos y creencias, la parada del operador ni la no destrucción de memoria. Si
  pudiera, se perdería la medición y el control.
- **Examen previsto:** agente curioso frente a no curioso en el mismo mundo y tiempo.
  Se mide qué descubre y aprende de nuevo, y si consigue hacer algo que antes no sabía.
  Control de ruido (debe aburrirse de lo que no se puede aprender).

## METAVERSE-1 ampliado — vóxeles, drones y tiempo real

- Mundo de vóxeles propio y ligero, determinista: poner y quitar bloques, daño y
  curación entre agentes, recursos y energía. Godot solo dibuja.
- Cuerpo de dron simplificado, heredado de lo aprendido en ECHO-3/DRONE-3. **No** PX4
  SITL por agente: cuesta un núcleo por dron.
- **Tiempo real** sincronizado con el reloj del PC (60 s = 1 min). Córtex **raro y
  asíncrono**; el núcleo actúa en tiempo real.
- **Método:** es etología, no examen. Se graba todo (percepciones, acciones, marcas de
  tiempo, semillas) para **reproducir** en modo controlado cualquier episodio
  interesante y auditarlo. Se preregistran los comportamientos buscados antes de
  mirar (cooperación, construcción conjunta, conflicto, curar a otro, roles, engaño).
  Se documenta qué reglas existen, para separar lo emergente de lo programado.
- **Coste estimado:** en el PC local, ~0 €. Con un córtex más rápido: GPU alquilada
  (~250–500 $/mes 24/7) o API (~15–150 $/día con 10 agentes a 1 llamada/min),
  cifras aproximadas por comprobar. Kaggle solo para lotes.

Se mantienen WSP16, CAM sin borrado, el núcleo sin LLM, el cortafuegos y la parada
del operador. Sin afirmaciones de conciencia.
