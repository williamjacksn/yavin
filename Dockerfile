FROM ghcr.io/astral-sh/uv:0.7.7-bookworm-slim

RUN /usr/sbin/useradd --create-home --shell /bin/bash --user-group python
USER python

WORKDIR /app
COPY --chown=python:python .python-version pyproject.toml uv.lock ./
RUN /usr/local/bin/uv sync --frozen

ENV PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin" \
      org.opencontainers.image.title="Yavin"

COPY --chown=python:python package.json run.py ./
COPY --chown=python:python yavin ./yavin

ENTRYPOINT ["/usr/local/bin/uv", "run", "run.py"]
