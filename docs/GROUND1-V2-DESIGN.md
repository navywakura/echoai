# GROUND-1 v2 — el sello de entrega, arreglado en su origen

Estado: **contrato aprobado por Roger** (2026-09-11). Sin lock ni vuelos de
banco. GROUND-1 v1 queda rojo y se conserva entero
([GROUND1-RESULTS.md](GROUND1-RESULTS.md)).

## Qué cambia

Cambia una sola cosa: el emisor del canal lee `now` dentro del cerrojo con el
que saca mensajes de la cola, en la misma sección crítica. Hoy lo lee antes
(`sensor1s_v2/assets/sensor_runner.py:240–242`).

Por qué basta:

- `ingest` lee `arrive` y después encola bajo el mismo cerrojo;
- si `now` se lee dentro, todo mensaje que salga en la tanda se encoló antes
  de esa lectura;
- el reloj del proceso es monótono, así que `now ≥ arrive` siempre.

El cambio vive en una copia del canal, `nexus0/ground1_v2/assets/`. SENSOR-1S
v2/v3 y GROUND-1 v1 no se tocan, y sus locks siguen reconstruyendo.

## Qué no cambia

- La comprobación y su límite: `delivered_ns ≥ arrive` (o ≥ liberación, si hay
  retraso), estricta. No se añade tolerancia de un tic.
- Evaluador, criterios, enmiendas 1–3, mutantes, consumidor, traducción,
  muestra (A 16+4, banco 24+6) y regla de parada: los de GROUND-1 v1.
- El protocolo difiere de v1 sólo en versión, semillas, la huella del canal
  (`channel_runner`) y su declaración (`sender_clock`).

## Prueba antes de volar

El canal importa Gazebo y sólo corre dentro del contenedor, así que la prueba
se hace en el host, con los módulos de Gazebo sustituidos:

1. Un test conduce la clase `Tap` con un reloj controlado y fuerza el
   intercalado: un mensaje encolado entre la lectura de `now` y el cerrojo.
   Con el canal de v1 sale `delivered < arrive`; con el de v2, no.
2. Un test de diferencias: sólo cambian las líneas del emisor.
3. Una tanda de desarrollo con el código final, como en v1.

## Límite declarado

Con 2 casos en 3 020 167 envíos, un banco de 30 vuelos no puede demostrar
estadísticamente que la carrera desapareció: a la tasa de v1 se esperaría
~0.3 casos en un banco. La prueba de la corrección es el test determinista.
El banco comprueba que nada más se rompió y vuelve a juzgar todo lo demás.

## Muestra y semillas

La de v1, con semillas nuevas: 20261111 (A) y 20261112 (banco). Mismos 12
mundos de rehearsal. La historia incluye toda la evidencia de GROUND-1 v1.
