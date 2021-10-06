FROM python:3.10.0-alpine3.14

RUN /sbin/apk add --no-cache libpq
RUN /usr/sbin/adduser -g python -D python

USER python
RUN /usr/local/bin/python -m venv /home/python/venv

COPY --chown=python:python requirements.txt /home/python/yavin/requirements.txt
RUN /home/python/venv/bin/pip install --no-cache-dir --requirement /home/python/yavin/requirements.txt

ENV APP_VERSION="2021.11" \
    PATH="/home/python/venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

ENTRYPOINT ["/home/python/venv/bin/python"]
CMD ["/home/python/yavin/run.py"]
HEALTHCHECK CMD ["/home/python/yavin/docker-healthcheck.sh"]

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin/" \
      org.opencontainers.image.title="Yavin" \
      org.opencontainers.image.version="${APP_VERSION}"

COPY --chown=python:python docker-healthcheck.sh /home/python/yavin/docker-healthcheck.sh
COPY --chown=python:python run.py /home/python/yavin/run.py
COPY --chown=python:python yavin /home/python/yavin/yavin
