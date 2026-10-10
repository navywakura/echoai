# ECHO-5

Preparación creada el 10 de octubre de 2026. Estado: **setup e inventario**.
La implementación funcional de ECHO-5 **no ha comenzado**.

```sh
cd ECHO-5
make setup
make check
```

Python 3.12.13, entorno propio `.venv`, biblioteca estándar. No necesita GPU,
LLM, credenciales ni descarga de paquetes. `make test` ejecutará las pruebas
cuando existan; por ahora informa de su ausencia y devuelve código 2.

```text
ECHO-5/
├── AGENTS.md          instrucciones para agentes de desarrollo
├── docs/              decisiones e integración futura
├── src/echo5/         namespace del nuevo código
├── tests/             futuras pruebas unittest
├── scripts/dev.py     setup y comprobaciones
├── artifacts/         salidas locales, excluidas de Git
├── pyproject.toml     metadatos y versión de Python
└── Makefile           comandos de desarrollo
```

El objetivo es consolidar el núcleo compartido para robótica y trabajo con
neocórtex, recuperando las capacidades verificadas de versiones anteriores.
ECHO-5 aún no contiene un agente integrado ni una GUI. El setup no acredita
capacidades científicas. ECHO-4.5 y B24 conservan sus archivos y estados.

[Guía de desarrollo](docs/DEVELOPMENT.md).

Inventario previo completado: [módulos y dependencias](docs/MODULE-INVENTORY.md),
[catálogo por archivo](docs/inventory/CATALOG.md) y
[datos estructurados](docs/inventory/modules.json). `make inventory` lo
regenera leyendo fuentes; no importa ni ejecuta el agente. La integración
continúa pendiente.

Idea conservada para investigación futura:
[aprendizaje adversarial inspirado en GAN](docs/ADVERSARIAL-LEARNING-PROPOSAL.md).
Describe propuestas, contraejemplos, verificación y un posible microensayo;
no implementa el ciclo ni registra nuevos resultados científicos.
