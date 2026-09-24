# Security

Report vulnerabilities privately through the repository's security reporting
channel when enabled, or contact the maintainers before public disclosure.

Serve only on loopback with dedicated random credentials. The package runs with
the operator's local authority and does not sandbox model runtime code. Treat
model output as untrusted data. Downloaded weights are size- and SHA-256-checked
against the pinned official artifact. Inference sends no requests to cloud model
services. The explicit fetch task uses Hugging Face's HTTPS distribution service.
No credentials, prompts or completions belong in issues or execution logs.
