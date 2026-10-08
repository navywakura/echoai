# DREAM-A — primer incremento ejecutado y verificado

2026-09-22. Historial de intentos y replay parcial implementados en el perfil
nominal declarado. Banco de desarrollo válido; **no cierre de DREAM-1, no
Qwen, no auto-mejora medida**. [Contrato previo](ECHO4-DREAM1-A-DESIGN.md).

## Implementación

- `dream_history.py`: archivo privado versionado, esquema y digest estrictos,
  árbol causal sin fusiones por WSP, vistas públicas con revelación parcial,
  handles por sesión, presupuesto y lotes atómicos.
- `dream_history_bench.py`: recolector nativo normal/greedy mediante los
  flags existentes de `ContinuityRun`; un turno por intento, restaurado
  desde el checkpoint del padre. No cambia Q, el agente, gate ni física.
  Registra estado completo en custodia y reconstruye todos los archivos.
- El replay entrega observaciones ya registradas, no estimaciones de T ni
  salidas imaginadas por un modelo. El controlador de este banco es fijo;
  no se ha construido todavía el proponente cortical ni el bucle de promoción.

## Evidencia

| Árbol de desarrollo | Nodos, incluida raíz | Intentos nativos nuevos | Consultas replay | Observados / desconocidos / terminales |
|---|---:|---:|---:|---|
| nominal2 | 15 | 14 | 30 | 14 / 16 / 0 |
| nominal4 | 15 | 14 | 30 | 14 / 16 / 0 |
| terminal | 1 | 0 | 2 | 0 / 0 / 2 |
| Total | 31 | 28 | 62 | 28 / 32 / 2 |

Los 32 desconocidos son consultas sin continuación registrada, no fallos de
predicción ni mundos imaginados. Las dos respuestas terminales consultan la
misma raíz terminal por los dos modos; no son dos muertes adicionales.
Las dos ramas desde cada padre son ejecuciones separadas con memoria propia,
aunque alguna observación coincida.

Los seis grupos del banco pasan: invariantes, igualdad de observaciones,
replay sin ejecución, contabilidad, terminalidad y fuentes/procedencia.
Las vistas completas coinciden con los registros online y con su replay en
un proceso nuevo. Reconstrucción independiente de árboles, checkpoints,
archivos e informe válida, sin hallazgos:

`011cc0d91febda369348997c69f9d46e3a19c089aadf8662e71fbe46eaa7f8aa`

[Informe íntegro](../lab/echo4/dream1-a-v1/report.json).
Mantiene `dream1_green=false`, `qwen_implemented=false`.
No se emite un certificado de mejora por almacenar datos correctamente.

## Costes y procedencia

- Escuela: 64 pasos por contexto, 192 en total; prefijos nativos: 3, 4 y
  37, respectivamente. El corte terminal tiene límite 128, pero muere a 37.
- Recolección posterior: 28 turnos nativos, sin LLM, hechos falsos ni slots
  destruidos; balances correctos y raíces intactas.
- Checkpoints: 24.439.563 + 24.442.254 + 1.631.509 = **50.513.326 bytes**.
- Archivos de historia privados: 10.805 + 10.805 + 6.618 = **28.228 bytes**.
- Replay: 62 consultas, 28 pasos históricos representados; cero nuevos
  turnos del agente y cero llamadas LLM. Lectura/cálculo consumen recursos:
  esto no significa cómputo total gratuito ni mide julios.
- Manifiesto de 66 fuentes. CONT-D conserva sus 62 fuentes y artefactos;
  se vincula su certificado existente, no se repite su examen completo aquí.

Los costes anteriores no incluyen volver a ejecutar las pruebas ni el
auditor. El archivo privado contiene referencias de custodia: **no debe
entregarse entero al LLM ni publicarse automáticamente en Hugging Face**.

## Tests

31 pruebas nuevas pasan, incluidas ejecuciones nativas, replay en proceso
nuevo, archivos alterados y aprobación falsificada. Los fixtures sintéticos
prueban el esquema/API; no se cuentan como intentos del banco nativo.
229 regresiones pertinentes pasan. Se ejecutan además 488 pruebas NEXUS-0:
ocho errores iniciales fueron restricciones de sockets del sandbox; repetidas
con autorización las 29 pruebas GUI implicadas, todas pasan sin cambiar código.
Total: **748 tests distintos, 747 aprobados y un fallo esperado histórico**;
no quedan errores inesperados. No se cuentan dos veces los reintentos.
Ruff pasa en los tres archivos nuevos y `git diff --check` no encuentra errores.

Se comprueba que cambiar o añadir un futuro no revelado no modifica la vista
actual; los IDs públicos tampoco revelan huecos del orden privado. Pedir
padres futuros, exceder presupuesto, duplicar peticiones o introducir tipos
incorrectos no aplica parcialmente un lote. Una vista devuelta no permite
mutar otras sesiones. Tests con los métodos del agente/entorno bloqueados
comprueban que replay no los llama.

## Reproducción

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_dream1a -q
PYTHONPATH=.. python3 -m echoai.echo4.dream_history_bench verify lab/echo4/dream1-a-v1
```

Para una recolección independiente, usar `campaign` con un directorio que
no exista. Nunca sobrescribir este banco. `replay <history.json> <digest>`
solo reproduce el archivo; `verify <directorio>` sí vuelve a ejecutar el
agente para comprobar su origen físico virtual.

## Límites y continuación

Solo perfil nominal y turnos completos. No captura concurrente, aislamiento
de Python hostil, robustez ante cualquier crash ni redistribución de estado.
El consumidor futuro recibirá solo la vista permitida; ejecutar propuestas
arbitrarias en el mismo proceso rompería esa frontera y no está autorizado.
La confianza del custodio y el digest externo son necesarios.

Recompensa nativa, sin objetivos artificialmente premiados: este banco no
demuestra que una estrategia encuentre mejores soluciones. Antes del ensayo
cortical se fijarán tarea de descubrimiento/evaluador discriminantes y
contrato de DREAM-B; después vendrán selección offline y examen nuevo en
DREAM-C/D. No se afirma entrenamiento de pesos, conciencia ni autorreparación.

RELEASE-1 queda en PLAN tras INTEGRATE; hardware después y METAVERSE-1 último.
Sin publicación, subida a Hugging Face, commit ni push en esta entrega.
[README de producto](../echo4/README.md) · [Roadmap](ROADMAP.md).
