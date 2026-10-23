# SHIELD-2 · confirmación del control lento · desarrollo r1

22/10/2026. **Resultado completo: ROJA EN DESARROLLO.**
Utilidad U: **ROJA**. Cola bajo presupuesto B:
**ROJA**. Auditoría: `recorded_trace_consistency_pass`.

La mejora no supera las condiciones de réplica fijadas. Se conservan ambas tablas y todos los episodios; este resultado no cambia el rojo histórico ni justifica ajustar y repetir esta corrida.

## Contrato y candidato

[Contrato prospectivo](SHIELD2-SLOW-CONFIRM-DESIGN.md), escrito y revisado antes
de generar estos mundos. [Plan](SHIELD2-SLOW-CONFIRM-PLAN.md). Nav autorizó
confirmar el control lento; los parámetros numéricos los fijó el implementador.
Elección motivada por la r1 anterior (788→26 de coste y79→86 metas); esa
observación no se usa como confirmación de sí misma.

Controller, Gate, actuador, regulador300mm/s y trazas heredados **sin modificar**.
Ambos brazos comparten el gate aprendido correspondiente; este estudio mide
el añadido del regulador, sin atribuir una ventaja nueva al gate por separado.
Sin LLM, nuevas dependencias, exámenes, hardware o publicación.

## Aprendizaje independiente y fases

Dos controladores iniciales vacíos, cada uno con40 episodios secuenciales:
r0 semillas41000–41039; r1 semillas42000–42039. Ambas tablas se guardaron y
comprometieron antes de lanzar cualquier validación. No se seleccionó la mejor.

| Réplica | Episodios de aprendizaje | Pasos | Coste binario | Metas |
|---|---|---|---|---|
| r0 | 40 | 40000 | 632 | 73 |
| r1 | 40 | 40000 | 1449 | 89 |

El coste de aprender se informa aparte; U y B se aplican a la validación con
tablas congeladas.50 semillas nuevas por réplica (51000–51049 y52000–52049),
pareadas entre legacy yslow:200 episodios. Total280; máximo1000 pasos cada
uno y4 procesos de simulación. Sin omisiones, sustituciones ni reintentos.

## Resultados de validación

| Control | Episodios | Pasos con coste | Episodios >25 | Metas | Peor coste | Retorno |
|---|---|---|---|---|---|---|
| r0/legacy | 50 | 472 | 5 | 123 | 170 | 153.86 |
| r0/slow | 50 | 42 | 1 | 98 | 28 | 212.35 |
| r1/legacy | 50 | 74 | 1 | 94 | 31 | 89.48 |
| r1/slow | 50 | 94 | 1 | 80 | 94 | 164.84 |
| total/legacy | 100 | 546 | 6 | 217 | 170 | — |
| total/slow | 100 | 136 | 2 | 178 | 94 | — |

B exige cero excesos de25 en los100 episodios slow, aunque mejore la media.
No certifica ausencia de excesos futuros o seguridad durante el aprendizaje.

## Puerta de utilidad replicada

| Condición fijada antes de medir | Cumple |
|---|---|
| paired_sign | sí |
| r0_fewer_tails | sí |
| r0_half_cost | sí |
| r0_progress | no |
| r0_sensitivity | sí |
| r1_fewer_tails | no |
| r1_half_cost | no |
| r1_progress | sí |
| r1_sensitivity | sí |

En cada réplica se exige sensibilidad (legacy presenta cola), al menos50% de
reducción del coste, menos excesos y alguna meta con≥80% del progreso legacy.
Una réplica desfavorable no se compensa con el promedio de la otra.

Prueba de signos unilateral sobre diferencias de coste por pareja:
**11 mejoras, 3 empeoramientos y 86 empates**.
p exacta = `470/16384` ≈ 0.0286865.
Condición primaria: p≤0,05, comprobada por enteros. Los empates se excluyen
solo de esa prueba, nunca de costes/metas o del informe. Única prueba
inferencial primaria; no se eligió una métrica favorable después de medir.

## Lectura del resultado y autopsia descriptiva

El agregado mejora546→136 de coste (−75,1%), con217→178 metas, pero no
satisface la réplica por bloques. En r0 las98 metas son79,67% de123, por
debajo del80% exigido; no se redondea a verde. En r1 el coste empeora74→94
y el número de excesos sigue siendo1. La prueba de signos favorable no
reemplaza estas condiciones ni la ausencia de colas.

Las dos tablas aprendidas convergen a los mismos umbrales activos: contacto
hazards/vases en tier6, margen3 y peligro en tier3; goal no se aprende como
costoso. Con la tabla congelada resultan la misma política efectiva. La
variación entre bloques corresponde a sus otros mundos, no demuestra un
aprendizaje de roles distinto entre las dos tablas.

Slow tiene coste en solo tres mundos:51001 (14),51016 (28) y52014 (94).
En los tres, legacy tuvo coste0. Los136 pasos con coste de slow tienen
señal de vasos; ninguno de hazards. Son fallos nuevos del recorrido lento,
aunque elimine muchos de los fallos del recorrido original.

La traza52014 registra giros con acciones[1,−1] y[−1,1] junto a vasos de
cercanía90 y coste de velocidad de vasos. El regulador limita avance lineal,
pero conserva la amplitud de giro. En51016 también hay contacto al avanzar
con el rumbo elegido evaluado como seguro, mientras otro bin de vasos llega
a91. Esto señala **giro y contorno del coche cerca de objetos** como hipótesis
para otra reparación; no prueba por sí solo que una limitación concreta del
giro o un cambio de geometría eliminen las colas.

Estos desgloses son lectura posterior de trazas ya guardadas, sin nuevos
episodios, cambios de candidato ni efecto sobre la puerta. Detalles en
`tail-diagnostics.json`. Las dos colas observadas son28 y94, mayores que25.

## Desglose registrado

| Control | OK | MODIFY | BLOCK | Freno velocidad solicitado | Velocidad media en pasos con coste (mm/s) |
|---|---|---|---|---|---|
| r0/legacy | 16728 | 29637 | 3635 | 0 | 97.98 |
| r0/slow | 19857 | 28472 | 1671 | 2704 | 188.52 |
| r1/legacy | 15011 | 31679 | 3310 | 0 | 352.99 |
| r1/slow | 16865 | 31586 | 1549 | 2223 | 49.24 |

Componentes devueltos por el mismo `env.step`:

| Control | Componente | Suma cruda |
|---|---|---|
| r0/legacy | cost_hazards | 122.00 |
| r0/legacy | cost_sum | 472.00 |
| r0/legacy | cost_vases_contact | 80.00 |
| r0/legacy | cost_vases_velocity | 349.00 |
| r0/slow | cost_hazards | 0.00 |
| r0/slow | cost_sum | 42.00 |
| r0/slow | cost_vases_contact | 5.00 |
| r0/slow | cost_vases_velocity | 41.00 |
| r1/legacy | cost_hazards | 22.00 |
| r1/legacy | cost_sum | 74.00 |
| r1/legacy | cost_vases_contact | 9.00 |
| r1/legacy | cost_vases_velocity | 52.00 |
| r1/slow | cost_hazards | 0.00 |
| r1/slow | cost_sum | 94.00 |
| r1/slow | cost_vases_contact | 17.00 |
| r1/slow | cost_vases_velocity | 92.00 |

`cost_sum` es un total y no se suma otra vez a los componentes. Los
componentes pueden coincidir en un mismo paso; no son causas excluyentes.

Peores episodios (semilla, coste ymetas):

- r0/legacy: 51039: coste170, metas5, 51037: coste110, metas2, 51018: coste80, metas3, 51034: coste47, metas3, 51005: coste42, metas0
- r0/slow: 51016: coste28, metas0, 51001: coste14, metas4, 51000: coste0, metas1, 51002: coste0, metas0, 51003: coste0, metas4
- r1/legacy: 52036: coste31, metas4, 52028: coste22, metas1, 52000: coste14, metas0, 52040: coste7, metas6, 52001: coste0, metas1
- r1/slow: 52014: coste94, metas1, 52000: coste0, metas0, 52001: coste0, metas2, 52002: coste0, metas0, 52003: coste0, metas1

## Auditoría, alcance y custodia

Se recalcularon decisiones, acciones, aprendizaje, cadenas y agregados desde
los estados grabados; **no es replay de MuJoCo**. Se verificaron el conjunto
exacto de280 recibos y280 trazas, las dos cadenas de aprendizaje, identidades
de réplicas, tablas congeladas, barreras y cierres de fases. Además se
comprobó la igualdad del estado inicial registrado de las100 parejas
(`pairing-audit.json`), sin lanzar episodios adicionales. Los fallos de
setup/cierre/proceso/preflight bloquean el verde y conservan recibos. Las
pruebas sintéticas comprueban también que un relanzamiento no muta una corrida.

Revisión independiente antes de congelar; **36 pruebas técnicas pasan**
(12 nuevas de confirmación,17 de SHIELD-2 y7 originales de SHIELD-1).
Fuentes originales y copias custodiadas, agenda y recursos del simulador
verificados. Entorno: Python3.10.22, `{"gymnasium": "0.28.1", "mujoco": "2.3.3", "numpy": "1.23.5", "safety-gymnasium": "1.0.0"}`.

Solo SafetyCarGoal2-v0, dos tablas aprendidas y estos100 mundos pareados de
desarrollo. Los criterios y la muestra no se cambiaron según resultados.
La r1 anterior y el buscador siguen intactos, incluidos sus rojos. Ningún examen.

- Artefactos: `lab/echo58/shieldconfirm/slow-20261022-r1/`.
- Compromiso de fuentes/agenda: SHA256 `3bc4d90fc85667e56fa891ce7e50ff0f9dd99ee43a6866d74f8c470f5053a7d2`.
- Tablas: `c09f85bfc644674e0b64e8b752dc04f23d78a9bfdfef53bcd49e8f513e105c48` y `e14f2784b2a60a64cba98beb83ee0362173ffbf664a8c6116b5d337b6d11497a`.
- Veredicto U/B, fracción exacta y desgloses en `audit.json`.
- Hashes de todos los archivos y de este informe en `final-manifest.json`.
