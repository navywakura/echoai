# ECHO-4.5 · H1/H3: memoria temporal, v5.8

2026-09-27. Desarrollo autorizado por Nav. Este documento se escribe antes
de medir la implementación. No abre un examen ni modifica S5-E/S6 cerrados.

## Funciones

- **H1, orden:** recordar entradas a objetos observados, proponer una relación
  A → B cuando esa secuencia precede a un cambio remoto y volver a probarla.
  Se conserva el tipo de objeto; las posiciones se buscan de nuevo en cada nivel.
- **H3, conteo:** distinguir entrar de permanecer sobre un objeto, contar las
  entradas por instancia e intento y proponer un umbral a partir del primer
  efecto observado. No introducir el número tres como respuesta del agente.

Los cambios remotos y las secuencias son evidencia de hipótesis, no una prueba
automática de causalidad. Se registra apoyo en intentos/niveles independientes,
predicciones incumplidas y límites de observación. Un reinicio borra el estado
episódico, pero conserva hipótesis aprendidas; otro nivel también borra posiciones.

## Integración y límites

Nueva clase v5.8 en archivos propios, heredando v5.7. `agent.py`, `runner.py`,
el generador y los contratos anteriores conservan sus bytes. Un adaptador usa
el runner original con una fábrica privada, sin modificar su registro global.

El actor recibe solo frames, acciones disponibles y resultados del runner.
No recibe familia, semilla del mundo, solucionador, estado oculto ni contraseña
de ningún mundo. No usa LLM ni añade neuronas, bus o importaciones del núcleo.

Primera integración limitada a juegos de movimiento con un cuerpo rectangular
identificado, reglas motoras observadas y marcadores estáticos de tamaño
compatible. Clics, teclas de modo/copia y empuje siguen su controlador anterior.
La exploración temporal prueba entradas repetidas y pares ordenados, con memoria
y búsquedas acotadas. Los umbrales y reglas se infieren, no se leen del simulador.

Las decisiones se exportan mediante el observador existente y se muestran en
la mini terminal. Sus textos no vuelven al actor. Trazar añade tiempo: todas
las comparaciones de desarrollo usan presupuesto de decisiones, sin deadline.

## Comprobaciones y medición prevista

1. Tests stdlib de orden, reentradas, umbrales diferentes, reset, separación de
   instancias y evidencia contradictoria. Nunca contar una permanencia como entrada.
2. Tests ARC con entorno reducido controlado: orden invertido, conteos distintos
   de tres, frames con contador oculto, límites de observación y reset/nivel.
3. Comparación en **gym-train 0–39**, versiones v2/v3, presupuesto 2000, reps
   0/1/2. Depuración solo en entrenamiento; resultados por familia y costes.
4. Ablaciones sin orden, sin conteo y sin ambos módulos; paridad de acciones y
   frames de la última con v5.7, y paridad del observador con/sin exportación.
5. Medición sobre los ocho juegos oficiales de desarrollo existentes, presupuesto
   2000 y reps 0/1/2. No se usan para ajustar la implementación después de medir.
6. Verificar hashes de todas las fuentes del freeze S6-B2, trazas completas,
   acciones, reinicios automáticos y resultados reproducibles.

Se considera **implementación comprobada en desarrollo** si los tests pasan,
H1 y H3 mejoran frente a v5.7 en entrenamiento, H2/H4 y gym v2 no pierden
niveles agregados, y se declaran las ablaciones y cualquier regresión de coste
o desarrollo oficial. Esto no es un VERDE científico de un examen reservado.
Una caída se publica y se corrige en entrenamiento antes de una nueva evaluación.

Queda pendiente un contrato de examen nuevo con fuentes congeladas, cohortes
reservadas y criterios fijados antes de abrir resultados. Construir H1/H3 no
cierra S6 ni demuestra por sí solo mejora en ARC-AGI-1/2/3.
