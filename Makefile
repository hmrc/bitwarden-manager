.EXPORT_ALL_VARIABLES:

SHELL = /bin/bash
.SHELLFLAGS = -euo pipefail -c

.PHONY: $(MAKECMDGOALS)

PYTHON_VERSION = $(shell head -1 .python-version)

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
	@$(POETRY_DOCKER_MOUNT) black --line-length 120 --exclude=.venv .

fmt-check: python
	@$(POETRY_DOCKER) black --line-length 120 --check .

mypy: python
	@$(POETRY_DOCKER) mypy --strict .

bandit: python
	@$(POETRY_DOCKER) bandit -c bandit.yaml -r -q .

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

md-check:
	@docker pull zemanlx/remark-lint:0.2.0
	@docker run --rm -i -v $(PWD):/lint/input:ro zemanlx/remark-lint:0.2.0 --frail .

container-release:
	docker build --target lambda \
		--file Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--tag container-release:local .
