ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry \
    awslambdaric

WORKDIR /build

COPY pyproject.toml .
COPY poetry.lock .

#---- dev ----
FROM base AS dev
RUN poetry install --no-root --with=dev
COPY . .


#---- lambda ----
FROM base AS lambda

COPY bitwarden_manager .
COPY main.py .
RUN poetry install --without=dev

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD ["app.handler"]
