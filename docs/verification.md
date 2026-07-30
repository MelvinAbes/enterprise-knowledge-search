# Verification Record

This record captures the final local release checks run on 2026-07-30. It is evidence for the
documented setup, not a permanent guarantee about future dependency databases or host
environments.

## Functional and quality checks

| Check | Observation |
| --- | --- |
| Formatting and linting | Ruff formatting check and lint passed |
| Static typing | Strict mypy check passed |
| Automated tests | 63 tests passed, including container-backed integration tests |
| Python dependency audit | No known vulnerable locked Python packages reported |
| Compose validation | Configuration rendered successfully with a local password |
| Clean Compose startup | Fresh volumes, migrations, API, worker, PostgreSQL, Redis, and Qdrant started |
| API smoke test | Upload, ingestion polling, hybrid search, metrics, UI, and deletion passed |
| Browser check | Desktop and mobile layouts rendered without horizontal overflow or console errors |
| Secret scan | No findings in the repository working tree |

The application image is approximately 122 MB and runs as UID/GID 10001 with a read-only root
filesystem in Compose. The Qdrant image runs as UID/GID 1000, omits the unused administration
UI, and exposes only its service ports on the internal Compose network. PostgreSQL starts as
its dedicated service user, and only the API port is published to the host.

## Container vulnerability scan

Trivy 0.72.0 scanned the locally built application, PostgreSQL, Qdrant, and pinned Redis images
for high and critical findings.

| Image | High | Critical |
| --- | ---: | ---: |
| Application | 0 | 0 |
| PostgreSQL 17.10 runtime | 0 | 0 |
| Redis 7.2.15 | 0 | 0 |
| Qdrant 1.18.3 runtime | 2 | 0 |

The Qdrant software bill of materials reports:

- `pyo3` 0.28.3, affected by `GHSA-36hh-v3qg-5jq4`, fixed in 0.29.0
- `quinn-proto` 0.11.14, affected by `GHSA-4w2j-m93h-cj5j`, fixed in 0.11.15

These are dependencies inside the current upstream Qdrant release binary and cannot be replaced
independently. The local configuration does not expose a Python extension or a QUIC endpoint,
Qdrant is not published to the host, and the runtime runs without root privileges. Those
controls reduce the applicable attack surface but do not remove the findings. The next Qdrant
patch release should be rescanned and adopted when its software bill of materials contains the
fixed versions.

Run the same image report with:

```bash
make container-build
make container-scan
```
