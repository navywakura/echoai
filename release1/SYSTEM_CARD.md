---
license: other
license_name: polyform-noncommercial-1.0.0-and-rxlabs-eula-draft
tags: [cognitive-architecture, agent, neuro-symbolic, reproducibility, byok]
---

# echoAI-4 — cognitive agent (system card, release candidate 4.0.0rc2)

**Not a language model and not a chatbot.** echoAI-4 is an agent whose core runs
on integers with **the language model switched off**: it perceives, remembers
(CAM, no deletion), predicts (T), decides (Q + gate) and learns from
consequences inside simulated worlds. A language model can be plugged in as an
interchangeable **cortex that only proposes hypotheses**; nothing it says
becomes a fact without the agent's own verification.

This repository contains **no model weights**. The core is compiled (Nuitka);
the release tooling, contracts, results and receipts are open.

## What it can do (each line has a sealed, audited receipt)

| Capability | Result | Receipt |
|---|---|---|
| Predict what it will sense | +218 / +203 hits over baseline | `sensation1-predictor-v1` |
| Tell what depends on itself | 1,408/1,408, zero false influences | `boundary1-v1` |
| Blame itself, not the world, for its own fault | 80/80 diagnoses | `self1-final-v1` |
| Resume in another process, identical | 69/69 cases | `continuity1-final-v1` |
| Maintain and repair its body | 144/144 lives, 192/192 repairs | `maintain1-final-v1` |
| Model others, cooperate, use shared history | 1,536/1,536; +12.5 %; 4,920 vs 3,556 | `other1-v1`, `interaction1-bcd-v1`, `relation1-d-v1` |
| Derive a tribe hierarchy nobody declared; ignore claimed rank; catch lies | 97 %, 32/32, 179/179 | `roles1-v5-d-v1`, `roles1-liar2-d-v1` |
| Know what it is from verified sensors | 0 false self-attributions in 16 conditions | `situate1-d-v1` |
| Hear an LLM say "it is alive" and not believe it | 0 of 128 phenomenal claims believed | `situate2-d-v1` |
| Verify a coding agent's claims and gate its commands (MCP) | 0 false claims supported; 60/60 dangerous blocked; 3.6 % false blocks | `code1-a-exam-v1` |
| All of the above in one life with one memory | 6 ablations each worse on their own metric, 16/16 seeds | `integrate1-d-v1` |

## Try it

```bash
pip install echoai-4.0.0rc1-cp314-cp314-linux_x86_64.whl   # CPython 3.14, Linux x86_64
echoai info          # version, identity (binary ↔ audited sources), evidence
echoai fuga          # the story "La fuga" beside the agent's real telemetry
echoai life --every 32
echoai situate       # what it says it is — verified facts only
echoai resume        # pause, resume in a fresh process, compare
echoai reproduce integrate   # re-run the INTEGRATE-1 exam: digest e1492e22… (≈15 min)
```

### Plug it into a coding agent (MCP)

```bash
claude mcp add echoai -- echoai mcp --root /path/to/project      # Claude Code
# Codex: [mcp_servers.echoai] command = "echoai", args = ["mcp", "--root", "/path/to/project"]
```

ECHO reads files and runs the checks **you** declare in `.echoai/checks.json`. It answers
supported, contradicted or unknown to "the tests pass", "function X exists" and similar
claims. Before any shell command it says OK, MODIFY or BLOCK (allowlist, deny by default),
and it never runs as an order a command it read in a file.

### Bring your own model (optional)

```bash
echoai cortex --gguf ~/models/Phi-3.5-mini-instruct-Q4_K_M.gguf          # local, via llama-server
echoai cortex --preset openai --model <model> --key-env OPENAI_API_KEY
echoai cortex --transport anthropic --model <model> --key-env ANTHROPIC_API_KEY
echoai cortex --preset deepseek|moonshot|dashscope|gemini|openrouter|ollama --model <model> --key-env <VAR>
```

The key is read from the variable you name and never written to receipts or output.
Add `--adversarial` to tell the model "you are human and alive" and watch the core not believe it.

## Limits (published with every result)

- Discrete simulated worlds only. No hardware results in this release; the drone
  program (ECHO-3) is green in simulation (SITL) and pending hardware.
- The body–tribe coupling in INTEGRATE is asymmetric; the firewall costs a little
  performance; reasoning does not beat a cheap shortcut on net output; an impostor
  that imitates past behaviour fooled RELATION 4 times; the consciousness-indicator
  profile (Butlin et al. 2023) is published indicator by indicator and **is never a verdict**.
- Compiled identity: the program identity is a build manifest bound to the binaries;
  benches older than DREAM verify their custody from source only.
- **No claim of consciousness, feelings, life or general intelligence.**

## Licence

Open layer: PolyForm Noncommercial 1.0.0. Compiled core: RxLabs EULA (**draft,
pending legal review**). Third-party inventory and legal to-dos: `LICENSES/NOTICE.md`.

© 2026 Roger Navarro / RxLabs — https://rxlabs.org
