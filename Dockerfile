ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry

WORKDIR /build
COPY pyproject.toml poetry.lock ./


#---- dev ----
FROM base AS dev
RUN poetry install --no-root --with=dev
COPY . .


#---- lambda ----
FROM base AS lambda

COPY bitwarden_manager app.py ./
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --no-root --without=dev

ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD ["app.handler"]
