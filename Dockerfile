ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry

WORKDIR /build
COPY pyproject.toml poetry.lock ./


# create our virtualenvv in the current folder and allow non root users (such as the lambda runner) to read the config file
RUN poetry config virtualenvs.in-project true --local && chmod +r poetry.toml

#---- dev ----
FROM base AS dev
RUN poetry install --no-root --with=dev
COPY . .


#---- lambda ----
FROM base AS lambda


COPY app.py .
COPY bitwarden_manager/ bitwarden_manager/
RUN poetry install --no-root --without=dev

ENTRYPOINT ["poetry", "run", "python", "-m", "awslambdaric" ]
CMD ["app.handler"]
