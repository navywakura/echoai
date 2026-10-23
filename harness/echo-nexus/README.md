# echo-nexus

The terminal interface for ECHO: commands, observation panels, images and optional
language-adviser connections. It is included by the [repository installer](../../README.md#start).

```bash
echoai tui
```

In the terminal:

```text
/help
/demo
/agents
/watch /absolute/path/thought.jsonl
/stop
```

`/demo` displays sample data. `/watch` follows a local session journal. Tab completes
commands; F2 expands panels on smaller terminals. `/stop` cancels a task started here.

## Optional adviser

```text
/connect api https://provider.example/v1 your-model PROVIDER_API_KEY
/connect local /absolute/path/model.gguf
/connections save my-adviser
/connections default my-adviser
/disconnect
```

Use the name of an environment variable for the API key. Local GGUF requires
`llama-server`. Saved connections retain credential references. Provider calls
use your selected account and its pricing.

A custom installed engine can be attached through a [backend manifest](docs/backend.md).
The terminal component uses the [MIT license](LICENSE).
