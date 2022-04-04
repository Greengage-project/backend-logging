import asyncio
import aiormq

from aiormq.abc import DeliveredMessage
import os
import logging
from sys import stdout
import json
from base64 import b64encode, b64decode

class RabbitBody:
    service: str
    data: dict
    
    def __init__(self, service, data):
        self.service = service
        self.data = data

    def encode(self):
        dicc = {"service": self.service, "data": self.data}
        return b64encode(json.dumps(dicc).encode())

    @staticmethod
    def decode(encoded):
        dicc = json.loads(b64decode(encoded))
        return RabbitBody(**dicc)
        
# Define logger
logger = logging.getLogger('mylogger')

logger.setLevel(logging.DEBUG) # set logger level
# logFormatter = logging.Formatter\
# ("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
logFormatter = logging.Formatter\
("%(asctime)s %(levelname)-8s %(message)s")
consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


exchange_name = os.environ.get("EXCHANGE_NAME")
rabbitmq_host = os.environ.get("RABBITMQ_HOST")
rabbitmq_user = os.environ.get("RABBITMQ_USER")
rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD")

async def log_event(message: DeliveredMessage):
    response = RabbitBody.decode(message.body)
    logger.info(response.__dict__)

    await message.channel.basic_ack(
        message.delivery.delivery_tag
    )

async def consume():
    connection = await aiormq.connect("amqp://{}:{}@{}/".format(rabbitmq_user, rabbitmq_password, rabbitmq_host))
    channel = await connection.channel()
    
    await channel.basic_qos(prefetch_count=1)

    await channel.exchange_declare(
        exchange=exchange_name, exchange_type='direct'
    )
    
    declare = await channel.queue_declare(durable=True, auto_delete=True)
    await channel.queue_bind(declare.queue, exchange_name, routing_key='logging')

    await channel.basic_consume(declare.queue, log_event)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    logger.info("CONSUMER STARTED")
    loop.run_until_complete(consume())
    loop.run_forever()