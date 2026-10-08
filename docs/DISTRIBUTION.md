# ECHO-AI source distribution

The repository root is the former echoai/ directory. The six shared integer representation, associative-memory and plasticity helpers are now core/qn.py, cam.py, wsp.py, stdp.py, spoke.py and dag.py. They are the same implementation with distribution import paths updated; no chatbot runtime is included. Historical research reports retain their original paths and source hashes. They describe the original experiments, not hashes of this reorganized distribution.

The live research workspace and frozen S6 sources were not edited. Raw lab environments, sealed input datasets, credentials and legacy websites are not distributed. Documented results remain in docs/. The source manifest verifies the distribution independently of scientific gates.

The supported 4.5 installer is install.sh; release1/ contains the historical 4.0 compilation and licensing tooling. Use the linked Hugging Face 4.0 release for its original binary artifact. A successful setup or devtest does not close S6.
