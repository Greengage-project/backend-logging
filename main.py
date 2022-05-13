import asyncio
import aiormq

from aiormq.abc import DeliveredMessage
import os
import logging
from sys import stdout
from base64 import b64decode
from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from deps import get_current_user
import json

BASE_PATH = os.environ.get("BASE_PATH")

app = FastAPI(
    docs_url="/docs", openapi_url=f"/api/v1/openapi.json", root_path=BASE_PATH
)

# Define logger
logger = logging.getLogger('mylogger')

logger.setLevel(logging.DEBUG) # set logger level
# logFormatter = logging.Formatter\
# ("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
logFormatter = logging.Formatter\
("%(message)s")
# ("%(asctime)s %(levelname)-8s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


exchange_name = os.environ.get("EXCHANGE_NAME")
rabbitmq_host = os.environ.get("RABBITMQ_HOST")
rabbitmq_user = os.environ.get("RABBITMQ_USER")
rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD")

async def log_event(message: DeliveredMessage):
    response = b64decode(message.body)
    message_dict = json.loads(response.decode("utf-8"))
    message_dict["from"] = "MESSAGE_BROKER"
    logger.info(message_dict)

    await message.channel.basic_ack(
        message.delivery.delivery_tag
    )

async def consume(loop):
    connection = await aiormq.connect("amqp://{}:{}@{}/".format(rabbitmq_user, rabbitmq_password, rabbitmq_host), loop=loop)
    channel = await connection.channel()
    
    await channel.basic_qos(prefetch_count=1)

    await channel.exchange_declare(
        exchange=exchange_name, exchange_type='direct'
    )
    
    declare = await channel.queue_declare(durable=True, auto_delete=True)
    await channel.queue_bind(declare.queue, exchange_name, routing_key='logging')

    await channel.basic_consume(declare.queue, log_event)

@app.on_event('startup')
def startup():
    loop = asyncio.get_event_loop()
    # use the same loop to consume
    asyncio.ensure_future(consume(loop)) 

@app.get("/")
async def root():
    return RedirectResponse(url=f"{BASE_PATH}/docs")


class LogsCreate(BaseModel):
    action: str
    model: str
    object_id: str


@app.post("/api/v1/log")
async def insert_log(
    *,
    log_in: LogsCreate,
    # current_user: dict = Depends(get_current_user),
):
    """
    Insert new log
    """
    message_dict = log_in.__dict__
    message_dict["from"] = "API"
    return logger.info(message_dict)



