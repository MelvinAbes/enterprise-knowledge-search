# syntax=docker/dockerfile:1.7

FROM postgres:17.10-alpine3.23@sha256:8189a1f6e40904781fc9e2612687877791d21679866db58b1de996b31fc312e4

RUN apk upgrade --no-cache \
    && rm /usr/local/bin/gosu

USER postgres
