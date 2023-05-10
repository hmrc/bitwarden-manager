.EXPORT_ALL_VARIABLES:

SHELL = /bin/bash
.SHELLFLAGS = -euo pipefail -c

.PHONY: $(MAKECMDGOALS)

PYTHON_VERSION = $(shell head -1 .python-version)

POETRY = docker run \
	--interactive \
	--rm \
	--env "PYTHONWARNINGS=ignore:ResourceWarning" \
	--volume "$(PWD):/build:z" \
	build:local poetry run

python:
	docker build --target dev\
		--file Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--tag build:local .

ci: flake8 fmt-check mypy bandit test md-check

install-poetry:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

init:
	@echo "if you do not have poetry installed please run 'make install-poetry'"
	poetry install
	poetry run pre-commit autoupdate

flake8: python
	@$(POETRY) flake8 --max-line-length 120

fmt:
	@$(POETRY) black --line-length 120 .

fmt-check: python
	@$(POETRY) black --line-length 120 --check .

mypy: python
	@$(POETRY) mypy --strict .

bandit: python
	@$(POETRY) bandit -c bandit.yaml -r -q .

test: python
	@$(POETRY) pytest \
		-v \
		-p no:cacheprovider \
		--no-header \
		--cov=. \
		--cov-report term-missing \
		--no-cov-on-fail
		# --cov-fail-under=100 \

md-check:
	@docker pull zemanlx/remark-lint:0.2.0
	@docker run --rm -i -v $(PWD):/lint/input:ro zemanlx/remark-lint:0.2.0 --frail .

container-release:
	docker build --target lambda \
		--file Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--tag container-release:local .
