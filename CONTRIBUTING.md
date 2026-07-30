# Contributing

## Development setup

Install Python 3.13 and [uv](https://docs.astral.sh/uv/), then run:

```bash
make sync
cp .env.example .env
make check
```

Start the development server with:

```bash
make run
```

For the complete local environment:

```bash
make compose-up
make seed
make smoke
```

## Change guidelines

- Keep changes focused on one coherent behaviour.
- Add or update tests for observable behaviour.
- Preserve the boundaries between ingestion, retrieval, ranking, and answer generation.
- Document configuration or API changes in the same change set.
- Use only project-authored or clearly licensed test documents.

Before opening a change for review, run:

```bash
make format
make check
make audit
make container-build
make container-scan
make secret-scan
```

Do not include local configuration, credentials, uploaded files, or model caches.
