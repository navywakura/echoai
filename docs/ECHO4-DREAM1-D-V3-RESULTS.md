# DREAM-D v3 — resultados y límites

2026-09-22. **DREAM-D v3 verde; E4-DREAM-1 cerrada en su perfil experimental
WORLD-1 restaurado.** Auditoría completa válida, cero hallazgos,
`dream1_green=true`. ECHO-4 completo sigue abierto.
[Contrato congelado](ECHO4-DREAM1-D-V3-DESIGN.md).

## Qué cambia y por qué

V2 quedó limitada por el catálogo y el presupuesto, no por falta de otra
permutación. V3 conserva los seis ensayos existentes y añade dos contrastes
corporales de ocho pasos, manteniendo un máximo de 12 pasos por diagnóstico.
El adaptador importa calibración, prior, predicción, validación/consumo de
recibos, física y gate originales: ninguno de los módulos certificados se
modifica. WSP16, CAM y camino basal sin LLM permanecen intactos.

La novedad más importante es **seguridad condicionada por observaciones**:
una prueba puede ser peligrosa para algunas hipótesis iniciales, pero dejar
de serlo tras una intervención corta que las descarte. No se ejecuta por
conocer el cuerpo real: debe ser segura para todas las hipótesis restantes.
El archivo registra caminos, no una bolsa intercambiable de respuestas.
Si falta una rama condicionada, replay devuelve desconocido y no inventa
resultados mediante la física o el LLM. Hasta 22 ramas por contexto.

El catálogo y los programas iniciales son trabajo de ingeniería del
laboratorio. No se atribuyen a Qwen. El modelo recibe puntuaciones históricas
de programas sistemáticos y propone prioridades/cuotas; el selector basal
elige por evidencia. Copiar o recombinar una buena estrategia observada no
equivale a descubrir nuevas leyes ni a entrenar los pesos.

## Desarrollo, separado de confirmación

El [cribado del prior](../lab/echo4/dream1-d-v3-screen/report.json) enumera
6.561 secuencias de ocho acciones después del ensayo corto original, en
320 condiciones ya abiertas del segundo ciclo v2. Máximo278 resueltas para
ese par; no es una cota de todos los controladores posibles. Se usan las
predicciones originales para analizar particiones de hipótesis, **sin
fabricar recibos observados**. Coste adicional de calibración: 1.152 pasos.
Digest `5a77f83dff56b0fea492b7def0422d0aebb61b5cce55ce4cabe311216af42c0c`.
El cribado exploratorio previo también comprobó que repetir acciones puras
largas pierde utilidad por las restricciones de seguridad.

Después se recogieron físicamente las ramas del catálogo elegido en 1.040
condiciones antiguas: cuatro cuerpos v1 y los 48 cuerpos v2. Ocho programas
sistemáticos compiten por peor margen histórico, resolución y coste. El
seleccionado es `[2,6,0,1,3,4,5,7]`, presupuesto 12 y cuotas activadas.

| Lote abierto | Casos | Selección sin LLM | Fijo | Aleatorio | Adaptativo | Legado v2 |
|---|---:|---:|---:|---:|---:|---:|
| Cuatro cuerpos v1 | 80 | 76 | 60 | 77 | 80 | 80 |
| Primer ciclo v2 | 320 | 292 | 180 | 227 | 225 | 245 |
| Segundo ciclo v2 | 320 | 290 | 210 | 232 | 245 | 245 |
| Tercer ciclo v2 | 320 | 298 | 200 | 248 | 265 | 240 |

Cero atribuciones erróneas/terminalidades y referencias conservadas. Paridad
online/replay exacta en los cuatro brazos del nuevo perfil. La selección
pierde en el pequeño lote v1: no existe dominancia universal ni se oculta
ese contraejemplo. Los tres lotes estratificados apoyan la factibilidad del
examen, sin ser evidencia independiente. 290 supera el 278 del par cribado
porque el intérprete puede tomar otro ensayo cuando el 6 no resulta seguro.

[Desarrollo reproducible](../lab/echo4/dream1-d-v3-development/report.json):
digest `b708751b6ba6f2daa4e211bd47dbf297ac516a80eacad0e148314285f7591093`.
La colección registra 14.565 ramas y 100.332 pasos, más 3.744 nominales.
La selección/historia no es gratis: el examen contabiliza además su propia
revalidación física y las nuevas colecciones.

## Examen prospectivo completo

Los tres ciclos superan sus márgenes sin errores ni terminalidades.
La selección está escrita antes de abrir cada lote; solo después se añade
el nuevo historial. El informe declara elegibilidad, no concede cierre por sí solo.

| Brazo | Ciclo 1 / 320 | Ciclo 2 / 320 | Ciclo 3 / 320 | Total / 960 |
|---|---:|---:|---:|---:|
| DREAM | 300 | 298 | 302 | 900 |
| Incumbente v3 | 190 | 298 | 302 | 790 |
| Fijo | 190 | 230 | 220 | 640 |
| Aleatorio | 238 | 246 | 237 | 721 |
| Sin Qwen | 300 | 298 | 302 | 900 |
| Sin feedback | 300 | 298 | 302 | 900 |
| Sin historial en prompt | 230 | 298 | 302 | 830 |
| Sin selección replay | 0 | 0 | 0 | 0 |
| Adaptativo minimax | 255 | 260 | 240 | 755 |
| Legado v2 | 245 | 245 | 240 | 730 |

| Margen obligatorio por ciclo | Ciclo 1 | Ciclo 2 | Ciclo 3 |
|---|---:|---:|---:|
| Al menos +32 frente al fijo | +110 | +68 | +82 |
| Al menos +16 frente al aleatorio | +62 | +52 | +65 |

Los diez brazos conservan las invariantes, con cero errores y terminalidades.
Los nueve del perfil nuevo tienen paridad online/replay exacta. No se rebajan
umbrales ni se sustituye un fallo por un agregado favorable. DREAM se abstiene
en 60 casos: se conserva esa incertidumbre, no se rellena con diagnósticos.

Primera promoción: `[2,6,0,1,3,4,5,7]`, presupuesto 12. En los dos ciclos
siguientes se conserva la misma política. Hay una mejora inicial, **no** una
sucesión ilimitada de mejoras. El control sin-Qwen y la ablación sin-feedback
empatan; no se ha demostrado una contribución exclusiva del LLM ni un
beneficio adicional de la revisión con feedback. La ablación sin-historial
vacía el prompt, **no** elimina el incumbente ni la selección por replay:
puede heredar la política ya validada, como ocurre en el segundo ciclo.

En el primer examen, 126 casos terminan con el ensayo corto, 164 utilizan
la secuencia 2→6 y otros 30 usan 2→0. Los 164 de la nueva secuencia se
resuelven correctamente; 20 de los 30 restantes mantienen la abstención.
Es un análisis descriptivo posterior, no un criterio añadido al cierre.

## Costes e identidad

- Qwen3-4B-Instruct-2507 Q4_K_M local, 2.497.280.736 bytes, SHA256
  `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`.
  llama.cpp `0.3.0-dev` / `d230ddd`, CPU cuatro hilos, GPU cero, contexto 8192,
  temperatura cero. Pesos sin modificar; servidor propio cerrado al terminar.
- 15 llamadas reales y 60 propuestas válidas, no todas distintas. 23.137
  tokens de entrada y 4.704 generados. Peticiones acumuladas: 1.859.458 ms
  (unos 31 minutos); arranque: 6.026 ms. No son tiempos de un benchmark
  aislado de CPU ni una medida energética.
- DREAM/sin-feedback/sin-historial disponen cada uno de dos llamadas y ocho
  plazas de candidato por ciclo. DREAM produce 5/6/7 programas distintos;
  sin-feedback y sin-historial, cuatro; el control sin-Qwen, ocho. El cupo
  igualado no elimina diferencias de diversidad efectiva.
- Historial antes de seleccionar: 1.040→1.360→1.680 contextos; al final, 2.000.
  Revalidarlo físicamente al empezar cuesta otros 100.332 pasos de colección
  y 3.744 nominales, además del desarrollo y costes hundidos v1/v2.
- Nuevas colecciones: 13.336 ramas y 91.424 pasos. Calibración de los tres
  lotes: 3.456 pasos, compartida entre brazos y ampliación; no contar dos veces.
- Diez brazos online: 87.368 pasos. DREAM: 7.936 frente a 11.520 del fijo,
  9.340 del aleatorio y 9.144 del legado v2. Menos pasos online no acredita
  menor coste total, dados colección, replay e inferencia.
- Selección/resúmenes replay: 77.707 consultas y 454.956 pasos representados,
  cero ejecución física nueva y cero llamadas LLM dentro de esas consultas.
  12/14/14 evaluaciones distintas por ciclo, no 40 programas globalmente únicos.

Regresiones, reconstrucción final y diagnósticos adicionales añaden cómputo
fuera de los contadores de campaña. No se equipara un token a un paso ni
se afirman ahorros de energía. El presupuesto fijo compara interacciones
online; los costes totales son un vector, no un único presupuesto igualado.

## Reproducción

[Informe de campaña](../lab/echo4/dream1-d-v3/report.json), digest
`965ce6cbcd759b48a12a9b04080ca5b78e657ab5b9e3869b081b0138ce240f15`.
`criteria_passed=true`; el informe conserva `dream1_green=false` por diseño.
El [recibo reconstructivo](../lab/echo4/dream1-d-v3/audit-receipt.json), generado
en proceso nuevo, concede **`valid=true`, cero hallazgos y `dream1_green=true`**.
Las 82 fuentes y las evidencias v1/v2 vinculadas permanecen intactas.
Sus resultados rojos no se reetiquetan. Próximo trabajo: E4-MAINTAIN-1,
todavía pendiente; no se ha iniciado en esta entrega.

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_dream1_v3 -q
PYTHONPATH=.. python3 -m echoai.echo4.dream_v3_bench verify lab/echo4/dream1-d-v3
```

La verificación reconstruye física, historias, selecciones, decisiones,
versiones e informe. Audita los recibos del modelo sin volver a inferir;
requiere los archivos locales de modelo/servidor para cotejar su identidad.
No añadir `--write-receipt` sobre el recibo existente. Una campaña nueva
requiere directorio inexistente, los argumentos explícitos de modelo/servidor
y permiso de loopback. Repetir casos ya publicados no crea otro holdout.
Los hashes aportan integridad local, no atestación externa de un tercero.

## Límites que permanecen

La validación pertenece a WORLD-1 restaurado, con familia causal y física
declaradas. No es autorreparación, vida autónoma continua, conciencia
subjetiva, aprendizaje de pesos ni mejora general en cualquier tarea.
La integración del producto sigue pendiente; el banco basal funciona sin
LLM. Un empate frente al selector sin Qwen limitaría la atribución de
beneficio exclusivo al modelo. Hardware después, METAVERSE-1 último.

No se modifica ni utiliza Discord; no hay publicación web, commit, push ni
subida a Hugging Face en este trabajo.

## Verificación de código

926 pruebas distintas: **925 aprobadas y un fallo esperado histórico**, sin
errores inesperados. Son 35 nuevas de v3, 50 de DREAM v1/v2, 583 de
DREAM-A/SELF-B/CONT-A/NEXUS-0/Q y 258 de CONT-B/C/D, SELF final, WORLD,
SENSATION y BOUNDARY. Las pruebas GUI usan loopback autorizado; no ha hecho
falta cambiar código por restricciones de sockets. No se afirma que estos
grupos sean toda la suite histórica del repositorio.

Cuatro corrupciones adicionales de una copia en memoria de evidencia real
de desarrollo —catálogo, token, rama huérfana y bytes— son rechazadas sin
escribir los archivos originales. La cota v2 se reprodujo también usando
sus recibos reales: 16 programas, máximo y unión 245, frente a 246 exigidos.
El auditor v2 vuelve a dar válido, cero hallazgos y rojo, sin reinferir.

Sintaxis Python comprobada mediante AST y ausencia de espacios finales en
los archivos nuevos; no se afirma haber ejecutado Ruff. Las 82 fuentes
congeladas de campaña incluyen los módulos basales y navi10 del repo padre.
