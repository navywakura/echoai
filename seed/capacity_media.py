"""Publishable charts and 3D tree GIFs derived from verified capacity evidence.

Rendering is outside measurement. Tree positions and animation speed are visual;
indices, weights, scores and program outputs are reconstructed and checked.
"""
import csv
import html
import json
import math
import os
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))
os.environ.setdefault("MPLCONFIGDIR", str(REPO / "lab/tools/matplotlib-capacity"))
from seed import capacity_study as study
from echoai.seed import dsl
from echoai.seed.learn import Library

OUT = REPO / "lab/publication/capacity-20261001"
REFERENCE = "e3497940"
CASES = ("2013d3e2", "a68b268e", "e3497940")
BG, PANEL, INK, MUTED, PURPLE = "#09070f", "#15101f", "#f3edf9", "#aea3bc", "#bb8bfa"
ARC_COLORS = ("#11111a", "#2581ff", "#ee414c", "#41b875", "#f7d64c",
              "#9396a2", "#d852c7", "#ff9e48", "#54d6ef", "#a63b55")


def trace_operation(guide, task, name):
    study.require(name in guide.names, "unknown operation")
    branches = []
    for feature in guide.features(task):
        indices = guide._indices(feature, name)
        branches.append({"feature": feature, "indices": list(indices),
                         "weights": [guide.weights[i] for i in indices]})
    raw = sum(sum(b["weights"]) for b in branches)
    scores = {op: sum(guide.weights[i] for f in guide.features(task)
                      for i in guide._indices(f, op)) for op in guide.names}
    peak = max(scores.values())
    score = .05 + .55 * raw / peak if peak else .05
    study.require(score == guide.probs(task)[name], "trace score does not reproduce guide")
    ids = [i for b in branches for i in b["indices"]]
    return {"operation": name, "units": guide.units, "branches": branches,
            "raw_score": raw, "normalization_peak": peak, "guide_score": score,
            "reads": len(ids), "unique_indices": len(set(ids)),
            "nonzero_reads": sum(w > 0 for b in branches for w in b["weights"]),
            "representation": "deterministic reconstruction; coordinates and camera motion illustrative",
            "not_lif_activity": True, "guide_computed_once_before_search": True}


def evidence(profile):
    guides, _ = study.fit(profile["source_profile"])
    guide = guides["guide500000"]
    info = study.original.guide_info({"guide500k": guide})["guide500k"]
    original_info = study.read(study.HISTORY / "training.json")["guides"]["guide500k"]
    study.require(info == original_info, "historical guide weights differ")
    lib = Library(profile["source_profile"]["state"]["concepts"],
                  profile["source_profile"]["state"]["prior"])
    records = []
    for tid in CASES:
        task = study.checked_task(tid, profile["source_profile"])
        path = study.HISTORY / "primary/decisions/guide500k" / tid / "arc-decisions.jsonl"
        journal = [json.loads(line) for line in path.read_text().splitlines()]
        saved_scores = next(row["guide"] for row in journal if row["kind"] == "hypothesis")
        study.require(guide.probs(task) == saved_scores, "recorded guide scores differ")
        row = study.read(study.HISTORY / "primary/results/guide500k" / (tid+".json"))
        study.require(row["correct"], "illustration is not an exact success")
        grid = dsl.G(task["test"][0]["input"])
        steps = []
        for number, item in enumerate(row["result"]["program"], 1):
            before = grid
            grid = lib.apply(grid, item)
            steps.append({"number": number, "item": item, "input": before, "output": grid,
                          "trace": trace_operation(guide, task, lib.key(item))})
        study.require([list(r) for r in grid] == row["result"]["predictions"][0], "program prediction differs")
        records.append({"task": tid, "expansions": row["result"]["expansions"],
                        "program": row["result"]["program"], "steps": steps,
                        "source_result_sha256": study.file_hash(study.HISTORY / "primary/results/guide500k" / (tid+".json")),
                        "source_journal_sha256": study.file_hash(path)})
    public = study.checked_task(REFERENCE, profile["source_profile"])
    return guide, public, records


def charts(summary, synthetic, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.facecolor": BG, "axes.facecolor": BG,
                         "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                         "font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none"})
    names = ("Sin guía", "640", "4.096", "16.384", "65.536", "500.000")
    colors = ("#747180", "#78619a", "#946cc3", "#a677dc", "#c99bec", "#e0c4ff")

    def save(fig, name, note):
        fig.text(.08, .035, note, fontsize=9, color=MUTED)
        fig.tight_layout(rect=(0, .07, 1, 1))
        for ext in ("svg", "png"):
            fig.savefig(out / (name+"."+ext), dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.3))
    for i, arm in enumerate(study.ARMS):
        d = summary["arms"][arm]
        if d["status"] == "AUDITED":
            value = 100*d["solved"]/d["of"]
            ax.bar(i, value, color=colors[i], width=.64)
            ax.text(i, value+.09, f'{d["solved"]}/250 · {value:.1f} %', ha="center", fontsize=10)
        else:
            ax.text(i, .16, "Pendiente", ha="center", color=MUTED, fontsize=10)
    ax.set_xticks(range(6), names); ax.set_ylim(0, max(3.2, max((100*d.get("solved", 0)/250 for d in summary["arms"].values()))+.7))
    ax.set_ylabel("Tareas exactas (%)"); ax.set_title("ARC-1 de desarrollo · mismo límite de búsqueda", loc="left", pad=20)
    save(fig, "accuracy", "250 tareas conocidas · 60 programas de entrenamiento separados · no es una puntuación oficial ARC")

    fig, axes = plt.subplots(1, 2, figsize=(10, 5.3))
    for ax, metric, label in ((axes[0], "cpu_seconds", "CPU acumulada (minutos)"),
                              (axes[1], "applications", "Aplicaciones DSL (millones)")):
        scale = 60 if metric == "cpu_seconds" else 1e6
        for i, arm in enumerate(study.ARMS):
            d = summary["arms"][arm]
            if d["status"] == "AUDITED":
                v = d[metric]/scale
                ax.bar(i, v, color=colors[i], width=.7)
                ax.text(i, v+.7, f"{v:.1f}", ha="center", fontsize=9)
        ax.set_xticks(range(6), names, rotation=35, ha="right"); ax.set_title(label, loc="left")
        ax.set_ylim(0, max([d.get(metric, 0)/scale for d in summary["arms"].values()])*1.2)
    save(fig, "cost", "CPU descriptiva; controles históricos y capacidades nuevas en lotes distintos. Renderizado excluido.")

    fig, axes = plt.subplots(1, 2, figsize=(10, 5.3))
    ds = [summary["arms"]["guide"+str(n)] for n in study.CAPACITIES]
    axes[0].plot(study.CAPACITIES, [d["nonzero_units"] for d in ds], "o-", color=PURPLE)
    axes[0].set_xscale("log"); axes[0].set_xlabel("Capacidad (escala logarítmica)")
    axes[0].set_ylabel("Pesos distintos de cero"); axes[0].set_title("Uso después de aprender 60 programas", loc="left", fontsize=11)
    axes[1].bar(range(5), [100*d["nonzero_units"]/d["units"] for d in ds], color=colors[1:])
    for i, d in enumerate(ds):
        v = 100*d["nonzero_units"]/d["units"]
        axes[1].text(i, v+2, f"{v:.2f} %", ha="center", fontsize=9)
    axes[1].set_xticks(range(5), names[1:], rotation=35, ha="right"); axes[1].set_ylim(0, 114)
    axes[1].set_title("Fracción del banco utilizada", loc="left", fontsize=11)
    save(fig, "memory", "Un byte por peso · memoria del banco, no memoria total del solver · no mide nuevas neuronas LIF")

    fig, ax = plt.subplots(figsize=(10, 5.3))
    values = [synthetic["results"][str(n)]["correct"] for n in study.CAPACITIES]
    ax.bar(range(5), values, color=colors[1:])
    for i, v in enumerate(values): ax.text(i, v+.6, f"{v}/40", ha="center")
    ax.set_xticks(range(5), names[1:]); ax.set_ylim(0, 45); ax.set_ylabel("Familia geométrica correcta")
    ax.set_title("Control sintético · clasificación de cuatro transformaciones", loc="left", pad=20)
    save(fig, "synthetic", "80 ejemplos de entrenamiento · 40 de desarrollo · esta clasificación NO mide respuestas ARC")


def font(size, bold=False):
    from PIL import ImageFont
    path = "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono" + ("-Bold" if bold else "") + ".ttf"
    if not Path(path).exists():
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono" + ("-Bold" if bold else "") + ".ttf"
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype("DejaVuSansMono.ttf", size)


def grid(draw, values, x, y, width=240, height=150):
    h, w = len(values), len(values[0])
    cell = max(2, min(width//w, height//h, 22))
    for iy, row in enumerate(values):
        for ix, val in enumerate(row):
            xx, yy = x+ix*cell, y+iy*cell
            draw.rectangle((xx, yy, xx+cell-1, yy+cell-1), fill=ARC_COLORS[val], outline="#292132")


def tree_frame(trace, title, subtitle, before, after, index=0, count=28):
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (1120, 650), BG)
    draw = ImageDraw.Draw(image)
    draw.text((32, 22), "RxLabs / ECHO 4.5", font=font(18, True), fill=PURPLE)
    draw.text((32, 55), title, font=font(25, True), fill=INK)
    draw.text((32, 94), subtitle, font=font(13), fill=MUTED)
    draw.line((32, 123, 1088, 123), fill="#3a294a", width=1)
    draw.rounded_rectangle((776, 143, 1088, 560), radius=10, fill=PANEL)
    draw.text((800, 160), "CONTEXTO DE LA REJILLA", font=font(13, True), fill=MUTED)
    draw.text((800, 190), "Entrada", font=font(13), fill=INK); grid(draw, before, 800, 215)
    output_label = "Salida del paso" if trace.get("role") == "VERIFIED_PROGRAM_STEP" else "Salida del ejemplo público"
    draw.text((800, 382), output_label, font=font(13), fill=INK); grid(draw, after, 800, 408, height=120)
    angle = 2*math.pi*index/count
    def project(x, y, z):
        xx = x*math.cos(angle)-z*math.sin(angle)
        zz = x*math.sin(angle)+z*math.cos(angle)
        scale = 1/(1+.12*zz)
        return (int(390+xx*235*scale), int(490-y*105*scale+zz*18))
    root = project(0, 0, 0)
    trunk = project(0, .52, 0)
    draw.line((*root, *trunk), fill=PURPLE, width=4)
    draw.ellipse((root[0]-8, root[1]-8, root[0]+8, root[1]+8), fill=INK)
    draw.text((root[0]-110, root[1]+20), trace["operation"], font=font(17, True), fill=INK)
    branches = trace["branches"]
    maximum = max((w for b in branches for w in b["weights"]), default=1) or 1
    edges, nodes = [], []
    active = min(len(branches)-1, int(index*len(branches)/count)) if branches else -1
    for j, branch in enumerate(branches):
        theta = 2*math.pi*j/max(1, len(branches))
        center = (.64*math.cos(theta), 1.35+.2*math.sin(theta), .64*math.sin(theta))
        pt = project(*center)
        draw.line((*trunk, *pt), fill=PURPLE if j == active else "#644675", width=3 if j == active else 1)
        nodes.append((pt, 5, "#e0bbff"))
        for k, (weight_id, weight) in enumerate(zip(branch["indices"], branch["weights"])):
            phase = theta+(k-3.5)*.12
            leaf = project((.85+.05*(k%2))*math.cos(phase), 2.04+.10*(k%4),
                           (.85+.05*(k%2))*math.sin(phase))
            color = (int(83+150*weight/maximum), int(63+122*weight/maximum), int(113+137*weight/maximum)) if weight else (51, 46, 60)
            edges.append((pt, leaf, color)); nodes.append((leaf, 3+int(3*weight/maximum), color))
        draw.text((pt[0]+7, pt[1]+4), str(j+1), font=font(11), fill=INK)
    for a, b, color in edges: draw.line((*a, *b), fill=color, width=1)
    for (x, y), radius, color in nodes: draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
    branch = branches[active] if active >= 0 else {"feature": "Sin rasgos comunes", "indices": [], "weights": []}
    draw.text((32, 145), "ÁRBOL DE ASOCIACIONES", font=font(14, True), fill=INK)
    draw.text((32, 173), f'{trace["unique_indices"]} pesos únicos / {trace["reads"]} lecturas', font=font(13), fill=MUTED)
    draw.text((32, 199), f'Suma {trace["raw_score"]} · prioridad {trace["guide_score"]:.3f}', font=font(13), fill=PURPLE)
    draw.text((32, 538), f'Rama {active+1}: {branch["feature"]}', font=font(13), fill=INK)
    draw.text((32, 560), "Índices: " + ", ".join(map(str, branch["indices"])), font=font(10), fill=MUTED)
    draw.line((32, 590, 1088, 590), fill="#3a294a")
    draw.text((32, 605), "Reconstrucción comprobada · pesos reales · posición 3D y giro ilustrativos", font=font(13), fill=MUTED)
    draw.text((32, 626), "Guía calculada antes de buscar. No es una grabación de neuronas LIF ni de tiempos de inferencia.", font=font(11), fill=MUTED)
    return image


def animation(trace, title, subtitle, before, after, path):
    from PIL import Image
    frames = [tree_frame(trace, title, subtitle, before, after, i) for i in range(28)]
    frames[0].save(path.with_suffix(".png"))
    palette = frames[0].quantize(colors=128)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    frames[0].save(path.with_suffix(".gif"), save_all=True, append_images=frames[1:],
                   duration=100, loop=0, optimize=False, disposal=2)
    study.save(path.with_suffix(".json"), trace)


def needs_render(path, trace):
    if not all(path.with_suffix(ext).exists() for ext in (".png", ".gif", ".json")):
        return True
    return study.digest(study.read(path.with_suffix(".json"))) != study.digest(trace)


def page(summary, gallery, out):
    esc = html.escape
    options = "".join(f'<option value="{esc(x["file"])}">{esc(x["operation"])}</option>' for x in gallery["operations"])
    rows = ""
    for arm, d in summary["arms"].items():
        label = "Sin guía" if arm == "base" else f'{d["units"]:,}'.replace(",", ".")
        score = f'{d["solved"]}/250' if d["status"] == "AUDITED" else "Pendiente"
        cpu = f'{d["cpu_seconds"]:.1f} s' if d["status"] == "AUDITED" else "—"
        loss = str(len(d["versus_base"]["lost"])) if d["status"] == "AUDITED" else "—"
        rows += f'<tr><td>{label}</td><td>{score}</td><td>{loss}</td><td>{cpu}</td><td>{"Auditado" if d["status"] == "AUDITED" else "Pendiente"}</td></tr>'
    steps = "".join(f'''<article class="step"><h3>{esc(x['task'])} · paso {x['step']}</h3>
        <p>{esc(x['operation'])}</p><img loading="lazy" width="1120" height="650" src="{x['file']}.png" alt="Paso verificado {esc(x['operation'])}">
        <button type="button" class="animate" data-file="{x['file']}">Reproducir GIF</button> <a href="{x['file']}.json">Datos del paso</a></article>''' for x in gallery["steps"])
    first = next(x["file"] for x in gallery["operations"] if x["operation"] == "sym_h")
    text = f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ECHO 4.5 · Banco de capacidad | RxLabs</title><meta name="description" content="Resultados reproducibles de memoria asociativa, gráficas y visualizaciones 3D de operaciones verificadas.">
<style>
:root{{color-scheme:dark;--bg:{BG};--panel:{PANEL};--ink:{INK};--muted:{MUTED};--accent:{PURPLE}}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}header{{border-bottom:1px solid #40324d;padding:12px 0 38px}}.brand,.tag,button,select,th{{font-family:ui-monospace,monospace}}.brand{{color:var(--accent);font-size:19px}}h1{{font-size:clamp(30px,5vw,56px);letter-spacing:-.04em;line-height:1.1;margin:28px 0 20px}}h2{{font-size:25px;margin-top:55px}}h3{{margin-bottom:6px}}p{{max-width:850px}}.tag,.note{{color:var(--muted)}}.tag{{font-size:13px}}a{{color:var(--accent)}}.controls{{display:flex;gap:12px;flex-wrap:wrap;align-items:center}}select,button{{border:1px solid #69527f;background:var(--panel);color:var(--ink);padding:11px 15px;border-radius:3px;font-size:14px;cursor:pointer}}button:hover{{background:#382746}}button:focus-visible,select:focus-visible,a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}img{{max-width:100%;height:auto;display:block}}.tree{{border:1px solid #40324d;margin:20px 0}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}}.step{{border:1px solid #40324d;padding:18px;background:var(--panel)}}.step button{{margin-top:14px}}.table{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;text-align:left}}td,th{{padding:12px;border-bottom:1px solid #40324d;white-space:nowrap}}th{{font-size:13px;color:var(--muted)}}footer{{margin-top:60px;padding-top:22px;border-top:1px solid #40324d;color:var(--muted)}}.downloads{{display:flex;gap:18px;flex-wrap:wrap}}@media(max-width:700px){{main{{padding:18px}}.grid{{grid-template-columns:1fr}}h2{{margin-top:38px}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto}}}}
</style><main><header><div class="brand">Rx / RxLabs</div><p class="tag">ECHO 4.5 · INVESTIGACIÓN EN DESARROLLO · 01 OCT 2026</p>
<h1>Cuánta memoria ayuda a encontrar una solución</h1><p>Medimos un banco asociativo que orienta la búsqueda de programas. Las 500.000 unidades son pesos de un byte. El núcleo LIF y el modelo de lenguaje no se amplían con este experimento.</p>
<p class="note">250 tareas conocidas de ARC-1 training. Los resultados no son un examen ciego ni una puntuación oficial ARC, y no cierran S6.</p></header>
<h2>Resultados y coste</h2><p>Los controles auditados resolvieron 3/250 sin guía, 5/250 con 640 unidades y 6/250 con 500.000. No perdieron aciertos previos. Las capacidades intermedias se muestran únicamente cuando termina su replay completo.</p>
<div class="table"><table><thead><tr><th>Unidades</th><th>Exactas</th><th>Pérdidas vs base</th><th>CPU</th><th>Estado</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">Máximo 400 expansiones y profundidad 4 por tarea; mismo solver, datos y operaciones. CPU descriptiva: los nuevos tamaños se miden en otro lote. Solo una tarea adicional frente a 640 no demuestra una mejora general.</p>
<div class="grid">{''.join(f'<figure><img loading="lazy" width="1500" height="795" src="{name}.png" alt="{label}"><figcaption>{label} · <a href="{name}.svg">SVG</a></figcaption></figure>' for name,label in [('accuracy','Aciertos exactos'),('cost','Coste de búsqueda'),('memory','Uso de los pesos'),('synthetic','Control sintético, no ARC')])}</div>
<h2>Una operación vista desde sus asociaciones</h2><p>El árbol representa los rasgos de la tarea {REFERENCE}, los índices consultados y sus pesos. Cada rama tiene ocho lecturas. El color indica el peso; el giro y la posición son recursos gráficos. Un índice puede aparecer en varias ramas sin convertirse en varias unidades diferentes.</p>
<div class="controls"><label for="operation">Operación</label><select id="operation">{options}</select><button id="play" type="button">Reproducir GIF</button><a id="download" href="{first}.gif" download>Descargar GIF</a><a id="trace" href="{first}.json">Datos completos</a></div>
<img class="tree" id="tree" width="1120" height="650" src="{first}.png" alt="Reconstrucción de asociaciones de la operación sym_h">
<p class="note">La guía puntúa 84 familias candidatas. Una puntuación no significa que esa operación se ejecutase. Las puntuaciones reconstruidas coinciden con el diario guardado. La animación no reproduce tiempos de inferencia ni muestra un monólogo interno.</p>
<h2>Pasos de programas que sí resolvieron la tarea</h2><p>Los ocho pasos siguientes pertenecen a tres casos ganados frente a la base. Se reconstruyen sobre el primer input de test y el resultado final coincide con la predicción registrada. Son ejemplos elegidos por su interés explicativo, no una muestra representativa. La guía se calcula una vez antes de la búsqueda.</p>
<div class="grid">{steps}</div>
<h2>Qué queda por demostrar</h2><p>Hay que terminar la comparación de capacidades intermedias y después medir otra cohorte. La memoria grande utiliza 3.085 de sus 500.000 pesos tras 60 programas. No sabemos aún qué tamaño ofrece el mejor equilibrio ni si la ventaja se transfiere a ARC-2, ARC-3 o S6.</p>
<div class="downloads"><a href="metrics.csv">Métricas CSV</a><a href="summary.json">Resultados JSON</a><a href="synthetic.json">Control sintético</a><a href="gallery.json">Índice de GIF</a><a href="manifest.json">Manifiesto SHA-256</a><a href="article.md">Artículo Markdown</a></div>
<footer>Developer: RxLabs · Visualizaciones de resultados de desarrollo. Paquete sin fuentes privadas de ECHO.<br>El material conserva la procedencia de ARC-AGI. Los pesos y las coordenadas de una visualización no son equivalentes a neuronas biológicas.</footer></main>
<script>
const select=document.getElementById('operation'), tree=document.getElementById('tree'), play=document.getElementById('play');
select.value={json.dumps(first)};let running=false;
function update(){{tree.src=select.value+(running?'.gif':'.png');tree.alt='Asociaciones de '+select.selectedOptions[0].textContent;play.textContent=running?'Pausar animación':'Reproducir GIF';document.getElementById('download').href=select.value+'.gif';document.getElementById('trace').href=select.value+'.json';}}
select.addEventListener('change',()=>{{running=false;update()}});play.addEventListener('click',()=>{{running=!running;update()}});
document.querySelectorAll('.animate').forEach(button=>button.addEventListener('click',()=>{{const img=button.closest('article').querySelector('img');const active=button.dataset.running==='yes';img.src=button.dataset.file+(active?'.png':'.gif');button.dataset.running=active?'no':'yes';button.textContent=active?'Reproducir GIF':'Pausar animación';}}));
</script></html>'''
    (out / "index.html").write_text(text)


def build(out=OUT):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    profile = study.integrity()
    summary = study.report(profile)
    synthetic = study.read(study.ROOT / "synthetic.json")
    charts(summary, synthetic, out)
    study.save(out / "summary.json", summary); study.save(out / "synthetic.json", synthetic)
    with (out / "metrics.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("arm", "units", "status", "solved", "of", "cpu_seconds", "expansions", "applications", "nonzero_units", "weight_bytes", "measurement_batch"))
        for arm, row in summary["arms"].items():
            writer.writerow([arm]+[row.get(k, "") for k in ("units", "status", "solved", "of", "cpu_seconds", "expansions", "applications", "nonzero_units", "weight_bytes", "measurement_batch")])
    guide, task, cases = evidence(profile)
    renderer_sha = study.file_hash(Path(__file__))
    gallery = {"reference_task": REFERENCE, "operations": [], "steps": [],
               "reconstructed_guide_matches_original": True,
               "program_outputs_match_original": True, "renderer_source_sha256": renderer_sha}
    (out / "operations").mkdir(exist_ok=True); (out / "steps").mkdir(exist_ok=True)
    for name in guide.names:
        trace = trace_operation(guide, task, name)
        trace.update(task=REFERENCE, role="CANDIDATE_SCORE", source="reconstructed from verified historical guide", renderer_source_sha256=renderer_sha)
        path = out / "operations" / name
        if needs_render(path, trace):
            animation(trace, name, f"Operación candidata · tarea {REFERENCE} · demostración pública", task["train"][0]["input"], task["train"][0]["output"], path)
        gallery["operations"].append({"operation": name, "file": "operations/"+name, "score": trace["guide_score"], "role": "CANDIDATE_SCORE"})
    for case in cases:
        for step in case["steps"]:
            name = step["trace"]["operation"]
            path = out / "steps" / f'{case["task"]}-{step["number"]:02}-{name}'
            trace = dict(step["trace"], task=case["task"], role="VERIFIED_PROGRAM_STEP", step=step["number"],
                         item=step["item"], input=step["input"], output=step["output"],
                         source_result_sha256=case["source_result_sha256"], source_journal_sha256=case["source_journal_sha256"], renderer_source_sha256=renderer_sha)
            if needs_render(path, trace):
                animation(trace, name, f'Paso verificado {step["number"]}/{len(case["steps"])} · tarea {case["task"]} · primer input de test', step["input"], step["output"], path)
            gallery["steps"].append({"task": case["task"], "step": step["number"], "operation": name, "file": str(path.relative_to(out)), "role": "VERIFIED_PROGRAM_STEP"})
    study.save(out / "gallery.json", gallery)
    page(summary, gallery, out)
    article = '''# ECHO 4.5 y el tamaño de su memoria de búsqueda

En 250 tareas conocidas de desarrollo ARC-1, el mismo solver resolvió 3 sin
guía, 5 con una guía de 640 pesos y 6 con 500.000. No hubo pérdidas frente
a las configuraciones menores. Estos resultados tienen 750 replays
guardados y comprobados; no son una puntuación oficial ni un cierre de S6.

La ampliación es una memoria asociativa: relaciona rasgos de ejemplos con
operaciones que funcionaron antes. No modifica los pesos del LLM ni amplía
el núcleo LIF. Solo 3.085 pesos de los 500.000 quedaron no cero tras aprender
60 programas. El banco ocupa 500.000 bytes; el solver necesita más memoria.

![Aciertos exactos](accuracy.png)

Frente a 640, la ampliación aporta una tarea: +0,4 puntos porcentuales.
La CPU del ensayo original aumentó un 0,9 % respecto a 640 y un 3,6 %
respecto a la base. El tamaño grande no acelera todas las tareas.

![Coste](cost.png)
![Uso de memoria](memory.png)

La nueva comparación incluye 4.096, 16.384 y 65.536 pesos, reutiliza los
controles auditados y repite cada medición nueva. Los tamaños pendientes
no tienen una puntuación asignada. Sus tiempos se medirán en otro lote y
serán descriptivos, sin presentar diferencias de hardware/carga como mejora.

![Clasificación sintética, separada de ARC](synthetic.png)

Los árboles 3D reconstruyen rasgos, índices y pesos reales y comprueban las
puntuaciones contra los diarios. Su posición y su giro son gráficos, no
tiempos de procesamiento ni un registro eléctrico. Hay un GIF por familia
candidata y otro por cada paso de tres programas que sí resolvieron casos.

![Simetría horizontal y memoria asociativa](operations/sym_h.gif)

[Explorar operaciones y pasos](index.html) · [Datos](summary.json) ·
[CSV](metrics.csv) · [Huellas de los archivos](manifest.json)

Falta evaluar la transferencia a tareas nuevas. Una tarea adicional no
permite afirmar una mejora general ni que 500.000 sea el tamaño óptimo.
'''
    (out / "article.md").write_text(article)
    (out / "PUBLICATION.txt").write_text("Paquete estático para rxlabs.org. Copiar la carpeta completa bajo public/research/capacity-20261001/ y enlazar su index.html. No contiene fuentes de ECHO ni pesos. Los resultados pending no deben anunciarse como terminados. Respetar la licencia Apache-2.0 de ARC-AGI y conservar la atribución.\n")
    licence = REPO / "lab/seed/ARC-AGI/LICENSE"
    if licence.exists(): (out / "ARC-AGI-LICENSE.txt").write_bytes(licence.read_bytes())
    hashes = {str(p.relative_to(out)): study.file_hash(p) for p in sorted(out.rglob("*"))
              if p.is_file() and p.name != "manifest.json"}
    study.save(out / "manifest.json", {"at": study.now(), "study_profile_sha256": study.digest(profile),
                                      "official_arc_score": False, "files": hashes})
    import zipfile
    with zipfile.ZipFile(out.parent / (out.name + "-web.zip"), "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.rglob("*")):
            if path.is_file(): archive.write(path, str(Path(out.name) / path.relative_to(out)))
    print(json.dumps({"output": str(out), "operation_gifs": len(gallery["operations"]),
                      "step_gifs": len(gallery["steps"]), "arc_study_complete": summary["complete"]}), flush=True)
    return gallery


if __name__ == "__main__":
    build()
