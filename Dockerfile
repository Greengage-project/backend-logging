FROM python:3.7-slim

COPY . /app
WORKDIR /app

RUN pip install aiormq fastapi "uvicorn[standard]" pydantic PyJWT 

CMD ["./wait-for-it.sh", "rabbitmq:5672", "--", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "${PORT}"]