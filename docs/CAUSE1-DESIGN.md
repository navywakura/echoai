# CAUSE-1 — atribución de movimiento en una cara plana

2026-09-17. Nav autoriza iniciar CAUSE-1. Protocolo de desarrollo previo al
código y a los datos. COMPOSE-1 v4 permanece congelado. Este documento concreta
la pregunta de §6 de ECHO-3-ACCEPTANCE; no cierra PX4-1 ni TRANSFER-3.

## Pregunta y alcance

¿Puede el agente separar la variación de distancia a una pared debida a su
desplazamiento de la debida al desplazamiento externo de esa pared, y reconocer
ambas contribuciones cuando coinciden? Una aceptación MAVLink no basta para
afirmar ejecución. Se exige orden previa, aceptación, desplazamiento observado
y corroboración privada de vuelo mediante ULog y pose del simulador.

Dominio inicial: X500 en Gazebo/PX4, altura de 2,5 m, una pared plana ancha al
norte, desplazamientos acotados sobre la normal. No estima causalidad general,
ni distingue empuje externo del cuerpo de movimiento motor bajo perturbaciones
no medidas. La confirmación de actuación se limita a este dominio sin empujes.
La pared puede trasladarse por intervención privada del experimento; nunca se
escribe la pose del dron. No hay hardware ni LLM.

## Intervención factorial y controles

Cada bloque usa la misma geometría y cuatro vuelos nuevos:

| Condición privada | Intención pública | Cambio externo |
|---|---|---|
| ninguno | esperar | ninguno |
| propio | trasladarse 1 m | ninguno |
| externo | esperar | pared 1 m en sentido opuesto |
| ambos | trasladarse 1 m | pared 1 m en sentido opuesto |

El signo del desplazamiento se alterna entre bloques. La variación sensorial
de `propio` y `externo` es aproximadamente igual: mirar sólo el cambio LiDAR
no permite atribuirlo. Cada vuelo tiene su propio arranque y aterrizaje; el
orden de los cuatro brazos se permuta reproduciblemente. La intención es una
entrada experimental legítima; condición, semilla, verdad y posición de pared
no llegan al consumidor.

Control principal: atribuir todo cambio sensorial a causa propia (coincidencia
temporal). Ablaciones: sin odometría, sin aceptación, sin confirmación de
movimiento y sin caducidad. Los controles se aplican a las mismas observaciones;
no se cuentan como vuelos nuevos. Se incluyen rechazo de orden, odometría
caducada, observación anterior al acto y campos privados inyectados.

## Entrada y salida

Consumidor aislado con la jaula SIM-3. Recibe intención WSP de 16 B, observación
LiDAR con ángulos/rangos/captura/entrega, estimador PX4 con posición y rumbo,
orden enviada y su aceptación. Un adaptador sensorial proyecta rayos cercanos
a la normal norte; la decisión usa enteros en milímetros y nanosegundos.
Nunca recibe pose verdadera, resultado del juez ni aviso de intervención.

Antes del acto publica WSP y predicción del cambio propio. Después registra
la aceptación y calcula:

```
desplazamiento_propio = odometría_después − odometría_antes
cambio_sensorial = distancia_después − distancia_antes
cambio_externo_estimado = cambio_sensorial + desplazamiento_propio
```

`published_ns` conserva el timestamp de observación como límite inferior;
el orden del diario y el envío posterior del WSP prueban que la publicación
precedió al acto. No se presenta como medición exacta del instante de
publicación. B/C registran además latencia de ida y vuelta del consumidor
con reloj monótono del host, distinta del reloj simulado.

El residuo es una estimación en el marco normal declarado. La salida distingue
ninguno, propio, externo, ambos y desconocido; las atribuciones son hipótesis
con evidencia, nunca hechos verificados en CAM. El diario externo conserva
referencias y tiempos; no constituye otro bus cognitivo. El banco no actualiza
CAM/T/Q con atribuciones ni transiciones imaginadas.

## Desarrollo y aceptación

Desarrollo: bloques 20262501–20262504. Validación B: 20262601–20262604.
Confirmación C de CAUSE-1: 20262701–20262704. Cada etapa prevista tiene 16
vuelos; C no es el C sellado de TRANSFER-3. Desarrollo puede modificar el
protocolo con motivo publicado. Antes de B se congelarán por hash código,
dependencias, criterios, modelo, semillas y controles. B rojo no abre C.
Cambiar después de B requiere versión nueva y conservar el rojo.

Criterios iniciales a contrastar en desarrollo: evidencia fresca ≤250 ms,
desplazamiento propio confirmado ≥600 mm en el sentido solicitado, error
respecto a 1 m ≤350 mm, residuo externo significativo >300 mm. Esperar
requiere desplazamiento ≤200 mm; la franja intermedia produce desconocido.
Cada captura posterior debe ser posterior a la aceptación; el cambio de
rumbo entre extremos debe ser ≤80 mrad. Datos inválidos producen desconocido.

Verde de aceptación requiere por separado en B y C: 16/16 vuelos válidos;
≥15/16 atribuciones correctas, ≥3/4 por condición; cero atribuciones propias
en `externo`/`ninguno`; más aciertos que el control temporal y test de signos
emparejado unilateral p<0,025; errores de residuo frente al desplazamiento
privado de pared ≤300 mm en ≥15/16; cero escrituras de pose del cuerpo,
filtraciones o cambios en los inventarios congelados. Se publican desconocidos
como fallos de acierto, intervalos binomiales y todos los denominadores.
Ningún vuelo fallido se omite o sustituye.

Precisión prospectiva antes de B: el desarrollo conserva la inicialización
aleatoria por defecto de Gazebo. En B/C se fija explícitamente `gz sim --seed`
a `10*semilla_bloque + índice_condición` (ninguno/propio/externo/ambos = 0/1/2/3),
con semillas distintas por vuelo. El emparejamiento entre clasificadores usa
exactamente la misma traza de cada vuelo. Las cuatro condiciones comparten
geometría, no ruido idéntico. Los intervalos describen este dominio finito;
no cuentan los rayos ni ticks como experimentos independientes.

## Auditoría y artefactos

Archivos propios en `nexus0/cause1/`, `tests/test_cause1.py`, `lab/cause1/` y
`lab/echo3_cause1_report.json`. La auditoría recompone la salida desde sensores,
comprueba orden intención/predicción/orden/ACK/consecuencia, vincula estimador
y comandos al ULog, y compara efectos con poses privadas. Verifica totalidad
de semillas, emparejamientos, archivos, hashes y protocolo, no sólo resúmenes.
Una segunda ejecución en proceso nuevo debe reconstruir el certificado.

Mutaciones mínimas rechazadas: falso verde, brazo omitido, semilla duplicada,
ACK falsificado, predicción publicada tarde, consecuencia alterada y residuo
modificado. Desarrollo, validez de evidencia y cierre CAUSE-1 son estados
distintos. No se avanza a PX4-1 por tener tests o desarrollo verdes.

## Ejecución desde echoai/

```
PYTHONPATH=.. python3 -m unittest echoai.tests.test_cause1 -q
PYTHONPATH=.. python3 -m echoai.nexus0.cause1.bench development
PYTHONPATH=.. python3 -m echoai.nexus0.cause1.bench freeze
PYTHONPATH=.. python3 -m echoai.nexus0.cause1.bench accept
PYTHONPATH=.. python3 -m echoai.nexus0.cause1.bench audit
```

El ejecutor necesita acceso local a Podman y Bubblewrap. Las etapas preservan
los directorios ya existentes: reanudar nunca sustituye un vuelo rojo. `freeze`
rechaza desarrollo incompleto o rojo y un lock existente; `accept` no
sobrescribe un certificado. `audit` es reconstrucción en otro proceso, sin
vuelos nuevos. `inspect --stage development|validation|confirmation` permite
consultar el estado, incluyendo denominadores ausentes.
