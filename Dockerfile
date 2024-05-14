ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

WORKDIR /build

RUN sed -i 's/http:/https:/g' /etc/apt/sources.list
RUN apt update && apt -y upgrade && apt -y install curl unzip
RUN curl -LO "https://github.com/bitwarden/clients/releases/download/cli-v2023.3.0/bw-linux-2023.3.0.zip" && unzip *.zip && rm bw-linux-2023.3.0.zip
RUN chmod +x bw
RUN PATH=$PWD:$PATH
RUN ./bw config server https://vault.bitwarden.eu

RUN pip install \
    --index-url https://artefacts.tax.service.gov.uk/artifactory/api/pypi/pips/simple \
    --no-cache-dir \
    poetry

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
