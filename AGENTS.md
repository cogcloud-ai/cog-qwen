# Local Qwen provider

Read COG.md and README.md. This is a model-only provider; interaction behavior
belongs to the separate turn harness. Source and tests are self-contained.

Keep bind candidate-only and admission host-owned. Never permit inference to
change model, endpoint, credential references, or routing. Model acquisition is
explicit and verified against model-artifact.json before atomic installation and
before serving. Do not commit weights, tokens, prompts, completions, or state.

Use Pixi's locked environments on the declared platforms. Run `pixi run test`
and `pixi run check`; tests use synthetic loopback servers and never fetch weights.
Live checks are separate and must identify the exact model artifact and runtime.
Commit with your own identity. Preserve Apache and upstream notices.
