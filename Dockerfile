FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
# If uv.lock exists, uv will use it automatically.
RUN uv sync --no-dev --no-install-project

COPY src ./src
COPY config ./config

RUN uv sync --no-dev

CMD ["uv", "run", "python", "-m", "gdacs_events_scraper"]
