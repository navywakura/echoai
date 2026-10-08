# echoAI — instructions for any coding agent

Read `echoai/CLAUDE.md` first. Then `echoai/docs/05-NEXUS-0-SPEC.md`.
Do not invent a second thought-bus. Do not turn on a LLM for NEXUS-0.
There is no AKD1000 in the lab.

## Project separation (2026-09-22)

`echo-discord` is a frozen legacy project, not part of ECHO-4. Do not edit,
launch, import from it, install into it, or use its `.venv`, tools or models
for this project. Archival relocation requires the owner's permission and
a check for active processes/references. Do not recreate the old directory
or add a compatibility symlink. Use system Python for ECHO-4's stdlib tests;
any optional developer tools must have a separate, explicitly managed home.

The official echoAI agent logo is `echo-ai-agent-logo.png`. Preserve its
design and original bytes; see `assets/brand/echoai/README.md` for derivatives.

## Decision visibility (2026-09-27)

For new development runs, keep decisions visible in the mini terminal:
`python3 observe.py --launch --demo` for ARC training, or the commands in
`docs/ECHO45-OBSERVABILITY.md` for ARC development and the existing core
`thought.jsonl`. Record actual observations, hypotheses, actions and results;
never fabricate an inner monologue or feed viewer text back into the agent.
Do not instrument or reopen sealed exams/campaigns: observation adds wall time.
