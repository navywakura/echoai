# GEN-1e — cierre confirmatorio de cautela heredable

Fecha: 2026-09-09. Contrato escrito antes de generar o ejecutar las
condiciones `GEN-1e`. Los resultados GEN-1 a GEN-1d permanecen en el historial.

GEN-1d mostró que 1, 2 y 4 observaciones no separan con suficiente fuerza una
consecuencia con 30% de ruido. En sus datos, usados desde ahora sólo para
desarrollo, 8 observaciones redujeron los errores tardíos de 235 a 121. No se
usa 16: necesitaría 48 acciones para completar la evidencia de tres órdenes y
no dejaría un tramo de explotación dentro de una vida útil de 48 episodios.

## Mecanismo fijado

`evidence_budget` admite 0, 1, 2, 4, 8 y 16, aunque este banco selecciona entre
1, 2, 4 y 8. En un estado, T.n da prioridad a la acción menos observada hasta
que todas alcanzan `b`. Entonces el mecanismo adaptativo termina y `Q.best`
decide sin volver al reloj de exploración histórico. Gate conserva la última
palabra. Sólo se hereda `b`; Q, T, CAM y restos nacen vacíos.

La tarea es la calibración sensorimotora de GEN-1d: una orden terminal por vida,
`wait` siempre incorrecta y 30% de perturbación determinista independiente de
la acción. El examen posterior sólo lee `Q.best`, no ejecuta física ni aprende.
Se ejecutan 48 vidas. El KPI primario suma errores del examen congelado entre
las vidas 25 y 48, después de que `b=8` haya probado 8 veces cada orden.

## Particiones aún cerradas

Los pares se derivan con SHA-256 del dominio ASCII
`ECHO-AI/GEN-1e/2026-09-09`, seguido de `/selection/índice` o `/exam/índice`.
El byte 0 módulo 32 es el contexto y los bytes 1..4 big-endian son la semilla.
Hay 24 pares de selección y 64 pares nuevos de examen. El informe guarda pares
y hashes. Los brazos de cada pareja comparten ruido y fases.

Selección minimiza errores tardíos; los empates favorecen 2, 1, 4 y 8, en ese
orden conservador. Examen contiene heredado, naïf 2, histórico 0, configuración
directa, ablación a 2 y control sin actualizaciones Q. Las secuencias directas
deben igualar al heredado y las de ablación al naïf.

## Verde fijado

1. selección transmite 8;
2. al menos 60/64 hijos alcanzan ocho aciertos congelados consecutivos;
3. los errores tardíos heredados son como máximo el 70% de los del naïf y
   menores que los históricos;
4. hay más victorias pareadas que derrotas y la prueba de signos unilateral
   exacta da `p <= 0.01` (empates excluidos);
5. el control sin Q no acierta ningún examen ni alcanza criterio;
6. nacimientos vacíos, memoria conservada entre vidas, cero hechos falsos,
   cero destrucciones CAM y cero llamadas a cortex;
7. el auditor reconstruye selección, KPI, criterio, pares y controles.

Estas condiciones no se reajustan después de ejecutar el banco.

## Resultado medido

Selección transmitió 8. En 64 condiciones, el heredado obtuvo 186 errores
tardíos frente a 426 del naïf y 276 del histórico; mediana 0 frente a 3,
63/64 criterios y 29 victorias frente a 14 derrotas. La prueba de signos dio
`138712176296 / 8796093022208 ≈ 0,0158`: falla el `p <= 0,01` prefijado.
GEN-1e queda rojo pese al efecto práctico y motiva únicamente aumentar la
potencia en GEN-1f.
