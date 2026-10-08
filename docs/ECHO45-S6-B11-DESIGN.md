# S6-B11 · contrastar consecuencias y aprender qué pedir

29 septiembre 2026. Contrato previo a mediciones B11 e inferencia. B10 y
sus auditorías permanecen cerrados y negativos. Hipótesis: contrastes de
trayectorias propias en desarrollo, más casos y selección adaptativa de
evidencia permitirán descubrir reparaciones que conserven capacidades y
eficiencia, y superar una petición genérica con idénticas herramientas.

## Límites de la afirmación

Autonomía acotada: el sistema selecciona evidencia, solicita una propuesta,
la ejecuta, la verifica, acepta/rechaza y usa su historial para elegir la
siguiente petición sin intervención humana por intento. El modelo genera
el programa; el verificador decide su aceptación. No hay entrenamiento de
pesos, conciencia, libre acceso al sistema ni autonomía general demostrada.
Una condición negativa cierra negativa. Solo B1–B5 juntos autorizan verde.

## Separación de datos

- A: 80 partidas, gym v2/v3, semillas **0–39**, 2000 decisiones, repetición 0.
  Incluye el A original 0–19 y amplía con 20–39, declaradas de desarrollo.
  Se muestran únicamente observaciones y resultados de A. No se seleccionan
  nuevas semillas por su resultado ni se trasladan partidas B al entrenamiento.
- B: 40 partidas protegidas nuevas **24920–24939**, v2/v3, 2000 decisiones.
  El modelo solo recibe el veredicto de rechazo; ningún detalle de B.
- Examen nuevo **25000–25059**, v2/v3, tres repeticiones: 360 partidas y 1800
  niveles por brazo. Sin abrir hasta promociones, auditorías y congelación.
- B histórica ya inspeccionada se conserva como evidencia del diagnóstico;
  sus casos, familias, trayectorias y controles humanos no entran en prompts.

## Qué cambia y qué se conserva

Se reutilizan v5.8, el lenguaje de condiciones B5 y el operador B9. Ambos
brazos pueden proponer **REVALIDATE_NOOP** 1–8, **HOLD** o **COOLDOWN_CAP**
dentro de sus límites existentes. Así pueden combinar reparaciones de
predicción y espera, sin limitarse al único operador aislado en B10.
Una propuesta añade un control y una a tres condiciones; máximo 32 parches.
Los actores iniciales tienen programa vacío. No se inyecta una reparación
humana ni una respuesta de ensayos anteriores como descubrimiento nuevo.

La gramática compartida exige compatibilidad con observaciones conjuntas:
contradicciones para revisar predicciones, lecturas efectivas para HOLD y
esperas activas para COOLDOWN_CAP. Excluye valores inertes en esas ocasiones
y repeticiones exactas propias. No busca programas ejecutándolos ni los
ordena por puntuación. Coincidir con una oportunidad no demuestra utilidad.
Una ausencia de opciones obliga a abstenerse, consumiendo la llamada.

Ambos brazos reciben el mismo formato de feedback: ganancias/pérdidas A,
ejemplos con resultados antes/después y acciones alrededor de la primera
divergencia, más repeticiones de comportamiento medidas. Los ejemplos
incluyen casos positivos y negativos cuando existen; nunca se inventan
contraejemplos para rellenarlos. Un contraste no demuestra una causa interna.
Los fingerprints comparan acciones, frames, niveles, reinicios y puntuación
en el mismo A; no equivalencia universal de programas. Los duplicados cuentan
y atraviesan V1–V4; no se reemplazan por llamadas gratuitas ocultas.

FIJO mantiene la petición genérica y los tres casos incompletos de menor
nivel, con su propio feedback completo. ECHO elige entre contradicciones,
esperas, generalización y refinamiento, usando resultados de desarrollo
propios; rota casos y prioriza contrastes si una propuesta útil fue rechazada.
El planificador usa ganancia aceptada por intento y exploración determinista.
Los tipos son decisiones del algoritmo; la reparación sigue siendo del modelo.
Ambos tienen igual modelo, parámetros, presupuesto, lenguaje y verificador.
Esta comparación estima el conjunto selección+petición adaptativa; no separa
causalmente cada componente. Una ablación de componentes sería otro ensayo.

## Aceptación y promociones

V1 seguridad/formato; V2 ejecución y replay completos; V3 ≥2 niveles nuevos A
sin pérdida individual de niveles ni score; V4 ninguna pérdida individual B
y replay completo. Tolerancia score **1e-10**, sin relajar el criterio.

Piloto: seis rondas × una propuesta × dos brazos × tres semillas emparejadas
675001/675017/675029; +1000 por ronda. 36 propuestas +2 calibraciones sin
tareas =38 llamadas. Feedback entre rondas. Promueve con aceptación ECHO,
suma A ECHO>FIJO y, adicionalmente, **al menos dos parejas ganadoras y ninguna
perdedora**. Este requisito fortalece la repetibilidad del piloto.

Campaña condicional desde programa vacío: semilla 685001, seis rondas × cinco
propuestas × dos brazos =60 propuestas +2 calibraciones. No hereda las
reparaciones del piloto. Debe volver a obtener aceptación y ECHO>FIJO para
promover al examen. SIN FILTRO acumula todas las propuestas ECHO que pasan
V1/V2, omitiendo V3/V4, con el mismo orden y sin selecciones posteriores.

Los prompts, gramáticas, contrastes, duplicados y veredictos de ambas fases
se reconstruyen en otro proceso y caché independiente. Las auditorías no
vuelven a generar respuestas LLM: validan la procedencia y el wrapper exacto,
y repiten todas las mediciones y decisiones del verificador.

## Examen y verde

Criterios originales reutilizados directamente desde `s6_precise_exam`:

| Criterio | Pasa solamente cuando |
|---|---|
| B1 | ECHO ≥105% de niveles SEMILLA, score medio no menor |
| B2 | ECHO resuelve más niveles que FIJO |
| B3 | ECHO resuelve más niveles que SIN FILTRO |
| B4 | Conserva niveles y score agregados en ocho juegos oficiales de desarrollo, tres repeticiones |
| B5 | Fuentes, modelo, peticiones, decisiones, solver y replays verificables |

SEMILLA/FIJO/ECHO/SIN FILTRO se congelan antes de abrir. Ningún observador en
B ni en examen. Replay independiente de repetición 0 y solver del generador.
ARC-AGI-1/2/3 oficiales se miden aparte; S6-B no es una puntuación oficial.

## Recursos, registro y recuperación

Qwen2.5-Coder-7B-Instruct, revisión
`c03e6d358207e414f1eca0bb1891e29f1db0e242`, caché privada con hashes verificados;
CPU int8 dinámico fbgemm, resto float32, cuatro hilos, temperatura 0,7,
top_p 0,95, máximo 900 tokens, prefill 512 sin truncar. Máximo **100 llamadas**,
12 trabajos privados CPU de 3600 s, sin GPU ni pago. Máximo 64000 partidas
programadas localmente, incluidos replays/auditorías e intentos interrumpidos;
cuatro procesos. Los juegos oficiales y el solver se contabilizan aparte.
Se detiene antes de programar más partidas si quedan menos de 12 GiB libres.

Diario de desarrollo existente, visor en mini terminal y resúmenes de acciones
observadas; no monólogo fabricado ni texto del visor realimentado al actor.
Paridad con A antiguo y cuatro pares con/sin observador antes del piloto.
Checkpoints nuevos usan fsync+rename. Un supervisor de usuario independiente
del chat continúa mientras el PC siga encendido. No se reenvían inferencias
ambiguas ni trabajos fallidos automáticamente. Un fallo se conserva y registra.

[Diagnóstico](ECHO45-S6-DIAGNOSIS-20260929.md) · [Resultados](ECHO45-S6-B11-RESULTS.md).
