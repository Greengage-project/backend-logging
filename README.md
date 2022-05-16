# Logging Instruction for Microservices

The microservice called "backend-logging", aims to centralize the logs that resulf from user actions. Within each of the deployed microservices, the necessary functions for sending logs to this component must be implemented.

The purpose of this short manual is to describe the series of steps that a microservice must perform to store and access the logs.

## Run the service
To deploy it locally in Docker, two microservices are required: rabbitmq and logging. 

[RabbitMQ](https://www.rabbitmq.com/) is a message broker: it accepts and forwards messages. You can think about it as a post office: when you depot the mail that you want posting in a post box, you can be sure that the letter carrier will eventually deliver the mail to your recipient. In this analogy, RabbitMQ is a post box, a post office, and a letter carrier.

The Logging microservice takes all information in the queue (a queue is the name for a post box which lives inside RabbitMQ) and stores it in a central storage unit.

The service must be included within docker-compose. For example:

```yaml
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
### Data structure

The data sent to the registration service needs to contain the information relevant to the application. In the case of the coproduction microservice, for example, a data log could contain the following information when a user creates a new asset.

```python
await log({
    "model": "ASSET",
    "action": "CREATE",
    "coproductionprocess_id": asset.task.objective.phase.coproductionprocess_id,
    "phase_id": asset.task.objective.phase_id,
    "objective_id": asset.task.objective_id,
    "task_id": asset.task_id,
    "asset_id": asset.id,
    "external_interlinker": False,
    "interlinker_type": "SOFTWAREINTERLINKER EXTERNALINTERLINKER",
    "knowledgeinterlinker_id": asset.knowledgeinterlinker_id,
    "knowledgeinterlinker_name": interlinker.get("name"),
    "softwareinterlinker_id": interlinker.get("softwareinterlinker").get("id"),
    "softwareinterlinker_name": interlinker.get("softwareinterlinker").get("name"),
})
```

The above line of code calls the log function (mentioned afterwards) with a dictionary including relevant data about the action performed (model, action, phase, task_id, etc). The amount of information saved in a log depends on the specific action that you want to record, therefore the internal structure could vary from one to another. 

Nevertheless, it is recommended to add at least these keys:

* "user_id"
* "service" ("coproduction", "servicepedia"...)
* "model" ("ASSET", "COPRODUCTIONPROCESS"...)
* "action" (GET, CREATE, UPDATE, DELETE)

### Send a log through a POST request to the API

![API](images/api.png)

You can log an action by simply creating a POST request to these endpoints (depending on the environment).

* POST http://localhost/logging/api/v1/log
* POST https://dev.interlink-project.eu/logging/api/v1/log
* POST https://demo.interlink-project.eu/logging/api/v1/log
* POST https://zgz.interlink-project.eu/logging/api/v1/log
* POST https://varam.interlink-project.eu/logging/api/v1/log
* POST https://mef.interlink-project.eu/logging/api/v1/log

Furthermore, the calls can be made internally, by replacing the DNS name by the name of the logging docker service:

* POST http://logging/logging/api/v1/log

### Send a log through RabbitMQ

Although it is possible to use the API deployed by the "backend-logging" microservice, another way is to connect directly to the message broker. The steps required to send messages are as follows:

The connection to the RabbitMQ service may vary depending on the libraries used by the producer program. RabbitMQ currently supports connection to most programming languages. In order to illustrate an example of how a connection is made, we will describe the code written in python.

Three environment variables must be specified to make the connection, these were specified during the configuration process. These are:

- exchange_name = os.environ.get("EXCHANGE_NAME")
- rabbitmq_host = os.environ.get("RABBITMQ_HOST")
- rabbitmq_user = os.environ.get("RABBITMQ_USER")
- rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD")

The username and password and exchange_name must be the same as the one used for the rabbitMQ microservice deployment and the hostname must be the name of the service within the docker-compose. In or case it is "rabbitmq".

Then we create the connection to the server and establish a communication channel and declares the exchanger name and type. These parameters must be defined when deploying the RabbitMQ service and are defined in the .env file that contains the environment variables.

Finally, the message is sent through the basic_publish function on the previously established channel. Again, the variable routing_key was defined in the rabbitMQ deployment and in our case it is 'logging'. The request variable, (at line 9) is the encoded form of the python dictionary that is the input to the function, we use library base64 as is show in the first part of the code.

The library used in this example is [Aiormq Python client](https://github.com/mosquito/aiormq). Aiormq is a pure python AMQP client library. The following function will connect to the service and send a message:

```python

rabbitmq_url = "amqp://{}:{}@{}/".format(rabbitmq_user rabbitmq_password, rabbitmq_host)

async def log(data: dict):
    if is_logging_disabled():
        return

    data["user_id"] = user.get("id", None)
    data["service"] = "coproduction"

    request = b64encode(json.dumps(data,cls=UUIDEncoder).encode())
    
    connection = await aiormq.connect(rabbitmq_url)
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
```

The complete python file that performs the sending of messages for the servicepedia microservice is [messages.py](https://github.com/interlink-project/backend-coproduction/blob/master/coproduction/app/messages.py).


