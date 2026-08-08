FROM python:3.12

WORKDIR /app

RUN pip install uv==0.12.0

COPY pyproject.toml .

RUN uv sync

COPY . .

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi"]