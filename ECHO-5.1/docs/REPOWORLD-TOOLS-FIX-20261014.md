# RepoWorld: páginas de código con líneas atómicas

Base: `0e70ff8`, rama `research/echo-5.1-pcworld1`.
Implementación y verificaciones locales; **0 GPU, 0 llamadas LLM**.

## Diagnóstico y alcance

La herramienta podía devolver un prefijo como si fuese la línea completa:
`        Matrix` en vez de `        Matrix([\n`. El límite de 380 bytes y
el recorte por búsqueda binaria explican esa observación. Es un defecto real
de interfaz; no demuestra por sí solo que todas las reparaciones fallidas
se debieran a él ni que el modelo vaya a acertar después de corregirlo.

Había además un recorte posterior: protocol.py resumía el feedback JSON de
más de 1.800 bytes con el sanitizador de logs. Ampliar solo tools.py habría
seguido ocultando parte del código al siguiente turno.

## Cambios

- `file_view` devuelve cada línea íntegra, incluyendo LF/CRLF cuando existe;
  conserva también una última línea real sin terminador. Nunca elimina ni
  inventa caracteres para completar la página.
- Capacidad de **2.500 bytes UTF-8 de código**. Una línea que no cabe se deja
  entera para el cursor siguiente. El cursor avanza solo por límites de línea;
  se rechaza un cursor antiguo que apunte dentro de ella.
- Si una línea sola excede el límite de código o de JSON codificado, devuelve
  un error explícito con su número. No devuelve un fragmento ni la omite
  silenciosamente. El usuario/agente puede solicitar otra línea explícitamente.
- La envoltura `file_view` permite hasta **6.000 unidades de contabilidad de
  salida**, con el límite general de 8.192 bytes serializados. Por defecto las
  unidades son bytes UTF-8 de JSON, un límite conservador, no tokens Qwen
  medidos. Se reserva ese máximo y se liquida el coste observado. Las otras
  herramientas conservan su límite de 1.000 unidades.
- `SWE-CONTRACT.json` declara explícitamente esta excepción de lectura. No
  cambia el presupuesto agregado del episodio. El prompt formateado sigue
  pasando por el tokenizer exacto del proveedor y **no se genera si excede
  3.200 tokens**; tampoco aumenta la salida de 768 tokens. No se promete que
  cualquier texto arbitrario quepa: un exceso de contexto sigue rechazado.
- El feedback estructurado de una lectura válida se conserva íntegro en el
  siguiente prompt; ya no pasa por el resumen destinado a logs. Las salidas
  de tests y los demás feedbacks conservan su sanitización.
- Se mantienen autenticación del cursor, autorización del snapshot/rutas,
  límites de lectura (100 líneas), recibos y contabilidad compartida.

## Pruebas

Primero se ejecutaron cuatro nuevas pruebas contra la implementación anterior:
fallaron la página completa, atomicidad/paginación, rechazo explícito de línea
sobredimensionada y conservación del feedback en el prompt. Tras la corrección
pasaron junto a las pruebas existentes de workspace y brazos.

`tests/test_repoworld_tools.py` verifica:

1. Bloque de 40 líneas completas, coste de salida liquidado y cero pendientes.
2. Varias páginas UTF-8/CRLF, texto exacto y última línea sin salto final.
3. Línea demasiado larga: error sin fragmento, congelamiento ni reserva pendiente.
4. Mock de proveedor: las 40 líneas llegan intactas al siguiente prompt.

Las pruebas anteriores de fragmentación de líneas largas se actualizaron al
nuevo contrato atómico. Se conservan paginación Unicode, firma de cursores,
contabilidad y rechazo de contenido que supera la capacidad codificada.

## Comprobación con el archivo real

Se preparó el commit público de `sympy__sympy-19007`, sin oráculo privado,
y se leyó `sympy/matrices/expressions/blockmatrix.py` mediante el dispatcher.
Cada texto se comparó byte a byte con la línea del snapshot.

| Solicitud | Respuesta íntegra | Bytes de código | Unidades de salida | Cursor |
|---|---|---:|---:|---|
| Inicio 220, 40 líneas | 220–259 | 1.280 | 2.615 | Ninguno |
| Inicio 220, 41 líneas | 220–260 | 1.281 | 2.646 | Ninguno |

En ambos casos la línea 225 es exactamente `        Matrix([\n` y la línea
235 contiene `def _entry(`. Cuarenta líneas desde 220 terminan en 259;
para incluir 260 se requieren 41. Las unidades de salida incluyen el JSON,
no solo el código. No se midieron aquí tokens del modelo real.

Evidencia local: `artifacts/repoworld-tools-fix-20261014/real-view-report.json`,
`check_real_view.py`, su log y `software/` para la suite completa.

## Estado experimental

Los gates y locks anteriores corresponden a otras fuentes y no autorizan una
campaña nueva. Hace falta renovarlos antes de repetir calibración y sellado.
Esta entrega no vuelve a ejecutar Kaggle ni atribuye una mejora de acierto:
solo demuestra que la interfaz local entrega ahora el código completo.

## Resultado final de verify

**427 pruebas pasadas, 3 integraciones opcionales omitidas, cero fallos**:
RepoWorld 157 pasadas de 160 descubiertas; PCWorld 257/257; diseño 13/13.
El gate `software-verification` es válido y declara `source_unchanged=true`.
También pasó `git diff --check`. No se iniciaron servicios de inferencia,
no se consumió GPU y no se hizo push.

- SHA-256 `software/report.json`: `2802ac1e214ce3af9f3209df91db4de02631ea1c59e2ab0bf7df049d50eb3571`.
- SHA-256 `real-view-report.json`: `4d51ac19816de6c5e1a2940a274f92243176e2d4ae30e1861abc43514b1a20df`.
