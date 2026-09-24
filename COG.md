---
type: cog [0.1]
name: cog-qwen
description: Local Qwen3-4B inference with pinned public weights, llama.cpp and host-admitted bindings.
version: "0.1.0"
license: Apache-2.0
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-manifest [0.1]
---

# Local Qwen model provider

Provides text and structured JSON inference on the operator's machine, with no
agent tools or remembered conversation. The package declares exact Qwen3-4B
Q4_K_M artifact bytes and installs a locked llama.cpp runtime. Weight acquisition
is an explicit task; weights and runtime state are not committed to Git.

Native consumers can resolve this package's loopback OpenAI-compatible endpoint.
The builder suite uses an independently admitted model binding through the
host gateway, paired with cog-turn-harness for a JSON interaction.

The bind task produces only a candidate. The separate host admission task
rechecks availability, request correlation and requested probe evidence before
storing an admitted revision. Inference cannot change the model, endpoint or
credential references. Revoked bindings cannot produce accepted results.

Checksum verification establishes the downloaded file's identity. The binding
reports the serving alias without claiming remote/process attestation of weights;
identity_verified and revision_pinned remain false. A probe establishes functional
behavior, not model quality. No automatic download, cloud fallback, model swap,
credential copying or arbitrary execution is performed during inference.

The local host is trusted. This is not a sandbox or a multi-user inference
service. Qwen3-4B is a small model; evaluate its accuracy for the intended task.
See README.md for setup, limits, model license and reproducible tests.
