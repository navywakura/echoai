# DYNAMIC-1 v2 — la velocidad, estimada de forma robusta

Estado al inicio del trabajo del 2026-09-14: **implementado, sin lock y sin
vuelos de cadena**. Roger autoriza revisar y ejecutar DYNAMIC-1 antes de
continuar con PATTERN-1R. Se adopta la tabla vigente de la enmienda 3;
el resultado dependerá de la cadena nueva, no del replay. DYNAMIC-1 v1 queda rojo y
se conserva entero ([DYNAMIC1-RESULTS.md](DYNAMIC1-RESULTS.md)).

Lo que rige es este cuerpo **más las enmiendas 1 y 3**. Las dos secciones
siguientes son el contrato original y quedan **superadas**: la enmienda 1
cambió el arreglo (la mediana de desplazamientos no funciona; se sigue la cara)
y la enmienda 3 cambió umbrales, evaluador y mutantes. La tabla vigente está
en la enmienda 3.

## Qué cambia (superado por la enmienda 1)

Una sola cosa, en el consumidor. Hoy estima la velocidad de una pista con el
primer y el último punto de su historia:

```
v = (último − primero) / Δt
```

Eso convierte cualquier salto de segmentación en velocidad. En v1, el punto
seguido saltó de y = −1006 mm a +101 mm en tres barridos —más de un metro—
porque el haz central de la silueta **se desliza por la pared** cuando cambia
el recorte, y el predictor lo tomó por movimiento: 29 registros con
predicciones de hasta 1.7 m en un vuelo, detección 0.684 y p95 848 mm.

v2:

- la velocidad es la **mediana de los desplazamientos barrido a barrido** de la
  historia, que ignora un salto aislado;
- un desplazamiento mayor que `JUMP_MM` entre dos barridos consecutivos
  **corta la pista**: eso no es un objeto que se mueve, es otra silueta.

`JUMP_MM` se fija en 300 mm: el móvil recorre unos 22 mm por barrido y el ruido
del LiDAR es de milímetros, así que 300 mm no puede ser movimiento real a esta
velocidad. Queda declarado que este banco no juzga objetos que se muevan más
rápido que eso.

## Qué no cambia (superado por las enmiendas 1 y 3)

- Mundos, arnés, velocidad mandada y verdad tomada de la pose publicada.
- Umbrales de la enmienda 1 y la corrección de la enmienda 2: detección ≥ 0.80,
  quietos ≤ 0.30 (≤ 0.15 sin nada moviéndose), diferencia ≥ 0.50, predicción
  ≤ 90 mm de mediana y ≤ 160 de p95.
- Evaluador, mutantes, muestra (A 8 + 2 controles; banco 12 + 6 mutantes) y
  regla de parada.
- El protocolo difiere de v1 sólo en versión, semillas y la huella del
  consumidor.

## Prueba antes de volar

La evidencia de v1 ya contiene el fallo, así que la corrección se demuestra sin
volar: alimentando el consumidor de v2 con las muestras crudas del vuelo que
cayó (`faulted-11b2f9bdbbccf260`), sus predicciones disparatadas deben
desaparecer y su detección subir por encima del umbral, mientras los otros
nueve vuelos y los dos controles se mantienen. Eso, más una tanda de desarrollo
nueva, antes del lock.

## Enmienda 1 (2026-09-13, antes del lock; aprobada por Roger)

El arreglo aprobado —la mediana de los desplazamientos barrido a barrido— **no
funciona**, medido sobre los diez vuelos grabados de v1: quita el disparate,
pero hunde la detección de 0.93 a 0.25, porque a 22 mm por barrido el
movimiento real queda por debajo del ruido paso a paso. Con extremos robustos
sube a 0.79 y empeora la predicción.

Lo que sí funciona, y pasa a ser el arreglo de v2: **seguir la cara**, no un
punto. De cada silueta se toma la recta de sus retornos, su normal y su
distancia perpendicular al cuerpo. Deslizarse a lo largo de una pared no la
cambia; cruzar su propia cara, sí. Una pista es la misma cara si su normal
coincide (20°) y su distancia no salta más de 400 mm; se mueve si esa distancia
recorre 80 mm en la historia **y** las dos mitades van en el mismo sentido, que
es lo que separa moverse de oscilar por la deriva del cuerpo.

De una cara plana sólo es observable el movimiento **perpendicular** a ella: es
el problema de la apertura, y no una carencia de este consumidor. Por eso la
predicción se juzga sobre esa componente, proyectando la verdad sobre la normal
que el evaluador recalcula del mismo barrido. Nada nuevo cruza el cable.

Medido sobre los diez vuelos de v1, con el consumidor y el evaluador de v2:

| Criterio | Umbral | Peor caso |
|---|---|---|
| Detección por vuelo | ≥ 0.70 | 0.789 (0.916–0.983 en los demás) |
| Detección agregada por etapa | ≥ 0.85 | 0.95 de media |
| Quietos marcados | ≤ 0.30 | 0.225 |
| Quietos marcados, sin nada moviéndose | ≤ 0.10 | 0.058 |
| Error de predicción, mediana | ≤ 60 mm | 28 mm |
| Error de predicción, p95 | ≤ 350 mm | 143 mm (288 en un control) |

Los diez vuelos que tumbaron a v1 quedan verdes con v2, incluido el que falló.
Muestra mínima: 15 registros juzgables por vuelo. La causa que aquí se daba
—los cuatro fallos del LiDAR dentro de la ventana— es **falsa**: corregida y
medida en la enmienda 3.

## Muestra y semillas

La de v1, con semillas nuevas: 20261311 (A) y 20261312 (banco). La historia
incluye toda la evidencia de DYNAMIC-1 v1.

Qué significan esas semillas, exactamente (enmienda 3): **los mundos no son
nuevos**. `WORLD_INDEX` y `WORLD_SEEDS` vienen del contrato de PATTERN-1R y no
dependen de la semilla de etapa, así que v2 vuela los mismos ocho mundos sobre
los que se fijaron los umbrales. La semilla de etapa sólo redibuja el orden de
condiciones y el calendario de fallos por vuelo. La única independencia real
frente a la tanda de ajuste es el ruido de episodio del SITL. Queda declarado.

## Límite que añade esta enmienda

La mediana de desplazamientos retrasa la respuesta a un cambio de velocidad:
este banco mueve la pared a velocidad constante, así que no lo mide. Un objeto
que acelere o gire no está cubierto.


## Enmienda 3 (2026-09-13, antes del lock; ejecución autorizada el 2026-09-14)

Hallazgos del revisor independiente sobre el código y el contrato de v2, todos
medidos antes de tocar nada. Tres eran bloqueantes.

### Dos defectos del consumidor, corregidos

1. **Un registro por silueta, siempre.** Una silueta sobrevive a huecos de
   hasta cuatro haces, pero la cara se ajustaba sobre la ventana contigua
   `[primero, primero+haces)`, que en ese caso puede contener un solo eco: el
   consumidor no emitía y el evaluador sí contaba, y a partir de ahí cada
   registro quedaba emparejado con el objeto equivocado. Una sola vez en un
   vuelo lo tumba entero y se lee como resultado científico. Medido: no ocurre
   en ninguno de los dieciocho vuelos examinados (v1 y desarrollo de v2), pero
   era alcanzable. Ahora la silueta sin recta emite igual —dónde está, sin
   reclamar movimiento— y el paso queda alineado por construcción.
2. **Una cara toma una pista.** La pista emparejada no salía del conjunto, así
   que dos siluetas del mismo barrido podían quedarse con la misma y su
   historia alternaba entre ambas: movimiento que el mundo nunca hizo. Ocurría
   11, 1 y 22 veces en vuelos de v1 y 43 y 7 en los de desarrollo de v2. Ahora
   la pista se reclama. Ambos defectos tienen test que falla contra el
   consumidor anterior.

### La causa de la muestra pequeña era falsa

El comentario congelado y la enmienda 1 atribuían los 19 registros de
`faulted-11b2f9bdbbccf260` a los fallos del LiDAR dentro de la ventana de
movimiento. **Imposible**: los fallos se inyectan a los 8, 16, 24 y 32 s y esa
ventana se abre a los 41.9 s. Medido en ese vuelo: sus 120 barridos dentro de
la ventana son `ok` y válidos, sin un solo hueco. De sus 145 siluetas en
ventana, 70 caen sobre la pared quieta, 56 sobre ninguna caja de verdad y sólo
19 sobre el móvil. Es una lotería de pose y geometría por episodio, no un
defecto: el mismo mundo volado otra vez da 119. El mínimo de 15 sigue en pie;
lo que guarda es eso, y así queda escrito.

### Lo que el aparato no miraba: dónde está

Nada en el evaluador leía la posición del registro. La detección usa
`rec[3]` y la predicción sólo la **diferencia** `rec[4]−rec[1]`, de modo que un
consumidor que pusiera todos sus registros en (0, 0) con el mismo paso pasaba
los cuatro grupos en verde con la misma mediana. La pregunta registrada dice
*dónde estará medio segundo después*.

Se añade un criterio y un mutante que lo prueba:

- **`where_it_is`**: la mediana de la distancia entre el punto del registro,
  llevado al mundo, y la caja a la que la votación lo asignó. Límite 500 mm.
- **`blind_place`**: séptimo mutante, emite el mismo desplazamiento desde
  (0, 0). Debe poner rojo `where_it_is` y sólo ese.

Medido sobre los diez vuelos de v1: honesto 15–178 mm de mediana por vuelo;
`blind_place` 2201 mm, y su percentil 5 ya está en 2015. `copy_current` sigue
cayendo sólo en `displacement` (116 mm) con `where_it_is` verde (78 mm).

Se juzga **la mediana y no la cola** a propósito: el punto de una silueta es su
alcance más corto puesto en la dirección de su haz central, que en una pared
oblicua cae a metros de la superficie (p95 de 2.9 m en vuelos honestos). Es el
punto que el consumidor siempre ha emitido, heredado de GROUND-1; medirlo con
una cola estrecha sería inventar un requisito que el consumidor honesto
incumple el 10 % de las veces.

### Lo que se descartaba sin decirlo

Las siluetas cuyos haces no cortan ninguna caja de verdad se tiraban en
silencio: 56 de las 145 en ventana de `faulted-11b2f9bdbbccf260`, el 39 %. No
cambian ningún umbral —nunca entraron en las cuentas— pero ahora el informe las
publica, junto con las que caen sobre algo que no es una barrera, en
`every_record_matched`.

### Tabla vigente

| Criterio | Umbral | Peor caso medido (10 vuelos de v1) |
|---|---|---|
| Detección por vuelo | ≥ 0.70 | 0.789 (0.916–0.983 en los demás) |
| Detección agregada por etapa | ≥ 0.85 | 0.947 sobre 833 registros |
| Quietos marcados | ≤ 0.30 | 0.225 |
| Quietos marcados, sin nada moviéndose | ≤ 0.15 | 0.056 (0.098 en desarrollo) |
| Diferencia detección − quietos | ≥ 0.50 | 0.609 |
| Error de predicción, mediana | ≤ 60 mm | 28 mm |
| Error de predicción, p95 | ≤ 350 mm | 143 mm (288 en un control) |
| Posición, mediana | ≤ 500 mm | 178 mm |
| Muestra juzgable por vuelo | ≥ 15 | 19 |

La fila de la diferencia faltaba en la enmienda 1 y puede ser más estricta que
la de detección: con quietos en 0.225 exige detección ≥ 0.725. Queda publicada.
El mínimo de muestra se aplicaba sólo a `moving_called_moving`; ahora rige
también en `still_left_alone` y en `displacement`, como decía el texto. La
normal de dos caras se declaró en 20°; `FACE_DOT = 950/1024` son **21.9°**.

### Un umbral que vuelve atrás

La enmienda 1 apretó el límite de falsas alarmas en control de 0.15 —el valor
registrado en v1— a 0.10, con los dos controles de v1 (0.035 y 0.056) como
única evidencia. La tanda de desarrollo volada con este consumidor mide 0.049 y
**0.098** en sus dos mundos quietos: la deriva del cuerpo en vuelo estacionario
depende del episodio más de lo que esos dos controles enseñaban. El límite
vuelve a 0.15. No es un umbral nuevo inventado para que salga verde: es el que
ya estaba registrado en v1, y se cambia **antes** del lock, con la tanda de
desarrollo delante.

### Qué margen hay, dicho en claro

Dos límites están a pocos registros del rojo, y el lector del contrato tiene
derecho a saberlo antes de que vuele:

- detección 0.789 son 15 de 19; con 13 de 19 (0.684) el vuelo cae. Dos
  registros.
- la muestra mínima, 15, contra 19 medidos, y el tamaño es una lotería de
  episodio: 19 o 119 en el mismo mundo.
- `p95` con 19 registros **es el máximo**; con 734 tolera 36 valores por encima.
  El mismo número no mide lo mismo a los dos tamaños.

Y el p95 de predicción: v1 lo tenía en 160 mm y v2 lo pone en 350, 2.2 veces
más. No es un ajuste cosmético: los fantasmas de 1.37 m que pusieron rojo a v1
**no se han eliminado, han quedado por encima del percentil 95** en la cola de
un control (`n = 734, p50 = 7, p90 = 42, p95 = 288, p99 = 807, max = 1368 mm`);
en ese mismo vuelo v1 puntuaba 112. Los controles propios de la tanda de
desarrollo de v2 dan 116 y 66, lo que confirma que es lotería de episodio y no
una regresión fija. Si la cadena sale verde, el informe lo dirá con estas
palabras.

### Lock

`docs/examples/sim3/protocol.json` no estaba ni en el inventario ni en la
historia, y `generate_suite` lo lee en el congelado, en cada etapa y en la
auditoría: lleva la altura de aparición del cuerpo (1000 mm) y con ella la del
LiDAR. Cambiarlo entre el lock y la carrera habría cambiado todos los mundos
sin que nada se quejara. Entra en el inventario.

## Revisión previa al lock — 2026-09-14

El auditor aún llamaba `d1.spec` (v1) para reconstruir el tratamiento y por
ello rechazaba `blind_place`, séptimo mutante de v2. Ejecución y auditor ahora
usan el mismo constructor v2 `scheduled_spec`; se añade una regresión sobre
todos los mutantes. Se comprueban además `arm` y `faulted` contra el calendario
congelado, junto a identidad, condición, semilla y mundo. No cambian consumidor,
evaluador, límites, muestra ni ventanas. La autorización no declara el verde:
A y banco deben completarse y auditarse con este código congelado.
