ARG PYTHON_VERSION

FROM python:${PYTHON_VERSION}-slim AS base

RUN pip install --no-cache-dir poetry awslambdaric

# Install Python dependencies so they are cached
WORKDIR /build

COPY . .

RUN poetry install --without=dev


#---- dev ----
FROM base AS dev
RUN poetry install --with=dev


#---- lambda ----
FROM base AS lambda

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD ["lambda.handler"]
