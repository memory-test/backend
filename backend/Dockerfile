FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable


FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi"]