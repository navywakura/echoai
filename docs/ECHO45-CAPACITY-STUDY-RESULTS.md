# ECHO 4.5 resultados y medios del banco de capacidad

2026-10-01. El paquete de publicación está generado. La ampliación ARC a
tres tamaños intermedios está en cola detrás de S6-PROBE1, todavía sin
ejecutar nuevas resoluciones. No se declara cerrada esa comparación.

## Mediciones disponibles

Los controles originales se han vuelto a contrastar con sus 750 replays
guardados: ninguna discrepancia. Sus 12 fuentes archivadas coinciden con
el perfil. No se han repetido partidas de S6 ni abierto otros exámenes.

| Guía | ARC-1 conocido | Pesos no cero tras 60 programas | Control sintético top-1 |
|---|---:|---:|---:|
| Sin guía | 3/250 | — | — |
| 640 | 5/250 | 633 | 33/40 |
| 4.096 | pendiente | 2.189 | 40/40 |
| 16.384 | pendiente | 2.832 | 40/40 |
| 65.536 | pendiente | 3.025 | 40/40 |
| 500.000 | 6/250 | 3.085 | 40/40 |

El control sintético nuevo utiliza los mismos 80 ejemplos de entrenamiento
y 40 de desarrollo en las cinco capacidades. Mide clasificación de cuatro
transformaciones; no es resolución ARC. Para ese control 4.096 ya iguala
a 500.000. La prueba ARC decidirá si sucede lo mismo con respuestas reales.

La ventaja histórica de 500.000 frente a 640 es una tarea, +0,4 puntos
porcentuales, sin perder sus cinco aciertos. CPU +0,918 % frente a 640,
+3,624 % frente a base. La memoria de pesos ocupa 500.000 bytes, no la
memoria total del proceso. No es evidencia de significación estadística ni
de transferencia a S6, ARC-2 o ARC-3.

## Material generado

- [Página estática](../lab/publication/capacity-20261001/index.html), con selector
  de operación, animación voluntaria, ocho pasos verificados y descargas.
- [ZIP para publicar](../lab/publication/capacity-20261001-web.zip), unos 60 MB.
- Cuatro gráficas PNG y SVG: aciertos, coste, ocupación y control sintético.
- 84 GIF, uno por familia candidata puntuada en la tarea `e3497940`.
- Ocho GIF adicionales, uno por paso de tres programas que ganaron frente
  a base. Su salida reconstruida coincide con la predicción registrada.
- Cada GIF tiene 28 fotogramas, póster PNG y JSON de índices, pesos y sumas.
  Las coordenadas y el giro son ilustrativos; no representan anatomía,
  tiempo de inferencia ni actividad del núcleo LIF.
- CSV, JSON, artículo Markdown, licencia del dataset y manifiesto SHA-256.
  El paquete no contiene las fuentes privadas de ECHO ni los pesos completos.

Ejemplo: [simetría, paso ejecutado](../lab/publication/capacity-20261001/steps/e3497940-01-sym_h.gif).
El cálculo de la guía ocurre antes de la búsqueda y no se vuelve a calcular
en cada paso del programa. Una familia candidata no implica una ejecución.

## Verificación

Nueve pruebas de integridad pasan: presupuestos, separación de respuestas,
rechazo de tareas ajenas al desarrollo, discrepancias de replay, regresiones,
espera de S6 y fidelidad de índices y pesos de la representación.

Se han decodificado los 92 GIF completos, comprobado los pesos de todas sus
ramas contra el candidato original y validado los 292 archivos del manifiesto
y el ZIP. Enlaces locales completos, 84 opciones en el selector y JavaScript
sintácticamente válido. Gráficas y pósteres inspeccionados visualmente.

No se pudo completar la revisión en navegador: `agent-browser` no pudo
arrancar su daemon dentro del entorno restringido. La interfaz interactiva
requiere aún esa comprobación en un navegador con permiso de ejecución.

## Continuidad

El ejecutor `python3 -m seed.capacity_study follow` está esperando S6 en una
sesión de proceso gestionada. El intento de crear un servicio de usuario
fue rechazado al conectar con D-Bus (`Operation not permitted`). Por ello
no se garantiza continuidad si se cierra esa sesión o se reinicia el equipo.

- [Estado](../lab/seed/capacity-study-20261001/status.json)
- [Registro de arranque](../lab/seed/capacity-study-20261001/launch.json)
- [Comprobación del paquete](../lab/seed/capacity-study-20261001/publication-check.json)
- [Contrato congelado](ECHO45-CAPACITY-STUDY-DESIGN.md)

El ejecutor utiliza dos workers y prioridad reducida después de S6 DONE.
Realizará 750 resoluciones nuevas y 750 replays. Una discrepancia bloquea
el cierre. Al completar la auditoría actualizará gráficas, página y ZIP.
Si el proceso termina antes, el mismo comando reanuda desde los resultados
completos; conserva los diarios de intentos interrumpidos.

## Integración en Artículos y publicación pendiente

Se ha preparado una copia aislada de la web en
`/tmp/rxlabs-capacity-publication-20261001`. El artículo está integrado en
español, inglés y catalán, como entrada destacada en Artículos. Todos los
GIFs, pósteres, gráficas y datos están incluidos en
`public/media/echoai/capacity-20261001/`. `PUBLISHING.md` registra la pauta:
las actualizaciones de investigación se publican en Artículos y su media
se versiona en GitHub. El repositorio original conserva su trabajo local.

Commit local preparado: `6787d0e4526da558f0f51d0e65ebc6702c9aa051`, sobre
`28f745ec1f2e852997482c4a48968a343776eea8`; 309 archivos añadidos o cambiados.
`npm run build` pasa: 114 rutas. Se comprueban los tres artículos generados,
sus índices, sitemap, 66 enlaces internos y los 292 archivos del manifiesto,
sin errores. Los artefactos se conservan byte a byte, incluidos el espacio
final de los SVG y los finales de línea CRLF del CSV generado. La
comprobación de espacios de los archivos editoriales y fuentes pasa.
El navegador automatizado sigue sin poder arrancar.

**Todavía no publicado.** La terminal no resuelve `github.com`. La conexión
de lectura de GitHub sí funciona y confirmó el commit base remoto, pero su
primera escritura (`create_blob`) fue rechazada con:
`MCP tool call requires approval, but approval policy is never`.
No se ha cambiado `main` en GitHub ni se ha iniciado un despliegue de Vercel.
El conector de Vercel también devolvió un error de validación de argumentos
al consultar el proyecto; no se ha inferido un estado de despliegue.

Se conserva el commit y toda su media en el
[paquete Git](../lab/publication/rxlabs-capacity-20261001.bundle), con su
[SHA-256](../lab/publication/rxlabs-capacity-20261001.bundle.sha256).
El [script de publicación](../lab/publication/publish-rxlabs-capacity-20261001.sh)
verifica el paquete, comprueba que `main` no haya cambiado, lo integra por
fast-forward, compila y hace un push normal al repositorio autorizado.
No incluye las fuentes privadas del motor ni modifica las fuentes congeladas
de S6 o del banco de capacidad. Debe ejecutarse desde la terminal del usuario:

```bash
bash /home/user/REALRXOS/RXos/echoai/lab/publication/publish-rxlabs-capacity-20261001.sh
```

Ruta pública prevista: `/articulos/echo45-memoria-asociativa-500k`.
Tras el push habrá que comprobar el despliegue y la URL pública antes de
considerar completada la publicación.
