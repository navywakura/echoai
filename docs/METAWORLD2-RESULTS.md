# META-WORLD-2 — resultados

**Estado:** verde en su alcance declarado. 20 de septiembre de 2026.
**Fase padre:** METAVERSE-1 ([contrato](METAVERSE1-DESIGN.md)).
**No cierra DRONE-3 ni sube ECHO-3 de 14/15.** Esto es geometría, no hardware.

Certificado `f508b10858e2a762e079106dfcb2ea3e5c3d9ac579e190482e4b19345c05d4e0`.

```bash
cd /home/user/REALRXOS/RXos
python3 -m echoai.metaverse1.bench
python3 -m echoai.tests.test_metaverse1
```

---

## 1. La pregunta

> ¿Se puede aumentar extensión, densidad y variedad del mundo sin cambiar
> trayectorias, eventos ni puntuación bajo el backend físico congelado?

La respuesta medida es **sí**, con los cuatro contrastes de abajo y los
límites del §6.

## 2. Qué se ha construido

COMPOSE-1 usa una losa fija de 7 × 7 celdas de tres metros. META-WORLD-2 la
sustituye por una **retícula de regiones**, y ahí es donde entra el invariante
de los campos de 8 bits:

- una **región** contiene como mucho 256 celdas, así que el índice **local**
  cabe en un byte: eso es lo que identifica `seq`, estado local, nunca el
  índice crudo del mundo;
- la **región** es otro byte, el campo `region` que `fusion1.core.packet` ya
  reservaba y que hasta ahora iba siempre a 0;
- todo lo que está por encima —coordenadas de la retícula, plantillas,
  identificadores de objetos del simulador, orientación— vive **fuera** del
  paquete, en `metaverse1/world.py`, y no llega a Q, CAM ni T.

Con dos bytes se direccionan hasta 256 × 256 = 65.536 celdas. El mundo
certificado usaba 49.

| | mínimo | 3 × 2 regiones | 4 × 4 regiones |
|---|---:|---:|---:|
| Regiones | 1 | 6 | 16 |
| Celdas | 49 | 294 | 784 |
| Tamaño | 21 × 21 m | 63 × 42 m | 84 × 84 m |

`MetaSpace` está escrito **contra la retícula, no heredando** de
`compose1_v3.Space`. Es deliberado: el banco compara las dos
implementaciones, y una subclase haría que esa comparación no pudiera fallar.
Hay un test que lo comprueba (`test_metaspace_is_not_a_subclass...`).

## 3. Resultado

| Medida | Casos | Fallos | Estado |
|---|---:|---:|---|
| **equivalencia** con el mundo certificado | 48 | 0 | verde |
| **detalle** visual sin tocar colisión | 12 | 0 | verde |
| **escalado** direccionable en dos bytes | 4 | 0 | verde |
| **sin ramas por mundo** en el motor | 1 | 0 | verde |

**Equivalencia.** 12 semillas × 4 condiciones (`static`, `closed`,
`low_energy`, `dynamic`), 40 pasos cada una con el mismo guion de acciones
sobre las dos implementaciones. Se comparan `scan()`, el resultado de
`step()`, la distancia a casa y la del oráculo, turno a turno. **Cero
diferencias en 48 trazas.** La retícula en su caso mínimo *es* el mundo
certificado.

**Detalle.** Tres niveles: 0 sin decoración, 1 con marcas de suelo por región,
2 con luminarias. El dígest de la geometría de colisión es **el mismo en los
tres** (`b69ae02e…` en el mundo mínimo), mientras los elementos visuales pasan
de 30 a 32. En el mundo 3 × 2, de 98 a 110 con el mismo dígest `217fef6b…`.
La emisión SDF separa `<collision>` de `<visual>`, y la decoración sólo puede
añadir visuales.

**Escalado.** Cuatro retículas hasta 4 × 4. Toda celda resuelve a (byte de
región, byte local) dentro de rango, ninguna región supera la capacidad y el
objetivo sigue siendo alcanzable.

**Sin ramas por mundo.** El motor se analiza con `ast`, no con `grep`: se
busca cualquier comparación contra una constante de texto que no sea una
condición o plantilla declarada, y contra cualquier entero ≥ 1000, que es
donde viven las semillas del banco. Cero infracciones.

## 4. Los controles pueden fallar

Un control que no puede salir rojo no demuestra nada. Es el hallazgo que un
revisor hizo contra DRONE-3, y esta fase lo hereda como regla. Cinco mutantes,
**los cinco detectados**:

| Mutante | Qué rompe | Medida que lo caza |
|---|---|---|
| coste de movimiento +1 | la puntuación | equivalencia |
| pared desplazada una celda | la geometría | equivalencia |
| luminaria emitida sólida | la colisión | detalle |
| `if seed == 7001` | rama por semilla | sin ramas por mundo |
| `name == 'sala-secreta'` | rama por nombre | sin ramas por mundo |

Además, un test comprueba que los visuales **crecen** con el detalle: sin eso,
«la colisión es estable» sería cierto también de un no-op.

23 tests en `tests/test_metaverse1.py`, todos verdes en 4,4 s.

## 5. Modelado

El mundo se declara en JSON —regiones, celdas bloqueadas, salida y meta— y
Blender reconstruye la malla desde esa declaración. El script **no importa
echoAI**: la tubería de assets no puede arrastrar el agente a un renderer.

- `metaverse1/declare.py` escribe la declaración.
- `metaverse1/assets/build_world.py` genera el GLB (Blender headless).
- `metaverse1/assets/render_room.py` saca la vista previa.

Reproducibilidad medida antes, en la sala de prueba: misma semilla dos veces
da la **misma malla byte a byte** (`78166fac…`); otra semilla, otra malla
(`07c4b479…`).

Blender es el Flatpak 5.2.0 LTS. El de `dnf` en esta máquina no arranca:
`undefined symbol: _ZTVN17MaterialX_v1_39_46OutputE`.

## 6. Lo que no demuestra

- **Nada sobre hardware ni vuelo real.** `drone3_green` sigue en `false` y
  ECHO-3 sigue en 14/15.
- **La equivalencia se mide contra `compose1_v3.Space`, no contra Gazebo.**
  Que la retícula reproduzca el mundo certificado en Python no prueba que el
  SDF ampliado se comporte igual dentro del simulador: eso es trabajo de
  FLIGHT-2 y PX4-2, con vuelos, no con geometría.
- **No se ha volado ni un metro en este banco.** No se ejecutó física.
- **Un mundo mayor no implica un agente mejor.** Aquí sólo crece el escenario;
  que el agente resuelva salas de 84 × 84 m está sin medir y es trabajo de
  COMPOSE en escala, no de esta fase.
- Las plantillas son dos (`room`, `hall`) y las regiones son rectángulos del
  mismo tamaño. «Variedad» hoy es modesta.
- Altura fija: el eje Z sigue sin usarse.

## 7. Custodia

Cero ficheros bajo `nexus0/`. Cero ediciones a ficheros sellados. Todo en
`echoai/metaverse1/` y `echoai/lab/metaverse1/`.

Comprobado tras implementar: POWER-1 y HOST-1 —que siembran su lock con
`rglob('*.py')` sobre `nexus0/`— reproducen su certificado, y la suite sigue
verde.

## 8. Siguiente

Del contrato de METAVERSE-1, por orden: **FLIGHT-2** (dinámica de mayor
fidelidad) o **SENSOR-2**. Antes de cualquiera de las dos conviene llevar el
SDF ampliado a Gazebo y medir allí, porque es el hueco que este informe deja
declarado en el §6.

— R.N.
