SHELL       := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: sync
sync: ## Create .venv from uv.lock
	uv sync --locked

.PHONY: lint
lint: ## Ruff lint and format check
	uv run ruff check .
	uv run ruff format --check .

.PHONY: format
format: ## Ruff format and autofix
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: typecheck
typecheck: ## mypy
	uv run mypy

.PHONY: test
test: ## Unit tests with coverage
	uv run pytest

.PHONY: build
build: ## Wheel and sdist into dist/
	uv build
