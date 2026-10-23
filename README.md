<p align="center"><img src="https://github.com/navywakura/echoai/raw/v5.8.2/assets/brand/banner-echo58.jpg" alt="ECHO 5.8" width="100%" /></p>
<h1 align="center"><strong>ECHO 5.8</strong></h1>
<p align="center"><strong>Official release · 5.8.3</strong><br />Learn from consequences. Carry memory forward.</p>
<p align="center"><a href="https://rxlabs.org/echoai">Website</a> · <a href="https://huggingface.co/RxLabs/echoai-5.8">Download</a> · <a href="https://github.com/navywakura/echoai">GitHub</a></p>

ECHO is a cognitive agent for local simulations and agent tooling. It observes
what happens, learns the consequences of actions and reuses that memory to guide
future decisions. Run it on CPU, explore its terminal and carry memory between
sessions in **WSP files**.

## What you can build

- **Agents with persistent memory:** record consequences, recall learned roles
  and save or reload the same memory.
- **Interactive simulations:** follow an agent's observations, map and actions
  in the browser panel.
- **Connected tools:** use the terminal with local backends and an optional
  language-model adviser.

One `echoai` installation brings the core, memory tools and terminal together.
The source includes the simulation and repository integrations.

## Getting started

Python **3.12+**, Git and a Linux, macOS or WSL shell:

```bash
git clone https://github.com/navywakura/echoai.git
cd echoai
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
echoai info
echoai demo --memory echo-memory.wsp
echoai memory verify echo-memory.wsp
echoai tui
```

The installer creates a dedicated environment. The small synthetic demo learns
three observations, predicts the same consequence for a new object with the
same role and reloads the saved memory. Expect `new_object_prediction: "HURT"`
and `valid: true`. Choose a new filename when repeating the demo.

In the terminal, `/help` lists commands and `/demo` opens a sample session.
Download the ready-to-install source package from **[Hugging Face](https://huggingface.co/RxLabs/echoai-5.8)**.

[Usage](docs/USAGE.md) · [Memory](docs/memory.md) ·
[Simulation](simulation/README.md) · [Terminal](harness/echo-nexus/README.md)

## Demonstrated in ECHO 5.8

Selected completed evaluations in simulated environments:

| Capability | Measured result | Evaluation context |
|---|---|---|
| Transfer learned roles | Harm **150.0 → 24.2** | MEMORIA-X, held-out family aggregate A1; learned memory versus empty memory |
| Accumulate improvements | Failed episodes **94.3 → 13.8**, harm **58.6 → 0** | ACUMULA-3, mean over 10 runs of a 120-episode probe; five rounds selecting and chaining supplied policy pieces |
| Cooperate through shared memory | **160/160 worlds solved**, versus **119/160** for isolated agents | ENJAMBRE-1, four agents across 20 teams; includes plate tasks designed for cooperation |

These measurements describe the named tasks. The 5.8.3 update brings these
components into an official distribution with common setup and memory commands.

## Built over time

ECHO 4/4.5 established the core and terminal; 5.0/5.1 added simulation,
composition and repository tools; 5.5 developed interactive-world tooling;
5.8 brings role memory, chained improvements and cooperation. The WSP persistence
work from 5.8.2 is included in this release.

<p align="center"><strong>RxLabs / Nav</strong><br /><a href="https://rxlabs.org">rxlabs.org</a> · <a href="https://github.com/navywakura/echoai">Source code</a></p>

GPL-3.0-or-later for the main source; component licenses are included.
