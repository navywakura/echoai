# ECHO simulation

ECHO's browser panel lets you create a grid-world mission and follow the agent's
observations, remembered map and actions. You can step, run and pause a session.

Requires CPython **3.12.13** and `make`. From the repository root:

```bash
cd ECHO-5
make setup
make setup-sandbox
make panel
```

Open **http://127.0.0.1:8765**. The setup commands create dedicated Python
environments; the sandbox setup installs the packages in `requirements-sandbox.lock`.
The panel runs as a local background process. Session data is saved under
`ECHO-5/artifacts/`. Use a fresh output directory for each new session.

Runtime settings live in `config/`. The panel displays records produced by the
running session. Its controls and observations describe the configured simulated world.

[General usage](../docs/USAGE.md) · [Terminal](../harness/echo-nexus/README.md).
