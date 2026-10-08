# S6-B4 · contrato de piloto y continuación condicional

2026-09-28. Fijado antes de la primera llamada B4 al modelo y antes de abrir
19000–19059. S6-A/B0/B2/B3 y S5-F/S5-F2 conservan sus fuentes y resultados.
S6-B3 cerró ROJO; H1/H3 S5-F2 cerró VERDE. Ninguna cifra del examen B3 ni del
examen H1/H3 se usa para seleccionar parches. Sus diagnósticos motivan esta
hipótesis; la selección utiliza únicamente A y el filtro protegido B.

## Qué se permite

La base es v5.8 en las cuatro versiones. El brazo local recibe propuestas
JSON de **una sola reparación**: una o dos condiciones observables y un único
parámetro entero dentro de los once límites B3. Hereda todos los demás
controles y conserva v5.8 fuera de la condición. Máximo 32 parches acumulados.
Las funciones temporales propuestas como operadores (orden, conteo, rutas tras
un efecto y preferencia de sondeo) ya están programadas; el modelo elige
cuándo/combinarlas, no genera Python, pesos, neuronas ni un algoritmo general.
La gramática restringe los tokens y el parser rechaza claves extra, valores
fuera de rango y duplicados. El parche inerte y la política vacía deben pasar
paridad de acciones, frames, niveles y modelo con v5.8 antes de cualquier GPU.

Episodios: los registros reales del observador existente aportan antes,
acción ejecutada y después, junto con predicciones, cambios remotos, progreso,
soporte/contradicciones temporales y estado observable. Como máximo tres
transiciones por partida; los objetos se renombran por orden de aparición.
No hay segundo bus de pensamiento. El texto del visor no entra al agente.
Solo semillas de entrenamiento 0–39: sin familia, coordenada absoluta, ID de
juego, solucionador, estados privados ni cohortes reservadas en el prompt.
Los rechazos V3 devuelven dos contraejemplos individuales de A como máximo.
V4 solo comunica que B sufrió regresión; B no se muestra al modelo.
La puntuación numérica calculada con las referencias humanas tampoco aparece
en prompts; en A se informa solamente el booleano de regresión de puntuación.

## Comparación y presupuesto

A = v2/v3, semillas 0–19, rep 0; B = v2/v3, semillas 20–39, rep 0.
40 partidas cada uno, 2000 decisiones, todas las once familias. Sin cambio
de generador ni base. FIJO recibe siempre tres fallos y la misma petición
genérica; ECHO escoge P1 próximo, P2 episodios parecidos por rasgos, P3
generalización del último parche aceptado o P4 diario. Ambos acceden a la
misma clase de evidencia y feedback de su propio historial, mismo Qwen2.5-
Coder-7B revisión `c03e6d358207e414f1eca0bb1891e29f1db0e242`, FP16,
dos T4 gratis, temperatura 0.7, top-p 0.95 y máximo 900 tokens. Las semillas
de muestreo coinciden por ronda. Cuota privada, pago desactivado.

Piloto: seis rondas de **una propuesta por brazo** para local-FIJO/local-ECHO
y dos controles de formato global FIJO/ECHO, 24 respuestas totales más cuatro
calibraciones sin tareas. El control global usa los once defaults completos
de B3, pero el mismo nuevo contexto episódico, modelo y presupuesto; compara
paquetes de formato, no identifica una causa aislada. Todos los brazos usan V1
formato, V2 ejecución y replay de A en pool independiente, V3 ≥2 niveles más
en A y sin pérdida individual de niveles/puntuación, V4 sin pérdida individual
en B. Tolerancia de score 1e-10. Rechazos no modifican la política aceptada.
El desarrollo usa el observador y se comprueba su paridad. Cada cache,
respuesta, petición, uso y veredicto es separable por brazo.

El piloto **autoriza continuación automática** de la campaña únicamente si
ECHO local acepta al menos un parche de utilidad ≥2 niveles A, sin regresiones
individuales en A/B. Si falla, se publica el piloto, no se abre examen y S6
permanece ROJO; el siguiente trabajo será revisar la evidencia u operaciones.
Si pasa, local-FIJO/local-ECHO continúan hasta 30 llamadas cada uno, en rondas
de tres. Los controles de formato se detienen en seis. SEMILLA conserva v5.8.
SIN FILTRO recibe la última política completa propuesta por ECHO local que
pasó V1 y V2; omite V3/V4. Sin nueva llamada al modelo. Nunca se selecciona
una propuesta por el examen.

## Examen, fijado condicionalmente

Se congelan las cuatro políticas antes de abrir 19000–19059, versiones 2/3,
reps 0/1/2, presupuesto 2000: 360 partidas, 1800 niveles por brazo. Validar
los 600 niveles con el solucionador. Sin observador. Repetir en pool y cache
nuevos las 120 partidas rep 0 de cada política distinta; exigir registros
completos idénticos. El archivo de examen se abre una vez y jamás se repite
tras ver resultados. Cualquier error antes de completar se conserva PENDIENTE.
La medición en ocho juegos oficiales **de desarrollo** (tres reps) ocurre
después de congelar las políticas y no influye en selección. El contador de
reinicios automáticos conserva la convención histórica y se audita.

B1: ECHO ≥105 % de niveles de SEMILLA y score medio ≥SEMILLA.
B2: ECHO > FIJO en niveles. B3: ECHO > SIN FILTRO. B4: desarrollo oficial sin
pérdida de niveles ni score frente a SEMILLA. B5: fuentes, diarios,
solucionador, score, decisiones y replays verificables. **VERDE = B1–B5**.
Publicar ROJO si algún criterio falla; PENDIENTE si la evidencia no completa.
No se rebaja umbral ni se cambia cohorte. Un piloto positivo tampoco implica
que S6 esté VERDE ni que ARC-AGI oficial reservado esté resuelto.

[Diagnóstico B3](ECHO45-S6-B4-PLAN.md) · [Resultado B3](ECHO45-S6-B3-RESULTS.md).
