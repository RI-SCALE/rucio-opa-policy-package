FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# The base image ships a yarn apt source with no signing key, which breaks
# `apt-get update`. This project doesn't need yarn, so drop the source.
RUN rm -f /etc/apt/sources.list.d/yarn.list

# uv; it also provides Python 3.9 (.python-version, Rucio server image) on demand.
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/