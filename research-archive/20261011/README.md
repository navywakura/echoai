# ECHO-5 evidence snapshot · 11 October 2026

**Research remains open. ECHO-5 has not passed its complete release criteria.**
This archive preserves selected receipts from the laboratory. It is not a full
dataset export or a new evaluation of the portable source distribution.

The separate [publication checks](../../docs/PUBLICATION-VALIDATION-20261011.md)
cover fresh bounded tests of that adapted source. Their [own manifest](publication-checks/MANIFEST.json)
distinguishes those logs from the historical scientific receipts below.

- [Cognitive confirmation result](closure-confirmation-20261011-r1/result.json)
  and [independent audit](closure-confirmation-20261011-r1/audit.json): audit
  valid, release ineligible pending the other mandatory gates.
- Independent domain audits for [transfer](closure-confirmation-20261011-r1/transfer/audit.json),
  [curriculum](closure-confirmation-20261011-r1/curriculum/audit.json),
  [MiniGrid/BabyAI](closure-confirmation-20261011-r1/sandbox/audit.json) and
  [discrete missions](closure-confirmation-20261011-r1/mission/audit.json).
- [Gazebo/PX4 confirmation audit](sitl-confirmation-20261011-r1/audit.json):
  negative result, including the invalid episode. It is retained as measured.
- [Correction regression checks](closure-checks-20261011-r4/result.json):
  software checks, not evidence of successful flights.
- [Calibration status snapshot](velocity-calibration-20261011-r1/status.json)
  and [coordinator snapshot](velocity-calibration-20261011-r1/coordinator-status.json):
  dated observations of an unfinished run, not a live status endpoint.

[MANIFEST.json](MANIFEST.json) records each original SHA-256 and its public-file
SHA-256. Absolute laboratory paths have been replaced with `<LAB_ECHO5>`,
`<LAB_ECHOAI>` or `<LAB_HOME>`, and JSON is reformatted. Embedded hashes still
identify the original experiment files. A public copy is therefore not claimed
to be byte-identical to its original.

The original per-domain results, replay stores, simulation images and complete
run environments remain local. The receipt files identify those omitted
artifacts by their original hashes; full independent reproduction requires
running the published code with a newly frozen source/configuration receipt.
The source was adapted to the public repository layout after the laboratory
runs, so source hashes cannot be equated across those distributions.

Read [the checkpoint](../../docs/PROJECT-CHECKPOINT-20261011.md) for measured
capabilities, controls and remaining work. S6 is still open and deferred until
after ECHO-5.5.
