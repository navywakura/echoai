# TRANSFER-3 — ensayo público v2

2026-09-18. **Dos limitaciones metodológicas corregidas en el banco funcional;
ventaja de transferencia no demostrada. No es confirmación reservada.**

V1, sus fuentes y su informe se conservan sin modificaciones. V2 añade
`transfer3/policy.py`, `transfer3/rehearsal_v2.py` y tests propios. No cambia
COMPOSE ni los hitos certificados.

## 1. Geometrías separadas

El nuevo generador produce salas extruidas estáticas de tamaños variables,
con una pared interior y abertura. Reutiliza sensores cinemáticos y ejecución
de COMPOSE v3, sin importar la geometría al consumidor aislado.

La huella usa dominio y sólidos, **sin seed, nombres, salida ni meta**;
normaliza traslaciones y las ocho transformaciones de rotación/reflexión del
plano. Una sala antigua con otra meta sigue siendo un duplicado. Se excluyen
duplicados dentro y entre conjuntos, con un ledger de cada intento y fallo
explícito tras 100 intentos por caso. La selección comprueba capacidad y
conectividad geométrica, nunca resultados de la política.

Resultado: **4 geometrías de entrenamiento y 16 de examen público distintas,
cero solapamientos**. Es una comprobación de geometría de celdas con material
uniforme, no un auditor general de SDF/materiales ni prueba de vuelo físico.

## 2. Scratch competente y diferencia causal acotada

Ambos brazos reciben los mismos cuatro efectos cinemáticos programados,
el mismo controlador COMPOSE v3 `echo32`, objetivo, sensores, reserva,
presupuesto y mundo inicial. Scratch significa ahora **sin Q aprendida**,
no sin conocimiento de cómo moverse. Ambos congelan parámetros en examen.

Sólo el transferido importa Q adquirida en A. Se exporta el vocabulario
existente de COMPOSE: 27 direcciones relativas de la meta × 64 máscaras de
obstáculos próximos. Los valores son int8; no se exportan coordenadas,
distancias, slots originales, mapas, episodios ni identidades. La importación
crea ranuras abstractas sin hechos, y cada episodio reinicia mapa y visitas.
No es herencia GEN-1f ni ampliación del bus WSP.

Entrenamiento: tres pasadas por las cuatro salas A, con el controlador y gate
existentes. Se actualiza Q únicamente tras ejecutar y recibir odometría:

```text
r = 8 × (distancia_L1_antes − distancia_L1_después) − 1
    + 32 si la llegada se observa realmente
```

La característica siguiente se calcula tras incorporar la observación
posterior; durante la escuela se observa también antes de cada decisión.
No hay recompensa por planes imaginados. Coste observado: **113 movimientos,
452 unidades simuladas**, aparte de los costes del examen. No son julios.
El aprendizaje no implica que la función de recompensa sea adecuada para
aprender desvíos; eso sigue siendo una hipótesis de desarrollo.

## 3. Resultado de las 32 misiones aisladas

| Brazo | Metas | Movimientos | Colisiones | Violaciones de reserva | Hechos falsos |
|---|---:|---:|---:|---:|---:|
| Q transferida | 15/16 | 260 | 0 | 0 | 0 |
| Scratch con cinemática común | 15/16 | 262 | 0 | 0 | 0 |

Los parámetros permanecieron sin cambios durante todos los exámenes.
Comparación por sala, priorizando llegada y luego movimientos entre llegadas
conjuntas: **3 victorias, 3 derrotas, 10 empates**. Los fallos conjuntos son
empates; no se presentan pocos movimientos por abandono como eficiencia.

**No hay una ventaja consistente demostrada.** La diferencia agregada de dos
movimientos no convierte este resultado en verde. En el controlador actual,
Q sólo desempata rutas con las mismas puntuaciones geométricas y profundidad;
no reemplaza búsqueda ni gate. Se necesita investigar si este aprendizaje
aporta algo reproducible, sin debilitar scratch para obtener una victoria.

## 4. Evidencia y pruebas

`lab/transfer3/rehearsal-v2.json` contiene protocolo público, manifest de
fuentes, ledger, salas, escuela, Q exportada, observaciones, WSP, decisiones,
consecuencias y comparaciones. Todos los casos se conservan, incluidos fallos.

Auditoría en proceso nuevo con consumidor aislado: `replay_valid=true`, exit 0.
Reejecuta el generador, la escuela y cada misión y compara el informe completo.
Hash canónico:
`4babba741c1099def917294b8e9f8dbfdde807bf04cae861df3b2963208ded88`.
No es certificado de campaña ni prueba de custodia externa.

**46 tests pasan:** 10 nuevos, 23 de transferencia/custodia previos y 13 de
COMPOSE v3/v4. Cubren igualdad cinemática, scratch móvil, reinicio y freeze,
exportación Q relativa, valores/campos inválidos, normalización geométrica,
exclusión de duplicados y agotamiento sin fallback del generador.

Desde `echoai/`, con permiso para namespaces Bubblewrap:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rehearsal_v2 audit lab/transfer3/rehearsal-v2.json
PYTHONPATH=.. python3 -m unittest echoai.tests.test_transfer3_v2 echoai.tests.test_transfer3 echoai.tests.test_transfer3_custody echoai.tests.test_compose1_v3 echoai.tests.test_compose1_v4 -q
```

Los manifests de estos ensayos públicos enumeran las fuentes presentes al
ejecutarlos; agregar código cambia ese manifest. Una reproducción histórica
requiere el conjunto de fuentes registrado, no reinterpretar un manifest
nuevo como el antiguo. Los informes v1/v2 no se sobrescriben.

## 5. Estado y siguiente trabajo

Resueltas en este dominio las dos limitaciones de v1: geometrías repetidas y
scratch inmóvil. **No resuelta la hipótesis de ventaja transferible**. La
campaña final continúa bloqueada por falta de una candidatura y criterios
de aceptación justificados; no por falta de secretos de Nav.

Siguiente: diagnosticar las decisiones donde Q cambia la ruta, explorar el
aprendizaje sólo con datos de desarrollo y conservar los resultados negativos.
Después fijar N, KPI/umbrales y el examinador final con custodia. Estos mundos
v2 ya son desarrollo público y no pueden reutilizarse como B/C reservados.

**No se necesita intervención del custodio todavía. C final no generado ni
abierto; ECHO-3 sigue en 13/15.**
