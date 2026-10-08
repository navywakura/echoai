# ECHO-4.5 · qué hacen H1 y H3

2026-09-27. Implementación v5.8, sobre el agente ARC v5.7.

## H1: recordar el orden

Dos visitas a los mismos objetos pueden tener resultados distintos:
**A → B** puede abrir una puerta y **B → A** no. El fotograma de B no tiene
por qué mostrar que antes se pasó por A.

`OrderMemory` guarda una secuencia breve de entradas observadas. Si un par
ordenado precede a la desaparición de un obstáculo remoto, lo propone como
hipótesis. El controlador prueba pares en ambos órdenes y reutiliza los que
tienen más apoyo que contradicciones. El apoyo se cuenta en episodios
distintos, no por repetir una afirmación dentro de un mismo intento.

En otro nivel conserva los tipos de objetos observados y busca sus posiciones
en el nuevo fotograma. El color es el tipo usado en esta primera integración;
no hay un significado universal de «interruptor» asignado a un color.

## H3: contar entradas

Un objeto puede requerir varias activaciones aunque su aspecto no cambie.
`CountMemory` cuenta **entradas por instancia e intento**. Permanecer encima,
chocar contra una pared o pulsar sin moverse no añade una entrada. El
controlador puede salir y volver a entrar deliberadamente.

Cuando observa un efecto, propone el número de entradas que lo precedió.
No contiene la respuesta «tres». Solo aprende un umbral si el episodio tiene
cobertura completa y las entradas no están confundidas con otros tipos o
instancias. Las observaciones incompletas no certifican un umbral. Si una
predicción falla, conserva la contradicción y puede dejar de usar esa regla.

Al reiniciar borra el contador y la ocupación actuales, conservando los
umbrales aprendidos. Al cambiar de nivel también borra las posiciones.

## Cómo se usan

`Arc3EchoV58` identifica su cuerpo y aprende las teclas con v5.7. Cuando hay
marcadores compatibles, busca rutas que lleguen realmente al objeto, prueba
orden/reentradas y comprueba cambios en los fotogramas. Excluye el movimiento
del cuerpo y la barra temporal al buscar efectos remotos. Tras un efecto,
explora primero objetos todavía no visitados: una hipótesis antigua de meta
no debe devolverlo indefinidamente al interruptor que acaba de usar.

Las reglas son hipótesis de comportamiento. Repetir una correlación aporta
evidencia, pero no demuestra causalidad general. El programa de exploración
está diseñado por nosotros; los pares y umbrales usados se adquieren mediante
interacciones. No es entrenamiento de pesos neuronales.

El actor recibe solo fotogramas, acciones disponibles y resultados del runner.
Los dos módulos no consultan el simulador, la familia o el solucionador, y no
usan ningún modelo de lenguaje. La integración conserva las fuentes congeladas
de v5.7/S5-E/S6 y usa una fábrica privada con el runner original.

## Ejecutar y observar

Desde `echoai/`, abrir el visor y ejecutar desarrollo:

```sh
python3 observe.py --launch
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m echo_arc.observe gym --agent v5.8 --seeds 0 4 5 10 --budget 600
```

El visor muestra entradas, orden, umbrales, apoyo, contradicciones y la prueba
que se ejecuta. Solo exporta campos ya calculados y nunca devuelve su texto
al actor. El registro original del núcleo continúa usando `thought.jsonl`.

Comparación reproducible de entrenamiento, con directorio de salida nuevo:

```sh
lab/arc3/ARC-AGI-3-Agents/.venv/bin/python -m echo_arc.temporal_bench gym --agents v5.7 v5.8 --versions 2 3 --reps 0 1 2 --budget 2000 --workers 4 --out lab/observability/h1h3-training-nueva
```

El adaptador ofrece `v5.8-noorder`, `v5.8-nocount` y `v5.8-nomemory`.
Sin conteo conserva ocupación y visitas para explorar después de un efecto,
pero elimina aprendizaje de umbrales y pruebas de repetición. Sin ambos
módulos las acciones y fotogramas coinciden con v5.7; solo cambia el informe
para declarar que las memorias están apagadas.

## Límites

- Primera percepción: cuerpo rectangular, marcadores estáticos de tamaño
  compatible y reglas motoras observadas. Clics, modo/copia y empuje conservan
  sus controladores anteriores. El módulo solo emite teclas presentes en las
  acciones disponibles; excluye las teclas virtuales aprendidas de clics.
- Memoria acotada: 16 entradas recientes, 64 pares, 64 instancias por intento
  y hasta 64 tipos con 64 umbrales por tipo; contador saturado a 255,
  ocho marcadores del controlador y búsquedas de
  hasta 4000 estados. Se proponen nuevas pruebas de repetición para instancias
  con menos de ocho entradas observadas; otras rutas pueden volver a visitarlas.
- Reutilizar un tipo por color presupone consistencia dentro del juego.
  No se ha demostrado transferencia entre juegos con otra semántica visual.
- El controlador distingue contextos temporales, pero no reescribe la tabla
  histórica T de v5.7 para convertirla en un modelo temporal completo.
- Trazar añade tiempo. Las comparaciones usan presupuesto de decisiones,
  sin límite de reloj. La fórmula de puntuación del gimnasio usa el contador
  histórico que excluye reinicios automáticos; las trazas los conservan.

[Contrato de desarrollo](ECHO45-H1-H3-DESIGN.md) ·
[Resultados y límites de la medición](ECHO45-H1-H3-RESULTS.md) ·
[Observabilidad](ECHO45-OBSERVABILITY.md).
