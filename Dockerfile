FROM python:3.7.0-alpine3.8

COPY requirements-docker.txt /yavin/requirements-docker.txt

RUN /sbin/apk --no-cache add --virtual .deps gcc musl-dev postgresql-dev \
 && /sbin/apk --no-cache add libpq \
 && /usr/local/bin/pip install --no-cache-dir --requirement /yavin/requirements-docker.txt \
 && /sbin/apk del .deps

COPY . /yavin

ENV PYTHONUNBUFFERED 1
ENV TZ UTC

ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/yavin/run.py"]

LABEL maintainer=william@subtlecoolness.com \
      org.label-schema.schema-version=1.0 \
      org.label-schema.version=2.1.1
