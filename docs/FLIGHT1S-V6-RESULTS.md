# FLIGHT-1S v6 — resultados

Estado: **VERDE bajo v6**. Validación A y banco completos, auditados, con
evidencia válida y todas las mutaciones de adulteración detectadas.
Contrato: [flight1s-v6/DESIGN.md](flight1s-v6/DESIGN.md) (criterios v4,
configuración v5). Lock `0a16d37e…5177`. Informe
`lab/echo3_flight1s_v6_report.json` (sha256 `4ce46d93…92cd`).

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría | Reinicios PX4 |
|---|---:|---|---|---:|
| Validación A | 64 + 4 negativos | 13/13 verdes | 827 comprobaciones, 0 hallazgos | 0 |
| Banco | 48 + 3 mutantes | 14/14 verdes | 601 comprobaciones, 0 hallazgos | 0 |

Mutaciones del informe detectadas 7/7: omitir episodio, cambiar una medida,
verde inventado, omitir recuperación, activar agente, reinicio falsificado y
relajar el radio de recuperación. La auditoría se repitió en un proceso nuevo
tras terminar la cadena con el mismo resultado. Regresión previa al lock: 9/9.

## Medidas

| | Validación A | Banco |
|---|---|---|
| Perturbados recuperados (200 mm, 3 s, ventana 10 s) | 32/32 | 24/24 |
| Tiempo de recuperación, mediana / máximo | 1295 / 4503 ms | 1388 / 4505 ms |
| Nominal, mín–máx | 81.495–230.140 mm | 79.514–215.311 mm |
| Nominal >250 mm | 0 | 0 |
| Perturbado, mín–máx | 415.776–610.219 mm | 355.712–628.632 mm |
| Separación global (mín. perturbado − máx. nominal) | 185.6 mm | 140.4 mm |
| Impulso | 637–771 ppk | 640–773 ppk |
| Desplazamiento máximo desde el inicio (límite 1000) | 649.3 mm | 666.5 mm |
| Repetición: máx. Δ RMS hover / Δ recuperación | 42.3 mm / 455 ms | 62.8 mm / 3530 ms |

Tolerancias de repetición v2: 230 mm y 5000 ms. El Δ de recuperación del banco,
3530 ms, es el margen más estrecho de la cadena.

**Contraste por mundo.** A: 4/4 medias >50 mm, mediana 372.3 mm, mínima 340.2
(puerta de ingeniería, sin inferencia). Banco: 12/12 medias >50 mm, mediana
399.2 mm, mínima 240.4; prueba de signos unilateral p = 1/4096 ≈ 0.00024
(α = 0.025); límite inferior exacto 95 % de la proporción de bloques positivos
0.779. Supone bloques de mundo independientes con probabilidad común; son
mundos rehearsal públicos en un host compartido, lo que limita la extrapolación.

**Controles.** Los 4 negativos de A sin fuerza no parecen estímulo válido.
Banco: configuración privada, red deshabilitada, hash de mundo alterado
rechazado y todas las parejas perturbado > nominal. Mutantes detectados:
`noforce`, `accumulate` y `frozen_clock` (watchdog).

## Qué significa y qué no

Significa: en SITL, este X500 con PX4 v1.15.4 y la imagen
`v1.15.4-gpsaccuracy` (eph 0.2 m, s_variance 0.158 m/s, ruido inyectado
intacto), GPS_P_NOISE 0.2, GPS_V_NOISE 0.158, P=3, D=0.4, I=0, distingue un
pulso de 7 N/600 ms de la deriva nominal y recupera 200 mm durante 3 s dentro de
10 s en todos los vuelos perturbados de ambas etapas. La estabilidad se
atribuye a PX4.

No significa: autonomía echoAI (`agent_in_gazebo=false`, `cortex_calls=0`,
`wsp_writes=0`), vuelo real, sim-to-real, ni garantía de precisión nominal
≤250 mm por vuelo (v4 retiró esa exigencia; aquí se observó, no se certificó).
Cero fallos observados no es tasa de fallo cero.

## Historia que acompaña al verde

- V1–v5 siguen rojos y no se reescriben. V4: 44/64, interrumpida, un
  perturbado sin recuperar (otro candidato). V5: 64/64, un cuelgue MAVLink
  de PX4 y parada del agregador antes del informe.
- V6 vuelve a volar el candidato de v5 tras su rojo; aceptado por Roger antes
  del lock, con regla de parada: un rojo físico cerraba el candidato. No se
  activó.
- V6 relaja la regla de cero reintentos sólo para un arranque sin heartbeat,
  antes de tocar el vehículo. No se usó: 0 reinicios en 119 vuelos.
- El criterio nominal por vuelo de v2 se sustituyó en v4 por contraste por
  mundo; es la pregunta que este verde responde.

## Reproducir

Desde `echoai`:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.flight1s_v6.campaign audit
```

Recalcula A y banco desde trazas, ULog y hashes contra el lock. Log de la
cadena: `lab/flight1s-v6-run.log`. Evidencia en `lab/flight1s-v6/`.
