import json
import logging
import os
from datetime import datetime
from sys import stdout
from typing import List, Optional

from elasticsearch import Elasticsearch
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Extra

BASE_PATH = os.environ.get("BASE_PATH")
ELASTIC_HOST = os.environ.get("ELASTIC_HOST", "elasticsearch")
ELASTIC_PORT = int(os.environ.get("ELASTIC_PORT", 9200))
ELASTIC_USERNAME= os.environ.get("ELASTIC_USERNAME", "elastic")
ELASTIC_PASSWORD = os.environ.get("ELASTIC_PASSWORD", "elastic")


class LogsCreate(BaseModel, extra=Extra.allow):
    user_id: str
    service: str
    action: Optional[str]
    model: Optional[str]
    timestamp: Optional[datetime] = datetime.now()


app = FastAPI(
    docs_url="/docs", openapi_url=f"/api/v1/openapi.json", root_path=BASE_PATH
)
es = Elasticsearch([
        {'host': ELASTIC_HOST, 'port': ELASTIC_PORT, 'scheme': 'http', },
    ], http_auth=(ELASTIC_USERNAME, ELASTIC_PASSWORD))

# This gets called once the app is shutting down.
@app.on_event("shutdown")
async def app_shutdown():
    es.close()

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

def send_to_backends(message_dict):
    logger.info(json.dumps(message_dict, default=str))
    es.index(index="logs", doc_type="log", body=message_dict)
    return True

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
    message_dict = log_in.dict()
    message_dict["from"] = "API"
    return send_to_backends(message_dict)


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

    return es.search(
        index="logs",
        body={"query": query},
        size=size,
    )


