# S6-B20 — ejecución y resultados

Actualización: 06-10-2026 15:55 Madrid. Estado del supervisor: **MICRO_CLOSED_NO_PROMOTION**.

B20 implementa una búsqueda por varias familias de ganancias, límites de refinamiento,
contrastes de guarda/duración y una biblioteca de conjunciones sin anclajes obligatorios.
Se conservan las fuentes B18/B19. Las 72 fuentes B20 de capacidad están congeladas.
Pasan 22 pruebas B20 y 52 pruebas anteriores (74 comprobaciones distintas).

Capacidad local: 2448 partidas reservadas de un máximo de 2.928. Última fase: CAPACITY_PASSED.
Doce candidatos de la biblioteca antigua, doce de la ampliada y tres controles humanos
separados. Cada candidato se ejecuta con replay; el primero que pase por categoría
debe conservar la mejora en 160 casos de desarrollo y en una auditoría independiente.

| Control | Propuestas | Pasan cribado | Pasa desarrollo amplio |
|---|---:|---:|---|
| old | 12 | 0 | False |
| expanded | 12 | 3 | False |
| human-control | 3 | 1 | True |

Son controles dirigidos de capacidad. No acreditan descubrimiento autónomo.

El micro privado en Kaggle está condicionado al control anterior. Comparará
C0/C1 (sin LLM, una vez) y H0/H1 (tres semillas LLM emparejadas), con
18 propuestas por recorrido y tres generaciones iniciales físicas. Después
solo avanzarán los candidatos elegibles a desarrollo amplio y conservación nueva.

| Recorrido del micro | Propuestas | Últimos niveles | Pasa cribado |
|---|---:|---:|---|
| C0 | 18 | 53 | False |
| C1 | 18 | 50 | False |
| H0-820101 | 18 | 57 | False |
| H1-820101 | 18 | 51 | False |
| H0-820117 | 18 | 57 | False |
| H1-820117 | 18 | 51 | False |
| H0-820129 | 18 | 57 | False |
| H1-820129 | 18 | 51 | False |

Revisión aritmética local: válida.

**S6 sigue abierto.** La cualificación no sustituye piloto, campaña ni examen B1–B5.
El siguiente contrato debe incluir los cuatro brazos y descubrimiento desde SEMILLA.
El cierre final de ECHO-4.5 también sigue pendiente. No se publicaron fuentes ni datos.

[Contrato](ECHO45-S6-B20-DESIGN.md) · [Estado del supervisor](../lab/seed/s6b20-20261006/pipeline-status.json) ·
[Estado de capacidad](../lab/seed/s6b20-capacity-20261006/status.json) ·
[Pruebas B20](../lab/kaggle/s6b20-20261006/tests-b20-final.log).
