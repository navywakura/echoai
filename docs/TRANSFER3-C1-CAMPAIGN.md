# TRANSFER-3 — campaña sellada de C1: lo que necesito de Nav

2026-09-19. **CAMPAÑA COMPLETADA; este documento conserva el procedimiento.**
El candidato estaba confirmado prospectivamente (nivel 2):
[resultados de C1](TRANSFER3-PLAN-C1-RESULTS.md). Nav ejecutó la custodia y la
campaña independiente final `campaign-c1-v2/` emitió un certificado verde.

La primera campaña real, bajo el protocolo `c9933cac…`, quedó consumida antes
de evaluar una sala porque el sandbox negó a `bwrap` un socket `NETLINK_ROUTE`.
C no se abrió. El reintento no reutilizó salas ni pestillos: se generó el
protocolo independiente `3b911b20…`, que excluyó las 64 salas B reveladas.
En él B pasó 38/0 bloques y C 48/1, con 0 pérdidas atribuibles en ambas; los dos
exámenes se auditaron con hash idéntico. Certificado `8c77aead…`,
`transfer3_green=true`.

La maquinaria está construida y **ensayada de punta a punta** con un secreto
público (ver al final). No hace falta que entiendas el código: sólo seguir los
pasos en orden. **El orden es el mecanismo; invertirlo lo anula.**

## Por qué no puedo hacerlo yo

Si yo genero el secreto, podría conocer las salas de B y C antes de congelar el
candidato, y el examen dejaría de ser independiente. Da igual que no lo hiciera:
nadie podría comprobarlo. La custodia existe para que no haga falta fiarse de mí.

## Qué NO vale como custodia

Cualquier sitio que un agente que corre como `roger` pueda leer: otra carpeta,
`.gitignore`, otro repo tuyo en este disco, permisos bajo el mismo usuario. Si yo
puedo leer `bundle.json`, no es custodia.

**Vale**, de menos a más sólido: otra cuenta de usuario del sistema cuyos
ficheros yo no pueda leer y que no uses para lanzarme; **otra máquina** o un
pendrive que sólo conectas para estos pasos (recomendado); o una segunda persona
que guarde el secreto.

## Paso 0 — preparar la máquina custodio

1. Copia a la máquina custodio el directorio `REALRXOS/RXos` completo, **sin**
   nada de `lab/transfer3/` salvo `campaign-c1/protocol.json`. El código de
   `transfer3` no está en git: hay que copiarlo del árbol de trabajo.
2. Usa **Python 3.14.6**, la misma versión. Las salas se generan con
   `random.Random(semilla)` y otra versión podría producir salas distintas. Si
   pasara, el examen **fallaría cerrado** —rechazaría la revelación, no aprobaría
   nada falso—, pero la campaña se perdería.
3. Comprueba que tu copia es exactamente el código que el protocolo fija:

   ```sh
   cd RXos/echoai
   PYTHONPATH=.. python3 -c "import json; from echoai.nexus0.transfer3 import bench_c1; \
   bench_c1.verify_manifest(json.load(open('lab/transfer3/campaign-c1/protocol.json'))['examiner_manifest']); \
   print('copia verificada')"
   ```

   Si no dice `copia verificada`, para y avísame.

## Paso 1 — tú, en la máquina custodio: crear el secreto

```sh
mkdir -p ~/custodia && chmod 700 ~/custodia
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custodian_c1 init ~/custodia/bundle.json
```

`bundle.json` contiene el secreto y dos sales. **No lo copies nunca a donde yo
pueda leerlo, ni lo pegues en el chat.**

## Paso 2 — tú: comprometer y PUBLICAR el aviso

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custodian_c1 commit \
  ~/custodia/bundle.json lab/transfer3/campaign-c1/protocol.json ~/custodia/notice.json \
  --custodian "Nav" --publication-reference "DONDE_LO_PUBLICAS"
```

`notice.json` es **público**: sólo lleva compromisos, ni semillas ni secreto.

**Publícalo con fecha fuera de este árbol antes de dármelo**: un correo a ti
mismo, un commit en un repositorio que yo no toque, un gist. Pon esa referencia
en `--publication-reference`. Es lo que demuestra que el aviso existía antes de
que yo congelase nada.

Luego dame `notice.json`. Sólo ese fichero.

## Paso 3 — yo: congelar el candidato

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.campaign_c1 freeze \
  notice.json lab/transfer3/campaign-c1/protocol.json \
  lab/transfer3/campaign-c1/latches lab/transfer3/campaign-c1/freeze.json
```

Entreno A, congelo los nueve payloads y los ato al hash de tu aviso. **Te doy el
hash `payloads_sha256`.** Guárdalo: prueba que congelé antes de ver B.

## Paso 4 — tú: revelar B

Sólo **después** de tener mi hash del paso 3:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custodian_c1 reveal \
  ~/custodia/bundle.json lab/transfer3/campaign-c1/protocol.json B ~/custodia/reveal-B.json
```

Dame `reveal-B.json`. Lleva las semillas y la sal de B; no revela nada de C.

## Paso 5 — yo: examinar B, una sola vez

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.campaign_c1 exam B \
  notice.json lab/transfer3/campaign-c1/protocol.json lab/transfer3/campaign-c1/freeze.json \
  reveal-B.json lab/transfer3/campaign-c1/latches lab/transfer3/campaign-c1/exam-B.json
```

Antes de tocar una sala verifica tu revelación contra el compromiso publicado y
regenera cada sala desde su semilla. Un cuelgue a mitad **consume** B: es
deliberado. Te doy el veredicto y el fichero `exam-B.json`, que puedes leer tú.

**Si B no pasa, aquí se acaba. No reveles C.** El fallo queda registrado y
cualquier intento nuevo necesita protocolo nuevo.

## Paso 6 — tú: revelar C, sólo si B pasó

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custodian_c1 reveal \
  ~/custodia/bundle.json lab/transfer3/campaign-c1/protocol.json C ~/custodia/reveal-C.json
```

## Paso 7 — yo: examinar C

Igual que B, con `--prior lab/transfer3/campaign-c1/exam-B.json`. El arnés se
niega a abrir C sin un B aprobado del mismo congelado, y esa negativa no gasta
el pestillo de C.

## Paso 8 — tú: revelar el secreto, sólo después de C

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.custodian_c1 secret \
  ~/custodia/bundle.json ~/custodia/secret.json
```

Dame `secret.json`. A partir de aquí el secreto es público, y eso es lo que
permite a cualquiera verificar que el protocolo se comprometió antes y que las
salas son **exactamente** las que ese secreto produce: nadie las eligió después.

## Paso 9 — yo: certificar

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.campaign_c1 certify \
  notice.json lab/transfer3/campaign-c1/protocol.json lab/transfer3/campaign-c1/freeze.json \
  lab/transfer3/campaign-c1/exam-B.json lab/transfer3/campaign-c1/exam-C.json \
  secret.json lab/transfer3/campaign-c1/certificate.json
```

Sólo aquí puede aparecer `transfer3_green = true`, y sólo si B y C pasan, el
aviso es de tipo `campaign`, el protocolo se comprometió con ese secreto y las
salas son las que produce.

## Qué dirá el certificado, y qué no

**Dirá**: que un parámetro del cuerpo aprendido en A mejora las misiones en B y C
frente al mismo agente sin él, en salas que nadie pudo elegir, con custodia
externa.

**No dirá**: nada sobre hardware, HIL, vuelo real ni DRONE-3. Un desplazamiento
de una celda son 3 metros: el resultado es sobre el mecanismo en un mundo
discretizado. Mundo estático, sensores sin ruido. Y su validez depende de que
hicieras de verdad los pasos 1–2 donde yo no puedo leer.

## Tamaño, coste y criterios

B y C: **64 salas cada una**, nueve desplazamientos por sala. Del orden de 2 000
misiones enjauladas por partición, unos 15–20 minutos cada examen en esta
máquina. α ≤ 1/240 en cada partición; C sólo cuenta si B pasa.

Criterios que **bloquean**: restricciones duras en todos los brazos, **ninguna
pérdida atribuible a la calibración**, más misiones que el nominal, amortización,
más allá de los priors fijos, y significación.

### Enmienda decidida antes del protocolo real

El primer ensayo encontró que la regla estricta de C1 —«el aprendido nunca
pierde una misión que complete el nominal descalibrado»— falló una vez en 1 080
misiones de C1, y **esa pérdida no la causó la calibración**: en esa sala el
agente con calibración **perfecta** también fracasa, y el descalibrado llegó
por suerte. Pérdidas atribuibles a la calibración en todos los datos de C1:
**0 de 1 080**. Extrapolada, la regla estricta suspendería una campaña real con
probabilidad ≈ 0,66 sólo por la suerte del control.

La campaña bloquea por tanto con la regla **atribuible**: el aprendido no puede
perder ninguna misión que complete un agente con el desplazamiento **verdadero**
(brazo `oracle`, cota externa, sometido a las mismas restricciones duras). La
cifra estricta **se sigue calculando y publicando**; sólo deja de bloquear.

Debilidad que se declara: la regla atribuible comprueba que la calibración
transferida es correcta, no que el aprendido gane cada misión. La ventaja la
sigue exigiendo la prueba de signo por bloques, que ya cuenta los bloques
perdidos.

## No toques estos ficheros hasta cerrar la campaña

El protocolo fija el hash de cada fichero del examinador: `campaign_c1.py`,
`custodian_c1.py`, `bench_c1.py`, `calib_c1.py`, `planner_c1.py`, el
consumidor, la jaula, sus dependencias, `tests/test_transfer3_campaign_c1.py` y
`docs/TRANSFER3-PLAN-C1-DESIGN.md`. Si cualquiera cambia, el examen se niega a
correr. Es deliberado: garantiza que examina exactamente el código comprometido.

Las dependencias van **más allá de `transfer3/`**. Incluyen el núcleo de
NEXUS-0: `nexus0/encoder.py`, `lex.py`, `qtable.py`, `gate.py`, `loop.py`,
`env.py`, `types.py`, además de `compose1*/`, `fusion1/`, `sim3/` y los cinco
`RXos/navi10_*.py`. **Portar `wsp_lex` al encoder** **rompería la campaña**: tiene que esperar a que cierre. La lista
exacta está en `examiner_manifest` del protocolo, y la orden del paso 0 dice en
un segundo si el árbol sigue intacto.

## Ensayos ya hechos

Toda la cadena —protocolo, compromiso, congelado, examen de B, examen de C,
certificado— se ejecutó dos veces con el secreto público de ensayo, aviso de
tipo `rehearsal`. Un ensayo **no puede** certificar verde, y así lo verifica su
propio test.

- **Ensayo 1** (`lab/transfer3/campaign-c1-rehearsal/`), regla estricta: B pasa;
  C falla por **una** misión perdida por suerte del control. Es lo que motivó la
  enmienda. Se conserva tal cual.
- **Ensayo 2** (`lab/transfer3/campaign-c1-rehearsal-v2/`), regla atribuible,
  sobre salas distintas porque el protocolo excluye las del ensayo 1: resultado
  en [resultados de C1](TRANSFER3-PLAN-C1-RESULTS.md).

## Protocolo real original, consumido sin examen

`lab/transfer3/campaign-c1/protocol.json`

```text
SHA-256  c9933cacaee356c7161d8cc1adb9a9b5508c0dd62e70d6781432607adedc2add
tipo     campaign     B = 64    C = 64    alpha <= 1/240
bloquea  hard_constraints, no_attributable_failures, more_missions,
         amortised, beyond_fixed_priors, significant
reporta  no_new_failures  (regla estricta, sin bloquear)
excluye  770 formas públicas, incluidas las salas de ambos ensayos
fija     69 ficheros del examinador por hash
```

Anota ese SHA-256 fuera de este árbol **antes** de empezar. Es lo que tu
compromiso del paso 2 ata: si el fichero cambiara después, tu aviso dejaría de
comprometerse con él y el examen se negaría a correr.

Los 69 ficheros incluyen cinco `navi10_*.py` que viven en `RXos/`, fuera de
`echoai/`: por eso el paso 0 copia `RXos` entero.

## Protocolo independiente final y certificado

Tras conservar el fallo de infraestructura, el nuevo protocolo excluyó las 64
salas B ya reveladas además de las 770 formas anteriores:

```text
protocolo  lab/transfer3/campaign-c1-v2/protocol.json
SHA-256    3b911b201e23623f6431548a320b486d4f78001ec7bb7407f344834a06da0f14
aviso      eeee7f80be646b7ea91972f1baa75bb2de32d0a0de55cccfec8ef91444a701be
freeze     c73b751010ee24e6d7e77c2f33b857f52e29d9524936c0bde5ac0592c5f2c613
examen B   fac69205f205d5c59e709f198d4a5983e08efe826c2a3a917123e8d431f3900c
examen C   5d4f58de861922e7a7843c90afea18a43cd464fc8d1076ac8ef5f9caaeaec42f
certificado 8c77aead2ccdfcc846f39cb2151364f67699988d422df4812786af7eedc39cd2
```

B y C tienen auditorías `replay_valid=true` con esos mismos hashes. El
certificado final lleva `kind=campaign` y `transfer3_green=true`.
