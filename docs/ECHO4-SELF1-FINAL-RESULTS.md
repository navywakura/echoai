# E4-SELF-1 — examen final software

2026-09-22. **E4-SELF-1 verde y cerrado en el dominio software declarado.**
A/B/C, 329 pruebas y replay completo pasan. El recibo final concede
`self1_green=true`, con alcance `WORLD1-binary-couplings-single-pulse-v1`.
[Contrato fijado antes del examen](ECHO4-SELF1-FINAL-DESIGN.md).

## Capacidad y alcance

La capacidad evaluada es un modelo funcional de sí mismo condicionado al
dominio WORLD-1: distinguir alteraciones propias/externas/mixtas, abstenerse
ante evidencia insuficiente o contradictoria, proteger memoria y utilizarla
en decisiones posteriores. No es identificación causal irrestricta ni
evidencia de experiencia subjetiva.

Se añade `SelfSession`, una confirmación acotada del diagnóstico existente.
El primer consenso no autoriza aprender o iniciar recuperación: se contrastan
los ensayos seguros restantes del catálogo. Una contradicción posterior o
un recibo inválido revoca la autorización. La sesión mantiene el prior y
los presupuestos originales; no recibe el estado físico exacto ni la causa
privada. Comparte el agente original, sin LLM ni segundo bus/CAM/T/Q.

Las dos tareas se publican por separado: vida continua de 24 pasos bajo una
alteración y reutilización de T tras restauración corporal **del ejecutor**.
No se llama autorreparación a esa restauración ni se cuentan paradas como
vidas completadas. Los controles usan las mismas condiciones y observaciones.

## Protocolo y trazabilidad

A: H={60,65}, temperatura={46,67}; B: H={61,66}, temperatura={47,68};
C: H={62,67}, temperatura={50,71}. Todos esos H están fuera de los estados
29..40 de los censos anteriores. Cada fase tiene 80 condiciones y 240
objetivos por brazo. Cada estado se calibra por separado: no es transferencia
sin entrenamiento. El mismo agente preparado se copia para emparejar controles.

B/C solo se abren tras A verde y un registro de congelación escrito en las
trazas. Las recetas son públicas y el propio laboratorio ejecuta el banco:
no se presenta como un examen ciego custodiado por un tercero. Los mecanismos
del grupo positivo pertenecen al prior conocido; los nuevos mecanismos que
lo contradicen se evalúan en el grupo de abstención, no como aciertos causales.

El informe de campaña solo puede declarar `closure_eligible`. El cierre
`self1_green=true` requiere además un replay completo en proceso nuevo y
la reproducción de las seis cadenas de evidencia anteriores. Un informe
reproducible rojo sigue siendo rojo. Los artefactos nunca se sobrescriben.

## Verificación de software

**27 pruebas nuevas y 302 regresiones seleccionadas pasan: 329 en total.**
Cubren confirmación posterior al consenso, predicción anterior a la física,
cancelación, presupuesto, recibos, veto real, mecanismos fuera del prior,
contraejemplo de identificabilidad, ausencia de acceso privado, manipulación
de evidencia y orden de apertura A/B/C. Los tests no ejecutan B/C antes
de la congelación; sus pruebas de orquestación usan dobles sintéticos.

Las fuentes y resultados de SELF-C v1 roja y SELF-C v2 verde se conservan,
igual que SELF-A/B, BOUNDARY y SENSATION. Los datos de la campaña final no
reescriben los criterios ni las conclusiones históricas.

## Resultados A/B/C

Los **16 criterios** pasan por separado en las tres fases. Diagnóstico
confirmado correcto: **80/80 en cada fase**, cero errores y cero terminalidades
diagnósticas dentro del dominio. Máximos: ocho candidatos H y 40 térmicos,
dentro de las capacidades 64/160. Las hipótesis verdaderas se conservan.

Reutilización: objetivos alcanzados de 240 por brazo/fase.

| Brazo | A | B | C |
|---|---:|---:|---:|
| Selectivo | **186** | **189** | **193** |
| Sin protección / todo externo | 148 | 152 | 143 |
| Congelar todo / todo propio | 136 | 144 | 148 |
| Igual aprendizaje, sin T al decidir | 80 | 96 | 84 |

B: 78,75% frente a 63,33% sin protección, **+15,42 puntos**. C: 80,42%
frente a 59,58%, **+20,83 puntos**. En C, congelar todo es el control más
fuerte (61,67%); también se supera, por 18,75 puntos. Ningún control gana
una comparación emparejada al selectivo. No se agregan las fases para
ocultar una que incumpla el umbral.

Victorias/pérdidas/empates del selectivo:

| Frente a | A | B | C |
|---|---:|---:|---:|
| Sin protección | 38/0/202 | 37/0/203 | 50/0/190 |
| Congelar todo | 50/0/190 | 45/0/195 | 45/0/195 |
| Sin T en la decisión | 106/0/134 | 93/0/147 | 109/0/131 |

### Las causas mixtas no están resueltas universalmente

| Causa | Selectivo A | Selectivo B | Selectivo C |
|---|---:|---:|---:|
| Nominal | 12/12 | 12/12 | 12/12 |
| Propia | 36/36 | 36/36 | 36/36 |
| Externa | 48/48 | 48/48 | 48/48 |
| Mixta | **90/144** | **93/144** | **97/144** |

En mixtas, el control sin protección obtiene 70/144, 73/144 y 67/144. Hay
ventaja en este banco nuevo, pero persisten **54, 51 y 47 fallos** del
selectivo. Esto no reescribe el empate mixto de SELF-C v2 en su otro banco.
La confirmación cuesta más y se ensayan otros estados/pulsos: no atribuir
toda diferencia entre bancos a una única mejora de software.

### Vida continua: supervivencia y paradas no son lo mismo

| Medida selectiva | A | B | C |
|---|---:|---:|---:|
| Vidas completadas / físicamente viables | **40/44** | **40/40** | **40/40** |
| Inviables, incluidos en el informe | 36 | 40 | 40 |
| Paradas | 40 | 40 | 40 |
| Muertes | 0 | 0 | 0 |
| Pasos reales | 1.620 | 1.620 | 1.580 |

En A hay **cuatro paradas en condiciones físicamente viables**: 90,91% de
completitud viable, no 100%. En B/C se completan todas las viables y se
detienen las inviables. La política sin protección ejecuta las mismas
acciones: la utilidad de proteger memoria se demuestra en reutilización,
no mediante un aumento ficticio de vidas completadas.

Los controles sin atribución/todo externo completan 44, 40 y 40 vidas, pero
sufren 20, 40 y 20 muertes, respectivamente; además se paran 16, 0 y 20 veces.
Congelar todo/todo propio no completa ninguna vida y se para 80 veces por
fase. Esas paradas no se contabilizan como éxito.

### Memoria e invariantes

En reutilización se retienen **1.104/1.104**, **1.056/1.056** y **1.164/1.164**
actualizaciones dejando T/PATTERN intactos. Cero escrituras con efecto
corporal en el selectivo, frente a esas mismas cantidades en el control
sin protección. Se permiten 1.416, 1.452 y 1.380 actualizaciones externas
legítimas; no se ha congelado todo el aprendizaje.

En vida continua, las 19, 16 y 16 retenciones también dejan los modelos
intactos. El selectivo conserva las hipótesis verdaderas en 80/80 condiciones
por fase. Los controles mantienen el balance de recursos y la referencia,
sin resets dentro de las vidas, hechos falsos, destrucción de slots o
llamadas corticales. En las tareas de reutilización T/PATTERN/Q permanecen
sin cambios; exposición y pasado del control no-T coinciden exactamente.

## Abstención: resultado y límite de seguridad

**48/48 pruebas de abstención por fase**, más el testigo de referencia
insuficiente y el veto nativo. Se rechaza autorizar aprendizaje/recuperación
con evidencia inválida, incompleta o contradictoria, sin alterar la memoria.
El veto real interrumpe el sondeo tras dos pasos; el veto nativo bloquea la
propuesta, retiene aprendizaje y no permite un segundo turno.

**Esto no significa cero daño fuera del prior.** Las perturbaciones
deliberadamente no modeladas producen **3 terminalidades en A, 4 en B y 4
en C**: enfriamiento invertido (1/2/2) y cambio térmico tardío +32 (2/2/2).
La sesión rechaza sus trazas, pero ese rechazo posterior no evita la
terminalidad durante el sondeo. No hay pasos después de morir. Calor
persistente y pulso retrasado se rechazan sin terminalidad en este banco.
El contrato separaba este grupo del dominio con garantía de seguridad;
la detección preventiva general de fallos desconocidos **no** queda cerrada.

El testigo de fuerzas externas que cancelan acciones reproduce exactamente
las observaciones del cuerpo desacoplado en las tres fases. El modelo emite
la misma etiqueta **condicional** en ambos. No puede determinar la causa
irrestricta: el informe registra `unrestricted_cause_identifiable=false`.
No se filtra una bandera de caso desconocido al consumidor para fingir que
lo distingue.

## Costes y artefactos

Confirmar no es gratis. Coste de diagnóstico medido en las trazas:

| Pasos | A | B | C |
|---|---:|---:|---:|
| Hasta el primer consenso | 544 | 720 | 680 |
| Confirmación adicional | 2.976 | 2.800 | 2.840 |
| Total | **3.520** | **3.520** | **3.520** |

Son seis ensayos/44 pasos por condición, dentro del presupuesto 6/48;
480 restauraciones diagnósticas por fase. La preparación principal requiere
672 pasos por fase: cuatro estados × (96 de la rama de reutilización + 72
de la rama de vida continua). La reutilización añade 12.480 pasos por fase
entre cuatro controles. Las pruebas negativas y testigos adicionales tienen
sus propias trazas/costes; no se presentan como experimentos gratuitos.

[Informe](../lab/echo4/self1-final-v1/report.json) ·
[Trazas completas](../lab/echo4/self1-final-v1/traces.jsonl) ·
[Recibo de cierre](../lab/echo4/self1-final-v1/audit-receipt.json).
Identidad de reproducción de la campaña:

```text
98ffc1ca438171a9bfb6a3926f5d3eef142f9338bc04827e311fc2bedec1a463
```

El registro anterior a B liga contrato, fuentes, padres y resultado A:
`d7203519d1df119990ee08ab53c4b1e6934392c3ee0768dc8252b0bcc663f810`.
El replay completo en proceso nuevo es **válido, sin hallazgos**. Reproduce
A/B/C, cada traza y el informe, y revalida íntegramente las seis cadenas
previas: SENSATION, BOUNDARY, SELF-A, SELF-B, SELF-C v1 roja y SELF-C v2.
El recibo concede el verde final. El informe de campaña conserva a propósito
`self1_green=false`: solo el recibo posterior, no la autoevaluación, cierra.

Desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_self1_final -v
PYTHONPATH=.. python3 -m echoai.echo4.self_final_audit verify lab/echo4/self1-final-v1
```

`campaign` exige una ruta nueva; `--quick` no abre B/C ni concede cierre.
`verify` compara cada línea con una nueva ejecución y vuelve a auditar
SENSATION, BOUNDARY, SELF-A/B y SELF-C v1/v2. Solo después podrá emitir
un nuevo recibo final verde del dominio limitado, sin sobrescribir el existente.

## Límites que permanecen

- Física nominal conocida, acoplamientos binarios, familia de pulsos finita
  y restauración experimental confiable. No aprendizaje autónomo de leyes.
- Todas las etiquetas positivas llevan el alcance del modelo. Una fuerza
  externa dependiente de la acción puede imitar exactamente una avería:
  igualdad de observaciones no permite recuperar dos causas incompatibles.
- Detectar los mecanismos nuevos ensayados no garantiza detectar cualquier
  perturbación desconocida ni garantizar seguridad fuera del dominio.
- Conservar una transición nominal puede perder también su componente
  externo en causas mixtas. Se publican sus aciertos y fallos por separado.
- Ni supervivencia indefinida ni reparación autónoma ni cierre de ECHO-4.

**Siguiente trabajo: E4-CONTINUITY-1**, contrato y pruebas de persistencia de
conocimiento al reanudar, cambiar de cuerpo o iniciar otro individuo. No se
ha implementado en este cierre. Hardware después del software; METAVERSE-1
al final. No se han realizado commit, push ni despliegue web.
