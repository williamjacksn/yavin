FROM python:3.7.2-alpine3.9

COPY requirements.txt /yavin/requirements.txt

RUN /sbin/apk add --no-cache --virtual .deps gcc musl-dev postgresql-dev \
 && /sbin/apk add --no-cache libpq \
 && /usr/local/bin/pip install --no-cache-dir --requirement /yavin/requirements.txt \
 && /sbin/apk del --no-cache .deps

ENV PYTHONUNBUFFERED 1
ENV TZ UTC

ENTRYPOINT ["/usr/local/bin/python"]
CMD ["/yavin/run.py"]

LABEL maintainer=william@subtlecoolness.com \
      org.label-schema.schema-version=1.0 \
      org.label-schema.version=2.3.4

COPY . /yavin
