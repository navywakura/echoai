# Verificación del guardado del 10 de octubre de 2026

La sincronización conserva las novedades del laboratorio en
`navywakura/echoai`, manteniendo las adaptaciones previas de la distribución:
auxiliares bajo `core/`, instalador y echo-nexus 1.5.2. No inicia ECHO-5,
no cambia las fuentes congeladas de B24 ni repite una campaña científica.

La selección de comprobaciones en la copia oficial ejecutó **100 pruebas,
todas aprobadas**, en Python 3.12: integridad del instalador, núcleo/Q,
observador, buscador B24, runner, revisión y custodia del cierre ARC/B24.
Comando, desde la copia oficial con su padre en `PYTHONPATH`:

```sh
python3.12 -m unittest \
  tests.test_source_setup \
  tests.test_nexus0.TestWorld tests.test_nexus0.TestTConf \
  tests.test_nexus0.TestGate tests.test_nexus0.TestBench tests.test_qtable \
  tests.test_observe tests.test_s6b24_search tests.test_s6b24_runner \
  tests.test_s6b24_review tests.test_arc_b24_closure
```

`make check` comprueba la preparación de ECHO-5 tanto en el laboratorio como
en la copia oficial: Python 3.12.13, tres archivos Python y
`capabilities_validated=false`. No existen todavía pruebas de capacidades
ECHO-5. La revisión estática analiza 22 archivos Python activos nuevos o
actualizados y comprueba 19 enlaces locales en los documentos nuevos.

La batería ampliada del laboratorio ejecutó 101 pruebas, con 100 aprobadas
y una omisión explícita del validador nativo configurado aparte. Además,
su invocación genérica produjo un error en `setUpClass` de R1Package:
faltaba `B24_R1_TEST_PROJECT`. Esa clase exige importar las fuentes del ZIP
aislado, no las del workspace. Se repitió únicamente esa clase desde una
extracción temporal verificada del ZIP, con operaciones de red, procesos
nativos y partidas científicas prohibidas.

La repetición aislada ejecutó ocho pruebas: siete pasaron y una falló.
`test_dataset_has_exact_native_bytes_and_fresh_private_references` supone
que `dataset_sources` contiene solo el dataset del lanzamiento inicial.
El notebook reanudado v3 tiene ese dataset y el dataset de checkpoint.
Se comprobó por separado que ambas referencias coinciden exactamente con
sus metadatos actuales. El fallo refleja el alcance antiguo de esa
aserción; se conserva el resultado y no se cambia la prueba congelada ni
se informa de un pase global de todos los tests.

Se verificaron los hashes de las 100 fuentes originales de B24: cero
cambios. El paquete R1 aislado conserva su SHA-256
`d68e890ce70b4400a6a8e046ef48f536a5fdeac9b5e8674625f8d6bfb1fb611d`.

La copia de investigación verifica las 725 rutas lógicas mediante 465
archivos únicos y sus hashes. Se revisaron también los contenidos de los
archivos comprimidos: 14.308 miembros, con cero coincidencias de los
patrones de credenciales buscados. Esta búsqueda es una comprobación
acotada, no una garantía universal de ausencia de información sensible.
No se distribuyen las claves locales ni los entornos virtuales.

Una extracción histórica fallida de R1 conserva un error de indentación.
Se identifica en el README del archivo de investigación y permanece con
sus bytes originales. Los resultados negativos y los errores anteriores
forman parte del expediente guardado.

`SOURCE-MANIFEST.json` se actualiza para verificar los archivos de la
distribución. La integridad de Git y del manifiesto permite comprobar la
copia; no acredita transferencia ARC, S6, RSI o una capacidad nueva de ECHO-5.
