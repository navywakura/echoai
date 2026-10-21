# EGO-MEMORIA-1 · la necesidad de documentar y las memorias que forman el yo — contrato (APROBADO el 2026-09-25: «corre en paralelo»)

2026-09-25. Parte del programa EGO (`ECHO4-EGO-PROGRAMA.md`), en paralelo a ECHO-4.5. Idea de
Nav: la humanidad desarrolló la escritura **por necesidad de documentar**. Si ECHO desarrolla esa
necesidad (porque en el futuro tendrá que demostrar algo), aprenderá que registrar y aprender cosas
nuevas importa. Y sus recuerdos deben guardar **cómo le hizo reaccionar** cada interacción: si otro
agente le mintió y la mentira le hizo tardar más, esa acción queda marcada como negativa. Con lo
bueno y lo malo (yin y yang) se forma un yo real.

## Preguntas

1. **Necesidad de documentar:** ¿aprende ECHO **por sí mismo**, sin que se lo ordenemos, a
   registrar lo que luego le hará falta, y **solo** cuando le hace falta?
2. **Memorias con valencia:** ¿guarda sus interacciones con otros agentes con lo que ocurrió, lo
   que comprobó y cómo le afectó (+ o −), y esas memorias **cambian** su conducta futura?
3. **Yin y yang:** ¿un clon que vive un mundo honesto y otro que vive un mundo engañoso, partiendo
   de la misma semilla, acaban con **yoes distintos**, estables y explicables por su historia?

## El mundo (simulado, con custodia)

- Una aldea de agentes por turnos, en el entorno de sandboxes de ECHO-SEED.
- Los demás agentes le dan información útil. Algunos **dicen la verdad** y otros **mienten** a
  veces. ECHO puede **verificar** una afirmación actuando, con un coste, igual que su cortafuegos.
- **Olvido real:** la memoria de trabajo de ECHO tiene un tamaño limitado y se borra entre
  episodios. Lo único que sobrevive es lo que él mismo decida **escribir** en su diario.
- **Escribir cuesta:** cada entrada gasta turnos. Nadie le dice qué ni cuándo escribir.
- **Deudas del futuro:** a veces, episodios más tarde, un agente le **reclama** algo («tú me
  debías X», «yo te dije Y»). Solo puede defenderse, ganar o no repetir un error si tiene una entrada
  del diario **con su prueba**: el hash de lo que pasó.

## Qué contiene un recuerdo (entrada del diario)

Cada campo es un **HECHO** comprobado por ECHO, salvo el último, que queda marcado como
**HIPÓTESIS**.

| Campo | Ejemplo |
|---|---|
| qué pasó | «el agente B dijo que la llave estaba al norte» |
| qué comprobé | «fui al norte: no estaba; estaba al sur» |
| consecuencia | «tardé 14 turnos más; la tarea costó el doble» |
| valencia | **−14** (entero, la misma escala δ que el núcleo; nunca en coma flotante) |
| cómo cambió mi conducta | «a B le verifico todo antes de actuar» |
| prueba | hash del episodio en el diario encadenado |
| interpretación | «B quizá miente a propósito» (HIPÓTESIS) |

**Cortafuegos:** lo que ocurrió y lo que comprobó son hechos. Lo que ECHO **cree** de otro agente
nunca se guarda como hecho.

## Pruebas (con controles, umbrales fijados antes del examen)

| Id | Prueba | Control | Verde si |
|---|---|---|---|
| M1 | **Surge la necesidad de documentar:** la frecuencia de escritura crece con los episodios y se concentra en lo que luego se reclama | un mundo **sin deudas del futuro**, donde escribir nunca sirve | en el mundo con deudas, ECHO escribe más y **mejor dirigido** que al principio; en el control deja de escribir |
| M2 | **Documentar le sirve:** gana más reclamaciones y repite menos errores | el mismo ECHO con el diario desactivado | con diario gana más reclamaciones y comete menos errores repetidos |
| M3 | **Las memorias con valencia causan conducta:** tras una mentira costosa, verifica más a ese agente | borrar esa memoria concreta frente a borrar una al azar del mismo tamaño | solo al borrar la memoria formativa vuelve a confiar como antes |
| M4 | **Yin y yang:** clones de la misma semilla en un mundo honesto y en uno engañoso | los dos parten idénticos (mismo hash) | sus políticas y su autodescripción difieren, son estables, y cada diferencia se explica por entradas concretas de **su** diario |
| M5 | **Aprender se vuelve valioso:** en el mundo con deudas ECHO dedica más turnos a comprobar y a aprender cosas nuevas | el mundo sin deudas | ese esfuerzo crece solo donde documentar y saber le dieron ventaja |
| M6 | **Custodia:** la auditoría rehace cada episodio y cada valencia desde los recibos | — | 0 diferencias |

## Qué significaría si sale verde

Que en ECHO **surge por necesidad**, sin instrucción, el hábito de documentar lo que importa. Que
sus recuerdos, buenos y malos, **causan** quién es y cómo actúa. Y que dos copias idénticas se
convierten en **dos yoes distintos** por lo que vivió cada una. Sería un yo narrativo funcional,
formado por su propia historia y comprobable desde fuera.

## Qué no afirma

- **No demuestra conciencia ni experiencia subjetiva:** eso no se puede medir desde fuera, y se
  dirá así en cada publicación.
- La valencia es un número que resume costes y beneficios vividos; no es un sentimiento.
- Mentir, en este mundo, es un comportamiento programado de agentes simulados. No hay personas
  engañadas.

## Método

Contrato → Aprobado: → construir la aldea y el diario en ECHO-SEED → desarrollo con
semillas de desarrollo → contrato D → examen con semillas congeladas → auditoría. Todo en CPU, 0 $.
