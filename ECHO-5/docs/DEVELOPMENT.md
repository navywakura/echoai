# Desarrollo

Setup creado el 10 de octubre de 2026. Alcance: carpeta, entorno Python
aislado, comandos de comprobación e instrucciones. No integra todavía el
agente, la GUI, robótica o neocórtex. No inicia pruebas científicas.

Se usa CPython 3.12.13 instalado en el host, con biblioteca estándar y una
`.venv` propia sin paquetes globales ni pip. No se requiere acceso de red para
el setup. No se reutilizan entornos antiguos. Si el intérprete no está
disponible en otra máquina, instalar esa versión antes de `make setup`.
El setup puede ejecutarse de nuevo: valida el entorno existente sin borrarlo.

`pyproject.toml` registra el espacio de desarrollo; aún no se ha definido
un backend de empaquetado ni una distribución instalable. `src/echo5` reserva
el namespace y el ejecutor de pruebas lo añade expresamente a su ruta.
La carpeta pertenece al repositorio Git padre; no tiene un repositorio anidado.

El [inventario estático](MODULE-INVENTORY.md) está completado, con catálogo
de archivos, dependencias y revisión documental. Se reproduce con
`make inventory`; no ejecuta código del agente. El siguiente trabajo será
definir el primer contrato de integración. Antecedentes a revisar:

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
