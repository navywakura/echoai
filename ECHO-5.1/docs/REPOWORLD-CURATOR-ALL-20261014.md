# RepoWorld · controles oficiales · 14 de octubre de 2026

## Resultado

**36 instancias comprobadas; 35 controles vacío/referencia válidos.** El único
bloqueo es `psf__requests-2674`. El informe agregado está autenticado, pero el
gate `official-controls` permanece **inválido**. No hay puntuación científica
de ECHO, calibración remota ni cierre de ECHO-5.1. El contrato sigue en `design`.
**0 horas nuevas de GPU y 0 llamadas LLM.**

La tanda y su repetición ya finalizaron. Se detuvo el API Podman propio de la
tarea y no quedaron contenedores de evaluación activos.

La tanda `controls-r4` terminó 34/36. Seaborn-3407 falló por un contenedor
residual de la interrupción anterior; tras retirar exclusivamente ese contenedor,
sus dos controles pasaron. `controls-r4-recovered` conserva los 36 intentos
originales y esa repetición de infraestructura. No se repitió ni se promovió
el fallo evaluado de Requests.

## Recuperación de almacenamiento y entornos

El primer balance del usuario, `-dusage=0`, no recuperó grupos. El segundo,
`sudo btrfs balance start -dusage=50,limit=2 /home`, reubicó dos grupos, dejó
1 GiB sin asignar y permitió ampliar metadatos de 7 a 7,5 GiB. Se comprobaron
creación de contenedores y escrituras antes de reanudar. No se necesitaron más
privilegios ni se borraron archivos personales o imágenes ajenas.
La [documentación de Btrfs](https://btrfs.readthedocs.io/en/latest/btrfs-balance.html)
describe los filtros de uso y límite utilizados.

La tarea usa un API Podman rootless propio con
`--storage-opt overlay.ignore_chown_errors=true`. Resuelve la extracción de
archivos de qhull cuyos UID/GID exceden el rango subordinado disponible. Ambos
controles de Matplotlib pasan. Se conserva el digest oficial de imagen, pero
**se declara la adaptación de propietarios**; no equivale a reproducir los UID
de rootful. No se modificó la configuración global de Podman. Véase su
[documentación](https://docs.podman.io/en/latest/markdown/podman.1.html).

La adquisición de imágenes es secuencial. El descarte opcional solo elimina
IDs ausentes antes de adquirirlos; nunca se poda el almacén global. La evaluación
final puede recuperarlas y vuelve a comprobar el digest fijado. Se conservan
los perfiles de httpbin loopback de Requests y de presentación de Pytest-7168.
Los ensayos interrumpidos r1/r2/r3 permanecen como diagnóstico, no como pases.

## Requests-2674: entorno corregible, control negativo no discriminante

Los controles originales de r4 fallan tanto en vacío como en referencia.
La inspección del BASE público identifica dos incompatibilidades ambientales:

1. Las pruebas de conexión esperan timeout contra `10.255.255.1`, mientras
   `network=none` devuelve inmediatamente `ENETUNREACH`.
2. El BASE usa la API histórica `pytest.raises(..., "código")`; la imagen
   incluye pytest 7.4.4, que ya no la admite. La eliminación está
   [documentada por pytest](https://docs.pytest.org/en/9.0.x/deprecations.html).

Un diagnóstico separado incorpora un dispositivo `dummy` y una ruta `/32`
solo dentro del namespace del contenedor. El destino descarta paquetes y produce
un timeout real sin internet; no cambia la red del host ni concede capacidades
administrativas al código probado. También usa pytest 4.6.11 y dependencias
fijadas en un suplemento de solo lectura, su entrypoint compatible y
`--assert=plain`. Las aserciones siguen ejecutándose y no se modifican tests.
La suite pública BASE obtiene **160 pasadas y 1 XPASS**. El suplemento es
experimental; no se incorporó silenciosamente al curador congelado.

La reparación ambiental no permite validar la instancia:

| Configuración | Control | F2P | P2P | `raw_resolved` | Control estricto |
|---|---|---|---|---|---|
| Imagen/perfil de r4 | Vacío | 12/12 pasan | 140/142 pasan | false | Inválido |
| Imagen/perfil de r4 | Referencia | 12/12 pasan | 140/142 pasan | false | Inválido |
| Diagnóstico corregido | Vacío | 12/12 pasan | 142/142 pasan | true | Inválido |
| Diagnóstico corregido | Referencia | 12/12 pasan | 142/142 pasan | true | Válido solo el positivo |

Con el entorno corregido ambos controles también presentan una prueba fallida
fuera de las listas F2P/P2P oficiales. El resumen exporta únicamente cantidades,
no nombres/contenido de pruebas reservadas ni el parche de referencia.

**Esta instancia no discrimina vacío/referencia bajo los entornos comprobados.**
Ni contar únicamente el positivo, ni cambiar las listas del oráculo, ni retirar
la instancia sin revisar el diseño serviría para acreditar el 36/36 solicitado.
El siguiente paso requiere investigar la procedencia de esas listas o preparar
una revisión explícita del registro con una regla de sustitución previa a
cualquier LLM, conservando estos resultados. No se ha aplicado una sustitución.

## Evidencia y verificación

- Preflight público: **36/36**, gate autenticado y fuentes coincidentes.
- Software: **419 pruebas pasadas**, dos integraciones omitidas explícitamente
  en esa suite y ejecutadas después aparte con pase **2/2**. El código de esas
  pruebas y del ejecutor no cambió durante r4.
- Utilidad administrativa de recuperación: **4 pruebas pasadas**, incluyendo
  rechazo de manipulación, deriva de fuentes y conservación de fallos evaluados.
- Smoke simulado: gate válido con regresión, rollback y replay; no resuelve
  científicamente el issue de SymPy.
- Curador: **35/36 válidos**, tras 36 intentos originales y una repetición de
  infraestructura. Los diagnósticos ambientales de Requests son experimentos
  separados y no se incluyen como pases del gate.
- Auditoría final: autenticación y hashes de todos los logs retenidos válidos;
  fuentes del núcleo sin cambios. `custody_valid: true`,
  `official_gate_valid: false`.
- Protección de cuota: una invocación de `calibrate-remote` con proveedor
  deshabilitado se rechazó con `official-controls has not passed`, antes de
  crear el directorio de calibración o contactar con un modelo.

`retry_curator_infrastructure.py` comprueba fuentes, dataset, harness, imagen y
logs antes de repetir exclusivamente errores de infraestructura. Firma el nuevo
intento y el agregado, enlazando el recibo original. Un fallo evaluado permanece
sin cambios y mantiene el agregado inválido. La utilidad y sus pruebas tienen
hashes propios, separados del manifiesto del ejecutor congelado.

Evidencia privada: `ECHO-5.1/artifacts/repoworld-curator-all-20261014/`:
`controls-r4/`, `controls-r4-recovered/`, `requests-diagnostic-receipt/`,
`requests-environment-diagnostic.json`, `retry-tool-tests/` y
`final-evidence-audit.json`. No publicar autoridades HMAC, certificados privados,
pruebas reservadas ni parches oficiales. El
[manifiesto público](swebench/REPOWORLD-CURATOR-PROGRESS-20261014.json)
solo contiene identidades, hashes y resultados agregados.

Los gates locales `/tmp/echo-curator-{software,smoke,preflight}-r2` tienen archivos
completos de recuperación y hashes comprobados. Restaurarlos únicamente en esas
rutas originales si desaparecen: sus autoridades no son trasladables. Las copias
de consulta bajo `artifacts/` no sustituyen a los gates autenticados.

## Checklist de esta entrega

- [x] Recuperar el progreso y completar las 36 instancias del registro.
- [x] Resolver almacenamiento, extracción rootless y contenedor residual.
- [x] Mantener preflight 36/36, software, integraciones y smoke válidos.
- [x] Conservar fallos originales, repetir solo infraestructura y auditar hashes.
- [x] Preparar alias, comando, relay y parada de calibración remota.
- [x] Comprobar que el gate inválido impide iniciar inferencia.
- [x] Mantener 0 GPU / 0 LLM; entrega local sin push.
- [ ] Gate `official-controls` válido 36/36: bloqueado por Requests-2674.
- [ ] Calibración remota y lock científico, después de resolver ese bloqueo.
- [ ] Campaña, evaluación independiente y cierre científico de ECHO-5.1.

[Procedimiento de Gate 3](REPOWORLD-REMOTE-CALIBRATION.md), preparado y **no
habilitado**. Diez minutos es un objetivo de inferencia, no una garantía de cuota
total: descargar y cargar el modelo también consume tiempo de GPU.
