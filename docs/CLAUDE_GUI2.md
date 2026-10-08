# CLAUDE — GUI-2 (pegar tal cual)

WORLD-3 está **verde**. No lo reabras. No descargues un LLM. No toques
kernel, ISO, `parse_reply`, `plan.py`, `thought.KEYS`, `graph.py` (salvo
un import de board si el log ya trae `cell` — no debería hacer falta),
`sign.py`, `qtable.py`, `world.py`, `encoder.py`, `loop.py`, ni
`lab/nexus0_report.json`.

Lees **antes**: `echoai/CLAUDE.md`, `echoai/WATCH.md`,
`echoai/nexus0/board.py`, `echoai/nexus0/view.py` (`follow()` ya existe),
`echoai/docs/NOW.md`, `echoai/docs/NEXT_APPROACH.md` § GUI.

Eres implementador. Un slice. Un KPI.

---

## Qué construyes

La placa de GUI-1 **en vivo**: mientras el loop escribe `thought.jsonl`,
el tablero enseña el turno que acaba de ocurrir. No un cerebro 3D. No
un WebSocket. No un segundo bus.

Hoy:

```
python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
# escribe board.html, file://, replay embebido, sin tail
python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --follow
# ANSI, ya hace tail. Se queda.
```

GUI-2:

```
PYTHONPATH=. python3 -m echoai.nexus0.bench --thought --short   # o demo
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought.jsonl --follow
# 127.0.0.1, stdlib http.server, JS hace poll del jsonl
# sin --follow el comportamiento de GUI-1 no cambia (HTML estático)
```

El demo ANSI **se queda**. CI no necesita un navegador: los tests de
`--follow` pueden ser un cliente `urllib` contra el server en un hilo,
o un helper que lea líneas nuevas. Cero imports nuevos en `loop.py`.
`board.py` sigue **sin** importar `loop`, `qtable`, `world`, `attend`.

---

## Contrato

1. Sin `--follow`: idéntico a GUI-1 (un HTML autónomo, CSS/JS inline,
   turns embebidos, `file://`, cero red). Tests viejos de board no se
   rompen.
2. Con `--follow`: stdlib only (`http.server` / `socketserver`). Bind
   **127.0.0.1**. Puerto por flag (`--port`, default p.ej. 8765).
3. El browser **poll** (GET cada ~200 ms). **Prohibido** WebSocket,
   SSE si implica otro protocolo, npm, CDN, Qt.
4. El JSON que pinta es el del log, `thought.KEYS` **no se amplía**.
5. Mundo de N celdas: ya lo saca `cell_count(records)`. Un log de
   graph.py (si algún día se escribe thought) no asume 32.
6. Si el fichero aún no existe, espera o error claro, no crash opaco.
7. Ctrl+C apaga el server. `--follow` no reescribe `board.html` como
   único mecanismo (el vivo es el server).

---

## KPI

```
board --follow sirve una placa que, al añadir líneas al jsonl,
pinta el turno nuevo sin recargar a mano el HTML embebido de GUI-1
sin --follow, board.html sigue siendo el replay autónomo
0 imports de loop/Q/T/ATTEND en board.py
0 WebSocket
anillo default intacto
tests GUI-1 siguen verdes
```

Un test que **falle** si el poll no ve la línea nueva: escribir un
jsonl de 2 turnos, arrancar follow en un hilo, GET, append 3ª línea,
GET de nuevo, la 3ª está. Eso es el KPI, no una captura de pantalla.

---

## Qué no se toca

`loop.py`, `thought.KEYS`, `graph.py`, `sign.py`, `parse_reply`,
encoder, kernel, ISO, Qwen, ANTI-ALIAS, CUERPO-1, `BENCH_TURNS`.
No “mejora” WORLD-3 desde la GUI.

---

## Tests

Añade en `TestGui1` o una clase `TestGui2`. Reutiliza el jsonl de
GUI-1. Sin red externa, sin GGUF.

Al final:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
```

Candados del anillo iguales. Tests ≥ 208.

---

## Informe que me pegas a Grok

- cómo hace el poll (ruta HTTP, intervalo)
- tests OK / N, y el test que añade una línea y la ve
- GUI-1 file:// sigue igual (nombra el test)
- archivos tocados
- si `--follow` en `file://` era imposible y por eso hay server:
  dímelo claro (es el diseño correcto, no un fallo)
