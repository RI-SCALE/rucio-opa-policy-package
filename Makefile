SHELL       := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
UV ?= uv
COMPOSE := docker compose -f docker/docker-compose.yml
OPA_PORT ?= 8181

.DEFAULT_GOAL := help

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk -F':.*?## ' '{printf "  %-18s %s\n", $$1, $$2}'

.PHONY: sync
sync: ## Create or refresh .venv from uv.lock
	$(UV) sync --locked

.PHONY: hooks
hooks: ## Install the git pre-commit hook
	$(UV) run pre-commit install

.PHONY: check
check: ## ruff, format, import contracts and mypy via pre-commit
	$(UV) run pre-commit run --all-files

.PHONY: format
format: ## Auto-fix ruff findings and formatting
	$(UV) run ruff check --fix src tests
	$(UV) run ruff format src tests

.PHONY: audit
audit: ## pip-audit the locked dev environment
	$(UV) run pip-audit --skip-editable

.PHONY: test-unit
test-unit: ## Unit tests only (no Docker)
	$(UV) run pytest tests/unit

.PHONY: test-integration
test-integration: ## Against a real OPA; set POLICY_TEST_OPA_URL to reuse `make up`, else testcontainers starts it
	$(UV) run pytest tests/integration -m integration

.PHONY: test
test: ## Unit and integration tests
	$(UV) run pytest tests/unit tests/integration

.PHONY: coverage
coverage: ## Unit and integration tests with coverage report
	$(UV) run pytest tests/unit tests/integration --cov=rucio_opa_v1_policy --cov-report=term-missing --cov-report=xml

.PHONY: up
up: ## Start OPA with the contract policy (POLICY_TEST_OPA_URL=http://localhost:$(OPA_PORT))
	OPA_PORT=$(OPA_PORT) $(COMPOSE) up -d --wait

.PHONY: down
down: ## Stop OPA
	$(COMPOSE) down -v

.PHONY: build
build: ## Wheel and sdist into dist/
	$(UV) build
