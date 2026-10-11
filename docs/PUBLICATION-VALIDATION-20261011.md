# Validación de la distribución pública · 11 de octubre de 2026

La copia pública de ECHO-5 se ha comprobado en entornos Python separados de los
experimentos activos. Se han adaptado las importaciones y la custodia de fuentes
al árbol `core/` de este repositorio. Los algoritmos del laboratorio y sus
resultados históricos no se certifican de nuevo por estas comprobaciones.

El [recibo de comprobaciones](../research-archive/20261011/publication-checks/result.json)
registra `valid: true` y códigos de salida cero para entorno, pruebas de núcleo,
sandbox opcional y sintaxis JavaScript. El hash agregado de fuentes propias
comprobadas es `2e91f4425dfc44c0f1251f79c6599336e756f659d4423f530bd7c4550eddc03a`.

- Suite de núcleo: **338 pruebas recogidas, 326 pasadas y 12 omitidas** por
  requerir el entorno opcional.
- MiniGrid/BabyAI: **32 pruebas pasadas** en su entorno separado. Hay solapamiento
  con las pruebas anteriores; no se suman como 370 casos independientes.
- `node --check src/echo5/web/app.js`: sintaxis válida. No sustituye a una
  prueba nueva de interfaz en navegador.
- La integridad de fuentes propias, módulos heredados y siete archivos `core/`
  permanece sin cambios durante estos checks.

Los [logs y su procedencia](../research-archive/20261011/publication-checks/MANIFEST.json)
declaran la sustitución de rutas locales. Los hashes internos del recibo siguen
refiriéndose a los originales. El manifiesto general `SOURCE-MANIFEST.json`
verifica por separado todos los bytes distribuidos.

No se ha ejecutado otro examen S6 ni un vuelo de confirmación para publicar
esta copia. La calibración del laboratorio conserva sus fuentes congeladas.
El paquete sigue en investigación; los resultados positivos de software no
cambian el resultado negativo del examen Gazebo/PX4 anterior.

[Comandos y límites de portabilidad](../ECHO-5/docs/PUBLICATION-PORTABILITY.md) ·
[Estado científico](PROJECT-CHECKPOINT-20261011.md).
