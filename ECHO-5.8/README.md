# WSP memory

ECHO stores observations and their consequences in memory. A `.wsp` archive
keeps that memory with its packets and metadata so it can be loaded again.

Run these commands from the repository root, in a checkout named `echoai`:

```bash
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles verify examples/memory.wsp
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles inspect examples/memory.wsp
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles export-json examples/memory.wsp /tmp/echo-memory.json
PYTHONPATH=..:. python3 -m echoai.echo58.wspfiles import-json /tmp/echo-memory.json /tmp/echo-memory.wsp
```

`verify` confirms the archive structure and checksum. `inspect` shows the records.
The conversion commands create new files; choose unused destination paths.
The included example contains synthetic observations for learning the format.

To load the memory in Python, from the same checkout:

```bash
PYTHONPATH=..:. python3 - <<'PYTHON'
from echoai.echo58.wspfiles.memory import load_memory
memory = load_memory('examples/memory.wsp')
print(memory.recall(7, 0, 'ENTER', 0))  # HURT
PYTHON
```

To export your own `Memory` object, call `export_memory(memory, path)` from
`echoai.echo58.wspfiles.memory`. [General usage](../docs/USAGE.md).
