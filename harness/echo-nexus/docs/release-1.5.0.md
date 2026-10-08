# echo-nexus 1.5.0 · beta development harness

Fix retired OpenRouter model IDs and make development sessions easier to use.

- HTTPS OpenRouter shortcut, live public model discovery, saved credential
  references and actionable provider errors. No automatic paid fallback.
- Multiline editor, native paste, F3 copy and `/copy last|why|session`.
  Pasted documents cannot execute embedded commands.
- `/world` runs an operator-provided development world alongside chat.
  Explicit stop and application exit close the owned process group.
- `/echo` reports recorded ECHO decisions without a language model; `/ask`
  sends those records to the optional adviser, with clear provenance.
- Website and guide explain beta status and invite volunteer contributors.
  Open Graph artwork stays in metadata; page captures show the actual terminal.

Tests cover provider errors, catalog filtering, paste safety, clipboard output
and concurrent world/chat lifecycle. Integration verified real free HTTPS replies
and an actor completing two custom-world episodes with one instance.
These are development checks, not ARC results or S6 approval.

Only the harness is public. ECHO source, private adapters, weights, credentials
and reserved experiments are excluded. ECHO-4.5 research remains separate.
