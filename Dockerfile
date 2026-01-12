FROM ghcr.io/astral-sh/uv:0.9.24-trixie-slim

RUN /usr/sbin/useradd --create-home --shell /bin/bash --user-group python
USER python

WORKDIR /app
COPY --chown=python:python .python-version pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin" \
      org.opencontainers.image.title="Yavin"

COPY --chown=python:python README.md ./
COPY --chown=python:python src/yavin ./src/yavin
RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "--no-sync", "yavin"]
