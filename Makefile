SHELL       := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
UV ?= uv

.DEFAULT_GOAL := help
.PHONY: help sync lint format typecheck test build

help: ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

sync: ## Create or refresh .venv from uv.lock
	$(UV) sync --locked

lint: ## ruff lint and format check
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests

format: ## Auto-fix ruff findings and formatting
	$(UV) run ruff check --fix src tests
	$(UV) run ruff format src tests

typecheck: ## mypy
	$(UV) run mypy

test: ## Unit tests with coverage (no Rucio, no OPA needed)
	$(UV) run pytest

build: ## Wheel and sdist into dist/
	$(UV) build
