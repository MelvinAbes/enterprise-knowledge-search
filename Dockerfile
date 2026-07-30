# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.4@sha256:5164bf84e7b4e2e08ce0b4c66b4a8c996a286e6959f72ac5c6e0a3c80e8cb04a AS uv
FROM python:3.13.11-slim-trixie@sha256:2b9c9803c6a287cafa0a8c917211dddd23dcd2016f049690ee5219f5d3f1636e AS python-runtime
FROM python-runtime AS runtime-support

RUN set -eu; \
    multiarch="$(python -c 'import sysconfig; print(sysconfig.get_config_var("MULTIARCH"))')"; \
    mkdir -p "/runtime-libs/usr/lib/${multiarch}"; \
    for library in libbz2.so.1.0 libffi.so.8 liblzma.so.5 libsqlite3.so.0; do \
        path="$(ldconfig -p | awk -v library="${library}" '$1 == library { print $NF; exit }')"; \
        test -n "${path}"; \
        cp --dereference "${path}" "/runtime-libs/usr/lib/${multiarch}/${library}"; \
    done

FROM python-runtime AS build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable \
    && mkdir -p /runtime/app/data/documents /runtime/app/model-cache \
    && chown -R 10001:10001 /runtime/app

FROM gcr.io/distroless/cc-debian13:nonroot@sha256:d97bc0a941b8d4be647dc0ee75b264ddbb772f1ac5ba690a4309c00723b23775

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/model-cache/huggingface \
    HF_HUB_DISABLE_XET=1 \
    XDG_CACHE_HOME=/app/model-cache/.cache \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=python-runtime /usr/local /usr/local
COPY --from=runtime-support /runtime-libs /
COPY --from=build --chown=10001:10001 /runtime/app /app
COPY --from=build --chown=10001:10001 /app/.venv ./.venv
COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 migrations ./migrations

USER 10001:10001
ENTRYPOINT []

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "knowledge_search.main:app", "--host", "0.0.0.0", "--port", "8000"]
