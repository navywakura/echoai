# TRANSFER-3 — índice de todo lo acumulado

2026-09-19. Mapa de entrada a TRANSFER-3, actualizado con la campaña C1 real.
Los hashes históricos se verificaron al crear el índice; B y C de la campaña
verde se auditaron de nuevo en procesos aislados.
Existe porque varias conclusiones han sido **corregidas o retiradas** por
trabajo posterior, y leer un informe sin saberlo lleva a error.

**Estado global (2026-09-19): TRANSFER-3 VERDE en su alcance software.** Plan C1
cerró el nivel 3 con custodia humana, aviso público anterior al congelado y una
campaña A→B→C de 64 salas por partición. B pasó con 38/0 bloques y C con 48/1;
la única pérdida estricta de C no fue atribuible a la calibración. Los dos
exámenes se reprodujeron con hash idéntico. Certificado `8c77aead…`,
`transfer3_green=true`. ECHO-3 queda en 14/15; sólo falta DRONE-3.

## Cómo leer esta tabla

La columna **vigencia** es lo importante:

- **vigente** — sus datos y su conclusión siguen en pie.
- **corregido** — los datos valen, la conclusión no. Lleva aviso en cabecera.
- **superado** — vigente pero reemplazado por una versión posterior.

## Línea de calibración de Q (codex)

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [REHEARSAL-V1](TRANSFER3-REHEARSAL-V1.md) | primer ensayo; scratch sin T no se mueve | superado |
| [REHEARSAL-V2](TRANSFER3-REHEARSAL-V2.md) | Q relativa transferida; sin ventaja | vigente |
| [V3-DESIGN](TRANSFER3-V3-DESIGN.md) · [REHEARSAL-V3](TRANSFER3-REHEARSAL-V3.md) | captura única corregida; Q idéntica | vigente |
| [V4-DESIGN](TRANSFER3-V4-DESIGN.md) · [REHEARSAL-V4](TRANSFER3-REHEARSAL-V4.md) | cribado a igual presupuesto: los tres brazos pierden | vigente |
| [REPAIR-V5](TRANSFER3-REPAIR-V5.md) | reparaciones + diagnóstico de sensibilidad a Q | vigente |
| [PREPARATION](TRANSFER3-PREPARATION.md) · [FINAL-PROTOCOL-DRAFT](TRANSFER3-FINAL-PROTOCOL-DRAFT.md) | custodia y borrador de protocolo | vigente |

## Línea de cobertura y representación (Claude)

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [V6-DESIGN](TRANSFER3-V6-DESIGN.md) · [V6-RESULTS](TRANSFER3-V6-RESULTS.md) | el optimismo por cero **no** era la restricción | vigente |
| [V7-DESIGN](TRANSFER3-V7-DESIGN.md) · [V7-RESULTS](TRANSFER3-V7-RESULTS.md) | el presupuesto no lo es: ×8 compra 2 pares | vigente |
| [V8-DESIGN](TRANSFER3-V8-DESIGN.md) · [V8-RESULTS](TRANSFER3-V8-RESULTS.md) | la diversidad de salas sí sube cobertura; sigue sin pasar | vigente |
| [OPUS5-IMPLEMENTATION](TRANSFER3-IMPLEMENTATION-20260918.md) | registro histórico de v6–v8 | **corregido**: afirma que la feature 504 era el único bloqueo; eran cuatro criterios. Corrección en [A1-DESIGN](TRANSFER3-PLAN-A1-DESIGN.md) |

## Cambio de variable: propiedades del cuerpo

Diseño en [la propuesta de transferencia útil](TRANSFER3-PROPUESTA-TRANSFERENCIA-UTIL.md).

### Plan A — calibración de costes de movimiento · **CERRADO EN ROJO**

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [A1-DESIGN](TRANSFER3-PLAN-A1-DESIGN.md) | contrato + enmienda 1 (reserva 4) | vigente |
| [A1-RESULTS](TRANSFER3-PLAN-A1-RESULTS.md) | rojo en 4 condiciones; dos controles propios degenerados | vigente |
| [A1-V2-DESIGN](TRANSFER3-PLAN-A1-V2-DESIGN.md) · [A1-V2-RESULTS](TRANSFER3-PLAN-A1-V2-RESULTS.md) | enmienda 2: controles corregidos; el contenido es casi **un bit** | vigente |
| [A2-DESIGN](TRANSFER3-PLAN-A2-DESIGN.md) · [A2-RESULTS](TRANSFER3-PLAN-A2-RESULTS.md) | enmienda 3: generador ampliado, jaula real; confirmación **fallida** | vigente |
| [A3-DESIGN](TRANSFER3-PLAN-A3-DESIGN.md) · [A3-RESULTS](TRANSFER3-PLAN-A3-RESULTS.md) | lo transferido es un **prior del programador**, no conocimiento | vigente, con **nota de retractación** de su explicación arquitectónica |

### Plan B — modelo de ejecución · **GANANCIA PROBADA Y ROJA**

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [B1-FILTER](TRANSFER3-PLAN-B1-FILTER.md) | «el modelo perfecto es peor que el equivocado» | **CORREGIDO** por ARCH-1: midió dilución por rotación, no el mecanismo |
| [B2-DESIGN](TRANSFER3-PLAN-B2-DESIGN.md) · [B2-RESULTS](TRANSFER3-PLAN-B2-RESULTS.md) | escuela aprende ganancia; ventaja heredada incumple reserva; reparada queda 51/72 vs 52/72 | vigente |
| [B3-DESIGN](TRANSFER3-PLAN-B3-DESIGN.md) · [B3-RESULTS](TRANSFER3-PLAN-B3-RESULTS.md) | modelar frenado observado no rescata utilidad: 51/72 vs 52/72, sin amortización | vigente; cierre acotado de esta rama |

No se ejecutó confirmación fresca: falló el criterio previo del piloto.
Retardo y otras primitivas de B siguen sin probar; C aún no se había iniciado
en ese corte histórico.

### Plan C — calibración perceptiva · **VERDE (nivel 3)**

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [C1-DESIGN](TRANSFER3-PLAN-C1-DESIGN.md) | contrato: calibración extrínseca de la cámara bajo fusión de dos familias | vigente; **fijado por hash en el protocolo real** |
| [C1-RESULTS](TRANSFER3-PLAN-C1-RESULTS.md) | confirmación sobre 64 salas frescas: 43/0 bloques, p = 2⁻⁴³, invariancia exacta | vigente |
| [C1-CAMPAIGN](TRANSFER3-C1-CAMPAIGN.md) | campaña real: primer intento consumido por infraestructura; protocolo independiente v2 verde | vigente |

Plan B retardo sigue sin probar; se anota como la hipótesis de B más fuerte que
queda, ya innecesaria mientras C1 siga en pie.

### ARCH-1 — ataque a la arquitectura · **HIPÓTESIS REFUTADA**

| Doc | Qué concluyó | Vigencia |
|---|---|---|
| [ARCH1-DESIGN](TRANSFER3-ARCH1-DESIGN.md) | contrato con regla de retractación escrita antes | vigente |
| [ARCH1-RESULTS](TRANSFER3-ARCH1-RESULTS.md) | el compromiso de plan es **inerte**; y B1 estaba mal | vigente |

## Artefactos

Los artefactos históricos y los pilotos conservan `transfer3_green=false`.
Sólo el certificado real de `campaign-c1-v2/` lleva `transfer3_green=true`.

| Artefacto | Tamaño | Hash | Auditado en proceso nuevo |
|---|---:|---|---|
| `rehearsal-v1.json` | 1,5 M | `a994449b…` | sí |
| `rehearsal-v2.json` | 4,3 M | `4babba74…` | sí |
| `rehearsal-v3.json` | 11 M | `e31770e7…` | sí |
| `rehearsal-v4.json` | 28 M | `dad375cc…` | sí |
| `diagnostic-v5.json` | 728 K | `bc8d3143…` | sí |
| `screen-v6-isolated.json` | 18 M | `3e02186b…` | sí, al crearse |
| `screen-v6.json` | 18 M | `10e58541…` | control no aislado |
| `screen-v6-stable.json` | 18 M | `f54c2f4d…` | **sí, vigente** |
| `curve-v7.json` | 55 M | `072b69e1…` | no (ver abajo) |
| `curve-v7-stable.json` | 55 M | `ba071694…` | **sí, vigente** |
| `rooms-v8.json` | 43 M | `7019d0eb…` | sí |
| `plan-a1-margin.json` | 44 K | `704f7f87…` | generador fuera de `nexus0` |
| `plan-a1-screen.json` | 1,5 M | `0553dc7e…` | sí, antes de la enmienda 2 |
| `plan-a1-v2-screen.json` | 1,8 M | `796dc860…` | sí |
| `plan-a2-confirmation.json` | 184 K | `cd87bd6c…` | sí |
| `plan-a3-confirmation.json` | 344 K | `b7a71a07…` | sí |
| `plan-b1-filter.json` | 44 K | `734ab6ae…` | manifiesto incompleto; conservado |
| `plan-b1-filter-v2.json` | 44 K | `82190543…` | sí |
| `arch1-filter.json` | 48 K | `fac99948…` | sí |
| `plan-b2-legacy-pilot.json` | 916 K | `55ad0d77…` | sí |
| `plan-b2-safe-pilot.json` | 913 K | `bcc52638…` | sí |
| `plan-b3-pilot.json` | 911 K | `d88b9666…` | sí |
| `plan-c1-pilot.json` | — | `c4b32b09…` | sí |
| `plan-c1-confirmation.json` | — | `e7a42d81…` | **sí — nivel 2** |
| `campaign-c1-rehearsal/` | — | protocolo `84e19a80…` | ensayo 1, regla estricta: C falla por 1 misión |
| `campaign-c1-rehearsal-v2/` | — | protocolo `aacd35f1…` | ensayo 2, regla atribuible: cadena completa, certificado `rehearsal` |
| `campaign-c1/` | — | protocolo `c9933cac…` | **campaña real consumida sin examen**: `bwrap` bloqueado por el sandbox; C no abierta |
| `campaign-c1-v2/protocol.json` | — | `3b911b20…` | protocolo independiente; 834 formas excluidas |
| `campaign-c1-v2/exam-B.json` | — | `fac69205…` | **pasa**, auditoría `replay_valid=true` |
| `campaign-c1-v2/exam-C.json` | — | `5d4f58de…` | **pasa**, auditoría `replay_valid=true`; 1 pérdida estricta, 0 atribuibles |
| `campaign-c1-v2/certificate.json` | — | `8c77aead…` | **`transfer3_green=true`** |

254 MB históricos más 2,74 MB nuevos. Los artefactos grandes de v4–v8
dominan el volumen; no se han duplicado para B2/B3.

## Defecto del arnés histórico; corregido en las nuevas versiones B2/B3

`rehearsal.inventory()` fotografía **todo** el árbol `nexus0/**/*.py` en vez de
las dependencias de la corrida. Consecuencia: **añadir cualquier módulo nuevo
invalida la reproducción de todos los informes anteriores**, aunque ninguna de
sus dependencias haya cambiado.

Me costó tres auditorías durante la sesión. Está documentado en
[V8-RESULTS](TRANSFER3-V8-RESULTS.md); no se corrige porque `inventory()`
pertenece al inventario congelado de v2, v3 y v4. Los artefactos `-stable`
existen por esto. **El protocolo final debería fijar el conjunto de dependencias
de cada corrida en vez de fotografiar el árbol.**

B2/B3 ya usan clausura conservadora de imports y entradas explícitas (71/76
dependencias), sin editar el arnés congelado. Añadir B3 no invalidó las
auditorías B2. Las 354 rutas guardadas por ARCH-1 conservan sus hashes; esto
no equivale a reejecutar hoy todas las auditorías históricas.

## Código

Regresión actual: 19 ficheros de test, **308 tests en verde** (25 C1 y 22 de campaña nuevos). Antes: 17 ficheros, 261 tests, incluidos los
27 nuevos de B2/B3. El recuento anterior era 234.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_arch1 tests.test_transfer3_b1 \
  tests.test_transfer3_a3 tests.test_transfer3_a2 tests.test_transfer3_a1_v2 \
  tests.test_transfer3_a1 tests.test_transfer3_v8 tests.test_transfer3_v7 \
  tests.test_transfer3_v6 tests.test_transfer3_v5 tests.test_transfer3_v4 \
  tests.test_transfer3_v3 tests.test_transfer3_v2 tests.test_transfer3 \
  tests.test_transfer3_custody tests.test_transfer3_b2 tests.test_transfer3_b3 -q
```

La suite global del repositorio **no** está verificada: agota la memoria en
`tests/test_dynamic1.py`, séptimo fichero por orden. Es anterior a este trabajo.

## Infraestructura reutilizable

Lo que queda construido y vale para cualquier plan futuro:

- **Generador de dos paredes** (`space_a2`): 11 638 formas canónicas, solapamiento
  cero con las 92 históricas; quedan más de 11 000 sin usar.
- **Jaula aislada** (`transport_a2`, `consumer_a2`): 17 módulos montados, cero
  simulador, grafo de importación del agente verificado por AST.
- **Adjudicador externo de reserva** con costes verdaderos.
- **Arnés de escuela y examen**, comparación emparejada, signo exacto y McNemar.
- **Alineación de salas** (`gain_b1`) para que un mecanismo de marco mundo se
  ejercite en lugar de diluirse.
