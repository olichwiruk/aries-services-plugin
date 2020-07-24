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

from .message_types import Application


class ApplySchema(Schema):
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
    connection_id = fields.Str()


async def apply(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection: ConnectionRecord = await ConnectionRecord.retrieve_by_id(
            context, params["connection_id"]
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound

    if connection.is_ready:
        request = Application(
            service_schema=context.message.service_schema,
            consent_schema=context.message.consent_schema,
        )
        await outbound_handler(request, connection_id=params["connection_id"])
        return web.json_response(request.serialize())

    return web.json_response("connection not ready")
