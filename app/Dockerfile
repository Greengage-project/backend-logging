FROM python:3.9-slim-buster as builder

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

FROM builder as dev
CMD "wait-for-it --service ${RABBITMQ_HOST}:${RABBITMQ_PORT} --service ${ELASTIC_HOST}:${ELASTIC_PORT} -- uvicorn main:app --reload --host 0.0.0.0 --port ${PORT}"

FROM builder as prod
CMD "wait-for-it --service ${RABBITMQ_HOST}:${RABBITMQ_PORT} --service ${ELASTIC_HOST}:${ELASTIC_PORT} -- gunicorn -k uvicorn.workers.UvicornWorker -c gunicorn_conf.py main:app"
