FROM python:3.9-slim-buster as builder

COPY . /app
WORKDIR /app

RUN pip install aiormq fastapi "uvicorn[standard]" pydantic PyJWT gunicorn

FROM builder as dev
CMD ["./wait-for-it.sh", "rabbitmq:5672", "--", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "${PORT}"]

FROM builder as prod
CMD ["./wait-for-it.sh", "rabbitmq:5672", "--", "gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "gunicorn_conf.py", "main:app"]