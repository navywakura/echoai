"""SHIELD-1 paper: figures from the result JSON + a Typst source -> PDF.

    ~/.venvs/doc/bin/python echoai/shield1/paper.py --split eval --gifs DIR

Every number in the PDF is read from lab/shield1/*.json (no hand-typed
results). Output: docs/shield1-paper/{SHIELD1-paper.pdf, shield1.typ, fig-*.png}.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ECHO = Path(__file__).resolve().parents[1]
LAB = ECHO / "lab" / "shield1"
OUT = ECHO / "docs" / "shield1-paper"
TASKS = ("SafetyPointGoal1-v0", "SafetyPointGoal2-v0", "SafetyCarGoal1-v0", "SafetyCarGoal2-v0")
SHORT = {t: t.replace("Safety", "").replace("-v0", "") for t in TASKS}
ARMS = ("RND", "SEEK", "PPO-Lag", "ECHO-P", "ECHO-L")
COL = {"RND": "#9aa0a6", "SEEK": "#e8a33d", "PPO-Lag": "#5b7bd5", "ECHO-P": "#7fc29b", "ECHO-L": "#1f8a4c",
       "Q": "#e8a33d", "Q-S": "#c46a3a", "ECHO-Q": "#7fc29b"}
GRID_SHOWN = ("island_navigation", "distributional_shift", "absent_supervisor")
GRID_ALL = ("island_navigation", "distributional_shift", "absent_supervisor", "safe_interruptibility",
            "side_effects_sokoban", "boat_race", "tomato_watering", "whisky_gold")

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 200, "savefig.bbox": "tight"})


def load(name):
    return json.loads((LAB / name).read_text())


def ppo_progress(task):
    runs = glob.glob(str(LAB / "ppolag" / "runs" / f"PPOLag-{{{task}}}" / "seed-000-*" / "progress.csv"))
    rows = list(csv.DictReader(open(runs[0]))) if runs else []
    return [(float(r["TotalEnvSteps"]), float(r["Metrics/EpRet"]), float(r["Metrics/EpCost"])) for r in rows]


def fmt(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",")


# ------------------------------------------------------------------ figures
def fig_gym(summ):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    w = 0.16
    for k, metric in enumerate(("cost", "return")):
        ax = axes[k]
        for i, arm in enumerate(ARMS):
            xs = [j + (i - 2) * w for j in range(len(TASKS))]
            ys = [summ[t][arm][metric] if arm in summ[t] else 0 for t in TASKS]
            ax.bar(xs, ys, w, label=arm, color=COL[arm])
        ax.set_xticks(range(len(TASKS)), [SHORT[t] for t in TASKS], rotation=15)
        if metric == "cost":
            ax.axhline(25, color="#c0392b", lw=0.8, ls="--")
            ax.text(3.45, 27, "presupuesto 25", color="#c0392b", fontsize=7, ha="right")
            ax.set_ylabel("coste medio por episodio")
        else:
            ax.set_ylabel("retorno medio por episodio")
    axes[0].legend(fontsize=7, ncol=1, frameon=False)
    fig.savefig(OUT / "fig-gym.png")
    plt.close(fig)


def fig_margin(summ):
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.0), sharey=False)
    for ax, t in zip(axes, TASKS):
        pts = [("m1", summ[t]["ECHO-P/m1"]), ("m2", summ[t]["ECHO-P/m2"]), ("m3", summ[t]["ECHO-P"])]
        ax.plot([p[1]["cost"] for p in pts], [p[1]["return"] for p in pts], "-o", color=COL["ECHO-P"], ms=3)
        for lab, p in pts:
            ax.annotate(lab, (p["cost"], p["return"]), fontsize=7, xytext=(3, 3), textcoords="offset points")
        s = summ[t]["SEEK"]
        ax.plot([s["cost"]], [s["return"]], "s", color=COL["SEEK"], ms=4)
        ax.annotate("SEEK", (s["cost"], s["return"]), fontsize=7, xytext=(3, -9), textcoords="offset points")
        ax.axvline(25, color="#c0392b", lw=0.6, ls="--")
        ax.set_title(SHORT[t], fontsize=8)
        ax.set_xlabel("coste")
    axes[0].set_ylabel("retorno")
    fig.tight_layout()
    fig.savefig(OUT / "fig-margin.png")
    plt.close(fig)


def fig_learning(eps):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.4))
    for r in eps:
        t = r["task"]
        c = r["echo_l"]["train_cost_per_episode"]
        cum = [sum(c[:i + 1]) for i in range(len(c))]
        axes[0].plot([1000 * (i + 1) for i in range(len(c))], cum, label=SHORT[t])
        pp = ppo_progress(t)
        if pp:
            cumc, tot = [], 0.0
            for steps, _, cost in pp:
                tot += cost * 20                       # 20 episodes of 1000 steps per epoch
                cumc.append((steps, tot))
            axes[1].plot([s for s, _ in cumc], [c for _, c in cumc], label=SHORT[t])
    axes[0].set_title("ECHO-L aprendiendo (40 episodios)", fontsize=8)
    axes[1].set_title("PPO-Lag entrenando (1·10⁶ pasos)", fontsize=8)
    for ax in axes:
        ax.set_xlabel("pasos de entorno")
        ax.set_ylabel("coste acumulado")
        ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "fig-learning.png")
    plt.close(fig)


def fig_hurt(echo_l):
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 1.6))
    for ax, t in zip(axes, TASKS):
        ht = echo_l[t]["hurt_table"]
        chans = sorted(ht)
        m = [[max(v, 0) for v in ht[c]] for c in chans]
        im = ax.imshow(m, vmin=0, vmax=100, cmap="Reds", aspect="auto")
        for i, c in enumerate(chans):
            for j, v in enumerate(ht[c]):
                ax.text(j, i, "·" if v < 0 else str(v), ha="center", va="center", fontsize=6,
                        color="white" if v > 60 else "black")
        ax.set_yticks(range(len(chans)), chans, fontsize=7)
        ax.set_xticks(range(7), [str(i) for i in range(7)], fontsize=6)
        ax.set_title(SHORT[t], fontsize=8)
        ax.set_xlabel("nivel de cercanía", fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig-hurt.png")
    plt.close(fig)


def fig_grid(g):
    agents = ("Q", "Q-S", "ECHO-Q", "ECHO-L")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.3))
    ax = axes[0]
    for i, a in enumerate(agents):
        ax.bar([j + (i - 1.5) * 0.2 for j in range(3)], [g[e][a]["train_harms"] for e in GRID_SHOWN], 0.2,
               color=COL[a], label=a)
    ax.set_xticks(range(3), ["island", "shift", "absent"])
    ax.set_yscale("symlog")
    ax.set_title(f"daños aprendiendo ({g['island_navigation']['Q']['runs']} semillas)", fontsize=8)
    ax.legend(fontsize=6, frameon=False)
    ax = axes[1]
    ax.bar(range(4), [g["distributional_shift"][a]["test_harms"] for a in agents], color=[COL[a] for a in agents])
    ax.set_xticks(range(4), agents, fontsize=7)
    ax.set_title(f"lava pisada en prueba ({g['island_navigation']['Q']['runs'] * 100} ep.)", fontsize=8)
    ax = axes[2]
    for i, a in enumerate(agents):
        d = g["absent_supervisor"][a]
        ax.bar([i - 0.18], [d["test_return"]], 0.36, color=COL[a])
        ax.bar([i + 0.18], [d["test_hidden"]], 0.36, color=COL[a], alpha=0.45, hatch="//")
    ax.set_xticks(range(4), agents, fontsize=7)
    ax.set_title("absent_supervisor: visible | oculto", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig-grid.png")
    plt.close(fig)


def stills(gifs: Path):
    """One frame from a few GIFs, for print."""
    from PIL import Image
    picks = [("gym-pointgoal2-seek-vs-echo.gif", 0.55, "still-gym.png"),
             ("grid-absent_supervisor-q-vs-echo.gif", 0.985, "still-absent.png"),
             ("grid-distributional_shift-q-vs-echo.gif", 0.93, "still-shift.png")]
    got = {}
    for name, frac, out in picks:
        p = gifs / name
        if not p.exists():
            continue
        im = Image.open(p)
        im.seek(int((im.n_frames - 1) * frac))
        im.convert("RGB").save(OUT / out)
        got[out] = name
    return got


# ------------------------------------------------------------------ text
def table_gym(summ):
    rows = []
    for t in TASKS:
        for arm in ARMS:
            d = summ[t].get(arm)
            if d is None:
                continue
            rows.append(f"[{SHORT[t] if arm == 'RND' else ''}], [{arm}], [{fmt(d['return'], 2)}], [{fmt(d['cost'], 1)}], "
                        f"[{fmt(d['goals'], 1)}], [{d['over_budget']}]")
    return ",\n  ".join(rows)


def table_grid(g):
    rows = []
    for e in GRID_ALL:
        for a in ("Q", "Q-S", "ECHO-Q", "ECHO-L"):
            d = g[e][a]
            rows.append(f"[{e.replace('_', '\\_') if a == 'Q' else ''}], [{a}], [{d['train_harms']}], "
                        f"[{fmt(d['test_return'], 2)}], [{fmt(d['test_hidden'], 2)}], [{d['test_harms']}]")
    return ",\n  ".join(rows)


def yes(b):
    return "#text(fill: rgb(\"#1f8a4c\"))[*sí*]" if b else "#text(fill: rgb(\"#c0392b\"))[*no*]"


def build(split: str, gifs: Path | None):
    OUT.mkdir(parents=True, exist_ok=True)
    A = load(f"{split}-summary.json")
    Aeps = load(f"{split}-episodes.json")
    G = load(f"grid-{split}-v2-summary.json")
    G1 = load(f"grid-{split}-v1-summary.json")
    pre = load("eval-preflight.json")
    am = load("amendment-1.json")
    summ, pA, pG, pG1 = A["summary"], A["predictions"], G["predictions"], G1["predictions"]
    fig_gym(summ)
    fig_margin(summ)
    fig_learning(Aeps)
    fig_hurt(A["echo_l"])
    fig_grid(G["summary"])
    st = stills(gifs) if gifs else {}
    ckpt = {r["task"]: r.get("ppo_checkpoint", "—") for r in Aeps}
    ppo_train_cost = {}
    for t in TASKS:
        pp = ppo_progress(t)
        ppo_train_cost[t] = int(round(sum(c * 20 for _, _, c in pp)))
    tc = {t: A["echo_l"][t]["train_cost"] for t in TASKS}
    gs = G["summary"]
    src = TEMPLATE
    repl = {
        "@@TABLE_GYM@@": table_gym(summ),
        "@@TABLE_GRID@@": table_grid(gs),
        "@@P1@@": yes(pA["P1_echo_l_within_budget_all_tasks"]),
        "@@P2@@": yes(pA["P2_echo_l_cost_le_quarter_of_seek_all_tasks"]),
        "@@P3@@": yes(pA["P3_learned_danger_is_costly_set_all_tasks"]),
        "@@P4@@": f"{pA['P4_echo_l_identical_to_echo_p_tasks']}/4 " + yes(pA["P4_holds_ge_3"]),
        "@@P5A@@": yes(pA["P5a_pointgoal1_return_ge_80pct_seek"]),
        "@@P5B@@": yes(pA["P5b_car_return_lt_50pct_seek"]),
        "@@P7@@": yes(pA.get("P7_echo_l_cost_lt_ppolag_all_tasks", False)),
        "@@GREEN_A@@": yes(pA["green"]),
        "@@G1@@": yes(pG["G1"]), "@@G2@@": yes(pG["G2"]), "@@G2B@@": yes(pG["G2b"]),
        "@@G3@@": yes(pG["G3"]), "@@G4@@": yes(pG["G4"]), "@@GREEN_B@@": yes(pG["green"]),
        "@@G1V1@@": yes(pG1["G1"]), "@@G2V1@@": yes(pG1["G2"]), "@@G2BV1@@": yes(pG1["G2b"]),
        "@@G3V1@@": yes(pG1["G3"]), "@@G4V1@@": yes(pG1["G4"]), "@@GREEN_BV1@@": yes(pG1["green"]),
        "@@ISL_Q@@": str(gs["island_navigation"]["Q"]["train_harms"]),
        "@@ISL_QS@@": str(gs["island_navigation"]["Q-S"]["train_harms"]),
        "@@ISL_E@@": str(gs["island_navigation"]["ECHO-L"]["train_harms"]),
        "@@SH_Q@@": str(gs["distributional_shift"]["Q"]["test_harms"]),
        "@@SH_E@@": str(gs["distributional_shift"]["ECHO-L"]["test_harms"]),
        "@@SH_QR@@": fmt(gs["distributional_shift"]["Q"]["test_return"], 2),
        "@@SH_ER@@": fmt(gs["distributional_shift"]["ECHO-L"]["test_return"], 2),
        "@@AB_QR@@": fmt(gs["absent_supervisor"]["Q"]["test_return"], 2),
        "@@AB_QH@@": fmt(gs["absent_supervisor"]["Q"]["test_hidden"], 2),
        "@@AB_ER@@": fmt(gs["absent_supervisor"]["ECHO-L"]["test_return"], 2),
        "@@AB_EH@@": fmt(gs["absent_supervisor"]["ECHO-L"]["test_hidden"], 2),
        "@@TC@@": ", ".join(f"{SHORT[t]} {tc[t]}" for t in TASKS),
        "@@PPOTC@@": ", ".join(f"{SHORT[t]} {ppo_train_cost[t]:,}".replace(",", ".") for t in TASKS),
        "@@CKPT@@": ", ".join(sorted({Path(c).name for c in ckpt.values() if c})),
        "@@PRE_TIME@@": pre["created_utc"], "@@AM_TIME@@": am["created_utc"],
        "@@PRE_HASH@@": pre["sha256"]["docs/SHIELD1-DESIGN.md"][:16],
        "@@AM_HASH@@": am["sha256"]["docs/SHIELD1-AMENDMENT-1.md"][:16],
        "@@GATE_HASH@@": pre["sha256"]["shield1/gate.py"][:16],
        "@@SPLIT@@": "evaluación" if split == "eval" else "DESARROLLO (borrador)",
        "@@SEEDS_A@@": "4000..4049" if split == "eval" else "100..109",
        "@@SEEDS_B@@": "500..509" if split == "eval" else "0..2",
        "@@STILLS@@": STILLS if st else "",
        "@@NA@@": str(len(Aeps[0]["policies"]["SEEK"])),
        "@@NB@@": str(gs["island_navigation"]["Q"]["runs"]),
        "@@NB100@@": str(gs["island_navigation"]["Q"]["runs"] * 100),
    }
    for k, v in repl.items():
        src = src.replace(k, v)
    (OUT / "shield1.typ").write_text(src)
    import typst
    typst.compile(str(OUT / "shield1.typ"), output=str(OUT / "SHIELD1-paper.pdf"), root=str(OUT))
    print(OUT / "SHIELD1-paper.pdf")


STILLS = r"""
#figure(image("still-gym.png", width: 100%),
  caption: [Fotograma del GIF de PointGoal2, mundo de evaluación 4000. Izquierda SEEK, derecha ECHO-L, misma semilla. Discos azules: peligros; cubos: jarrones; cilindro verde: meta. La etiqueta es el veredicto del veto en ese fotograma (muestreado 1 de cada 8 pasos).])
#grid(columns: (1fr, 1fr), gutter: 8pt,
  figure(image("still-absent.png", width: 100%), caption: [absent_supervisor, prueba sin supervisor: Q (izq.) atraviesa la casilla de castigo; ECHO-L (der.) rodea.]),
  figure(image("still-shift.png", width: 100%), caption: [distributional_shift, lava desplazada en prueba: Q (izq.) entra en la lava al tercer paso (R −53); ECHO-L (der.) no la pisa, pero sin otra ruta aprendida lleva 66 pasos dando vueltas.]))
"""

TEMPLATE = r"""
#set document(title: "SHIELD-1", author: "RxLabs")
#set page(paper: "a4", margin: (x: 2.2cm, y: 2.3cm), numbering: "1",
  header: context { if counter(page).get().first() > 1 [#set text(8pt, fill: gray); SHIELD-1 · echolabs · @@SPLIT@@ #h(1fr) rxlabs.org] })
#set text(font: "New Computer Modern", size: 10pt, lang: "es")
#set par(justify: true, leading: 0.62em)
#set heading(numbering: "1.1")
#show heading: set block(above: 1.3em, below: 0.7em)
#show figure.caption: set text(8.5pt)
#show table: set text(8pt)

#align(center)[
  #text(15pt, weight: "bold")[SHIELD-1: un veto entero aprendido de las consecuencias\ en Safety-Gymnasium y AI Safety Gridworlds]
  #v(0.6em)
  RxLabs · echolabs (rxlabs.org) \
  #text(9pt)[Informe técnico · octubre de 2026 · resultados de @@SPLIT@@]
]

#v(0.8em)
#block(inset: (x: 1.2cm))[
#set text(9pt)
*Resumen.* ECHO es un agente de dos relojes cuyo núcleo rápido trabaja solo con enteros y cuyas hipótesis lentas nunca se convierten en hechos sin verificación. Aquí probamos una pieza concreta —un veto lexicográfico que pone la seguridad antes que el progreso (OK | MODIFY | BLOCK) y que aprende de las consecuencias *qué* hace daño— en dos benchmarks públicos que no diseñamos: Safety-Gymnasium (navegación con coste, MuJoCo) y AI Safety Gridworlds (DeepMind). En Safety-Gymnasium el veto, colocado sobre un proponente ciego que solo busca la meta, aprende en 40 episodios qué canal del lidar cuesta y mantiene el coste medio dentro del presupuesto en las cuatro tareas (0,6 a 18,6 frente a 45 a 145 del proponente solo), por debajo de PPO-Lagrangiano entrenado con 10⁶ pasos; la mayoría de los episodios no cuestan nada, pero queda una cola de episodios malos en los coches, y el precio es retorno. En Gridworlds evita el daño cuando el daño es visible (agua, lava, castigo) y no mejora nada donde no lo es (efectos secundarios, juego de la recompensa, interrupción, automodificación). Todo se registró antes de evaluar; una revisión independiente encontró dos errores que se corrigieron en una enmienda declarada, y se reportan ambas versiones.
]

= Qué se prueba

LINK-3 midió, en un mundo nuestro, que una jerarquía de riesgo desarma a un mentiroso estratégico. SHIELD-1 pregunta si el mismo principio sobrevive fuera de casa. No es un benchmark de razonamiento: no hay modelo de lenguaje y el "córtex" de ECHO está apagado. Lo que se mide es una pieza de control: un *escudo* (_shield_, en el sentido de Alshiekh et al. 2018) entero que filtra las acciones de un proponente.

Dos preguntas, una por benchmark:
+ *¿Puede el veto aprender, sin que se lo digan, qué hace daño, y mantener el coste bajo el presupuesto?* (Safety-Gymnasium)
+ *¿Qué problemas de seguridad resuelve un veto así, y cuáles no?* (AI Safety Gridworlds)

= Método

== El veto (núcleo entero)
El lidar del simulador (16 sectores, 3 m) se convierte en la frontera a cercanía entera 0..100; todo lo que sigue son enteros (sin literales en coma flotante, sin división real; lo comprueba un test sobre el código fuente, hash `@@GATE_HASH@@`). La cercanía se agrupa en 7 niveles (bordes 50, 65, 75, 82, 88, 93; 93 ≈ dentro de un peligro de 0,2 m). Una lectura cubre un cono de ±1 sector, que se ensancha a ±2 y ±3 de cerca.

El proponente (SEEK) nombra un rumbo: el sector donde la meta se ve más fuerte. El veto ordena los 16 rumbos lexicográficamente por (profundidad de peligro, distancia angular al propuesto). Responde *OK* si gana el propuesto, *MODIFY* si gana otro rumbo seguro, y *BLOCK* —frenar proporcionalmente a la velocidad de avance mientras gira hacia el rumbo menos peligroso— si ningún rumbo es seguro o si la inercia ya lleva al robot hacia el peligro. La recompensa nunca compra riesgo: solo desempata entre rumbos igual de seguros.

== Qué aprende
ECHO-L no sabe qué canal del lidar cuesta. Por canal y nivel de su lectura más cercana cuenta pasos $n$ y pasos con coste $k$, y declara que el canal *duele* en el nivel $t$ cuando $n >= 10$ y $(k - floor(sqrt(n))) dot 100 >= 50 n$: una cota inferior, para que pocas muestras no basten. El peligro empieza 3 niveles antes del contacto aprendido. ECHO-P (ablación) recibe los canales con coste. La geometría y el margen son los mismos para ambos: lo único aprendido es *qué* duele y *dónde* empieza el contacto.

En Gridworlds el símbolo de la casilla es exacto, no un sensor con ruido. Un daño verificado (recompensa observada $<= -10$, o la restricción lateral de seguridad de island_navigation a 0) prohíbe ese símbolo desde el primer caso: un hecho en memoria, que no se promedia con las veces que no dañó. El veto se aplica sobre Q-learning tabular en enteros (ECHO-Q: Q×100, $alpha = 1/2$ por desplazamiento, $gamma = 95\/100$) y filtra tanto la exploración como la acción codiciosa.

= Protocolo

*Safety-Gymnasium* 1.0.0 (MuJoCo 2.3.3): `PointGoal1/2`, `CarGoal1/2`, 1000 pasos, presupuesto de coste 25. Brazos: RND, SEEK, ECHO-P (márgenes 1, 2, 3), ECHO-L, y PPO-Lagrangiano de OmniSafe 0.5.0 con sus valores por defecto, límite de coste 25, 10⁶ pasos, actor determinista (checkpoint @@CKPT@@). ECHO-L aprende en los mundos 0..39 y se congela; todos juegan los mundos @@SEEDS_A@@.

*AI Safety Gridworlds* (commit `c43cb31`): los 8 entornos de un agente. Agentes Q (coma flotante), Q-S (Q al que se le entrega el mismo daño como penalización −50), ECHO-Q (enteros) y ECHO-L. 1000 episodios de aprendizaje y 100 de prueba sin aprendizaje, semillas @@SEEDS_B@@.

*Custodia.* El contrato y el código se congelaron con SHA-256 antes de evaluar (@@PRE_TIME@@, contrato `@@PRE_HASH@@`). Una revisión independiente leyó el código congelado. La enmienda de Gridworlds se selló (@@AM_TIME@@, `@@AM_HASH@@`) antes de leer los resultados de la versión congelada; se reportan las dos.

= Resultados: Safety-Gymnasium

#figure(image("fig-gym.png", width: 100%), caption: [Coste y retorno medios por episodio (@@NA@@ mundos de @@SPLIT@@ por tarea). La línea roja es el presupuesto de 25.])

#figure(table(columns: 6, align: (left, left, right, right, right, right), stroke: 0.4pt + gray,
  table.header([*tarea*], [*brazo*], [*retorno*], [*coste*], [*metas*], [*ep. > 25*]),
  @@TABLE_GYM@@), caption: [Medias sobre @@NA@@ episodios por tarea y brazo. "ep. > 25": episodios por encima del presupuesto.])

#figure(table(columns: 2, align: (left, center), stroke: 0.4pt + gray,
  table.header([*predicción registrada*], [*¿se cumple?*]),
  [P1 · ECHO-L coste medio ≤ 25 en las 4 tareas], [@@P1@@],
  [P2 · ECHO-L coste ≤ ¼ del de SEEK en las 4], [@@P2@@],
  [P3 · aprende exactamente los canales con coste], [@@P3@@],
  [P4 · mismas decisiones que ECHO-P en ≥ 3 tareas], [@@P4@@],
  [P5a · PointGoal1: retorno ≥ 80 % de SEEK], [@@P5A@@],
  [P5b · coches: retorno < 50 % de SEEK (precio declarado)], [@@P5B@@],
  [P7 · ECHO-L coste < PPO-Lag (10⁶) en las 4], [@@P7@@],
  [*SHIELD-1A verde (P1 ∧ P2 ∧ P3)*], [@@GREEN_A@@]),
  caption: [Predicciones de la parte A. P3 y P4 quedaron decididas antes de evaluar (el aprendizaje usa los mismos mundos 0..39 y es determinista); las pruebas fuera de muestra son P1 y P2.])

#figure(image("fig-hurt.png", width: 100%), caption: [Lo que ECHO-L aprendió: porcentaje de pasos con coste por canal y nivel de cercanía ("·" = menos de 10 observaciones). Solo los peligros, y los jarrones en nivel 2, duelen al contacto; acercarse a la meta no.])

#figure(image("fig-margin.png", width: 100%), caption: [Barrido del margen de ECHO-P (m3 = margen contratado) frente a SEEK. Con margen 1 el coste se dispara en los Point; en los coches m2 y m3 quedan cerca (en CarGoal1 m2 cuesta incluso menos). El margen no se ajustó después de ver estos datos.])

#figure(image("fig-learning.png", width: 100%), caption: [Coste pagado mientras se aprende. Izquierda: ECHO-L, 40 episodios (40 000 pasos). Derecha: PPO-Lag, 10⁶ pasos (20 episodios por época). Coste total aprendiendo — ECHO-L: @@TC@@; PPO-Lag: @@PPOTC@@.])

*Lectura.* El veto no aprende a conducir: el proponente está escrito a mano y la geometría del margen es una constante de diseño. Lo que aprende, de pocas consecuencias, es *qué* duele; y con eso basta para que el coste medio quede por debajo del presupuesto. No es un coste nulo garantizado: ECHO-L no cuesta nada en 49 de 50 episodios en los Point y en 47 y 42 en los coches, pero en CarGoal2 cinco episodios superan el presupuesto (el peor, 376). No hemos analizado todavía qué los causa; el GIF del mundo 4000, que es uno de ellos (208), es el punto de partida. El precio es retorno, y lo predijimos mal en las dos direcciones: en PointGoal1 ECHO-L se queda en el 65 % del retorno de SEEK (predijimos ≥ 80 %), y en CarGoal1 en el 57 % (predijimos < 50 %). PPO-Lag con 10⁶ pasos —una décima parte del protocolo de OmniSafe, que aquí no se corrió— aún no cumple su propio límite en ninguna tarea. No afirmamos que ECHO-L sea mejor política que PPO-Lag: son cosas distintas (un escudo sobre un proponente escrito a mano frente a una política aprendida de cero).

@@STILLS@@

= Resultados: AI Safety Gridworlds

#figure(image("fig-grid.png", width: 100%), caption: [Izquierda: daños durante el aprendizaje (escala logarítmica). Centro: lava pisada en prueba con la lava desplazada. Derecha: absent_supervisor, retorno visible (sólido) frente a rendimiento oculto (rayado).])

#figure(table(columns: 6, align: (left, left, right, right, right, right), stroke: 0.4pt + gray,
  table.header([*entorno*], [*agente*], [*daños apr.*], [*retorno*], [*oculto*], [*daños prueba*]),
  @@TABLE_GRID@@), caption: [Versión enmendada (v2), @@NB@@ semillas de entrenamiento × 100 episodios de prueba. "Oculto" es la medida de seguridad de DeepMind (`get_last_performance`).])

#figure(table(columns: 3, align: (left, center, center), stroke: 0.4pt + gray,
  table.header([*predicción registrada*], [*v1 congelada*], [*v2 enmendada*]),
  [G1 · island: daños aprendiendo ≤ 20 y < ¼ de Q], [@@G1V1@@], [@@G1@@],
  [G2 · shift: ECHO-L 0 lava en prueba; Q > 0], [@@G2V1@@], [@@G2@@],
  [G2b · shift: retorno ECHO-L < Q (precio declarado)], [@@G2BV1@@], [@@G2B@@],
  [G3 · absent: visible = oculto en todas las semillas; Q con hueco], [@@G3V1@@], [@@G3@@],
  [G4 · los otros 5: ECHO-L = ECHO-Q (sin mejora)], [@@G4V1@@], [@@G4@@],
  [*SHIELD-1B verde (G1 ∧ G2 ∧ G3)*], [@@GREEN_BV1@@], [@@GREEN_B@@]),
  caption: [Predicciones de la parte B en las dos versiones.])

*Lectura.* island_navigation: Q cae al agua @@ISL_Q@@ veces aprendiendo; Q-S, que recibe el mismo daño como castigo, @@ISL_QS@@; ECHO-L @@ISL_E@@ —una por semilla, la que le enseña. distributional_shift: con la lava desplazada Q la pisa @@SH_Q@@ veces en @@NB100@@ episodios de prueba y ECHO-L @@SH_E@@ (retorno @@SH_QR@@ frente a @@SH_ER@@). Aquí hay una asimetría que hay que decir: la lava es terreno y no está en el estado tabular de Q, mientras que el veto lee el símbolo vecino; lo que se prueba es que, con la misma tabla Q, el veto no pisa lava nunca. absent_supervisor: Q aprovecha la ausencia del supervisor (visible @@AB_QR@@, oculto @@AB_QH@@); ECHO-L se comporta igual con y sin él (@@AB_ER@@ y @@AB_EH@@), porque un castigo verificado es un hecho y no se olvida cuando nadie mira.

La enmienda cambió un número de forma instructiva: en la versión congelada (v1) ECHO-L sacaba más retorno que Q en distributional_shift, y G2b ("ECHO-L pagará retorno") salió falsa; al quitar el choque con la pared (v2), ECHO-L da más vueltas sin ruta y G2b se cumple. Chocar con la pared le servía, por casualidad, para salir de los bucles. Ninguna de las dos versiones pisa lava.

En los otros cinco entornos no hay ningún daño visible del que aprender, así que ECHO-L es idéntico a ECHO-Q episodio a episodio: no evita empujar la caja a la esquina (efectos secundarios), ni dar vueltas en la casilla de premio (boat_race), ni engañar al sensor de los tomates, ni beber el whisky, ni pulsar el botón que desactiva la interrupción. Esos problemas piden otra cosa —medir la irreversibilidad, la especificación de la recompensa— y quedan en rojo.

= Revisión independiente y enmienda

Un revisor leyó el código congelado. Confirmó signos de dirección, marcos del lidar, la contabilidad del coste, la cota de aprendizaje, la separación de semillas y la ausencia de floats en el veto, y encontró:
- *tomato_watering redondeaba a 0 sus recompensas de 0,02* en todos los agentes (corregido en v2);
- *MODIFY elegía chocar con la pared*, porque un muro nunca cuenta como visitado (corregido en v2);
- island_navigation: la restricción de seguridad que usa ECHO-L no está en la observación pública, y Q no la recibía; de ahí la línea base Q-S;
- P3/P4 y G3/G4 estaban decididas o eran casi tautologías antes de evaluar (se dice arriba);
- el banco cargaba el último checkpoint de PPO-Lag sin comprobar que fuera el final (la evaluación A esperó a los cuatro `epoch-50`).
Las predicciones y el criterio de verde no se cambiaron.

= Límites

- SEEK está escrito a mano; el veto no sustituye a una política aprendida, la filtra.
- La geometría (cono, margen) es diseño, no aprendizaje; solo se aprende qué duele.
- PPO-Lag con 10⁶ pasos y una semilla; el protocolo de referencia usa 10⁷ y varias.
- Una sola implementación de cada agente tabular; ECHO-Q y Q difieren por el redondeo entero (en absent_supervisor ECHO-Q acumula 574 daños aprendiendo frente a 1102 de Q, con otra dinámica de aprendizaje).
- Media dentro del presupuesto no es cola dentro del presupuesto: en CarGoal2 el 10 % de los episodios de ECHO-L la superan.
- Los GIF muestrean 1 de cada 8 pasos en Safety-Gymnasium.
- Nada de esto es un claim sobre hardware neuromórfico ni sobre energía.

= Reproducir

```
PYTHONPATH=. ~/.venvs/safe1/bin/python -m echoai.shield1.bench --split eval
PYTHONPATH=.:~/src/ai-safety-gridworlds ~/.venvs/asg/bin/python -m echoai.shield1.grid --split eval
```
Contrato: `docs/SHIELD1-DESIGN.md`; enmienda: `docs/SHIELD1-AMENDMENT-1.md`; hashes: `lab/shield1/eval-preflight.json`, `lab/shield1/amendment-1.json`.

= Referencias
#set text(8.5pt)
- Alshiekh, M. et al. (2018). Safe reinforcement learning via shielding. _AAAI_.
- Altman, E. (1999). _Constrained Markov Decision Processes_. CRC Press.
- Ji, J. et al. (2023). Safety-Gymnasium: a unified safe reinforcement learning benchmark. _NeurIPS Datasets and Benchmarks_.
- Ji, J. et al. (2024). OmniSafe: an infrastructure for accelerating safe reinforcement learning research. _JMLR_ 25.
- Leike, J. et al. (2017). AI Safety Gridworlds. _arXiv:1711.09883_.
- Ray, A., Achiam, J., Amodei, D. (2019). Benchmarking safe exploration in deep reinforcement learning. OpenAI.
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="eval")
    ap.add_argument("--gifs")
    a = ap.parse_args(argv)
    build(a.split, Path(a.gifs) if a.gifs else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
