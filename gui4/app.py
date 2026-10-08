"""GUI-4 main window.

Tabs: Casos, Red neuronal, Dron 3D, Banco, Evidencia, Tutorial.

The window is an observer.  It reads snapshots published by the engine of
NEURAL-VIZ-1 (imported, never modified) and draws them.  It never calls an
action, never writes a memory and never hides a number's origin.

Tk is imported inside :func:`main` so this module stays importable without a
display, which the tests rely on.
"""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Optional

from . import ORIGIN_BENCH, ORIGIN_EVIDENCE, ORIGIN_LIVE, ORIGINS
from . import benchmark, capture, catalog, evidence, neural

ECHOAI = Path(__file__).resolve().parents[1]
VIZ_TASKS = ECHOAI / "viz_tasks"

BG = "#0b0e14"
PANEL = "#12161f"
TEXT = "#c4cede"
DIM = "#6e7a8e"
GOLD = "#ffcd5c"
OKC = "#56e696"
BADC = "#ff6078"

TUTORIAL = """GUI-4 · cómo leer esta ventana

Tres orígenes, nunca mezclados en una misma cifra:

  en vivo            el agente real corre ahora en esta ventana
  banco reducido     un banco real de ECHO-3 corre ahora con menos casos
  evidencia sellada  se reproduce un informe cerrado de lab/, sin recalcular

La pestaña «Casos» los lista todos. Un caso que no puede ejecutarse aquí
aparece deshabilitado con su motivo escrito; no se oculta.

Red neuronal
  Arriba, el monitor CAPACITY-1: 512 LIF y 128 Adaptive-LIF, con la historia
  de spikes avanzando hacia la derecha. Es un monitor medido, no la política.
  Abajo, el camino que sí decide: CAM → Q → gate → acción. El amarillo es la
  acción ejecutada y el recuadro de la derecha, el veredicto del gate.
  ΔQ distinto de cero significa que el agente aprendió algo en ese turno.

Banco
  Ejecuta bancos reales con denominador recortado y enseña al agente junto a
  su control. Exporta un JSON con semillas y denominador para que el número
  se pueda rastrear. No es un certificado.

Grabación
  «Capturar» escribe un PNG. «Grabar» vuelca un PNG por turno más un
  manifest.json; con ffmpeg instalado también monta el MP4. Cada frame lleva
  su marca de origen.

Lo que esta ventana no demuestra
  No demuestra inteligencia general ni autonomía física. No hay dron, ni
  jaula, ni hardware-in-the-loop. Un caso en vivo es una ejecución, no una
  medida: n=1 no es un resultado. Los certificados de ECHO-3 salen de lab/ y
  de sus hashes, no de esta pantalla.
"""


class Gui4:
    """The window.  Everything slow happens off the Tk thread."""

    def __init__(self, tk, ttk, ImageTk):
        self.tk, self.ttk, self.ImageTk = tk, ttk, ImageTk
        self.root = tk.Tk()
        self.root.title("echoAI · GUI-4")
        self.root.configure(bg=BG)
        self.root.geometry("1360x860")

        self.history = neural.SpikeHistory(width=200, bands=22)
        self.renderer = neural.Renderer()
        self.engine = None
        self.case: Optional[catalog.Case] = None
        self.origin = ""
        self.last_row: dict = {}
        self.photo = None
        self.recording: Optional[capture.Recording] = None
        self.bench: Optional[benchmark.Runner] = None
        self.presentation = tk.BooleanVar(value=False)
        self.paused = False

        self._style()
        self._top()
        self._tabs()
        self.root.bind("<F5>", lambda _event: self.shoot())
        self.root.bind("<space>", lambda _event: self.toggle_pause())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(80, self._pump)

    # ----------------------------------------------------------------- chrome

    def _style(self) -> None:
        style = self.ttk.Style()
        try:
            style.theme_use("clam")
        except self.tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT,
                        padding=(16, 7))
        style.map("TNotebook.Tab", background=[("selected", "#1d2432")])
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TButton", background=PANEL, foreground=TEXT)

    def _top(self) -> None:
        tk, ttk = self.tk, self.ttk
        bar = tk.Frame(self.root, bg=PANEL)
        bar.pack(fill="x")
        tk.Label(bar, text="echoAI · GUI-4", bg=PANEL, fg=TEXT,
                 font=("TkDefaultFont", 13, "bold")).pack(side="left", padx=12, pady=7)
        self.origin_label = tk.Label(bar, text="sin caso", bg=PANEL, fg=GOLD)
        self.origin_label.pack(side="left", padx=8)
        self.status = tk.Label(bar, text="", bg=PANEL, fg=DIM)
        self.status.pack(side="left", padx=12)

        for text, command in (("Capturar (F5)", self.shoot),
                              ("Grabar", self.toggle_record),
                              ("Pausa (espacio)", self.toggle_pause),
                              ("Paso", self.step)):
            ttk.Button(bar, text=text, command=command).pack(side="right", padx=4, pady=6)
        ttk.Checkbutton(bar, text="Presentación", variable=self.presentation,
                        command=self._presentation).pack(side="right", padx=8)

    def _tabs(self) -> None:
        self.notebook = self.ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self._tab_cases()
        self._tab_neural()
        self._tab_tree()
        self._tab_world()
        self._tab_bench()
        self._tab_evidence()
        self._tab_tutorial()

    # ------------------------------------------------------------------ casos

    def _tab_cases(self) -> None:
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Casos")
        header = tk.Frame(frame, bg=BG)
        header.pack(fill="x", pady=(6, 2))
        tk.Label(header, text="TODOS LOS CASOS DE USO", bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 12, "bold")).pack(side="left", padx=10)
        tk.Label(header, bg=BG, fg=DIM,
                 text="cada caso dice qué demuestra, qué control lo contrasta y qué no "
                      "demuestra").pack(side="left", padx=8)

        canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>",
                   lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        # Without this the cards keep their requested width and leave the right
        # third of the tab empty.
        canvas.bind("<Configure>",
                    lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.bind_all("<MouseWheel>",
                        lambda event: canvas.yview_scroll(
                            -1 if event.delta > 0 else 1, "units"))
        canvas.bind_all("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0))
        scroll.pack(side="right", fill="y")

        for case in catalog.CASES:
            self._case_card(inner, case)

    def _case_card(self, parent, case: catalog.Case) -> None:
        tk, ttk = self.tk, self.ttk
        runnable, reason = case.availability()
        card = tk.Frame(parent, bg=PANEL, padx=12, pady=9)
        card.pack(fill="x", pady=4, padx=6)
        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x")
        tk.Label(head, text=case.title, bg=PANEL, fg=TEXT if runnable else DIM,
                 font=("TkDefaultFont", 11, "bold")).pack(side="left")
        tk.Label(head, text=f"  {case.phase}  ·  {ORIGINS[case.origin]}", bg=PANEL,
                 fg=GOLD if runnable else DIM).pack(side="left")
        if case.seconds:
            tk.Label(head, text=f"  {case.seconds}", bg=PANEL, fg=DIM).pack(side="left")
        button = ttk.Button(head, text="Ejecutar" if runnable else "No disponible",
                            command=lambda c=case: self.run_case(c))
        button.pack(side="right")
        if not runnable:
            button.state(["disabled"])
        for label, value, colour in (("Demuestra", case.shows, TEXT),
                                     ("Control", case.control, DIM),
                                     ("No demuestra", case.limit, DIM)):
            line = tk.Frame(card, bg=PANEL)
            line.pack(fill="x", pady=1)
            tk.Label(line, text=f"{label}:", bg=PANEL, fg=DIM, width=13,
                     anchor="w").pack(side="left")
            tk.Label(line, text=value, bg=PANEL, fg=colour, anchor="w",
                     wraplength=980, justify="left").pack(side="left")
        if not runnable and reason:
            tk.Label(card, text=f"⚠ {reason}", bg=PANEL, fg=BADC, anchor="w",
                     wraplength=1100, justify="left").pack(fill="x", pady=(4, 0))

    # ----------------------------------------------------------------- neural

    def _tab_neural(self) -> None:
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Red neuronal")
        self.neural_canvas = tk.Label(frame, bg=BG)
        self.neural_canvas.pack(fill="both", expand=True)
        rail = tk.Frame(frame, bg=PANEL)
        rail.pack(fill="x")
        tk.Label(rail, text="ticks/s", bg=PANEL, fg=DIM).pack(side="left", padx=(12, 4))
        self.rate = tk.Scale(rail, from_=1, to=60, orient="horizontal", bg=PANEL,
                             fg=TEXT, highlightthickness=0, troughcolor=BG,
                             command=self._rate)
        self.rate.set(12)
        self.rate.pack(side="left", pady=2)
        self.neural_note = tk.Label(rail, text="", bg=PANEL, fg=DIM)
        self.neural_note.pack(side="left", padx=14)

    def _tab_tree(self) -> None:
        """The classic orbitable node graph, reused from NEURAL-VIZ-1.

        The raster says *when* the monitor fired; this says *what is wired to
        what*.  Both are useful, so GUI-4 keeps the old view rather than
        replacing it.
        """
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Red · árbol")
        self.tree = None
        try:
            from echoai.nexus0.neural_viz_gui import NetworkCanvas
            self.tree = NetworkCanvas(tk, frame)
        except Exception as exc:
            tk.Label(frame, bg=BG, fg=DIM, justify="left",
                     text=f"Vista de árbol no disponible: {type(exc).__name__}: {exc}"
                     ).pack(padx=20, pady=20)
            return
        rail = tk.Frame(frame, bg=PANEL)
        rail.pack(fill="x")
        tk.Label(rail, bg=PANEL, fg=DIM, anchor="w",
                 text="arrastra para orbitar · rueda para zoom · "
                      "LIF y Adaptive-LIF son el monitor CAPACITY-1, no la política"
                 ).pack(side="left", padx=12, pady=4)

    def _tab_world(self) -> None:
        frame = self.ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Dron 3D")
        self.world = None
        try:
            from echoai.nexus0.neural_viz_gui import DroneWorldView
            self.world = DroneWorldView(self.tk, frame)
        except Exception as exc:  # VTK missing or no GL: say so, do not crash
            self.tk.Label(frame, bg=BG, fg=DIM, justify="left",
                          text=f"Visor 3D no disponible: {type(exc).__name__}: {exc}\\n"
                               "El resto de GUI-4 funciona igual.").pack(padx=20, pady=20)

    # ------------------------------------------------------------------ banco

    def _tab_bench(self) -> None:
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Banco")
        head = tk.Frame(frame, bg=BG)
        head.pack(fill="x", pady=8)
        tk.Label(head, text="BANCO EN GUI", bg=BG, fg=TEXT,
                 font=("TkDefaultFont", 12, "bold")).pack(side="left", padx=10)
        tk.Label(head, bg=BG, fg=DIM,
                 text="bancos reales con denominador recortado · agente frente a su "
                      "control · no es un certificado").pack(side="left")
        ttk.Button(head, text="Ejecutar todos",
                   command=self.run_bench).pack(side="right", padx=6)
        self.bench_export = ttk.Button(head, text="Exportar JSON", command=self.export_bench)
        self.bench_export.pack(side="right")
        self.bench_export.state(["disabled"])
        self.bench_text = tk.Text(frame, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                                  relief="flat", font=("TkFixedFont", 11), height=26)
        self.bench_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.bench_text.insert("1.0",
                               "Pulsa «Ejecutar todos» para correr los bancos rápidos.\n")
        self.bench_text.configure(state="disabled")

    def _tab_evidence(self) -> None:
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Evidencia")
        text = tk.Text(frame, bg=PANEL, fg=TEXT, relief="flat",
                       font=("TkFixedFont", 11), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        lines = ["EVIDENCIA SELLADA · reproducida desde lab/, sin recalcular nada", ""]
        for name in evidence.READERS:
            record = evidence.read(name)
            if not record.available:
                lines += [f"{record.phase}: {record.reason}", ""]
                continue
            lines.append(f"{record.phase}  ·  {record.source}  ·  sha {record.sha8}")
            for figure in record.figures:
                detail = f"   ({figure.detail})" if figure.detail else ""
                lines.append(f"    {figure.label:<44} {figure.value}{detail}")
            if record.limit:
                lines.append(f"    límite: {record.limit}")
            lines.append("")
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")

    def _tab_tutorial(self) -> None:
        tk, ttk = self.tk, self.ttk
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Tutorial")
        text = tk.Text(frame, bg=PANEL, fg=TEXT, relief="flat",
                       font=("TkFixedFont", 11), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", TUTORIAL)
        text.configure(state="disabled")

    # ---------------------------------------------------------------- actions

    def run_case(self, case: catalog.Case) -> None:
        runnable, reason = case.availability()
        if not runnable:
            self._status(reason, BADC)
            return
        self.case = case
        self.origin = ORIGINS[case.origin]
        self.origin_label.configure(text=f"{case.phase} · {self.origin}")
        if case.origin == ORIGIN_LIVE:
            self._start_live(case)
            self.notebook.select(1)
        elif case.origin == ORIGIN_BENCH:
            self.run_bench([case.ident])
            self.notebook.select(4)
        else:
            self.notebook.select(5)
            self._status(f"{case.phase}: evidencia sellada en la pestaña Evidencia", GOLD)

    def _start_live(self, case: catalog.Case) -> None:
        from echoai.nexus0.neural_viz_gui import RuntimeEngine, TaskSpec
        self._stop_engine()
        try:
            spec = TaskSpec.load(VIZ_TASKS / str(case.task))
            self.engine = RuntimeEngine(spec, ticks_per_second=int(self.rate.get()))
        except Exception as exc:
            self._status(f"{type(exc).__name__}: {exc}", BADC)
            return
        self.history.clear()
        self.paused = False
        self.engine.start()
        self._status(f"en vivo · {spec.title}", OKC)

    def _stop_engine(self) -> None:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None

    def toggle_pause(self) -> None:
        if self.engine is None:
            return
        self.paused = not self.paused
        self.engine.set_paused(self.paused)
        self._status("en pausa" if self.paused else "en vivo",
                     GOLD if self.paused else OKC)

    def step(self) -> None:
        if self.engine is not None:
            self.engine.step_once()

    def _rate(self, value) -> None:
        if self.engine is not None:
            self.engine.set_rate(int(float(value)))

    def _presentation(self) -> None:
        self.renderer.presentation = bool(self.presentation.get())

    def shoot(self) -> None:
        image = self.renderer.render(self.history, self.last_row, self.origin,
                                     self.case.ident if self.case else "")
        path = capture.screenshot(image, self.case.ident if self.case else "gui4")
        self._status(f"captura → {path}" if path else "no se pudo capturar",
                     OKC if path else BADC)

    def toggle_record(self) -> None:
        if self.recording is not None and not self.recording.closed:
            manifest = self.recording.close()
            ok, message = self.recording.encode()
            self._status(f"grabación: {manifest['frames']} frames · {message}",
                         OKC if ok else GOLD)
            self.recording = None
            return
        origin = self.case.origin if self.case else ORIGIN_LIVE
        self.recording = capture.start(self.case.ident if self.case else "gui4", origin)
        self._status(f"grabando en {self.recording.directory}", OKC)

    def run_bench(self, cases: Optional[list[str]] = None) -> None:
        if self.bench is not None and self.bench.running:
            self._status("el banco ya está corriendo", GOLD)
            return
        chosen = cases or list(catalog.BENCH_RUNNERS)
        self.bench = benchmark.Runner(chosen)
        self._bench_write(f"ejecutando {len(chosen)} caso(s): {', '.join(chosen)}\n",
                          clear=True)
        self.bench.start()

    def export_bench(self) -> None:
        if self.bench is None or not self.bench.results:
            self._status("no hay resultados que exportar", GOLD)
            return
        path = self.bench.export()
        self._bench_write(f"\nexportado → {path}\n")
        self._status(f"exportado → {path}", OKC)

    def _bench_write(self, text: str, clear: bool = False) -> None:
        self.bench_text.configure(state="normal")
        if clear:
            self.bench_text.delete("1.0", "end")
        self.bench_text.insert("end", text)
        self.bench_text.see("end")
        self.bench_text.configure(state="disabled")

    def _status(self, text: str, colour: str = DIM) -> None:
        self.status.configure(text=text, fg=colour)

    # ------------------------------------------------------------------- loop

    def _pump(self) -> None:
        self._drain_engine()
        self._drain_bench()
        self._draw()
        self.root.after(60, self._pump)

    def _drain_engine(self) -> None:
        if self.engine is None:
            return
        row = None
        # Every published turn enters the raster; dropping the intermediate
        # ones would leave holes in the spike history.
        while True:
            try:
                row = self.engine.out.get_nowait()
            except queue.Empty:
                break
            self.history.push(row)
            self.last_row = row
        if row is None:
            return
        if self.world is not None:
            try:
                self.world.update(row)
            except Exception:
                pass
        # The graph only needs the newest turn: it draws wiring, not history.
        if self.tree is not None and self.notebook.index("current") == 2:
            try:
                self.tree.activity(row)
            except Exception:
                pass
        if self.engine.last_error:
            self._status("ERROR · " + self.engine.last_error, BADC)

    def _drain_bench(self) -> None:
        if self.bench is None:
            return
        while True:
            try:
                kind, ident, payload, total = self.bench.events.get_nowait()
            except queue.Empty:
                break
            if kind == "begin":
                self._bench_write(f"  · {ident} …\n")
            elif kind == "done":
                self._bench_write(
                    f"    {payload.phase:<11} {benchmark.summary(payload)}\n"
                    f"      semillas {payload.seeds} · {payload.elapsed_s:.2f} s"
                    f" · {payload.note}\n")
            elif kind == "error":
                self._bench_write(f"    ERROR {ident}: {payload}\n")
            elif kind == "finished":
                self._bench_write(f"\nlisto: {payload} de {total} casos. "
                                  "Banco reducido, no certificado.\n")
                self.bench_export.state(["!disabled"])
                self._status("banco terminado", OKC)

    def _draw(self) -> None:
        width = max(640, self.neural_canvas.winfo_width())
        height = max(400, self.neural_canvas.winfo_height())
        self.renderer.size = (width, height)
        image = self.renderer.render(self.history, self.last_row, self.origin,
                                     self.case.ident if self.case else "")
        self.photo = self.ImageTk.PhotoImage(image)
        self.neural_canvas.configure(image=self.photo)
        if self.recording is not None and not self.recording.closed and self.last_row:
            self.recording.add(image, self.last_row.get("turn"))
            self.neural_note.configure(text=f"grabando · {self.recording.frames} frames")
        elif self.engine is not None:
            self.neural_note.configure(
                text=f"turno {self.last_row.get('turn', 0)} · "
                     f"{len(self.history.ticks)} turnos en la historia")

    def close(self) -> None:
        self._stop_engine()
        if self.bench is not None:
            self.bench.cancel()
        if self.recording is not None:
            self.recording.close()
        self.root.destroy()

    def run(self) -> int:
        self.root.mainloop()
        return 0


def main(argv: Optional[list[str]] = None) -> int:
    import tkinter as tk
    from tkinter import ttk
    from PIL import ImageTk
    return Gui4(tk, ttk, ImageTk).run()
