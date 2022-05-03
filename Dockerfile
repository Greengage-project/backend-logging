FROM python:3.9-slim-bullseye

COPY . /app
WORKDIR /app

RUN pip install aiormq

CMD ["python", "./main.py"]