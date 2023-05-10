ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry

# Install Python dependencies so they are cached
WORKDIR /build

COPY . .


#---- dev ----
FROM base AS dev
RUN poetry install --with=dev


#---- lambda ----
FROM base AS lambda

RUN poetry install --without=dev

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD ["lambda.handler"]
