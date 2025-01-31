.EXPORT_ALL_VARIABLES:

SHELL = /bin/bash
.SHELLFLAGS = -euo pipefail -c

.PHONY: $(MAKECMDGOALS)

OS := $(shell uname -s | tr A-Z a-z)

ifeq ($(OS), darwin)
OS = macos
endif

BITWARDEN_CLI_VERSION := 2024.4.1

PYTHON_VERSION = $(shell head -1 .python-version)
PYTHON_SRC = *.py bitwarden_manager/ tests/

POETRY_DOCKER = docker run \
	--interactive \
	--rm \
	build:local poetry run

POETRY_DOCKER_MOUNT = docker run \
	--interactive \
	--rm \
	--volume "$(PWD)/bitwarden_manager:/build/bitwarden_manager:z" \
	--volume "$(PWD)/tests:/build/tests:z" \
	build:local poetry run

python:
	docker build --target dev \
		--file Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--tag build:local .

install-poetry:
	curl -sSL https://install.python-poetry.org | python -

init:
	@echo "if you do not have poetry installed please run 'make install-poetry'"
	poetry install
	poetry run pre-commit autoupdate

flake8: python
	@$(POETRY_DOCKER) flake8 --max-line-length 120 --exclude=.venv

fmt:
	@$(POETRY_DOCKER_MOUNT) black --line-length 120 --exclude=.venv $(PYTHON_SRC)

fmt-check: python
	@$(POETRY_DOCKER) black --line-length 120 --check $(PYTHON_SRC)

mypy: python
	@$(POETRY_DOCKER) mypy --strict $(PYTHON_SRC)

bandit: python
	@$(POETRY_DOCKER) bandit -c bandit.yaml -r -q $(PYTHON_SRC)

python-test: python
	@$(POETRY_DOCKER) pytest \
		-v \
		-p no:cacheprovider \
		--no-header \
		--cov=bitwarden_manager \
		--cov-report term-missing \
		--no-cov-on-fail \
		--cov-fail-under=100

test: python-test flake8 fmt-check mypy bandit md-check

ci: test

REMARK_LINT_VERSION = 0.3.5
md-check:
	@docker run --pull missing --rm -i -v $(PWD):/lint/input:ro ghcr.io/zemanlx/remark-lint:${REMARK_LINT_VERSION} --frail .

# Update (to best of tools ability) md linter findings
.PHONY: md-fix
md-fix:
	@docker run --pull missing --rm -i -v $(PWD):/lint/input:rw ghcr.io/zemanlx/remark-lint:${REMARK_LINT_VERSION} . -o

container-release:
	docker build --target lambda \
		--file Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--tag container-release:local .

install-bitwarden-cli:
	@curl -sL https://github.com/bitwarden/clients/releases/download/cli-v$(BITWARDEN_CLI_VERSION)/bw-macos-$(BITWARDEN_CLI_VERSION).zip -o bw.zip
	@unzip -o bw.zip -d /usr/local/bin/ && rm -f bw.zip

uninstall-bitwarden-cli:
	@rm -f /usr/local/bin/bw
