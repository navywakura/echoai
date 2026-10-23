# Connect a local backend

A backend manifest maps terminal commands to your installed engine.
Save this example as `backend.json`, replacing the working directory:

```json
{
  "schema": "echo-nexus-backend-v1",
  "name": "My ECHO",
  "tests": [{
    "id": "identity",
    "title": "Engine information",
    "kind": "development",
    "default": true,
    "argv": ["echoai", "info"],
    "cwd": "/absolute/project",
    "timeout": 120
  }]
}
```

Load it with `/backend /absolute/path/backend.json`, then use `/devtest list`
and `/devtest identity`. The terminal shows stdout and stops the owned process
on cancellation or timeout. Use manifests from a source you trust: `argv`
contains executable commands.

Backends can emit one JSON object per line for the panels:

```json
{"kind":"frame","origin":"local session","grid":[[0,1],[2,3]],"turn":1}
{"kind":"telemetry","origin":"local session","turn":1,"action":0,"reward":1}
{"kind":"result","text":"Session finished"}
```

Frames use rectangular integer grids. Existing journals can also be followed
with `/watch /absolute/path/thought.jsonl`. [Terminal guide](../README.md).
