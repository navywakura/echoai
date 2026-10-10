# Instrucciones de desarrollo de ECHO-5

Leer primero `../CLAUDE.md`, `../docs/05-NEXUS-0-SPEC.md`, este archivo,
`README.md` y `docs/DEVELOPMENT.md`. Aplican los invariantes del proyecto padre;
sus tareas históricas de NEXUS-0 no son tareas nuevas de ECHO-5.
Antes de integrar, leer `docs/MODULE-INVENTORY.md` y sus dos revisiones de
familias. El catálogo JSON registra dependencias potenciales, no cobertura
de tests ni una certificación nueva de capacidades.

- Trabajar dentro de esta carpeta. La `.venv` pertenece sólo a ECHO-5.
- No editar, mover ni importar por efectos laterales fuentes o experimentos
  congelados de 4.5/B24. No usar `echo-discord` ni su entorno.
- Antes de integrar código previo, identificar dependencias y evidencia;
  reutilizarlo mediante una interfaz explícita, sin duplicar motores cognitivos.
- WSP sigue siendo el bus existente. No inventar un segundo thought-bus.
- El núcleo basal funciona sin LLM. El neocórtex propone hipótesis; el
  verificador conserva su autoridad. No hay AKD1000 en el laboratorio.
- Robótica parte de ECHO-3 Gazebo/PX4. HIL y jaula física siguen pendientes;
  PX4 conserva estabilización y failsafes.
- La futura GUI mostrará trazas reales y resúmenes atribuidos. No fabricar
  monólogos ni devolver la narración del visor a la política.
- S6 de 4.5 sigue sin pase. La nueva investigación se retomará después de 5.5.
- Ejecutar `make check` y las pruebas pertinentes al cambiar código. El setup
  inicial no contiene pruebas de capacidades ni un agente ECHO-5 funcional.
- No publicar ni instalar dependencias pesadas por defecto. Declarar cambios
  de dependencias y conservar versiones y presupuestos al iniciar ensayos.
