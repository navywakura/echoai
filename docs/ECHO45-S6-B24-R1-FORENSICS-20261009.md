**B24 version 1 transport forensics — 9 October 2026**

B24 stopped on an empty selection because the pinned native CLI treated a
**prompt token at a batch boundary as end of generation**. The Python JSON
rejection is correct. There is no hidden JSON to recover by removing decoration.
Version 1 started **zero scientific games, zero scientific model calls and six
neutral format calls**. Five format cases passed; the sixth stopped before
proposal sampling. It remains a charged native invocation. This is an instrument
failure, not a scientific negative or an S6 result.

The investigation is offline. No model, tokenizer, game or cloud operation was
launched. Original sources and receipts were read, not amended. The new artifact
directory is [s6b24-r1-investigation-20261009](../lab/seed/s6b24-r1-investigation-20261009/).
This report describes a recovery proposal; it does not record an executed
recovery or authorize bypassing the format gate.

**Evidence and custody.** The small collected archive was extracted into that
directory, preserving all 52 file payloads. [extraction.json](../lab/seed/s6b24-r1-investigation-20261009/extraction.json)
records every extracted file's hash. Its source archive SHA256 is
`82a8021e5ba109724436da9992d0eb6f3079c18f8a806d52606ff662bad44b35`.
The frozen profile, computed with the project's canonical serializer, is
`de1c1dc9c7206ebde60a3a9de2756d3ae6c8ac1eb6d4fe7904a333553c43b488`.

All 100 source hashes match the collected manifest, local workspace and submitted
ZIP. The ZIP SHA256 remains
`a2cab9b6a6d5d1dd3fd9b0bcdf294c190f051ef733e695c2af77f4be91a74b2b`.
All four frozen input hashes and the cloud test-log hash match. All six call
receipts pass the original `model.load()`: request/profile/seed linkage, rendered
prompt, file hashes, token accounting and parsed proposal. Each stored command,
including its grammar, equals the frozen command builder at the recorded remote
path. See [receipt-verification.json](../lab/seed/s6b24-r1-investigation-20261009/receipt-verification.json).

The collection's four output-file hashes also match. Without extracting or
executing the native binaries, their archived CLI and tokenizer hashes were
checked against the model registry; both match. See
[collection-verification.json](../lab/seed/s6b24-r1-investigation-20261009/collection-verification.json).
Weights were neither opened nor downloaded by this investigation.

**The failing bytes and request.** The failure is `FORMAT-ID/001`, the second
ID case, seed `824901`. Its request SHA256 is
`49906d91420f8b1f1a000cfe09b3617e3bbad2dfe1f31ae008777ccdefe6e915`.
The prompt asks for exactly `{"candidate_id":"C000"}`. Its hash-bound menu maps
`C000` to HOLD 8 with `body_known == 1` and `click_only == 0`; `C001` is the
next synthetic case. It contains no game evidence. The recorded grammar is:

```text
root ::= ws "{" ws "\"candidate_id\"" ws ":" ws choice ws "}" ws
choice ::= "\"C000\"" | "\"C001\""
ws ::= [ \t\n\r]{0,4}
```

[stdout.txt](../lab/seed/s6b24-r1-investigation-20261009/b24-results/format-preflight/calls/FORMAT-ID/001/stdout.txt)
contains exactly 17 bytes:

```python
b' [end of text]\n\n\n'
```

Its SHA256 is `ef9ea7f6620ab14103f8da54b436115262606a0d462faea70dd1661d3d554df8`.
`seed/s6b24_model.py:56–68` already strips the recognized suffix. Offline replay
therefore calls `json.loads('')`, reproducing `JSONDecodeError`, position 0,
with `Expecting value: line 1 column 1 (char 0)`. Reconstruction is never reached.
All five earlier stdout files have the same end marker **after valid JSON** and
parse successfully. Accepting the failed bytes as `C000` would invent a choice.
The receipt's `transport_ok=true` means the subprocess exited successfully;
it does not mean the proposal was valid. `returncode=0`, `proposal=null` and the
recorded error are mutually consistent with the adapter's implementation.

**Native cause.** These are source/control-flow findings tied to the recorded
tokens, not a new inference run:

1. The command uses logical batch `-b 128`, physical microbatch `-ub 64`, explicit
   ChatML, `--no-conversation` and `--no-display-prompt`. The failed prompt has
   132 recorded tokens. Token **127, zero based**, is `151645`, `<|im_end|>`;
   stderr identifies it as EOG. Four tokens remain: `[198,151644,77091,198]`,
   the newline and assistant prefix.
2. The pinned CLI queues up to 128 prompt tokens and accepts them with grammar
   disabled. Before decoding that queued chunk, its unconditional noninteractive
   EOG check inspects the chunk's last token, prints the end marker and exits.
   It does not distinguish input from sampled output at that check. See the
   [pinned prompt-ingestion code](https://github.com/ggml-org/llama.cpp/blob/79e0b68c178656bb0632cb8602d2940b755077f8/tools/main/main.cpp#L625-L661)
   and [termination code](https://github.com/ggml-org/llama.cpp/blob/79e0b68c178656bb0632cb8602d2940b755077f8/tools/main/main.cpp#L864-L881).
3. This path never reaches proposal sampling or its grammar constraint. Stderr
   records 128 sampler accepts and zero-millisecond prompt/evaluation timings;
   initialization/warmup still occurred. Earlier successful prompts have no EOG
   at a 128-token chunk endpoint. Their actual evaluation timings are nonzero.

The notebook pins commit `79e0b68c178656bb0632cb8602d2940b755077f8`; the live build
trace names that source tree and `tools/main/main.cpp`. A read-only upstream
source copy and license are retained with
[URL and SHA256 provenance](../lab/seed/s6b24-r1-investigation-20261009/upstream-provenance.json).
No claim of a newly executed native reproduction is made.

**Exact accounting.** Slots below are zero based, as in the call directories.
The last column counts tokenization of the complete stdout file, including its
CLI decoration; it is not a count of sampled answer tokens.

| Format call | Seed | Result | Input tokens | Retokenized stdout tokens |
| --- | ---: | --- | ---: | ---: |
| FORMAT-REF/000 | 824900 | PASS | 263 | 33 |
| FORMAT-REF/001 | 824901 | PASS | 252 | 33 |
| FORMAT-REF/002 | 824902 | PASS | 259 | 71 |
| FORMAT-REF/003 | 824903 | PASS | 285 | 52 |
| FORMAT-ID/000 | 824900 | PASS | 117 | 18 |
| FORMAT-ID/001 | 824901 | INSTRUMENT_BLOCKED | 132 | 5 |
| **Total started/charged** | | **6 calls** | **1,308** | **212** |

`FORMAT-ID/002` and `/003` were not started. There is no format-pass receipt.
The live log records six starts and five passes, ending at
`2026-10-08T23:00:27.541121+00:00` (9 October, 01:00:27 Madrid). See the
[12 status events with original line numbers](../lab/seed/s6b24-r1-investigation-20261009/live-status-events.json).
The format ledger names exactly these six calls, and every receipt charges one.
Its `spend_eur=0` does not assert zero GPU resource usage.

There is no science budget, science model ledger, execution directory, micro
result, finalist or permit in the exported results. This absence agrees with
the control flow: `seed/s6b24.py:348` runs preflight before `micro()` at line 349,
and game reservations independently require a valid preflight receipt. Thus
new B24 baseline/calibration, candidate, replay, audit, broad-development and
retention games all started **0**; each science arm started **0** model calls.
The inherited baseline input is not a B24 execution. No sealed exam opened.

**Minimal declared recovery, proposed only.** A parser change cannot repair this
call. A bounded command workaround is to set logical `-b` to the already frozen
maximum input length, **8192**, for all R1 calls, retaining `-ub 64`. With the
existing input cap and assistant-terminated ChatML, this avoids intermediate
prompt chunks at the faulty check. All six recorded prompts fit and end on the
non-EOG token `198`. This is a static workaround argument; memory use, timing,
generation validity and numerical behavior on the two T4s are untested.

Before any recovery invocation, write a new, explicit recovery declaration
binding the v1 archive/profile, failed call, six charged calls, cause and amended
command profile. Preserve the original 100 sources and receipts. Use separately
named, hash-frozen R1 transport/entrypoint and verification artifacts; the
declaration must list their actual hashes and the parent-to-R1 profile relation.
Preserve weights, native binaries, tokenizer, prompts, grammars, case order,
seeds, scientific limits and acceptance rules. The original failed receipt must
remain failed; neither its proposal nor its profile may be rewritten.

Run the **complete eight-case neutral preflight** in a fresh R1 namespace under
that declared command, stopping on its first failure. Earlier passes belong to
the old command profile. If all eight pass, accounting is **6 v1 + 8 R1 = 14
format calls**, with the scientific 72-call ceiling unchanged. Any other retry
requires another declaration. The later closure must report accumulated format
costs rather than silently retain the original hard-coded eight. The present
task neither creates an executable R1 profile nor runs that preflight.

**Concrete resume risks.** An unchanged resume replays the five successes, then
`model.propose()` rejects the saved failure with
`prior failed model call; explicit recovery required` before any subprocess.
This was verified offline against the captured directory. Deleting only
`result.json` cannot evade the separate interrupted-call ledger check; removing
both would erase charged history. The manager also returns at
`INSTRUMENT_BLOCKED`; automatic continuation requires `CHECKPOINT_READY`
(`manage.py:105–116`).

Changing frozen files fails source integrity; changing the manifest changes the
profile SHA embedded in every call; changing only a command fails command
verification. The current verifier requires exactly the original eight cases,
and closure reports `format_calls=8` (`seed/s6b24_preflight.py:53–67`,
`seed/s6b24.py:365–368`). A recovery declaration alone cannot override those
checks: the separately reviewed R1 implementation must account for them.

The original runtime is Python 3.12.13, numpy 2.3.2 and arcengine 0.9.3, with
remote root `/kaggle/working/b24-results` and exact native/registry bytes. Moving
the forensic extraction or using the system test interpreter is not a valid
science resume. Rebuilding different binaries or altering prompt formatting to
shift this one boundary would change additional frozen conditions. Increasing
the batch to another small arbitrary number leaves the same failure possible
at other prompt lengths. Apply any declared transport change consistently to
all model-using arms and measure its actual resource effects.

Finally, the existing `follow()` immediately enters science after a format pass.
A recovery format-only validation needs its own bounded entrypoint. The
independent ARC batch evaluator is outside this recovery and outside its frozen
source set.

**Local verification.** [test_s6b24_r1_transport.py](../tests/test_s6b24_r1_transport.py)
adds five receipt-backed tests: empty-content rejection, successful suffix
handling, exact frozen custody/commands, the observed prompt/EOG boundary and
resume refusal without subprocesses. They passed with no skips using system
Python 3.14.6:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest tests.test_s6b24_r1_transport -v
```

The tests skip explicitly if the private extracted receipts are absent. They
verify the captured failure and existing fail-closed behavior, not a deployed
fix or an eight-case recovery pass. The original collected cloud log separately
records 63 passing tests; that log was checked, not rerun. Source and original
receipt hashes are recorded in
[original-hashes.json](../lab/seed/s6b24-r1-investigation-20261009/original-hashes.json)
and rechecked in
[final-verification.json](../lab/seed/s6b24-r1-investigation-20261009/final-verification.json).
