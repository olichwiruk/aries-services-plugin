from aries_cloudagent.connections.models.connection_record import ConnectionRecord
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError, StorageDuplicateError

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema

from marshmallow import fields, Schema
import logging
import hashlib
from typing import Sequence

from .records import ServiceRecord, ConsentSchema, ServiceSchema


class AddSchema(Schema):
    service_schema = fields.Nested(ServiceSchema())
    consent_schema = fields.Nested(ConsentSchema())


@request_schema(AddSchema())
@docs(tags=["verifiable-services"], summary="Add a verifiable service")
async def add(request: web.BaseRequest):
    context = request.app["request_context"]
    params = await request.json()

    serviceRecord = ServiceRecord(params["service_schema"], params["consent_schema"])
    serviceRecord.save(context)

    return web.json_response(serviceRecord.serialize())


async def register(app: web.Application):
    app.add_routes(
        [web.post("/verifiable-services/add", add),]
    )
