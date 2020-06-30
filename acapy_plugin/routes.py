"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema

from marshmallow import fields, Schema

from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError


class SendSchema(Schema):
    # request
    payload = fields.Str(required=True)
    connection_id = fields.Str(required=True)
    # response
    hashid = fields.Str(required=False)


@docs(tags=["TEST"], summary="Send a basic message to a connection")
@request_schema(SendSchema())
async def send(request: web.BaseRequest):
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, context.message.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready()

    return web.Response(text="aaaaa")


async def register(app: web.Application):
    app.add_routes([web.post("/schema-exchange/send", send)])

