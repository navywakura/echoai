# S6-B8 · aplicabilidad, consecuencias y refinamiento adaptativo

2026-09-29. Contrato previo a medir B8. Orden de Roger: implementar la
propuesta, cerrar S6 si la evidencia lo permite y después continuar 4.5.
Los negativos B5/B6/B7 y sus fuentes permanecen intactos.

## Hipótesis e intervención

B6 produjo ocho propuestas con HOLD nativo; B7 obtuvo una mejora válida,
pero empató con FIJO. B8 mide si elegir episodios por oportunidades observadas
de intervención y refinar con consecuencias reales supera la petición genérica.
El selector y los diagnósticos son algoritmos humanos explícitos, no aprendizaje
autónomo de su propio código. La reparación concreta sigue saliendo del modelo.

Se conserva v5.8, lenguaje B5 y V1–V4. Un diagnóstico calcula sobre estados
realmente visitados cuántas guardas coinciden, cuántos parámetros cambiarían
y dónde hay oportunidad de consumirlos. Son indicios, no una simulación
contrafactual ni prueba de mejora. Todas las propuestas se ejecutan y verifican;
un intento inactivo consume su llamada. No se sustituyen por reparaciones humanas.

El observador existente recoge estado→acción→resultado, esperas sin progreso,
ensayos de reinicio y errores de predicción. No lee estado privado del mundo.
Los resúmenes estructurados se calculan durante la ejecución; el texto de la
mini terminal no vuelve al agente. Solo A tiene observador.

FIJO recibe tres tareas incompletas con petición genérica. ECHO selecciona
casos cercanos a resolver con oportunidades de intervención, prioriza el
parámetro de su mejor mejora rechazada y rota el foco cuando no cambia acciones.
Ambos reciben el mismo lenguaje, diagnósticos, programa actual y sus propios
veredictos previos. No se incluye historia B6/B7 ni controles humanos en prompts.
La diferencia experimental es selección de evidencia y petición, no herramientas
gratuitas adicionales. Todos los pasos, llamadas, tokens y partidas se registran.

## Desarrollo y presupuesto

A: v2/v3, semillas 0–19, 2000 decisiones. B protegida nueva: 24420–24439.
Cada conjunto tiene 40 partidas. B nunca alimenta prompts; solo permite la
señal binaria de rechazo. El contrato conserva +2 niveles A sin pérdida
individual A y ninguna pérdida individual B, en niveles y score (1e-10).
V2 exige replay completo. Fuentes, prompts y políticas se congelan por hashes.

Piloto: tres parejas 615001/615017/615029 desde parche vacío; tres rondas
adaptativas de una propuesta por brazo/pareja. 18 propuestas y dos calibraciones.
Muestreo emparejado, con semilla base +1000×ronda. No se elige un ganador
intermedio ni se detiene por una puntuación favorable. Promoción: al menos una
aceptación ECHO y suma A final estrictamente superior a FIJO. Auditoría completa
en otro proceso y caché de replay propia antes de cualquier campaña.

Campaña condicional: nueva pareja desde parche vacío, seis rondas de cinco
propuestas por brazo, 30 cada uno. Feedback actualizado entre rondas, sin
seleccionar configuraciones por reserva. Piloto y campaña: 78 propuestas y cuatro calibraciones, 82 llamadas en total
(20 del piloto y 62 de la campaña).
Máximo nueve trabajos privados de 300 s, cuatro procesos por pool CPU,
tope conservador 40000 partidas CPU entre desarrollo, replays, auditorías y examen.
Qwen2.5-Coder-7B FP16, revisión c03e6d358207e414f1eca0bb1891e29f1db0e242,
temperatura 0.7, top-p 0.95, máximo 900 tokens, prefill por bloques de 512.
Sin pago. Si falta cuota, queda PENDIENTE; no se acorta el ensayo para aprobar.
Una inferencia incompleta se conserva y detiene; no se reenvía automáticamente.

## Cuatro brazos, examen y cierre

SEMILLA: v5.8 vacío. FIJO/ECHO: solo reparaciones V1–V4. SIN FILTRO acumula
las propuestas ECHO seguras y ejecutables con replay, omitiendo V3/V4,
sin nuevas llamadas. No elimina propuestas por el diagnóstico de inactividad.

Reserva nueva 24500–24559, versiones 2/3, tres repeticiones: 360 partidas y
1800 niveles por brazo. Ni LLM ni observador. Fuentes y políticas congeladas
antes de abrir, solucionador 300 niveles por versión y replay de las 120
partidas rep0 por política distinta. Se miden además los ocho juegos oficiales
de desarrollo, tres repeticiones, sin emplear sus resultados para reparar.

VERDE únicamente con B1–B5 originales: ECHO ≥105% de niveles de SEMILLA y
score ≥SEMILLA; ECHO >FIJO; ECHO >SIN FILTRO; conservación de niveles/score
agregados del desarrollo oficial; auditoría íntegra de fuentes, peticiones,
inferencia, composición, veredictos, solucionador y replays.

Si el piloto falla, cerrar sin abrir reserva. Si el examen falla, ROJO.
Si falta evidencia, PENDIENTE. No se rebajan umbrales ni se reabre un examen.
Este contrato prueba el paquete selector+feedback, no separa causalmente ambos;
las ablaciones por componente requerirán una condición posterior. S6 verde
en juegos sintéticos no acredita mejora del solver ARC-1/2 ni transferencia
oficial ARC-3, que se medirán después mediante comparación congelada.
