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

    record = SchemaExchangeRequestRecord(
        payload=params["payload"],
        connection_id=params["connection_id"],
        state=SchemaExchangeRequestRecord.STATE_PENDING,
        author=SchemaExchangeRequestRecord.AUTHOR_SELF,
    )

    if connection.is_ready:
        message = schema_exchange.Request(
            payload=params["payload"],
            cross_planetary_identification_number=record.cross_planetary_identification_number,
        )
        await outbound_handler(message, connection_id=connection.connection_id)

    try:
        record_id = await record.save(context, reason="Saved SchemaExchangeRequest")
    except StorageDuplicateError:
        raise web.HTTPConflict

    return web.json_response(
        {
            "payload": params["payload"],
            "connection_id": params["connection_id"],
            "record_id": record_id,
            "cross_planetary_identification_number": record.cross_planetary_identification_number,
        }
    )


class SendSchemaResponse(Schema):
    payload = fields.Str(required=True)
    cross_planetary_identification_number = fields.Str(required=True)
    decision = fields.Str(required=True)


## TODO: I need to figure out how to tell the second agent  which request are we talking about
@docs(tags=["Schema Exchange"], summary="Send response to the pending schema request")
@request_schema(SendSchemaResponse())
async def sendResponse(request: web.BaseRequest):
    outbound_handler = request.app["outbound_message_router"]
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)
    params = await request.json()

    try:
        record: SchemaExchangeRequestRecord = await SchemaExchangeRequestRecord.retrieve_by_cross_planetary_identification_number(
            context, params["cross_planetary_identification_number"]
        )
        logger.debug("\n\nSchemaExchangeRequestRecord query: %s", record)
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, record.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    record_id = "Connection not ready"
    if connection.is_ready:
        logger.debug("\n\nCONNECTION SEND RESPONSE Connection_is_ready\n\n")
        message = schema_exchange.Response(
            payload=params["payload"],
            decision=params["decision"],
            cross_planetary_identification_number=params[
                "cross_planetary_identification_number"
            ],
        )
        await outbound_handler(message, connection_id=connection.connection_id)

        record.state = params["decision"]
        record_id = await record.save(context)

    return web.json_response(
        {
            "record_id": record_id,
            "payload": message.payload,
            "connection_id": params["connection_id"],
            "decision": params["decision"],
            "cross_planetary_identification_number": record.cross_planetary_identification_number,
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


async def getSchemaExchangeRecords(request: web.BaseRequest):
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)

    try:
        query = await SchemaExchangeRecord.query(context)
        logger.debug("RECORD_LIST %s", query)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    query_list = [
        {
            "payload": i.payload,
            "author": i.author,
            "connection_id": i.connection_id,
            "hash_id": i._id,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        }
        for i in query
    ]

    return web.json_response(query_list)


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


class GetRequestList(Schema):
    state = fields.Str(required=False)
    author = fields.Str(required=False)


async def getRequestList(request: web.BaseRequest):
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)
    params = await request.json()

    positiveFilter = {}
    positiveFilter["author"] = params["author"]
    positiveFilter["state"] = params["state"]

    logger.debug("Get Request List %s", positiveFilter)

    try:
        query = await SchemaExchangeRequestRecord.query(
            context, post_filter_positive=positiveFilter
        )
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
            web.post("/schema-exchange/request/list", getRequestList),
            web.post("/schema-exchange/records/list", getSchemaExchangeRecords),
            web.post("/schema-exchange/send", send),
            web.post("/schema-exchange/send-response", sendResponse),
            web.get("/schema-exchange/record/{hashid}", get),
            web.get("/schema-exchange/request/{record_id}", getRequest),
        ]
    )
