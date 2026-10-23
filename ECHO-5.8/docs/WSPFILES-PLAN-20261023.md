# W+ · plan 23/10/2026

1. Contrato previo: formato, fuentes desarrollo fijas, cuatro controles,
   límites, rechazo adversarial e integración Memory/Agent.
2. Tests RED: roundtrip bytes/metadatos, perfiles, límites, truncamientos,
   versión/hash/sobrantes, JSON ambiguo, expansión y memoria alterada.
3. Implementar codec stdlib, CLI JSON de inspección y wrapper Memory sin
   editar sus módulos. Tests GREEN y suite WSP histórica sin modificar.
4. Archivar fuentes/contrato y fuentes de datos con hashes antes de medir.
   Generar `.wsp` reales, import/export e integración Agent; diario factual.
5. Nueve réplicas balanceadas para cada brazo/operación; resultados íntegros,
   auditor offline y reporte honesto de ventajas/pérdidas.

Comandos desde RXos con Python del sistema y `PYTHONPATH=.`:
`python3 -m unittest echoai.tests.test_echo58_wspfiles`;
`python3 -m echoai.echo58.wspfiles.bench`;
`python3 -m echoai.echo58.wspfiles.audit RUTA`.

Aplicadas instrucciones de pruebas primero y verificación antes de cierre.
La ejecución ya autorizada no requiere otra aprobación de diseño.
