FROM python:3.9.6-alpine3.14

COPY requirements.txt /yavin/requirements.txt

RUN /sbin/apk add --no-cache libpq
RUN /usr/local/bin/pip install --no-cache-dir --requirement /yavin/requirements.txt

ENV APP_VERSION="2021.7" \
    PYTHONUNBUFFERED="1" \
    TZ="Etc/UTC"

ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/yavin/run.py"]
HEALTHCHECK CMD ["/yavin/docker-healthcheck.sh"]

LABEL org.opencontainers.image.authors="William Jackson <william@subtlecoolness.com>" \
      org.opencontainers.image.description="Personal web tools" \
      org.opencontainers.image.source="https://github.com/williamjacksn/yavin/" \
      org.opencontainers.image.title="Yavin" \
      org.opencontainers.image.version="${APP_VERSION}"

COPY . /yavin
RUN chmod +x /yavin/docker-healthcheck.sh
