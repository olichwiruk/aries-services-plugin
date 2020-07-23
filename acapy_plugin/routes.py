from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema

from marshmallow import fields, Schema
import logging
import hashlib
from typing import Sequence

import acapy_plugin.schema_exchange as schema_exchange
from .records import SchemaExchangeRecord, SchemaExchangeRequestRecord


class SendRequestSchema(Schema):
    hash_id = fields.Str(required=True)
    connection_id = fields.Str(required=True)


class AddSchema(Schema):
    payload = fields.Str(required=True)


@docs(tags=["Schema Exchange"], summary="Request a schema by schema id")
@request_schema(SendRequestSchema())
async def requestSchemaRecord(request: web.BaseRequest):
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
        payload=params["hash_id"],
        connection_id=params["connection_id"],
        state=SchemaExchangeRequestRecord.STATE_PENDING,
        author=SchemaExchangeRequestRecord.AUTHOR_SELF,
    )

    if connection.is_ready:
        message = schema_exchange.Request(
            hash_id=params["hash_id"], exchange_id=record.exchange_id,
        )
        await outbound_handler(message, connection_id=connection.connection_id)

    try:
        record_id = await record.save(context, reason="Saved SchemaExchangeRequest")
    except StorageDuplicateError:
        raise web.HTTPConflict

    return web.json_response(
        {
            "hash_id": params["hash_id"],
            "connection_id": params["connection_id"],
            "record_id": record_id,
            "exchange_id": record.exchange_id,
            "state": record.state,
        }
    )


@docs(tags=["Schema Storage"], summary="Add schema to storage")
@request_schema(AddSchema())
async def addSchemaRecord(request: web.BaseRequest):
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)
    params = await request.json()

    record = SchemaExchangeRecord(params["payload"], "self")

    try:
        hash_id = await record.save(context)
    except StorageDuplicateError:
        hash_id = hashlib.sha256(params["payload"].encode("UTF-8")).hexdigest()
        record.retrieve_by_id(context, hash_id)

    return web.json_response({"hash_id": hash_id, "payload": record.payload,})


@docs(tags=["Schema Storage"], summary="Retrieve a schema record by it's hash_id")
async def getSchemaRecord(request: web.BaseRequest):
    context = request.app["request_context"]
    hash_id = request.match_info["hash_id"]

    try:
        record: SchemaExchangeRecord = await SchemaExchangeRecord.retrieve_by_id(
            context=context, record_id=hash_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    return web.json_response(record.serialize())


@docs(tags=["Schema Storage"], summary="Retrieve a list of schema records from storage")
async def getSchemaRecordList(request: web.BaseRequest):
    context = request.app["request_context"]
    logger = logging.getLogger(__name__)

    try:
        query = await SchemaExchangeRecord.query(context)
        logger.debug("RECORD_LIST %s", query)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    # create a list of serialized(in json format / dict format) records
    query_list = [i.serialize() for i in query]

    return web.json_response(query_list)


# Get schema request list
async def DEBUGGetSchemaRequestList(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    try:
        query = await SchemaExchangeRequestRecord.query(
            context, post_filter_positive=params
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    # create a list of serialized(in json format / dict format) records
    query_list = [i.serialize() for i in query]

    return web.json_response(query_list)


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/schema-exchange/request-schema", requestSchemaRecord),
            web.post("/schema-storage/add", addSchemaRecord),
            web.post("/schema-storage/list", getSchemaRecordList),
            web.post("/schema-storage/debug/request/list", DEBUGGetSchemaRequestList),
            web.get("/schema-storage/{hash_id}", getSchemaRecord, allow_head=False),
        ]
    )
