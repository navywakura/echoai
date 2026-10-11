# ECHO-5 — expediente público del 12 de octubre

**5.0.0 verde dentro del alcance validado.**

- [Veredicto de cierre r3](closure-verdict-20261011-r3/result.json): todos los criterios satisfechos.
- [Confirmación cognitiva](closure-confirmation-20261011-r3/result.json) y [auditoría](closure-confirmation-20261011-r3/audit.json).
- [Gazebo/PX4: informe](sitl-confirmation-20261011-r3/report.json) y [auditoría](sitl-confirmation-20261011-r3/audit.json): simulación, no hardware.
- [Piloto posterior de eficiencia](efficiency-pilot-20261012-r3/result.json): cuatro etapas y auditorías separadas.
- [Comprobaciones del laboratorio](efficiency-checks-20261012-r4/result.json).
- [Resultados completos y límites](../../ECHO-5/docs/SEARCH-EFFICIENCY-RESULTS-20261012.md).

Los cuatro resultados completos están en las subcarpetas del piloto. Los mayores
se comprimen como `result.json.gz`: descargar y abrir con `gzip -dc` o Python
`gzip.open`. Los resultados negativos y abstenciones se conservan dentro de ellos.
Este export no contiene el entorno completo, imágenes de simulación, ULogs ni
journals encadenados. La auditoría exportada informa de la ejecución original;
no puede repetirse íntegramente a partir de este subconjunto.

[MANIFEST.json](MANIFEST.json) registra SHA-256 de bytes originales y exportados.
Las rutas absolutas privadas se sustituyen por marcadores y se normaliza JSON;
los hashes embebidos siguen identificando los originales. El cierre r3 y el piloto
posterior congelaron fuentes distintas. Las adaptaciones públicas a `core/`
tienen nuevas identidades: las comprobaciones de publicación se registran aparte.

S6 queda abierto hasta después de 5.5. No se declara ausencia universal de errores,
una ventaja informativa no activada ni superioridad estadística general.

## Comprobación nueva de la distribución pública

[Recibo](publication-checks/result.json) y logs: 502 pruebas de core,
26 omisiones opcionales, ningún fallo; 32/32 del perfil externo requerido;
sintaxis JavaScript y custodia de fuentes válidas. Los tres tests adicionales
frente a los 499 del laboratorio comprueban la adaptación de distribución.
Esta comprobación no ejecuta un nuevo vuelo ni reabre exámenes sellados.
