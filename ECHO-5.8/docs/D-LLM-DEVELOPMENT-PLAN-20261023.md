# D1 y D2 · plan ejecutable

Spec: `D-LLM-DEVELOPMENT-DESIGN-20261023.md`. Python stdlib, cliente seguro
`echo58.crece.api`, MEMORIA-X original. Autorización autónoma de Nav, 23/10.

- [ ] Escribir pruebas de firmas, autorización, observación/recuerdo de roles,
  permutación de controles y no filtración de respuestas; observar rojo.
- [ ] Implementar `echo58/llmstudy/core.py`: generadores deterministas,
  entrenamiento, propuestas válidas y ejecución de herramientas en memoria.
- [ ] Implementar `bench.py`: freeze de agenda/fuentes, llamadas Groq con
  caché y cuota, límites, reanudación, trazas reales y agregados.
- [ ] Implementar `audit.py`: reproducción sin red de prompts, decisiones y
  métricas, integridad y controles de manipulación. Correr suites dirigidas.
- [ ] Revisión estática cruzada del contrato; corregir antes del freeze.
- [ ] Ejecutar las208 llamadas previstas, respetar cuota y registrar fallos.
- [ ] Auditoría en proceso nuevo, informe de costes/puertas/resultados reales;
  actualización de roadmap y handoff sin publicación.

Las herramientas tienen efectos solo en el banco, nunca shell o servicios
externos. Firma/acción/destino son las únicas señales del guardián. El ensayo
no se ajusta tras consultar validación; error API bloquea verde, no se cuenta
como abstención voluntaria. No modificar módulos históricos o certificados.
