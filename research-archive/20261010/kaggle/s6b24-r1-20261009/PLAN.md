**Bounded R1 packaging plan**

The user's approved scope is a ZIP-profile fork of the exact v1 package. Only
this directory, the named recovery report and the new package test may change.

1. Check parent ZIP, collected evidence/profile, six format-call receipts and
   native archive hashes; record the unchanged original 100 source hashes.
2. Write focused package/runtime tests and observe the batch-size test fail on
   an isolated extraction of v1. No native programs, model calls or games.
3. Create copied overrides for `seed/s6b24_model.py` (logical batch and explicit
   configuration), `seed/s6b24.py` (current and cumulative closure accounting),
   and the runtime contract (declared recovery). Keep the other 97 sources exact.
4. Add hash-bound `b24-input/recovery.json`, recompute the intent, and build a
   deterministic ZIP. Copy the exact native archive to dataset/b24-native.bin.
5. Copy the notebook with R1 paths/package hash, require the pinned native
   archive, and set new private reference/dataset metadata without a checkpoint.
6. Validate the extracted R1 ZIP with focused tests and the inherited bounded
   B24 suite. Emit actual source/ZIP/notebook diffs and final custody checks.

No deployment or execution is part of this package. The parent six calls remain
charged; eight fresh neutral probes are required. Science stays at 72 model
calls and 8,310 games maximum; total cumulative model-call maximum is 86.
