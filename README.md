# Logging Instruction for Microservices

The microservice called "backend-logging", aims to centralize the logs that are maintained by user actions. Within each of the deployed microservices, the necessary functions for sending logs to this component must be implemented.

The purpose of this instruction manual is to describe the series of steps that a microservice must perform to store and access the logs.

## Run the service
To deploy it locally in docker is required to deploy two microservices: rabbitmq and logging. 

[RabbitMQ](https://www.rabbitmq.com/) is a message broker: it accepts and forwards messages. You can think about it as a post office: when you put the mail that you want posting in a post box, you can be sure that the letter carrier will eventually deliver the mail to your recipient. In this analogy, RabbitMQ is a post box, a post office, and a letter carrier.

Logging microservice take all information in the queue (a queue is the name for a post box which lives inside RabbitMQ) and stores it in a central storage unit.

The service must be included within docker-compose. For example:

```
 rabbitmq:
    image: rabbitmq:3-management
    container_name: rabbitmq
    env_file:
      - ./.env
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=${RABBITMQ_DEFAULT_USER}
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_DEFAULT_PASS}
    healthcheck:
      test: rabbitmq-diagnostics -q ping
      interval: 30s
      timeout: 30s
      retries: 3
    networks:
      - traefik-public
      - default
    

  logging:
    image: interlinkproject/backend-logging:v1.0.0
    container_name: logging
    env_file:
      - ./.env
    restart: on-failure
    networks:
      - traefik-public
      - default
    depends_on:
      rabbitmq:
        condition: service_healthy
    command: ["./wait-for-it.sh", "rabbitmq:5672", "--", "python", "./main.py"]
```
The variable "RABBITMQ_DEFAULT_USER", contains the user name assigned to the Rabbitmq service, while the variable "RABBITMQ_DEFAULT_PASS" is the password used at login time. All the lines of code presented above have been taken as a reference from the [file](https://github.com/interlink-project/interlinker-service-augmenter/blob/master/docker-compose.yml) used for the local deployment of the servicepedia.


## Connect to the server

## Send logs


## Example from Python
### Import the library

### Connect to the service

### Send information

### Example of data
