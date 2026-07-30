# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately through the repository owner's GitHub
profile. Do not open a public issue containing exploit details, credentials, document content,
or other sensitive data.

Include the affected component, reproduction conditions, likely impact, and any suggested
mitigation. Reports will be acknowledged after they can be reproduced safely.

## Supported code

Security fixes apply to the latest revision of the default branch. Earlier commits and local
development snapshots are not maintained as separate release lines.

## Development practices

- Configuration values are supplied through environment variables.
- Local environment files, uploads, and model caches are excluded from version control.
- Upload types and sizes are validated before processing.
- Queue payloads contain identifiers rather than document content.
- Logs must not contain document text, credentials, or authorization values.
- Dependency and secret scans are part of the verification workflow.

The service is not ready for untrusted public access until authentication, authorization, rate
limiting, malware scanning, and storage isolation are implemented.
