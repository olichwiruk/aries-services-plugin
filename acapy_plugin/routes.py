from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema

from marshmallow import fields, Schema
import logging
import hashlib
from typing import Sequence

import acapy_plugin.schema_exchange as schema_exchange
from .records import SchemaExchangeRecord, SchemaExchangeRequestRecord


class SendSchema(Schema):
    payload = fields.Str(required=True)
    connection_id = fields.Str(required=True)


@docs(tags=["Schema Exchange"], summary="Send a schema to the connection")
@request_schema(SendSchema())
async def send(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()
    logger = logging.getLogger(__name__)

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
    except StorageNotFoundError or StorageDuplicateError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        message = schema_exchange.Request(payload=params["payload"])
        await outbound_handler(message, connection_id=connection.connection_id)

    record = SchemaExchangeRequestRecord(
        payload=message.payload,
        connection_id=params["connection_id"],
        state=SchemaExchangeRequestRecord.STATE_PENDING,
        author=SchemaExchangeRequestRecord.AUTHOR_SELF,
    )

    try:
        record_id = await record.save(context, reason="Saved SchemaExchangeRequest")
    except StorageDuplicateError:
        raise web.HTTPConflict

    return web.json_response(
        {
            "payload": message.payload,
            "connection_id": params["connection_id"],
            "record_id": record_id,
        }
    )


class SendSchemaResponse(Schema):
    payload = fields.Str(required=True)
    hashid = fields.Str(required=True)
    decision = fields.Str(required=True)


@docs(tags=["Schema Exchange"], summary="Send response to the pending schema request")
@request_schema(SendSchemaResponse())
async def sendResponse(request: web.BaseRequest):
    outbound_handler = request.app["outbound_message_router"]
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)
    params = await request.json()

    logger.debug(
        "ROUTES SCHEMA EXCHANGE SEND RESPONSE \nconnection_id:%s \ndecision:%s \nhashid: %s \npayload: %s",
        params["connection_id"],
        params["decision"],
        params["hashid"],
        params["payload"],
    )

    try:
        record: SchemaExchangeRequestRecord = await SchemaExchangeRequestRecord.retrieve_by_id(
            context, params["hashid"]
        )
        logger.debug("\n\nSchemaExchangeRequestRecord query: %s", record)
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, record.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        message = schema_exchange.Response(
            payload=params["payload"], decision=params["decision"]
        )
        await outbound_handler(message, connection_id=connection.connection_id)

        record.state = params["decision"]
        await record.save(context)

    return web.json_response(
        {
            "payload": message.payload,
            "connection_id": params["connection_id"],
            "decision": params["decision"],
        }
    )


@docs(tags=["Schema Exchange"], summary="Get schema by schema id")
async def get(request: web.BaseRequest):
    context = request.app["request_context"]
    params = request.match_info
    logger = logging.getLogger(__name__)
    logger.debug("ROUTES SCHEMA EXCHANGE GET hashid: %s", params["hashid"])

    try:
        record: SchemaExchangeRecord = await SchemaExchangeRecord.retrieve_by_id(
            context=context, record_id=params["hashid"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response(
        {
            "hashid": params["hashid"],
            "payload": record.payload,
            "state": record.state,
            "author": record.author,
            "connection_id": record.connection_id,
        }
    )


@docs(tags=["Schema Exchange"], summary="Get schema request by schema id")
async def getRequest(request: web.BaseRequest):
    context = request.app["request_context"]
    params = request.match_info

    try:
        record: SchemaExchangeRequestRecord = await SchemaExchangeRequestRecord.retrieve_by_id(
            context=context, record_id=params["record_id"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response(
        {
            "record_id": params["record_id"],
            "payload": record.payload,
            "state": record.state,
            "author": record.author,
            "connection_id": record.connection_id,
        }
    )


async def getRequestList(request: web.BaseRequest):
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)
    try:
        query = await SchemaExchangeRequestRecord.query(context)
        logger.debug("RECORD_LIST %s", query)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    query_list = [
        {
            "payload": i.payload,
            "author": i.author,
            "connection_id": i.connection_id,
            "record_id": i._id,
            "state": i.state,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        }
        for i in query
    ]

    return web.json_response(query_list)


async def register(app: web.Application):
    app.add_routes(
        [
            web.get("/schema-exchange/request-list", getRequestList),
            web.post("/schema-exchange/send", send),
            web.post("/schema-exchange/send-response", sendResponse),
            web.get("/schema-exchange/record/{hashid}", get),
            web.get("/schema-exchange/request/{record_id}", getRequest),
        ]
    )
