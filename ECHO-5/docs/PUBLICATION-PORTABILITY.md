# Public source distribution boundary — 2026-10-11

ECHO-5 is research, **not green**. The authoritative current status is the
[project checkpoint](../../docs/PROJECT-CHECKPOINT-20261011.md). In particular,
the conventional contradiction calibration receipt lacks `ulog-parameters.json`;
completion of calibration jobs does not establish a clean calibration.

This export contains the current implementation, scripts, tests, contracts,
lockfile and historical reports. It excludes agent instructions, environments,
caches and live artifacts. Historical reports and `docs/inventory/` retain their
original content and scope. The publication checklist clarifies that the 24
transfer controls are 12 ambiguous rotations and 12 unsupported-color cases,
and points to the current project checkpoint. Its private paths and hashes describe
that history; they are not claims about the public source distribution.

**The published bytes differ from the original audited source hashes.** Import,
layout and distribution adaptations also change newly generated source receipts.
Passing the publication checks establishes bounded software portability only.
It does not reproduce or extend the historical scientific audits. No live or
sealed campaign, S6 experiment, simulator or flight is part of this validation.

## Adaptation boundary

The full flattened echoAI repository is required. ECHO-5 is still a source
workspace, not an independently installable package; no build backend is added.

- `src/echo5/distribution.py` declares the six `core/*.py` dependencies and
  their package initializer. It contains layout information only.
- `legacy.py` loads the local `echoai` package from its explicit path, keeps
  existing short and qualified import identities together, and admits `core`.
  It exposes only the repository root, never its parent. Shared imports disable
  bytecode writes so imported sources remain read-only. No `navi10_*` fallback,
  compatibility files, second bus or cognitive engine is introduced.
- `neural_observer.py` imports `echoai.core.qn` and `echoai.core.spoke` through
  that boundary and reports the actual qualified module name. Its measured
  Layer256 diagnostic remains outside the acting policy.
- `cli.py`, `audit.py`, `closure.py`, `control.py` and `release.py` resolve the
  existing `host` receipt group against the repository's `core/` files. The
  archive label `host/` remains for schema continuity; it no longer denotes
  files in the checkout's parent. Empty or incomplete core receipts are not
  accepted as a substitute for the declared core coverage. Do not replay a
  historical private-layout receipt against this adapted checkout.
- `sitl.py` stages the actual `echoai/core/` package and helpers needed by the
  transformed inherited runner. Receipts hash these staged files under their
  public paths. The availability report looks for PX4 on PATH instead of a
  developer's absolute home directory. Simulator configuration and gates stay
  unchanged. The local image digest remains pinned; the image is not shipped.
- `scripts/inventory.py` scans the flattened `core/` tree instead of discovering
  arbitrary Python files in the parent checkout. It writes new results to
  `artifacts/inventory-publication/`, preserving the historical catalogue.
- `pyproject.toml` requires exactly CPython 3.12.13, matching `.python-version`
  and runtime checks. `scripts/setup_sandbox.py --wheel-dir` supports an offline,
  hash-checked wheel directory and disables pip's shared cache writes. The
  sandbox dependency pins and lockfile hashes are unchanged.

Other inherited algorithms, scientific thresholds, held-out seed intervals and
failure classifications are retained. The source layout adaptations are not
an assertion of bit-for-bit or experimental equivalence.

## Local checks

From the public repository's `ECHO-5/` directory, with CPython 3.12.13 already
installed:

```sh
mkdir -p artifacts/publication-checks/tmp
export TMPDIR="$PWD/artifacts/publication-checks/tmp"
make setup
make check
nice -n 10 make test
node --check src/echo5/web/app.js
```

Setup creates a new local `.venv` without pip or global packages. It never
uses the original experiment's environment. Temporary test files stay under
ECHO-5 through `TMPDIR`; the integration boundary avoids caches in shared code.

The optional MiniGrid/BabyAI profile uses a separate `.venv-sandbox`:

```sh
# wheel-dir must contain the seven wheels covered by requirements-sandbox.lock.
python3.12 -I scripts/setup_sandbox.py --wheel-dir /path/to/locked-wheels
python3.12 -I scripts/setup_sandbox.py --check
nice -n 10 .venv-sandbox/bin/python -I -B scripts/closure.py test-external
```

With `--wheel-dir`, pip uses `--no-index`, wheels only and `--require-hashes`.
The export validation can reuse cached wheel bytes read-only, after checking
the lock hashes; it does not reuse an installed or frozen environment. Without
that option, `make setup-sandbox` explicitly installs the optional locked profile
from the configured package index. No training framework is required.

`test_distribution.py` checks core namespace identity, agreement of custody
readers and imports of staged runner helpers in a fresh `-I -B -S` subprocess.
Staging writes a new temporary fixture and launches no container. The ordinary
suite uses small synthetic fixtures; it does not open old experiment artifacts.

The publication checks completed under CPython 3.12.13: 338 stdlib tests
reported `OK (skipped=12)`, and all 32 sandbox tests passed, including those
12 native tests. These overlapping suites must not be added as distinct tests.
Environment/syntax checks covered 67 Python files; JavaScript syntax passed.
The three new distribution regressions passed. Static inventory parsed 987
published files without errors. Source custody stayed unchanged across the
required checks (81 own files, 714 inherited files and seven core files).
Local logs and receipts are in `artifacts/publication-checks/required/`; these
validation artifacts and managed environments are excluded from Git.

## Remaining limits

- Browser automation needs a separately managed Playwright/browser environment;
  JavaScript syntax and HTTP unit checks do not establish a browser UI pass.
- Gazebo/PX4, Podman and the pinned local image are separate requirements. Helper
  import checks do not establish SITL readiness or validation. No image build,
  simulator launch, calibration replay or flight is performed for this export.
- Kaggle scripts are retained as historical optional tooling, including their
  original private notebook/account and artifact defaults. They are not portable
  cloud deployment instructions and were not invoked during publication checks.
- Historical documents may refer to unpublished local artifacts or private
  checkout locations. They remain historical evidence, not executable paths
  for the public source tree. S6 and the ECHO-5 research closure remain open.
