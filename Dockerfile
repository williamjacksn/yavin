FROM python:3.7-alpine

ENV TZ UTC

COPY requirements.txt /app/requirements.txt

RUN apk --no-cache add gcc musl-dev postgresql-dev \
 && /usr/local/bin/pip install --no-cache-dir --requirement /app/requirements.txt

COPY . /app

CMD /usr/local/bin/python /app/run.py
