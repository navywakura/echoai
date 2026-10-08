# HOST-1 — autoridad por consecuencias, no por pulsación

2026-09-18 (contrato y banco iniciados el 17). **Verde funcional, con replay complementario de tres vuelos existentes.**
Sin nuevos vuelos, operador humano, hardware ni confianza social general.

| Medida por etapa reservada | B | C |
|---|---:|---:|
| Semillas, mismas cintas para ambas políticas | 64 | 64 |
| Decisiones útiles, completo | 1.536/1.536 | 1.536/1.536 |
| Decisiones útiles, recompensa-botón | 768/1.536 | 768/1.536 |
| Pérdidas de autoridad en ≤3 contradicciones | 1.024/1.024 | 1.024/1.024 |
| Recuperaciones en ≤6 confirmaciones nuevas | 1.024/1.024 | 1.024/1.024 |
| Casos de comunicación/arbitraje correctos | 14/14 | 14/14 |
| Ventajas por semilla, completo vs control | 64–0 | 64–0 |

Contraste de signos pareado por semilla: p=5,4210×10⁻²⁰ por etapa.
Wilson 95% descriptivo: completo [0,997505; 1], control [0,475026; 0,524974].
No son límites de fiabilidad humana o de producción: la matriz de tarea es
finita y las decisiones dentro de cada semilla comparten calibración.

## Qué se midió realmente

Dos fuentes de máquina, cuatro signos WSP y dos contextos; fases de fiabilidad
inicial, inversión y restauración. La cinta se genera completa antes de actuar
y no recibe comportamiento ni rendimiento: prueba Anti-Clever-Hans mecánica.
El consumidor corre en namespaces SIM-3 sin semilla, mundo ni cinta futura.

La calibración es supervisada y balanceada: se prueban ambas fuentes, incluso
la desacreditada. No demuestra exploración autónoma para recuperar confianza.
Tras cada fase, las elecciones de fuente se evalúan en lectura contra las
instrucciones/consecuencias registradas en su última repetición. **No son
metas nuevas ejecutadas después del examen ni transferencia semántica.**
El mecanismo es una ventana entera de ocho resultados por fuente/signo/contexto,
no una confianza global en una persona. Una fuente puede ser fiable en un
contexto y no en otro. Ningún botón, silencio o paso del tiempo actualiza
la autoridad del completo; sólo el recibo posterior ligado a su predicción.

Desarrollo: 16 semillas por política, 384/384 decisiones del completo frente
a 192/384. A/B/C suman 288 sesiones de política y 110.592 presentaciones de
recibos cinemáticos, con cada cinta compartida por ambas políticas; no son
110.592 experiencias físicas independientes. B/C no alteraron código ni umbrales.

## Comunicación y seguridad

Salida explícita SILENCIO|A|B|C|D por el mismo WSP de 16 bytes.
Cada símbolo emitido cuesta 2 sim_u, preserva reserva 40 y requiere oportunidad,
estado seguro, no estar ocupado y enfriamiento de un segundo. El gasto es
acumulado; repetir el mismo presupuesto no repone créditos ya consumidos.
Prioridad fija: veto → candidato de vuelo → silencio si ocupado → comunicación.
Las intenciones siguen necesitando SAFE/PX4/POWER: HOST no tiene un actuador
de vuelo ni puede hacer pasar WSP comunicativo por una orden PX4.
La comunicación aquí es salida simbólica del consumidor y registro del banco,
no voz, conversación libre ni entrega a un humano.

## Replay físico separado

Se reauditaron los nominales A de SAFE-1 y B/C de SAFE-1 v2. Las hipótesis
se construyen del objetivo comandado, antes de seleccionar la llegada medida:
una fuente lo predice correctamente y otra afirma el extremo contrario.
El replay confirma 3/3 afirmaciones de la primera y contradice 3/3 de la otra.
Autoridad final 256 frente a 0, **ambas aún sin permiso de confianza** porque
n=3 y se requieren cuatro observaciones. No se duplicó un vuelo para inflar n.
Cada recibo conserva hash de traza y ULog, auditoría nativa y mapeo explícito
del reloj de sesión. No son fuentes que hayan intervenido en esos vuelos.

## Verificación y artefactos

- 127 tests finales pasan (19 nuevos de HOST-1 y 108 de sus dependencias).
- Seis mutantes detectados: sin fuente/signo/contexto, premio por botón,
  ignorar consecuencia y omitir el gate comunicativo.
- Cinco corrupciones de episodio rechazadas: publicación, recibo, fuente,
  elección y numerador; tres alteraciones de informe rechazadas.
- Aislamiento real comprobado; auditoría reconstructiva en proceso nuevo válida.

Lock: `b077f665a75410476c064ca9082c45b03ff4fd33170600e6583edfbf58d93493`.
Certificado: `18d4a4fa07f57c7aacaa6064ec6c120b099a7d2e47e28920f14e1bc16d4b8ac4`.
Informe: `lab/echo3_host1_report.json`; recibo: `lab/host1/audit-receipt.json`.
Los certificados anteriores y el C sellado de TRANSFER-3 permanecen intactos.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_host1
PYTHONPATH=.. python3 -m echoai.nexus0.host1.bench audit
```

No afirma autenticación de fuentes, robustez ante sensores hostiles, herencia
entre agentes, autonomía social, batería física o integración DRONE-3.
Siguiente hito: TRANSFER-3, con su propio contrato y examen sellado.
