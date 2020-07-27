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
from ..discovery.models import ConsentSchema, ServiceSchema
from .models import ServiceIssueRecord


class ApplySchema(Schema):
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())
    connection_id = fields.Str()


@docs(
    tags=["Verifiable Services"],
    summary="Get the saved list of services from another agent",
)
@request_schema(ApplySchema())
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
        record = ServiceIssueRecord(
            state=ServiceIssueRecord.ISSUE_WAITING_FOR_RESPONSE,
            author=ServiceIssueRecord.AUTHOR_SELF,
            service_schema=params["service_schema"],
            consent_schema=params["consent_schema"],
            connection_id=params["connection_id"],
        )

        await record.save(context)

        request = Application(
            service_schema=params["service_schema"],
            consent_schema=params["consent_schema"],
            exchange_id=record.exchange_id,
        )
        await outbound_handler(request, connection_id=params["connection_id"])
        return web.json_response("success")

    return web.json_response("connection not ready")
