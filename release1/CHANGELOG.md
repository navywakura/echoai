# Changelog — echoAI-4 release

## 4.0.0rc2 — 2026-09-24 (release candidate)

- New: `echoai mcp`, the MCP server "echoai-verify" for coding agents (Claude Code, Codex,
  any MCP client). Tools: observe_file, run_check, verify_claim, check_action, note, recall,
  receipts. E4-CODE-1 A green (receipt 68964ed2; exam not blind, declared).
- Command gate: an allowlist that denies by default. Inline code and SQL always need the operator.
- Everything in 4.0.0rc1 unchanged (the INTEGRATE-1 exam must still reproduce e1492e22…).

## 4.0.0rc1 — 2026-09-24 (release candidate, published gated on Hugging Face)

- First packaged release of the ECHO-4 agent: compiled core (Nuitka) with the
  ECHO-1 (NEXUS-0), ECHO-2 and ECHO-3 code it builds on, plus the open
  `echoai_release` layer.
- CLI `echoai`: `info`, `life`, `fuga`, `situate`, `resume`, `cortex`, `reproduce`.
- BYOK cortex: OpenAI-compatible APIs, Anthropic Messages, local GGUF via llama-server.
- Release identity: build manifest binding the 163 audited sources pinned by the
  INTEGRATE-1 receipt (and every other packaged source) to the compiled binaries.
- Evidence: receipts of the 14 ECHO-4 milestone audits; the INTEGRATE-1 exam
  is reproducible from the wheel (`echoai reproduce integrate`).
- Not included: Hugging Face publication (REL-D), model weights, the lab tree,
  GUI/Metaverse viewers, hardware adapters.
