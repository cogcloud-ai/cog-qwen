# Local Qwen provider

A public successor to the small local-model Cog: **Qwen3-4B Q4_K_M** with a locked
llama.cpp runtime. Native context Cogs can resolve it directly. Workbench can
admit it as a model provider and compose it with `cog-turn-harness`.

The [official model](https://huggingface.co/Qwen/Qwen3-4B-GGUF) and this package use
Apache-2.0; llama.cpp uses MIT. See [provenance](docs/provenance.md). Weights are
not bundled into Git: [model-artifact.json](model-artifact.json) pins their
revision, exact SHA-256 and size (about 2.5 GB). Allow additional memory for the
runtime and context. Supported environments: macOS Apple Silicon and Linux x86-64.

## Install and start the model

From this repository:

```sh
pixi install --locked
pixi run test
pixi run check
pixi run fetch
export COG_QWEN_BACKEND_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export COG_QWEN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
pixi run serve-model
```

The first three commands are model-free. `fetch` is the explicit network and disk
operation; it verifies size and SHA-256 before atomic installation. `serve-model`
verifies the artifact again, requires the backend token and starts the locked
llama-server on `127.0.0.1:8080`. It never downloads weights or falls back to a
cloud model. An existing incorrect model file is refused, not silently replaced.

Run subsequent commands in a shell with the **same exported tokens**. Do not put
them in a request file or commit them. Wait until the server is ready; from this
package `pixi run models -- --model qwen3-4b-q4_k_m` checks the serving alias.
The model's non-thinking mode is selected for bounded JSON responses.

## Native context Cogs

The suite's context-Cog manifests point at the sibling `cog-qwen`. With the
backend running and its token exported, use `pixi run resolve` in a consumer,
then its native `ask` interface. The local preset (`pixi run use -- local`) also
uses this provider's alias and backend-token reference. Binding records stay
local and ignored. Starting a model does not automatically bind a consumer.

## Admit through Workbench

From the public workspace root, with the backend still running and both tokens
exported:

```sh
pixi run --manifest-path cog-workbench/pixi.toml suite -- bind \
  --provider cog-qwen --request cog-qwen/examples/bind-request.json
```

The provider returns a candidate and Workbench independently admits it after a
second availability/probe check. This example creates binding `qwen-local`,
revision 1, with local processing only. The configured model is fixed; an
inference request cannot override it. To serve the admitted binding, from this
package run the following in another shell with the same tokens:

```sh
pixi run serve -- --state-dir ../cog-workbench/var/suite/qwen --port 8114
```

From the workspace root, admit the separate local interaction harness:

```sh
pixi run --manifest-path cog-workbench/pixi.toml suite -- bind \
  --provider cog-turn-harness --request cog-qwen/examples/harness-request.json
pixi run --manifest-path cog-workbench/pixi.toml suite -- activate-composition \
  --context cog-author --binding-id qwen-interaction --revision 1
```

Activate the same interaction for other context Cogs as needed. The Workbench
Studio also lists Qwen alongside the other providers: bind Qwen, start its model
gateway, then bind the turn harness to that model. Start the native model first;
Studio does not fetch weights or create credentials for you.

Change binding IDs or increment revisions when repeating admission. Source or
metadata changes require re-admission and reactivation. Revocation is available
through Workbench's `suite revoke` command. The gateway checks revocation before
and after inference and requires its token for every bound endpoint. Native
access is a separate operator-controlled endpoint; revoking a gateway binding
does not stop the native model process.

## Limits and validation

This is model inference, not an agent with tools. It supports text, JSON objects
and locally validated JSON-schema responses; no streaming, tools, multimodal
input, remote endpoint overrides or model fallback. Output is untrusted and a
small model can fail complex builder contracts. No quality claim follows from a
successful health check or schema probe.

The downloaded artifact is checksum-pinned. An admitted binding reports the
server's alias and functional evidence, **not independent process attestation**;
`identity_verified` and `revision_pinned` remain false. The host runs with the
operator's local authority. The authenticated loopback services are not intended
as public or multi-user hosting.

`pixi run test` uses fake models and synthetic loopback requests. It covers
candidate/host separation, fresh admission checks, locality, model substitution,
authentication, malformed output, revocation and artifact integrity without a
model download. Model and gateway processes should be stopped when no longer
needed. State contains binding metadata and request/response hashes, not prompts,
completion text or credential values.

A local macOS qualification run is recorded in
[the verification summary](docs/local-verification-2026-09-24.json). It covers
real authenticated inference and the separate harness, not builder task accuracy.
Linux has a locked environment and CI configuration; this local run was on macOS.
