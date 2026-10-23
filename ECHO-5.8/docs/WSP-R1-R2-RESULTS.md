# W · R1/R2: resultados

Contrato y ejecución iniciada el 21/10/2026; cierre el 22/10/2026. **R1 VERDE; R2 ROJA. Auditoría VERDE.**

Estudio de representación de observaciones públicas. No mide score, inteligencia ni decisiones de ECHO.
No hubo inferencia, API, nuevas partidas ni apertura de un examen ARC.

Compatibilidad: 768/768 mensajes reconstruidos exactamente, 192 registros, cero fallos de parseo; 23 pruebas técnicas verdes antes de medir.
El auditor vuelve a normalizar las filas públicas originales, reconstruye todos los mensajes,
recuenta tokens/bytes, comprueba la selección de modo y recalcula la puerta con fracciones exactas.

| Juego | Uso | Formato | Tokens con leyenda | Mediana por mensaje¹ | p95 sin leyenda | Bytes con leyenda |
|---|---|---|---:|---:|---:|---:|
| bp35 | calibración | wsp | 1388200 | 2251.2969 | 94682 | 2014285 |
| bp35 | calibración | named | 1389666 | 2274.2031 | 94705 | 2023537 |
| bp35 | calibración | positional | 1388061 | 2249.1250 | 94680 | 2014286 |
| bp35 | calibración | wrapped | 1388510 | 2256.6250 | 94687 | 2016162 |
| s5i5 | evaluación | wsp | 48337 | 497.7969 | 1905 | 67996 |
| s5i5 | evaluación | named | 49803 | 520.7031 | 1928 | 77248 |
| s5i5 | evaluación | positional | 48198 | 495.6250 | 1903 | 67997 |
| s5i5 | evaluación | wrapped | 48613 | 502.1250 | 1909 | 70105 |
| sp80 | evaluación | wsp | 261260 | 481.2969 | 35125 | 366311 |
| sp80 | evaluación | named | 262726 | 504.2031 | 35148 | 375563 |
| sp80 | evaluación | positional | 261121 | 479.1250 | 35123 | 366312 |
| sp80 | evaluación | wrapped | 261589 | 485.6250 | 35130 | 368144 |

¹ Leyenda amortizada entre 64 registros, también cobrada una vez en los totales.

Ahorro mediano de los 128 cocientes relativos: **-0.4441 %**; ahorro total: **-0.0899 %**. Ambos deben alcanzar 15 %.
Totales de evaluación: WSP 309597 tokens; mejor JSON por juego 309319 tokens. Controles elegidos: `{"s5i5": "positional", "sp80": "positional"}`.
Sin regresión por juego: False. Veredicto determinado con enteros exactos, sin redondear. Esta tabla solo redondea la presentación.

## Coste CPU descriptivo

| Juego | Formato | Codificar: mediana µs | Decodificar: mediana µs | Primer mensaje + leyenda: tokens |
|---|---|---:|---:|---:|
| bp35 | wsp | 148692.84 | 7886.83 | 5039 |
| bp35 | named | 147407.60 | 7935.47 | 5056 |
| bp35 | positional | 147177.68 | 7909.77 | 5026 |
| bp35 | wrapped | 152887.90 | 7908.87 | 5063 |
| s5i5 | wsp | 17968.90 | 1637.85 | 1110 |
| s5i5 | named | 18185.79 | 1630.70 | 1127 |
| s5i5 | positional | 18144.46 | 1630.90 | 1097 |
| s5i5 | wrapped | 19751.84 | 1644.23 | 1134 |
| sp80 | wsp | 21705.99 | 1650.01 | 780 |
| sp80 | named | 21007.48 | 1642.98 | 797 |
| sp80 | positional | 20996.40 | 1637.76 | 767 |
| sp80 | wrapped | 22827.22 | 1666.55 | 804 |

Cinco repeticiones por registro. Codificar incluye construir y tokenizar los tres modos candidatos;
decodificar incluye validar y reconstruir. Los tiempos son descriptivos de esta máquina, no una puerta científica.
Se guardan las 320 muestras por juego/formato y operación. No se deducen julios ni velocidad de un LLM.

## Interpretación y límites

Se conservan los tres controles JSON, incluido el wrapper de la cadena WSP. La comparación permite a todos
raw/RLE/delta y elige el JSON de menor coste total por juego. No demuestra optimalidad sobre todo JSON posible.
Son dos juegos públicos de evaluación conocidos, 64 registros iniciales de cada uno; no un examen ciego
de tareas nuevas ni una prueba estadística de generalización. No hubo ajuste entre calibración y evaluación.
La postal WSP16 y el núcleo no cambian: el frame completo viaja como payload adicional del adaptador.
El adaptador conserva bits declarados, sin conceder autoridad a un mensaje recibido.

Si R2 queda roja, se conserva ese resultado y se recomienda el control JSON más económico de este banco.
R3 no se activa con este contrato. No se retiran controles ni se prueban otros alfabetos para buscar verde.

## Incidencias y decisiones anteriores a medir

- La primera preparación falló por una cota incorrecta de ocho imágenes. Se conserva como r1, con cero
  mediciones. Enmienda técnica antes de tokenizar: hasta 64 imágenes, pues el prefijo contiene hasta 47.
  Se preservaron todos los registros e imágenes; siguen 4 MiB por mensaje y 128×128 por imagen.
- La revisión encontró cifras derivadas sin auditar: regresiones de alteración y auditor corregidos antes de congelar.
- El caso de un modo perdedor demasiado grande se reclasificó importante y se corrigió con RED→GREEN:
  un mensaje válido puede elegir entre los modos que caben. Sin menores diferidos.
- Coste si estas decisiones fueran incorrectas: mayor memoria máxima admitida y rechazo de un formato
  cuando ninguno de sus modos cabe; no se ha alterado la puerta ni usado información de tokens de evaluación.

## Artefactos

Ruta: `/home/user/REALRXOS/RXos/echoai/lab/echo58/wspstudy/w-r1r2-20261021-r2`. Fuentes y contrato archivados en `sources/`; corpus en `corpus/`;
mensajes exactos en `messages/`; tiempos y métricas en `results.json`; auditoría en `audit.json`;
recibos técnicos y logs RED→GREEN en `technical/`. Figura `token-comparison.svg`.

- SHA-256 preflight: `8ca856610425e1d14cbca52a9096d2b7ad29f3bc9f33e169b66f705b69ca9215`
- SHA-256 resultados: `d48c14928610d4a65d8b73f063286d8181514093d08e5da2ced8b12e52047b0f`
- SHA-256 auditoría: `d4f27c2b469b048a3c46e68da8b4e0a0d95e4dc7446c6c1ac7af7d21951ba83d`
