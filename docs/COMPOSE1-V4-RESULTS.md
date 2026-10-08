# COMPOSE-1 v4 — resultados del examen ampliado

Estado: **COMPOSE-1 cerrado en su alcance software/SITL; certificado verde y segunda auditoría válida**.
[Diseño previo](COMPOSE1-V4-DESIGN.md).

Lock: `7575a764aa74e4782dd3dc950b6c1e4ed05a6f10e57a0495963458ab9a341e6f`.
Certificado: `b5974a9e18bf56fd3c94aea74f54eeecf93843498c1eb5ca25c5c9e6733d7073`.
`evidence_valid=true`, `functional_green=true`, `sitl_green=true`,
`compose1_green=true`, cero hallazgos. Estos son SHA-256 canónicos contenidos
en los JSON; no se confunden con el hash de sus bytes formateados.
Regresión de congelación: 37 tests aprobados. La reconstrucción previa confirmó
el rojo válido de v3 y la identidad del desarrollo reutilizado.
Trece controles v3 reutilizados por hash: siete mutantes software y seis
alteraciones de evidencia, todos rechazados y recalculados durante el cierre.
La cadena completa y la auditoría en un proceso nuevo terminan con **exit 0**.
La segunda reconstruye exactamente el mismo certificado, sin vuelos nuevos:

```json
{"compose1_green": true, "evidence_valid": true, "findings": [], "functional_green": true, "sitl_green": true}
```

## Validación funcional B

**Verde**, 3.072 misiones. Completo y horizonte uno: 256/256 metas alcanzables.
El completo ahorra 468 movimientos entre esas parejas; IC 97,5 % del ahorro
medio [1,234375; 2,4375]. Test de signos: 114 ventajas, 56 desventajas,
86 empates; p=0,000005116597346755562. Ambos criterios superan sus umbrales.
La confirmación C y la puerta física también superan sus criterios medidos.
La primera reconstrucción integral confirma ambas puertas; la segunda
auditoría en un proceso nuevo reproduce el mismo resultado.

## Confirmación funcional C

**Verde**, otras 3.072 misiones con semillas nuevas. Completo y horizonte uno:
256/256 metas alcanzables. Ahorro de 370 movimientos; IC 97,5 % del ahorro
medio [0,9296875; 1,953125]. Test de signos: 111 ventajas, 41 desventajas,
104 empates; p=0,000000006081095003021745. La ventaja demostrada está en
movimientos, no en una mayor tasa de llegada frente al horizonte uno.

Son 6.144 misiones funcionales entre B y C; las semillas muestrean una familia
finita de 48 geometrías con reemplazo. No equivalen a 1.024 salas distintas
ni al examen reservado de TRANSFER-3.

En B y C, completo con 8/32 candidatos, horizonte uno, convencional y sin caducidad
registran cero colisiones, hechos falsos, escrituras imaginadas y violaciones
de reserva. Q no alcanza ninguna de las 512 metas entre ambos exámenes y
registra **6 violaciones de reserva por examen**; en dos dinámicas de cada
examen tampoco termina en origen. Se publica este
límite del control y del estimador de retorno; el banco no prueba un gate
energético infalible. POWER-1 conserva su trabajo pendiente. El convencional
queda prácticamente empatado con el completo y sin caducidad empata exactamente
en este banco; no se les atribuye una desventaja que no aparece en los datos.

V4 utiliza directamente la implementación congelada v3. Sólo cambian versión,
semillas funcionales y tamaño muestral: 512 por etapa, 3.072 misiones en B y
3.072 en C. Mantiene p<0,025, intervalos 97,5 %, controles, modelo y límites
físicos. La potencia estimada del test de signos pasa del 49,80 % al 98,92 %
bajo la alternativa observada en v3; esa estimación no es un resultado del
examen nuevo.

Se reutilizan por hash los diez vuelos A y trece controles v3, sin contarlos
como nuevos. Los 32 vuelos de aceptación se ejecutaron por primera vez en v4;
esas etapas no se abrieron en las versiones anteriores. Los rojos de v1, v2 y v3 se conservan y quedan
referenciados en el lock. La reconstrucción de v3 B precede a la congelación.

Comando de cadena, desde `echoai/`:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.compose1_v4.bench finish
```

Sólo sirve para la primera ejecución: rechaza un lock o carpetas de examen
existentes. Para reconstruir el certificado ya cerrado:

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.compose1_v4.bench audit
```

## Validación física B

16/16 vuelos con evidencia válida y ejecución verde. El completo alcanza
3/3 metas accesibles y abandona en origen el caso de energía insuficiente,
sin desplazamientos de misión. Q no alcanza ninguna de las tres metas y
vuelve al origen. Horizonte uno y convencional alcanzan las tres.

Movimientos del completo por caso accesible: 24, 6 y 14; horizonte uno:
24, 6 y 10; convencional: 24, 6 y 14. En esta muestra física el completo
**no reduce movimientos** frente a horizonte uno; el contraste favorable
de composición corresponde a la puerta funcional agregada. No presentar
ambos bancos como si demostraran la misma ventaja.

## Confirmación física C y total

Otros 16/16 vuelos con evidencia válida y ejecución verde. Completo,
horizonte uno y convencional alcanzan 3/3 metas accesibles; Q 0/3. Los cuatro
modos abandonan en origen con energía insuficiente y cero desplazamientos de
misión. La primera reconstrucción integral está aprobada.

| Modo | Metas B+C | Desplazamientos B+C | Órdenes de desplazamiento/inspección aceptadas por PX4 |
|---|---:|---:|---:|
| Completo, 32 candidatos | 6/6 | 70 | 75 |
| Horizonte uno | 6/6 | 78 | 93 |
| Q reactiva | 0/6 | 306 | 306 |
| Convencional | 6/6 | 70 | 75 |

Son 32 vuelos nuevos, incluidos ocho abandonos con poca energía. Cero
violaciones de reserva y cero muestras inseguras entre 148.377 poses juzgadas;
menor distancia geométrica registrada: 1.175 mm. Son muestras correlacionadas
de trayectorias, no 148.377 ensayos de seguridad independientes. Tiempo
acumulado de sesiones: 5.062,22 s (~84,37 min), sin contar el banco funcional,
desarrollo o auditoría. ULog de aceptación: 828.157.814 bytes.

El ahorro físico de ocho desplazamientos es descriptivo: seis parejas no
constituyen el contraste estadístico funcional. El convencional empata en
desplazamientos y llegadas; no hay superioridad demostrada frente a él.

## Costes y límites

Completo funcional: máximo 32 expansiones por decisión y horizonte cuatro;
máximo 49 celdas observadas y 160 ranuras CAM usadas. Mediana del P99 por
misión B/C: 7,522/7,436 ms; máximo de esos P99: 12,532/12,731 ms. Mide
`agent.call(frame)` incluyendo IPC con el consumidor aislado, excluye el
arranque y el vuelo; no es un P99 global de todos los turnos ni un plazo
garantizado. Son contadores de ocupación, no una medición RSS ni de vatios.

El cuerpo sí vuela bajo PX4 en Gazebo; las decisiones proceden del consumidor
aislado, con WSP como única orden causal. LiDAR y cuatro vistas de profundidad
aportan geometría; las cuatro vistas pertenecen a una sola familia de
evidencia. RGB verifica un marcador verde definido de antemano. No acredita
reconocimiento visual genérico ni integración causal de todas las capacidades
de PATTERN-1R/DYNAMIC-1 en un animal completo.

Las salas son extrusiones de una retícula planar con vuelo a altura fija,
posición estimada disponible y escala conocida. El agente recibe coordenadas
de meta como hipótesis de misión, no el mapa ni la identidad del mundo; sólo
las confirma con percepción. No se demuestra búsqueda de cualquier objeto
por lenguaje, manipulación, carga real, SLAM general o transferencia al C
sellado de TRANSFER-3. El coste energético sigue siendo abstracto; los
abandonos de poca energía se deciden tras el despegue del arnés. POWER-1
deberá incluir energía física de despegue, vuelo, regreso y aterrizaje.

Informe: `lab/echo3_compose1_v4_report.json`. Ambas puertas reconstruidas,
segunda auditoría válida. El siguiente hito es CAUSE-1; no hay
hardware ni se cierra aquí PX4-1, POWER-1, SAFE-1 o TRANSFER-3.
