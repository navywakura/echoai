# echoAI-4 — notices and licence inventory

Copyright © 2026 RxLabs / RxLabs (Rogex Laboratories).

## Two layers

| Layer | Contents | Licence |
|---|---|---|
| Open | `echoai_release/` (CLI, BYOK cortex, identity, reproduction), contracts (`echoai/docs/*.md`), results, receipts (`echoai/receipts`, `echoai/lab`) | PolyForm Noncommercial 1.0.0 |
| Compiled core | `echoai.*.so`, `navi10_*.so` (Nuitka) | RxLabs EULA — **DRAFT, pending legal review** |

Required notice for the open layer: `Required Notice: Copyright © 2026 RxLabs / RxLabs (https://rxlabs.org)`

## Third-party components

| Component | Where | Licence | Shipped? |
|---|---|---|---|
| CPython 3.14 standard library | runtime | PSF License | No (uses the user's interpreter) |
| Nuitka runtime support compiled into the binaries | `*.so` | Apache-2.0 (Nuitka) | Yes (inside binaries) |
| Qwen3-4B-Instruct-2507 (reference cortex) | referenced only | Apache-2.0 (Qwen) | **No** — the user downloads it |
| Phi-3.5-mini-instruct (tested local cortex) | referenced only | MIT (Microsoft) | **No** |
| llama.cpp `llama-server` | user's system | MIT | **No** |
| Any API model (OpenAI, Anthropic, Google, DeepSeek, Moonshot, Alibaba…) | user's key | the provider's terms | **No** — BYOK |

The core imports only the Python standard library. Optional viewers in the lab
(tkinter, VTK, PIL) are not part of this package.

## Legal to-dos before publication (REL-D)

1. **GPLv3 notice of the parent repository (downgraded 2026-09-24).** The RXos tree
   that contains this code carries a GPLv3 `LICENSE`. Checked on 2026-09-24: every
   GitHub remote that holds it (`navywakura/RXos`, `knightslabs/echos`,
   `knightslabs/rxos-9`, `knightslabs/rxos-8.5`) is **private**, so the echoAI code
   was never distributed to third parties under GPLv3. Git history: the only
   non-Nav author is `qwen.ai[bot]` (one commit, `.gitignore` and two docs, no
   echoAI code); pull requests #1–#6 came from branches of `navywakura` (confirm it
   is Nav's own account). As sole author, RxLabs may license echoAI as it
   chooses. Before publishing: add an explicit licence file to `echoai/` so the
   repository-level GPLv3 notice does not appear to cover it, and have a lawyer
   glance at the EULA. **No longer a blocker; a to-do.**
2. The EULA is a draft.
3. Model licences: Qwen and Phi are only referenced; the abliterated Qwen3.5-9B
   variant on the lab disk is a third-party fine-tune whose terms were not
   reviewed and is **not** recommended as a default cortex.
