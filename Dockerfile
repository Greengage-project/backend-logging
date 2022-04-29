FROM python:3.7-slim

COPY . /app
WORKDIR /app

RUN pip install aiormq fastapi "uvicorn[standard]" pydantic PyJWT 

CMD ["uvicorn", "main:app", "--reload"]