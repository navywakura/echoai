# ECHO-AI source distribution

The repository root is the former echoai/ directory. The six shared integer representation, associative-memory and plasticity helpers are now core/qn.py, cam.py, wsp.py, stdp.py, spoke.py and dag.py. They are the same implementation with distribution import paths updated; no chatbot runtime is included. Historical research reports retain their original paths and source hashes. They describe the original experiments, not hashes of this reorganized distribution.

The live research workspace and frozen S6 sources were not edited. Raw lab environments, sealed input datasets, credentials and legacy websites are not distributed. Documented results remain in docs/. The source manifest verifies the distribution independently of scientific gates.

The supported 4.5 installer is install.sh; release1/ contains the historical 4.0 compilation and licensing tooling. Use the linked Hugging Face 4.0 release for its original binary artifact. A successful setup or devtest does not close S6.

The 11 October publication adds the implemented ECHO-5 research package under
`ECHO-5/`, its local viewer, regression tests, contracts and documentation.
It remains a research alpha and does not change the terminal's 4.5.0b1 release.
Its legacy imports and frozen-source discovery are adapted to the public
`core/` layout. Consequently, historical experiment source hashes identify
the laboratory snapshots, not these adapted publication files.

`research-archive/20261011/MANIFEST.json` records original and distributed
receipt hashes. JSON formatting and absolute local paths are normalized as
declared there; embedded source and evidence hashes still refer to originals.
The archive is a selected evidence snapshot, not the complete execution data.
The live calibration, its runners and frozen sources are not modified by this
publication. A complete re-run must freeze a new distribution-specific receipt.

The Unity project is distributed separately at
https://github.com/navywakura/echounity. It retains its own source integrity
manifest and lists optional third-party artwork separately from its code.
