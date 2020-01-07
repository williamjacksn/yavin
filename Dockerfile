FROM python:3.8.1-alpine3.11

COPY requirements.txt /yavin/requirements.txt

RUN /sbin/apk add --no-cache --virtual .deps gcc musl-dev postgresql-dev \
 && /sbin/apk add --no-cache libpq \
 && /usr/local/bin/pip install --no-cache-dir --requirement /yavin/requirements.txt \
 && /sbin/apk del --no-cache .deps

ENV APP_VERSION="2020.1" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/yavin/run.py"]
HEALTHCHECK CMD ["/groupmemail/docker-healthcheck.sh"]

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin/" \
      org.opencontainers.image.title="Yavin" \
      org.opencontainers.image.version="${APP_VERSION}"

COPY . /yavin
RUN chmod +x /groupmemail/docker-healthcheck.sh
