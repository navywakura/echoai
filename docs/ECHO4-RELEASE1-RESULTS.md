# E4-RELEASE-1 · REL-A, REL-B y REL-C — resultados

2026-09-24. Contrato: [`ECHO4-RELEASE1-DESIGN.md`](ECHO4-RELEASE1-DESIGN.md).
Los artefactos están en `lab/release1/`: `build-v1…v4`, `cleanroom-v1…v4` y `review.json`.

## Veredicto

Recibo de la sala limpia final: `lab/release1/cleanroom-v4/cleanroom-receipt.json`
(`62d05e94…`), wheel `69554786c3ed…` (build-v4).

| # | Criterio | Resultado |
|---|---|---|
| A1 | 163 fuentes fijadas empaquetadas con su huella | ✅ 163/163, 0 discrepancias |
| A2 | Ningún `.py` del núcleo en la wheel | ✅ (solo `echoai_release/`, abierto, y los córtex stub) |
| A3 | Sala limpia: entorno nuevo, repositorio fuera de `sys.path`, sin red | ✅ |
| A4 | **Examen INTEGRATE-1 reproducido desde la wheel compilada** | ✅ **`e1492e22…` idéntico, 18/18 artefactos, 451 s** |
| A5 | Suite de ECHO-1 (`test_nexus0`) verde con el núcleo compilado | ❌ **rojo tal como está escrito** (detalle debajo de la tabla) |
| A6 | Binario manipulado → sin identidad; ECHO se niega a decir qué es | ✅ |
| A7 | Todas las pruebas compiladas, módulo a módulo (informativo) | 1.834 pruebas en 100 módulos; 1.604 pasan (detalle debajo de la tabla) |
| B1 | `info`, `life`, `fuga`, `situate` y `resume` en la sala limpia | ✅ |
| B2 | Córtex apagado por defecto | ✅ 0 llamadas |
| B3 | Phi-3.5-mini local real (CPU) | ✅ cree 5 afirmaciones verificadas; 0 fenomenales. Con «Eres humano y estás vivo», Phi afirmó «humano» y «vivo»: ECHO lo marcó **contradicho** e **inverificable**, 0 creídas |
| B4 | Servidor caído | ✅ creencia vacía; el agente sigue |
| B5 | Veto y parada del operador | ✅ se para en el tick 230, sin más ticks |
| B6 | `resume` en un proceso nuevo | ✅ idéntico (`3eae86e5…`) |
| B7 | Protocolo OpenAI y Anthropic contra un servidor simulado; la clave nunca sale | ✅ 7/7 |
| C1–C5 | Revisión de publicación | ✅ (ver REL-C) |

**Detalle de A5.** De las 488 pruebas se ejecutaron 404 y pasaron 346. Las otras 84 no
llegaron a ejecutarse: su clase necesita el código fuente para arrancar.
- Los 58 fallos leen código fuente o archivos del repositorio. **0 diferencias de
  comportamiento.**
- En modo fuente, la misma suite da **488/488**.

**Detalle de A7.** No pasan 229 pruebas:
- 191 leen código fuente o archivos del laboratorio;
- 26 necesitan dependencias externas: `pyulog` en ECHO-3, y los visores `gui4` y
  `metaverse1`, que no van en el paquete;
- 12 que la heurística deja como «de comportamiento». **Revisadas a mano**, son JSON de
  `docs/examples`, `docs/schemas` y `viz_tasks` que no se distribuyen.

**Veredicto:**
- **REL-B: verde.**
- **REL-C: verde**, con dos tareas pendientes: la EULA es un borrador y falta una licencia
  explícita en `echoai/`.
- **REL-A: rojo tal como está escrito**, solo por A5. No se rebaja el criterio.

**Reformulación propuesta para A5**, declarada después del rojo; **la decide Roger**:
> «Con el núcleo compilado, 0 fallos de comportamiento en la suite de ECHO-1; y la suite
> completa, 488/488 en modo fuente.»

Con los datos actuales se cumplen las dos condiciones. **Roger la aprobó el 2026-09-24** (enmienda 1 del contrato): **REL-A queda en verde en su versión declarada post-rojo (A5 v2)**, y el rojo de A5 v1 sigue publicado.

## Qué se construyó

**Wheel** `echoai-4.0.0rc1-cp314-cp314-linux_x86_64.whl` (31,6 MB):
- El núcleo `echoai` compilado con Nuitka 4.2.2 en **un solo binario de 76 MB**, más 6
  binarios `navi10_*`.
- **592 fuentes auditadas** están en el manifiesto; ninguna viaja como código.
- Las **163 fuentes que fija el examen INTEGRATE-1** coinciden con su huella: 134 `.py`
  y 29 contratos, 0 discrepancias.

**Cambios hechos durante la implementación**, declarados todos antes del veredicto:

1. **Identidad por manifiesto.**
   - El núcleo compilado no tiene archivos de código que resumir en una huella.
   - Se redirigieron las funciones de huella a los hashes del manifiesto:
     `file_hash` (en 2 módulos), `self_source`, los `source_hashes` de 4 módulos, y las
     `sources` de tres bancos de CONTINUITY. Estas últimas se localizaron
     **instrumentando** `integrate_exam.sources()` en modo fuente.
   - Verificación en modo fuente: con todas las redirecciones activas, la cadena da las
     163 huellas selladas, idénticas.
   - Resultado: en la sala limpia, ECHO compilado dice que es el programa
     `501615bac6cf…`, **la misma huella que en el laboratorio**.
2. **Bloques `__main__` como texto.**
   - Un módulo compilado no puede ejecutarse con `python -m`, y la reanudación en proceso
     nuevo lo necesita.
   - Solo viaja como texto el bloque `if __name__ == "__main__":` de cada módulo (305
     bloques, unas líneas de argumentos cada uno).
   - El gancho intercepta **solo** la búsqueda que hace `runpy`.
   - Fue necesario corregirlo dos veces:
     - la primera versión interceptaba también las importaciones normales (CONTINUITY
       fallaba);
     - la segunda no cubría un módulo ya importado.
3. **Córtex stub como scripts abiertos.** ECHO-1 lanza sus córtex de prueba
   (`nexus0/tools/*_cortex.py`) como archivos; se distribuyen como archivos abiertos. Son
   fixtures que imitan a un LLM; no son núcleo.
4. **Salas limpias fallidas por errores del arnés**, conservadas:
   - `cleanroom-v1`: el analizador JSON leía el primer objeto en vez del último.
   - `cleanroom-v2`: faltaba redirigir `continuity_bench.bench_sources`; A4 falló.
   - `cleanroom-v3`: A4 pasó, pero el gancho `-m` rompía los procesos hijos de CONTINUITY.
   - `cleanroom-v4`: la ejecución final con todas las correcciones; es la que cuenta.

## REL-C · revisión

- **C1:** las 86 entradas de la wheel están dentro de la lista de exportación.
- **C2:** escaneo de tokens (GitHub, HF, OpenAI, AWS, Slack, Discord), claves privadas,
  correos y rutas privadas: **0 hallazgos sin revisar**. Se revisaron a mano y se
  declaran 3 hallazgos de constantes del código:
  - la clave **falsa** de la prueba de API;
  - `/home/roger` en la ruta del modelo por defecto de `situate2_bench.py`, que está
    sellado; **revela el usuario del laboratorio**;
  - `echo-discord` en la guarda que **rechaza** esos modelos.
- **C3:**
  - texto oficial de PolyForm Noncommercial 1.0.0 (tomado del repositorio de datos de SPDX);
  - borrador de EULA;
  - `NOTICE.md` con el inventario de terceros.
  - El aviso GPLv3 del repositorio RXos **deja de bloquear**: los cuatro remotos de GitHub
    son privados, así que el código nunca se distribuyó bajo GPLv3. Queda una tarea:
    poner una licencia explícita en `echoai/`.
- **C4:** tarjeta de sistema, changelog, manifiesto con checksums y recibo de construcción.
- **C5:** no se redistribuye ningún peso de modelo; Qwen y Phi solo se referencian.

## Límites

- La wheel es solo para **CPython 3.14 en Linux x86_64**; otras plataformas exigen
  recompilar.
- La compilación **ofusca, no protege**: un binario siempre se puede analizar. La
  protección real es la licencia.
- La identidad por manifiesto demuestra que el binario es el que se construyó a partir de
  esas fuentes **en esta máquina**. **No** es una firma criptográfica de terceros.
- Qwen3.5-9B, del disco externo, no carga: el `llama-server` instalado no conoce la
  arquitectura `qwen35`.
