# Provenance

The provider/host separation, immutable binding store and gateway request
validation are adapted from the Apache-2.0 cog-openrouter reference implementation
at commit 27060d041becac3b1f12c6c7b0418c17d672616e. This package replaces cloud
routing with fixed loopback llama.cpp transport and local qualification.

Weights are the official Qwen/Qwen3-4B-GGUF Q4_K_M artifact at Hugging Face commit
bc640142c66e1fdd12af0bd68f40445458f3869b, SHA-256
7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5.
The upstream model uses Apache-2.0; llama.cpp uses MIT. Installed dependencies
retain their licenses. This package's Apache license does not replace them.

Sources:
- https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/bc640142c66e1fdd12af0bd68f40445458f3869b
- https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc640142c66e1fdd12af0bd68f40445458f3869b/LICENSE
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://github.com/cogcloud-ai/cog-openrouter
