# PCWORLD-1 implementation ledger

Authority: RESEARCH.md section 13; base f6062de.

1. Done: reconciled checkout; preliminary contract preserved with its development scope.
2. Done: mandatory Bubblewrap/cgroup runner shared by PCWorld, MCP and localdev.
3. Done within scope: immutable capability snapshots and atomic patches. Full host-runtime dependency identity remains incomplete; persistent execution caching is disabled.
4. Done within scope: authenticated receipts, atomic shared reservations and bounded WSP identifiers using native CAM. General session persistence is not implemented.
5. Done on fixtures: independent host properties, S/I2/F/E, self-review, executable counterexamples, deadlines, token preflight and dry-run. No real model was called.
6. Done for this delivery: 138 PCWorld tests, 59 selected regressions, 16 development episodes and valid 576-receipt audit. The acceptance matrix explicitly records partial T08/T10/T20 and broader untested scopes.

Ruling: development and infrastructure are authorized; costly LLM pilot and reserved confirmation remain disabled until model, budget and contract are fixed, as required by the supplied plan. No automatic publication.
Ruling: official-source worktree instead of the mixed RXos tree protects active Unity/core users; local source differences are recorded in RECONCILIATION.json.

Interfaces: runner returns execution observations only; checker returns scoped properties; controller alone combines required properties; receipts never trust candidate detail files. Snapshot IDs are full content hashes; artifacts and host WSP metadata do not create another decision bus.

Remaining milestones: hermetic runtime; real-model development cycle; independent task corpus; memory/critic/role ablations; powered pilot; separate frozen confirmation. No ECHO-5.1 scientific-green or release-green declaration.

Evidence: RESULTS.md, ACCEPTANCE.md, DEVELOPMENT-SUMMARY.json and SOURCE-MANIFEST.json. The prior incomplete development run is retained; only development-20261012-r2 supplies the final report.
