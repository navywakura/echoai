# SENSOR-1S v2 — resultados

Estado: **rojo en banco**. La parada del adaptador que tumbó v1 desaparece:
validación A verde en los 14 grupos y el banco verde en latencia. El banco cae
en `noise` por episodio: sesgo de LiDAR en 2 de 12 mundos, que el diagnóstico
atribuye al modelo de verdad del evaluador, no al sensor ni al adaptador.
Contrato: [SENSOR1S-V2-DESIGN.md](SENSOR1S-V2-DESIGN.md) (criterios de v1 sin
cambios). Lock `731b10e5…6858`; A `fc59bfb9…`, banco `274509e8…`, final
`lab/echo3_sensor1s_v2_report.json` (`ccc01e52…`).

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría |
|---|---|---|---|
| Validación A | 16 + 4 controles, 0 reinicios | **14/14 verdes** | 169 comprobaciones, 0 hallazgos |
| Banco | 24 + 7 mutantes, 0 reinicios | 14/15; **`noise` rojo** | 257 comprobaciones, 0 hallazgos |

Auditoría de la cadena y auditoría independiente en proceso nuevo: evidencia
válida en ambas etapas. Mutaciones del informe detectadas 5/5. Mutantes del
banco 7/7: cada uno pone rojo su caso concreto con el vuelo completo y su gemelo
honesto del mismo mundo pasa.

## La corrección funcionó

| Espera máxima (IMU / RGB / profundidad / LiDAR) | v1 A | v2 A | v2 banco |
|---|---|---|---|
| ms | 28 / 3 / **31** / 3 | 6 / 3 / 3 / 3 | 5 / 4 / 3 / 2 |

P99 limpia captura→entrega en v2: IMU 1, RGB 14–15, profundidad 19–22, LiDAR
60–68 ms (cotas 10 / 50 / 60 / 150). En las dos etapas, los vuelos con fallos
informaron exactamente 5 pérdidas, 2 obsoletos y 1 inválido por fuente; los
limpios, 0. Inicio del pulso 1–6 ms en 40 perturbados; 4/4 controles sin
fuerza en silencio. 749 963 tramas sin un canario.

Ruido agrupado: A LiDAR 1.006 / profundidad 1.002; banco LiDAR 1.001 (sesgo
4.0 mm, n = 23 886) / profundidad 1.007 (n = 64 337). Todo dentro de banda.

## Lo que cae

`clean` y `faulted` de `fc7b66ad1d741609` (sesgo LiDAR +12.2 y +13.0 mm) y de
`3d98a13f6860a097` (+83 mm), frente al máximo de 10 mm. σ en esos mismos
episodios 0.98–1.06× lo declarado; profundidad en esos mundos, sesgo ≈ 0. El
fallo se repite en los dos vuelos de cada mundo: es del mundo, no del azar.

## Diagnóstico (posterior al banco, sin vuelos nuevos)

Todas las cajas son opacas; no hay cristal. Esos dos mundos tienen muros
laterales paralelos a la dirección de vuelo y extremos de 200 mm:

- `3d98…`, haz de 0°: la verdad trazada da el extremo de 200 mm del muro m2 a
  5.08 m; el LiDAR mide 7.38 m, el muro m1 de detrás. El haz real pasa junto al
  borde.
- `fc7b…`, haces de ±13–15°: muros casi rasantes, errores de ±0.1–0.19 m a
  5–7 m. En esa geometría el rango cambia ~r·cot θ por radián de dirección: a
  14°, 0.5° de discrepancia mueven ~0.2 m.

Al retirar los haces cuya verdad cambia > 10 mm con ±0.5° de dirección, el
sesgo pasa a −1.9 / −1.6 mm (`fc7b`) y −1.1 / 0.0 mm (`3d98`), y el error
sistemático por haz baja de 53 y 445 mm a 2.5–3.7 mm; en los otros 20 vuelos
honestos el sesgo filtrado queda ≤ 7.2 mm y σ no cambia (0.95–1.07). Coste: en
`cb83617b…` quedan 46 muestras por episodio, por debajo del mínimo de 200.

Conclusión: el modelo de verdad del evaluador es demasiado sensible a la
dirección del haz en caras rasantes y bordes estrechos, geometría que el
desarrollo en A no ejercitó. El revisor independiente lo había anticipado
(hallazgo 6); v2 corrigió σ pero no el sesgo. Este filtro se diseñó **después**
de ver el banco rojo: una v3 debe declararlo así y volar todo de nuevo.

## Qué dice y qué no

Dice: el canal de sensores entrega en SITL, en 51 vuelos, tiempo, fuente,
pérdida, validez y latencia correctos contra la verdad privada, sin paradas y
sin filtrar identidad. No dice que el sesgo del LiDAR esté certificado en toda
geometría: el evaluador no pudo juzgarlo en dos mundos. SENSOR-1S no es verde.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.sensor1s_v2.campaign audit
```

Log: `lab/sensor1s-v2-run.log`. Evidencia: `lab/sensor1s-v2/`.
