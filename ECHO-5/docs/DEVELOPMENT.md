# Desarrollo

Integración experimental iniciada el 10 de octubre de 2026. El diseño actual
está en [IMPLEMENTATION-DESIGN.md](IMPLEMENTATION-DESIGN.md). `make check`
comprueba entorno y sintaxis; `make test` ejecuta pruebas funcionales.
`make bench` mide el contrato sintético y `make audit` recalcula y reproduce
resultados en otro proceso. Cada comando conserva su alcance.

Se usa CPython 3.12.13 instalado en el host, con biblioteca estándar y una
`.venv` propia sin paquetes globales ni pip. No se requiere acceso de red para
el setup. No se reutilizan entornos antiguos. Si el intérprete no está
disponible en otra máquina, instalar esa versión antes de `make setup`.
El setup puede ejecutarse de nuevo: valida el entorno existente sin borrarlo.

`pyproject.toml` registra la versión experimental 5.0.0a1; aún no se ha definido
un backend de empaquetado ni una distribución instalable. `src/echo5` contiene
la implementación y el ejecutor añade expresamente esa ruta bajo `-I`.
La carpeta pertenece al repositorio Git padre; no tiene un repositorio anidado.

El [inventario estático](MODULE-INVENTORY.md) está completado, con catálogo
de archivos, dependencias y revisión documental. Se reproduce con
`make inventory`; no ejecuta código del agente. El contrato numérico vigente
es [BENCHMARK-CONTRACT.json](BENCHMARK-CONTRACT.json). Antecedentes:

- [Dirección acordada](../../docs/ECHO45-TO-ECHO5-DECISION-20261009.md).
- [Robótica previa](../../docs/DRONE3-RESULTS.md): SITL validado;
  hardware pendiente.
- [Módulos V3](../../docs/ECHO45-RELATIONAL-V3-RESULTS.md): resultados
  sintéticos y límites de transferencia.
- [Observabilidad](../../docs/ECHO45-OBSERVABILITY.md): diarios existentes
  para la futura GUI local.
- [Visión 5/5.1/5.5](../../docs/ECHO5-51-55-RESEARCH-VISION.md): propuestas
  de investigación, sujetas a la decisión posterior de octubre.

La limpieza futura requiere comprobar imports y referencias antes de mover
archivos. Este setup conserva intactas las rutas existentes. B24 sigue bajo
su gestor propio; el desarrollo de ECHO-5 no lo relanza ni lo cancela.

Los resultados se guardan en `artifacts/`, excluido de Git. Cada banco conserva
contrato, fuentes por hash, biblioteca adquirida, resultados por caso, costes,
trazas y manifiesto. Un error del instrumento deja `instrument-error.json` y
detiene la ejecución; no se convierte en un resultado negativo del agente.
Una vez iniciada una ejecución no se editan sus fuentes. La auditoría con
`--replay` se lanza desde un proceso nuevo y usa el mismo código congelado.

Los presupuestos son unidades lógicas explícitas, no FLOPs, milisegundos ni
julios. Su comparación requiere el mismo contrato. El banco de interacción
permite nuevas observaciones durante la prueba, como define ADAPT; el banco
de rejillas congela la biblioteca y no aprende de las consultas.

La primera evaluación completa tiene [informe y recibos](RESULTS-20261010.md).
El auditor sin `--replay` informa `arithmetic_only_pending_replay` y no emite
`valid: true`; `make audit` incluye el replay. El ejemplo de memoria puede
guardarse, cargarse en otro proceso y volver a verificarse sin llamadas al LLM.
