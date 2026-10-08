# echo-nexus 0.1.1

Fix local GGUF startup and persist named connections.

- CPU startup now disables host-operation GPU offload as well as GPU layers.
  A real ROCm/HIP warmup abort was observed on AMD gfx90c with the old launcher.
- Smaller 2048-token context, batches 256/64, four threads. Progress every ten
  seconds, monotonic 300-second deadline, unique attempt logs and signal errors.
- `/connections`: list, save, use, remove, and default profiles; CLI startup overrides.
- `@KEY_FILE` credentials: lazy runtime loading, references only in configuration,
  no shell evaluation, secret redaction. No credential or local setup is shipped.

Validation: 12 harness tests passed, including persistence across application
restarts and lazy key-file loading/redaction using dummy credentials. A real Qwen3
4B Q4_K_M GGUF loaded in 2.08 seconds and answered a short prompt in 31.31 seconds
total on the affected Linux machine using the corrected system llama-server.
These are one observed run, not a loading-time guarantee. No real OpenRouter key
was inspected or used during setup; that API is validated on the first message.

The ECHO core, development adapter, model weights and research exams are excluded.
