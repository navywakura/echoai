# TRANSFER-3 v4 — cribado a igual presupuesto: ninguna candidata pasa

2026-09-18. **Resultado público negativo conservado. No es B/C reservado.**
[Diseño fijado antes de ejecutar](TRANSFER3-V4-DESIGN.md).

## Qué se implementó

`budget_school.train` termina tras **128 movimientos observados**, no tras
un número de episodios desigual. Cada variante usa 512 unidades simuladas;
no ejecuta una cola de movimientos para descartarla del denominador. La
última escuela puede quedar cortada a mitad de misión, explícitamente rotulada
como corte del banco cinemático, no como llegada, retorno o maniobra de vuelo.
Se conserva la reparación de captura única y no se combinan reward/cobertura.

Se generaron antes del examen 64 geometrías nuevas del generador v2,
excluyendo las 4 A, las 16 públicas anteriores y todos los duplicados internos
bajo traslación, giro/reflexión. **84 geometrías públicas distintas en total.**
Se ejecutaron 256 misiones con consumidor aislado: scratch y tres candidatas.

## Resultado

| Brazo | Metas | Movimientos examen | Escuela + examen | Victorias/derrotas/empates vs scratch | Fallos nuevos |
|---|---:|---:|---:|---|---:|
| Scratch | 62/64 | 1065 | 1065 | — | — |
| Corrected | 62/64 | 1130 | 1258 | 11 / 13 / 40 | 2 |
| Reward only | 63/64 | 1048 | 1176 | 11 / 7 / 46 | 1 |
| Coverage only | 60/64 | 1152 | 1280 | 12 / 14 / 38 | 4 |

Cero colisiones, hechos falsos y violaciones de reserva observados; parámetros
sin cambios en los 256 exámenes. Eso acredita esos checks del banco, no
seguridad física universal ni superioridad de aprendizaje.

Ninguna pasa el cribado preregistrado. p unilateral exacta de signo:
corrected 0,7294; reward 0,2403; coverage 0,7214; umbral para tres candidatas
1/60. No se interpreta «no significativo» como igualdad demostrada.

La recompensa nueva sigue siendo la menos mala de estas tres por métricas
agregadas, **no una candidata aprobada**: introduce fallo en `20264682`, donde
scratch llega en 22 movimientos, y consume 56 antes de abandonar. Su mejora
neta de una meta convive con ese fallo nuevo. Los 17 movimientos menos
agregados no son ahorro homogéneo: entre éxitos conjuntos usa **12 más** que
scratch. Con la escuela sumada, los movimientos son 1176 frente a 1065;
no se demuestra amortización en este bloque.

Mayor cobertura, a igual presupuesto, tampoco sostiene la mejora sugerida
por las 16 salas anteriores: llega a menos metas y genera cuatro fallos nuevos.
No se ajustaron criterios ni se eliminaron esas salas después del resultado.

| Escuela | Características | Pares característica–acción | Características con una sola acción |
|---|---:|---:|---:|
| Corrected | 27 | 38 | 19 |
| Reward only | 27 | 41 | 16 |
| Coverage only | 32 | 57 | 16 |

## Verificación

Informe: `lab/transfer3/rehearsal-v4.json` (trazas completas, escuelas,
payloads, protocolo, hashes de fuentes/tests/diseño, ledger y pares).
El historial v3 y todas sus fuentes guardadas se comprueban sin sobrescribirlos.
9 tests nuevos cubren corte exacto, ausencia de cola oculta, contabilidad,
signo exacto, restricciones del cribado, fallos conjuntos y capacidad de
generación del banco. La regresión completa incluye las versiones previas.

**68 tests pasan**, exit 0. La auditoría en proceso nuevo reejecutó escuelas
y 256 exámenes con consumidor aislado: `replay_valid=true`, exit 0.
Hash canónico del informe:
`dad375cc479021769e45ff17af6605ef62cadcec7aab2f1fdbe3ba119ce00170`.
Es un resultado negativo reproducible, no un certificado del hito.

Desde `echoai/`, con namespaces Bubblewrap habilitados:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rehearsal_v4 audit lab/transfer3/rehearsal-v4.json
PYTHONPATH=.. python3 -m unittest echoai.tests.test_transfer3_v4 echoai.tests.test_transfer3_v3 echoai.tests.test_transfer3_v2 echoai.tests.test_transfer3 echoai.tests.test_transfer3_custody echoai.tests.test_compose1_v3 echoai.tests.test_compose1_v4 -q
```

## Estado de las cuatro fases pedidas

1. **Ventaja fiable:** investigada con presupuesto comparable; no conseguida.
2. **Examen final:** requisitos y cálculo prospectivo documentados en el
   [borrador](TRANSFER3-FINAL-PROTOCOL-DRAFT.md), pero no congelado. La familia
   actual sólo tiene 126 formas y quedan 42 no examinadas; no cabe una campaña
   grande sin ampliar el generador y validar su alcance.
3. **Banco–custodia–auditoría:** sigue incompleto. Hay ensayos criptográficos
   y auditoría conductual, pero no un examinador final integrado que los una.
   No se presenta un plan de implementación como trabajo terminado.
4. **Campaña A→B→C:** no ejecutada ni generada. No hay candidatura válida ni
   protocolo final; custodia externa de Nav pendiente cuando estén listos.

Se solicita revisión independiente
antes de decidir otro cambio de representación/experimento. No se delega
custodia de secretos a un agente con acceso al desarrollo. TRANSFER-3 permanece
abierto, ECHO-3 en 13/15. No se pide aún generar secretos.
