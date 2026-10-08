# Backend contract v1

The harness is a separate process. No Python import of the engine is required.
A local backend manifest declares supported commands; it is executable operator
configuration, never inferred from model text or discovered repository files.

```json
{
  "schema": "echo-nexus-backend-v1",
  "name": "My installed ECHO",
  "tests": [
    {
      "id": "identity",
      "title": "ECHO identity",
      "kind": "development",
      "default": true,
      "argv": ["echoai", "info"],
      "cwd": "/absolute/project",
      "timeout": 120
    },
    {
      "id": "audit",
      "title": "Published audit",
      "kind": "evidence",
      "report": "/absolute/reports/audit.json"
    },
    {
      "id": "reserved",
      "title": "Reserved exam",
      "kind": "sealed",
      "note": "Owned by the experiment coordinator; never run here."
    }
  ]
}
```

`development` may execute. `evidence`/`sealed` only display a local report or
explanation, even if the entry also contains argv. Timeouts are 1–3600 seconds.
The harness stops its own process group on cancel/timeout on POSIX. On Windows
native Python only direct children are terminated; the supported installer
targets Linux/macOS/WSL. Nonzero exit halts `/devtest all`.

stdout may contain plain text and/or one JSON object per line, up to 2 MB each.
The UI consumes frames and telemetry without feeding them back into the agent:

```json
{"kind":"frame","origin":"LIVE / development","grid":[[0,1],[2,3]],"turn":1}
{"kind":"telemetry","origin":"LIVE / ECHO","turn":1,"wsp":"observed-value","action":0,"reward":1,"gate":0,"q":[1,0,0],"cam_used":3}
{"kind":"result","text":"Actual measurement, with denominator and limitations"}
```

Optional neuronal arrays: `lif_a`, `lif_b`, `alif_spikes`. They must contain
measured counts, never inferred activation from prose. The monitor is explicitly
labeled as distinct from the control policy. Existing `thought.jsonl` and
ARC decision journals can be viewed directly with `/watch`; fields absent from
those formats remain unavailable. Grids must be rectangular, at most 1024×1024.

LIVE means data received during the requested development command; it does not
authenticate the backend. A local manifest can lie. Scientific evidence must
be traced to the engine's own journals, hashes and independent audits. A hash
chain is not verified by this UI. Full journal verification stays in ECHO.

To keep screenshots public, emit only data you intend to disclose: adapter
paths, environment variables, program candidates and private test IDs need not
be visible. Never include credentials. The renderer strips terminal control
sequences and logs redact common credential patterns and key environment values.

## Uninstall

Delete the `echo-nexus` launcher in your chosen bin directory and the matching
`echo-nexus` directory under `~/.local/share`. Configuration lives under
`~/.config/echo-nexus`; logs under `~/.local/state/echo-nexus`. Retain logs if
needed. These locations honor XDG overrides and installer environment options.


## Optional agent profiles and viewer progress (0.1.2)

The manifest may declare `agents: [{id, description, tests: [...]}]` and
`default_agent`. Agent tests override root tests by ID; common root tests remain.
All argv lists undergo the same validation. `/agent ID` persists selection, and
each `/devtest` reloads the manifest. The harness does not bundle any engine.

Emit `kind: progress` with `cases_done`, `cases_total`, `solved`, `step`, `budget`,
`levels`, `levels_total`, `resets`, and `stop_reason` as applicable. A zero process
exit is not counted as a solved case. Counters describe the current run.

A frame may include `observer` with `position: [x,y]`, `direction: [dx,dy]`,
`direction_kind`, `label`, optional `world_position`, `world_direction`, and
`cell_world: {"x,y": [world_x,world_y,world_z]}`. These are output-only viewer
fields and must never be sent back to the agent. Direction should be measured
facing or explicitly labeled movement; missing pose must remain unavailable.
`/cell X Y` only changes the viewport. Coordinates are zero based.

## Continuous session worlds · 1.5

Root manifests and agent profiles may declare `worlds` alongside `tests`.
Each entry uses the same development argv, cwd and validation rules as a test.
Only `kind: development` can run. `/world start ID` starts one world process;
`/world stop` and application exit terminate its process group. Chat remains
available. Changing engine/backend or running a separate test requires stopping
the world first. A running world owns the displayed decision source.

World sessions have no harness wall timeout. The operator must define episode,
memory and resource limits in their backend. Its canonical journal remains the
decision source. Emit `progress` for steps and completed/solved episodes; the
UI must not infer solved cases from process exits. Actor memory retention and
persistence between restarts are backend responsibilities.

`/ask QUESTION` sends the latest decision summary to the optional LLM adviser.
It excludes the frame's viewer-only `observer` metadata. The adviser response
is never sent back to the world process. `/echo` displays the same recorded
summary deterministically without an API request.
