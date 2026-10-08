"""
GUI-1 — the board. A replay of `thought.jsonl`, as one HTML file.

    PYTHONPATH=. python3 -m echoai.nexus0.bench --thought
    PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
    # writes echoai/lab/board.html — open it with file://, no server

A circuit board, not a 3D brain: eight blocks that light up with the
turn — CAM, WSP, T, Q, GATE, ATTEND, CORTEX, ORACLE — and each one shows
what the log says about *this* turn, not a metaphor for it.

This module reads the jsonl and nothing else. It does not import `loop`,
`qtable`, `world` or `attend`; it never calls Q, T, ATTEND or CAM. If a
number is not in the log, the board cannot show it, which is the right
constraint for a viewer: the log is the contract (`thought.KEYS`).

Stdlib only, and the page is self-contained — CSS and JS inline, the
turns embedded as a JSON array. Zero CDN, zero network, no WebSocket, no
tail. The ANSI demo (`view.py`, `demo.py`) stays: CI does not need a
browser, and this does not replace it.

An older log written before GUI-1 has only twelve keys. Missing keys are
read as 0 / null rather than crashing — a replay of yesterday's run is
still a replay.

GUI-2 — the same board, live:

    PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought.jsonl --follow
    # serves http on 127.0.0.1:8765; the page polls /turns.json every 200 ms

A page opened with `file://` cannot watch a file grow: it has no timer's
worth of permission to re-read the disk, and the turns of GUI-1 are baked
into the document. So `--follow` starts a stdlib server on the loopback
and the page asks it, once every POLL_MS, only for the turns it does not
have yet. That is a design consequence, not a workaround — and it is the
whole of the addition: no WebSocket, no second protocol, no npm, no CDN,
no Qt. Without `--follow` nothing changes: the same self-contained file,
byte for byte.

The loop is never told that anybody is watching. `loop.py` gained nothing,
this module still imports no part of the fast path, and the server reads
the same jsonl a human could `tail`.

GUI-3 — the aquarium, next to the electrocardiogram:

    PYTHONPATH=. python3 -m echoai.nexus0.body3d --thought
    PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl

The eight blocks read the same line they always read. What is new is on
the left: a cube, drawn from `x`, `y`, `z` and `heading` — five keys the
log gained in GUI-3, null in a world that has no pose. The side comes
from the log, the visited voxels come from the log, and the walls come
from nowhere: this module still knows nothing about PULPO's cube, and a
voxel nobody has ever stood in is drawn as a hole, which is exactly what
a wall looks like from inside a body. A ring log has no pose, so it gets
no cube — the aquarium is not invented, and the strip of 32 is untouched.
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Same legend as view.py's terminal ring. Duplicated on purpose: the
# board must not import the loop's modules to draw a picture of them.
SYMBOL = {"EMPTY": "·", "GOAL": "G", "THREAT": "T", "NOVEL": "N",
          "OBJECT": "O"}
UNKNOWN = "?"
ROW = 16  # cells per printed row, as in view.py

ACTION_NAME = ("approach", "avoid", "wait")
GATE_NAME = ("ok", "modify", "block")
# The six the log's `heading` indexes, in the order the turning ring
# walks them. Duplicated on purpose, like SYMBOL above: a legend for six
# integers is not a model of the world, and importing the cube to read
# it would make the board depend on the thing it is drawing.
HEADING_NAME = ("+X", "+Y", "+Z", "-X", "-Y", "-Z")
# Six faces per voxel, drawn by CSS transforms. A cube made of six divs
# is the whole of the 3D here: no library, no canvas context, no shader,
# and nothing to fetch — the browser's own compositor does the projection.
FACES = ("px", "nx", "py", "ny", "pz", "nz")

# GUI-2. Loopback only, and not a flag: a board that can be reached from
# another machine is a service, and this is a lab instrument.
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_POLL_MS = 200
POLL_PATH = "/turns.json"

DEFAULTS: Dict[str, object] = {
    "turn": 0, "cell": 0, "kind": "EMPTY", "action": 2, "reward": 0,
    "wsp": "", "attend_on": False, "reason_name": "off", "q_row": [0, 0, 0],
    "t_pred": None, "questions": 0, "cortex_calls": 0,
    # GUI-1 keys. A log written before them reads as "nothing happened",
    # which is the honest default: absence is not evidence of an event.
    "n": 0, "s": 0, "delta": 0, "cortex_action": None, "gate_decision": 0,
    # GUI-3. A world with a body says where it is; the ring writes null
    # and gets no cube, which is the difference between not knowing and
    # being at the origin.
    "x": None, "y": None, "z": None, "heading": None, "frame": None,
}


def has_cube(records: List[dict]) -> bool:
    """Does this log come from a world that has a where?"""
    return any(r.get("x") is not None for r in records)


def cube_side(records: List[dict]) -> int:
    """How big is the cube? Asked of the log, exactly as `cell_count` is.

    Nothing here knows that PULPO's cube is 3, and nothing here knows
    where its stone is: a viewer that carried a copy of the world's walls
    would be a second world, and the first one to go stale. What the
    board can say is what the log said — this voxel was stood in, that
    one never was — and a voxel nobody has ever stood in is drawn as a
    hole, which is what a wall looks like from the inside of a body.
    """
    best = -1
    for r in records:
        if r.get("x") is None:
            continue
        best = max(best, int(r["x"]), int(r["y"]), int(r["z"]))
    return best + 1


def read_records(path: Path) -> List[dict]:
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def normalise(records: List[dict]) -> List[dict]:
    """Fill in what an older log does not carry. No key is invented."""
    out = []
    for rec in records:
        row = dict(DEFAULTS)
        row.update({k: v for k, v in rec.items() if k in DEFAULTS})
        row["q_row"] = [int(v) for v in (row["q_row"] or [0, 0, 0])][:3]
        while len(row["q_row"]) < 3:
            row["q_row"].append(0)
        out.append(row)
    return out


def cell_count(records: List[dict]) -> int:
    """How big is this world? Asked of the log, never assumed to be 32.

    A `sign.py` run has two cells and a corridor has five; hard-coding
    N_CELLS would draw thirty empty boxes around them.
    """
    if not records:
        return 1
    return max(int(r["cell"]) for r in records) + 1


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _payload(records: List[dict]) -> str:
    """JSON for the page. `<` is escaped so no string can close the tag."""
    raw = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("<", "\\u003c").replace("\u2028", " ").replace("\u2029", " ")


CSS = """
:root {
  color-scheme: dark;
  --bg: #0d1013; --panel: #151a1f; --line: #263038; --ink: #d7e0e6;
  --dim: #6d7c86; --fact: #58c98a; --hyp: #9aa7b0; --hot: #e0574a;
  --warm: #d9a441; --cold: #4e9bd6;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
header { padding: 14px 18px 10px; border-bottom: 1px solid var(--line); }
h1 { font-size: 14px; margin: 0 0 2px; letter-spacing: .14em;
  text-transform: uppercase; font-weight: 600; }
.sub { color: var(--dim); font-size: 12px; }
main { padding: 16px 18px 40px; max-width: 1100px; }
.ring { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 12px 14px; overflow-x: auto; }
.ring pre { margin: 0; font: inherit; letter-spacing: 2px; white-space: pre; }
.ring .idx { color: var(--dim); }
.ring .agent { color: var(--warm); }
.grid { display: grid; gap: 10px; margin-top: 12px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
.block { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 10px 12px; min-height: 84px; }
.block h2 { font-size: 10px; letter-spacing: .18em; margin: 0 0 6px;
  color: var(--dim); text-transform: uppercase; font-weight: 600; }
.val { font-size: 15px; }
.note { color: var(--dim); font-size: 11px; margin-top: 3px; }
.on   { border-color: var(--fact); }
.on .val { color: var(--fact); }
.hyp  { border-style: dashed; border-color: var(--hyp); }
.hyp .val { color: var(--hyp); }
.hot  { border-color: var(--hot); }
.hot .val { color: var(--hot); }
.warm { border-color: var(--warm); }
.warm .val { color: var(--warm); }
.cold { border-color: var(--cold); }
.cold .val { color: var(--cold); }
.off .val { color: var(--dim); }
.bars { margin: 0; }
.bar { display: flex; gap: 8px; align-items: baseline; }
.bar b { font-weight: 400; color: var(--dim); width: 62px;
  display: inline-block; }
.bar i { font-style: normal; width: 46px; text-align: right; }
.bar u { text-decoration: none; color: var(--cold); }
.bar.pos u { color: var(--fact); }
.bar.neg u { color: var(--hot); }
.bar.took b { color: var(--ink); }
.controls { display: flex; gap: 8px; align-items: center; margin-top: 14px;
  flex-wrap: wrap; }
button { background: var(--panel); color: var(--ink);
  border: 1px solid var(--line); border-radius: 4px; padding: 5px 12px;
  font: inherit; cursor: pointer; }
button:hover { border-color: var(--dim); }
input[type=range] { flex: 1 1 260px; accent-color: var(--cold); }
.loopbox { color: var(--dim); font-size: 11px; display: flex;
  gap: 5px; align-items: center; }
.legend { color: var(--dim); font-size: 11px; margin-top: 16px;
  line-height: 1.7; }
"""

# GUI-3. Added to the page only when the log carries a pose, so a ring
# board is what it always was.
VOX = 44  # px per voxel in the 3D stage; the writer and the CSS share it

# `$S` is VOX and `$H` half of it: one constant, substituted rather than
# repeated, because the writer places the voxels and the stylesheet draws
# their faces and the two have to agree about how big one is.
CUBE_CSS = """
.stage { display: grid; gap: 12px; grid-template-columns: 1fr; }
@media (min-width: 960px) {
  .stage { grid-template-columns: 340px 1fr; align-items: start; }
}
.cube { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 10px 12px; }
.cube h2, .think h2 { font-size: 10px; letter-spacing: .18em;
  margin: 0 0 8px; color: var(--dim); text-transform: uppercase;
  font-weight: 600; }
#stage3d { height: 300px; perspective: 760px; overflow: hidden;
  cursor: grab; touch-action: none; user-select: none;
  border: 1px solid var(--line); border-radius: 4px; background: #070a0c;
  display: flex; align-items: center; justify-content: center; }
#stage3d.drag { cursor: grabbing; }
#world { position: relative; width: 0; height: 0;
  transform-style: preserve-3d; }
.cell3d { position: absolute; left: -$Hpx; top: -$Hpx;
  width: $Spx; height: $Spx; transform-style: preserve-3d;
  display: none; }
.cell3d.on { display: block; }
.f { position: absolute; width: $Spx; height: $Spx;
  border: 1px solid #35424c; background: rgba(78,155,214,.16); }
.cell3d.goal .f { border-color: var(--fact);
  background: rgba(88,201,138,.22); }
.cell3d.here .f { border-color: var(--warm);
  background: rgba(217,164,65,.30); }
.f.px { transform: rotateY(90deg)   translateZ($Hpx); }
.f.nx { transform: rotateY(-90deg)  translateZ($Hpx); }
.f.py { transform: rotateX(90deg)   translateZ($Hpx); }
.f.ny { transform: rotateX(-90deg)  translateZ($Hpx); }
.f.pz { transform: translateZ($Hpx); }
.f.nz { transform: rotateY(180deg)  translateZ($Hpx); }
.beak { display: none; position: absolute; left: 38%; top: 38%;
  width: 24%; height: 24%; background: var(--warm); border-radius: 2px; }
.cell3d.here .beak { display: block; }
.beak.h0 { transform: translate3d($Hpx, 0, 0); }
.beak.h1 { transform: translate3d(0, -$Hpx, 0); }
.beak.h2 { transform: translate3d(0, 0, $Hpx); }
.beak.h3 { transform: translate3d(-$Hpx, 0, 0); }
.beak.h4 { transform: translate3d(0, $Hpx, 0); }
.beak.h5 { transform: translate3d(0, 0, -$Hpx); }
.viewbar { display: flex; gap: 8px; align-items: center;
  margin-top: 8px; flex-wrap: wrap; }
.viewbar button { padding: 3px 9px; font-size: 11px; }
#pose { color: var(--dim); font-size: 11px; }
.mini { margin-top: 8px; }
.mini summary { color: var(--dim); font-size: 10px; cursor: pointer;
  letter-spacing: .14em; text-transform: uppercase; }
.slice { margin: 6px 0 0; }
.slice b { display: block; font-weight: 400; font-size: 10px;
  color: var(--dim); margin-bottom: 3px; letter-spacing: .1em; }
.voxrow { display: flex; gap: 2px; margin-bottom: 2px; }
.vox { width: 16px; height: 16px; border: 1px solid var(--line);
  border-radius: 2px; display: flex; align-items: center;
  justify-content: center; font-size: 8px; color: var(--dim);
  background: #090c0e; }
.vox.seen { background: #1b2228; color: var(--ink); }
.vox.goal { border-color: var(--fact); color: var(--fact); }
.vox.here { border-color: var(--warm); color: var(--warm);
  background: #2a2317; }
.think { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 10px 12px; margin-top: 12px; }
#thought { max-height: 280px; overflow: auto; font-size: 11px;
  line-height: 1.55; }
.tl { white-space: pre; color: var(--dim); }
.tl.now { color: var(--ink); background: #1b2228; }
.tl.miss em { font-style: normal; color: var(--hot); }
.tl.paid em { font-style: normal; color: var(--fact); }
""".replace("$H", str(VOX // 2)).replace("$S", str(VOX))

JS = """
const $ = (id) => document.getElementById(id);
let i = 0, timer = null;

function ring(rec) {
  // Rebuilt from turn 0 every frame, never carried over. Scrubbing back
  // must un-reveal: the board shows what the log had said *by then*, so
  // the phase F threat move (7 -> 8) appears when it happened and not
  // before. A cell nobody has stood on yet is '?', not a guess.
  const seen = {};
  for (let k = 0; k <= i; k++) seen[TURNS[k].cell] = TURNS[k].kind;
  const n = window.__CELLS__, out = [];
  for (let start = 0; start < n; start += 16) {
    const span = [];
    for (let c = start; c < Math.min(start + 16, n); c++) span.push(c);
    out.push('<span class="idx">' + span.map(c => c % 10).join('') + '</span>');
    out.push(span.map(c => SYMBOL[seen[c]] || '?').join(''));
    out.push('<span class="agent">' +
      span.map(c => (c === rec.cell ? '@' : ' ')).join('') + '</span>');
  }
  return out.join('\\n');
}

function bars(rec) {
  return rec.q_row.map((v, a) => {
    const w = Math.max(-12, Math.min(12, v));
    const cls = 'bar' + (v > 0 ? ' pos' : v < 0 ? ' neg' : '') +
      (a === rec.action ? ' took' : '');
    const pad = ' '.repeat(12 + Math.min(0, w));
    const glyph = '#'.repeat(Math.abs(w));
    const left = w < 0 ? pad + glyph : ' '.repeat(12);
    const right = w > 0 ? glyph : '';
    return '<div class="' + cls + '"><b>' + ACTIONS[a] + '</b>' +
      '<i>' + (v >= 0 ? '+' : '') + v + '</i>' +
      '<u>' + left + '|' + right + '</u></div>';
  }).join('');
}

function block(id, cls, value, note) {
  const el = $(id);
  el.className = 'block ' + cls;
  el.querySelector('.val').textContent = value;
  el.querySelector('.note').textContent = note || '';
}

function draw() {
  const rec = TURNS[i], prev = i > 0 ? TURNS[i - 1] : null;
  $('ring').innerHTML = ring(rec);
  $('where').textContent =
    'turn ' + rec.turn + '  ·  cell ' + rec.cell + ' ' + rec.kind +
    '  ·  r ' + (rec.reward >= 0 ? '+' : '') + rec.reward;
  $('slider').value = i;

  block('cam', rec.n ? 'warm' : 'on', rec.n ? 'MISS' : 'hit',
        rec.n ? 'first turn ever on this slot' : 'seen before');
  block('wsp', 'on', rec.wsp || '—', 'the packet the loop perceived');
  block('t', rec.s ? 'hot' : (rec.t_pred === null ? 'off' : 'on'),
        rec.t_pred === null ? '—' : 's\\u0302\\u2032 ' + rec.t_pred,
        rec.s ? 'predicted, and was wrong' :
        (rec.t_pred === null ? 'no map for this move' : 'held'));
  $('q').className = 'block' + (rec.delta ? ' cold' : ' off');
  $('qbars').innerHTML = bars(rec);
  $('qnote').textContent = rec.delta ? '\\u03b4 \\u2260 0 — Q moved'
                                     : '\\u03b4 = 0';
  block('gate', rec.gate_decision === 0 ? 'on' : 'hot',
        GATES[rec.gate_decision] || '?',
        'took ' + ACTIONS[rec.action]);
  block('attend', rec.attend_on ? 'warm' : 'off',
        rec.attend_on ? 'ON' : 'off',
        rec.attend_on ? rec.reason_name : 'the fast path was enough');
  const spoke = rec.cortex_action !== null && rec.cortex_action !== undefined;
  block('cortex', spoke ? 'hyp' : 'off',
        spoke ? ACTIONS[rec.cortex_action] : '—',
        spoke ? 'hypothesis, proposed to the gate'
              : (rec.attend_on ? 'woke and proposed nothing'
                               : 'calls ' + rec.cortex_calls));
  const asked = prev && rec.questions > prev.questions;
  block('oracle', asked ? 'on' : 'off', asked ? 'ASKED' : '—',
        'questions ' + rec.questions);
}

function go(d) { stop(); i = Math.max(0, Math.min(TURNS.length - 1, i + d)); draw(); }
function stop() { if (timer) { clearInterval(timer); timer = null;
  $('play').textContent = 'play'; } }
function play() {
  if (timer) return stop();
  $('play').textContent = 'pause';
  timer = setInterval(() => {
    if (i >= TURNS.length - 1) {
      // The end of the log is not the end of the run. Live: hold here,
      // the poll will push `i` on when a turn arrives. Replay: start
      // over, unless the reader asked it to stop.
      if (LIVE) return;
      const box = $('loop');
      if (!box || !box.checked) return stop();
      i = 0;
    } else {
      i++;
    }
    draw();
  }, 220);
}

window.addEventListener('DOMContentLoaded', () => {
  $('prev').onclick = () => go(-1);
  $('next').onclick = () => go(1);
  $('play').onclick = play;
  $('slider').max = TURNS.length - 1;
  $('slider').oninput = (e) => { stop(); i = +e.target.value; draw(); };
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') go(-1);
    if (e.key === 'ArrowRight') go(1);
    if (e.key === ' ') { e.preventDefault(); play(); }
  });
  draw();
});
"""

CUBE_JS = """
// GUI-3 / GUI-3.5 — the aquarium. The voxels were laid out by the writer
// from the coordinates the log actually carries; this only says which one
// the body is in and which ones it has been in by now. Rebuilt from turn
// 0 every frame like the ring strip, so scrubbing back un-reveals: the
// cube shows what the log had said by then. No wall table, because there
// is none to have -- a voxel nobody stood in is never drawn at all, which
// is what a wall looks like from inside a body.
let rx = -20, ry = -34, sc = 1;

function view() {
  const w = $('world');
  if (w) w.style.transform =
    'rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) scale(' + sc + ')';
}

function orbit() {
  const st = $('stage3d');
  if (!st) return;
  let drag = null;
  st.addEventListener('pointerdown', (e) => {
    drag = { x: e.clientX, y: e.clientY };
    st.classList.add('drag');
    st.setPointerCapture(e.pointerId);
  });
  st.addEventListener('pointermove', (e) => {
    if (!drag) return;
    ry += (e.clientX - drag.x) * 0.55;
    rx -= (e.clientY - drag.y) * 0.55;
    rx = Math.max(-89, Math.min(89, rx));
    drag = { x: e.clientX, y: e.clientY };
    view();
  });
  const up = () => { drag = null; st.classList.remove('drag'); };
  st.addEventListener('pointerup', up);
  st.addEventListener('pointercancel', up);
  st.addEventListener('wheel', (e) => {
    e.preventDefault();
    sc = Math.max(0.4, Math.min(2.6, sc * (e.deltaY < 0 ? 1.09 : 0.92)));
    view();
  }, { passive: false });
  $('reset3d').onclick = () => { rx = -20; ry = -34; sc = 1; view(); };
  view();
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function pose(rec) {
  return '(' + rec.x + ',' + rec.y + ',' + rec.z + ',' +
    (HEADINGS[rec.heading] || '?') + ')';
}

function __cube(rec) {
  const box = $('cube');
  if (!box) return;
  const on = rec.x !== null && rec.x !== undefined;
  box.hidden = !on;
  if (!on) return;
  const seen = {};
  for (let k = 0; k <= i; k++) {
    const r = TURNS[k];
    if (r.x === null || r.x === undefined) continue;
    seen[r.x + ',' + r.y + ',' + r.z] = r.kind;
  }
  const at = rec.x + ',' + rec.y + ',' + rec.z;
  for (const el of box.querySelectorAll('.cell3d')) {
    const key = el.dataset.v, kind = seen[key];
    let cls = 'cell3d';
    if (kind !== undefined) cls += kind === 'GOAL' ? ' on goal' : ' on';
    if (key === at) cls += ' on here';
    el.className = cls;
    const beak = el.querySelector('.beak');
    if (beak) beak.className = 'beak h' + rec.heading;
  }
  for (const el of box.querySelectorAll('.vox')) {
    const key = el.dataset.v, kind = seen[key];
    let cls = 'vox';
    if (kind !== undefined) cls += kind === 'GOAL' ? ' seen goal' : ' seen';
    if (key === at) cls += ' here';
    el.className = cls;
    el.textContent = key === at ? (HEADINGS[rec.heading] || '@')
                                : (kind === 'GOAL' ? 'G' : '');
  }
  $('pose').textContent = pose(rec) +
    (rec.frame === null || rec.frame === undefined
       ? '' : '  ·  frame ' + rec.frame);
}

// The diary, and nothing but the diary: every field on the line is a key
// of the record. No sentence is composed here -- the board does not know
// why the body turned, and inventing a reason would be the one thing a
// viewer must never do.
function tline(rec) {
  const where = (rec.x === null || rec.x === undefined)
    ? 'cell ' + rec.cell : pose(rec);
  const q = '[' + rec.q_row.join(',') + ']';
  const t = rec.t_pred === null || rec.t_pred === undefined
    ? '—' : rec.t_pred;
  const r = (rec.reward >= 0 ? '+' : '') + rec.reward;
  return esc(String(rec.turn).padStart(6) + '  ' + where.padEnd(12) + '  ' +
    ACTIONS[rec.action].padEnd(8) + '  ' + rec.wsp + '  T=' + t +
    '  Q' + q + '  r=' + r + '  \u03b4=' + rec.delta + '  s=' + rec.s);
}

const THOUGHT_TAIL = 200;

function thought() {
  const box = $('thought');
  if (!box) return;
  const stick = box.scrollTop + box.clientHeight >= box.scrollHeight - 6;
  const from = Math.max(0, i - THOUGHT_TAIL + 1);
  const out = [];
  for (let k = from; k <= i; k++) {
    const rec = TURNS[k];
    let cls = 'tl';
    if (k === i) cls += ' now';
    if (rec.s) cls += ' miss';
    if (rec.reward > 0) cls += ' paid';
    out.push('<div class="' + cls + '"><em>' + tline(rec) + '</em></div>');
  }
  box.innerHTML = out.join('');
  // Follow the tail only if the reader was already at the tail. Scroll
  // up to read what happened and the panel leaves you there, exactly as
  // the slider does with the turn.
  if (stick) box.scrollTop = box.scrollHeight;
}

const __draw_ring = draw;
draw = function () { __draw_ring(); __cube(TURNS[i]); thought(); };
window.addEventListener('DOMContentLoaded', orbit);
"""

BLOCKS = (
    ("cam", "CAM", "does this slot have a past?"),
    ("wsp", "WSP", "the 16 bytes, as atoms"),
    ("t", "T", "the map's guess at s'"),
    ("gate", "GATE", "ok / modify / block"),
    ("attend", "ATTEND", "spend the slow clock?"),
    ("cortex", "CORTEX", "a hypothesis, never a fact"),
    ("oracle", "ORACLE", "testimony from outside"),
)


# Appended to the page only when it is served live, so the file:// board
# stays byte for byte what GUI-1 wrote.
LIVE_CSS = """
.dot { display: inline-block; margin-top: 6px; font-size: 11px;
  letter-spacing: .12em; text-transform: uppercase; color: var(--dim);
  border: 1px solid var(--line); border-radius: 10px; padding: 1px 9px; }
.dot.on { color: var(--fact); border-color: var(--fact); }
"""

LIVE_JS = """
// GUI-2 — the same board, fed by one GET on a timer. The page asks the
// loopback server only for the turns it does not already hold, appends
// them, and draws. No WebSocket, no second protocol, no second bus: the
// fast loop writes its jsonl exactly as before and is never told that
// anybody is reading it.
const __draw0 = draw;
draw = function () {
  if (!TURNS.length) {
    $('where').textContent = 'waiting for ' + LOG_NAME + ' — no turns yet';
    return;
  }
  __draw0();
};

function __live(on, total) {
  const el = $('live');
  if (!el) return;
  el.className = on ? 'dot on' : 'dot';
  el.textContent = on ? 'live · ' + total + ' turns' : 'waiting';
}

function __sync() {
  fetch(POLL_PATH + '?from=' + TURNS.length, { cache: 'no-store' })
    .then((r) => r.json())
    .then((d) => {
      const fresh = d.turns || [];
      if (fresh.length) {
        // Only jump to the newest turn if the viewer was already at the
        // end. Scrub back to turn 3 and the board leaves you there.
        const wasEnd = i >= TURNS.length - 1;
        for (const rec of fresh) {
          TURNS.push(rec);
          if (rec.cell + 1 > window.__CELLS__) window.__CELLS__ = rec.cell + 1;
        }
        $('slider').max = TURNS.length - 1;
        if (wasEnd) i = TURNS.length - 1;
        draw();
      }
      __live(!d.waiting, TURNS.length);
    })
    .catch(() => __live(false, TURNS.length));
}

window.addEventListener('DOMContentLoaded', () => {
  // A live board opens at the tail, not at turn 0: the interesting turn
  // is the one that just happened. From here `wasEnd` above does the
  // rest — scrub back and it leaves you there, scrub to the end and it
  // starts following again.
  if (TURNS.length) { i = TURNS.length - 1; draw(); }
  __live(TURNS.length > 0, TURNS.length);
  setInterval(__sync, POLL_MS);
});
"""


def render_html(
    records: List[dict],
    source: str = "",
    live: bool = False,
    poll_ms: int = DEFAULT_POLL_MS,
) -> str:
    """The whole page, as one string.

    `live=False` is GUI-1 unchanged: nothing is fetched when the file is
    opened. `live=True` adds one stylesheet rule, one badge and the poll
    loop, and nothing else — the static page must stay byte for byte what
    it was, so every addition is appended rather than woven in.
    """
    rows = normalise(records)
    cells = cell_count(rows)
    if live:
        sub = (
            f"live from {_esc(source)} over {HOST} — {POLL_PATH} every "
            f"{int(poll_ms)} ms.\n"
            f"  {len(rows)} turns so far, {cells} cells. Still no model and no "
            "second bus: this is the log, as it is written."
        )
        badge = '\n  <div class="dot" id="live">waiting</div>'
        live_css = LIVE_CSS
        live_js = (
            f"const POLL_PATH = {json.dumps(POLL_PATH)};\n"
            f"const POLL_MS = {int(poll_ms)};\n"
            f"const LOG_NAME = {json.dumps(source)};\n"
            f"{LIVE_JS}"
        )
    else:
        sub = (
            f"replay of {_esc(source)} — {len(rows)} turns,\n"
            f"  {cells} cells. No network, no model, no live loop: this is "
            "the log."
        )
        badge = ""
        live_css = ""
        live_js = ""
    live_flag = "true" if live else "false"
    # A replay that dies on its last turn can only be watched once. The
    # box is not offered on a live board: there the last turn is only the
    # last one so far, and Play waits for the next instead of rewinding.
    loop_box = (
        ""
        if live
        else '\n    <label class="loopbox">'
             '<input type="checkbox" id="loop" checked> loop</label>'
    )
    blocks = "\n".join(
        f'    <section class="block off" id="{bid}">'
        f'<h2>{_esc(name)}</h2><div class="val">—</div>'
        f'<div class="note">{_esc(note)}</div></section>'
        for bid, name, note in BLOCKS
    )
    # GUI-3. The voxels are laid out here, from the coordinates the log
    # carries and from nothing else: side comes from the log, and a log
    # without a pose gets no cube at all rather than an empty aquarium.
    # A live board is built the same way, so one opened before the first
    # pose line was written needs a reload to grow one — the shape is
    # read once, the state every poll.
    side = cube_side(rows)
    if side > 0:
        # The 27 voxels, placed here and not in the browser: their
        # coordinates are the log's, the offsets are arithmetic on VOX,
        # and the page that comes out can be checked without opening it.
        mid = (side - 1) / 2
        voxels = []
        for z in range(side):
            for y in range(side):
                for x in range(side):
                    off = (
                        f"translate3d({(x - mid) * VOX:g}px,"
                        f"{(mid - y) * VOX:g}px,{(z - mid) * VOX:g}px)"
                    )
                    voxels.append(
                        f'        <div class="cell3d" data-v="{x},{y},{z}"'
                        f' style="transform:{off}">'
                        + "".join(f'<i class="f {f}"></i>' for f in FACES)
                        + '<b class="beak"></b></div>'
                    )
        slices = []
        for z in range(side):
            voxrows = []
            for y in range(side - 1, -1, -1):
                voxrows.append(
                    '<div class="voxrow">'
                    + "".join(
                        f'<div class="vox" data-v="{x},{y},{z}"></div>'
                        for x in range(side)
                    )
                    + "</div>"
                )
            slices.append(
                f'        <div class="slice"><b>z = {z}</b>'
                + "".join(voxrows)
                + "</div>"
            )
        cube_html = (
            '    <section class="cube" id="cube">\n'
            f'      <h2>cube {side}\u00d7{side}\u00d7{side}</h2>\n'
            '      <div id="stage3d"><div id="world">\n'
            + "\n".join(voxels)
            + '\n      </div></div>\n'
            '      <div class="viewbar"><button id="reset3d">reset view'
            '</button><span id="pose"></span></div>\n'
            '      <details class="mini"><summary>slices</summary>\n'
            + "\n".join(slices)
            + '\n      </details>\n    </section>\n'
        )
        think_html = (
            '\n  <section class="think"><h2>thought</h2>'
            '<div id="thought"></div></section>'
        )
        stage_open = '\n  <div class="stage">\n' + cube_html + '    <div>'
        stage_close = "\n    </div>\n  </div>"
        cube_css = CUBE_CSS
        cube_js = (
            f"const HEADINGS = {json.dumps(list(HEADING_NAME))};\n{CUBE_JS}"
        )
        # The strip of cells is the same pose in one dimension, and with a
        # cube on the page it is a hundred boxes that lie about the shape
        # of the world. The ring, which has nothing else, keeps it.
        ring_attr = " hidden"
    else:
        stage_open = stage_close = cube_html = cube_css = cube_js = ""
        think_html = ""
        ring_attr = ""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>echoAI · board</title>
<style>{CSS}{cube_css}{live_css}</style>
</head><body>
<header>
  <h1>echoAI · board</h1>
  <div class="sub">{sub}</div>{badge}
</header>
<main>{stage_open}
  <div class="ring" id="ringbox"{ring_attr}><pre id="ring"></pre></div>
  <div class="sub" id="where" style="margin-top:8px"></div>{think_html}
  <div class="grid">
    <section class="block off" id="q"><h2>Q</h2>
      <div class="bars" id="qbars"></div>
      <div class="note" id="qnote"></div></section>
{blocks}
  </div>{stage_close}
  <div class="controls">
    <button id="prev">◀ prev</button>
    <button id="play">play</button>
    <button id="next">next ▶</button>
    <input type="range" id="slider" min="0" value="0" step="1">{loop_box}
  </div>
  <div class="legend">
    solid green = a fact the loop recorded · dashed grey = a hypothesis
    the cortex proposed · red = the gate or the map disagreed<br>
    G goal · T threat · N novel · · empty · ? not yet stood on ·
    @ the agent<br>
    CAM MISS is N (first turn on this slot), T red is S (predicted and
    was wrong), Q blue is δ ≠ 0. Three learnings, counted apart.<br>
    The log carries no per-turn reject flag, so a cortex that woke and
    said nothing reads the same as one whose reply was refused.
  </div>
</main>
<script>
const TURNS = {_payload(rows)};
const SYMBOL = {json.dumps(SYMBOL, ensure_ascii=False)};
const ACTIONS = {json.dumps(list(ACTION_NAME))};
const GATES = {json.dumps(list(GATE_NAME))};
window.__CELLS__ = {cells};
const LIVE = {live_flag};
{JS}{cube_js}{live_js}
</script>
</body></html>
"""


# The last parse of the log, keyed by (mtime, size). A poll every 200 ms
# must not re-read a growing file for nothing.
_CACHE: Dict[str, object] = {"key": None, "rows": []}


def read_live(path: Path) -> Tuple[List[dict], bool]:
    """The records on disk right now, and whether we are still waiting.

    Two differences from `read_records`, both because the writer is still
    running. A log that does not exist yet is not an error — the loop may
    not have started — it is `waiting`. And a final line torn in half by a
    write that landed between our stat and our read is dropped, because it
    will be whole on the next poll; a bad line anywhere earlier is a
    corrupt log and is raised, not swallowed.
    """
    try:
        st = path.stat()
    except OSError:
        return [], True
    key = (st.st_mtime_ns, st.st_size)
    if _CACHE["key"] == key:
        return list(_CACHE["rows"]), False

    rows: List[dict] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for n, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            if n == len(lines) - 1:
                break
            raise
    _CACHE["key"] = key
    _CACHE["rows"] = rows
    return list(rows), False


def _from_param(query: str, total: int) -> int:
    """`?from=N`, parsed by hand.

    The board does not import a URL library to read one integer, and junk
    reads as 0 rather than as an error: a viewer that asks badly gets the
    whole log, never a stack trace.
    """
    for part in query.split("&"):
        if part.startswith("from="):
            digits = part[5:]
            if digits.isdigit():
                return min(int(digits), total)
    return 0


def make_handler(path: Path, poll_ms: int):
    """A handler bound to one log file.

    Two routes and no files: nothing on disk is reachable by URL, so there
    is no path to traverse. `/` renders the same page `render_html` writes,
    with the turns known at that moment; `/turns.json?from=N` answers with
    the turns after N and nothing else.
    """

    class BoardHandler(http.server.BaseHTTPRequestHandler):
        server_version = "echoai-board"

        def log_message(self, fmt, *args) -> None:
            """Quiet. The terminal belongs to the loop, not to the viewer."""

        def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 — stdlib spelling
            route, _, query = self.path.partition("?")
            if route in ("/", "/index.html"):
                rows, _waiting = read_live(path)
                html = render_html(
                    rows, source=path.name, live=True, poll_ms=poll_ms
                )
                self._send(html.encode("utf-8"), "text/html; charset=utf-8")
                return
            if route == POLL_PATH:
                raw, waiting = read_live(path)
                rows = normalise(raw)
                start = _from_param(query, len(rows))
                body = json.dumps(
                    {
                        "total": len(rows),
                        "from": start,
                        "waiting": waiting,
                        "cells": cell_count(rows) if rows else 1,
                        "turns": rows[start:],
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
                return
            self._send(b"not here\n", "text/plain; charset=utf-8", 404)

    return BoardHandler


def make_server(
    path, port: int = DEFAULT_PORT, poll_ms: int = DEFAULT_POLL_MS
):
    """Bound to the loopback and nowhere else. Port 0 lets the OS pick."""
    server = http.server.ThreadingHTTPServer(
        (HOST, int(port)), make_handler(Path(path), int(poll_ms))
    )
    server.daemon_threads = True
    return server


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m echoai.nexus0.board",
        description="Turn a thought jsonl into one self-contained HTML board.",
    )
    ap.add_argument("path", help="thought jsonl written by bench --thought")
    ap.add_argument("-o", "--out", default=None, help="default: lab/board.html")
    ap.add_argument(
        "--follow", action="store_true",
        help=f"serve a live board on {HOST} instead of writing a file",
    )
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument(
        "--poll", type=int, default=DEFAULT_POLL_MS, help="poll interval, ms"
    )
    args = ap.parse_args(argv)

    path = Path(args.path)
    if args.follow:
        # A log that is not there yet is not an error here: the loop may
        # not have started. The board says so and keeps serving.
        server = make_server(path, port=args.port, poll_ms=args.poll)
        host, port = server.server_address[0], server.server_address[1]
        sys.stdout.write(
            f"http://{host}:{port}/  poll {args.poll} ms  route {POLL_PATH}\n"
        )
        if not path.is_file():
            sys.stdout.write(f"waiting for {path} — nothing written yet\n")
        sys.stdout.write("Ctrl-C to stop\n")
        sys.stdout.flush()
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            sys.stdout.write("\n")
        finally:
            server.server_close()
        return 0

    if not path.is_file():
        sys.stderr.write(f"no such log: {path}\n")
        return 1
    records = read_records(path)
    if not records:
        sys.stderr.write(f"empty log: {path}\n")
        return 1

    out = (
        Path(args.out)
        if args.out
        else Path(__file__).resolve().parents[1] / "lab" / "board.html"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(records, source=path.name)
    out.write_text(html, encoding="utf-8")
    # st_size, not len(html): the page is UTF-8 and the ring glyphs are
    # multi-byte, so the two differ by about 1.5 kB.
    rows = normalise(records)
    side = cube_side(rows)
    sys.stdout.write(
        f"{out}  {out.stat().st_size} bytes  {len(records)} turns  "
        f"{cell_count(rows)} cells"
        + (f"  cube {side}x{side}x{side}\n" if side else "\n")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
