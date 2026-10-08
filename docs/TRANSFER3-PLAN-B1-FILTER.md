# TRANSFER-3 Plan B1 — filtro previo: el modelo perfecto es peor que el equivocado

> ## CORREGIDO por ARCH-1 — leer antes que nada de lo que sigue
>
> **La conclusión de este informe es incorrecta y el defecto es de su diseño, no
> de sus datos.** Las salas del generador están **rotadas** y la ganancia está
> fija en la acción 0, que es de marco mundo: en unas tres cuartas partes de las
> salas el agente nunca usa la acción con ganancia, así que no hay error de
> modelo que corregir, mientras que la desventaja del oráculo —la ráfaga gruesa—
> actúa en todas. Este filtro midió **dilución por rotación**, no el mecanismo.
>
> Con las salas alineadas, mismo cuerpo y mismo planificador, el signo se
> invierte: el oráculo hace **21/24 metas frente a 17/24** con ganancia 2, y
> **20/24 frente a 19/24** con ganancia 3. Ver
> [resultados de ARCH-1](TRANSFER3-ARCH1-RESULTS.md).
>
> **Plan B no queda descartado.** Los números de abajo siguen siendo válidos para
> el régimen rotado en que se tomaron, y el artefacto se conserva intacto; lo que
> no vale es la conclusión que extraje de ellos.
>
> Se retira además de este informe la explicación arquitectónica de la sección
> «La conclusión que ya no es sobre un parámetro»: ARCH-1 midió que el compromiso
> de plan es conductualmente inerte, de modo que la causa común que yo proponía
> para Plan A y Plan B **no está demostrada**.

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Filtro previo a
campaña, no una campaña: sin escuela, sin jaula, sin candidato, sin B/C. Aplica
la regla que dejó [la fase A](TRANSFER3-PLAN-A3-RESULTS.md): *antes de gastar una
campaña midiendo un parámetro, comprobar que el planificador puede usar su
precisión y no sólo su signo.*

## Qué se probó

Plan B propone aprender una propiedad reutilizable de la **ejecución**. La
instancia elegida es la **ganancia de actuación por acción**: una ráfaga
comandada avanza hasta `gain[a]` celdas por el gasto de una actuación y se
detiene ante lo ocupado, de modo que un agente mal calibrado se equivoca en la
predicción pero **nunca colisiona**. Físicamente: un actuador más potente en un
eje.

El brazo `oracle` recibe las ganancias verdaderas **directamente**, sin escuela.
Es por tanto una **cota superior de cualquier aprendiz**: si el oráculo no gana,
ningún aprendizaje puede.

## Hallazgo previo: la ganancia sólo cabe en una acción

La ganancia conserva la paridad a lo largo de su eje, así que subirla en más de
una acción destruye la alcanzabilidad de la meta:

| Ganancia | Ahorro óptimo | Salas resolubles |
|---|---:|---:|
| (2,1,1,1) | 10,9 % | **24/24** |
| (3,1,1,1) | 15,1 % | **24/24** |
| (2,2,1,1) | 70,3 % | 10/24 |
| (2,2,2,2) | 95,8 % | 2/24 |

La familia declarada lleva ganancia en una sola acción, y el validador lo
impone. Margen óptimo disponible: 10,9 % y 15,1 %.

## Resultado del filtro

24 salas del generador de dos paredes, reserva 6, gate de trayectoria y reserva
coherentes con la creencia, idénticos en todos los brazos.

| Ganancia real | Brazo | Cree | Metas | Energía | Colisiones | Err. predicción |
|---|---|---|---:|---:|---:|---:|
| (1,1,1,1) | nominal ≡ oracle | 1 | 17/24 | 2348 | 0 | 0 |
| (1,1,1,1) | sobreestima | 2 | 7/24 | 3412 | 0 | 300 |
| **(2,1,1,1)** | **nominal** | 1 | **18/24** | **2152** | 0 | 67 |
| (2,1,1,1) | **oracle** | 2 | 17/24 | 2324 | 0 | **0** |
| (2,1,1,1) | sobreestima | 3 | 6/24 | 3476 | 0 | 159 |
| **(3,1,1,1)** | **nominal** | 1 | **19/24** | **2024** | 0 | 55 |
| (3,1,1,1) | **oracle** | 3 | 17/24 | 2100 | 0 | 0 |
| (3,1,1,1) | subestima | 2 | **19/24** | 2028 | 0 | 56 |

`passes_filter = false`. **El oráculo no supera al nominal en ninguna condición
no trivial**, ni en metas ni en energía.

## Lo que significa

El brazo oráculo tiene un modelo **perfecto** —cero errores de predicción, cero
colisiones— y aun así completa **menos** misiones y gasta **más** energía. Y
subestimar la propia ganancia rinde igual o mejor que conocerla: con ganancia
real 3, creer 2 da 19/24 frente a los 17/24 de creer 3.

El mecanismo es doble:

- Una ráfaga de dos o tres celdas es **gruesa**. Se pasa de los huecos de una
  celda, impide el posicionamiento fino y deja al planificador de horizonte 4
  con un conjunto alcanzable mucho más pobre.
- El agente nominal **se lleva la distancia extra gratis**: comanda un paso,
  recibe dos, y la replanificación por turno absorbe la sorpresa sin coste. Sus
  67 errores de predicción no son daño, son progreso no planificado.

Sobreestimar sí es catastrófico —6 o 7 metas de 24—, así que el canal **es**
sensible a la magnitud, al revés que en Plan A. Pero lo es en una sola
dirección: hacia abajo es inocuo y hacia arriba es ruinoso, y el óptimo está
por debajo de la verdad.

## La conclusión que ya no es sobre un parámetro

Dos propiedades del cuerpo, independientes entre sí —coste de giro en Plan A,
ganancia de actuación en Plan B—, **ambas aprendidas con exactitud**, ambas
inútiles o dañinas, por razones distintas en la superficie y la misma debajo:

> El planificador replanifica desde cero en cada paso sobre un horizonte corto.
> Eso lo hace **robusto al error de modelo** e **incapaz de rentabilizar la
> precisión del modelo**. En Plan A la precisión no entra —el canal sólo lee el
> orden—; en Plan B la precisión entra pero lo que corrige ya lo absorbía la
> replanificación, y el modelo fiel encima estrecha el conjunto alcanzable.

No es mala suerte con la elección de parámetros. Es una propiedad de la
arquitectura, y cualquier Plan C debería enfrentarla antes que elegir variable.

## Decisión

**Plan B, en su instancia de ganancia, queda descartado antes de gastar una
campaña.** El filtro costó 24 salas y unos minutos, frente a las tres enmiendas
y dos confirmaciones que costó llegar a la misma clase de conclusión en Plan A.
La regla heredada funciona y se conserva.

Quedan sin probar otras instancias de Plan B —retardo de actuación, efecto de
una primitiva—, pero la conclusión estructural de arriba las afecta a todas: si
la replanificación absorbe el error, calibrar el modelo no puede pagar. Antes de
abrir ninguna, hay que decidir si se ataca la arquitectura o se cambia de
pregunta.

## Verificación

Artefacto: `lab/transfer3/plan-b1-filter-v2.json`, hash canónico
`82190543eceb6ba0c85e2833e66584cfc2b10ac1a1c82dbf148413164da18e28`.
Auditoría completa en proceso nuevo: `replay_valid=true`, exit 0, mismo hash.
15 tests B1 nuevos, todos en verde.

Se conserva `lab/transfer3/plan-b1-filter.json` (`734ab6ae…`), primer intento
público con resultados idénticos, cuyo manifiesto quedó incompleto por añadir el
fichero de tests después de ejecutarlo. La causa está corregida en el módulo: el
manifiesto ya no omite en silencio un fichero ausente.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_b1 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.filter_b1 audit lab/transfer3/plan-b1-filter-v2.json
```

TRANSFER-3 sigue en rojo. Custodia externa intacta, sin secretos pedidos.
ECHO-3 permanece en 13/15.
