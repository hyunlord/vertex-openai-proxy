# Security Policy

## Reporting A Vulnerability

If you discover a private vulnerability in `vertex-openai-proxy`, please avoid opening a public issue with exploit details.

Instead:

1. prepare a short private report with:
   - affected version or commit
   - reproduction steps
   - impact
   - any workaround you already know
2. contact the maintainer through a private channel before disclosure
3. wait for an acknowledgment before sharing public details

## Disclosure Expectations

- do not publish proof-of-concept exploit details before a fix or mitigation is available
- give maintainers time to confirm, reproduce, and prepare a response
- prefer coordinated disclosure over surprise public drops

## Scope

This repository includes:

- the FastAPI application
- Helm and Kubernetes deployment assets
- documentation and verification scripts

Reports about configuration mistakes in private downstream environments may still be useful, but the main priority is vulnerabilities in the public repository itself.
