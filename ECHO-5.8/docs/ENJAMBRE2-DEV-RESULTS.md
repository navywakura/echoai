# C v2 · conclusión del desarrollo, 22/10/2026

**Desarrollo terminado y auditado; resultado desfavorable para pasar a examen.**
La auditoría técnica es VERDE. No se ha ejecutado un examen ni hay un verde científico.

| Ataque | Ingenuo: puntuación / daño | Prudente: puntuación / daño | Por autor: puntuación / daño |
|---|---:|---:|---:|
| Falsa seguridad | 99 / 26 | 129 / 34 | 126 / 34 |
| Falsa alarma | 313 / 20 | 136 / 38 | 296 / 21 |
| Falso vínculo remoto | 86 / 20 | 132 / 36 | 110 / 26 |

Menor puntuación y daño son mejores. Cada fila suma tres macros,24mundos.
El prudente resuelve24/24 en los tres ataques; ante falsa alarma, ingenuo
resuelve16/24 y por_autor17/24. Recuperar ese progreso es útil, pero el daño
prudente es mayor que el ingenuo en **los tres** ataques. Tampoco gana a
por_autor en puntuación en falsa seguridad ni falso vínculo. La regla de
seguridad previa al examen no está respaldada por este desarrollo.

Hubo exposición real en los tres ataques. En el lector prudente, las consultas
expuestas / respuestas afectadas fueron6722/99 (seguridad),5692/42 (alarma)
y82/0 (remoto). Retirar testimonios falsos cambia muchas menos respuestas de
memoria en este lector, pero eso no equivale a mejorar la seguridad física.
La medida cuenta consultas, no decisiones independientes ni daños causados.
No se usa ese contador como sustituto de las métricas físicas del contrato.

La memoria global todavía aporta algo frente a silenciarla: el prudente suma
129/136/132 puntos frente a137 en cada ataque y daño34/38/36 frente a39.
El problema es que no cumple simultáneamente la comparación de seguridad
con el ingenuo y la ventaja específica frente al control por autor.

Recomendación: **no abrir el examen con esta versión**, conservar este resultado
negativo de desarrollo y continuar con las reparaciones pendientes de E.
Si se quisiera otra versión de C v2, necesitaría un contrato prospectivo que
revise la adaptación entre testimonios y acciones; no se retocará esta corrida.
ENJAMBRE-1 y LINK-3 mantienen sus resultados congelados: aquí se probó una
adaptación a memoria, no el selector de acciones completo de LINK-3.

Custodia:48/48 trabajos OK, recibos duraderos por ronda y auditoría offline.
18 pruebas C v2 verdes y11 pruebas C v1 verdes en su entorno habitual.
El inventario de C v1 falló inicialmente en Python del sistema por ausencia de
gymnasium; se comprobó con éxito en su entorno existente, sin instalar nada.
Las cuatro observaciones de la revisión independiente se corrigieron antes
de congelar o medir: truncación, evidencia ante fallo, desglose del informe
y procedencia/precedencia de consultas. No hay menores diferidos.
Sin llamadas LLM/API, publicación, cambios de facturación ni examen.


---

# C v2 · ENJAMBRE con mentiroso: desarrollo

**48 trabajos de desarrollo; examen cerrado.** Auditoría técnica VERDE.
Tres macros, cuatro agentes, ocho mundos por macro,30rondas y300pasos por episodio.
No hay veredicto científico de examen ni pruebas estadísticas sobre estas tres macros.

| Ataque | Brazo | Puntuación ↓ | Daño ↓ | Resueltos /24 | Fallidos | Consultas expuestas | Respuestas afectadas |
|---|---|---:|---:|---:|---:|---:|---:|
| false_safe | honesto | 86 | 18 | 24 | 33 | 0 | 0 |
| false_safe | ingenuo | 99 | 26 | 24 | 44 | 4156 | 4121 |
| false_safe | por_autor | 126 | 34 | 24 | 59 | 4710 | 4488 |
| false_safe | prudente | 129 | 34 | 24 | 62 | 6722 | 99 |
| false_safe | sin_global | 137 | 39 | 24 | 68 | 0 | 0 |
| false_safe | oraculo | 101 | 22 | 24 | 52 | 0 | 0 |
| false_alarm | honesto | 86 | 18 | 24 | 33 | 0 | 0 |
| false_alarm | ingenuo | 313 | 20 | 16 | 247 | 90771 | 90771 |
| false_alarm | por_autor | 296 | 21 | 17 | 155 | 47206 | 47199 |
| false_alarm | prudente | 136 | 38 | 24 | 67 | 5692 | 42 |
| false_alarm | sin_global | 137 | 39 | 24 | 68 | 0 | 0 |
| false_alarm | oraculo | 101 | 22 | 24 | 52 | 0 | 0 |
| false_remote | honesto | 86 | 18 | 24 | 33 | 0 | 0 |
| false_remote | ingenuo | 86 | 20 | 24 | 33 | 11 | 8 |
| false_remote | por_autor | 110 | 26 | 24 | 46 | 49 | 49 |
| false_remote | prudente | 132 | 36 | 24 | 63 | 82 | 0 |
| false_remote | sin_global | 137 | 39 | 24 | 68 | 0 | 0 |
| false_remote | oraculo | 101 | 22 | 24 | 52 | 0 | 0 |

Menor puntuación: resolver antes; un mundo no resuelto cuenta31. La referencia
`honesto` se ejecutó una sola vez por macro: se muestra en cada ataque como la misma
referencia, nunca como tres muestras independientes.

Exposición significa que una postal alterada de otro agente alcanzó una consulta global,
después de la precedencia local/privada/notas. Respuesta afectada significa que retirar
esas postales de esa misma consulta cambia su respuesta de memoria. No prueba por sí
sola un cambio de acción ni identifica la causa de cada daño.

## Lectura descriptiva

- `false_safe`: exposición presente.
  Comparaciones descriptivas: harm_leq_ingenuo=False, harm_leq_sin_global=True, score_lt_sin_global=True, score_lt_por_autor=False.
- `false_alarm`: exposición presente.
  Comparaciones descriptivas: harm_leq_ingenuo=False, harm_leq_sin_global=True, score_lt_sin_global=True, score_lt_por_autor=True.
- `false_remote`: exposición presente.
  Comparaciones descriptivas: harm_leq_ingenuo=False, harm_leq_sin_global=True, score_lt_sin_global=True, score_lt_por_autor=False.

## Desglose por tipo de mundo

| Ataque | Brazo | Tipo | Puntuación ↓ | Daño ↓ | Resueltos /6 | Fallidos |
|---|---|---|---:|---:|---:|---:|
| false_safe | honesto | door | 15 | 0 | 6 | 0 |
| false_safe | honesto | lava | 18 | 7 | 6 | 7 |
| false_safe | honesto | plate | 31 | 0 | 6 | 16 |
| false_safe | honesto | local | 22 | 11 | 6 | 10 |
| false_safe | ingenuo | door | 15 | 0 | 6 | 0 |
| false_safe | ingenuo | lava | 22 | 11 | 6 | 11 |
| false_safe | ingenuo | plate | 37 | 0 | 6 | 21 |
| false_safe | ingenuo | local | 25 | 15 | 6 | 12 |
| false_safe | por_autor | door | 20 | 0 | 6 | 0 |
| false_safe | por_autor | lava | 27 | 15 | 6 | 15 |
| false_safe | por_autor | plate | 45 | 0 | 6 | 25 |
| false_safe | por_autor | local | 34 | 19 | 6 | 19 |
| false_safe | prudente | door | 21 | 0 | 6 | 1 |
| false_safe | prudente | lava | 27 | 15 | 6 | 15 |
| false_safe | prudente | plate | 47 | 0 | 6 | 27 |
| false_safe | prudente | local | 34 | 19 | 6 | 19 |
| false_safe | sin_global | door | 22 | 0 | 6 | 0 |
| false_safe | sin_global | lava | 29 | 17 | 6 | 17 |
| false_safe | sin_global | plate | 49 | 0 | 6 | 29 |
| false_safe | sin_global | local | 37 | 22 | 6 | 22 |
| false_safe | oraculo | door | 15 | 0 | 6 | 0 |
| false_safe | oraculo | lava | 21 | 10 | 6 | 10 |
| false_safe | oraculo | plate | 41 | 0 | 6 | 31 |
| false_safe | oraculo | local | 24 | 12 | 6 | 11 |
| false_alarm | honesto | door | 15 | 0 | 6 | 0 |
| false_alarm | honesto | lava | 18 | 7 | 6 | 7 |
| false_alarm | honesto | plate | 31 | 0 | 6 | 16 |
| false_alarm | honesto | local | 22 | 11 | 6 | 10 |
| false_alarm | ingenuo | door | 68 | 0 | 4 | 83 |
| false_alarm | ingenuo | lava | 73 | 6 | 4 | 35 |
| false_alarm | ingenuo | plate | 92 | 0 | 4 | 55 |
| false_alarm | ingenuo | local | 80 | 14 | 4 | 74 |
| false_alarm | por_autor | door | 50 | 0 | 5 | 6 |
| false_alarm | por_autor | lava | 78 | 11 | 4 | 40 |
| false_alarm | por_autor | plate | 88 | 0 | 4 | 43 |
| false_alarm | por_autor | local | 80 | 10 | 4 | 66 |
| false_alarm | prudente | door | 22 | 0 | 6 | 0 |
| false_alarm | prudente | lava | 29 | 17 | 6 | 17 |
| false_alarm | prudente | plate | 49 | 0 | 6 | 29 |
| false_alarm | prudente | local | 36 | 21 | 6 | 21 |
| false_alarm | sin_global | door | 22 | 0 | 6 | 0 |
| false_alarm | sin_global | lava | 29 | 17 | 6 | 17 |
| false_alarm | sin_global | plate | 49 | 0 | 6 | 29 |
| false_alarm | sin_global | local | 37 | 22 | 6 | 22 |
| false_alarm | oraculo | door | 15 | 0 | 6 | 0 |
| false_alarm | oraculo | lava | 21 | 10 | 6 | 10 |
| false_alarm | oraculo | plate | 41 | 0 | 6 | 31 |
| false_alarm | oraculo | local | 24 | 12 | 6 | 11 |
| false_remote | honesto | door | 15 | 0 | 6 | 0 |
| false_remote | honesto | lava | 18 | 7 | 6 | 7 |
| false_remote | honesto | plate | 31 | 0 | 6 | 16 |
| false_remote | honesto | local | 22 | 11 | 6 | 10 |
| false_remote | ingenuo | door | 15 | 0 | 6 | 0 |
| false_remote | ingenuo | lava | 18 | 7 | 6 | 7 |
| false_remote | ingenuo | plate | 31 | 0 | 6 | 16 |
| false_remote | ingenuo | local | 22 | 13 | 6 | 10 |
| false_remote | por_autor | door | 19 | 0 | 6 | 0 |
| false_remote | por_autor | lava | 25 | 13 | 6 | 13 |
| false_remote | por_autor | plate | 39 | 0 | 6 | 20 |
| false_remote | por_autor | local | 27 | 13 | 6 | 13 |
| false_remote | prudente | door | 22 | 0 | 6 | 0 |
| false_remote | prudente | lava | 29 | 17 | 6 | 17 |
| false_remote | prudente | plate | 47 | 0 | 6 | 27 |
| false_remote | prudente | local | 34 | 19 | 6 | 19 |
| false_remote | sin_global | door | 22 | 0 | 6 | 0 |
| false_remote | sin_global | lava | 29 | 17 | 6 | 17 |
| false_remote | sin_global | plate | 49 | 0 | 6 | 29 |
| false_remote | sin_global | local | 37 | 22 | 6 | 22 |
| false_remote | oraculo | door | 15 | 0 | 6 | 0 |
| false_remote | oraculo | lava | 21 | 10 | 6 | 10 |
| false_remote | oraculo | plate | 41 | 0 | 6 | 31 |
| false_remote | oraculo | local | 24 | 12 | 6 | 11 |

## Confianza por autor

Cada celda es aciertos en disputa / errores, sumados sobre observadores y macros.
La suma es descriptiva: cada agente conserva su propio registro; no decide con esta suma.
El autor malicioso cambia con macro%4; los registros individuales están en cada recibo.
| Ataque | Brazo | Autor0 | Autor1 | Autor2 | Autor3 |
|---|---|---:|---:|---:|---:|
| false_safe | honesto | 0/1 | 0/0 | 0/1 | 0/3 |
| false_safe | ingenuo | 2/1 | 12/18 | 14/23 | 5/47 |
| false_safe | por_autor | 26/7 | 16/32 | 28/37 | 23/32 |
| false_safe | prudente | 20/6 | 17/37 | 23/38 | 23/38 |
| false_safe | sin_global | 25/8 | 13/37 | 11/56 | 15/38 |
| false_safe | oraculo | 6/3 | 0/21 | 0/20 | 0/32 |
| false_alarm | honesto | 0/1 | 0/0 | 0/1 | 0/3 |
| false_alarm | ingenuo | 16/4 | 12/25 | 16/19 | 14/18 |
| false_alarm | por_autor | 15/4 | 12/15 | 10/16 | 13/9 |
| false_alarm | prudente | 14/6 | 14/23 | 12/19 | 15/19 |
| false_alarm | sin_global | 13/8 | 14/19 | 12/21 | 14/22 |
| false_alarm | oraculo | 14/3 | 15/10 | 12/17 | 8/20 |
| false_remote | honesto | 0/1 | 0/0 | 0/1 | 0/3 |
| false_remote | ingenuo | 0/1 | 0/0 | 0/2 | 0/3 |
| false_remote | por_autor | 2/3 | 2/4 | 0/5 | 4/4 |
| false_remote | prudente | 0/6 | 4/8 | 4/7 | 6/5 |
| false_remote | sin_global | 0/8 | 3/10 | 4/6 | 5/7 |
| false_remote | oraculo | 1/3 | 0/0 | 0/2 | 0/1 |

Un empate con `por_autor` no demuestra una ventaja de la jerarquía de riesgo.
Sin exposición real, un ataque no puede presentarse como una defensa exitosa.
Estos resultados son de desarrollo; ninguna comparación activa un examen automáticamente.

## Límites del mecanismo

- Una adaptación de riesgo a lectura de memoria, no el selector completo de LINK-3.
- Un emisor autenticado altera solo el tablón global. No hay suplantación, colusión,
  sabotaje físico ni falsificación de notas o peticiones de ayuda.
- La confianza se contrasta con experiencia propia, una vez por clave y autor.
  Una excepción local puede desacreditar una generalización honesta.
- RM no entrena confianza; utiliza la obtenida en L1/L2. Exigir confirmación también
  puede suprimir información útil, especialmente con autores nuevos.
- El mundo, la política física y la cooperación son los mismos mecanismos humanos
  programados de C v1. No se demuestra invención de cooperación ni defensa ante todo atacante.

## Custodia y siguiente decisión

Fuentes/dependencias/contrato/agenda congelados antes de ejecutar; recibos exclusivos de
cada trabajo, rondas, observaciones reales, publicaciones original/enviada y consultas.
Auditoría offline: recuento de métricas, reconstrucción de postales propias y notas,
ataques, confianza y resoluciones. No vuelve a jugar mundos ni toca exámenes antiguos.
Preflight SHA256: `6ea4d630543df151280037ef03aa9e02fe53e4d25250b788c5d8f8025fe90987`.
Completed SHA256: `8aee523f800c38bd5e6a6bc960c90824b36f49fd615db2e9d157bc62d3aee997`.
Sin LLM, API, GPU, Hugging Face o publicación web. Conservar este desarrollo; Nav
decide el siguiente paso con sus resultados. No se cambian ataques ni reglas para buscar verde.

Artefactos: `lab/echo58/enjambre2/dev-20261022-r1`.
