"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema

from marshmallow import fields, Schema
import logging

from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError

from .schema_exchange import SchemaExchange
from .records import SchemaExchangeRecord


class SendSchema(Schema):
    payload = fields.Str(required=True)
    connection_id = fields.Str(required=True)


class GetSchema(Schema):
    hashid = fields.Str(required=True)


@docs(tags=["Schema Exchange"], summary="Send a schema to the connection")
@request_schema(SendSchema())
async def send(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()
    logger = logging.getLogger(__name__)

    try:
        logger.debug(
            "ROUTES SCHEMA EXCHANGE SEND connection_id:%s", params["connection_id"]
        )
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        message = SchemaExchange(payload=params["payload"])
        await outbound_handler(message, connection_id=connection.connection_id)

    return web.json_response(
        {"payload": message.payload, "connection_id": params["connection_id"]}
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
            "hashid": record.hashid,
            "payload": record.payload,
            "state": record.state,
            "author": record.author,
            "connection_id": record.connection_id,
        }
    )


async def register(app: web.Application):
    app.add_routes(
        [
            web.post("/schema-exchange/send", send),
            web.get("/schema-exchange/{hashid}", get),
        ]
    )
