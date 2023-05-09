.EXPORT_ALL_VARIABLES:

SHELL = /bin/bash
.SHELLFLAGS = -euo pipefail -c

.PHONY: $(MAKECMDGOALS)

docker-build:
	docker build \
		--build-arg "python_version=$$(head -n1 .python-version)" \
		--tag build:local \
		.

install-poetry:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -

init:
	@echo "if you do not have poetry installed please run 'make install-poetry'"
	poetry install --no-root
	poetry run pre-commit autoupdate

static-analysis:
	poetry run bandit . *.py -r
	poetry run flake8 . *.py

test:
	poetry run pytest
