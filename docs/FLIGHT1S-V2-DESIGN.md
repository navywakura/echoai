# FLIGHT-1S v2 — tres preguntas, tres denominadores

**Estado: diseño congelado antes de calibrar.** Fecha: 2026-09-10.
Repara: [FLIGHT1S-DESIGN.md](FLIGHT1S-DESIGN.md) y su resultado rojo en
[FLIGHT1S-RESULTS.md](FLIGHT1S-RESULTS.md), que **no se tocan**.
Resultados: [FLIGHT1S-V2-RESULTS.md](FLIGHT1S-V2-RESULTS.md).

## 1. El defecto que se repara

v1 metió tres preguntas en un número. Su grupo `disturbance` exigía
`min_disturb_excursion_mm=400`, es decir que el desplazamiento **de lazo
cerrado** llegara a dos radios de la envolvente nominal. Dos episodios
recibieron una wrench real, registraron 963 y 957 partes por mil del impulso
mandado, salieron de la banda de recuperación y volvieron a ella — y fueron
rechazados por 389,4 y 291,7 mm. El criterio los suspendió por responder
demasiado bien.

Una excursión es el residuo que queda **después** de que el controlador
reaccione. Usarla como prueba de que hubo estímulo castiga a un PX4 mejor y
premia a uno peor. Eso es un defecto de medición, no del vehículo.

v2 no baja el 400. Lo sustituye por tres preguntas que no se compensan:

| # | Pregunta | Se responde con | Grupo |
|---|---|---|---|
| 1 | ¿se aplicó una entrada física? | una wrench publicada una vez y retirada, y el cambio de momento en el flujo de poses del backend | `stimulus` |
| 2 | ¿esa entrada sacó al cuerpo de la banda? | excursión estrictamente mayor que `radio + margen` | `challenge` |
| 3 | ¿PX4 lo devolvió y lo sostuvo? | vuelta al radio y permanencia, medida sólo desde que la wrench para | `recovery` |

Cada una tiene su denominador visible. Un impulso perfecto que nunca sale de
la banda suspende `challenge`; una salida que no vuelve suspende `recovery`;
una recuperación de un empujón que nunca se aplicó suspende `stimulus`.

**Por qué no es una relajación retrospectiva.** El criterio nuevo es más
exigente en lo que v1 no miraba: v1 no comprobaba que la wrench se publicara
exactamente una vez, ni que se retirara, ni que el impulso estuviera dentro de
una banda por arriba y por abajo, ni que el cuerpo saliera de la banda desde la
que luego afirma recuperación. v1 aceptaba, por construcción, una excursión de
1.500 mm producida por una wrench acumulada diez veces. v2 no.

## 2. Qué no cambia

Cuerpo, PX4 `v1.15.4` commit `99c40407…`, modelos `d754381a…`, airframe 4001,
los doce mundos rehearsal de SIM-3, el guion temporal, la fuerza de 5 000 mN
durante 600 ms, el aterrizaje, los límites de seguridad y el supervisor de
host. **No se toca ningún PID.** El SDF efectivo, el runner y el arnés son los
que v1 congeló, byte por byte.

`nexus0/flight1s/v2/` es un subpaquete a propósito: el lock de v1 hashea
`nexus0/flight1s/*.py` con un glob **no recursivo**, así que nada de v2 mueve
el `code_sha256` de v1 y el informe v1 sigue reconstruyendo. El esquema v2 vive
en `docs/schemas/flight1s-v2/` por la misma razón: un archivo
`docs/schemas/flight1s-*.schema.json` entraría en el inventario de v1 y lo
rompería. Comprobado, no supuesto: el preflight v2 registra el `code_sha256` de
v1 y se niega a correr si ha cambiado.

**La CLI v1 tampoco se toca.** Añadir `--protocol` a
`nexus0/flight1s/__main__.py` cambiaría ese inventario y rompería la
reconstrucción de v1, que es justo lo que §2 del relevo prohíbe. Por eso v2
tiene su propia entrada, `python3 -m echoai.nexus0.flight1s.v2`, y todos sus
comandos aceptan `--protocol` con el instante v2 por defecto. Los comandos
históricos conservan su significado exacto.

## 3. Física del estímulo

Con `F = 5 000 mN`, `dt = 600 ms` y la masa del X500 `m = 2 064 g`:

```text
impulso mandado      F·dt      = 3 000 mN·s
delta-v libre        F·dt/m    = 1 453 mm/s
```

Son cantidades **mandadas y libres**. No son el cambio de momento neto que
queda tras la reacción de PX4: ese es el que se mide, y en v1 salió entre 874 y
1 008 por mil del mandado. La medida viene de una diferencia finita del flujo
de poses del backend; no es un sensor de velocidad independiente y el
controlador también influye en ella. Está escrito así en el protocolo y en el
informe.

Que el servicio acepte la publicación es necesario y no suficiente. La
evidencia independiente sigue siendo el momento medido, y el control negativo
—declarar la fuerza y no publicar la wrench— dio 15 por mil en v1 frente a 913
de su control positivo.

## 4. Reglas fijadas antes de calibrar

Escritas en `nexus0/flight1s/v2/protocol.py` antes de volar A-v2, para que
elegir sea mecánico:

```text
recovery.radius_mm        = max(200, ceil(máximo horizontal nominal en A-v2, 50))
                            nunca por debajo del radio de v1
challenge.exit_margin_mm  = ceil(techo de velocidad × techo de intervalo de
                            muestreo) + error de la referencia, redondeado
stimulus.min_impulse_ratio_ppk = max(500, media + 6σ de los controles
                            negativos, redondeado a 10)
stimulus.max_impulse_ratio_ppk = 1500, fijo
```

El margen sale sólo de cantidades declaradas, nunca de un mínimo observado:

```text
techo de velocidad            1 500 mm/s   (por encima del delta-v libre de 1 453)
techo de intervalo de muestreo   25 ms     (por encima de 1/50 Hz y de los 21,3 ms medidos)
punto ciego                      38 mm     = 1500 × 0,025
error de la referencia           10 mm     (banda de 200 mm sobre ~400 muestras)
margen                           50 mm     = ceil(48 → 10)
```

Umbral de desafío = `radio + margen`. El suelo de impulso sólo puede alejarse
de los controles negativos, nunca acercarse: la regla toma el máximo entre 500
y `media + 6σ`.

## 5. Calibración A-v2

v1 eligió con cuatro episodios por nivel y cuatro no acotaba la dispersión: el
mínimo de A fue 455 mm y el banco completo bajó a 292 mm. v2 mide en los cuatro
mundos A:

- 8 repeticiones frescas nominales por mundo — 32 episodios;
- 8 repeticiones frescas perturbadas por mundo — 32 episodios;
- 1 control negativo por mundo, `force_declared_without_wrench` — 4 episodios;
- orden permutado por una seed nueva (20260911), procesos frescos, un solo lock.

Se publican todas las rondas, también las fallidas, y la dispersión por mundo y
por repetición, no sólo la mediana agregada.

La calibración es además una **puerta**. Se detiene y conserva el rojo si:

```text
algún episodio no completa
los controles negativos no quedan por debajo del suelo de impulso
algún perturbado queda fuera de la banda de impulso
algún perturbado no sale de la banda de desafío
algún nominal sí sale de ella
la actitud pasa del techo de 25°
algún perturbado no recupera
```

Nada de B o C entra en la elección de bandas. Los resultados de v1 en B/C son
públicos y v2 se rotula como **reparación de un banco rehearsal**, no como un
examen ciego de generalización.

## 6. Banco v2

Tras el freeze: los mismos 12 mundos × 2 condiciones × 2 repeticiones = 48
episodios, sin ramas por mundo, split, seed o resultado, sin reutilizar
procesos y sin red. Verde exige como mínimo:

```text
48/48 episodios completos
24/24 perturbados con wrench exactamente una vez y retirada registrada
24/24 perturbados dentro de la banda de impulso
24/24 perturbados fuera de la banda de recuperación más su margen
24/24 perturbados recuperados dentro del timeout y estables 3 s
24/24 nominales dentro de esa misma banda          ← puerta añadida, ver abajo
 0 teleports, replay, contacto no autorizado, NaN/Inf o regresión de reloj
 1 lock y 1 protocolo v2 en los 48
controles, mutantes, repetición y regresiones en verde
v1 intacto y auditable
```

**La última línea es más estricta que el relevo y se declara aquí, antes de
correr el banco.** El grupo `challenge` juzga los 24 perturbados *y* los 24
nominales: los primeros deben salir de la banda y los segundos deben quedarse
dentro. La razón es que un umbral que el vehículo cruza también sin
perturbación no separa nada, y sin esa mitad el criterio volvería a depender de
una sola cola.

Se deja escrito el riesgo que esto acepta: en A-v2 el máximo nominal fue
235,0 mm contra un umbral de 250 mm, un margen de 15 mm sobre 32 episodios.
Si un nominal del banco lo cruza, el grupo queda rojo y se conserva. No se
quitará la puerta después de verlo.

La excursión se conserva y se publica como resultado —junto con pico de
velocidad y actitud— pero no sustituye a la fuerza aplicada. Ninguna mediana
puede tapar un episodio fallido.

Un verde aquí se describe como **reproducción con un protocolo reparado sobre
esos doce mundos**. No es evaluación reservada ni sim-to-real.

## 7. Mutantes obligatorios

Cada uno desde un control positivo que cerró:

```text
fuerza declarada sin wrench                    stimulus debe suspender
wrench acumulada varias veces                  publicaciones ≠ 1 o impulso fuera de banda
ventana de perturbación desplazada             impulso fuera de banda o wrench fuera de ventana
unidades de fuerza equivocadas                 impulso por encima del techo
nunca sale de la banda pero declara recuperación   challenge debe suspender
recuperación puntuada antes de parar la wrench     el esquema fija measured_from
pose teleportada o replay                      sin firma PX4 y sin stimulus
reloj congelado                                el episodio no puede completar
rama por A/B/C, seed o package_id              el inspector de configuración lo ve
verdad del simulador como setpoint             ídem
descarga de asset durante el banco             sin ruta fuera del contenedor
impulso alterado en el informe                 auditor
banda o margen relajados en el informe         auditor
episodio rojo omitido                          auditor
protocolo, lock o código v1/v2 mezclados       auditor
traza o ULog alterados                         auditor
v1 declarado verde o v1 tocado                 auditor
```

## 8. Orden

1. Congelar diseño, esquema y reglas. *(este archivo)*
2. Calibrar en A-v2, publicar todo, pasar la puerta o parar.
3. Congelar protocolo v2, lock y seed de orden.
4. Banco de 48, controles, mutantes, regresiones.
5. Auditar, publicar, actualizar `NOW.md` y `ROADMAP.md` con lo medido.

Si algo falla, se conserva el informe rojo. No se mueve el umbral, no se
repiten sólo los episodios fallidos y no se declara cerrado FLIGHT-1S.
