# echo-nexus

**A beta development terminal for ECHO · version 1.5.2.** Dark purple, black and white.
Developer: **rxlabs** · © 2026 RxLabs · Harness source: **MIT**.

[Website](https://www.rxlabs.org/echo-nexus) · [Guía en español](https://www.rxlabs.org/docs/echoai/echo-nexus)

We welcome volunteer developers interested in the harness, development backends
and reproducible ECHO training and evaluation. See [CONTRIBUTING](CONTRIBUTING.md).

```sh
curl -fsSL https://rxlabs.org/echo-nexus.sh | bash
echo-nexus
```

Linux and macOS, Python 3.10+, curl, and a UTF-8 terminal. Windows: use WSL.
No sudo. The installer creates a private virtual environment, checks the
published wheel's SHA-256, and keeps a timestamped installation log. Add
`~/.local/bin` to PATH if your shell does not already include it.
The exact installer is available at `scripts/install.sh`; inspect it before
running if preferred. Python dependencies are downloaded from PyPI.

## First session

```text
/help
/agents
/demo
/devtest list
/devtest
```

Tab completes commands and test IDs; inline help describes syntax. F2 expands
the telemetry/image panels on small terminals. `/stars off` disables motion.
`/stop` stops the development process owned by the harness; it does not stop
independent experiments. Remote API processing may finish after cancellation.

**The engine is a separate installation.** This repository contains the TUI,
connectors, image renderer, installer, protocol documentation and harness tests.
The harness component itself contains no ECHO policies or weights. This combined source distribution also includes the ECHO core and development modules, with sealed input data excluded.
If `echoai` is on PATH, the harness exposes its public `info`, `situate`, `life`
and `resume` commands. Research installations supply an operator-owned backend
manifest with their supported development tests.

```text
/backend /absolute/path/backend.json
/devtest list
/devtest all
/watch /absolute/path/thought.jsonl
/image /absolute/path/frame.png
```

`/devtest` runs the backend's default development set. `all` runs all declared
development tests sequentially, stopping on error. Evidence entries display
existing reports. Sealed entries cannot be executed by the runner. `/demo` is
a labeled synthetic viewer fixture; it is not ECHO and earns no ARC score.

## Optional neocortex

Export the provider's key in your shell, then launch echo-nexus. Supply the
**environment variable name**, never the secret itself, in the command:

```text
/connect api https://provider.example/v1 your-model PROVIDER_API_KEY
/connect anthropic https://api.anthropic.com/v1 your-model ANTHROPIC_API_KEY
/connect local /absolute/path/model.gguf
/disconnect
```

The API must implement Chat Completions or Anthropic Messages. Local GGUF
requires `llama-server` on PATH. It binds to loopback, uses four CPU threads, a 2048-token context and small batches,
and writes its own log. Models are never downloaded automatically.
Connection configuration is validated immediately; credentials and remote model
availability are checked on the first message. The harness keeps conversation
context in memory and writes redacted session logs with user-only permissions.
Chat sends only the text you enter and recent conversation, not your local
telemetry, files or images. Treat session logs as personal data.

`/ask QUESTION` explicitly adds a summary of the latest recorded ECHO decisions
to the adviser request. Viewer-only coordinates are excluded. `/echo` produces
a deterministic report from those records without calling a model. The adviser
response is not fed into the motor or its journal.

The neocortex is a language interface. Its text is labeled as a **proposal**;
it cannot operate motors, execute code, invoke tools or update ECHO facts.
This does not enable the NEXUS-0 core's optional cortex.

## HTTPS OpenRouter and saved connections

```text
/connect local /path/model.gguf
/connections save qwen-local
/connections default qwen-local
/connections
/connections use qwen-local
/connect api https://openrouter.ai/api/v1 openrouter/free @/path/.openrouterkey
/connections save openrouter
/connections use openrouter
/connections default off
/connections remove openrouter
```

Profiles survive restarts. They store model settings and the path to a credential
file or the name of an environment variable, never the credential itself. `@PATH`
links a single-line key file (a plain key or `export KEY="value"`); it is read only
when making an API request. It is never executed. File secrets are redacted from
session output. `/connections` lists profiles without opening their key files.
[OpenRouter's free router](https://openrouter.ai/openrouter/free) picks an available
free model; it does not promise a specific model or permanent availability.

```text
/models free
/connect openrouter free @/path/.openrouterkey
/connections save openrouter
/connect openrouter liquid/lfm-2.5-2.6b:free
```

The short command reuses the credential reference from a profile named
`openrouter`, if present. OpenRouter always uses HTTPS. Connecting checks the
public model catalog without opening a key file; a retired ID is rejected with
useful alternatives. HTTP errors retain the provider's redacted message.
No paid model is substituted automatically. Free availability changes; consult
`/models free` instead of relying on an old list.

## Editor, copy and development worlds · 1.5

```text
/paste
/copy last
/copy why
/copy session
/world list
/world start dev-world
/echo
/ask What observations support the next action?
/world stop
```

Ctrl+V opens a multiline editor; F3 copies the latest message. Use the editor's
Send button or Ctrl+Enter. Pasted text is a single chat message, never a sequence
of slash commands. Clipboard integration uses an available native utility;
copy falls back to the terminal's OSC52 support. `/paste` also allows manual
editing when no clipboard utility is installed.

An operator-owned backend can advertise `worlds`. A world runs alongside chat
until `/world stop` or application exit, independent of `/devtest` timeouts.
The backend decides whether to retain actor memory across episodes. The harness
does not invent a world or guarantee persistence between application restarts.
Changing the engine/backend or starting a separate test requires stopping the
world first. `/stop` cancels an active chat first; `/world stop` stops the world.

`/connections default NAME` reconnects that profile on launch. Use
`echo-nexus --no-connect` to skip this, or `echo-nexus --connect NAME` to choose
another saved profile for one launch. Capture mode never auto-connects.

GGUF startup now disables both GPU layers **and host-operation offload**. This
fixes an observed ROCm/HIP abort during warmup even with zero GPU layers.
The CPU profile uses context 2048, batches 256/64 and four threads. It retains
warmup, reports progress every ten seconds, and waits up to 300 seconds. `/logs`
shows a unique log for each attempt; failures report their exit code or signal.
Choose a binary with `/connect local PATH --server /path/llama-server` or
`ECHO_NEXUS_LLAMA_SERVER`. That binary must support `--device none` and
`--no-op-offload`. Updating the harness requires restarting its running session.

## Visible activity (0.1.2)

Type ordinary text and press Enter to chat with the connected model. For example:
"Help me break a problem into testable steps; summarize evidence and limitations."
The animated status shows observed request phases, elapsed time and the number
of public answer characters received. Text streams as the provider sends it.
`/stars off` stops animation while retaining status. `/stop` cancels the wait.

`/why` summarizes ECHO observations, recorded branch criteria, actions and results
from `/devtest` or `/watch`. Missing reasons remain explicitly unavailable. The
panel is the source's last received evidence, not the LLM's private reasoning or
new observations from a chat request. Chat never automatically receives journals;
paste specific observations to discuss them. Provider reasoning/tool-call fields
are not displayed, executed or retained in conversation history. An interrupted
stream is reported as incomplete and never saved as a complete answer.

## Agents, counters and the developer world

```text
/agent
/agent echo-4.0-cognitive-agentic
/agent echo-4.5-adaptative-agentic
/devtest dev-world
/devtest arc-gym
/devtest arc1-train
/devtest arc2-train
/devtest arc1-replay
/devtest arc2-replay
/devtest arc3-replay
/view coords on
/cell 3 2
/why
```

`/agent` selects a backend engine profile; `/connections` selects the language adviser. The private lab adapter maps 4.0 to ARC v2 and the initial grid library, and 4.5 to ARC v5.7 and current grid refinement. These are explicit component adapters, not an integration of every research module. Shared core tests are common to both profiles. Each new process reloads local code and records its hash; `/agent reload` refreshes the manifest. Unintegrated S6/EGO results are not activated automatically.

Counters distinguish completed processes from solved cases and show steps, limits, levels, resets, and deaths/generations where reported. ARC3-GYM now uses three development seeds and 600 steps each, with an explicit stop reason. The private editable world uses `lab/echo-nexus/dev-world.json`; runner settings are in `lab/echo-nexus/live-agent.json`. Edit and rerun `dev-world`. The checked 4.5 run reached the goal in 56 steps without resets; this is one synthetic puzzle.

Coordinates, compass and arrows are human-only overlays. `/cell X Y` inspects and centers a cell; F2 expands the panel, and `/view coords off` restores the whole image. Screen coordinates use +X east and +Y south. Body3D includes actual XYZ and facing; ARC3-GYM shows last observed movement, not an assumed facing direction. Recordings without pose data leave it unavailable. Overlays never enter agent observations.

`arc1-train`/`arc2-train` solve small public training samples. `*-replay` displays archived examinations: ARC-1/2 input, prediction and published answer, or ARC-3 actions with per-frame hash checks. These are visualizations, not new scores or reopened exams. The public harness ships neither ECHO code nor the private adapter.

## MCP and installed agents

`/agents` and installation detection only find executable paths. They never
start coding agents or alter their configuration. Connect a trusted MCP stdio
server explicitly, then inspect and call its tools:

```text
/mcp connect echo -- echoai mcp --root /absolute/project
/mcp connect claude -- claude mcp serve
/mcp tools echo
/mcp call echo echo_receipts {"limit":5}
/mcp close echo
```

MCP tools execute with the connected server's permissions; a tool can modify
files. Only explicit `/mcp call` commands invoke tools. The neocortex cannot
invoke them. Stdio protocol versions are negotiated. Streamable HTTP MCP is
not included in 1.5.1. Current Codex installations may expose app-server
instead of the retired MCP server: detection does not claim these protocols
are interchangeable. Supply a compatible MCP adapter if needed.

## What the visualization means

The tree shows fields received from ECHO: observations, CAM/Q/T, gate verdicts
and actions. LIF/Adaptive-LIF counts are shown only when a backend emits actual
monitor samples. This monitor is distinct from the policy controlling ECHO.
Missing measurements stay **sin muestra**; chat calls never fabricate neuron
activity. Stars are decoration. JSONL files are read-only inputs; the harness
log is an operator log, not a second thought bus.

Grids and PNG/JPEG images render as true-color half blocks, including in SSH.
Large images are downsampled to the panel. This is a terminal view, not a
pixel-perfect image editor. `--capture PATH.svg` captures the actual TUI widgets.
Backend development runs can stream frame events for live ARC and custom worlds.

## Develop and verify

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
echo-nexus --capture session.svg --command /demo
```

See [the backend contract](docs/backend.md). Custom manifests are executable
operator configuration: do not load one from an untrusted project. The harness
runs argv directly, never through a shell, and does not import ECHO source.
Process exit zero means the command finished successfully; it does not turn a
scientific milestone green. Research audits decide that independently.

## License and scope

MIT covers this harness. ECHO core and model licenses remain separate.
Brand names are reserved; see [NOTICE](NOTICE). The new echo-nexus name makes
no claim of registered trademark status.

## Protocol references

- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Textual testing and screenshots](https://textual.textualize.io/guide/testing/)
- [OpenAI's archived Codex MCP integration and migration note](https://developers.openai.com/cookbook/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk)

## OpenCode adviser · 1.5.2

`/connect opencode provider/model` uses a separately installed OpenCode CLI. It requests JSON text output, denies tools in an ephemeral adviser configuration, and ignores reasoning and tool events. Provider authentication remains managed by OpenCode. This is a language adviser; its text does not change verified ECHO state. The connector has timeout and cancellation limits.
