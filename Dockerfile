ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry \
    awslambdaric

ENV AWS_DEFAULT_REGION="foobar"

WORKDIR /build

COPY pyproject.toml poetry.lock .

#---- dev ----
FROM base AS dev
RUN poetry install --no-root --with=dev
COPY . .


#---- lambda ----
FROM base AS lambda

COPY bitwarden_manager app.py .
RUN poetry install --no-root --without=dev --system

ENTRYPOINT [ "poetry", "run", "python", "-m", "awslambdaric" ]
CMD ["app.handler"]
