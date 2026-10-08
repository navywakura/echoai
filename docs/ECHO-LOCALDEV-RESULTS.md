# LOCALDEV-1 — cierre de ingeniería del 2 de octubre de 2026

**VERDE en el perfil de ingeniería descrito en este documento.** Está instalado
`echo-dev`, con mapa de fuentes, ejecución aislada, diagnóstico estructurado,
pruebas CPU y bucle de reparación en una copia. El recibo se cerró a las 17:13
Madrid. Se comprobaron 160 archivos congelados y ninguno cambió. S6 conserva su
estado pendiente; estos resultados no acreditan mejora ARC ni RSI.

| Comprobación | Resultado | Tiempo observado |
|---|---|---|
| Inventario AST | 844/844 archivos Python analizados, cero errores; 14 archivos JS/JSX inventariados | Ejecución local, sin importar módulos |
| Compilación Python | 844 archivos sin errores sintácticos | 2,04 s |
| NEXUS-0, cinco clases seleccionadas | 31/31 pruebas | 10,33 s |
| Primitivas de rejilla | 5/5 grupos de propiedades sobre rejillas generadas con semilla fija | 2,69 s |
| Protocolos RSI con dobles declarados | 12/12 pruebas existentes | 4,64 s |
| Tipos del nuevo arnés | Mypy: sin incidencias en 8 archivos | 2,59 s |
| Integración del arnés | 28/28 pruebas; incluye aislamiento real y límites | 5,20 s |
| Reparación automática de demostración | Fallo inicial → propuesta fallida → propuesta válida; 3/3 pruebas finales y 500 casos generados | 1,05 s |

El perfil `echo-dev run` sumó 22,28 segundos en sus cinco trabajos. Los 28 tests
del arnés y los 48 del perfil suman 76 pruebas seleccionadas. Los tres tests de
la demostración se informan aparte porque son una fixture de reparación. No
se ejecutó la batería completa del repositorio ni se abrieron los exámenes
reservados. Hubo cero llamadas a modelos y cero gasto en inferencia o GPU.

La memoria se mide dentro del trabajador y se contrasta con muestreo del árbol
de procesos. El mayor máximo individual registrado fue 136.676 KiB, en mypy;
el mayor agregado muestreado fue 157.116 KiB. Este último es una observación
cada 100 ms, no un máximo continuo exacto. El test de recursos verifica una
asignación real de 80 MiB y su reflejo en las métricas; otro exige que una
asignación de 512 MiB falle con 256 MiB de espacio virtual permitido. El límite
virtual incluye el intérprete y sus reservas, no solo los objetos Python.

El análisis estático encontró 4.006 aristas de importación, 13 componentes
cíclicos, 264 grupos de cuerpos posiblemente duplicados y 11 posibles stubs.
También señaló 779 llamadas relacionadas con mocks o interfaces externas.
Estas listas son candidatos a revisión, no defectos confirmados. El mapa
completo contiene rutas, líneas, firmas, anotaciones y hashes; el grafo Mermaid
resume conexiones entre paquetes.

La demostración usa un mutador AST determinista sobre un `clamp` defectuoso.
Conserva ambos intentos y el fallo inicial. La copia final pasa y se exporta
como `candidate.patch`; el archivo original mantiene su defecto de fixture,
lo que prueba que el bucle no escribió sobre él. El adaptador HTTP también se
probó contra un servidor local simulado. Su uso con un modelo real queda sujeto
a configuración explícita y a una evaluación posterior de la calidad de las
propuestas. El verde actual no atribuye capacidad creativa a ese mutador.

Las calibraciones permanecen en `lab/localdev/`. La primera rechazó una opción
de Bubblewrap que necesitaba declarar `--unshare-user` explícitamente. Otra
agotó 90 segundos al trazar todas las líneas de la fixture RSI: se conservaron
los mismos doce tests y se retiró ese trazado del perfil; acabaron en 4,64 s.
Mypy y el compilador detectaron una anotación incompleta y un corchete ausente
en el módulo nuevo de propiedades; ambos se corrigieron antes del cierre.
La medición inicial de RSS correspondía al supervisor de Bubblewrap. Se
sustituyó por la medición del trabajador y del árbol, con una prueba específica.
El recibo `closure-20261002.json` sustituye las métricas de
`validation-20261002.json`, que se conserva como evidencia histórica.

El criterio del módulo exige que los controles seleccionados pasen, que el
aislamiento y los límites funcionen en sus pruebas, que no haya suites vacías,
skips o fallos esperados ocultando defectos, que el bucle termine dentro de su
presupuesto y que los originales protegidos conserven sus hashes. El alcance
depende de las pruebas elegidas. La revisión de parches, pruebas adicionales
por módulo y exámenes científicos siguen teniendo funciones distintas.

Evidencia reproducible:

- [Recibo de cierre y hashes de evidencia](../lab/localdev/closure-20261002.json).
- [Resultado del perfil](../lab/localdev/final-20261002/result.json) y [contrato](../lab/localdev/final-20261002/contract.json).
- [28 pruebas de integración](../lab/localdev/closure-integration-tests.log).
- [Resultado del bucle](../lab/localdev/final-demo-20261002/loop/result.json) y [parche](../lab/localdev/final-demo-20261002/loop/candidate.patch).
- [Inventario completo](../lab/localdev/closure-map-20261002/inventory.json) y [grafo Mermaid](../lab/localdev/closure-map-20261002/dependencies.mmd).
- [Custodia de las fuentes congeladas](../lab/localdev/frozen-custody-20261002.json).
- [Instalación, comandos, límites y alcance](ECHO-LOCALDEV-HARNESS.md).
