# ECHO-AI 4.5 beta distribution

S6 remains under investigation; this is not the final scientific closure of ECHO-4.5. No new S6 campaign or sealed examination was launched by packaging. Stable 4.0: https://huggingface.co/RxLabs/echoai-4-cognitive-agentic

Validation performed in the cleaned source: 30 core tests, 30 grid-memory/local-development tests, 28 terminal tests including mocked OpenCode integration, and 5 source-integrity tests. An isolated wheel installation reproduced the 30 core tests outside the lab directory and verified every packaged source file. External provider credentials and live model inference are not exercised by these tests.

The full current source is at repository root. Six required integer-core helper modules were relocated into core/ with their import paths updated; their algorithms were retained. Historical evidence documents retain their original paths and hashes. Sealed datasets, models, local credentials and raw laboratory environments are not distributed.
