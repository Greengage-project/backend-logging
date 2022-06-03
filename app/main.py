import asyncio
import json
import logging
import os
from base64 import b64decode
from datetime import datetime
from sys import stdout
from typing import Optional

import aiormq
from aiormq.abc import DeliveredMessage
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Extra

BASE_PATH = os.environ.get("BASE_PATH")
ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST", "elasticsearch")
ELASTICSEARCH_PORT = int(os.environ.get("ELASTICSEARCH_PORT", 9200))


class LogsCreate(BaseModel, extra=Extra.allow):
    user_id: str
    service: str
    action: Optional[str]
    model: Optional[str]
    object_id: Optional[str]
    timestamp: Optional[str] = datetime.now()


app = FastAPI(
    docs_url="/docs", openapi_url=f"/api/v1/openapi.json", root_path=BASE_PATH
)
es = AsyncElasticsearch([
    {'host': ELASTICSEARCH_HOST, 'port': ELASTICSEARCH_PORT, 'scheme': 'http'},
])

# This gets called once the app is shutting down.


@app.on_event("shutdown")
async def app_shutdown():
    await es.close()

# Define logger
logger = logging.getLogger('mylogger')

logger.setLevel(logging.DEBUG)  # set logger level
# logFormatter = logging.Formatter\
# ("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
logFormatter = logging.Formatter("%(message)s")
# ("%(asctime)s %(levelname)-8s %(message)s")
consoleHandler = logging.StreamHandler(stdout)  # set streamhandler to stdout
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

    try:
        LogsCreate(**message_dict)
        logger.info(json.dumps(message_dict))
        await es.index(index="logs", document=message_dict)
    except Exception as e:
        logger.error(json.dumps(message_dict), "not valid", e)

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
    try:
        asyncio.ensure_future(consume(loop))
    except Exception as e:
        logger.exception(e)
        raise Exception("ERROR TO START CONSUMER")


@app.get("/")
async def root():
    return RedirectResponse(url=f"{BASE_PATH}/docs")


@app.post("/api/v1/log")
async def insert_log(
    *,
    log_in: LogsCreate,
):
    """
    Insert new log
    """
    message_dict = log_in.__dict__
    message_dict["from"] = "API"
    return logger.info(message_dict)


@app.get("/api/v1/log")
async def get_log(
    from_date: datetime = None,
    to_date: datetime = datetime.now(),
    model: str = None,
    action: str = None,
    service: str = None,
):
    query = {"match_all": {}}
    """
    Get logs
    """
    if from_date and to_date:
        del query["match_all"] 
        query["range"] = {
         "@timestamp":{
            "gte": "now-3d/d",
            "lt": "now/d"
         }
      }

    if service or action or model:
        del query["match_all"] 
        query["bool"] = { "must": [] }
    if service:
        query["bool"]["must"].append({"match": {"service": service}})
    if action:
        query["bool"]["must"].append({"match": {"action": action}})
    if model:
        query["bool"]["must"].append({"match": {"model": model}})
        
    return await es.search(
        index="logs",
        body={"query": query},
        size=20,
    )
