"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema

from marshmallow import fields, Schema
import logging

from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError

from .schema_exchange import SchemaExchange


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
        logger.debug("ROUTES SCHEMA EXCHANGE SEND %s", params["connection_id"])
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        message = SchemaExchange(payload=params["payload"])
        await outbound_handler(message, connection_id=connection.connection_id)

    adminReply = SendSchema()
    return web.json_response(
        {"payload": message.payload, "connection_id": params["connection_id"]}
    )


async def register(app: web.Application):
    app.add_routes([web.post("/schema-exchange/send", send)])
