# Repository Development Rules

These rules apply to the entire repository.

## Scope and architecture

- Keep ingestion, retrieval, ranking, and answer generation in separate modules.
- PostgreSQL is the source of truth for document state and chunk metadata.
- Qdrant stores searchable vector representations referenced by stable chunk identifiers.
- External services must be accessed through narrow interfaces defined near their consumers.
- Do not add an abstraction until production code or a test needs the boundary.

## Implementation

- Use typed Python and keep strict static analysis passing.
- Prefer focused domain names over generic names such as manager, helper, or utility.
- Validate data at API and infrastructure boundaries.
- Make retries idempotent and record failures using safe, structured error codes.
- Comments should explain constraints or non-obvious decisions.
- Keep repository content focused on the product and its engineering provenance.

## Data and security

- Never commit credentials, local environment files, uploaded documents, or model caches.
- Use project-authored or clearly licensed demonstration data only.
- Do not log document contents, authorization values, or sensitive request fields.
- Run the secret scan before every push.

## Quality

- Run `make format` before committing code changes.
- Run `make check` before every coherent commit.
- Add tests with each behavioural change.
- Integration tests must exercise real service boundaries where practical.
- Do not suppress lint, type, security, or test failures without documenting the reason.

## Git

- Keep commits small enough to review but complete enough to run.
- Use concise imperative commit messages describing the delivered behaviour.
- Never force-push or rewrite published history.
