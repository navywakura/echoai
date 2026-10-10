# ECHO-4.5 → ECHO-5: decisión de continuidad

9 de octubre de 2026, revisión a las 14:15 Europe/Madrid. Decisión del
propietario: terminar B24, cerrar la etapa ECHO-4.5 con su resultado real y
retomar la investigación S6 después de completar ECHO-5.5. Este documento
registra la dirección; no declara cerrada la versión ni aprobado S6.

B24-R1 continúa con su contrato y sus fuentes congeladas. La consulta de
Kaggle devuelve `COMPLETE` para el segmento v1; el recibo científico conserva
`CHECKPOINT_READY`. El gestor local está en `WAITING_GPU_QUOTA`, con 3.719,135
segundos disponibles, por debajo de su mínimo de 10.800. La renovación
anunciada es el 10 de octubre a las 02:00 de Madrid. Los servicios
`echoai-s6b24-r1-manager` y `echoai-s6b24-r1-live` están activos. El ordenador
debe permanecer despierto y conectado para gestionar nuevas continuaciones;
no se garantiza que el ensayo termine mañana. El gestor recoge los recibos
finales, pero no publica una release ni declara S6 verde automáticamente.

Al terminar se revisarán cierre, custodia y auditoría de B24. Se mantiene la
medición ARC pendiente ya acordada; el lote completo de ARC-1/2 no se ha
ejecutado y la calibración conocida dio 0/16 en cada corpus. El alcance final
de 4.5 distinguirá capacidades verificadas, resultados negativos, pruebas no
realizadas y cierre de ingeniería. Un fallo de instrumento se documentará
como tal, sin convertirlo en un resultado científico negativo. No se rebajan
los criterios históricos ni se convierte el cierre de etapa en un pase S6.

La robótica tiene una base anterior a ECHO-4. La revisión de
[ECHO-3](ECHO-3-ACCEPTANCE.md) registra catorce hitos software certificados.
[DRONE-3](DRONE3-RESULTS.md) integró percepción, evidencia, composición,
energía, supervisión y objetivos enviados a PX4 dentro de Gazebo: B y C
obtuvieron 12/12 cada uno. PX4 conserva estabilización y failsafes. El tramo
SITL está verde; HIL y jaula física siguen pendientes. Recuperar esta cadena
y comprobar su compatibilidad con el núcleo vigente será parte de ECHO-5;
no se presume que todos los módulos de 4.5 ya estén integrados en ella.

4.5 aporta capacidades adicionales documentadas, con alcance acotado:

- [Memoria 3E](ECHO45-EGO-MEMORIA3-RESULTS.md): criterios M1–M5 en 16/16
  semillas nuevas y reconstrucción exacta M6, en la aldea declarada.
- [V3](ECHO45-RELATIONAL-V3-RESULTS.md): composición 32/32 frente a 0/32
  sin refinamiento; vistas 160/192 → 192/192; política de memoria con
  19,21 % de ahorro en la batería equilibrada de 64 tareas. Son contrastes
  internos de 4.5, no una comparación global 4.0 contra 4.5.
- [Memoria temporal H1/H3](ECHO45-H1-H3-EXAM2-RESULTS.md): 1.537/1.800
  niveles frente a 1.239/1.800 en ARC3-GYM sintético, sin regresiones
  individuales en ese contrato. No es una puntuación oficial ARC.
- [Inventario de evidencia](ECHO45-CLOSURE-EVIDENCE-20261009.md): límites
  de transferencia y de integración. La guía de 500k son posiciones
  asociativas uint8; no son 500k neuronas LIF ni pesos de un LLM.

El objetivo de ECHO-5 es consolidar un núcleo reutilizable para robótica y
para trabajo con herramientas y lenguaje. Antes de añadir subsistemas se
inventariarán imports, interfaces, dependencias y pruebas reproducibles.
Se separarán runtime vigente, adaptadores, evaluadores y experimentos
históricos, preservando recibos, fuentes y referencias. No se moverán fuentes
activas de B24 ni se borrarán versiones antiguas necesarias para reproducir
resultados. El proyecto legacy `echo-discord` mantiene su congelación.

La GUI web local propuesta será una vista de decisiones observables. Reusará
`nexus0/thought.py`, TALK-1 y los diarios descritos en
[observabilidad](ECHO45-OBSERVABILITY.md), sin crear otro thought-bus. Su
primera versión debería mostrar estado del entorno, observaciones, hipótesis
registradas, acción y veto, consecuencias, recuerdos consultados y coste.
Deberá distinguir histórico, ejecución activa, espera y fallo de lectura.

El neocórtex podrá redactar resúmenes breves de esos eventos con referencias
a sus IDs y con autoría del modelo explícita. Su explicación es una
interpretación de la traza, no una lectura literal del pensamiento interno
ni una prueba causal por sí sola. Ante datos ausentes mostrará desconocido.
El visor funcionará sin LLM; el texto explicativo no se devolverá a la
política ni modificará CAM, Q, T o el verificador. La GUI sigue propuesta,
sin implementación en esta revisión. Las metáforas «cerebro reptiliano» y
«neocórtex» describen roles; no certifican equivalencia neurobiológica.

La nueva investigación de S6 se programará después de 5.5 bajo otro contrato,
con referencias congeladas de 4.5. Para atribuir una mejora se compararán
memoria privada/compartida, uno/varios agentes, muestreo independiente/
competición, planificación con/sin simulación y el investigador inicial/
evolucionado. Se empezará por ablaciones acotadas y después se estudiarán
interacciones prometedoras; añadir todo a la vez no permite saber qué ayudó.
Se contarán llamadas, tokens, simulaciones, tiempo y coste de aprender o
seleccionar investigadores. La confirmación usará tareas nuevas y medirá
conservación; los casos que ya orientaron el diseño no recuperan condición
ciega. Un pase futuro no cambia los rojos históricos de S6 en 4.5.

La publicación en Hugging Face queda pendiente de decisión. Recomendación:
conservar 4.0 como MVP publicado y preparar 4.5 como release de software de
investigación con código, estados aprendidos necesarios, instrucciones y
resultados. Si se publica también allí, describir con precisión esos
artefactos y la procedencia del neocórtex; no presentarlos como nuevos pesos
de un LLM entrenado por ECHO. Esta revisión no sube archivos ni crea releases.
