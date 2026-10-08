# DYNAMIC-1 — resultados

Estado: **ROJO bajo v1**. Validación A roja en dos grupos por **un** vuelo de
diez; el banco no se voló, como manda el protocolo. Evidencia válida: 89
comprobaciones, 0 hallazgos, y las 7 mutaciones del informe detectadas.
Contrato: [DYNAMIC1-DESIGN.md](DYNAMIC1-DESIGN.md), con sus enmiendas 1 y 2.
Lock `8ef26875…ae03`; informe `lab/echo3_dynamic1_report.json` (`2dda7544…`).

## Veredicto

| Etapa | Vuelos | Grupos | Auditoría |
|---|---|---|---|
| Validación A | 8 con pared móvil + 2 controles sin movimiento | 26/28 verdes; rojos `detection` y `prediction` | 89 comprobaciones, 0 hallazgos |
| Banco | no autorizado | — | — |

## Qué funcionó

- **El mundo se mueve y el arnés lo demuestra**: 2.7–2.9 m recorridos por la
  pared en cada vuelo, con la pose que publica el mundo como verdad. El
  servicio `set_pose` responde `false` aunque mueve; se comprueba la pose.
- **Sólo sensores**: los registros del consumidor se recomputan byte a byte
  desde las muestras crudas privadas en los 10 vuelos.
- **Un solo cable**, y todos los grupos heredados de SENSOR-1S y GROUND-1
  verdes en los 10 vuelos.
- **Nueve de diez vuelos cumplen la pregunta**: detección 0.908–0.966, error de
  predicción 18–66 mm de mediana y 84–118 de p95, con los controles en 0.091 y
  0.095 de falsas alarmas.

## El rojo

Un solo vuelo, `faulted-11b2f9bdbbccf260`:

| | Ese vuelo | Los otros nueve | Umbral |
|---|---|---|---|
| Detección | 0.684 | 0.908–0.966 | ≥ 0.80 |
| Predicción, p95 | 848 mm | 84–118 mm | ≤ 160 mm |

**Causa, medida.** El consumidor sigue cada silueta por su haz central y su
alcance más corto, y eso **no es un punto físico del objeto**: cuando la
silueta cambia de recorte (una pared deja de tapar a la otra), el punto se
desliza a lo largo de la pared. En ese vuelo la historia de una pista salta de
y = −1006 mm a +101 mm en tres barridos, más de un metro en 0.3 s, y la
extrapolación lineal convierte ese salto en velocidad: 29 registros con
predicciones de hasta 1.7 m. El vuelo tenía los cuatro fallos inyectados del
LiDAR dentro de la ventana de movimiento, que es cuando más cambia el recorte.

No es el mundo ni el sensor: es que la velocidad se estima con el primer y el
último punto de la historia, sin defensa contra un salto de segmentación.

## Qué significa y qué no

Significa que, en SITL, un consumidor aislado que sólo recibe sensores por un
cable detecta qué pared se mueve y predice su posición medio segundo después
con decenas de milímetros de error, en nueve de diez vuelos, y sin marcar los
objetos quietos más de lo que la deriva del propio cuerpo obliga.

No significa que lo haga de forma fiable cuando la geometría de la silueta
cambia bruscamente; ahí falla, y el protocolo lo cuenta como rojo. Tampoco
separa el movimiento propio del ajeno: el cuerpo está en estacionario y eso
queda declarado.

## Propuesta de v2

Una sola corrección, en el origen: estimar la velocidad de forma **robusta**
—la mediana de los desplazamientos barrido a barrido en lugar de la diferencia
entre el primero y el último— y tratar un salto grande entre barridos como un
corte de pista, no como movimiento. El resto del contrato, incluidos los
umbrales de la enmienda 1 y la verdad de la enmienda 2, se conserva.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.dynamic1.campaign audit
```

Log: `lab/dynamic1-run.log`. Evidencia: `lab/dynamic1/`.
