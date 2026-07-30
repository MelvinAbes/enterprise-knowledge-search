# syntax=docker/dockerfile:1.7

FROM qdrant/qdrant:v1.18.3-unprivileged@sha256:affb67e1d6f2f93d7d20b90d238a7d4b974d36351c162e73bda794e4b2e03483 AS qdrant

USER root

RUN set -eu; \
    library_dir="$(dirname "$(ldd /qdrant/qdrant | awk '$1 == "liblzma.so.5" { print $3; exit }')")"; \
    multiarch="$(basename "${library_dir}")"; \
    mkdir -p "/runtime-libs/usr/lib/${multiarch}" \
        /runtime/qdrant/snapshots \
        /runtime/qdrant/storage; \
    ldd /qdrant/qdrant \
        | awk '$1 ~ /^lib(unwind|lzma)/ { print $3 }' \
        | while read -r path; do \
            cp --dereference "${path}" "/runtime-libs/usr/lib/${multiarch}/$(basename "${path}")"; \
        done; \
    chown -R 1000:1000 /runtime/qdrant

FROM gcr.io/distroless/cc-debian13:nonroot@sha256:d97bc0a941b8d4be647dc0ee75b264ddbb772f1ac5ba690a4309c00723b23775

ENV QDRANT__SERVICE__ENABLE_STATIC_CONTENT=false \
    QDRANT__SERVICE__HOST=0.0.0.0

COPY --from=qdrant /runtime-libs /
COPY --from=qdrant --chown=1000:1000 /runtime/qdrant /qdrant
COPY --from=qdrant --chown=1000:1000 /qdrant/config /qdrant/config
COPY --from=qdrant --chown=1000:1000 /qdrant/qdrant /qdrant/qdrant
COPY --from=qdrant --chown=1000:1000 /qdrant/qdrant.spdx.json /qdrant/qdrant.spdx.json

WORKDIR /qdrant

USER 1000:1000

EXPOSE 6333 6334

CMD ["/qdrant/qdrant", "--disable-telemetry"]
