import asyncio
import json
import logging
import os
import uuid
from base64 import b64decode
from datetime import datetime
from sys import stdout
from typing import List, Optional

import aiormq
from aiormq.abc import DeliveredMessage
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from fastapi import FastAPI, Query
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
    timestamp: Optional[datetime] = datetime.now()


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
        message_dict = LogsCreate(**message_dict).dict()
        logger.info(json.dumps(message_dict, default=str))
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
    models: List[str] = Query(None),
    actions: List[str] = Query(None),
    services: List[str] = Query(None),
    coproductionprocess_ids: List[str] = Query(None),
    team_ids: List[str] = Query(None),
    user_ids: List[str] = Query(None),
    size: int = 20
):
    if size > 200:
        size = 200
    query = {"match_all": {}}
    """
    Get logs
    """
    if (from_date and to_date) or services or actions or models or coproductionprocess_ids or user_ids or team_ids:
        del query["match_all"]
    
    if from_date and to_date:
        query["range"] = {
            "timestamp": {}
        }
        query["range"]["timestamp"]["gte"] = from_date.isoformat()
        query["range"]["timestamp"]["lt"] = to_date.isoformat()
      
    

    if services or actions or models or coproductionprocess_ids or user_ids or team_ids:
        query["bool"] = { "must": [] }
    if services:
        query["bool"]["must"].append({"terms": {"service.keyword": services}})
    if actions:
        query["bool"]["must"].append({"terms": {"action.keyword": actions}})
    if models:
        query["bool"]["must"].append({"terms": {"model.keyword": models}})
    if coproductionprocess_ids:
        query["bool"]["must"].append({"terms": {"coproductionprocess_id.keyword": coproductionprocess_ids}})
    if user_ids:
        query["bool"]["must"].append({"terms": {"user_id.keyword": user_ids}})
    if team_ids:
        query["bool"]["must"].append({"terms": {"team_id.keyword": team_ids}})

    return await es.search(
        index="logs",
        body={"query": query},
        size=size,
    )


