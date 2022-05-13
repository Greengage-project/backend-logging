FROM python:3.9-slim-bullseye

COPY . /app
WORKDIR /app

RUN pip install aiormq fastapi "uvicorn[standard]" pydantic PyJWT 

CMD ["./wait-for-it.sh", "rabbitmq:5672", "--", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "${PORT}"]