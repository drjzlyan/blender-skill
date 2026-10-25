# Security

## Local execution by design

`blender-skill` runs arbitrary Python inside your Blender process and can launch
a local CUDA inference process. That is the intended function of a Blender MCP.

- Bind the bridge to `127.0.0.1` only.
- A local token is generated at setup and required by the MCP client.
- Never expose the port to a network, container bridge, or tunnel.
- Only run the skill against scenes and files you trust.

## Secrets

- No credentials are stored in this repository.
- Hugging Face tokens are read from the user's environment (`HF_TOKEN`) or the
  standard Hugging Face token file.
- `.env` files and model weights are excluded from git.

## Reporting

Open a private security advisory on the GitHub repository. Do not include
tokens, model weights, or proprietary `.blend` files in a report.
