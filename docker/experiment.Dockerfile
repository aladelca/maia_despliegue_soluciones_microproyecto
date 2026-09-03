FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    GIT_PYTHON_REFRESH=quiet \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --all-groups --no-editable \
    && rm -rf /tmp/uv-cache

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin experiment

USER experiment

ENTRYPOINT ["/app/.venv/bin/python", "-m", "online_shoppers"]
