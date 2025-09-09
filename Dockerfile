FROM ghcr.io/astral-sh/uv:0.8.15-python3.13-alpine

WORKDIR /app
COPY ./.python-version ./.python-version
COPY ./pyproject.toml ./pyproject.toml
COPY uv.lock uv.lock

RUN uv sync --locked --no-install-project

COPY ./src ./src
COPY ./main.py ./main.py

ENTRYPOINT [ "uv", "run", "./main.py" ]