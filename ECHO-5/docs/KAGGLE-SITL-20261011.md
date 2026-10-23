# Kaggle SITL feasibility and corrected CPU tests — 2026-10-11

Kaggle executed **28 corrected stdlib tests with exact CPython 3.12.13**:
all 18 recovery/adapter tests and 10 explicitly selected parameter/ULog tests.
All passed on private CPU notebooks. **Gazebo/PX4 was not executed on Kaggle.**
The current Podman launcher is incompatible with the probed Kaggle environment
without changes. No frozen scientific source or receipt was edited by this task.

Final evidence: [verification-all.json](../artifacts/kaggle-sitl-20261011-r1/verification-all.json).
All artifacts are under `ECHO-5/artifacts/kaggle-sitl-20261011-r1/`.

## Authentication, quota and privacy

Kaggle MCP quota/search calls returned `Unauthenticated`; `authorize` returned
`Authentication required`. The existing separately managed
`/home/user/.venvs/kaggle` API environment authenticated successfully.
Only launch mechanics and metadata from `lab/kaggle` were inspected; its
managers and campaigns were not imported, relaunched or changed.

Before and after all four jobs, GPU usage was 14,699.588 of 21,600 seconds:
**0 reserved; 6,900.412 seconds remaining** (about 115 minutes). Refresh:
**2026-10-17 00:00 UTC**. The SDK serializes usage as `14699.588.0s`; its
leading decimal is parsed as seconds, matching the existing launcher.
This measures accelerator quota, not CPU quota. The five most recently run
own notebooks were queried before launch: three complete, two errors.
This was not a global enumeration of interactive sessions.

All four new notebooks were read back as **private**, GPU/TPU disabled,
no attached datasets/models/competitions/notebooks, and status `COMPLETE`.
Remote source bytes matched submitted bytes. Every session had a
**300-second service limit**. No model weights, personal files, credentials,
full repository or sealed evaluation data were uploaded.

## Runtime capability

[Private capability probe, version 1](https://www.kaggle.com/code/navywakura/echo5-sitl-capability-20261011-r1)
completed its code in **2.056 seconds**, below its 240-second internal limit.
Exact command outputs: [capability.json](../artifacts/kaggle-sitl-20261011-r1/output-v1/capability.json).

| Check | Observed result |
|---|---|
| Runtime | Ubuntu 24.04.5; default CPython 3.13.15 |
| CPU and memory limits | 4 CPUs; 30 GiB cgroup memory |
| Working disk | 20,940,546,048 bytes free |
| Identity | UID/EUID 0; seccomp mode 2 |
| Simulator/runtime executables | `gz`, Gazebo, PX4, Podman, Docker absent |
| Expected PX4 binary | `/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4` absent |
| Container sockets / FUSE | Docker/Podman sockets and `/dev/fuse` absent |
| Namespace creation | User, mount and network `unshare` each failed with `Operation not permitted` |
| Root operation | `chroot / /bin/true` returned 0; no simulator root filesystem tested |
| Network | HEAD requests to GitHub, PX4 source, OSRF packages and Ubuntu archive returned HTTP 200 |
| Local transport | UDP loopback succeeded |

No Gazebo/PX4 installation or image transfer was attempted. Read-only local
image inspection found ID
`5364c865ebf08b1dd19ee7a6a46ca3c3911056269974e7d9db2ced4a74201d27`,
tag `localhost/echoai-flight1s-px4:v1.15.4-gpsaccuracy`, reported size
**5,264,496,758 bytes**, and a localhost-only repository digest.
The existing launcher requires this exact image, Podman and an isolated
network namespace. Root identity and disk space do not satisfy those requirements.

The existing local pinned-image route remains the appropriate route for the
main agent's actual corrected simulator experiments. A future Kaggle native
or chroot route would need a separately prepared runtime and validated
launcher/evidence changes; `chroot /` success does not establish that route.
GPU acceleration was neither assumed nor requested.

## Exact Python

[Private interpreter probe, version 1](https://www.kaggle.com/code/navywakura/echo5-python312-capability-20261011-r1)
found system Python 3.12.3 and default 3.13.15, neither matching the pin.
Portable setup installed **3.12.13** entirely under
`/kaggle/working/portable-runtime` in **3.391 seconds** including checks.
The Python download was 32.6 MiB; the uv archive was 19,906,150 bytes.
No system interpreter, shell profile or system package installation changed.

The setup follows Astral's [Python installation documentation](https://docs.astral.sh/uv/guides/install-python/)
and [portable release instructions](https://docs.astral.sh/uv/getting-started/installation/).
It uses uv 0.12.23 with archive SHA-256
`9167d72b3319674b6303c4cbe071854bba13ebdf3d76b1a7cbdc175471fb66d6`,
then `uv python install 3.12.13` with an explicit working-directory
installation path and `--no-bin --no-cache --no-config --no-progress`.
Setup is bounded to 180 seconds. Each test job independently verified
the exact interpreter and executed with **`-I -S -B`**.

Evidence: [python-runtime.json](../artifacts/kaggle-sitl-20261011-r1/python312-probe/output-v1/python-runtime.json).
Installed interpreter executable SHA-256:
`021044895e95be79dc2f110367607e684119afbc8ce75f6f0eec94844e0acec7`.

## Corrected tests actually executed

| Private CPU notebook, version 1 | Scope | Result | Test time |
|---|---|---|---|
| [Recovery](https://www.kaggle.com/code/navywakura/echo5-sitl-stdlib-r1-20261011) | Complete suite: 14 recovery + 4 guarded adapter tests | 18/18 passed | 0.178964 s |
| [Parameters](https://www.kaggle.com/code/navywakura/echo5-sitl-stdlib-r2-20261011) | Explicit calibration, ULog framing/binding and EOF selections | 10/10 passed | 0.004509 s |

Both jobs reported **zero failures, errors, skips, expected failures or
unexpected successes**. Runner times including interpreter setup were
4.453004 and 4.228032 seconds; provisioning/collection time is separate.
Source hashes matched before/after execution and against local frozen files.

Of 11 available parameter tests, this one was explicitly unselected because
it imports the full `echo5.sitl` launcher:

`test_sitl_parameters.ParameterCalibrationTests.test_extractor_timeout_becomes_failed_evidence_and_cleans_only_owned_container`

Its omission is recorded in the input manifest, selection receipt and remote
test receipt. No skip decorator, test rewrite, import substitution or hidden
suite patch was added by the Kaggle runner. The original EOF test's own
`pyulog` mock remains in its unchanged source. These are stdlib safeguards,
not validation of a real pyulog installation or actual flight logs.

Recovery upload: exactly **43,945 source bytes** across the module, unchanged
test file and unchanged legacy runner used only as a read-only AST fixture.
Parameter upload: **17,701 source bytes** across its module and test file.
Generated harness/bootstrap code is additional; no other project source was attached.

| Frozen source | SHA-256 |
|---|---|
| `ECHO-5/src/echo5/sitl_recovery.py` | `8e5779a44fe1ab164f476dc44f3a04e7f18cbc22108bfcb7d58e707877fe7660` |
| `ECHO-5/tests/test_sitl_recovery.py` | `637aa7d638b3df53e2da06975a8aa52d5fa4fa1e7708626893555ef748e2884f` |
| `nexus0/drone3/assets/runner.py` | `f10d83d7b750d4c15cef6ea008d688ad8e2c7e15c30af6b16ea3c652725e1c56` |
| `ECHO-5/src/echo5/sitl_parameters.py` | `505736634d011d89b37f9e2b988a854fd3521c46b8d4d229ca77e556896b5e39` |
| `ECHO-5/tests/test_sitl_parameters.py` | `9b9152152bb7c3940dd2c3bf06ae87562694964b5572dd29b37cd8a372c553e5` |

These results validate the selected recovery and calibration/evidence code
contracts. They do not establish correction of flight dynamics, mission
success, hardware performance or a new physical confirmation.

## Artifacts and reproduction

- [Recovery results](../artifacts/kaggle-sitl-20261011-r1/stdlib-r1/output-v1/stdlib-tests.json) and [test log](../artifacts/kaggle-sitl-20261011-r1/stdlib-r1/output-v1/unittest.log).
- [Parameter results](../artifacts/kaggle-sitl-20261011-r1/stdlib-r2/output-v1/stdlib-tests.json), [test log](../artifacts/kaggle-sitl-20261011-r1/stdlib-r2/output-v1/unittest.log) and [explicit selection](../artifacts/kaggle-sitl-20261011-r1/stdlib-r2/selection.json).
- Each job preserves submission/version, remote privacy metadata, exact submitted/remote code, source manifest, execution/interpreter receipts and SHA-256 collection records.
- [Final verification](../artifacts/kaggle-sitl-20261011-r1/verification-all.json) reconciles all four completed private CPU notebooks, both results, all five source hashes, frozen helpers and unchanged GPU quota.

The new helpers are `scripts/kaggle_capability_probe.py`,
`scripts/kaggle_pinned_python.py` and `scripts/kaggle_stdlib_bundle.py`.
The builder accepts only its explicit source allowlist, requires hashes,
embeds unchanged source, lists selected/unselected test IDs and refuses to
overwrite existing artifact directories. It neither authenticates nor submits.
Saved metadata fixes privacy and CPU use; submission used
`kernels_push(..., timeout='300')`.

For a future authorized repeat with unchanged sources, use the preserved input
manifest and a new `stdlib-rN` output name. Changed sources require a new
reviewed hash manifest. Do not modify earlier receipts. Helper syntax and
project `make check` passed before the main agent's source freeze; no helper
source changed afterwards.

One SDK recursively paginated output-listing attempt received HTTP 429 while
traversing portable Python files. Collection switched to **direct, version-bound
downloads of the five named receipts/logs**. No failed job was rerun and no
broad output archive was downloaded.
