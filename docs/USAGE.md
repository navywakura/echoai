# Using ECHO

## Install and open

Follow the [installation commands](../README.md#getting-started), then run `echoai tui`.
The terminal opens a command prompt with panels for observations and actions.
Use `/help` for the command list, `/demo` for a sample session and `/stop` to
stop a task started by the terminal.

Useful shell commands:

```bash
echoai --version
echoai info
echoai demo --memory echo-memory.wsp
echoai memory verify echo-memory.wsp
echoai verify
echoai doctor
echoai setup list
```

`verify` checks the installed files against their manifest. `doctor` lists
available tools and paths. `setup list` shows the commands available locally.

## Save and load memory

From the source checkout named `echoai`:

```bash
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles verify examples/memory.wsp
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles inspect examples/memory.wsp
```

The example is a small synthetic memory. `verify` prints JSON with `valid: true`;
`inspect` also displays the stored packets and metadata. See [WSP usage](memory.md)
for export, reload and JSON conversion.

## Open a simulation

The [simulation guide](../simulation/README.md) explains how to prepare its Python
environment and open the browser panel. Create a mission, advance one step,
or use the run and pause controls. The panel displays the observed grid,
remembered map and selected actions. Session files are written locally.

## Connect a language adviser

Set your provider key in an environment variable, then enter this in the terminal:

```text
/connect api https://provider.example/v1 your-model PROVIDER_API_KEY
```

Use the environment variable's name in the command. For a local GGUF model,
install `llama-server` and use `/connect local /absolute/path/model.gguf`.
Provider credentials, model availability and pricing belong to your selected service.
The [terminal guide](../harness/echo-nexus/README.md) includes saved connections.

## Troubleshooting

- **Command unavailable:** add `~/.local/bin` to PATH and open a new shell.
- **Missing terminal dependency:** rerun `bash install.sh` from the checkout.
- **Source verification fails after editing:** use a fresh checkout to compare
  with the distributed files. For your own edits, `devrun` accepts `--allow-modified`.
- **WSP output already exists:** choose a new destination filename.
- **Simulation Python version differs:** install the version in `simulation/.python-version`.
