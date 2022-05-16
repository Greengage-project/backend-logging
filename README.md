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

The following are all the environment variables that need to be specified, during the setup of the services.

RABBITMQ_DEFAULT_USER=
RABBITMQ_DEFAULT_PASS=
RABBITMQ_HOST=
RABBITMQ_USER=
RABBITMQ_PASSWORD=
EXCHANGE_NAME = logging

Another important detail is the version of the backend-logging service, this must correspond to the most recent version of the microservice (this information can be seen at the [link](https://github.com/interlink-project/backend-logging/tags).


## Send or produce logs

A producer program need to connect to the data store to send a messages. There are two ways to send messages (logs) to be stored, they are:
- Use the API.
- Use the RabbitMQ (message broker).


### Use of RabbitMQ

Although it is possible to use the API deployed by the "backend-logging" microservice, another way is to connect directly to the message broker. The steps required to send messages are as follows:

#### 1. Connect to the RabbitMQ microservice (Python Flask).

The connection to the RabbitMQ service may vary depending on the libraries used by the producer program. RabbitMQ currently supports connection to most programming languages. In order to illustrate an example of how a connection is made, we will address the code used with python.

The library that we will use in this example is [Pika Python client](https://pika.readthedocs.io/en/stable/). Pika is a pure-Python implementation of the AMQP 0-9-1 protocol. The foollow function will connect to the service and send a message:

```
1 import pika
  from base64 import b64encode
  from uuid import UUID

2 def log(data: dict):
3    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
4    parameters = pika.ConnectionParameters(host=rabbitmq_host,credentials=credentials)

5    connection = pika.BlockingConnection(parameters)

6    channel = connection.channel()

7    channel.exchange_declare(
        exchange=exchange_name, exchange_type='direct'
    )
8    request = b64encode(json.dumps(data,cls=UUIDEncoder).encode())

9    channel.basic_publish(
        exchange=exchange_name,
        routing_key='logging', 
        body=request
    )
```
Three environment variables must be specified to make the connection, these were specified during the configuration process. These are:

- exchange_name = os.environ.get("EXCHANGE_NAME")
- rabbitmq_host = os.environ.get("RABBITMQ_HOST")
- rabbitmq_user = os.environ.get("RABBITMQ_USER")
- rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD")

The username and password and exchange_name must be the same as the one used for the rabbitMQ microservice deployment and the hostname must be the name of the service within the docker-compose. In or case it is "rabbitmq".

Then we create the connection to the server and establish a communication channel and declares the exchanger name and type. These parameters must be defined when deploying the RabbitMQ service and are defined in the .env file that contains the environment variables.

Finally, the message is sent through the basic_publish function on the previously established channel. Again the variable routing_key was defined in the rabbitMQ deployment and in our case it is 'logging'. The request variable, (at line 9) is the encoded form of the python dictionary that is the input to the function, we use library base64 as is show in the first part of the code.

The complete python file that performs the sending of messages for the servicepedia microservice is [messages.py](https://github.com/interlink-project/interlinker-service-augmenter/blob/master/app/messages.py).

#### 2. Connect to the RabbitMQ microservice ( Python Fastapi ).

[FastAPI](https://fastapi.tiangolo.com/) is a modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints. This platform allows the use of libraries such as React that make asynchronous calls (await).

The library that we will use in this example is [Aiormq Python client](https://github.com/mosquito/aiormq). Aiormq is a pure python AMQP client library. The foollow function will connect to the service and send a message:

```
async def log(data: dict):
    if is_logging_disabled():
        return

    try:
        data["user_id"] = context.data.get("user", {}).get("sub", None)
    except:
        data["user_id"] = None
    data["service"] = "coproduction"

    request = b64encode(json.dumps(data,cls=UUIDEncoder).encode())
    
    connection = await aiormq.connect("amqp://{}:{}@{}/".format(rabbitmq_user, rabbitmq_password, rabbitmq_host))
    channel = await connection.channel()

    await channel.exchange_declare(
        exchange=exchange_name, exchange_type='direct'
    )

    await channel.basic_publish(
        request, 
        routing_key='logging', 
        exchange=exchange_name,
        properties=aiormq.spec.Basic.Properties(
            delivery_mode=2
        )
    )
    print("MENSAJE ENVIADO POR RABBITMQ")
```
The similarity with the previous example is evident, first it connects with the credentials, it establishes a channel, route identifier and an exchanger. The message is then sent.

The complete python file that performs the sending of messages for the servicepedia microservice is [messages.py](https://github.com/interlink-project/backend-coproduction/blob/master/coproduction/app/messages.py).

#### 2. Definition of a data structure.

The data sent to the registration service needs to contain the information relevant to the application. In the case of Servicepedia, for example, a data log could contain the following information when a user creates a new asset.

```
await log({
    **{
    "model": "ASSET",
    "action": "CREATE",
    "crud": False,
    "coproductionprocess_id": asset.task.objective.phase.coproductionprocess_id,
    "phase_id": asset.task.objective.phase_id,
    "objective_id": asset.task.objective_id,
    "task_id": asset.task_id,
    "asset_id": asset.id,
},
**specific_log_data
})
```

The above line of code takes the data from a description and creates a dictionary including (id,title and description). It also calls the log() function that was defined to send log messages.

The implementation of the sending functions could include a series of additional data such as user_id or any other relevant data. This process could be included before sending the message in the log() function as is done in the servicepedia case.


