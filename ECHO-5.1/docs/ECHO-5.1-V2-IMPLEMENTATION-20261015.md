# ECHO-5.1-V2 — interfaz de localización y edición

Estado: núcleo de interfaz V2 implementado y verificado localmente; no cierre científico de ECHO-5.1.
No se ha iniciado Kaggle en esta entrega. El contrato sigue `design`, sin lanzamiento.

## Cambios

- `interface_version: 2` en el contrato; identidad de episodio vinculada a esa
  versión. El API conserva V1 explícita para reproducir fixtures y contratos antiguos.
  Smoke, calibración y campaña propagan la versión a todos los brazos, incluido I2.
- `file_outline`: AST en un subproceso aislado de Python (`-I`), sin ejecutar el
  código candidato, con límites de 1 MiB de fuente, 256 MiB, CPU y tiempo. No es
  un ejecutor de candidatos ni sustituye Bubblewrap. Devuelve símbolos/rangos
  completos, filtrables por clase y paginados con cursor autenticado.
- `patch_apply(path,search,replace)`: una sustitución exacta de líneas completas,
  única y observada íntegramente para el contenido actual del archivo. Sin
  normalización de indentación, prefijos, espacios ni saltos de línea. Rechaza
  archivos protegidos y snapshots obsoletos. AST de Python es un filtro sintáctico
  del parser del supervisor, no prueba de compatibilidad con el runtime ni de
  corrección del issue.
- Compilación interna a diff, comprobación de roundtrip contra el parser estricto
  y staging mediante el CAS/retención/rollback existentes. Ninguna escritura
  directa sobre el checkout del candidato. Una edición por llamada, varias
  llamadas pueden producir un parche agregado.
- Observaciones completas autenticadas por ReceiptStore; unión de líneas sin
  duplicados por ruta/hash de archivo. Conflictos rechazados. Las vistas vuelven
  a ser utilizables cuando un rollback restaura el mismo contenido.
- Proyección de líneas actuales sin recortar líneas. Deduplicación del último
  feedback solo si está completo en la proyección. El tokenizador real sigue
  limitando el prompt a 3.200 y salida a 768: los límites de bytes no son tokens.
- Ocho llamadas por fase de localización en V2 (se reinicia tras retener una
  reparación), sin forzar editor al agotar ese número.
  Dos rescates por formato rechazado; la reserva global no aumenta. E puede
  terminar sin inventar código. El gate efectivo es sobre todas las líneas de
  SEARCH, no un porcentaje del símbolo ni una afirmación del modelo.
- E/E_no_guard pueden reutilizar rechazos exactos de formato y regresiones
  públicas verificadas. Clave SHA-256 completa de snapshot, argumentos, entorno
  y plan de checks; mantiene espacios/indentación. Repetir cobra herramienta y
  generación, pero no aplica otra vez el parche. No cachea como refutación un
  error de infraestructura ni falta de observación.

## Decisiones respecto a la propuesta

No se añade otra CAM con clave HMAC propia ni una jerarquía que confunda
«observado», «aplicado» y «resuelto». La memoria de conceptos entre episodios
existente no se reemplaza; las vistas de fuente permanecen en la sesión y
pueden pasar entre roles dentro de ella. No se transfiere evidencia de lectura
entre repositorios distintos como si sus bytes fueran iguales.

La búsqueda literal se conserva: el nuevo outline proporciona navegación por
símbolos dentro de archivos sin añadir regex arbitrarias. El diagnóstico de
mismatch ofrece una ventana real acotada por ancla, nunca edición fuzzy. No se
convierte ese texto de diagnóstico automáticamente en lectura autorizada: el
agente debe obtener un `file_view` auténtico antes de modificarla.

No se implementa autoalineación, sustitución de múltiples bloques en una sola
llamada ni «cero tokens» por recuperar memoria. El formato estructurado evita
los delimitadores SEARCH/REPLACE dentro de cadenas de código y los contadores
manuales de hunks.

## Verificación y siguiente compuerta

Las pruebas específicas cubren paginación de símbolos, lectura completa exigida,
bytes CRLF/EOF, ambigüedad, sintaxis, ausencia de normalización implícita,
persistencia de recibos, paths protegidos, identidad V1/V2, rollback mock y
rechazos repetidos contabilizados. La suite completa y smoke con SymPy real
se registran en `artifacts/repoworld-interface-v2-20261015/`.

Pendiente tras el código: renovar preflight y enlace del curador al nuevo
manifiesto/contrato, comprobar el helper y hacer una calibración reservada.
Los gates v3 anteriores no autorizan V2. No se atribuirán ventajas de E a
herramientas que no estén disponibles también para S/I2/F, ni se interpretará
un smoke programado como capacidad del 32B. Los antiguos problemas temporales
del test de cancelación siguen sujetos a su verificación independiente.

## Reproducción local

```bash
python3 ECHO-5.1/scripts/run_repoworld.py verify --output <nuevo-directorio>/software
python3 ECHO-5.1/scripts/run_repoworld.py smoke \
  --registry ECHO-5.1/artifacts/repoworld-gates-v3-20261014/registry.json \
  --instance sympy__sympy-19007 \
  --actions ECHO-5.1/docs/swebench/V2-SMOKE-ACTIONS.json \
  --output <nuevo-directorio>/smoke
```

El fixture es público y programado: navega a `_entry`, provoca una regresión
artificial en `Basic.__eq__` y finalmente añade un comentario inocuo. Nunca se
usa como respuesta del proponente real. El outline de la instancia congelada
contiene 19 símbolos y localiza `BlockMatrix._entry` en 235–247; las cifras de
líneas y tokens ilustrativas del briefing no se toman como verdad del archivo.

## Resultados finales de esta fase

- Verify final: **439 pruebas pasadas y 3 opcionales omitidas**, sin fallos;
  RepoWorld 169 pasadas/3 omitidas, PCWorld 257, diseño 13.
- 12 pruebas nuevas de interfaz V2; pruebas V1 conservadas.
- Smoke real de SymPy con proveedor programado: **valid=true**, replay idéntico,
  regresión pública bloqueada, segunda propuesta retenida y fuentes intactas.
- Auditoría: **127 recibos válidos**, dos propuestas aplicables, una regresión
  bloqueada, contabilidad completa. No equivale a resolver el issue.
- `require_gate` valida software-final y smoke-final frente al manifiesto final.
- **0 GPU y 0 llamadas LLM reales**. No push ni campaña ni sellado nuevo.

Se conserva el primer smoke con `source_unchanged=false`: la incorporación del
caso de traspaso invalidó su gate durante la ejecución. No se usa para habilitar
inferencia; el segundo smoke se ejecutó después de congelar las fuentes finales.

### Checklist de continuación

- [x] Navegación AST paginada y edición exacta disponibles para todos los brazos.
- [x] Gate de observación íntegra del SEARCH y traspaso entre roles comprobado.
- [x] Recibos de fuente reutilizables tras rollback y rechazo contextual repetido.
- [x] Suite completa y smoke con Bubblewrap, exportación y auditoría.
- [ ] Renovar 36 entornos/enlace del curador y helper bajo este manifiesto V2.
- [ ] Calibración con el 32B real: localizar, aplicar y evaluar un parche útil.
- [ ] Ablaciones separadas de navegación, edición, memoria y coordinación.
- [ ] Confirmación SWE-bench reservada y auditoría antes del cierre científico.

La memoria entre episodios sigue siendo la biblioteca existente; una nueva
política de transferencia de vistas/fragmentos entre tareas no está implementada.
La proyección es una unión acotada de fuente actual, no el plan completo de
proyecciones por rol del briefing. Ambas extensiones requieren su propia ablación.

### Hashes de evidencia final

- `software-final/report.json`: `641585fb14ff545e1c4dfd3b1e467acd540b4dc1676a402eab13e7b3d56630ec`.
- `smoke-final/report.json`: `51af02fe37cf43f5b94598d0623fd99854765d2045b5c2f121680cb108c689c8`.
- `audit-final.json`: `9a20415e7ad7530ff7f5bf61e7274e31c511e61cd313751def2bb5a091f7c151`.

## Continuación: renovación y modelo real

La fase posterior ya renovó las 36 instancias y enlazó los controles oficiales.
La [calibración V2](REPOWORLD-V2-CALIBRATION-20261015.md) confirma navegación
y lecturas íntegras, pero no generó parches por un bucle de localización.
El checklist histórico anterior corresponde a la entrega de código sin GPU;
el informe enlazado contiene el estado actual y las obligaciones pendientes.
