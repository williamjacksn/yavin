FROM ghcr.io/astral-sh/uv:0.7.5 AS uv
FROM python:3.13-slim

COPY --from=uv /uv /bin/uv

RUN /usr/sbin/useradd --create-home --shell /bin/bash --user-group python

USER python

COPY --chown=python:python .python-version /home/python/yavin/.python-version
COPY --chown=python:python pyproject.toml /home/python/yavin/pyproject.toml
COPY --chown=python:python uv.lock /home/python/yavin/uv.lock
WORKDIR /home/python/yavin
RUN /bin/uv sync --frozen

ENV PYTHONDONTWRITEBYTECODE="1" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin" \
      org.opencontainers.image.title="Yavin"

COPY --chown=python:python package.json /home/python/yavin/package.json
COPY --chown=python:python run.py /home/python/yavin/run.py
COPY --chown=python:python yavin /home/python/yavin/yavin

ENTRYPOINT ["/bin/uv", "run", "run.py"]
