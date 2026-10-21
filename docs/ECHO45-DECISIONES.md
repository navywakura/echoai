# ECHO-4.5 · decisiones y argumentación (Nav y Claude, 2026-09-25)

Registro de cómo decidimos entrenar ECHO-4.5, por qué y qué buscamos que sea capaz de hacer.
Contratos que salen de aquí:
- `ECHO45-SEED-DESIGN.md` (aprobado);
- `ECHO45-EGO-MEMORIA1-DESIGN.md` (aprobado; va en paralelo).

## 1. De dónde partimos (medido y auditado)

| Prueba | Resultado | Lectura |
|---|---|---|
| ARC-AGI-3, ECHO solo (16 juegos de examen) | 13 de 112 niveles (11,6 %); azar: 2; puntuación oficial 0,07/100 (corregida el 2026-09-25; antes ponía 1/100) | ECHO gana al azar explorando, pero no entiende la meta |
| ARC-AGI-3, Qwen3-30B + ECHO | 4 niveles, frente a 0 de Qwen solo; los 4 los completó `EXPLORE` | un modelo débil delega, no razona |
| ARC-AGI-3, Opus 5.5 + ECHO (desarrollo, partidas cortadas) | 2 niveles con **jugadas propias**, en 23 y 40 acciones | pista, no resultado: entender la meta es lo decisivo |
| ARC-AGI-2, ECHO solo | 0 de 120 | 17 operaciones fijas no llegan a las soluciones |
| SimpleQA con ECHO | entre un 81 % y un 87 % menos respuestas inventadas en 4 modelos | el cortafuegos funciona donde hay evidencia que comprobar |

## 2. La pregunta de Nav

Nav dudó de que ARC-AGI-2 fuera un banco que ECHO pudiera hacer. Propuso **una versión de ECHO
sin preentrenar, como base, que se pueda clonar en otro sandbox y entrenarse allí**. Entrenar
significa que **aprenda, evolucione y entienda significado abstracto**.

**Argumentación de Claude:**
- ECHO solo no puede hacer ARC-2 tal como está. Como verificador del código de un modelo sí encaja,
  y eso se mide en el examen de ARC-2.
- La idea de Nav es la dirección correcta, y buena parte de lo que pedía un análisis externo que
  pegó Nav ya existía en ECHO:
  - ejecutar programas y devolver los fallos (brazo L+ECHO);
  - un DSL de primitivas (ECHO solo);
  - un modelo del mundo y curiosidad (el agente de ARC-3);
  - el juez simbólico (el cortafuegos).
- **Lo que falta de verdad:** (1) aprender abstracciones nuevas y (2) inferir la meta en ARC-3.
- **Del «100 %» del análisis externo, desconfiar:** nadie lo tiene y el texto no lo demuestra.

## 3. Decisiones

1. **ECHO-SEED** (`echoai/seed/`):
   - una semilla que al nacer solo sabe 44 familias de primitivas;
   - sandboxes clonables, cada una con su biblioteca, un diario encadenado por hashes y su curva
     de aprendizaje;
   - un gimnasio con las 1009 tareas de entrenamiento de ARC-1 y ARC-2, de las que 201 quedan
     reservadas para medir la transferencia;
   - las evaluaciones, selladas por código.
2. **Cómo aprende:**
   - **despierto:** busca programas, y solo es HECHO lo que reproduce todos los ejemplos;
   - **sueño:** lo que se repite en tareas distintas se convierte en **concepto nuevo**.

   Es la misma idea que DREAM: el modelo propone y el núcleo verifica contra lo vivido.
3. **«Entender significado abstracto», definido para poder medirlo:** un concepto aprendido en unas
   tareas que resuelve tareas que la sandbox **no ha visto nunca**.
4. **Requisitos de ECHO-4.5, de Nav:**
   - **R1 (ARC-1) y R2 (ARC-2):** superar el 0 % sin modelo de lenguaje y **superar a la semilla
     sin entrenar**, midiendo las dos en el mismo examen;
   - **R3 (ARC-3):** **al menos el 20 % de los 112 niveles**;
   - **R4:** auditoría completa.
5. **Métrica de R3:** Nav eligió el **% de niveles** (opción a), no la puntuación oficial
   (opción b). Hoy estamos en 11,6 %, así que el 20–25 % exige casi doblarlo. La puntuación oficial
   se publica siempre, sin umbral.
6. **Por qué 112 niveles:**
   - de los 25 juegos públicos, 8 se usaron para desarrollar y 1 (ls20) se vio en la prueba
     inicial;
   - quedan 16 limpios, con 112 niveles.

   Para compararse con otros se publicarán **tres números**:
   - el % de niveles en el examen limpio;
   - la puntuación oficial en esos 16 juegos;
   - si Nav lo aprueba, una partida en el modo oficial de ARC Prize, tras comprobar cómo funciona
     su tabla.
7. **No se promete el 100 %** en ningún banco. Si ECHO-4.5 supera el 25 % se sube el listón; si
   no llega al 20 %, es rojo y se publica.

## 4. El diagnóstico que ordena el trabajo

- **Rejillas:**
  - el vocabulario solo sabe transformar la rejilla entera, y ARC habla de **objetos**;
  - los programas son cadenas lineales, sin «para cada objeto», sin condiciones y sin parámetros
    sacados de la entrada;
  - no hay intuición sobre qué probar primero.

  El sueño **no puede comprimir soluciones que el vocabulario no alcanza**. Por eso primero se
  amplía el vocabulario y después se aprende.
- **Juegos:**
  - el estado es una huella de píxeles, así que casi cada fotograma es «nuevo» y no hay
    transferencia entre niveles;
  - ECHO no infiere la meta.

  La pista de Opus (23 y 40 acciones) dice que **entender la meta** es la pieza que falta.
- **Conclusión:** el 20 % de ARC-3 depende de ver el juego como **objetos** e **inferir metas**.
  ARC-1 > 0 es lo más fácil y ARC-2 > 0, lo más duro, porque está diseñado contra la búsqueda de
  programas.

## 5. Roadmap acordado

| Fase | Qué | Por qué |
|---|---|---|
| S0 | semilla, sandboxes, gimnasio, despierto/sueño | base (en marcha) |
| S1 | objetos en rejillas: seleccionar, transformar cada objeto, construir, parámetros sacados de la entrada | lo que piden la mayoría de tareas |
| S3 | juegos como objetos, con reglas de acción verificadas a nivel de objeto | menos estados, transferencia entre niveles |
| S4 | inferir la meta al completar un nivel, planificar hacia ella y confirmarla o refutarla | la pieza que separa el 11 % del 20–25 % |
| S5 | ARC3-GYM: simulador propio de juegos por turnos | solo hay 8 juegos de desarrollo y sin él se sobreajusta |
| S2 | conceptos con parámetros, intuición por frecuencias (enteros), evolución entre clones | afinar el aprendizaje cuando ya hay vocabulario |
| S6 | córtex opcional (de pago, con orden de Nav): el modelo propone y ECHO verifica | solo si el examen de ARC-2 demuestra que aporta |

Orden: **S1 → S3 → S4 → S5 → S2 → examen**. Los objetos sirven a la vez para las rejillas y para
los juegos. **Riesgos declarados:**
- ARC-2 > 0 sin modelo puede no salir;
- que la inferencia de metas generalice con pocos juegos;
- tiempo de CPU.

## 6. Lo que esperamos que ECHO-4.5 sea capaz de hacer

Estas son las capacidades que buscamos:
- ver el mundo como objetos;
- aprender conceptos por sí mismo y reutilizarlos en problemas nuevos;
- deducir para qué sirve un juego y planificar hacia esa meta con pocas acciones;
- no dar nada por cierto que no haya comprobado.

**Si sale verde:** sería la primera evidencia medida y auditada de que un sistema pequeño, en una
CPU normal y sin preentrenamiento masivo, **adquiere abstracciones por su cuenta y las traslada a
situaciones nuevas**, en un banco hecho para que memorizar no sirva. No significaría que «entienda»
como una persona ni que sea una inteligencia general.

## 7. El yo: identificarse, saber dónde está y con quién trata

**Pregunta de Nav:** cómo demostrar que ECHO se identifica a sí mismo en una simulación, que sabe
que es un programa en un sistema y que interactúa con humanos (los módulos EGO).

**Argumentación de Claude:** con pruebas funcionales a ciegas, nunca preguntándole «¿eres
consciente?».
- una prueba del espejo entre agentes idénticos;
- descubrir **con pruebas** que el mundo es simulado (reinicios idénticos, tiempo distinto del
  reloj real) y decir «no lo sé» si no bastan, con una grabación real como control;
- distinguir a ciegas humanos de programas guionizados;
- coherencia al pausar, clonar y reanudar.

Base ya verde: BOUNDARY, SITUATE-1/2 y CONTINUITY. Si sale verde, sería un **modelo de sí mismo
funcional y verificado**, que se comprueba en lugar de solo declararse.

## 8. Conciencia, memorias y la necesidad de documentar

**Pregunta de Nav:** qué podría demostrar la conciencia y la experiencia subjetiva. ¿Que ECHO anote
recuerdos que le hagan recordar que él es él, como las memorias que moldean el ego humano?

**Argumentación de Claude:**
- Nada demuestra la experiencia subjetiva **desde fuera**, en ninguna IA. Lo serio es medir
  **indicadores** que las teorías científicas de la conciencia asocian con ella, y hablar de
  grados de plausibilidad, nunca de prueba.
- Las memorias formativas **sí** se pueden medir, si **causan** la conducta: quitarlas debe cambiar
  la conducta y quitar otras al azar, no.
- Clones con historias distintas deberían acabar con yoes distintos.

**Corrección de Nav, aceptada:** la escritura humana nació **por necesidad de documentar**. Si
ECHO desarrolla esa necesidad porque tendrá que demostrar algo en el futuro, aprenderá que registrar
y aprender importa. Sus recuerdos deben guardar **cómo reaccionó**: si un agente le mintió y eso le
hizo tardar más, esa acción queda con valencia negativa. Con lo positivo y lo negativo (yin y yang)
se forma un ego real.

**Decisión: EGO-MEMORIA-1**, aprobado el 2026-09-25, en paralelo a ECHO-4.5 y en CPU:
- **el mundo:** una aldea de agentes, algunos mentirosos; olvido real entre episodios; escribir
  cuesta; reclamaciones futuras que solo se ganan con pruebas del diario;
- **los recuerdos:** hechos (qué pasó, qué comprobó, qué costó), valencia entera (+/−) y el cambio
  de conducta. La interpretación sobre otro agente queda como hipótesis;
- **las pruebas (M1–M6):**
  - surge la necesidad de documentar, frente a un mundo control donde no sirve;
  - documentar le da ventaja;
  - borrar una memoria formativa cambia su conducta y borrar una al azar, no;
  - dos clones de la misma semilla, uno en un mundo honesto y otro en uno engañoso, acaban con
    yoes distintos;
  - aprender se vuelve valioso;
  - la auditoría cuadra.

**Si sale verde:** un **yo narrativo funcional**, formado por su propia historia y comprobable desde
fuera. **No demuestra conciencia ni experiencia subjetiva**, y se dirá así siempre.

## 9. Principios que no cambian

- Cortafuegos: una hipótesis nunca se escribe como hecho.
- Valencias y estados en enteros; nada de coma flotante en el paso rápido.
- Contrato y umbrales antes del examen; los rojos se publican.
- Nunca se usa AGI como objetivo ni se afirma conciencia.
- Todo lo de ECHO-4.5 y EGO-MEMORIA-1 corre en CPU, a 0 $. Lo de pago requiere la orden de Nav.
