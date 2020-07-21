from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError
from aries_cloudagent.storage.base import BaseStorage

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
from typing import Sequence

from .records import ServiceRecord, ConsentSchema, ServiceSchema
from .discovery import Discovery


class AddSchema(Schema):
    label = fields.Str(required=True)
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


@request_schema(AddSchema())
@docs(tags=["verifiable-services"], summary="Add a verifiable service")
async def add(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    serviceRecord = ServiceRecord(
        label=params["label"],
        service_schema=params["service_schema"],
        consent_schema=params["consent_schema"],
    )
    hash_id = await serviceRecord.save(context)

    return web.json_response(serviceRecord.serialize())


@docs(
    tags=["verifiable-services"],
    summary="Get the list of all currently registered services",
)
async def getList(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        request = Discovery()
        await outbound_handler(request, connection_id=connection_id)
        return web.json_response(request.serialize())

    return web.json_response("failed")


@docs(
    tags=["verifiable-services"],
    summary="Get the list of all currently registered services",
)
async def get(request: web.BaseRequest):
    context = request.app["request_context"]
    connection_id = request.match_info["connection_id"]
    storage: BaseStorage = await context.inject(BaseStorage)

    if connection_id == "self":
        query = await ServiceRecord().query(context)

        # create a list of serialized(in json format / dict format) records
        query_serialized = [record.serialize() for record in query]

        return web.json_response(query_serialized)

    else:
        record = storage.search_records(
            "ServiceDiscovery", {"connection_id": connection_id}
        )
        record = await record.fetch_single()

        return web.json_response(record.value)


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/verifiable-services/add", add),
            web.get(
                "/verifiable-services/send/{connection_id}", getList, allow_head=False
            ),
            web.get("/verifiable-services/{connection_id}", get, allow_head=False),
        ]
    )
