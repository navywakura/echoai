# TRANSFER-3 — cierre y registro de lo que estuvo pendiente

2026-09-19. Complemento de [el índice](TRANSFER3-INDEX.md), que mapea los
documentos; esto conserva el trabajo que estuvo pendiente. **SUPERADO:
TRANSFER-3 está verde.** La campaña real C1 v2 completó custodia, B, C,
revelación final y certificado. B: 38/0 bloques; C: 48/1 frente al nominal,
con 0 pérdidas atribuibles. Certificado `8c77aead…`; ambos exámenes auditados
con reproducción exacta. Véase el cierre en el
[paquete de custodia](TRANSFER3-C1-CAMPAIGN.md).

## Los dos ejes, que se confunden fácil

**Planes** son hipótesis alternativas sobre *qué* se aprende. **Niveles** son
grados de evidencia sobre *cuánto* está demostrado. Son ortogonales.

### Planes

| Plan | Qué aprende | Estado |
|---|---|---|
| **A** — coste de movimiento | cuánto cuesta cada acción y girar | **cerrado en rojo**, 3 enmiendas, 2 confirmaciones fallidas |
| **B** — modelo de ejecución | ganancia, retardo o efecto de una primitiva | **ganancia probada y roja** en B2/B3 con escuela y jaula; otras primitivas sin probar |
| **C** — calibración perceptiva | calibración extrínseca de la cámara | **C1 confirmado prospectivamente: 43/0 bloques, p = 2⁻⁴³** |
| D/E | libres, mismo dominio | no procede aún |
| ARCH-1 | ataque a la arquitectura, fuera de la propuesta | **hipótesis refutada** |

### Niveles

| Nivel | Qué es | Estado |
|---|---|---|
| 1 — efecto público observado | desarrollo y selección | alcanzado varias veces |
| 2 — candidato confirmado prospectivamente | salas frescas, criterio fijado antes | **ALCANZADO por C1** (fallado 2 veces antes en Plan A) |
| 3 — campaña A→B→C con custodia | único punto donde cabe `transfer3_green` | **ALCANZADO por C1 v2; certificado verde y dos auditorías exactas** |

El nivel 3 exigía un candidato que hubiera pasado el 2. C1 lo hizo y la
campaña independiente final usó el protocolo SHA-256
`3b911b201e23623f6431548a320b486d4f78001ec7bb7407f344834a06da0f14`.
El resto de este documento queda como registro histórico del plan previo.

## Qué se ha demostrado, y qué no

**Demostrado, con artefacto y auditoría:**

- La calibración de un parámetro del cuerpo **se aprende exacta** con 16
  movimientos ejecutados y se transfiere en cinco enteros, sin mapa ni geometría.
- En Plan A el **canal de influencia es un desempate por orden**: no transmite
  magnitud. Un valor puesto a mano produce conducta **idéntica en 256/256 salas**
  al valor aprendido.
- El aislamiento funciona: jaula real, grafo de importación verificado por AST,
  calibración releída tras cada misión.
- El gate funciona con reserva 6: cero violaciones en 1 152 misiones.
- El **compromiso de plan es conductualmente inerte**: energía idéntica dígito a
  dígito en cinco niveles de compromiso.

**No demostrado, y conviene no confundirlo con lo anterior:**

- Que exista transferencia útil en este dominio.
- Que el fracaso de Plan A y el de Plan B tengan **causa común**. Lo afirmé y
  ARCH-1 lo refutó; queda retirado.
- Que la ganancia de actuación pague: B2 reproduce las +4 metas del filtro con
  aprendizaje, pero viola reserva. B2 seguro y B3 quedan en 51/72 frente a
  52/72 nominal. La escuela identifica exactamente la ganancia en ocho
  actuaciones por condición; eso no demuestra utilidad. Tres auditorías
  reproducidas y 261 tests pasan. [Cierre B](TRANSFER3-PLAN-B3-RESULTS.md).

## Lo que falta, en orden

### 1. Plan B de ganancia — ejecutado hasta la parada del cribado

Ya hay contrato previo, escuela desde observaciones, esquema versionado sin
mapa, jaula, dos priors fijos y adjudicación independiente de seguridad.
Se probaron controlador heredado, reserva reparada y frenado observado.
Los tres pilotos fallan; por la regla previa **no se ejecuta confirmación**.
Se preparó N=256, pero no se consume ninguna forma fresca ni campaña real.

No falta repetir el mismo examen con más salas: falta una hipótesis que pase
el cribado sin sacrificar reserva, llegadas ni coste. Retardo y otras primitivas
siguen abiertos, pero no se declaran prometedores sin una prueba del mecanismo.
Esta sesión cierra la rama de ganancia acotada, no todo posible Plan B.

### 2. Plan C, si B falla

Calibración perceptiva. Sin empezar. El contrato exige comprobar antes que no
introduce un canal oracle disimulado ni convierte desconocidos en hechos.

### 3. Deuda técnica que arrastra todo

- **`inventory()` fotografía el árbol** en vez de las dependencias. Invalida
  auditorías anteriores al añadir cualquier módulo. Congelado en v2–v4, así que
  no se editó. B2/B3 ya fijan la clausura conservadora de dependencias; queda
  incorporar esa estrategia al protocolo final.
- **254 MB históricos más 2,74 MB de B2/B3**, sin duplicar los grandes.
- **La suite global no se puede verificar**: agota la memoria en
  `tests/test_dynamic1.py`. Anterior a este trabajo.
- **Acciones de marco mundo**: el agente no tiene marco de cuerpo, así que
  cualquier propiedad asimétrica del cuerpo se diluye con la rotación de la
  sala. Es lo que estropeó B1. Afecta al diseño de cualquier plan futuro.

### 4. Nivel 3 — aquí sí, y sólo aquí, hace falta Roger

**No lo montes todavía.** Sin candidato de nivel 2 no hay nada que sellar.
Cuando lo haya, esto es lo que necesito, y conviene que lo vayas preparando
porque es lo más lento.

**Lo que NO vale como custodia** —está así en el contrato, y `custody_v2`
rechaza campañas reales por eso—: `.gitignore`, otra carpeta, otro repo tuyo,
permisos bajo el mismo usuario. Si un agente que corre como `roger` puede
leerlo, no es custodia.

**Tres niveles, de menos a más sólido:**

1. **Mínimo** — otra cuenta de usuario cuyos ficheros yo no pueda leer, y que no
   uses para lanzarme. Débil si tienes `sudo` a mano, pero es un límite real.
2. **Recomendado** — otra máquina, o un pendrive que sólo conectas para generar
   y para abrir.
3. **Fuerte** — una segunda persona que guarde el secreto y ejecute la apertura.

**Los pasos, en orden estricto. El orden es el mecanismo; invertirlo lo anula:**

1. En el sitio custodio, generas el secreto. Nunca en este repo, nunca pegado en
   el chat:
   `python3 -c "import secrets; print(secrets.token_bytes(32).hex())"`
2. Yo te entrego el protocolo de la campaña y su hash. Tú calculas el compromiso
   con tu secreto y **lo publicas con fecha fuera de este árbol**: un commit en
   un repo que yo no toque, un correo a ti mismo, algo verificable y anterior.
3. Publicas también los compromisos de inventario de B y C, el custodio y la
   referencia de publicación. **Todo esto antes de entrenar el A final.**
4. Yo entreno A y **congelo** el payload.
5. Se abre **B una sola vez**. Si B falla, **C no se abre**, el fallo queda
   registrado y cualquier campaña nueva exige protocolo independiente.
6. Sólo si B pasa, se abre C una vez, bajo la misma congelación.
7. Un cuelgue a mitad **consume** el intento. Es deliberado.

Cuando llegue el momento te doy los comandos exactos y los ficheros concretos.

## Decisiones que son tuyas

1. **Nueva hipótesis de Plan B**, ir a Plan C, o parar la línea de calibración
   del cuerpo. La rama de ganancia ya tiene resultado negativo con aprendizaje.
2. **Autoría concurrente**: coordinar nuevas escrituras antes de otra corrida.
   B2/B3 usan sufijos propios y preservan las 354 rutas congeladas de ARCH-1;
   no se infiere del historial que siga habiendo otro agente activo.
3. **Cuándo montar la custodia.** Mi recomendación sigue siendo: no antes de
   tener candidato de nivel 2.

## Lo que yo cambiaría de mi propio método

Tres errores míos de esta sesión, por si sirven para el próximo contrato:

- **Controles degenerados** en A1: dos de cinco brazos eran la identidad por
  construcción, demostrable sin datos. Ahora los verifico antes de ejecutar.
- **Filtro mal planteado** en B1: exigí a Plan A comprobar que el mecanismo se
  ejercita y luego monté un banco donde no se ejercitaba. El filtro necesitaba
  su propio filtro.
- **Carreras de manifiesto**: tres auditorías invalidadas por crear ficheros
  mientras corrían. Ahora escribo contrato y tests **antes** de ejecutar.

Ninguno de los tres favoreció a un candidato; los tres costaron tiempo.
