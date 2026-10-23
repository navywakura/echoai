**B24 R1 recovery package — 9 October 2026**

The separate R1 ZIP is ready for main's review. It forks the exact v1 frozen
ZIP with **three copied source overrides**, leaving the original 100 workspace
sources unchanged. Local isolated validation passed **69 tests**; the two
inherited native-validator checks were explicitly skipped. No cloud operation,
native executable, model, tokenizer or game was run for this packaging task.

Package directory:
[lab/kaggle/s6b24-r1-20261009](../lab/kaggle/s6b24-r1-20261009/).
The first R1 execution must run eight fresh neutral format probes before any
science. The local test result is not an R1 preflight-pass receipt.

**Ready artifacts.**

| Artifact | Path relative to the package directory |
| --- | --- |
| Dataset upload directory | `dataset/` |
| Runtime ZIP | `dataset/echo-b24-r1-private.zip` |
| Exact parent native archive | `dataset/b24-native.bin` |
| New notebook and metadata | `notebook/run.py`, `notebook/kernel-metadata.json` |
| Copied runtime source overrides | `source-override/` |
| Exact source diff | `source-overrides.diff` |
| Exact notebook diff | `notebook.diff` |
| Recovery declaration, also inside ZIP | `recovery.json` → `b24-input/recovery.json` |
| Recomputed intent and package identity | `intent.json`, `package.json` |
| Source hashes and parent provenance | `source-diff.json`, `provenance/` |
| Actual isolated test results | `local-validation.json`, `checks/r1-package.log`, `checks/inherited-b24.log` |
| Final artifact/custody checks | `handoff.json` |

Runtime ZIP SHA256:
`d68e890ce70b4400a6a8e046ef48f536a5fdeac9b5e8674625f8d6bfb1fb611d`.

Recovery input SHA256:
`414f1b336a806c3bcca56132036de72fa3859f1363c48a63f51f882a70e124e5`.

Configuration SHA256:
`0116b528988a0d4ef2faf824b842be2662bd2bb617df625ef12c7c3489cb0cda`.

The new runtime manifest/profile will be created by the inherited fresh
`seed.s6b24_cloud prepare` entrypoint on the pinned runtime. These local hashes
are not presented as an already-created cloud runtime profile.

**Exact runtime delta.** All overrides are stored in `source-override` and
archived under their normal runtime paths, without runtime monkeypatching:

| Runtime source | Change |
| --- | --- |
| `seed/s6b24_model.py` | Set only command `-b` to `MAX_INPUT` (8192); retain `-ub 64`. Add deterministic config keys `logical_batch_size=8192`, `microbatch_size=64`, `transport_revision="B24-R1"`. |
| `seed/s6b24.py` | Read the hash-bound recovery input and verified current format receipt at closure; report inherited format costs, current-profile costs, cumulative costs, and recovery file hash. |
| `docs/ECHO45-S6-B24-DESIGN.md` | Append a declared R1 amendment, including fresh preflight, source fork, batching and cumulative accounting. Preserve the original contract text. |

The other **97 sources are identical** to v1. The ZIP's only other changed
member is `b24-input/intent.json`; its only added member is
`b24-input/recovery.json`. All original baseline/exposure/parent-closure inputs
and dependency requirements retain their bytes. Actor, partitions, 8,310-game
budget, 72 scientific-call ceiling, prompts, grammar, seeds, all eight format
cases, strict parser, scientific acceptance and exam protections are unchanged.
The independent ARC evaluator and its criteria are outside these overrides.

For `S` scientific calls, the runtime closure now reports:

| Field | Value |
| --- | ---: |
| `model_calls` | `S` (science; unchanged meaning) |
| `prior_format_calls` | 6 |
| `current_profile_format_calls` | 8 |
| `format_calls` | 14 (cumulative) |
| `current_profile_total_model_calls` | `S + 8`, at most 80 |
| `total_model_calls` | `S + 14`, at most 86 |
| `recovery_sha256` | SHA256 of the exact runtime recovery input |

Main's manager/live display should use the explicit current-profile fields when
it wants current-run counts. `format_calls` and `total_model_calls` include the
six historical calls. The inherited arithmetic audit continues to count the
current scientific ledger and verify eight current-profile format receipts.

**Recovery evidence.** `recovery.json` is an input hashed by the R1 intent and,
on preparation, the runtime manifest. It binds the parent ZIP, collected archive,
profile, manifest, failed case, all six result-file hashes and their usage,
parent zero-science counts, native/CLI/tokenizer/model hashes, source override
hashes and explicit new limits. Tampering with its charged-call count is rejected
by the inherited integrity check before execution, as exercised locally.

The parent archive is
`82a8021e5ba109724436da9992d0eb6f3079c18f8a806d52606ff662bad44b35`;
its runtime profile is
`de1c1dc9c7206ebde60a3a9de2756d3ae6c8ac1eb6d4fe7904a333553c43b488`.
It records five format successes and failure `FORMAT-ID/001`, with raw stdout
`b' [end of text]\n\n\n'`, six charged calls, zero scientific calls and zero
science games. The source-level cause and receipt analysis are in the
[forensics report](ECHO45-S6-B24-R1-FORENSICS-20261009.md).
Parent evidence is preserved under `provenance/`, outside the upload dataset;
no parent execution checkpoint is imported into R1.

**Notebook/dataset integration.** The prepared private reference is
`navywakura/echo45-s6b24-r1-20261009`, with sole dataset source
`navywakura/echo45-s6b24-r1-private-20261009`. The dataset contains only its
metadata, new ZIP and `b24-native.bin`; there is no `b24-checkpoint.bin`.
The project root is `/kaggle/working/b24-r1-project`, and results root is
`/kaggle/working/b24-r1-results`. Inherited entrypoints remain in use.

The copied notebook requires exactly one native archive with SHA256
`a0dac5390422129b6cf4eacda0746d4e1f7b1ee81edea6c96d9aa5f90128b2f8`.
Missing/mismatched native input stops preparation; the compile/download fallback
for native tools was removed. CLI/tokenizer bytes match the parent registry.
Model revision, weights digest, asset paths and model setup remain inherited;
no weights are bundled or downloaded by this task.

Export filenames stay `b24-status.json`, `b24-evidence.tar.gz`,
`b24-native.tar.gz`, etc. The evidence archive's internal root is now
**`b24-r1-results/`**, matching the new runtime root. This matters when main
implements collection and later checkpoint continuation. Initial metadata
contains no checkpoint dataset; later exact-profile continuation remains main's
responsibility. Do not rerun the local builder after main freezes a submission.

**Validation and remaining runtime checks.** The two focused batch/config tests
first failed as expected against an isolated v1 extraction. The final R1 checks
then passed against the actual ZIP: eight focused tests plus 61 inherited
tests. Those checks cover recorded-command equivalence except `-b`, config
equivalence except its declared fields, exact ZIP/source/input custody, native
hash/reference metadata, closure counts for 0/7/72 scientific calls, strict
parser/acceptance behavior, and recovery-input tamper rejection. System Python
3.14.6 ran the tests; production still requires frozen Python 3.12.13, numpy
2.3.2 and arcengine 0.9.3. The two native grammar checks remain for the inherited
production preparation step.

To repeat the local checks without native/model/game execution:

```bash
/usr/bin/python3 -I -B lab/kaggle/s6b24-r1-20261009/validate.py
```

The validator blocks native subprocesses and network access and keeps temporary
files inside the owned package directory. GPU memory/timing/numerical behavior
at logical batch 8192 and the eight real format probes remain unmeasured here.
No manager/live process, dataset upload, notebook push or cloud launch was
performed; main owns those operations.
